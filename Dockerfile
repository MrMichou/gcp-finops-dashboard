# syntax=docker/dockerfile:1

# --- Build stage: produce a wheel from the source tree ----------------------
FROM python:3.12-slim AS build

WORKDIR /src
RUN pip install --no-cache-dir build

# Copy only what's needed to build the wheel (see .dockerignore for exclusions).
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m build --wheel --outdir /dist

# --- Runtime stage: minimal image with the package installed ----------------
FROM python:3.12-slim AS runtime

# Don't write .pyc files / buffer stdout — better logs in Cloud Logging / kubectl.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install the wheel with the optional extras (PDF export + YAML config support).
COPY --from=build /dist/*.whl /tmp/
RUN WHEEL="$(ls /tmp/*.whl)" \
    && pip install --no-cache-dir "${WHEEL}[pdf,yaml]" \
    && rm -rf /tmp/*.whl

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 finops
USER finops
WORKDIR /home/finops

# Default to the sample dashboard so `docker run <image>` does something useful
# with no arguments; override the args in your CronJob / `docker run`.
ENTRYPOINT ["gcp-finops"]
CMD ["--dry-run", "--trend"]
