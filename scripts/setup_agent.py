"""Create or update the Kibana Agent Builder tools and the Before You Sign agent.

Reads elastic/tools/*.json and elastic/agent.json. Existing tools and the agent are updated
in place (PUT), so this is safe to re-run; nothing is deleted.

Usage:
  python scripts/setup_agent.py            create or update tools and agent
  python scripts/setup_agent.py ask "..."  send one message to the agent and print the answer
"""
import glob
import json
import os
import sys

import requests

from common import KIBANA, ROOT, kibana_headers

API = f"{KIBANA}/api/agent_builder"


def upsert(kind, body):
    """POST to create; if it already exists, PUT the updatable fields."""
    r = requests.post(f"{API}/{kind}", headers=kibana_headers(), json=body, timeout=60)
    if r.status_code < 300:
        return "created"
    update = {k: v for k, v in body.items() if k not in ("id", "type")}
    r = requests.put(f"{API}/{kind}/{body['id']}", headers=kibana_headers(), json=update, timeout=60)
    r.raise_for_status()
    return "updated"


def setup():
    for path in sorted(glob.glob(os.path.join(ROOT, "elastic", "tools", "*.json"))):
        tool = json.load(open(path))
        print("tool", tool["id"], upsert("tools", tool))
    agent = json.load(open(os.path.join(ROOT, "elastic", "agent.json")))
    print("agent", agent["id"], upsert("agents", agent))


def ask(message, connector_id="mistral-chat"):
    body = {"agent_id": "before-you-sign", "input": message, "connector_id": connector_id}
    r = requests.post(f"{API}/converse", headers=kibana_headers(), json=body, timeout=300)
    r.raise_for_status()
    j = r.json()
    for s in j.get("steps", []):
        if s.get("type") == "tool_call":
            print("tool:", s.get("tool_id"), json.dumps(s.get("params")))
    print()
    print(j.get("response", {}).get("message", ""))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "ask":
        ask(sys.argv[2])
    else:
        setup()
