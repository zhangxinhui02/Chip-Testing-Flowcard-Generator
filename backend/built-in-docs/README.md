# 内建文档库

这个目录用于存储内建文档，即通用的知识文档。

系统启动时会遍历检查所有内建文档，确保内建文档在用户使用时已经被向量化存储于知识库并可用于用户检索。

## 目录结构说明

```text
built-in-docs/
└── <DOC_TITLE>/
    ├── assets/
    ├── chunks/
    │   ├── 1.md
    │   ├── 2.md
    │   └── 3.md
    ├── target.md
    └── target.pdf
```

- `<DOC_TITLE>/`表示一个文档，即`built-in-docs/`目录下的每一个文件夹都表示一个内建文档，文件夹名称会被读取为系统中的文档名称。
- `target.pdf`表示原文档。在Web面板中可以下载此文件。
- `target.md`表示由`target.pdf`转换得到的Markdown文件。此文件为中间产物，对于系统运行不起实际作用。
- `assets/`为`target.md`对应的图片资源目录。此目录为中间产物，对于系统运行不起实际作用。
- `chunks/`存储`target.md`分块得到的若干`.md`文档内容块。这些块的内容会被遍历读取、由Embedding模型向量化并存储到向量数据库。
