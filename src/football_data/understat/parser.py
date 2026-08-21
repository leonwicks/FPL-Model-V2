from __future__ import annotations

import ast
import json
import re
from typing import Any

from bs4 import BeautifulSoup

PAYLOAD_RE = re.compile(
    r"(?:var|let|const)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*JSON\.parse\(\s*"
    r"(?P<quote>['\"])(?P<payload>.*?)(?P=quote)\s*\)",
    re.DOTALL,
)


def parse_payloads(html: str | bytes) -> dict[str, Any]:
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, Any] = {}
    for script in soup.find_all("script"):
        text = script.string or script.get_text()
        for match in PAYLOAD_RE.finditer(text):
            encoded = (
                match.group("quote") + match.group("payload") + match.group("quote")
            )
            try:
                decoded = ast.literal_eval(encoded)
                found[match.group("name")] = json.loads(decoded)
            except (SyntaxError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Could not decode Understat payload {match.group('name')}"
                ) from exc
    if not found:
        raise ValueError("No Understat JSON.parse payloads found")
    return found


def require_payload(payloads: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in payloads:
            return payloads[name]
    raise ValueError(f"Missing Understat payload; expected one of {names}")


def modern_league_payloads(value: dict[str, Any]) -> dict[str, Any]:
    """Map Understat's current AJAX response to the established payload names."""
    required = {"dates", "players", "teams"}
    missing = sorted(required.difference(value))
    if missing:
        raise ValueError(f"Understat league JSON missing fields: {missing}")
    return {
        "datesData": value["dates"],
        "playersData": value["players"],
        "teamsData": value["teams"],
    }


def modern_match_payloads(value: dict[str, Any]) -> dict[str, Any]:
    required = {"rosters", "shots"}
    missing = sorted(required.difference(value))
    if missing:
        raise ValueError(f"Understat match JSON missing fields: {missing}")
    return {"rostersData": value["rosters"], "shotsData": value["shots"]}
