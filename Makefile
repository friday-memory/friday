.PHONY: help install dev test lint format docker-up docker-down docker-logs clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

dev: ## Run local development server
	uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload

test: ## Run test suite
	python -m pytest tests/ -v --tb=short

lint: ## Check code formatting and linting
	ruff check .

format: ## Auto-format code with ruff
	ruff format .

docker-up: ## Launch Friday and Neo4j via Docker Compose
	docker compose up -d

docker-down: ## Stop Docker Compose containers
	docker compose down

docker-logs: ## View container logs
	docker compose logs -f

clean: ## Clean Python caches and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache 2>/dev/null || true
