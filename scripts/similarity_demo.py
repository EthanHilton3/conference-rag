"""
Embedding by hand: does cosine similarity follow meaning or shared words?

Usage:
    python scripts/similarity_demo.py
"""
import json
import math

from openai import OpenAI

with open("config.secret.json") as f:
    client = OpenAI(api_key=json.load(f)["OPENAI_API_KEY"])

question = "How can I find peace during hard times?"
candidates = {
    "same meaning, no shared words": "The Savior offers comfort and rest to all who are weary and heavy laden.",
    "shared words, different meaning": "Finding a parking spot in Times Square during the holidays is hard.",
    "unrelated": "The auditing department reviewed the financial records.",
}

texts = [question] + list(candidates.values())
vectors = [d.embedding for d in client.embeddings.create(model="text-embedding-3-small", input=texts).data]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


q = vectors[0]
print(f"dimensions: {len(q)}   first 5 numbers: {[round(x, 4) for x in q[:5]]}")
print(f"length (norm) of question vector: {math.sqrt(dot(q, q)):.4f}\n")
print(f"Q: {question}")
for (label, text), v in zip(candidates.items(), vectors[1:]):
    cosine = dot(q, v) / (math.sqrt(dot(q, q)) * math.sqrt(dot(v, v)))
    print(f"  cosine {cosine:.3f}  [{label}]  {text}")
