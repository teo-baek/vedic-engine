# pyswisseph is a C extension with no Windows wheels, so everything runs in Docker.

IMAGE ?= vedic-engine
DEV_IMAGE ?= vedic-engine-dev
PORT ?= 8080
DEV_RUN = docker run --rm -v "$(CURDIR)":/app -w /app $(DEV_IMAGE)

.PHONY: build dev-image test lint golden run test-image shell verify

build:
	docker build -t $(IMAGE) .

dev-image:
	docker build -t $(DEV_IMAGE) -f Dockerfile.dev .

test: dev-image
	$(DEV_RUN) pytest -q

lint: dev-image
	$(DEV_RUN) ruff check .

golden: dev-image
	$(DEV_RUN) python tools/generate_golden.py

# Run the suite inside the *pruned* runtime image — proves the Dockerfile's asset removal
# did not break anything the endpoints need.
test-image: build
	docker run --rm -u root -v "$(CURDIR)/tests":/app/tests -v "$(CURDIR)/tools":/app/tools \
		-v "$(CURDIR)/pyproject.toml":/app/pyproject.toml \
		$(IMAGE) sh -c "pip install --quiet --no-cache-dir pytest httpx && python -m pytest -q"

verify: lint test test-image

run: build
	docker run --rm -p $(PORT):8080 $(IMAGE)

shell: dev-image
	$(DEV_RUN) bash
