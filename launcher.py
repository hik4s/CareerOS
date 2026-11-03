"""Native desktop entry point (also used by PyInstaller)."""
from app.desktop import main

if __name__ == '__main__':
    raise SystemExit(main())
