FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .

# Crear wheels (cacheables)
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt



FROM python:3.12-slim

WORKDIR /app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear usuario no-root (seguridad 🔐)
RUN useradd -m appuser

# Copiar wheels desde builder
COPY --from=builder /wheels /wheels

# Instalar deps SIN cache
RUN pip install --no-cache-dir /wheels/*

# Copiar solo el código necesario
COPY weather/ weather/
COPY config/ config/

# Cambiar usuario
USER appuser

# Comando
CMD ["python", "-m", "weather.bot.main"]