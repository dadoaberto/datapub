FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app  

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip setuptools wheel \
    && pip install "dlt[sqlalchemy]" \
    && pip install -e ".[sqlalchemy]" 

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["bash"]