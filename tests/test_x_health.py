from __future__ import annotations

import tempfile
from pathlib import Path

import httpx

from hot_monitor.config import Settings
from hot_monitor.database import Database
from hot_monitor.service import HotMonitorService


def _service_with_temp_db(*, token: str) -> HotMonitorService:
    db_path = Path(tempfile.gettempdir()) / "hot_monitor_test_x_health.db"
    settings = Settings(database_path=str(db_path), x_bearer_token=token)
    return HotMonitorService(db=Database(settings.database_path), settings=settings)


def test_x_health_disabled_without_token() -> None:
    service = _service_with_temp_db(token="")
    health = service.get_x_health()
    assert health["enabled"] is False
    assert health["status"] == "disabled"
    assert health["available"] is False
    assert health["last_error"] == "X_BEARER_TOKEN is empty"


def test_x_health_records_http_status_failure() -> None:
    service = _service_with_temp_db(token="test-token")

    request = httpx.Request("GET", "https://api.x.com/2/tweets/search/recent")
    response = httpx.Response(
        402,
        request=request,
        json={"errors": [{"message": "Payment Required"}]},
    )
    error = httpx.HTTPStatusError("402 Payment Required", request=request, response=response)

    def _raise_402():
        raise error

    items = service._safe_fetch_x_items("x_probe", _raise_402)
    assert items == []

    health = service.get_x_health()
    assert health["enabled"] is True
    assert health["status"] == "error"
    assert health["available"] is False
    assert health["failed_calls"] == 1
    assert health["last_error_code"] == "402"
    assert "x_probe: Payment Required" in health["last_error"]
