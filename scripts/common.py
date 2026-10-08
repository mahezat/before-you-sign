"""Shared settings. Keys come from a .env file in the repo root (see .env.example), never from code."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env():
    path = os.path.join(ROOT, ".env")
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("ES_URL", "ES_API_KEY", "KIBANA_URL", "MISTRAL_API_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


ENV = _load_env()
ES = ENV.get("ES_URL", "").rstrip("/")
KIBANA = ENV.get("KIBANA_URL", "").rstrip("/")


def es_headers(content_type="application/json"):
    return {"Authorization": "ApiKey " + ENV["ES_API_KEY"], "Content-Type": content_type}


def kibana_headers():
    return {"Authorization": "ApiKey " + ENV["ES_API_KEY"], "kbn-xsrf": "true", "Content-Type": "application/json"}
