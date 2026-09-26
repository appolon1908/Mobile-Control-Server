from __future__ import annotations
import json, os, sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any
DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./mobile_control.db")
def _sqlite_path()->str:
    if DATABASE_URL.startswith("sqlite:///"): return DATABASE_URL.removeprefix("sqlite:///")
    raise RuntimeError("Production PostgreSQL adapter not configured")
@contextmanager
def connect():
    p=_sqlite_path()
    if p!=":memory:": Path(p).parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(p);c.row_factory=sqlite3.Row
    try: yield c;c.commit()
    finally:c.close()
def init_db():
    with connect() as c:c.executescript("""
CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,platform TEXT NOT NULL,enrollment_id TEXT NOT NULL UNIQUE,model TEXT,os_version TEXT,status TEXT NOT NULL,last_seen TEXT);
CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,device_id TEXT NOT NULL,type TEXT NOT NULL,idempotency_key TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,result TEXT,created_at TEXT NOT NULL,UNIQUE(device_id,idempotency_key));
CREATE TABLE IF NOT EXISTS policies(device_id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events(id TEXT PRIMARY KEY,action TEXT NOT NULL,resource TEXT NOT NULL,actor TEXT NOT NULL,timestamp TEXT NOT NULL);
""")
def rowdict(r):return dict(r) if r else None
def dumps(v:Any)->str:return json.dumps(v,separators=(",",":"))
def loads(v:str|None)->Any:return json.loads(v) if v else None