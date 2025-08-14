# -*- mode: python ; coding: utf-8 -*-
import os

# 定义 site-packages 路径
site_packages_path = os.path.join(os.getcwd(), 'python_portable', 'Lib', 'site-packages')

# 分析阶段：指定脚本和依赖项
a = Analysis(
    ['main.py'],
    pathex=[site_packages_path],
    binaries=[],
    datas=[
        ('dependencies', 'dependencies'),
        ('assets', 'assets'),
        (os.path.join(site_packages_path, 'opencc'), 'opencc'),
        (os.path.join(site_packages_path, 'whisper', 'assets'), 'whisper/assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 解决 'torch.distributed' 未找到的问题
    excludes=[],
)

pyz = PYZ(a.pure, a.zipped_data)

# EXE 创建阶段：只包含脚本和 PYZ，不直接捆绑数据文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True, # 在 EXE 中排除二进制文件，它们将由 COLLECT 处理
    name='VideoEditingToolkit-v1.1.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # 发布时建议将 console 设置为 False
    console=True, 
    runtime_tmpdir=None,
    icon='assets\\favicon1.ico',
)

# COLLECT 阶段：创建最终的输出文件夹
# 这是实现“文件夹模式”的关键步骤
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    # 关键：保留对CUDA二进制文件的排除，以减小体积
    upx_exclude=[
        'cudnn*',
        'cublas*',
        'nvrtc*',
        'cufft*',
    ],
    # 指定输出文件夹的名称
    name='VideoEditingToolkit-v1.1.1'
)