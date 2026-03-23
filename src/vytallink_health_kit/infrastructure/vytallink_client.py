from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import httpx

from vytallink_health_kit.domain.entities import (
    ActivityRecord,
    HealthData,
    HRRecord,
    SleepRecord,
)

if TYPE_CHECKING:
    from vytallink_health_kit.infrastructure.settings import VytalLinkSettings

DATE_KEYS = ("date", "day", "recorded_on", "measurement_date", "start_date")
LIST_CONTAINER_KEYS = ("data", "items", "results", "records", "measurements")


class VytalLinkClientError(Exception):
    """Base error raised by the VytalLink REST adapter."""


class VytalLinkAuthenticationError(VytalLinkClientError):
    """Raised when VytalLink authentication fails."""


class VytalLinkResponseError(VytalLinkClientError):
    """Raised when the VytalLink response cannot be parsed."""


class VytalLinkRESTClient:
    """Fetch and normalize seven-day health data from the VytalLink REST API."""

    def __init__(
        self, settings: VytalLinkSettings, http_client: httpx.Client | None = None
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client(
            base_url=str(settings.base_url).rstrip("/"),
            timeout=settings.timeout_seconds,
        )
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._http_client.close()

    def fetch_window(self, *, end_date: date, days: int) -> HealthData:
        window = [
            end_date - timedelta(days=offset) for offset in range(days - 1, -1, -1)
        ]
        start_date = window[0]

        sleep_payload = self._get_json(self._settings.sleep_path, start_date, end_date)
        hr_payload = self._get_json(
            self._settings.heart_rate_path, start_date, end_date
        )
        activity_payload = self._get_json(
            self._settings.activity_path, start_date, end_date
        )

        return HealthData(
            days=window,
            sleep=self._build_sleep_map(window, sleep_payload),
            heart_rate=self._build_hr_map(window, hr_payload),
            activity=self._build_activity_map(window, activity_payload),
        )

    def _get_json(self, path: str, start_date: date, end_date: date) -> Any:
        try:
            response = self._http_client.get(
                path,
                params=self._build_query_params(start_date, end_date),
                headers=self._build_headers(),
            )
        except httpx.HTTPError as exc:
            raise VytalLinkClientError(
                f"Failed to reach VytalLink endpoint '{path}': {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise VytalLinkAuthenticationError(
                "VytalLink rejected the provided credentials. Check VYTALLINK_WORD and VYTALLINK_CODE."
            )
        if response.is_error:
            raise VytalLinkClientError(
                f"VytalLink endpoint '{path}' returned {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise VytalLinkResponseError(
                f"VytalLink endpoint '{path}' did not return valid JSON."
            ) from exc

    def _build_query_params(self, start_date: date, end_date: date) -> dict[str, Any]:
        params: dict[str, Any] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        if self._settings.word:
            params["word"] = self._settings.word
        if self._settings.code:
            params["code"] = self._settings.code
        return params

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._settings.word:
            headers["X-VytalLink-Word"] = self._settings.word
        if self._settings.code:
            headers["X-VytalLink-Code"] = self._settings.code
        return headers

    def _build_sleep_map(
        self, window: list[date], payload: Any
    ) -> dict[str, SleepRecord]:
        mapped = {day.isoformat(): SleepRecord(date=day) for day in window}
        for item in _extract_items(payload):
            day = _coerce_date(_pick_value(item, DATE_KEYS))
            if day is None or day.isoformat() not in mapped:
                continue
            mapped[day.isoformat()] = SleepRecord(
                date=day,
                total_minutes=_coerce_int(
                    _pick_value(
                        item,
                        (
                            "total_minutes",
                            "total",
                            "minutes_asleep",
                            "sleep_minutes",
                            "duration_minutes",
                        ),
                    )
                ),
                deep_minutes=_coerce_int(
                    _pick_value(item, ("deep_minutes", "deep", "deep_sleep_minutes"))
                ),
                rem_minutes=_coerce_int(
                    _pick_value(item, ("rem_minutes", "rem", "rem_sleep_minutes"))
                ),
                light_minutes=_coerce_int(
                    _pick_value(item, ("light_minutes", "light", "light_sleep_minutes"))
                ),
                awake_minutes=_coerce_int(
                    _pick_value(item, ("awake_minutes", "awake", "awake_time_minutes"))
                ),
            )
        return mapped

    def _build_hr_map(self, window: list[date], payload: Any) -> dict[str, HRRecord]:
        mapped = {day.isoformat(): HRRecord(date=day) for day in window}
        for item in _extract_items(payload):
            day = _coerce_date(_pick_value(item, DATE_KEYS))
            if day is None or day.isoformat() not in mapped:
                continue
            mapped[day.isoformat()] = HRRecord(
                date=day,
                resting_bpm=_coerce_float(
                    _pick_value(
                        item, ("resting_bpm", "resting_hr", "restingHeartRate", "bpm")
                    )
                ),
            )
        return mapped

    def _build_activity_map(
        self, window: list[date], payload: Any
    ) -> dict[str, ActivityRecord]:
        mapped = {day.isoformat(): ActivityRecord(date=day) for day in window}
        for item in _extract_items(payload):
            day = _coerce_date(_pick_value(item, DATE_KEYS))
            if day is None or day.isoformat() not in mapped:
                continue
            mapped[day.isoformat()] = ActivityRecord(
                date=day,
                steps=_coerce_int(
                    _pick_value(item, ("steps", "step_count", "daily_steps"))
                ),
                active_calories=_coerce_int(
                    _pick_value(
                        item,
                        (
                            "active_calories",
                            "calories",
                            "activeCalories",
                            "activity_calories",
                        ),
                    )
                ),
                exercise_minutes=_coerce_int(
                    _pick_value(
                        item,
                        (
                            "exercise_minutes",
                            "active_minutes",
                            "exerciseMinutes",
                            "minutes",
                        ),
                    )
                ),
            )
        return mapped


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in LIST_CONTAINER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        if payload and all(isinstance(value, dict) for value in payload.values()):
            items: list[dict[str, Any]] = []
            for key, value in payload.items():
                if _coerce_date(key) is None:
                    continue
                items.append({"date": key, **value})
            if items:
                return items

    raise VytalLinkResponseError(
        "Unsupported VytalLink payload shape. Expected a list or a dictionary containing records."
    )


def _pick_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in item:
            return item[key]
    return None


def _coerce_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
