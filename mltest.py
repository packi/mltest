import json
import os
import uuid
from pathlib import Path

import click
import psycopg2
import psycopg2.extras
from docutils.core import publish_doctree
from sentence_transformers import SentenceTransformer

OUTPUT = Path("out")


@click.group()
def cli():
    OUTPUT.mkdir(exist_ok=True)


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def extract_titles(path):
    GLOB = "*.rst"
    path_and_titles = {}

    def section_title(node):
        try:
            return node.parent.tagname == "section" and node.tagname == "title"
        except AttributeError:
            return None  # not a section title

    for rst in Path(path).rglob(GLOB):
        try:
            doctree = publish_doctree(rst.read_text())
            titles = doctree.traverse(condition=section_title)
            if titles:
                path_and_titles[str(rst)] = [t.astext() for t in titles]
        except:
            # it throws a lot of exceptions, sinc this is only a demo, go with the broad-except
            pass

    with OUTPUT.joinpath("titles.json").open("w") as f:
        json.dump(path_and_titles, f)


@cli.command()
def create_embeddings():
    with OUTPUT.joinpath("titles.json").open("r") as f:
        path_and_titles = json.load(f)

    model = SentenceTransformer('all-MiniLM-L6-v2')
    with OUTPUT.joinpath("embeddings.sql").open("w") as out_sql:
        for path_str, titles in path_and_titles.items():
            if not titles:
                continue
            embeddings = model.encode(titles)
            article_id = str(uuid.uuid4())
            out_sql.write(f"INSERT INTO articles(article_id, link) VALUES ('{article_id}', '{path_str}');\n")
            out_sql.write("INSERT INTO titles(article_id, title, embedding) VALUES\n")
            values = []
            for title, embedding in zip(titles, embeddings):
                title_clean = title.replace("'", "''")
                values.append(f"('{article_id}', '{title_clean}', '{embedding.tolist()}')")
            out_sql.write(f"{','.join(values)};\n")


@cli.command()
def prompt():
    QUERY_TEMPLATE = """
        SELECT link, similarity FROM match_titles(%s, %s, %s)
        JOIN articles using (article_id);
    """

    print("Loading model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Done.\n")
    conn = psycopg2.connect(os.environ.get("DB_URL"))
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        running = True
        while running:
            try:
                prompt = input("query:> ")
            except (EOFError, KeyboardInterrupt):
                running = False
                continue
            prompt_embedding = model.encode([prompt])
            cur.execute(QUERY_TEMPLATE, (str(prompt_embedding[0].tolist()), 0.5, 3))
            results = cur.fetchall()
            for result in results:
                print(f"* file://{result['link']} ({result['similarity']})")

    # empty line to get a nice aligned prompt when exiting
    print()
