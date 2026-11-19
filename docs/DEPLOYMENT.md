# Deployment guide

## Docker locally

Copy `.env.example` to `.env`. Leave demo mode enabled initially.

```bash
docker compose up --build
```

Visit http://127.0.0.1:8000. The named volume retains documents and traces. To use Gemini, edit `.env`, add your own key, restart, and re-upload documents into the Gemini collection. Do not commit `.env`.

The Docker image and Compose file have not been executed in the build environment; run this locally before claiming a container deployment.

## Private Google Cloud Run prototype

Deployment is deliberately not automatic. This can incur charges. You need a Google Cloud project with billing, permissions to use Cloud Build/Artifact Registry/Cloud Run, and the appropriate APIs enabled. Follow the official [source deployment prerequisites](https://docs.cloud.google.com/run/docs/deploying-source-code).

1. Provision an external Qdrant instance with TLS and an API key. Local vectors on Cloud Run would be lost on restart. The app rejects production mode without `QDRANT_URL`.
2. Create a dedicated runtime service account. Grant only needed permissions; do not grant project Owner or Editor.
3. Create Secret Manager secrets for the Gemini API key, Qdrant key, and workspace key JSON. Generate long random workspace keys, e.g. with Python's `secrets.token_urlsafe(32)`. JSON format: `{"your-random-key":"rohit-demo"}`. Store the generated value privately, not in Git.
4. Grant the runtime account Secret Accessor on these specific secrets. Consult [Cloud Run secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets).
5. Set `PROJECT_ID`, `SERVICE_ACCOUNT`, `QDRANT_URL`, `GEMINI_SECRET`, `WORKSPACE_SECRET`, and `QDRANT_SECRET` in your shell. The last three values are secret names, not secret contents. `REGION` defaults to `asia-south1`.
6. Review and run `bash scripts/deploy_cloud_run.sh` from the project root. It deploys a private service with a single-instance cap, four concurrent requests and secret injection.
7. Access it through an authenticated local proxy: `gcloud run services proxy fieldkit --project "$PROJECT_ID" --region "$REGION" --port 8080`. Then open http://localhost:8080 and enter your workspace API key. Cloud IAM invoker permission and the application API key are separate controls.
8. Upload sample files, run positive and negative queries, inspect Cloud Logging, restart the service and confirm vector persistence. Record these results before claiming deployment.

Cloud Run tracing history in SQLite is temporary. JSON metrics go to stdout and can be captured by Cloud Logging. Set log-retention and access policies for your environment. There is no durable trace-query API across restarts in this version. A single-instance cap reduces cost/concurrency but does not prevent transient overlap during revisions.

This design uses Gemini Developer API from a Cloud Run container. It does not implement Vertex AI/enterprise ADC authentication. No Google Cloud resources were created during project generation.

## Live acceptance checklist

- Upload each supported format; test a corrupted and oversized document.
- Verify a real Gemini answer against its exact source and citation.
- Try unanswerable questions and malicious instructions inside a document.
- Create two workspaces and confirm cross-workspace reads, deletes and trace lookup fail.
- Confirm model usage fields and configure current pricing before quoting costs.
- Measure a representative held-out evaluation set, with answer correctness and retrieval recall annotated by a human.
- Record model IDs, versions, environment, cost and commit in your results.
