import os
import re
import subprocess
from ebooklib import epub
from bs4 import BeautifulSoup
import shutil

def clean_filename(filename):
    """清理文件名中的非法字符"""
    # 替换 Windows 不允许的字符
    return re.sub(r'[\\/*?:"<>|]', '_', filename).strip()

def extract_images(book, output_dir):
    """从 epub 中提取真正的图片文件并保存到 assets 文件夹"""
    assets_dir = os.path.join(output_dir, 'assets')
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    image_map = {} # 原路径 -> 提取后的相对路径
    # 常见的图片扩展名
    img_exts = ('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp')
    
    for item in book.get_items():
        # ITEM_IMAGE 为 9
        is_image_type = item.get_type() == 9
        has_img_ext = item.get_name().lower().endswith(img_exts)
        
        if is_image_type or has_img_ext:
            name = os.path.basename(item.get_name())
            # 避免重名
            target_path = os.path.join(assets_dir, name)
            content = item.get_content()
            if content:
                with open(target_path, 'wb') as f:
                    f.write(content)
                # 记录映射关系，用于后续 HTML 中的路径替换
                image_map[item.get_name()] = os.path.join('assets', name)
                # 同时也记录不带路径的名字映射，因为 HTML 中可能是相对路径
                image_map[name] = os.path.join('assets', name)
    return image_map

def html_to_md(html_soup, output_path, image_map):
    """将 BeautifulSoup 处理后的 HTML 转换为 Markdown"""
    # 移除不必要的样式和空标签，使 Markdown 更简洁
    for tag in html_soup.find_all(['span', 'div']):
        # 如果没有重要属性（如 id），则剥离标签保留内容
        if not tag.get('id') and not tag.find('img'):
            tag.unwrap()
    
    # 移除所有 style 属性
    for tag in html_soup.find_all(True):
        if tag.has_attr('style'):
            del tag['style']
        if tag.has_attr('class'):
            del tag['class']

    # 处理图片路径
    for img in html_soup.find_all('img'):
        src = img.get('src', '')
        if not src: continue
        
        src_name = os.path.basename(src)
        if src_name in image_map:
            img['src'] = image_map[src_name]
        else:
            for orig, new in image_map.items():
                if orig in src or src in orig:
                    img['src'] = new
                    break
    
    temp_html = output_path + '.temp.html'
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(str(html_soup))
    
    try:
        # 使用 pandoc 转换为 markdown，禁用原生 div 和 span 以获得更干净的输出
        subprocess.run([
            'pandoc', 
            temp_html, 
            '-f', 'html-native_divs-native_spans', 
            '-t', 'commonmark_x-raw_html', # 使用更标准的 Markdown 并禁用原始 HTML
            '--wrap=none',
            '-o', output_path
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Pandoc 转换失败: {output_path}")
    finally:
        if os.path.exists(temp_html):
            os.remove(temp_html)

def get_content_segment(soup, start_anchor, end_anchor):
    """提取 HTML 中两个锚点之间的内容"""
    if not soup.find('body'):
        return soup
        
    new_soup = BeautifulSoup("<html><body></body></html>", 'html.parser')
    body = new_soup.body
    
    # 定位起始和结束节点
    start_node = None
    if start_anchor:
        start_node = soup.find(id=start_anchor) or soup.find(attrs={"name": start_anchor})
    
    end_node = None
    if end_anchor:
        end_node = soup.find(id=end_anchor) or soup.find(attrs={"name": end_anchor})

    found_start = False if start_node else True
    
    # 递归查找并收集节点
    def collect_nodes(current_soup_node):
        nonlocal found_start
        for child in current_soup_node.children:
            if not found_start:
                if child == start_node or (hasattr(child, 'descendants') and start_node in child.descendants):
                    found_start = True
                    # 如果起始点就在这个节点，我们开始收集
                    if child == start_node:
                        body.append(child.__copy__())
                    else:
                        # 如果起始点在内部，需要递归进去找
                        # 简化处理：直接包含整个父节点（通常是标题）
                        body.append(child.__copy__())
                continue
            
            if end_node and (child == end_node or (hasattr(child, 'descendants') and end_node in child.descendants)):
                # 遇到结束节点，停止
                return False
            
            body.append(child.__copy__())
        return True

    collect_nodes(soup.find('body'))
    return new_soup

def process_toc(book, toc, parent_dir, image_map):
    """递归处理 TOC 并拆分章节"""
    # 预先平坦化 TOC 以便查找“下一个”锚点
    flat_toc = []
    def flatten(entries):
        for entry in entries:
            if isinstance(entry, tuple):
                flat_toc.append(entry[0])
                flatten(entry[1])
            else:
                flat_toc.append(entry)
    flatten(toc)

    def get_entry_info(entry):
        if isinstance(entry, tuple):
            return entry[0].title, entry[0].href, entry[1]
        return entry.title, entry.href, []

    for i, entry in enumerate(flat_toc):
        title, href, _ = get_entry_info(entry)
        
        # 查找当前 entry 的子项（在原始嵌套 TOC 中找）
        # 这里我们换个思路：直接按 flat_toc 顺序处理，但维护目录结构
        pass

    # 重新实现递归逻辑，同时利用 flat_toc 寻找边界
    def process_recursive(entries, current_dir):
        for i, entry in enumerate(entries):
            title, href, sub_entries = get_entry_info(entry)
            clean_title = clean_filename(title)
            
            if '#' in href:
                filename, anchor = href.split('#', 1)
            else:
                filename, anchor = href, None
            
            item = book.get_item_with_href(filename)
            if not item: continue
            
            content = item.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            
            # 确定当前段落的终点
            next_anchor = None
            if sub_entries:
                _, sub_href, _ = get_entry_info(sub_entries[0])
                if '#' in sub_href:
                    sub_file, sub_anchor = sub_href.split('#', 1)
                    if sub_file == filename:
                        next_anchor = sub_anchor
            else:
                # 寻找 flat_toc 中的下一个
                try:
                    curr_idx = -1
                    target_entry = entry if not isinstance(entry, tuple) else entry[0]
                    for idx, e in enumerate(flat_toc):
                        if e == target_entry:
                            curr_idx = idx
                            break
                    
                    if curr_idx != -1 and curr_idx + 1 < len(flat_toc):
                        next_entry = flat_toc[curr_idx + 1]
                        next_href = next_entry.href
                        if '#' in next_href:
                            next_file, next_anchor_val = next_href.split('#', 1)
                            if next_file == filename:
                                next_anchor = next_anchor_val
                except Exception:
                    pass
            
            segment_soup = get_content_segment(soup, anchor, next_anchor)
            
            target_md_path = os.path.join(current_dir, f"{clean_title}.md")
            html_to_md(segment_soup, target_md_path, image_map)
            
            if sub_entries:
                sub_dir = os.path.join(current_dir, clean_title)
                if not os.path.exists(sub_dir):
                    os.makedirs(sub_dir)
                process_recursive(sub_entries, sub_dir)

    process_recursive(toc, parent_dir)

def process_epub(epub_path):
    print(f"正在处理: {epub_path}")
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        print(f"读取失败 {epub_path}: {e}")
        return

    base_name = os.path.splitext(os.path.basename(epub_path))[0]
    output_dir = os.path.join(os.getcwd(), clean_filename(base_name))
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # 提取图片
    image_map = extract_images(book, output_dir)
    
    # 处理目录
    process_toc(book, book.toc, output_dir, image_map)
    print(f"完成: {epub_path}")

if __name__ == "__main__":
    for file in os.listdir('.'):
        if file.endswith('.epub'):
            process_epub(file)
