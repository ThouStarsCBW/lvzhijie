from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from app.seed import build_seed_data

T = TypeVar("T", bound=BaseModel)


class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.data = build_seed_data()
            self.save()
        else:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            self.normalize()

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def normalize(self) -> None:
        seed = build_seed_data()
        changed = False
        for key, value in seed.items():
            if key not in self.data:
                self.data[key] = value
                changed = True

        existing_agent_roles = {
            item.get("role")
            for item in self.data.get("legal_agents", [])
            if isinstance(item, dict)
        }
        seed_agents_by_role = {
            agent.get("role"): agent
            for agent in seed.get("legal_agents", [])
            if isinstance(agent, dict) and agent.get("role")
        }
        for item in self.data.get("legal_agents", []):
            if not isinstance(item, dict):
                continue
            seed_agent = seed_agents_by_role.get(item.get("role"))
            if not seed_agent:
                continue
            for field in ("title", "description", "responsibilities", "group", "reports_to", "active"):
                if item.get(field) != seed_agent.get(field):
                    item[field] = seed_agent.get(field)
                    changed = True

        for agent in seed.get("legal_agents", []):
            if isinstance(agent, dict) and agent.get("role") not in existing_agent_roles:
                self.data.setdefault("legal_agents", []).append(agent)
                existing_agent_roles.add(agent.get("role"))
                changed = True

        if changed:
            self.save()

    def list(self, key: str, model: type[T]) -> list[T]:
        return [model.model_validate(item) for item in self.data.get(key, [])]

    def get(self, key: str, item_id: str, model: type[T]) -> T | None:
        for item in self.data.get(key, []):
            if item.get("id") == item_id:
                return model.model_validate(item)
        return None

    def add(self, key: str, item: BaseModel) -> None:
        self.data.setdefault(key, []).append(item.model_dump())
        self.save()

    def upsert_single(self, key: str, item: BaseModel) -> None:
        self.data[key] = item.model_dump()
        self.save()

    def update(self, key: str, item: BaseModel) -> None:
        rows = self.data.setdefault(key, [])
        for index, row in enumerate(rows):
            if row.get("id") == getattr(item, "id"):
                rows[index] = item.model_dump()
                self.save()
                return
        rows.append(item.model_dump())
        self.save()

    def delete(self, key: str, item_id: str) -> bool:
        rows = self.data.setdefault(key, [])
        next_rows = [row for row in rows if row.get("id") != item_id]
        deleted = len(next_rows) != len(rows)
        if deleted:
            self.data[key] = next_rows
            self.save()
        return deleted

    def remove_where(self, key: str, predicate: Callable[[dict[str, Any]], bool]) -> int:
        rows = self.data.setdefault(key, [])
        next_rows = [row for row in rows if not predicate(row)]
        removed = len(rows) - len(next_rows)
        if removed:
            self.data[key] = next_rows
            self.save()
        return removed

    def filter(self, key: str, model: type[T], **conditions: Any) -> list[T]:
        rows = []
        for item in self.data.get(key, []):
            if all(item.get(field) == value for field, value in conditions.items()):
                rows.append(model.model_validate(item))
        return rows
