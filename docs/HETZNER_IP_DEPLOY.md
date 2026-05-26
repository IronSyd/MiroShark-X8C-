# Hetzner IP-Only Deployment

This deployment runs MiroShark on one Hetzner Cloud VM and exposes only Caddy on port `80`. Caddy applies shared Basic Auth before serving the frontend or proxying backend routes. Backend, frontend, and Neo4j are private Docker-network services.

## Prerequisites

- Hetzner Cloud VM in Germany/EU.
- Ubuntu 24.04 LTS or Debian 12.
- Docker Engine and Docker Compose plugin installed.
- A private X8C repo/fork containing the customized `local/cloud-preset-settings` branch.
- One OpenRouter API key for the Cloud preset slots.

Do not use the upstream `ghcr.io/aaronjmars/miroshark:latest` image for this deployment; it will not include the X8C customizations.

## Server Setup

Clone the private X8C repo on the server, then enter the deployment folder:

```bash
git clone <private-x8c-miroshark-repo-url> /opt/miroshark
cd /opt/miroshark/deploy/hetzner
cp .env.example .env
```

Generate a strong shared password and Caddy hash:

```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'replace-with-strong-password'
```

Edit `.env`:

- set `PUBLIC_BASE_URL=http://<hetzner-ip>`;
- set `BASIC_AUTH_USER`;
- paste the generated hash into `BASIC_AUTH_HASH`;
- set `SECRET_KEY`, `MIROSHARK_ADMIN_TOKEN`, and `NEO4J_PASSWORD`;
- paste the OpenRouter key into every `*-API_KEY` slot in the Cloud preset block.

Keep `.env` on the server only.

## Start

```bash
docker compose up -d --build
docker compose ps
```

Verify from the server:

```bash
curl -i http://127.0.0.1/health
curl -u miroshark:replace-with-strong-password http://127.0.0.1/health
```

The first request should return `401 Unauthorized`; the authenticated request should return the MiroShark health payload.

## Hetzner Firewall

Expose only:

- `80/tcp` for Caddy and Basic Auth.
- `22/tcp` for SSH, preferably restricted to administrator IPs.

Do not expose:

- `3000/tcp`;
- `5001/tcp`;
- `7474/tcp`;
- `7687/tcp`;
- `11434/tcp`.

This production profile does not run Ollama.

## Team Smoke Test

Open `http://<hetzner-ip>` in a browser. Confirm:

- Basic Auth prompt appears;
- app loads after login;
- Settings shows the Cloud preset;
- Test Connection succeeds;
- a small document/graph ingest works;
- a tiny simulation can run;
- a report can be generated and exported.

## Updates

From `/opt/miroshark`:

```bash
git fetch --all --prune
git pull --ff-only
cd deploy/hetzner
docker compose up -d --build
```

Before pulling upstream MiroShark updates into the private repo, preserve and re-test the X8C customizations: Cloud preset, settings persistence, empty LLM response handling, responsive workbench, chat focus mode, and report export controls.

## Backups

Enable Hetzner server backups for the VM. The deployment stores durable data in Docker named volumes:

- `miroshark_neo4j_data`;
- `miroshark_uploads_data`;
- `miroshark_backend_logs`;
- Caddy state volumes.

For a clean manual snapshot before risky updates:

```bash
cd /opt/miroshark/deploy/hetzner
docker compose stop backend caddy web
# take Hetzner snapshot from the Cloud Console
docker compose up -d
```

## Security Notes

Basic Auth over plain HTTP is a pilot-grade gate, not strong transport security. Credentials can be intercepted on untrusted networks. Rotate the shared password regularly, restrict SSH tightly, and move to HTTPS, per-user auth, or IP allowlisting before client-facing use.
