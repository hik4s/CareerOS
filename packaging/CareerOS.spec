from PyInstaller.utils.hooks import collect_submodules,collect_data_files
hidden=collect_submodules('uvicorn')+collect_submodules('feedparser')+collect_submodules('docx')
data=[('app/static','app/static'),('extension','extension')]+collect_data_files('feedparser')
a=Analysis(['launcher.py'],pathex=['.'],binaries=[],datas=data,hiddenimports=hidden,hookspath=[],runtime_hooks=[],excludes=[],noarchive=False)
pyz=PYZ(a.pure);exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='CareerOS',debug=False,bootloader_ignore_signals=False,strip=False,upx=True,console=False,disable_windowed_traceback=False)
