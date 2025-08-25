# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('success.wav', '.'),
        ('fail.wav', '.'),
        ('model', 'model'),
        ('function', 'function'),
        ('yolov5','yolov5')
    ],
    hiddenimports=[
        'pandas', 'openpyxl', 'cv2', 'torch', 'PIL', 'pygame', 'tkinter'
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ParkingSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Kích hoạt UPX compression
    upx_exclude=[],  # Không loại trừ gì
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)