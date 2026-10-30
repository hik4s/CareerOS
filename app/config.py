import os,sys
from pathlib import Path
if getattr(sys,'frozen',False):
 DATA_ROOT=Path(os.getenv('LOCALAPPDATA',Path.home()))/'CareerOS'
else:DATA_ROOT=Path('./data')
DATA_ROOT.mkdir(parents=True,exist_ok=True)
DB_PATH=Path(os.getenv('CAREER_OS_DB',str(DATA_ROOT/'career_os.db')))
UPLOAD_DIR=Path(os.getenv('CAREER_OS_UPLOAD_DIR',str(DATA_ROOT/'uploads')));UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
MAX_PDF_BYTES=int(os.getenv('MAX_PDF_BYTES','5242880'))
