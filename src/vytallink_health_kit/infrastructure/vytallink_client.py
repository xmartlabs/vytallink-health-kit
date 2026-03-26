from __future__ import annotations

import logging
from datetime import date, timedelta
from time import perf_counter, sleep
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
import structlog
from opentelemetry.trace import Status, StatusCode
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from vytallink_health_kit.domain.entities import (
    ActivityRecord,
    HealthData,
    HRRecord,
    SleepRecord,
)
from vytallink_health_kit.infrastructure.observability import (
    get_tracer,
    get_vytallink_metrics,
)

if TYPE_CHECKING:
    from vytallink_health_kit.infrastructure.settings import VytalLinkSettings

logger = structlog.get_logger(__name__)
retry_logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
metrics = get_vytallink_metrics()

DATE_KEYS = (
    "date",
    "day",
    "recorded_on",
    "measurement_date",
    "start_date",
    "start_time",
    "date_from",
    "date_to",
    "timestamp",
    "time",
    "dateTime",
)
LIST_CONTAINER_KEYS = (
    "data",
    "items",
    "results",
    "records",
    "measurements",
    "healthData",
)


class VytalLinkClientError(Exception):
    """Base error raised by the VytalLink REST adapter."""


class VytalLinkAuthenticationError(VytalLinkClientError):
    """Raised when VytalLink authentication fails."""


class VytalLinkResponseError(VytalLinkClientError):
    """Raised when the VytalLink response cannot be parsed."""


