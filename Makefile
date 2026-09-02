.PHONY: up down logs backend-shell db-shell test lint

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-shell:
	docker compose exec backend bash

db-shell:
	docker compose exec db psql -U bhudrishti -d bhudrishti

test:
	docker compose exec backend pytest -q

lint:
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint
