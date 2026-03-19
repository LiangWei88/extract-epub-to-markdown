# EPUB to Markdown Chapter Splitter

**English** | [简体中文](./README_zh.md)

A powerful Python script designed to precisely split EPUB ebooks into chapter-organized Markdown files. It maintains the original hierarchical structure, intelligently handles images, and generates exceptionally clean Markdown text. Perfect for knowledge base management, personal note-taking systems (like Obsidian, Logseq, Notion), or ebook remixing.

## ✨ Features

-   **🎯 Precise Chapter Splitting**: Uses HTML anchor technology to split not just major chapters but also nested sub-sections perfectly.
-   **📂 Structured Directory**: Automatically creates folder hierarchies based on the book's Table of Contents (TOC). If a chapter contains sub-sections, it preserves both the chapter's introductory content (.md) and the sub-section folder.
-   **🖼️ Intelligent Image Processing**:
    -   **Localized Storage**: Automatically extracts images into `assets` folders at each level, ensuring Markdown previews never break.
    -   **Adaptive Icon Scaling**: Automatically identifies icons or small images within titles or text lines and scales them to text height (1.2em) for a beautiful layout.
-   **🧹 Clean Output**:
    -   Thoroughly removes redundant HTML attributes (like `id`, `class`, `style`).
    -   **Artifact Elimination**: Effectively resolves common Pandoc conversion issues like leftover `cfi` attributes or ID anchors.
-   **🚀 Batch Processing**: Processes all EPUB files in the current directory with a single command.

## 🛠️ Requirements

Before using this script, ensure you have the following tools installed:

1.  **Python 3.10+**
2.  **Pandoc** (Version 2.0+ recommended for core conversion)
    -   Windows users can install via `choco install pandoc` or from the official website.

### Installation Steps

It is recommended to use a virtual environment to keep your system environment clean:

1.  **Create and Activate Virtual Environment**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 📖 How to Use

1.  Copy the `.epub` files you want to convert into the project root directory (where `epub_to_md.py` is located).
2.  Activate the virtual environment (see "Installation Steps" above).
3.  Run the conversion script in your terminal:
    ```bash
    python epub_to_md.py
    ```
4.  The script will automatically identify all EPUB files and create a separate folder for each book containing the converted Markdown files and images.

## 📁 Output Example

The converted structure looks like this:
```text
My_Book/
├── Chapter_1.md (Contains only the intro content of this chapter)
├── assets/ (Images for this level)
└── Chapter_1/
    ├── Section_1.1.md
    ├── Section_1.2.md
    └── assets/ (Images for sub-sections)
```

## 🌟 Why Choose This Tool?

-   **Note-Taking Friendly**: Generates clearly structured Markdown with image paths perfectly suited for tools like Obsidian.
-   **AI & RAG Optimized**: Extremely clean text output and chapter-split structure make it ideal as a source for AI model training, long-text processing, or RAG (Retrieval-Augmented Generation) knowledge bases.
-   **Boosts Efficient Learning**: Structured Markdown snippets align perfectly with **Incremental Reading**, SuperMemo, or Anki, enhancing knowledge internalization efficiency.
-   **Clean Code**: Single-file script with clear logic, easy to customize for personal needs.
-   **Robust**: Heavily optimized for complex anchor positioning in EPUBs, ensuring no content is missed or duplicated.

---

**If you find this tool helpful, please give it a ⭐️ Star!**
Feel free to submit an Issue or Pull Request to help improve it.
