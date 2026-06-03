from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from app.models import LegalDocument, LegalDocumentBranch, LegalDocumentRevision, new_id
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

        # Ensure new tables exist
        if "legal_document_branches" not in self.data:
            self.data["legal_document_branches"] = []
            changed = True
        if "legal_document_analyses" not in self.data:
            self.data["legal_document_analyses"] = []
            changed = True
        if "case_task_comments" not in self.data:
            self.data["case_task_comments"] = []
            changed = True
        if "legal_research_runs" not in self.data:
            self.data["legal_research_runs"] = []
            changed = True
        if "legal_research_results" not in self.data:
            self.data["legal_research_results"] = []
            changed = True

        for task in self.data.get("case_tasks", []):
            if not isinstance(task, dict):
                continue
            defaults = {
                "task_type": "general",
                "due_at": None,
                "depends_on_task_ids": [],
                "document_id": None,
                "base_revision_id": None,
                "target_revision_id": None,
                "output_document_id": None,
                "output_revision_id": None,
                "metadata": {},
            }
            for field, default in defaults.items():
                if field not in task:
                    task[field] = default
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

        # Migrate existing documents to branch structure
        for doc_data in self.data.get("legal_documents", []):
            if not isinstance(doc_data, dict):
                continue
            if not doc_data.get("default_branch_id"):
                # Create main branch for this document
                doc_id = doc_data.get("id")
                if not doc_id:
                    continue
                
                # Find all revisions for this document
                revisions = [
                    rev for rev in self.data.get("legal_document_revisions", [])
                    if isinstance(rev, dict) and rev.get("document_id") == doc_id
                ]
                revisions.sort(key=lambda x: x.get("version_number", 0))
                
                # Create main branch
                main_branch_id = new_id("branch")
                main_branch = {
                    "id": main_branch_id,
                    "document_id": doc_id,
                    "name": "main",
                    "head_revision_id": revisions[-1]["id"] if revisions else None,
                    "base_revision_id": revisions[0]["id"] if revisions else None,
                    "is_default": True,
                    "created_at": doc_data.get("created_at", ""),
                    "updated_at": doc_data.get("updated_at", ""),
                }
                self.data.setdefault("legal_document_branches", []).append(main_branch)
                
                # Update document
                doc_data["default_branch_id"] = main_branch_id
                if revisions:
                    doc_data["current_revision_id"] = revisions[-1]["id"]
                
                # Update revisions
                for i, rev in enumerate(revisions):
                    if not rev.get("branch_id"):
                        rev["branch_id"] = main_branch_id
                    if not rev.get("parent_revision_id"):
                        rev["parent_revision_id"] = revisions[i-1]["id"] if i > 0 else None
                    if not rev.get("created_from_revision_id"):
                        rev["created_from_revision_id"] = revisions[i-1]["id"] if i > 0 else None
                    if not rev.get("short_hash"):
                        rev["short_hash"] = rev["id"].replace("rev_", "")[:7]
                
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
