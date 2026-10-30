import os,sys,time,threading,webbrowser,socket
from pathlib import Path
def base():return Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
os.chdir(base())
from app.main import app
import uvicorn
def available(port):
 with socket.socket() as s:return s.connect_ex(('127.0.0.1',port))!=0
def open_ui():time.sleep(1.2);webbrowser.open('http://127.0.0.1:8765')
if __name__=='__main__':
 threading.Thread(target=open_ui,daemon=True).start();uvicorn.run(app,host='127.0.0.1',port=8765,log_level='warning')
