FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with UID 1000
RUN useradd -m -u 1000 user

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=user:user . .

# Ensure storage directories exist and have proper permissions
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R user:user /app && \
    chmod -R 775 /app

USER user

RUN python manage.py collectstatic --noinput

EXPOSE 10000 8000 7860

CMD ["sh", "-c", "python manage.py migrate && gunicorn screening.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 2 --timeout 120"]
