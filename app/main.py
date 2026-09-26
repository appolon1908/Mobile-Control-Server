from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from uuid import uuid4
from fastapi import FastAPI,Header,HTTPException,Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from .db import connect,dumps,init_db,loads,rowdict
from .auth import Principal,require
app=FastAPI(title="Codestra Mobile Control Server",version="0.2.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_credentials=False,allow_methods=["GET","POST","PUT","OPTIONS"],allow_headers=["Authorization","Content-Type","X-Actor"])
init_db()
class Registration(BaseModel):
    platform:str="android";enrollment_id:str;model:str|None=None;os_version:str|None=None
class CommandRequest(BaseModel):
    type:str;idempotency_key:str=Field(min_length=1);payload:dict[str,Any]={}
class Result(BaseModel):
    status:str;error_code:str|None=None;detail:str|None=None
def now():return datetime.now(timezone.utc).isoformat()
def event(action:str,resource:str,actor:str="system"):
    with connect() as c:c.execute("INSERT INTO audit_events VALUES(?,?,?,?,?)",(str(uuid4()),action,resource,actor,now()))
@app.get("/v1/health")
def health():return {"status":"ok","persistence":"durable"}
@app.get("/v1/devices")
def list_devices(p:Principal=Depends(require("viewer","operator","admin"))):
    with connect() as c:return {"items":[rowdict(x) for x in c.execute("SELECT * FROM devices ORDER BY id")]}
@app.post("/v1/devices",status_code=201)
def register_device(body:Registration,p:Principal=Depends(require("device-agent","admin"))):
    did=str(uuid4())
    try:
        with connect() as c:c.execute("INSERT INTO devices(id,platform,enrollment_id,model,os_version,status) VALUES(?,?,?,?,?,?)",(did,body.platform,body.enrollment_id,body.model,body.os_version,"active"))
    except Exception as e:
        if "UNIQUE" in str(e):
            with connect() as c:return rowdict(c.execute("SELECT * FROM devices WHERE enrollment_id=?",(body.enrollment_id,)).fetchone())
        raise
    event("device.registered",did);return get_device(did,p)
@app.get("/v1/devices/{device_id}")
def get_device(device_id:str,p:Principal=Depends(require("viewer","operator","admin","device-agent"))):
    with connect() as c:r=rowdict(c.execute("SELECT * FROM devices WHERE id=?",(device_id,)).fetchone())
    if not r:raise HTTPException(404,"device not found")
    return r
@app.post("/v1/devices/{device_id}/heartbeat",status_code=202)
def heartbeat(device_id:str,body:dict[str,Any],p:Principal=Depends(require("device-agent","admin"))):
    get_device(device_id,p)
    with connect() as c:c.execute("UPDATE devices SET last_seen=? WHERE id=?",(body.get("timestamp"),device_id))
    return {"accepted":True}
def cmd(r):
    d=rowdict(r)
    if not d:return None
    d["payload"]=loads(d["payload"]) or {};d["result"]=loads(d["result"]);return d
@app.get("/v1/devices/{device_id}/commands")
def poll_commands(device_id:str,p:Principal=Depends(require("device-agent","operator","admin"))):
    get_device(device_id,p)
    with connect() as c:return {"items":[cmd(x) for x in c.execute("SELECT * FROM commands WHERE device_id=? AND status='queued' ORDER BY created_at",(device_id,))]}
@app.post("/v1/devices/{device_id}/commands",status_code=202)
def create_command(device_id:str,body:CommandRequest,p:Principal=Depends(require("operator","admin")),x_actor:str=Header("unknown")):
    get_device(device_id,p)
    with connect() as c:
        old=c.execute("SELECT * FROM commands WHERE device_id=? AND idempotency_key=?",(device_id,body.idempotency_key)).fetchone()
        if old:return cmd(old)
        cid=str(uuid4());c.execute("INSERT INTO commands VALUES(?,?,?,?,?,?,?,?)",(cid,device_id,body.type,body.idempotency_key,dumps(body.payload),"queued",None,now()))
        out=cmd(c.execute("SELECT * FROM commands WHERE id=?",(cid,)).fetchone())
    event("command.queued",cid,x_actor);return out
@app.post("/v1/devices/{device_id}/commands/{command_id}/result",status_code=202)
def command_result(device_id:str,command_id:str,body:Result,p:Principal=Depends(require("device-agent","admin"))):
    with connect() as c:
        if not c.execute("SELECT id FROM commands WHERE id=? AND device_id=?",(command_id,device_id)).fetchone():raise HTTPException(404,"command not found")
        c.execute("UPDATE commands SET status=?,result=? WHERE id=?",(body.status,dumps(body.model_dump()),command_id))
    event("command.result",command_id);return {"accepted":True}
@app.get("/v1/devices/{device_id}/policies")
def get_policy(device_id:str,p:Principal=Depends(require("viewer","operator","admin","device-agent"))):
    get_device(device_id,p)
    with connect() as c:r=c.execute("SELECT body FROM policies WHERE device_id=?",(device_id,)).fetchone()
    return loads(r["body"]) if r else {"revision":"none"}
@app.put("/v1/devices/{device_id}/policies")
def set_policy(device_id:str,body:dict[str,Any],p:Principal=Depends(require("admin")),x_actor:str=Header("unknown")):
    get_device(device_id,p)
    if "revision" not in body:raise HTTPException(422,"revision required")
    with connect() as c:c.execute("INSERT INTO policies(device_id,body) VALUES(?,?) ON CONFLICT(device_id) DO UPDATE SET body=excluded.body",(device_id,dumps(body)))
    event("policy.updated",device_id,x_actor);return body
@app.post("/v1/devices/{device_id}/sync/contacts",status_code=202)
def sync_contacts(device_id:str,p:Principal=Depends(require("operator","admin"))):return create_command(device_id,CommandRequest(type="sync_contacts",idempotency_key=str(uuid4())),p)
@app.post("/v1/devices/{device_id}/sync/media",status_code=202)
def sync_media(device_id:str,p:Principal=Depends(require("operator","admin"))):return create_command(device_id,CommandRequest(type="sync_media",idempotency_key=str(uuid4())),p)
@app.get("/v1/audit/events")
def audit_events(p:Principal=Depends(require("viewer","admin"))):
    with connect() as c:return {"items":[rowdict(x) for x in c.execute("SELECT * FROM audit_events ORDER BY timestamp DESC")]}