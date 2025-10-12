import logging
from pathlib import Path
from typing import Any, Dict, List

from tinydb import Query, TinyDB


class KnowledgeBase:
    """Zarządza interakcjami z plikową bazą wiedzy (TinyDB)."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db = TinyDB(db_path)
        logging.info(
            "Baza Wiedzy połączona. Ścieżka: %s. Liczba wpisów: %s",
            db_path,
            len(self.db),
        )

    def add_record(self, record: Dict[str, Any]) -> None:
        """Dodaje nowy wpis analizy do bazy."""
        if "analysis_id" not in record:
            raise KeyError("Rekord bazy wiedzy musi zawierać pole 'analysis_id'.")
        self.db.insert(record)
        logging.info("Nowy rekord dodany do Bazy Wiedzy (ID: %s)", record["analysis_id"])

    def query_by_type(self, action_type: str) -> List[Dict[str, Any]]:
        """Wyszukuje analizy po typie akcji (node/docker)."""
        Action = Query()
        results = self.db.search(Action.action_manifests.any(Query().type == action_type))
        logging.info("Znaleziono %s akcji typu '%s'.", len(results), action_type)
        return results

    def close(self) -> None:
        """Zamyka połączenie z bazą."""
        self.db.close()

    def __enter__(self) -> "KnowledgeBase":  # pragma: no cover - prosty kontekst
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - prosty kontekst
        self.close()
