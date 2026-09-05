FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with UID 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=user:user . .

# Ensure storage directories exist and have proper permissions for user 1000
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R user:user /app && \
    chmod -R 775 /app

USER user

RUN python manage.py collectstatic --noinput

EXPOSE 7860

CMD ["sh", "-c", "python manage.py migrate && python manage.py create_admin && gunicorn screening.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 120"]
