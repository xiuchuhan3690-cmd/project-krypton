FROM python:3.12.13-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

LABEL org.opencontainers.image.title="Project Krypton" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.description="Rights-safe restricted research-software prototype"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock pyproject.toml README.md LICENSE NOTICE THIRD_PARTY_NOTICES.md ./
RUN python -m pip install --no-cache-dir --requirement requirements.lock

COPY src ./src
COPY tests ./tests
COPY examples ./examples
COPY krypton_v1_release_metadata.yaml ./
RUN python -m pip install --no-cache-dir --no-deps --no-build-isolation .

CMD ["python", "-m", "krypton"]
