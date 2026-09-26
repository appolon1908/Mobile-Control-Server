from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Codestra Mobile Control Server", version="0.1.0")
devices: dict[str, dict[str, Any]] = {}
commands: dict[str, list[dict[str, Any]]] = {}
policies: dict[str, dict[str, Any]] = {}
audit: list[dict[str, Any]] = []

class Registration(BaseModel):
    platform: str = "android"
    enrollment_id: str
    model: str | None = None
    os_version: str | None = None

class CommandRequest(BaseModel):
    type: str
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any] = {}

class Result(BaseModel):
    status: str
    error_code: str | None = None
    detail: str | None = None

def event(action: str, resource: str, actor: str = "system") -> None:
    audit.append({"id": str(uuid4()), "action": action, "resource": resource, "actor": actor,
                  "timestamp": datetime.now(timezone.utc).isoformat()})

@app.get("/v1/health")
def health(): return {"status": "ok"}

@app.get("/v1/devices")
def list_devices(): return {"items": list(devices.values())}

@app.post("/v1/devices", status_code=201)
def register_device(body: Registration):
    device_id = str(uuid4())
    d = {"id": device_id, **body.model_dump(), "status": "active"}
    devices[device_id] = d; commands[device_id] = []
    event("device.registered", device_id)
    return d

@app.get("/v1/devices/{device_id}")
def get_device(device_id: str):
    if device_id not in devices: raise HTTPException(404, "device not found")
    return devices[device_id]

@app.post("/v1/devices/{device_id}/heartbeat", status_code=202)
def heartbeat(device_id: str, body: dict[str, Any]):
    if device_id not in devices: raise HTTPException(404, "device not found")
    devices[device_id]["last_seen"] = body.get("timestamp")
    return {"accepted": True}

@app.get("/v1/devices/{device_id}/commands")
def poll_commands(device_id: str):
    if device_id not in devices: raise HTTPException(404, "device not found")
    return {"items": [x for x in commands[device_id] if x["status"] == "queued"]}

@app.post("/v1/devices/{device_id}/commands", status_code=202)
def create_command(device_id: str, body: CommandRequest, x_actor: str = Header("unknown")):
    if device_id not in devices: raise HTTPException(404, "device not found")
    for c in commands[device_id]:
        if c["idempotency_key"] == body.idempotency_key: return c
    c = {"id": str(uuid4()), **body.model_dump(), "status": "queued"}
    commands[device_id].append(c); event("command.queued", c["id"], x_actor)
    return c

@app.post("/v1/devices/{device_id}/commands/{command_id}/result", status_code=202)
def command_result(device_id: str, command_id: str, body: Result):
    for c in commands.get(device_id, []):
        if c["id"] == command_id:
            c["status"] = body.status; c["result"] = body.model_dump()
            event("command.result", command_id); return {"accepted": True}
    raise HTTPException(404, "command not found")

@app.get("/v1/devices/{device_id}/policies")
def get_policy(device_id: str): return policies.get(device_id, {"revision": "none"})

@app.put("/v1/devices/{device_id}/policies")
def set_policy(device_id: str, body: dict[str, Any], x_actor: str = Header("unknown")):
    if device_id not in devices: raise HTTPException(404, "device not found")
    if "revision" not in body: raise HTTPException(422, "revision required")
    policies[device_id] = body; event("policy.updated", device_id, x_actor); return body

@app.post("/v1/devices/{device_id}/sync/contacts", status_code=202)
def sync_contacts(device_id: str): return create_command(device_id, CommandRequest(type="sync_contacts", idempotency_key=str(uuid4())))

@app.post("/v1/devices/{device_id}/sync/media", status_code=202)
def sync_media(device_id: str): return create_command(device_id, CommandRequest(type="sync_media", idempotency_key=str(uuid4())))

@app.get("/v1/audit/events")
def audit_events(): return {"items": audit}
