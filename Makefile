COMPOSE := docker compose

# Fall back on Windows / environments without GNU id(1).
UID := $(shell id -u 2>/dev/null || echo 1000)
GID := $(shell id -g 2>/dev/null || echo 1000)
UNAME := $(shell id -un 2>/dev/null || echo user)

BUILD_ARGS := \
	--build-arg uid=$(UID) \
	--build-arg gid=$(GID) \
	--build-arg user_name=$(UNAME)

ifneq (,$(wildcard .env))
include .env
export
endif

# Host port published to MySQL (MySQL's default listen port inside the container is 3306).
MYSQL_PUBLISH_PORT ?= 3306
# Default deployment stamp for DB smoke tests (override in .env).
SCENE_DEPLOYMENT_ID ?= test-local

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
test-db: db_up
	DJ_HOST=127.0.0.1 DJ_PORT=$(MYSQL_PUBLISH_PORT) DJ_USER=root DJ_PASS=$(MYSQL_ROOT_PASSWORD) \
	AUTO_ACTIVATE=1 SCENE_DEPLOYMENT_ID=$(SCENE_DEPLOYMENT_ID) \
		pytest -q tests/ -m db
