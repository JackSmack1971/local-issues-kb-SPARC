from pathlib import Path
import json
import pytest
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from json_utils import MAX_JSON_BYTES, load_json


def test_load_json_rejects_oversized_file(tmp_path: Path) -> None:
    big_value = 'x' * MAX_JSON_BYTES
    path = tmp_path / 'big.json'
    path.write_text(json.dumps({'data': big_value}), encoding='utf-8')
    assert path.stat().st_size > MAX_JSON_BYTES
    with pytest.raises(ValueError):
        load_json(path)
