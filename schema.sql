CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE articles (
    article_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    link VARCHAR
);

CREATE TABLE blocks (
    block_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID,
    block VARCHAR,
    embedding VECTOR(384),
    CONSTRAINT fk_article_id FOREIGN KEY(article_id) REFERENCES articles(article_id)
);

CREATE INDEX ON blocks USING ivfflat (embedding vector_cosine_ops)
WITH
  (lists = 100);

CREATE OR replace FUNCTION match_blocks (
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  article_id uuid,
  content text,
  similarity float
)
LANGUAGE SQL stable
AS $$
SELECT
    blocks.article_id,
    blocks.block,
    1 - (blocks.embedding <=> query_embedding) AS similarity
  FROM blocks
  WHERE 1 - (blocks.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
