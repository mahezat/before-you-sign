"""Create the Mistral inference endpoint in Elasticsearch (Elastic Inference API).

  mistral-chat   chat_completion, model mistral-large-2512. The agent uses it as its LLM.

mistral-large-2512 is pinned on purpose: newer Mistral Large versions stream "thinking" content
blocks that the chat_completion integration could not parse at the time.

Usage: python scripts/setup_inference.py
"""
import requests

from common import ENV, ES, es_headers

ENDPOINTS = {
    "chat_completion/mistral-chat": {
        "service": "mistral",
        "service_settings": {"api_key": ENV["MISTRAL_API_KEY"], "model": "mistral-large-2512"},
    },
}


def main():
    for path, body in ENDPOINTS.items():
        r = requests.put(f"{ES}/_inference/{path}", headers=es_headers(), json=body, timeout=120)
        if r.ok:
            print(path, "created")
        elif "resource_already_exists_exception" in r.text:
            print(path, "already exists (delete it first to change the model or key)")
        else:
            print(path, r.status_code, r.text[:300])


if __name__ == "__main__":
    main()
