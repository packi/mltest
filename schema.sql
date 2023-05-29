CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE articles (
    article_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    link VARCHAR
);

CREATE TABLE titles (
    title_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID,
    title VARCHAR,
    embedding VECTOR(384),
    CONSTRAINT fk_article_id FOREIGN KEY(article_id) REFERENCES articles(article_id)
);

CREATE INDEX ON titles USING ivfflat (embedding vector_cosine_ops)
WITH
  (lists = 100);

CREATE OR replace FUNCTION match_titles (
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
    titles.article_id,
    titles.title,
    1 - (titles.embedding <=> query_embedding) AS similarity
  FROM titles
  WHERE 1 - (titles.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;