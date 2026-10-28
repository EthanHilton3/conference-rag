"""
Scale experiment: exact vector search (no index) vs. approximate HNSW index.

Usage:
    python scripts/index_experiment.py explain exact   # before the index
    python scripts/index_experiment.py create-index
    python scripts/index_experiment.py explain hnsw    # after the index; compares with exact
    python scripts/index_experiment.py drop-index      # to repeat the experiment

Runs SQL through the Supabase Management API (admin role, so RLS doesn't apply).
"""
import json
import os
import re
import sys

import requests
from openai import OpenAI

with open("config.secret.json") as f:
    secret = json.load(f)

QUESTION = "How can I find peace during hard times?"
OUT = os.path.join("scripts", "output")


def sql(query):
    r = requests.post(
        f"https://api.supabase.com/v1/projects/{secret['SUPABASE_PROJECT_REF']}/database/query",
        headers={"Authorization": f"Bearer {secret['SUPABASE_ACCESS_TOKEN']}"},
        json={"query": query},
    )
    if not r.ok:
        sys.exit(f"SQL error {r.status_code}: {r.text[:500]}")
    return r.json()


def question_vector():
    client = OpenAI(api_key=secret["OPENAI_API_KEY"])
    v = client.embeddings.create(model="text-embedding-3-small", input=QUESTION).data[0].embedding
    return "[" + ",".join(map(str, v)) + "]"


def explain(label):
    vec = question_vector()
    top20 = f"SELECT id FROM sentence_embeddings ORDER BY embedding <=> '{vec}'::vector LIMIT 20"
    plan = [row["QUERY PLAN"] for row in sql("EXPLAIN ANALYZE " + top20)]
    print(f"\n--- {label}: query plan ---")
    for line in plan:
        if re.search(r"Scan|Sort|Limit|Execution Time|Planning Time", line):
            print(" ", line.strip()[:110])

    ids = [row["id"] for row in sql(top20)]
    with open(os.path.join(OUT, f"top20_{label}.json"), "w") as f:
        json.dump(ids, f)
    exact_file = os.path.join(OUT, "top20_exact.json")
    if label != "exact" and os.path.exists(exact_file):
        with open(exact_file) as f:
            exact = set(json.load(f))
        print(f"\nrecall@20 vs exact search: {len(exact & set(ids))}/20 of the true top 20 found")


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "explain":
        explain(sys.argv[2])
    elif action == "create-index":
        # Free tier defaults: 2-minute statement timeout and 32MB of build memory, too little
        # for ~170MB of graph. Raise both for this session only, and build in one process:
        # a parallel build needs the graph in shared memory, which this container can't fit.
        sql("SET statement_timeout = 0; SET maintenance_work_mem = '200MB'; SET max_parallel_maintenance_workers = 0; "
            "CREATE INDEX IF NOT EXISTS sentence_embeddings_embedding_hnsw "
            "ON sentence_embeddings USING hnsw (embedding vector_cosine_ops);")
        print(sql("SELECT pg_size_pretty(pg_relation_size('sentence_embeddings_embedding_hnsw')) AS index_size"))
    elif action == "drop-index":
        sql("DROP INDEX IF EXISTS sentence_embeddings_embedding_hnsw;")
        print("dropped")
