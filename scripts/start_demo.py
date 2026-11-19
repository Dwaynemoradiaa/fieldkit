"""Run from the project root: python scripts/start_demo.py"""
import os, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('AI_MODE','demo')
import uvicorn
if __name__=='__main__': uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
