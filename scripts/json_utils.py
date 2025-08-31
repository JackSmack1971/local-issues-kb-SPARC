import json
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 1_000_000


def load_json(path: Path) -> Any:
    size = path.stat().st_size
    if size > MAX_JSON_BYTES:
        raise ValueError(f'JSON file {path} exceeds {MAX_JSON_BYTES} bytes (size={size})')
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)
