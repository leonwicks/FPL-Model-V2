from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SchemaDrift:
    new_columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    type_changes: list[str] = field(default_factory=list)
    structure_changes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "new_columns": self.new_columns,
            "missing_columns": self.missing_columns,
            "type_changes": self.type_changes,
            "structure_changes": self.structure_changes,
        }


class SchemaRegistry:
    """Tracks observed fields without rejecting additive upstream changes."""

    def __init__(self, directory: Path | str = "schemas") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def compare(
        self,
        name: str,
        observed: dict[str, str],
        *,
        critical: Iterable[str] = (),
        season: str | None = None,
    ) -> SchemaDrift:
        path = self.directory / f"{name}.json"
        previous: dict[str, Any] = {}
        if path.exists():
            previous = json.loads(path.read_text(encoding="utf-8")).get("columns", {})
        new = sorted(set(observed) - set(previous)) if previous else []
        missing = sorted(set(previous) - set(observed))
        type_changes = sorted(
            name
            for name in set(previous) & set(observed)
            if previous[name].get("type") not in (None, observed[name], "object")
            and observed[name] != "object"
        )
        absent_critical = sorted(set(critical) - set(observed))
        if absent_critical:
            raise ValueError(f"{name}: missing critical columns: {absent_critical}")
        columns = dict(previous)
        for column, dtype in observed.items():
            old = columns.get(column, {})
            columns[column] = {
                "type": dtype,
                "first_season": old.get("first_season", season),
                "last_season": season or old.get("last_season"),
            }
        payload = {"schema": name, "columns": columns}
        self._atomic_json(path, payload)
        return SchemaDrift(new, missing, type_changes)

    @staticmethod
    def _atomic_json(path: Path, payload: Any) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        temporary.replace(path)
