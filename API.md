# API wiring

Consumes the canonical Mobile-Contracts-SDK contract.

Owns:
- GET /v1/health
- GET,POST /v1/devices
- GET /v1/devices/{device_id}
- POST /v1/devices/{device_id}/commands
- GET,PUT /v1/devices/{device_id}/policies
- GET /v1/audit/events

Calls Device Gateway for dispatch and Mobile Sync for contacts/media jobs. Completion is based on agent result/readback, not dispatch success.