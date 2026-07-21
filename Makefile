# Makefile for HawkNet-Ai

.PHONY: demo setup test eval build down clean

demo:
	@echo "=== HawkNet-Ai — Initializing Demo Environment ==="
	@python3 -m venv .venv 2>/dev/null || true
	@. .venv/bin/activate && pip install -q -r backend/requirements.txt
	@echo "\n--- Seeding Datasets & Proxy Models ---"
	@. .venv/bin/activate && python3 data/scam_transcripts/load.py || true
	@. .venv/bin/activate && python3 data/counterfeit/generate.py || true
	@. .venv/bin/activate && python3 data/fraud_graph/generate.py || true
	@. .venv/bin/activate && python3 data/geospatial/load.py || true
	@echo "\n--- Starting Docker Compose Services ---"
	docker compose up --build -d
	@echo "\n=========================================================="
	@echo "  HawkNet-Ai is LIVE!"
	@echo "=========================================================="
	@echo "  Frontend Command Center:  http://localhost:5173"
	@echo "  Backend OpenAPI Swagger:   http://localhost:8000/docs"
	@echo "  Health Endpoint:          http://localhost:8000/health"
	@echo "  Prometheus Metrics:       http://localhost:8000/metrics"
	@echo "=========================================================="

test:
	@. .venv/bin/activate && PYTHONPATH=backend pytest tests/ -v

eval:
	@. .venv/bin/activate && PYTHONPATH=backend python3 backend/app/evaluation/run_eval.py

build:
	docker compose build

down:
	docker compose down

clean:
	docker compose down -v
	rm -rf .venv
