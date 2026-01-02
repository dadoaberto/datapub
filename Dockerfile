FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app  

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl build-essential git ca-certificates \
    tesseract-ocr \
    chromium chromium-driver \
    fonts-liberation libnss3 libxss1 libgbm1 libasound2 libxshmfence1 \
    libatk-bridge2.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip setuptools wheel \
    && pip install "dlt[sqlalchemy]" \
    && pip install -e ".[sqlalchemy]" 

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000

CMD ["uvicorn", "datapub.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
