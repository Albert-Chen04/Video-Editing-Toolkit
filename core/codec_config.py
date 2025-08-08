# core/codec_config.py
"""
视频编码器配置模块
统一管理不同编码器的参数配置
"""

# 编码器参数配置
CODEC_PARAMS = {
    'h264_nvenc': {
        'params': ['-preset', 'p5', '-cq', '18'],
        'description': 'NVIDIA GPU H.264编码器'
    },
    'hevc_nvenc': {
        'params': ['-preset', 'p4', '-cq', '20'],
        'description': 'NVIDIA GPU H.265编码器'
    },
    'libx264': {
        'params': ['-preset', 'medium', '-crf', '18'],
        'description': 'CPU H.264编码器'
    },
    'libx265': {
        'params': ['-preset', 'medium', '-crf', '20'],
        'description': 'CPU H.265编码器'
    },
    'copy': {
        'params': [],
        'description': '无损复制（不重新编码）'
    }
}

# 默认编码参数
DEFAULT_CODEC_PARAMS = ['-preset', 'medium', '-crf', '18']

# 编码器显示名称
CODEC_DISPLAY_NAMES = {
    'h264_nvenc': 'h264_nvenc (N卡)',
    'hevc_nvenc': 'hevc_nvenc (N卡)',
    'libx264': 'libx264 (CPU)',
    'libx265': 'libx265 (CPU)',
    'copy': 'copy (无损复制)'
}

# UI中的编码器选项列表
def get_codec_options_for_ui(include_copy=False, include_h265=True, copy_label="copy (无损复制)"):
    options = []
    
    if include_copy:
        options.append(copy_label)
    
    options.extend([
        "h264_nvenc (N卡)",
        "libx264 (CPU)"
    ])
    
    if include_h265:
        options.insert(-1, "hevc_nvenc (N卡)")  # 插入到CPU前面
        options.append("libx265 (CPU)")
    
    return options

def get_codec_params(codec_name):
    # 从显示名称提取实际编码器名称
    actual_codec = codec_name
    for codec, display_name in CODEC_DISPLAY_NAMES.items():
        if codec in codec_name:
            actual_codec = codec
            break
    
    return CODEC_PARAMS.get(actual_codec, {}).get('params', DEFAULT_CODEC_PARAMS)

def get_actual_codec_name(codec_display_name):
    """提取实际编码器名称"""
    for codec, display_name in CODEC_DISPLAY_NAMES.items():
        if codec in codec_display_name:
            return codec
    return codec_display_name

def build_video_command_with_codec(base_command, codec_name, output_file=None):
    """构建完整的FFmpeg命令"""
    command = base_command.copy()
    
    # copy模式不需要额外编码参数
    if codec_name != 'copy':
        codec_params = get_codec_params(codec_name)
        command.extend(codec_params)
    
    if output_file:
        command.extend(['-y', output_file])
    
    return command
