.PHONY: db-start db-stop db-migrate db-reset backend frontend test test-rag lint install

# --- Datenbank ---
db-start:
	docker-compose up -d postgres

db-stop:
	docker-compose down

db-migrate:
	cd backend && alembic upgrade head

db-reset:
	docker-compose down -v
	docker-compose up -d postgres
	sleep 3
	cd backend && alembic upgrade head

db-shell:
	docker exec -it meetmind_postgres psql -U meetmind -d meetmind

# --- Lokale Entwicklung ---
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# --- Tests ---
test:
	cd backend && pytest tests/ -v

test-rag:
	cd backend && pytest tests/test_rag.py -v

# --- Code-Qualität ---
lint:
	cd backend && ruff check . && black --check .

format:
	cd backend && ruff check . --fix && black .

# --- Installation ---
install:
	pip install -r backend/requirements.txt
	cd frontend && npm install
