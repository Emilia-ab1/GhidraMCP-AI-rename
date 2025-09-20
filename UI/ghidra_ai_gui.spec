# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

# 收集证书（用于 HTTPS）
certifi_datas = collect_data_files('certifi')


a = Analysis(
    ['ghidra_ai_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[('res/logo.ico', 'res'), ('res/pay.JPG', 'res')] + certifi_datas,
    hiddenimports=[
        # 仅保留显式需要的 Qt 模块（其余由静态导入自动发现）
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 单文件模式：将 binaries/zipfiles/datas 直接并入 EXE 参数
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Ghidra-AI-Rename-GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='res/logo.ico',
) 