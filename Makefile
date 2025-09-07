# C2 Framework Makefile

.PHONY: help setup build run stop clean test lint format docs

# Colors
GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m

help:
	@echo "C2 Framework Build System"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup       - Initial setup"
	@echo "  make build       - Build all components"
	@echo "  make run         - Run all services"
	@echo "  make stop        - Stop all services"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"
	@echo "  make docs        - Generate documentation"
	@echo ""
	@echo "Component-specific commands:"
	@echo "  make server      - Build server only"
	@echo "  make client      - Build client only"
	@echo "  make agent       - Build agent only"
	@echo "  make payloads    - Generate all payload types"

setup:
	@echo "$(GREEN)[+] Setting up C2 Framework...$(NC)"
	./scripts/setup.sh

build: server client agent
	@echo "$(GREEN)[+] Build complete!$(NC)"

server:
	@echo "$(GREEN)[+] Building server...$(NC)"
	docker-compose build server

client:
	@echo "$(GREEN)[+] Building client...$(NC)"
	docker-compose build client

agent:
	@echo "$(GREEN)[+] Building agent...$(NC)"
	cd agent && python setup.py build

run:
	@echo "$(GREEN)[+] Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)[+] Services started!$(NC)"
	@echo "Web UI: http://localhost:3000"
	@echo "API: http://localhost:8000"

stop:
	@echo "$(RED)[-] Stopping services...$(NC)"
	docker-compose down

clean:
	@echo "$(RED)[-] Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf agent/build agent/dist
	rm -rf client/dist client/node_modules
	rm -rf payloads/*.exe payloads/*.dll payloads/*.bin

test: test-server test-agent test-integration

test-server:
	@echo "$(GREEN)[+] Running server tests...$(NC)"
	cd server && python -m pytest tests/ -v

test-agent:
	@echo "$(GREEN)[+] Running agent tests...$(NC)"
	cd agent && python -m pytest tests/ -v

test-integration:
	@echo "$(GREEN)[+] Running integration tests...$(NC)"
	python -m pytest tests/integration/ -v

lint: lint-python lint-javascript

lint-python:
	@echo "$(GREEN)[+] Linting Python code...$(NC)"
	cd server && flake8 . --config=../.flake8
	cd agent && flake8 . --config=../.flake8

lint-javascript:
	@echo "$(GREEN)[+] Linting JavaScript code...$(NC)"
	cd client && npm run lint

format: format-python format-javascript

format-python:
	@echo "$(GREEN)[+] Formatting Python code...$(NC)"
	black server/ agent/ --line-length 100
	isort server/ agent/

format-javascript:
	@echo "$(GREEN)[+] Formatting JavaScript code...$(NC)"
	cd client && npm run format

docs:
	@echo "$(GREEN)[+] Generating documentation...$(NC)"
	cd docs && make html

# Payload generation
payloads: payload-windows payload-linux payload-macos

payload-windows:
	@echo "$(GREEN)[+] Generating Windows payloads...$(NC)"
	python scripts/build_agent.py \
		--name windows-agent \
		--type exe \
		--platform windows \
		--arch x64 \
		--callback https://c2.example.com \
		--session default \
		--output payloads/

payload-linux:
	@echo "$(GREEN)[+] Generating Linux payloads...$(NC)"
	python scripts/build_agent.py \
		--name linux-agent \
		--type python \
		--platform linux \
		--arch x64 \
		--callback https://c2.example.com \
		--session default \
		--output payloads/

payload-macos:
	@echo "$(GREEN)[+] Generating macOS payloads...$(NC)"
	python scripts/build_agent.py \
		--name macos-agent \
		--type python \
		--platform darwin \
		--arch x64 \
		--callback https://c2.example.com \
		--session default \
		--output payloads/

# Development helpers
dev-server:
	cd server && python run.py

dev-client:
	cd client && npm run dev

dev-db:
	docker-compose up -d postgres redis

# Docker helpers
docker-build:
	docker-compose build

docker-push:
	docker-compose push

docker-pull:
	docker-compose pull

# Database management
db-migrate:
	docker-compose run --rm server alembic upgrade head

db-reset:
	docker-compose run --rm server python -c "from core.database import Base, engine; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"

# Logs
logs:
	docker-compose logs -f

logs-server:
	docker-compose logs -f server

logs-client:
	docker-compose logs -f client
