.PHONY: help setup migrate run-backend run-frontend run-celery test lint

help:
	@echo ""
	@echo "Grant Proposal AI — Commands"
	@echo "============================="
	@echo "  make setup         Full first-time setup"
	@echo "  make migrate       Run Django migrations"
	@echo "  make run-backend   Start Django dev server"
	@echo "  make run-frontend  Start React dev server"
	@echo "  make run-celery    Start Celery worker"
	@echo "  make test          Run all tests"
	@echo "  make lint          Run ruff linter"
	@echo "  make superuser     Create Django admin superuser"
	@echo ""

setup:
	@echo "Setting up backend..."
	cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
	cd backend && cp .env.example .env
	@echo "Setting up frontend..."
	cd frontend && npm install --legacy-peer-deps
	@echo ""
	@echo "✅ Setup complete! Next:"
	@echo "  1. Edit backend/.env with your settings"
	@echo "  2. make migrate"
	@echo "  3. make superuser"
	@echo "  4. make run-backend (in one terminal)"
	@echo "  5. make run-frontend (in another terminal)"

migrate:
	cd backend && python manage.py makemigrations && python manage.py migrate

superuser:
	cd backend && python manage.py createsuperuser

run-backend:
	cd backend && PYTHONPATH=. python manage.py runserver

run-frontend:
	cd frontend && DISABLE_ESLINT_PLUGIN=true npm start

run-celery:
	cd backend && celery -A config worker --loglevel=info

test:
	cd backend && pytest

lint:
	cd backend && ruff check apps/

docker-up:
	docker compose up -d

docker-down:
	docker compose down

pull-models:
	ollama pull llama3.1:8b
	ollama pull nomic-embed-text
	@echo "✅ Models ready"
