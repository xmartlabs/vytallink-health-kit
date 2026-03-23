from __future__ import annotations

import json
from datetime import date
from urllib.parse import parse_qs

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


def test_vytallink_client_falls_back_to_metrics_api_when_legacy_paths_are_missing() -> (
    None
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/sleep":
            return httpx.Response(404, json={"detail": "Not Found"})

        if request.method == "POST" and request.url.path == "/api/direct-login":
            assert request.headers["openai-conversation-id"].startswith(
                "vytallink-health-kit-"
            )
            return httpx.Response(200, json={"success": True})

        if request.method == "GET" and request.url.path == "/api/get_health_metrics":
            params = parse_qs(request.url.query.decode())
            value_type = params["value_type"][0]
            assert params["group_by"] == ["DAY"]

            payloads = {
                "SLEEP": {
                    "healthData": [
                        {
                            "date_from": "2026-03-22T00:00:00.000Z",
                            "type": "SLEEP_DEEP",
                            "value": 120,
                        },
                        {
                            "date_from": "2026-03-22T00:00:00.000Z",
                            "type": "SLEEP_LIGHT",
                            "value": 250,
                        },
                        {
                            "date_from": "2026-03-22T00:00:00.000Z",
                            "type": "SLEEP_REM",
                            "value": 50,
                        },
                        {
                            "date_from": "2026-03-22T00:00:00.000Z",
                            "type": "SLEEP_AWAKE",
                            "value": 30,
                        },
                        {
                            "date_from": "2026-03-23T00:00:00.000Z",
                            "type": "SLEEP_ASLEEP",
                            "value": 400,
                        },
                        {
                            "date_from": "2026-03-23T00:00:00.000Z",
                            "type": "SLEEP_AWAKE",
                            "value": 40,
                        },
                    ]
                },
                "HEART_RATE": {
                    "healthData": [
                        {
                            "date_from": "2026-03-22T00:00:00.000Z",
                            "type": "HEART_RATE",
                            "value": 68,
                        },
                        {
                            "date_from": "2026-03-22T00:00:00.000Z",
                            "type": "RESTING_HEART_RATE",
                            "value": 56,
                        },
                        {
                            "date_from": "2026-03-23T00:00:00.000Z",
                            "type": "RESTING_HEART_RATE",
                            "value": 57,
                        },
                    ]
                },
                "STEPS": {
                    "healthData": [
                        {"date_from": "2026-03-22T00:00:00.000Z", "value": 5000},
                        {"date_from": "2026-03-22T00:00:00.000Z", "value": 4000},
                        {"date_from": "2026-03-23T00:00:00.000Z", "value": 8500},
                    ]
                },
            }
            if value_type == "HEART_RATE":
                assert params["statistic"] == ["AVERAGE"]
            else:
                assert params["statistic"] == ["SUM"]
            return httpx.Response(200, json=payloads[value_type])

        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    settings = VytalLinkSettings(
        base_url="https://example.test",
        word="demo",
        code="demo",
        sleep_value_type="SLEEP",
        heart_rate_value_type="HEART_RATE",
        activity_value_type="STEPS",
        metrics_group_by="DAY",
    )
    client = VytalLinkRESTClient(
        settings=settings,
        http_client=httpx.Client(base_url="https://example.test", transport=transport),
    )

    data = client.fetch_window(end_date=date(2026, 3, 23), days=2)

    assert data.available_days == 2
    assert data.sleep["2026-03-23"].total_minutes == 400
    assert data.sleep["2026-03-22"].awake_minutes == 30
    assert data.heart_rate["2026-03-22"].resting_bpm == 56.0
    assert data.activity["2026-03-22"].steps == 9000


def test_vytallink_client_surfaces_direct_login_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/sleep":
            return httpx.Response(404, json={"detail": "Not Found"})

        if request.method == "POST" and request.url.path == "/api/direct-login":
            return httpx.Response(
                401,
                json={
                    "success": False,
                    "error": "invalid_credentials",
                    "message": "Invalid word/code combination",
                },
            )

        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    settings = VytalLinkSettings(
        base_url="https://example.test",
        word="demo",
        code="bad-code",
        sleep_value_type="SLEEP",
        heart_rate_value_type="HEART_RATE",
        activity_value_type="STEPS",
        metrics_group_by="DAY",
    )
    client = VytalLinkRESTClient(
        settings=settings,
        http_client=httpx.Client(base_url="https://example.test", transport=transport),
    )

    with pytest.raises(VytalLinkAuthenticationError, match="direct login rejected"):
        client.fetch_window(end_date=date(2026, 3, 23), days=2)
