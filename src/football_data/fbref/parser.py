from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup, Comment, Tag

EXPLICIT_COLUMNS = {
    "player": "player_name",
    "squad": "squad",
    "team": "team",
    "date": "date",
    "time": "time",
    "round": "round",
    "week": "gameweek",
    "home_team": "home_team",
    "away_team": "away_team",
    "score": "score",
    "minutes": "minutes",
    "minutes_90s": "nineties",
    "goals": "goals",
    "assists": "assists",
    "shots": "shots",
    "shots_on_target": "shots_on_target",
    "xg": "xg",
    "npxg": "npxg",
    "xg_assist": "xa",
    "cards_yellow": "yellow_cards",
    "cards_red": "red_cards",
    "match_report": "match_report",
}


@dataclass
class ParsedTable:
    table_id: str
    frame: pd.DataFrame
    column_mapping: list[dict[str, str]]


def parse_tables(html: str | bytes) -> list[ParsedTable]:
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    tables = list(soup.find_all("table"))
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        if "<table" in str(comment):
            tables.extend(BeautifulSoup(str(comment), "lxml").find_all("table"))
    result = []
    seen: set[tuple[str, str]] = set()
    for index, table in enumerate(tables):
        parsed = _parse_table(table, index)
        fingerprint = (parsed.table_id, "|".join(parsed.frame.columns))
        if fingerprint not in seen:
            result.append(parsed)
            seen.add(fingerprint)
    return result


def _parse_table(table: Tag, index: int) -> ParsedTable:
    table_id = table.get("id") or f"table_{index}"
    header_rows = table.select("thead tr")
    top_labels = _expanded_header(header_rows[0]) if len(header_rows) > 1 else []
    last = header_rows[-1] if header_rows else None
    headers = last.find_all(["th", "td"]) if last else []
    columns: list[str] = []
    mapping: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for position, cell in enumerate(headers):
        source = (
            cell.get("data-stat")
            or cell.get_text(" ", strip=True)
            or f"column_{position}"
        )
        normalized = EXPLICIT_COLUMNS.get(source, _slug(source))
        counts[normalized] = counts.get(normalized, 0) + 1
        if counts[normalized] > 1:
            normalized = f"{normalized}_{counts[normalized]}"
        columns.append(normalized)
        mapping.append(
            {
                "original_table": table_id,
                "original_header_level_1": top_labels[position]
                if position < len(top_labels)
                else "",
                "original_header_level_2": cell.get_text(" ", strip=True),
                "source_data_stat": source,
                "normalized_column": normalized,
            }
        )
    rows: list[dict[str, Any]] = []
    for tr in table.select("tbody tr"):
        if "thead" in (tr.get("class") or []):
            continue
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        row = {
            columns[i] if i < len(columns) else f"column_{i}": cell.get_text(
                " ", strip=True
            )
            or None
            for i, cell in enumerate(cells)
        }
        for cell in cells:
            anchor = cell.find("a", href=True)
            if not anchor:
                continue
            href = anchor["href"]
            for kind, pattern in (
                ("player", r"/players/([^/]+)"),
                ("squad", r"/squads/([^/]+)"),
                ("match", r"/matches/([^/]+)"),
            ):
                match = re.search(pattern, href)
                if match:
                    row[f"fbref_{kind}_id"] = match.group(1)
                    row[f"{kind}_url"] = href
        rows.append(row)
    frame = pd.DataFrame(rows)
    return ParsedTable(table_id, frame, mapping)


def _expanded_header(row: Tag) -> list[str]:
    values = []
    for cell in row.find_all(["th", "td"]):
        values.extend([cell.get_text(" ", strip=True)] * int(cell.get("colspan", 1)))
    return values


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return value or "unnamed"
