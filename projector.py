"""
Simple read-model projector for graph snapshots.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class GraphReadModel:
    def __init__(self, db_path: str = "insurance_graph_read.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS container_snapshots (
                container_id TEXT PRIMARY KEY,
                snapshot_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def project_snapshot(self, snapshot: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO container_snapshots (container_id, snapshot_json, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                snapshot["container_id"],
                json.dumps(snapshot),
                datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            ),
        )
        conn.commit()
        conn.close()

    def get_container_graph(
        self,
        container_id: str,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT snapshot_json FROM container_snapshots WHERE container_id = ?",
            (container_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {}

        snapshot = json.loads(row[0])
        if as_of_date:
            as_of = datetime.fromisoformat(as_of_date.replace("Z", "+00:00"))
            snapshot["relationships"] = [
                rel
                for rel in snapshot.get("relationships", [])
                if datetime.fromisoformat(rel["effective_from"].replace("Z", "+00:00")) <= as_of
                and (
                    rel["effective_to"] is None
                    or datetime.fromisoformat(rel["effective_to"].replace("Z", "+00:00")) > as_of
                )
            ]
            snapshot["as_of_date"] = as_of_date
        return snapshot


def run_projector(snapshot: Optional[Dict[str, Any]] = None) -> GraphReadModel:
    read_model = GraphReadModel()
    if snapshot:
        read_model.project_snapshot(snapshot)
    return read_model
