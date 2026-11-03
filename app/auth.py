from __future__ import annotations
import os
from dataclasses import dataclass
from fastapi import Header,HTTPException,Depends
import jwt
from jwt import PyJWKClient
ISSUER=os.getenv("OIDC_ISSUER","");AUDIENCE=os.getenv("OIDC_AUDIENCE","mobile-control");AUTH_DISABLED=os.getenv("AUTH_DISABLED","false").lower()=="true"
@dataclass(frozen=True)
class Principal:
    subject:str;roles:set[str];kind:str
def _roles(c:dict)->set[str]:
    out=set(c.get("realm_access",{}).get("roles",[]));out.update(c.get("roles",[]));return out
def principal(authorization:str|None=Header(None))->Principal:
    if AUTH_DISABLED:return Principal("dev",{"admin","operator","viewer","device-agent"},"human")
    if not authorization or not authorization.startswith("Bearer "):raise HTTPException(401,"bearer token required")
    if not ISSUER:raise HTTPException(503,"OIDC issuer not configured")
    try:
        token=authorization[7:];key=PyJWKClient(ISSUER.rstrip("/")+"/protocol/openid-connect/certs").get_signing_key_from_jwt(token)
        c=jwt.decode(token,key.key,algorithms=["RS256"],audience=AUDIENCE,issuer=ISSUER)
    except Exception:raise HTTPException(401,"invalid token")
    return Principal(c["sub"],_roles(c),c.get("identity_kind","human"))
def require(*allowed:str):
    def dep(p:Principal=Depends(principal)):
        if not p.roles.intersection(allowed):raise HTTPException(403,"insufficient role")
        return p
    return dep