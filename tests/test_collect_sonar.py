import pathlib
import sys
import requests
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import collect_sonar


def test_fetch_with_retry_success(monkeypatch):
    session = requests.Session()
    attempts = {'count': 0}

    class DummyResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {'rules': []}

    def fake_get(url, params, timeout):
        attempts['count'] += 1
        if attempts['count'] < 2:
            raise requests.RequestException('boom')
        return DummyResponse()

    monkeypatch.setattr(session, 'get', fake_get)
    monkeypatch.setattr(collect_sonar.time, 'sleep', lambda *_: None)
    logger = collect_sonar.get_logger('test')
    resp = collect_sonar.fetch_with_retry(session, 'http://example', {}, logger, max_attempts=3)
    assert attempts['count'] == 2
    assert resp.json() == {'rules': []}


def test_fetch_with_retry_failure(monkeypatch):
    session = requests.Session()

    def always_fail(url, params, timeout):
        raise requests.RequestException('nope')

    monkeypatch.setattr(session, 'get', always_fail)
    monkeypatch.setattr(collect_sonar.time, 'sleep', lambda *_: None)
    logger = collect_sonar.get_logger('test')
    with pytest.raises(requests.RequestException):
        collect_sonar.fetch_with_retry(session, 'http://example', {}, logger, max_attempts=2)


def test_invalid_base_url():
    with pytest.raises(ValueError):
        collect_sonar.parse_args(['--base', 'http://example.com'])


def test_unknown_language():
    with pytest.raises(ValueError):
        collect_sonar.parse_args(['--langs', 'java,foo'])


@pytest.mark.parametrize(
    'argv',
    [
        ['--page-size', '0'],
        ['--page-size', '501'],
        ['--limit', '0'],
        ['--limit', '5001'],
    ],
)
def test_numeric_range(argv):
    with pytest.raises(ValueError):
        collect_sonar.parse_args(argv)
