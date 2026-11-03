"""Application paths; desktop data is independent of the working directory."""
import os
import sys
from pathlib import Path

APP_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
DESKTOP = getattr(sys, 'frozen', False) or os.getenv('CAREER_OS_DESKTOP') == '1'
DATA_ROOT = (Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'CareerOS'
             if DESKTOP else Path('./data').resolve())
DATA_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv('CAREER_OS_DB', str(DATA_ROOT / 'career_os.db'))).resolve()
UPLOAD_DIR = Path(os.getenv('CAREER_OS_UPLOAD_DIR', str(DATA_ROOT / 'uploads'))).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_PDF_BYTES = int(os.getenv('MAX_PDF_BYTES', '5242880'))
