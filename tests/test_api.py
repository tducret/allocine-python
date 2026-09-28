from unittest.mock import Mock, call, patch

from allocine.api import AllocineApi


def test_rate_limit_uses_capped_exponential_backoff():
    api = AllocineApi(cache=False)
    rate_limited = [Mock(status_code=429) for _ in range(6)]
    success = Mock(status_code=200)
    api.session.get = Mock(side_effect=[*rate_limited, success])

    with patch("time.sleep") as sleep:
        response = api._fetch("https://example.com", 200)

    assert response is success
    assert sleep.call_args_list == [call(5), call(10), call(20), call(40), call(80), call(120)]
