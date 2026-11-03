from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Built-in webview/pythonnet hooks collect native assemblies. Keep only WinForms
# and explicitly collect the JS bridge + lib data used by EdgeChromium/downloads.
hidden = (collect_submodules('uvicorn') + collect_submodules('feedparser') +
          collect_submodules('docx') + ['webview.platforms.winforms',
          'webview.platforms.edgechromium', 'webview.platforms.mshtml', 'clr'])
data = [('app/static', 'app/static'), ('extension', 'extension')]
data += collect_data_files('feedparser') + collect_data_files('webview')
a = Analysis(['launcher.py'], pathex=['.'], binaries=[], datas=data,
             hiddenimports=hidden, hookspath=[], runtime_hooks=[],
             excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'gi', 'cefpython3',
                       'webview.platforms.qt', 'webview.platforms.gtk',
                       'webview.platforms.cocoa', 'webview.platforms.cef'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='CareerOS', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          disable_windowed_traceback=False)
