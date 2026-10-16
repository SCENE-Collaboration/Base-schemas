COMPOSE := docker compose

# Fall back on Windows / environments without GNU id(1).
UID := $(shell id -u 2>/dev/null || echo 1000)
GID := $(shell id -g 2>/dev/null || echo 1000)
UNAME := $(shell id -un 2>/dev/null || echo user)

BUILD_ARGS := \
	--build-arg uid=$(UID) \
	--build-arg gid=$(GID) \
	--build-arg user_name=$(UNAME)

.PHONY: init build_all db_up up_all down_all client_build client_up client_stop \
	client_down client_bash test test-db

init:
	@cp -n .env.example .env 2>/dev/null || true
	@echo "Created .env from .env.example (if missing). Edit MYSQL_ROOT_PASSWORD / MYSQL_PUBLISH_PORT as needed."

build_all:
	@$(COMPOSE) build $(BUILD_ARGS)

db_up:
	@$(COMPOSE) up -d --wait db

up_all:
	@$(COMPOSE) up -d --wait

down_all:
	@$(COMPOSE) down

client_build:
	@$(COMPOSE) build $(BUILD_ARGS) client

client_up:
	@$(COMPOSE) up -d --wait client

client_stop:
	@$(COMPOSE) stop client

client_down: client_stop
	@$(COMPOSE) rm -f client

client_bash:
	@$(COMPOSE) exec client bash

# Unit tests on the host (no database).
test:
	pytest -q tests/ -m "not db"

# DB smoke tests on the host against published MySQL (client → server).
# .env is loaded by the shell (not by make), so quoted values may contain '#' or '$'.
# MYSQL_PUBLISH_PORT defaults to MySQL's 3306; SCENE_DEPLOYMENT_ID to test-local.
test-db: db_up
	set -a && . ./.env && set +a && \
	DJ_HOST=127.0.0.1 DJ_PORT=$${MYSQL_PUBLISH_PORT:-3306} DJ_USER=root DJ_PASS="$$MYSQL_ROOT_PASSWORD" \
	AUTO_ACTIVATE=1 SCENE_DEPLOYMENT_ID=$${SCENE_DEPLOYMENT_ID:-test-local} \
		pytest -q tests/ -m db
