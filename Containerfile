# --- STAGE 1: Builder ---
FROM python:3.14-slim-bookworm AS builder

WORKDIR /build

# Installiere notwendige Build-Tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopiere die Dateien, die für die Erstellung der Metadaten und den Build benötigt werden
COPY pyproject.toml README.md ./

# Installiere die Abhängigkeiten in ein lokales Verzeichnis
RUN pip install --no-cache-dir --prefix=/install .

# Kopiere den restlichen Quellcode
COPY . .

# Installiere das Paket selbst mit dem vollständigen Kontext
RUN pip install --no-cache-dir --prefix=/install .

# --- STAGE 2: Runtime ---
FROM python:3.14-slim-bookworm

WORKDIR /app

# Kopiere nur die bereits fertig installierten Pakete aus der Builder-Stage
COPY --from=builder /install /usr/local

# Kopiere den restlichen Quellcode
COPY . .

# Exponiere den Port
EXPOSE 8090

# Startbefehl
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8090"]
