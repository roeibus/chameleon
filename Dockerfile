# Stage 1: Build stage
FROM python:3.14-slim AS builder

# Set the working directory
WORKDIR /app

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /usr/bin/uv /usr/bin/uv

# Copy project configuration files
COPY pyproject.toml ./
COPY VERSION ./

# Sync dependencies to create a virtual environment
# We use --no-install-project as we only want dependencies in the build layer
RUN uv sync --no-install-project

# Stage 2: Production stage
FROM python:3.14-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    LOG_DIR="/var/log/chameleon"

# Set the working directory
WORKDIR /app

# Install runtime dependencies (e.g., docker-cli if needed, but the python lib handles it)
# We might need docker-cli if we want to manually check things, but for the lib it's not strictly required.
# However, having it is good for the "build inside" requirement if we want to pre-build.
RUN apt-get update && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the source code and resources
COPY src ./src
COPY resources ./resources
COPY VERSION ./

# Create log directory
RUN mkdir -p ${LOG_DIR}


# Avoid root to prevent honeypot escape
RUN useradd --create-home --shell /usr/sbin/nologin chameleon

RUN chown -R chameleon:chameleon /app ${LOG_DIR}

USER chameleon

# Expose common honeypot ports (customize as needed)
# Telnet: 23, HTTP Proxy: 8080, SSH: 22
EXPOSE 23 22 8080 9090 80



# Entry point
# The app will build backend images at runtime if they don't exist
# We ensure the Docker socket is accessible at runtime
CMD ["python", "src/main.py"]