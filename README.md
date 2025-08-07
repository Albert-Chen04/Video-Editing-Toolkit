# 口袋48视频剪辑工具箱 (Pocket 48 Video Editing Toolkit)

![Public](https://img.shields.io/badge/Public-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

这是一个使用 Python (PySide6) 和 FFmpeg 构建的桌面应用程序，旨在为口袋48等场景的视频处理提供一个简单易用的图形化界面，将繁琐的命令行操作变得直观、高效。

<!-- 
【请替换这里！】
为了让你的项目更吸引人，请截取一张你软件主界面的图片，
将它拖拽到GitHub仓库的文件列表里上传，然后将下面的图片链接替换成你上传后的链接。
-->
![应用截图](https://raw.githubusercontent.com/Albert-Chen04/Pocket-48-Video-Editing-Toolkit/main/screenshot.png)

---

## 核心功能

*   **媒体转码:**
    *   **视频转码:** 支持将视频转换为 `mp4`, `mkv`, `ts`, `flv` 等多种格式。
    *   **音频提取:** 支持从视频中无损或有损提取 `aac`, `mp3`, `flac`, `wav` 等格式的音频。
    *   **编码器选择:** 支持 `NVIDIA (NVENC)` 硬件加速和 `CPU (libx264)` 软件编码，兼顾速度与质量。

*   **字幕制作:**
    *   **LRC弹幕烧制:** 将 `.lrc` 格式的歌词/弹幕文件，以“聊天框”的形式硬编码（烧制）到视频画面中。
    *   **样式自定义:** 提供丰富的参数选项，如字体、大小、边距、弹幕区高度等。

*   **批量处理:**
    *   **批量转码:** 支持一次性添加多个文件，并以相同的设置进行批量转换或音频提取。
    *   **批量裁剪:** 支持一次性把文件裁剪成多个片段，只需要输入片段名称，开始时间，结束时间。批量裁剪后会把此次批量裁剪的各个片段名称，开始时间，结束时间保存为txt
---

## 快速开始 (给普通用户)

### 下载与安装

1.  前往本项目的 **[Releases 页面](https://github.com/Albert-Chen04/Pocket-48-Video-Editing-Toolkit/releases)**。
2.  下载最新版本下方的 `Pocket-48-Video-Editing-Toolkit-vX.X.X.zip` 压缩包。
3.  解压下载的 `.zip` 文件到你电脑的任意位置。
4.  进入解压后的文件夹，双击运行 **`Pocket 48 Video Editing Toolkit.exe`** 即可使用。

**注意：** 本程序为绿色免安装版，所有需要的文件都已包含在内。

---

## 开发与构建 (给开发者)

### 技术栈

*   **核心语言:** Python 3.12+
*   **图形界面:** PySide6 (Qt for Python)
*   **核心引擎:** FFmpeg

### 开发环境搭建

1.  **克隆仓库**
    ```bash
    git clone https://github.com/Albert-Chen04/Pocket-48-Video-Editing-Toolkit.git
    cd Pocket-48-Video-Editing-Toolkit
    ```

2.  **配置Python环境 (便携版)**
    *   前往 [Python官网](https://www.python.org/downloads/windows/) 下载 **"Windows embeddable package"**。
    *   解压到项目根目录，并重命名为 `python_portable`。
    *   参考项目开发文档，为这个便携版Python安装 `pip`。

3.  **配置FFmpeg**
    *   前往 [FFmpeg官网](https://ffmpeg.org/download.html) 下载。
    *   将解压后 `bin` 目录下的 `ffmpeg.exe` 和 `ffprobe.exe` 复制到本项目的 `dependencies` 文件夹中。

4.  **安装Python依赖**
    ```bash
    .\python_portable\Scripts\pip.exe install -r requirements.txt
    ```

5.  **运行程序 (开发模式)**
    ```bash
    # 直接运行启动脚本即可
    .\run_app.bat
    ```

### 创建 `requirements.txt`

为了方便管理依赖，请在项目根目录创建一个名为 `requirements.txt` 的文件，内容如下：
PySide6  
pyinstaller  
### 打包为 `.exe`

1.  **准备打包工具**
    *   确保已按上述步骤安装了 `pyinstaller`。
    *   下载 `UPX` 并将 `upx.exe` 放置于项目根目录以启用压缩。

2.  **执行打包**
    *   项目已包含一个配置好的 `build.spec` 文件。
    *   运行以下命令：
    ```bash
    .\python_portable\Scripts\pyinstaller.exe build.spec
    ```

3.  **获取成果**
    *   打包完成后，最终的可分发文件夹位于 `dist/Pocket 48 Video Editing Toolkit`。

---

## 未来计划 (To-Do)

*   [ ] 画布弹幕视频制作
*   [ ] 批量视频裁剪
*   [ ] 视频添加静态封面
*   [ ] 导出指定时间点的视频帧图片
*   [ ] UI美化与用户体验优化

## 许可证 (License)

本项目采用 **MIT 许可证**。详情请见 `LICENSE` 文件。
