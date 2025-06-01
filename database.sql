-- Estrutura do banco de dados
CREATE TABLE documentos (
    id SERIAL PRIMARY KEY,
    orgao VARCHAR(255) NOT NULL,
    data_publicacao DATE NOT NULL,
    caminho_arquivo VARCHAR(512) NOT NULL,
    hash_arquivo VARCHAR(64) UNIQUE NOT NULL,
    metadata JSONB
);

CREATE TABLE entidades (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER REFERENCES documentos(id),
    tipo_entidade VARCHAR(50) NOT NULL,  -- 'PESSOA', 'ORGAO', 'LOCAL', etc.
    valor TEXT NOT NULL,
    contexto TEXT,
    inicio_pos INTEGER,
    fim_pos INTEGER
);

CREATE TABLE gastos (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER REFERENCES documentos(id),
    orgao TEXT NOT NULL,
    valor NUMERIC(15,2) NOT NULL,
    descricao TEXT,
    data DATE,
    categoria TEXT
);

-- Extensão para armazenar embeddings
CREATE EXTENSION vector;
CREATE TABLE document_embeddings (
    document_id INTEGER PRIMARY KEY REFERENCES documentos(id),
    embedding vector(768)  -- Dimensão do embedding
);