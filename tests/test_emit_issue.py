import json
import pathlib
import pytest
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import emit_issue


def test_write_issue_valid(monkeypatch, tmp_path):
    monkeypatch.setattr(emit_issue, 'ROOT', tmp_path)
    doc = {
        'issue_id': 'a' * 40,
        'source': 'src',
        'title': 'ok',
    }
    path = emit_issue.write_issue(doc)
    expected = tmp_path / 'src' / 'unknown' / (doc['issue_id'] + '.json')
    assert path == expected
    assert path.exists()
    data = json.loads(path.read_text('utf-8'))
    assert data['issue_id'] == doc['issue_id']


def test_write_issue_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(emit_issue, 'ROOT', tmp_path)
    doc = {
        'issue_id': '../../../etc/passwd',
        'source': 'src',
        'title': 'bad',
    }
    with pytest.raises(ValueError):
        emit_issue.write_issue(doc)
    assert not list(tmp_path.rglob('passwd'))


def test_write_issues_batch_success(monkeypatch, tmp_path):
    monkeypatch.setattr(emit_issue, 'ROOT', tmp_path)
    docs = [
        {'issue_id': 'a' * 40, 'source': 'src', 'title': 'one'},
        {'issue_id': 'b' * 40, 'source': 'src', 'title': 'two'},
    ]
    paths = emit_issue.write_issues_batch(docs)
    assert len(paths) == 2
    for doc in docs:
        path = tmp_path / 'src' / 'unknown' / (doc['issue_id'] + '.json')
        assert path.exists()


def test_write_issues_batch_atomic(monkeypatch, tmp_path):
    monkeypatch.setattr(emit_issue, 'ROOT', tmp_path)
    docs = [
        {'issue_id': 'c' * 40, 'source': 'src', 'title': 'ok'},
        {'issue_id': 'invalid', 'source': 'src', 'title': 'bad'},
    ]
    with pytest.raises(ValueError):
        emit_issue.write_issues_batch(docs)
    assert not list(tmp_path.rglob('*.json'))


def test_write_issue_too_big(monkeypatch, tmp_path):
    monkeypatch.setattr(emit_issue, 'ROOT', tmp_path)
    monkeypatch.setattr(emit_issue, 'MAX_JSON_BYTES', 10)
    doc = {
        'issue_id': 'a' * 40,
        'source': 'src',
        'title': 'ok',
        'payload': 'x' * 20,
    }
    with pytest.raises(ValueError):
        emit_issue.write_issue(doc)
    assert not list(tmp_path.rglob('*.json'))


def test_write_issues_batch_too_big(monkeypatch, tmp_path):
    monkeypatch.setattr(emit_issue, 'ROOT', tmp_path)
    monkeypatch.setattr(emit_issue, 'MAX_JSON_BYTES', 10)
    docs = [
        {
            'issue_id': 'a' * 40,
            'source': 'src',
            'title': 'ok',
            'payload': 'x' * 20,
        },
        {'issue_id': 'b' * 40, 'source': 'src', 'title': 'ok'},
    ]
    with pytest.raises(ValueError):
        emit_issue.write_issues_batch(docs)
    assert not list(tmp_path.rglob('*.json'))
