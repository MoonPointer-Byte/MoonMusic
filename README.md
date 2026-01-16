# 🌙 MoonMusic  (Project Moon)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flet](https://img.shields.io/badge/Flet-UI-purple)
![License](https://img.shields.io/badge/License-MIT-green)

**MoonMusic** 是一个基于 Python + Flet 构建的跨平台聚合媒体播放器。它集成了全网音乐搜索与播放、高清图片检索以及社交媒体用户搜索功能，拥有现代化的 Dark Mode UI 和流畅的交互体验。

## ✨ 功能特性 (Features)

*   **🎵 聚合音乐播放**
    *   支持 **网易云音乐**、**QQ音乐**、**酷狗音乐** 三大平台聚合搜索。
    *   支持 VIP 歌曲 Cookie 配置（需自行获取）。
    *   内置音频播放器：支持播放、暂停、进度条拖动、自动连播。
    *   支持 `.mp3` / `.m4a` 格式自动下载与缓存。
    *   本地播放列表管理、收藏夹与历史记录。

*   **🖼️ 沉浸式搜图**
    *   基于 Bing 引擎的高清图片搜索（4K壁纸、二次元、头像）。
    *   瀑布流网格布局，支持大图预览。
    *   一键下载图片到本地。

*   **🔍 社交聚合搜索**
    *   聚合 **Bilibili**、**微博**、**抖音**、**小红书** 用户搜索。
    *   一键直达用户主页。
    *   异步并发请求，拒绝界面卡顿。

*   **🎨 现代化 UI**
    *   全暗色模式（Dark Theme）。
    *   响应式布局，平滑的动画过渡效果。
    *   全屏沉浸式播放界面。

## 🛠️ 安装与运行 (Installation)

### 环境要求
*   Python 3.12
*   Windows / macOS / Linux

### 1. 克隆项目
```bash
git clone https://github.com/MoonPointer-Byte/MoonMusic.git
cd MoonMusic
