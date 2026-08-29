from __future__ import annotations

import json
import os
import urllib.request

from .knowledge import CAUTION, SAFE

PROVIDERS = ("heuristic", "anthropic")


class HeuristicProvider:
    name = "heuristic"

    def classify_unknown(self, path: str, size: int, evidence: list[str]) -> tuple[str, str]:
        return CAUTION, "unknown path: no matching rule; defaulting to caution"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        self.api_key = api_key
        self.model = model

    def classify_unknown(self, path: str, size: int, evidence: list[str]) -> tuple[str, str]:
        prompt = (
            "You classify filesystem paths for a disk-cleanup agent. "
            "Answer with strict JSON only: {\"tier\": \"SAFE\"|\"CAUTION\"|\"FORBIDDEN\", \"reason\": \"...\"}. "
            "SAFE = regenerable artifact/cache. CAUTION = may hold state. "
            "FORBIDDEN = user data, credentials, git objects, irreversible.\n"
            f"path: {path}\nsize_bytes: {size}\nevidence: {json.dumps(evidence)}"
        )
        body = json.dumps({
            "model": self.model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            text = data["content"][0]["text"].strip()
            parsed = json.loads(text)
            tier = parsed.get("tier", CAUTION)
            if tier not in (SAFE, CAUTION, "FORBIDDEN"):
                tier = CAUTION
            return tier, f"llm({self.model}): {parsed.get('reason', '')}"
        except Exception as exc:
            return CAUTION, f"llm unavailable ({exc}); defaulting to caution"


def get_provider(name: str):
    if name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return HeuristicProvider()
        return AnthropicProvider(key)
    return HeuristicProvider()
