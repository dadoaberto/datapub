FROM postgres:15

# Instala a extensão pgvector
RUN apt-get update && \
    apt-get install -y git build-essential postgresql-server-dev-15 && \
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git /tmp/pgvector && \
    cd /tmp/pgvector && \
    make && \
    make install && \
    rm -rf /tmp/pgvector && \
    apt-get remove -y git build-essential postgresql-server-dev-15 && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
