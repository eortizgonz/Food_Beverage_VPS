CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.sop_chunks (
    id bigserial PRIMARY KEY,
    document_hash varchar(64) NOT NULL,
    document_name varchar(255) NOT NULL,
    page integer NOT NULL CHECK (page >= 1),
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    content text NOT NULL,
    embedding vector NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sop_document_chunk UNIQUE (document_hash, page, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_sop_chunks_document_hash
    ON public.sop_chunks (document_hash);

-- El índice HNSW se debe crear después de fijar la dimensión del modelo de embeddings.
