import os,tempfile
db=tempfile.NamedTemporaryFile(suffix=".db",delete=False);db.close()
os.environ["DATABASE_URL"]="sqlite:///"+db.name
from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def test_durable_flow_and_idempotency():
    d=c.post("/v1/devices",json={"platform":"android","enrollment_id":"durable-e1"});assert d.status_code==201
    did=d.json()["id"];body={"type":"collect_inventory","idempotency_key":"k1","payload":{"scope":"basic"}}
    a=c.post(f"/v1/devices/{did}/commands",json=body);b=c.post(f"/v1/devices/{did}/commands",json=body);assert a.json()["id"]==b.json()["id"]
    cid=a.json()["id"];assert c.post(f"/v1/devices/{did}/commands/{cid}/result",json={"status":"succeeded"}).status_code==202
    assert c.put(f"/v1/devices/{did}/policies",json={"revision":"r1","managed_apps":[]}).status_code==200
    assert c.get(f"/v1/devices/{did}/policies").json()["revision"]=="r1";assert c.get("/v1/audit/events").json()["items"]
def test_enrollment_is_idempotent():
    body={"platform":"android","enrollment_id":"same-enrollment"}
    assert c.post("/v1/devices",json=body).json()["id"]==c.post("/v1/devices",json=body).json()["id"]
def test_browser_cors_preflight():
    r=c.options("/v1/devices",headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"GET"});assert r.status_code==200