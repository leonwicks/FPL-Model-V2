import json

import pytest

from football_data.common.http import HttpClient


@pytest.mark.integration
def test_live_fpl_bootstrap_smoke():
    try:
        with HttpClient("fpl") as client:
            payload = client.get(
                "https://fantasy.premierleague.com/api/bootstrap-static/"
            )
    except RuntimeError as exc:
        pytest.skip(f"live network unavailable: {exc}")
    response = json.loads(payload.content)
    assert response["elements"]
    assert response["teams"]
