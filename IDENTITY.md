# Identity and authorization
Production is fail-closed. OIDC_ISSUER points to Keycloak and OIDC_AUDIENCE=mobile-control.
Roles: viewer reads fleet/policy/audit; operator creates normal commands and sync jobs; admin mutates policy/admin actions; device-agent enrolls, heartbeats, polls commands, reports results and reads effective policy.
JWT signature, issuer and audience are verified. AUTH_DISABLED=true is only for isolated tests/development and must never be enabled in production.