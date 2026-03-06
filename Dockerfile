# Stage 1: Build Rust Core
FROM rust:1.82-slim AS builder

# Install build dependencies for pyo3 and maturin
RUN apt-get update && apt-get install -y python3-dev python3-pip python3.11-venv build-essential

# We will use uv inside the container to build
RUN pip install --break-system-packages uv maturin

WORKDIR /build

# Copy project files
COPY pyproject.toml Cargo.toml ./
COPY src/ src/
COPY src-rust/ src-rust/
COPY README.md .

# Build the native python wheel
RUN maturin build --release --out dist

# Stage 2: Runtime Environment
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install uv for fast dependency resolution in runtime
RUN pip install --break-system-packages uv

# Copy the built wheel from Stage 1
COPY --from=builder /build/dist/*.whl /app/

# Install the wheel and production dependencies
# Note: we also add uvicorn to run the FastAPI app
RUN uv pip install --system /app/*.whl uvicorn

# Set environment variables for production default
ENV AURA_DB_PROVIDER="sqlite"
ENV DEFAULT_DB_PATH="/app/data/auragraph.db"
ENV AURA_MODEL="llama3-8b"

# Expose FastAPI port
EXPOSE 8000

# Run the FastAPI server natively
CMD ["uvicorn", "auragraph.app:app", "--host", "0.0.0.0", "--port", "8000"]
