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

def extract_images(book):
    """从 epub 中获取所有图片项并返回名称到内容的映射"""
    image_data = {}
    img_exts = ('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp')
    
    for item in book.get_items():
        is_image_type = item.get_type() == 9
        name = item.get_name()
        has_img_ext = name.lower().endswith(img_exts)
        
        if is_image_type or has_img_ext:
            content = item.get_content()
            if content:
                base_name = os.path.basename(name)
                image_data[base_name] = content
                image_data[name] = content
    return image_data

def html_to_md(html_soup, output_path, image_data_map):
    """清理 HTML 并将图片保存到本地 assets 文件夹"""
    # 彻底清理所有不必要的标签属性，防止 Pandoc 产生 artifacts (如 {cfi="..."})
    # 只保留 img 的 src 属性
    for tag in html_soup.find_all(True):
        if tag.name == 'img':
            # 只保留 src，移除 cfi, data-cfi, id, class 等
            src = tag.get('src', '')
            tag.attrs = {'src': src}
        else:
            # 移除所有属性
            tag.attrs = {}
            
    # 如果是 span 或 div，尽量剥离
    for tag in html_soup.find_all(['span', 'div']):
        if not tag.find('img'):
            tag.unwrap()

    # 处理图片本地化存储
    current_dir = os.path.dirname(output_path)
    local_assets_dir = os.path.join(current_dir, 'assets')
    
    found_images = html_soup.find_all('img')
    if found_images and not os.path.exists(local_assets_dir):
        os.makedirs(local_assets_dir)

    for img in found_images:
        src = img.get('src', '')
        if not src: continue
        
        src_name = os.path.basename(src)
        if src_name in image_data_map:
            # 将图片写入当前层级的 assets 文件夹
            target_img_path = os.path.join(local_assets_dir, src_name)
            if not os.path.exists(target_img_path):
                with open(target_img_path, 'wb') as f:
                    f.write(image_data_map[src_name])
            
            # 设置 Markdown 链接指向本地 assets
            img['src'] = f"assets/{src_name}"
    
    temp_html = output_path + '.temp.html'
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(str(html_soup))
    
    try:
        # 使用 gfm 格式，它比较纯净，不会带 Pandoc 自定义的属性
        subprocess.run([
            'pandoc', 
            temp_html, 
            '-f', 'html', 
            '-t', 'gfm', 
            '--wrap=none',
            '-o', output_path
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError:
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

def process_toc(book, toc, parent_dir, image_data_map):
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
            html_to_md(segment_soup, target_md_path, image_data_map)
            
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
    
    # 获取所有图片数据
    image_data_map = extract_images(book)
    
    # 处理目录
    process_toc(book, book.toc, output_dir, image_data_map)
    print(f"完成: {epub_path}")

if __name__ == "__main__":
    for file in os.listdir('.'):
        if file.endswith('.epub'):
            process_epub(file)
