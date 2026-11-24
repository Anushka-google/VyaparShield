# Workers Module — Asynchronous Task Processing

## Status: Planned / Deferred

Currently, all document parsing, OCR extraction, and financial reconciliation operations execute asynchronously within the FastAPI core application processes.

The Celery worker service previously configured in `docker-compose.yml` has been safely disabled to prevent misleading execution or container crash-loops (`ModuleNotFoundError: No module named 'workers.celery_app'`).

### Planned Architecture (Phase A2 Scale-Out):
When distributed background workers are introduced:
- `workers/celery_app.py`: Celery instance configuration with Redis broker.
- `workers/document_worker.py`: Offloaded PyMuPDF OCR parsing for large batches.
- `workers/workflow_worker.py`: Long-running reconciliation and anomaly detection pipelines.
