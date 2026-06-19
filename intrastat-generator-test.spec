# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\intrastat_generator\\__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[('Słowniki', 'Słowniki'), ('Taryfa', 'Taryfa'), ('Icon', 'Icon')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='intrastat-generator-test',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='build\\version_info.txt',
    icon='Icon\\icon.ico',
)
