# Persistence authority
Control Server owns durable device, command, policy, idempotency, and audit state.
Local development uses SQLite through the repository adapter. Production authority is PostgreSQL and will use DATABASE_URL.
Invariants: unique device enrollment IDs; unique device/idempotency keys; restart-safe command state; append-only audit intent; terminal status comes from device readback.