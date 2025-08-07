# build.spec

# -*- mode: python ; coding: utf-8 -*-

# 在文件的最顶端导入os模块，这是最佳实践
import os

# 这个 block_cipher 是标准模板，我们不需要动它
block_cipher = None


# 【核心部分】这里定义了我们的应用程序
a = Analysis(
    ['main.py'],  # 我们的主入口脚本
    pathex=[],
    binaries=[],
    datas=[
        # 这是最关键的部分：告诉PyInstaller需要包含哪些非代码文件
        # 格式是 ('源文件或文件夹路径', '打包后在exe根目录下的目标文件夹名')
        ('dependencies/ffmpeg.exe', '.'),        # 将ffmpeg.exe放到根目录
        ('dependencies/ffprobe.exe', '.'),       # 将ffprobe.exe放到根目录
        ('assets', 'assets')                     # 将整个assets文件夹包含进去
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# pyz是Python库的压缩包，我们用默认设置
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# exe是可执行文件的设置
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pocket 48 Video Editing Toolkit',  # 这是我们最终exe文件的名字
    debug=False,
    strip=False,
    upx=True,  # 启用UPX压缩
    console=False, # 设置为窗口程序，不显示命令行
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # 【核心修正】使用 os.path.join 来构建图标路径，确保路径正确无误
    icon=os.path.join('assets', 'favicon1.ico')
)

# coll是将所有文件收集到一个文件夹的设置，我们用默认设置
coll = COLLECT(
    exe,
    a.binaries,
a.zipfiles,
    a.datas,
    strip=False,
    upx=True,  # 启用UPX压缩
    upx_exclude=[],
    name='Pocket 48 Video Editing Toolkit' # 这是最终生成的文件夹的名字
)