class VytalLinkEndpointNotFoundError(VytalLinkClientError):
    """Raised when a configured endpoint does not exist in the current deployment."""

    def __init__(self, path: str, response_text: str) -> None:
        super().__init__(f"VytalLink endpoint '{path}' returned 404: {response_text}")
        self.path = path


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
        self._conversation_id = f"vytallink-health-kit-{uuid4()}"
        self._session_authenticated = False

    def close(self) -> None:
        if self._owns_client:
            self._http_client.close()

    def fetch_window(self, *, end_date: date, days: int) -> HealthData:
        window = [
            end_date - timedelta(days=offset) for offset in range(days - 1, -1, -1)
        ]
        start_date = window[0]

        if self._settings.api_mode == "metrics":
            return self._fetch_metrics_window(window, start_date, end_date)

        try:
            return self._fetch_legacy_window(window, start_date, end_date)
        except VytalLinkEndpointNotFoundError:
            if self._settings.api_mode != "auto":
                raise
            return self._fetch_metrics_window(window, start_date, end_date)

    def _fetch_legacy_window(
        self, window: list[date], start_date: date, end_date: date
    ) -> HealthData:
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

    def _fetch_metrics_window(
        self, window: list[date], start_date: date, end_date: date
    ) -> HealthData:
        self._authenticate_metrics_session()

        sleep_payload = self._get_metric_json(
            value_type=self._normalize_metric_value_type(
                self._settings.sleep_value_type
            ),
            start_date=start_date,
            end_date=end_date,
        )
        self._pause_between_metric_requests("heart_rate")
        hr_payload = self._get_metric_json(
            value_type=self._normalize_metric_value_type(
                self._settings.heart_rate_value_type
            ),
            start_date=start_date,
            end_date=end_date,
        )
        self._pause_between_metric_requests("activity")
        activity_payload = self._get_metric_json(
            value_type=self._normalize_metric_value_type(
                self._settings.activity_value_type
            ),
            start_date=start_date,
            end_date=end_date,
        )

        return HealthData(
            days=window,
            sleep=self._build_sleep_map(window, sleep_payload),
            heart_rate=self._build_hr_map(window, hr_payload),
            activity=self._build_activity_map(window, activity_payload),
        )

    def _authenticate_metrics_session(self) -> None:
        if self._session_authenticated:
            return

        if not self._settings.word or not self._settings.code:
            raise VytalLinkAuthenticationError(
                "The metrics API requires VYTALLINK_WORD and VYTALLINK_CODE for direct login."
            )

        try:
            response = self._request(
                method="POST",
                path=self._settings.direct_login_path,
                metric_name="direct_login",
                data={
                    "word": self._settings.word,
                    "code": self._settings.code,
                },
                headers=self._build_session_headers(),
            )
        except httpx.HTTPError as exc:
            raise VytalLinkClientError(
                f"Failed to reach VytalLink direct login endpoint '{self._settings.direct_login_path}': {exc}"
            ) from exc

        if response.status_code in (401, 403):
            detail = _extract_error_message(response)
            raise VytalLinkAuthenticationError(
                "VytalLink direct login rejected the provided credentials. "
                "Check VYTALLINK_WORD and VYTALLINK_CODE. "
                f"Server response: {detail}"
            )
        if response.status_code == 404:
            raise VytalLinkEndpointNotFoundError(
                self._settings.direct_login_path,
                response.text,
            )
        if response.is_error:
            raise VytalLinkClientError(
                "VytalLink direct login failed with "
                f"{response.status_code}: {_extract_error_message(response)}"
            )

        self._session_authenticated = True

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(retry_logger, logging.WARNING),
        reraise=True,
    )
    def _get_metric_json(
        self, *, value_type: str, start_date: date, end_date: date
    ) -> Any:
        params: dict[str, Any] = {
            "value_type": value_type,
            "start_time": f"{start_date.isoformat()}T00:00:00Z",
            "end_time": f"{end_date.isoformat()}T23:59:59Z",
        }
        if self._settings.metrics_group_by:
            params["group_by"] = self._settings.metrics_group_by.upper()
            params["statistic"] = self._resolve_metric_statistic(value_type)
        elif self._settings.metrics_statistic:
            params["statistic"] = self._settings.metrics_statistic.upper()

        try:
            response = self._request(
                method="GET",
                path=self._settings.metrics_path,
                metric_name=value_type.lower(),
                params=params,
                headers=self._build_session_headers(),
                timeout=self._settings.metrics_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise VytalLinkClientError(
                "Failed to reach VytalLink metrics endpoint "
                f"'{self._settings.metrics_path}' for value_type '{value_type}': {exc}. "
                "If the server is saturated, retry in a moment or increase VYTALLINK_METRICS_TIMEOUT_SECONDS."
            ) from exc

        if response.status_code in (401, 403):
            detail = _extract_error_message(response)
            raise VytalLinkAuthenticationError(
                "VytalLink metrics request was not authenticated. "
                f"Server response: {detail}"
            )
        if response.status_code == 404:
            raise VytalLinkEndpointNotFoundError(
                self._settings.metrics_path,
                response.text,
            )
        if response.is_error:
            raise VytalLinkClientError(
                "VytalLink metrics endpoint "
                f"'{self._settings.metrics_path}' returned {response.status_code}: {_extract_error_message(response)}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise VytalLinkResponseError(
                "VytalLink metrics endpoint "
                f"'{self._settings.metrics_path}' did not return valid JSON for value_type '{value_type}'."
            ) from exc

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(retry_logger, logging.WARNING),
        reraise=True,
    )
    def _get_json(self, path: str, start_date: date, end_date: date) -> Any:
        try:
            response = self._request(
                method="GET",
                path=path,
                metric_name=path.strip("/").replace("/", "_") or "root",
                params=self._build_query_params(start_date, end_date),
                headers=self._build_headers(),
                timeout=self._settings.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise VytalLinkClientError(
                f"Failed to reach VytalLink endpoint '{path}': {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise VytalLinkAuthenticationError(
                "VytalLink rejected the provided credentials. Check VYTALLINK_WORD and VYTALLINK_CODE."
            )
        if response.status_code == 404:
            raise VytalLinkEndpointNotFoundError(path, response.text)
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

    def _build_session_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "openai-conversation-id": self._conversation_id,
        }

    def _request(
        self,
        method: str,
        path: str,
        metric_name: str,
        **kwargs: Any,
    ) -> httpx.Response:
        start_time = perf_counter()
        logger.info(
            "vytallink_request_started",
            method=method,
            path=path,
            metric_name=metric_name,
        )

        with tracer.start_as_current_span(f"vytallink.{metric_name}") as span:
            span.set_attribute("http.request.method", method)
            span.set_attribute("url.path", path)
            span.set_attribute("vytallink.metric_name", metric_name)

            try:
                response = self._http_client.request(method, path, **kwargs)
            except Exception as exc:
                elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                metrics.duration_ms.record(
                    elapsed_ms,
                    {
                        "method": method,
                        "path": path,
                        "metric_name": metric_name,
                        "status": "error",
                    },
                )
                metrics.requests_total.add(
                    1,
                    {
                        "method": method,
                        "path": path,
                        "metric_name": metric_name,
                        "status": "error",
                    },
                )
                metrics.errors_total.add(
                    1,
                    {"method": method, "path": path, "metric_name": metric_name},
                )
                logger.exception(
                    "vytallink_request_failed",
                    method=method,
                    path=path,
                    metric_name=metric_name,
                    duration_ms=elapsed_ms,
                    error=str(exc),
                )
                raise

            elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
            span.set_attribute("http.response.status_code", response.status_code)
            if response.is_error:
                span.set_status(
                    Status(StatusCode.ERROR, f"HTTP {response.status_code}")
                )
            else:
                span.set_status(Status(StatusCode.OK))

            status = "error" if response.is_error else "success"
            metrics.duration_ms.record(
                elapsed_ms,
                {
                    "method": method,
                    "path": path,
                    "metric_name": metric_name,
                    "status": status,
                },
            )
            metrics.requests_total.add(
                1,
                {
                    "method": method,
                    "path": path,
                    "metric_name": metric_name,
                    "status": status,
                },
            )
            if response.is_error:
                metrics.errors_total.add(
                    1,
                    {
                        "method": method,
                        "path": path,
                        "metric_name": metric_name,
                    },
                )

            logger.info(
                "vytallink_request_completed",
                method=method,
                path=path,
                metric_name=metric_name,
                duration_ms=elapsed_ms,
                status_code=response.status_code,
                status=status,
            )
            return response

    def _pause_between_metric_requests(self, next_metric_name: str) -> None:
        interval = self._settings.metrics_request_interval_seconds
        if interval <= 0:
            return

        logger.info(
            "vytallink_request_spacing",
            next_metric_name=next_metric_name,
            sleep_seconds=interval,
        )
        sleep(interval)

    def _build_sleep_map(
        self, window: list[date], payload: Any
    ) -> dict[str, SleepRecord]:
        mapped = {day.isoformat(): SleepRecord(date=day) for day in window}
        for item in _extract_items(payload):
            day = _coerce_date(_pick_value(item, DATE_KEYS))
            if day is None or day.isoformat() not in mapped:
                continue
            if _pick_value(item, ("type",)):
                mapped[day.isoformat()] = _merge_sleep_metric_item(
                    mapped[day.isoformat()], item
                )
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
                            "value",
                            "metric_value",
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

        for key, record in mapped.items():
            if record.total_minutes is None:
                sleep_parts = [
                    record.deep_minutes,
                    record.rem_minutes,
                    record.light_minutes,
                ]
                if any(value is not None for value in sleep_parts):
                    mapped[key] = record.model_copy(
                        update={
                            "total_minutes": sum(value or 0 for value in sleep_parts)
                        }
                    )
        return mapped

    def _build_hr_map(self, window: list[date], payload: Any) -> dict[str, HRRecord]:
        mapped = {day.isoformat(): HRRecord(date=day) for day in window}
        for item in _extract_items(payload):
            day = _coerce_date(_pick_value(item, DATE_KEYS))
            if day is None or day.isoformat() not in mapped:
                continue
            metric_type = str(_pick_value(item, ("type",)) or "").upper()
            resting_value = _coerce_float(
                _pick_value(
                    item,
                    (
                        "resting_bpm",
                        "resting_hr",
                        "restingHeartRate",
                        "bpm",
                        "value",
                        "metric_value",
                    ),
                )
            )

            current = mapped[day.isoformat()]
            if metric_type == "RESTING_HEART_RATE" or current.resting_bpm is None:
                mapped[day.isoformat()] = HRRecord(date=day, resting_bpm=resting_value)
        return mapped

    def _build_activity_map(
        self, window: list[date], payload: Any
    ) -> dict[str, ActivityRecord]:
        mapped = {day.isoformat(): ActivityRecord(date=day) for day in window}
        for item in _extract_items(payload):
            day = _coerce_date(_pick_value(item, DATE_KEYS))
            if day is None or day.isoformat() not in mapped:
                continue
            current = mapped[day.isoformat()]
            mapped[day.isoformat()] = ActivityRecord(
                date=day,
                steps=_sum_optional_ints(
                    current.steps,
                    _coerce_int(
                        _pick_value(
                            item,
                            (
                                "steps",
                                "step_count",
                                "daily_steps",
                                "value",
                                "metric_value",
                            ),
                        )
                    ),
                ),
                active_calories=_sum_optional_ints(
                    current.active_calories,
                    _coerce_int(
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
                ),
                exercise_minutes=_sum_optional_ints(
                    current.exercise_minutes,
                    _coerce_int(
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
                ),
            )
        return mapped

    def _normalize_metric_value_type(self, value_type: str) -> str:
        return value_type.upper()

    def _resolve_metric_statistic(self, value_type: str) -> str:
        if self._settings.metrics_statistic:
            return self._settings.metrics_statistic.upper()

        if value_type == "HEART_RATE":
            return "AVERAGE"

        return "SUM"


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in LIST_CONTAINER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        if payload and all(_coerce_date(key) is not None for key in payload):
            items: list[dict[str, Any]] = []
            for key, value in payload.items():
                if isinstance(value, dict):
                    items.append({"date": key, **value})
                    continue
                items.append({"date": key, "value": value})
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


def _sum_optional_ints(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return int((left or 0) + (right or 0))


def _merge_sleep_metric_item(record: SleepRecord, item: dict[str, Any]) -> SleepRecord:
    metric_type = str(_pick_value(item, ("type",)) or "").upper()
    value = _coerce_int(_pick_value(item, ("value", "metric_value")))
    if value is None:
        return record

    updates: dict[str, int | None] = {}
    if metric_type == "SLEEP_ASLEEP":
        updates["total_minutes"] = value
    elif metric_type == "SLEEP_DEEP":
        updates["deep_minutes"] = _sum_optional_ints(record.deep_minutes, value)
    elif metric_type == "SLEEP_REM":
        updates["rem_minutes"] = _sum_optional_ints(record.rem_minutes, value)
    elif metric_type == "SLEEP_LIGHT":
        updates["light_minutes"] = _sum_optional_ints(record.light_minutes, value)
    elif metric_type == "SLEEP_AWAKE":
        updates["awake_minutes"] = _sum_optional_ints(record.awake_minutes, value)

    if not updates:
        return record
    return record.model_copy(update=updates)


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    if isinstance(payload, dict):
        for key in ("message", "detail", "error", "error_message"):
            value = payload.get(key)
            if value:
                return str(value)
    return response.text
