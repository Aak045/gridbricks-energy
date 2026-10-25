
from datetime import date, datetime, time, timedelta, timezone
from math import sqrt

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from elexon import fetch_wind_forecasts, fetch_wind_actuals


app = FastAPI(
    title="Gridbricks Energy API",
    description="Wind generation forecast and accuracy analysis",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "gridbricks-energy-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/forecast/wind")
async def get_wind_forecast():
    try:
        data = await fetch_wind_forecasts()
        return {"count": len(data), "data": data}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch wind forecast data: {exc}",
        ) from exc


@app.get("/api/actuals/wind")
async def get_wind_actuals(
    settlement_date_from: date = Query(...),
    settlement_date_to: date = Query(...),
):
    if settlement_date_from > settlement_date_to:
        raise HTTPException(
            status_code=400,
            detail="Start date must not be after end date",
        )

    try:
        data = await fetch_wind_actuals(
            settlement_date_from=settlement_date_from.isoformat(),
            settlement_date_to=settlement_date_to.isoformat(),
        )
        return {"count": len(data), "data": data}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch actual wind generation: {exc}",
        ) from exc



@app.get("/api/analysis/wind-accuracy")
async def get_wind_accuracy(
    settlement_date_from: date = Query(...),
    settlement_date_to: date = Query(...),
):
    if settlement_date_from > settlement_date_to:
        raise HTTPException(
            status_code=400,
            detail="Start date must not be after end date",
        )

    try:
        actuals = await fetch_wind_actuals(
            settlement_date_from=settlement_date_from.isoformat(),
            settlement_date_to=settlement_date_to.isoformat(),
        )

        # Keep actual readings belonging to the requested UK settlement dates.
        # Elexon's settlementDate is not necessarily the UTC calendar date.
        actual_by_time = {}

        for row in actuals:
            if not row.get("startTime") or row.get("generation") is None:
                continue

            settlement_day = row.get("settlementDate")
            if settlement_day:
                if not (
                    settlement_date_from.isoformat()
                    <= settlement_day
                    <= settlement_date_to.isoformat()
                ):
                    continue

            target = parse_timestamp(row["startTime"])
            generation = float(row["generation"])

            if target in actual_by_time:
                if actual_by_time[target] != generation:
                    raise ValueError(
                        f"Conflicting actual readings for {target.isoformat()}"
                    )
                continue

            actual_by_time[target] = generation

        # Aggregate the two half-hourly readings into an hourly average.
        # This assumes the hourly forecast is intended to represent an average.
        readings_by_hour = {}

        for timestamp, generation in actual_by_time.items():
            hour_start = timestamp.replace(
                minute=0, second=0, microsecond=0
            )
            readings_by_hour.setdefault(hour_start, {})[
                timestamp.minute
            ] = generation

        hourly_actuals = {}

        for hour_start, readings in readings_by_hour.items():
            if 0 in readings and 30 in readings:
                hourly_actuals[hour_start] = (
                    readings[0] + readings[30]
                ) / 2

        if not hourly_actuals:
            return {
                "settlementDateFrom": settlement_date_from.isoformat(),
                "settlementDateTo": settlement_date_to.isoformat(),
                "forecastRecordsReceived": 0,
                "actualRecordsReceived": len(actuals),
                "matchedPeriods": 0,
                "metrics": {
                    "mae": None,
                    "rmse": None,
                    "mapePercent": None,
                },
                "data": [],
                "message": "No complete hourly actual periods were available.",
            }

        publish_from = datetime.combine(
            settlement_date_from - timedelta(days=2),
            time.min,
            tzinfo=timezone.utc,
        )
        publish_to = datetime.combine(
            settlement_date_to + timedelta(days=1),
            time.max,
            tzinfo=timezone.utc,
        )

        forecasts = await fetch_wind_forecasts(
            publish_date_from=publish_from.isoformat().replace(
                "+00:00", "Z"
            ),
            publish_date_to=publish_to.isoformat().replace(
                "+00:00", "Z"
            ),
        )

        # Choose the latest forecast published strictly before each target hour.
        selected = {}

        for row in forecasts:
            if (
                not row.get("startTime")
                or not row.get("publishTime")
                or row.get("generation") is None
            ):
                continue

            target = parse_timestamp(row["startTime"])
            published = parse_timestamp(row["publishTime"])

            if target not in hourly_actuals or published >= target:
                continue

            previous = selected.get(target)

            if previous is None or published > previous["published"]:
                selected[target] = {
                    "published": published,
                    "forecast": float(row["generation"]),
                }

        matched = []

        for target in sorted(selected):
            forecast_value = selected[target]["forecast"]
            actual_value = hourly_actuals[target]
            error = forecast_value - actual_value

            matched.append({
                "startTime": target.isoformat(),
                "publishTime": selected[target]["published"].isoformat(),
                "forecast": forecast_value,
                "actual": actual_value,
                "error": round(error, 3),
                "absoluteError": round(abs(error), 3),
            })

        if matched:
            errors = [item["error"] for item in matched]
            absolute_errors = [abs(value) for value in errors]

            mae = sum(absolute_errors) / len(matched)
            rmse = sqrt(sum(value**2 for value in errors) / len(matched))

            nonzero_actuals = [
                item for item in matched if item["actual"] != 0
            ]

            mape = (
                sum(
                    abs(item["error"] / item["actual"]) * 100
                    for item in nonzero_actuals
                ) / len(nonzero_actuals)
                if nonzero_actuals
                else None
            )
        else:
            mae = rmse = mape = None

        return {
            "settlementDateFrom": settlement_date_from.isoformat(),
            "settlementDateTo": settlement_date_to.isoformat(),
            "forecastRecordsReceived": len(forecasts),
            "actualRecordsReceived": len(actuals),
            "matchedPeriods": len(matched),
            "metrics": {
                "mae": round(mae, 3) if mae is not None else None,
                "rmse": round(rmse, 3) if rmse is not None else None,
                "mapePercent": round(mape, 3) if mape is not None else None,
            },
            "data": matched,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to calculate wind forecast accuracy: {exc}",
        ) from exc
