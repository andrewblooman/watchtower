# ECS / Fargate migration (design-ready notes)

Target: run the same 3 containers on ECS/Fargate with Postgres on RDS.

## Services

1. **UI service**
   - Public behind an ALB (listener `:80`/`:443`)
   - Container exposes `3000`
   - Env: `NEXT_PUBLIC_API_BASE` points at the API ALB path (or separate host)

2. **API service**
   - Private (no public IP), reachable from ALB via internal target group + listener rule (e.g. `/api/*`)
   - Container exposes `8000`
   - Env: `DATABASE_URL` points to RDS Postgres
   - Secrets: `INGEST_API_KEY`, DB creds via Secrets Manager
   - Logs: CloudWatch Logs

3. **Agent service**
   - Private (no ingress)
   - Runs as a long-lived service (or scheduled tasks later)
   - Env: `API_BASE` points to internal API address, `INGEST_API_KEY` from Secrets Manager

## Storage

- Replace the local artifacts volume with S3:
  - `artifacts.path_or_url` becomes an S3 URL
  - Agent uploads artifacts; API only stores metadata and optionally proxies downloads

## Observability

- CloudWatch Logs for `ui`, `api`, `agent`
- ALB access logs (optional)
- Add health checks (`/healthz`) to API target group

