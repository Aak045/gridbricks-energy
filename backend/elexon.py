
import httpx
from typing import Any

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
TIMEOUT = 30.0


async def _fetch_records(
    endpoint: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    """Fetch records from Elexon and validate the response."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            f"{BASE_URL}{endpoint}",
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

    # Some Elexon endpoints return a list; others wrap records in "data".
    if isinstance(payload, dict):
        payload = payload.get("data")

    if not isinstance(payload, list):
        raise ValueError(
            f"Unexpected response format from {endpoint}"
        )

    if not all(isinstance(record, dict) for record in payload):
        raise ValueError(
            f"Unexpected record format from {endpoint}"
        )

    return payload


async def fetch_wind_actuals(
    settlement_date_from: str,
    settlement_date_to: str,
) -> list[dict[str, Any]]:
    """
    Fetch half-hourly actual generation by fuel type.

    Dates must use YYYY-MM-DD format.
    """
    if settlement_date_from > settlement_date_to:
        raise ValueError(
            "Start date must not be after end date"
        )

    params = {
        "settlementDateFrom": settlement_date_from,
        "settlementDateTo": settlement_date_to,
        "fuelType": "WIND",
    }

    return await _fetch_records(
        "/datasets/FUELHH/stream",
        params,
    )


async def fetch_wind_forecasts(
    publish_date_from: str | None = None,
    publish_date_to: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch wind forecasts, optionally filtered by publication time."""
    params: dict[str, str] = {}

    if publish_date_from:
        params["publishDateTimeFrom"] = publish_date_from

    if publish_date_to:
        params["publishDateTimeTo"] = publish_date_to

    if (
        publish_date_from
        and publish_date_to
        and publish_date_from > publish_date_to
    ):
        raise ValueError(
            "Publication start must not be after publication end"
        )

    return await _fetch_records(
        "/datasets/WINDFOR/stream",
        params,
    )
