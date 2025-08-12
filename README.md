# Video Editing Toolkit v1.1.1

<p align="center">
  <img src="assets/favicon1.ico" width="128" alt="App Icon">
</p>
<h1 align="center">Video Editing Toolkit</h1>
<p align="center">
  一个基于 Python 和 PySide6 构建的桌面视频处理工具箱，集成了 FFmpeg 和 OpenAI-Whisper，旨在为视频创作者提供一系列简单、高效的自动化处理功能。
</p>
<p align="center">
  A desktop video processing toolkit built with Python and PySide6, integrating FFmpeg and OpenAI-Whisper. It aims to provide video creators with a suite of simple and efficient automated processing tools.
</p>

## ✨ 功能展示 (Features Showcase)

| 功能 (Function) | 效果预览 (Preview) |
| :--- | :--- |
| **语音转文本** | <img src="assets/语音转文本.png" width="400"> |
| **竖屏画布字幕** | <img src="assets/竖屏字幕视频制作.png" width="400"> |
| **横屏字幕 & 静帧导出** | <img src="assets/横屏字幕视频与静帧导出(视频播放).png" width="400"> |
| **Chatbox弹幕效果** | <img src="assets/口袋48录播chatbox弹幕视频制作.png" width="400"> |
| **批量裁剪** | <img src="assets/批量裁剪.png" width="400"> |
| **程序主界面** | <img src="assets/screenshot.png" width="400"> |

## 🌟 主要功能详解 (Feature Details)

- **语音转文本 (Speech-to-Text)**
  - 使用 **OpenAI-Whisper** 模型将视频或音频文件高精度地转换为带时间戳的文本。
  - 支持 GPU (CUDA) 加速，大幅提升处理速度。
  - 智能简繁转换，确保输出为统一的简体中文。
  - 支持多格式导出 (`.lrc`, `.srt`, `.vtt`, `.txt`)。
  - 智能字幕切分，确保每行字幕长度和显示时间适中，提升阅读体验。

- **字幕视频合成 (Subtitle Video Synthesis)**
  - **竖屏画布字幕**: 为竖屏视频添加右侧画布，并将字幕精确居中显示。
  - **横屏字幕**: 为传统横屏视频在底部添加居中字幕。
  - **Chatbox弹幕**: 将从48系工具下载的LRC格式弹幕文件，转换为类似直播聊天框的滚动字幕效果。
  - **格式兼容**: 支持导入由“语音转文本”功能生成的四种字幕文件。

- **批量处理工具 (Batch Processing Tools)**
  - **批量裁剪**: 根据时间码列表，从一个源视频中无损或转码裁剪出多个片段。
  - **批量转码**: 批量转换视频格式或从视频中提取音轨。
  - **合并媒体**: 以无损方式快速合并多个视频或音频文件。

- **实用小工具 (Utilities)**
  - **静帧导出**: 内置视频播放器，可逐帧预览并导出任意一帧为高质量图片。对于直播流文件（如.ts, .flv），逐帧功能可能受限于关键帧，建议使用.mp4以获得最佳体验。
  - **视频换背景**: 使用一张静态图片作为背景，与音频文件合成为一个新的视频。

## 🛠️ 技术栈 (Tech Stack)

- **核心框架**: Python 3.12
- **图形界面**: PySide6
- **音视频处理核心**: FFmpeg
- **语音识别**: OpenAI-Whisper
- **简繁转换**: OpenCC
- **打包工具**: PyInstaller

## 🚀 运行与开发 (Usage & Development)

### 1. 搭建开发环境 (推荐使用 Conda 或 venv)

如果您熟悉Python虚拟环境，这是参与开发的标准方式。

#### a. 创建并激活虚拟环境

```bash
# 使用 Conda (推荐)
conda create -n toolkit-env python=3.12
conda activate toolkit-env

# 或者使用 Python 内置的 venv
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate
```

#### b. 安装依赖库

在激活的虚拟环境中，执行以下命令：

```bash
# 1. 安装核心依赖 
   pip install pyside6 openai-whisper opencc-python-reimplemented 


# 2. (可选, 但强烈推荐) 安装PyTorch以启用GPU加速
# requirements.txt 默认安装的是CPU版本。如果您的电脑配备了NVIDIA显卡，
# 请务必执行以下命令来安装GPU版本，这可以极大地加快“语音转文本”的速度。
#
# 请根据您自己的CUDA版本，访问 https://pytorch.org/get-started/locally/ 
# 获取最适合您环境的安装命令。
#
# 例如 (适用于CUDA 11.8):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2. 配置 FFmpeg

本项目依赖 `ffmpeg.exe` 和 `ffprobe.exe` 来处理所有音视频任务。请选择以下任一方式进行配置：

#### 方式 A (项目内配置)

1.  **下载**: 前往 [**BtbN/FFmpeg-Builds**](https://github.com/BtbN/FFmpeg-Builds/releases) 下载预编译好的版本。
2.  **选择文件**: 在下载页面，找到最新的 `ffmpeg-master-latest-win64-gpl.zip` 或类似名称的文件并下载。
3.  **解压**: 解压下载的 `zip` 文件后，进入 `bin` 文件夹。
4.  **放置**: 将 `ffmpeg.exe` 和 `ffprobe.exe` 这两个文件复制出来，粘贴到**本项目根目录下**一个**新建**的 `dependencies` 文件夹中。

#### 方式 B (推荐全局配置)

如果您希望在电脑的任何位置都能使用FFmpeg，可以将其添加到系统环境变量中。

1.  **下载并放置**: 按照上述方式下载并解压FFmpeg，但您可以将 `bin` 文件夹放置在电脑的任意位置（例如 `D:\tools\ffmpeg\bin`）。
2.  **编辑环境变量**:
    *   在Windows搜索框中搜索“环境变量”，并选择“编辑系统环境变量”。
    *   在弹出的“系统属性”窗口中，点击“环境变量...”按钮。
    *   在“系统变量”区域，找到名为 `Path` 的变量，双击它。
    *   在“编辑环境变量”窗口中，点击“新建”，然后将您存放 `ffmpeg.exe` 的文件夹路径（例如 `D:\tools\ffmpeg\bin`）粘贴进去。
    *   一路点击“确定”保存所有更改。
3.  **验证**: 重新打开一个新的命令行窗口(CMD)，输入 `ffmpeg -version` 并回车。如果能看到版本信息，说明配置成功。

### 3. 运行程序

-   **对于开发者**: 确保您的虚拟环境已激活，然后在项目根目录的命令行中运行：
    ```bash
    python main.py
    ```
-   **对于普通用户**: 请直接下载我们打包好的发行版。

### 4. 使用发行版 (For End Users)

如果您不想进行任何环境配置，可以直接下载我们打包好的版本：

1.  前往本仓库的 [**Releases**](https://github.com/Albert-Chen04/Video-Editing-Toolkit/releases) 页面。
2.  下载最新版本的 `.zip` 压缩包。
3.  解压后，双击运行里面的 `VideoEditingToolkit-v1.1.1.exe` 程序即可。

## 🤝 贡献 (Contributing)

欢迎提交问题 (Issues) 或拉取请求 (Pull Requests)！

## 📄 许可证 (License)

本项目采用 [MIT License](LICENSE)。
