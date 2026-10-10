# Nutze das offizielle Python 3.14 Debian-basierte Image
FROM python:3.14-slim-bookworm

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere zuerst die pyproject.toml, um den Docker-Cache optimal zu nutzen
COPY pyproject.toml .

# Installiere das Projekt und alle Abhängigkeiten aus der pyproject.toml
# Da wir hatchling als Build-Backend nutzen, installiert 'pip install .' alles korrekt
RUN pip install --no-cache-dir .

# Kopiere den restlichen Quellcode in den Container
COPY . .

# Exponiere den Port, auf dem die FastAPI-App läuft
EXPOSE 8000

# Startbefehl (Platzhalter, wird angepasst, sobald die main.py existiert)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
