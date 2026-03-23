from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from vytallink_health_kit.infrastructure.settings import VytalLinkSettings
from vytallink_health_kit.infrastructure.vytallink_client import (
    VytalLinkAuthenticationError,
    VytalLinkRESTClient,
)


def test_vytallink_client_parses_supported_payload_shapes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sleep":
            payload = {
                "data": [
                    {"date": "2026-03-22", "total_minutes": 420, "awake_minutes": 30},
                    {"date": "2026-03-23", "total_minutes": 400, "awake_minutes": 40},
                ]
            }
        elif request.url.path == "/heart-rate/resting":
            payload = {
                "2026-03-22": {"resting_bpm": 56},
                "2026-03-23": {"resting_bpm": 57},
            }
        else:
            payload = [
                {"date": "2026-03-22", "steps": 9000, "active_calories": 300},
                {"date": "2026-03-23", "steps": 8500, "active_calories": 280},
            ]
        return httpx.Response(200, text=json.dumps(payload))

    transport = httpx.MockTransport(handler)
    settings = VytalLinkSettings(
        base_url="https://example.test", word="demo", code="demo"
    )
    client = VytalLinkRESTClient(
        settings=settings,
        http_client=httpx.Client(base_url="https://example.test", transport=transport),
    )

    data = client.fetch_window(end_date=date(2026, 3, 23), days=2)

    assert data.available_days == 2
    assert data.sleep["2026-03-23"].total_minutes == 400
    assert data.heart_rate["2026-03-22"].resting_bpm == 56.0
    assert data.activity["2026-03-22"].active_calories == 300


def test_vytallink_client_raises_authentication_error() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(401, json={"detail": "nope"})
    )
    settings = VytalLinkSettings(base_url="https://example.test")
    client = VytalLinkRESTClient(
        settings=settings,
        http_client=httpx.Client(base_url="https://example.test", transport=transport),
    )

    with pytest.raises(VytalLinkAuthenticationError):
        client.fetch_window(end_date=date(2026, 3, 23), days=7)
