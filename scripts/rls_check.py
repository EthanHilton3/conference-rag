"""
RLS / GRANT checker: run the same query as each Postgres role and show what happens.

Usage:
    python scripts/rls_check.py sentence_embeddings page_views

For each table, sends GET /rest/v1/<table> as:
    anon           - just the public anon key (a visitor who isn't logged in)
    user_a         - a logged-in test user (role "authenticated")
    service_role   - the admin key (bypasses RLS)

Test users are created with the admin API (no emails sent). Their password is
generated once and saved in config.secret.json (git-ignored); it is never printed.
"""
import json
import secrets
import sys

import requests

with open("config.public.json") as f:
    public = json.load(f)
with open("config.secret.json") as f:
    secret = json.load(f)

URL = public["SUPABASE_URL"]
ANON = public["SUPABASE_ANON_KEY"]
SERVICE = secret["SUPABASE_SERVICE_KEY"]
TEST_USERS = {"user_a": "rls-test-a@example.com", "user_b": "rls-test-b@example.com"}


def test_password():
    if "TEST_USER_PASSWORD" not in secret:
        secret["TEST_USER_PASSWORD"] = secrets.token_urlsafe(24)
        with open("config.secret.json", "w") as f:
            json.dump(secret, f, indent=4)
    return secret["TEST_USER_PASSWORD"]


def login(email):
    """Ensure the test user exists, then sign in and return their access-token JWT."""
    password = test_password()
    admin = {"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}"}
    requests.post(f"{URL}/auth/v1/admin/users", headers=admin,
                  json={"email": email, "password": password, "email_confirm": True})
    r = requests.post(f"{URL}/auth/v1/token?grant_type=password", headers={"apikey": ANON},
                      json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def identities():
    """(name, Authorization bearer token) for each role we test."""
    return [("anon", ANON), ("user_a", login(TEST_USERS["user_a"])), ("service_role", SERVICE)]


def query(table, bearer):
    headers = {"apikey": ANON, "Authorization": f"Bearer {bearer}", "Prefer": "count=exact"}
    r = requests.get(f"{URL}/rest/v1/{table}?select=*&limit=1", headers=headers)
    if r.ok:
        total = r.headers.get("Content-Range", "*/?").split("/")[-1]
        return f"{r.status_code} OK      -> {total} rows visible"
    return f"{r.status_code} ERROR   -> {r.json().get('message')}"


if __name__ == "__main__":
    tables = sys.argv[1:] or ["sentence_embeddings", "page_views"]
    who = identities()
    for table in tables:
        print(f"\n{table}")
        for name, bearer in who:
            print(f"  {name:13} {query(table, bearer)}")
