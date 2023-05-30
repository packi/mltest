import json
import os
import uuid
from itertools import islice
from pathlib import Path
from typing import Sequence, Iterator

import click
import psycopg2
import psycopg2.extras
from docutils.core import publish_doctree
from sentence_transformers import SentenceTransformer

OUTPUT = Path("out")
MODEL_NAME = "all-MiniLM-L6-v2"


@click.group()
def cli():
    OUTPUT.mkdir(exist_ok=True)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def extract_blocks(path):
    GLOB = "*.rst"
    path_and_blocks = {}

    def extract_text_nodes(node):
        try:
            return (
                node.parent.tagname in ("section", "document")
                and node.tagname == "title"
            ) or (
                node.parent.tagname != "system_message" and node.tagname == "paragraph"
            )
        except AttributeError:
            return None  # not a usable text node

    for rst in Path(path).rglob(GLOB):
        print("Processing", rst)
        try:
            doctree = publish_doctree(rst.read_text())
            blocks = doctree.traverse(condition=extract_text_nodes)
            if blocks:
                path_and_blocks[str(rst)] = [t.astext() for t in blocks]
        except:
            # it throws a lot of exceptions, since this is only a demo, go with the broad-except
            pass

    with OUTPUT.joinpath("blocks.json").open("w") as f:
        json.dump(path_and_blocks, f)


def usable_blocks(blocks: Sequence[str]) -> Iterator[str]:
    MODEL_MAX_INPUT_LENGH = 100
    for block in blocks:
        if len(block.split(" ")) < MODEL_MAX_INPUT_LENGH:
            yield block
        else:
            for sentence in block.split(". "):
                sentence_words = sentence.split(" ")
                if len(sentence_words) < MODEL_MAX_INPUT_LENGH:
                    yield sentence
                else:
                    it = iter(sentence_words)
                    for sentence_part in islice(it, MODEL_MAX_INPUT_LENGH):
                        yield " ".join(sentence_part)


@cli.command()
def create_embeddings():
    with OUTPUT.joinpath("blocks.json").open("r") as f:
        path_and_blocks = json.load(f)

    model = SentenceTransformer(MODEL_NAME)
    with OUTPUT.joinpath("embeddings.sql").open("w") as out_sql:
        for path_str, blocks in path_and_blocks.items():
            if not blocks:
                continue

            print("Processing", path_str)

            blocks_to_calculate = list(usable_blocks(blocks))

            embeddings = model.encode(blocks_to_calculate)
            article_id = str(uuid.uuid4())
            out_sql.write(
                f"INSERT INTO articles(article_id, link) VALUES ('{article_id}', '{path_str}');\n"
            )
            out_sql.write("INSERT INTO blocks(article_id, block, embedding) VALUES\n")
            values = []
            for block, embedding in zip(blocks_to_calculate, embeddings):
                block_clean = block.replace("'", "''")
                values.append(
                    f"('{article_id}', '{block_clean}', '{embedding.tolist()}')"
                )
            out_sql.write(f"{','.join(values)};\n")


@cli.command()
def prompt():
    QUERY_TEMPLATE = """
        SELECT link, similarity FROM match_blocks(%s, %s, %s)
        JOIN articles using (article_id);
    """

    print("Loading model...")
    model = SentenceTransformer(MODEL_NAME)
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
