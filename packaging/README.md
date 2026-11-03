# Windows build and release

Use Windows x64, Python 3.12 x64 and Inno Setup 6. From the repository root:

```powershell
python -m venv .buildvenv
.\.buildvenv\Scripts\python.exe -m pip install -r requirements.txt
.\.buildvenv\Scripts\python.exe -m pytest -q
.\.buildvenv\Scripts\python.exe scripts/build_windows.py
```

The builder downloads Microsoft's Evergreen WebView2 bootstrapper if absent,
checks its Authenticode signature even when cached, bundles it, and emits
`installer/CareerOS-Setup-VERSION.exe` plus `.exe.sha256`. Users need internet
only when WebView2 is missing. A failed WebView2 install prevents app installation.
The release installer itself is currently unsigned; the checksum proves file
integrity against the release asset, not publisher identity.

Push a tag matching `app/version.py`, for example `v0.7.0`, to run Windows CI.
CI tests and builds, uploads artifacts, and creates a **draft** GitHub release.
Manually publish only after testing its exact installer assets on Windows:

- Fresh non-admin install with and without WebView2; verify desktop window,
  local API, native downloads, and Start menu extension guide/folder shortcuts.
- Upgrade an existing installation using the in-app updater; verify app exit,
  installer completion, one restarted window, and retained settings/database.
- Install into a custom directory; verify the updater reuses that directory.
- Attempt a downgrade; verify rejection. Try updating while app remains open;
  verify it waits and aborts after 60 seconds without replacing running files.
- Uninstall; verify user data remains in its configured user-data directory.

Installer update protocol: `/SILENT /SUPPRESSMSGBOXES /NORESTART
/CAREEROSUPDATE /DIR="actual application directory"`. The application holds
`Local\CareerOS.Desktop` until shutdown. Setup waits for that mutex to disappear
before replacing files and restarts the app only after successful installation.
Setup's automatic AppMutex prompt is intentionally omitted so it cannot interrupt
this wait during an unattended update.

References:
- https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution
- https://pywebview.flowrl.com/guide/freezing
- https://jrsoftware.org/ishelp/topic_isxfunc_strtoversion.htm
- https://jrsoftware.org/ishelp/topic_isxfunc_comparepackedversion.htm
