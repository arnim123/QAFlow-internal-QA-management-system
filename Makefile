.PHONY: up up-dev down test lint migrate

up:
	docker compose up --build

up-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down:
	docker compose down

test:
	docker compose exec api pytest

lint:
	docker compose exec api ruff check app tests
	docker compose exec api python -m compileall -q app tests

migrate:
	docker compose exec api alembic upgrade head
