# core/codec_config.py
# 文件作用：统一管理项目中所有 FFmpeg 编码器相关的配置和参数。

# 定义编码器预设的配置字典
# 键 (key): 在UI下拉框中显示的名称
# 值 (value): 传递给 FFmpeg 的命令行参数列表
CODEC_CONFIGS = {
    "N卡 H.264 (高质量)": [
        '-c:v', 'h264_nvenc', 
        '-preset', 'p5', 
        '-cq', '18',
        '-pix_fmt', 'yuv420p' # 确保像素格式兼容性
    ],
    "N卡 HEVC/H.265 (高压缩)": [
        '-c:v', 'hevc_nvenc', 
        '-preset', 'p5', 
        '-cq', '20',
        '-pix_fmt', 'yuv420p'
    ],
    "CPU x264 (高兼容)": [
        '-c:v', 'libx264', 
        '-preset', 'medium', 
        '-crf', '23',
        '-pix_fmt', 'yuv420p'
    ],
    "CPU x264 (速度优先)": [
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '28',
        '-pix_fmt', 'yuv420p'
    ],
    "直接复制 (无损/极速)": [
        '-c:v', 'copy'
    ]
}

def get_encoder_options():
    """
    返回所有可用的编码器选项名称列表，用于填充UI下拉框。
    :return: list of strings
    """
    return list(CODEC_CONFIGS.keys())

def get_codec_params(name):
    """
    根据用户选择的编码器名称，返回对应的FFmpeg参数列表。
    如果名称不存在，则返回一个安全的默认值（CPU x264 高兼容）。
    :param name: str, a key from CODEC_CONFIGS
    :return: list of strings
    """
    return CODEC_CONFIGS.get(name, CODEC_CONFIGS["CPU x264 (高兼容)"])

def get_copy_tooltip():
    """
    返回“直接复制”选项的详细说明文本。
    :return: str
    """
    return (
        "极速模式，不重新编码视频流，无画质损失。\n"
        "适用场景：\n"
        "- 快速裁剪或合并视频。\n"
        "- 仅更换视频容器格式 (如 .mkv -> .mp4)。\n"
        "使用条件：\n"
        "- 合并时，所有视频的编码、分辨率、帧率等需一致。\n"
        "- 转码时，目标容器必须支持源视频的编码格式。\n"
        "- 不能用于添加字幕、画布等需要修改画面的任务。"
    )