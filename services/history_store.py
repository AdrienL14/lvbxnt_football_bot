from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

DATA_PATH = Path("data")
DATA_PATH.mkdir(exist_ok=True)
HISTORY_FILE = DATA_PATH / "analysis_history.json"


def _read() -> List[Dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(items: List[Dict]) -> None:
    HISTORY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def append_history(item: Dict) -> None:
    items = _read()
    items.insert(0, item)
    _write(items[:100])


def read_history() -> List[Dict]:
    return _read()
