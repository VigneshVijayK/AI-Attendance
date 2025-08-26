# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
	['app_launcher.py'],
	pathex=[],
	binaries=[],
	datas=[('data', 'data'), ('README.md', '.'), ('requirements.txt', '.')],
	hiddenimports=[],
	hookspath=[],
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
	name='AI-Attendance',
	debug=False,
	bootloader_ignore_signals=False,
	strip=False,
	upx=True,
	console=False,
	disable_windowed_traceback=False,
	target_arch=None,
	codesign_identity=None,
	entitlements_file=None,
)


