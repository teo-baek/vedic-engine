# Build stage — pyswisseph is a C extension and needs a compiler; the runtime does not.
FROM python:3.12-slim AS builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv

WORKDIR /build
COPY pyproject.toml README.md ./
RUN uv pip install --system --no-cache -r pyproject.toml

# PyJHora ships a desktop app's worth of assets. None of it is reachable from the six
# endpoints here, and it is ~65 MB of image. The import check at the end of this stage is
# what proves the pruning is safe; `make test-image` then runs the full suite in the
# built image, so a wrong entry here fails the build rather than production.
#   images/, ui/       Qt widgets and artwork
#   experiments/,tests/ the upstream author's scratch code
#   data/geonames*.csv  city lookup — this service is given coordinates, never a place name
#   data/ephe/seasnam.txt  asteroid name index; planetary positions come from the
#                          Moshier ephemeris compiled into pyswisseph, not from data files
RUN SITE=$(python -c "import jhora, os; print(os.path.dirname(jhora.__file__))") \
 && rm -rf "$SITE/images" "$SITE/ui" "$SITE/experiments" "$SITE/tests" \
 && rm -f "$SITE"/data/geonames_places_5k.csv "$SITE"/data/geonames_places_5k_IN.csv \
 && rm -f "$SITE/data/ephe/seasnam.txt" \
 && python -c "from jhora.panchanga import drik; drik.set_ayanamsa_mode('LAHIRI'); print('post-prune import ok')"

# Runtime stage
FROM python:3.12-slim

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY constants.py schemas.py main.py ./
COPY wrappers ./wrappers

RUN useradd --create-home --uid 10001 engine
USER engine

# Cloud Run injects PORT; 8080 is its default.
ENV PORT=8080 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
