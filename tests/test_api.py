from fastapi.testclient import TestClient
from app.main import app

c=TestClient(app)
def test_flow():
    d=c.post("/v1/devices",json={"platform":"android","enrollment_id":"e1"}); assert d.status_code==201
    did=d.json()["id"]
    q=c.post(f"/v1/devices/{did}/commands",headers={"x-actor":"test"},json={"type":"collect_inventory","idempotency_key":"k1","payload":{}})
    assert q.status_code==202
    cmd=q.json()["id"]
    assert len(c.get(f"/v1/devices/{did}/commands").json()["items"])==1
    assert c.post(f"/v1/devices/{did}/commands/{cmd}/result",json={"status":"succeeded"}).status_code==202
    assert c.get("/v1/audit/events").json()["items"]

def test_browser_cors_preflight():
    r=c.options("/v1/devices",headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"GET"})
    assert r.status_code==200
    assert r.headers["access-control-allow-origin"]=="http://localhost:5173"

def test_idempotent_command():
    d=c.post("/v1/devices",json={"platform":"android","enrollment_id":"e2"}).json()
    body={"type":"collect_inventory","idempotency_key":"same","payload":{}}
    a=c.post(f"/v1/devices/{d['id']}/commands",json=body).json()
    b=c.post(f"/v1/devices/{d['id']}/commands",json=body).json()
    assert a["id"]==b["id"]
