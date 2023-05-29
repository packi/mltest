Small demo for pgvector and embeddings
======================================

NOTE: This works but probably has major flaws, please don't use this.

* Imports titles and headings from reStructured text files (.rst)
* Creates a big SQL file with the articles/titles and their embeddings
* Query prompt to find similar titles

Setup
-----

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install --editable .
```

Configuration
-------------
* Export `DB_URL` with a connection string to run commands

Running
-------
```bash
psql $DB_URL -f schema.sql
mltest extract-titles
mltest create-embeddings
psql $DB_URL -f out/embeddings.sql
mltest prompt
```

Idea and query function based on https://supabase.com/blog/openai-embeddings-postgres-vector but with free and open tools
