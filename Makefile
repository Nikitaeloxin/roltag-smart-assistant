DOCKER_COMPOSE=docker-compose.yml
ENV_FILE=.env
DC=docker compose --env-file $(ENV_FILE) -f $(DOCKER_COMPOSE)

FILE ?= indigo_6600.pdf

.PHONY: roltag-ai-assistant-service index

roltag-ai-assistant-service:
	$(DC) up -d --build roltag-ai-assistant-service

index:
	$(DC) run --rm --build roltag-ai-assistant-service uv run python -m app.indexing.index --file data/$(FILE) $(ARGS)

roltag-assistant:
	$(DC) up -d --build roltag-ai-assistant-service roltag-telegram-bot-service

down:
	@echo "Stopping and removing services..."
	$(DC) down

down-v:
	@echo "Stopping and removing services and volumes..."
	$(DC) down -v


