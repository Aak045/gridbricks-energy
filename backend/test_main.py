from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def sample_actuals():
    return [
        {
            "settlementDate": "2026-10-21",
            "startTime": "2026-10-21T00:00:00Z",
            "generation": 10,
        },
        {
            "settlementDate": "2026-10-21",
            "startTime": "2026-10-21T00:30:00Z",
            "generation": 20,
        },
    ]


def sample_forecasts():
    return [
        {
            "startTime": "2026-10-21T00:00:00Z",
            "publishTime": "2026-10-20T22:00:00Z",
            "generation": 14,
        },
        {
            "startTime": "2026-10-21T00:00:00Z",
            "publishTime": "2026-10-20T23:00:00Z",
            "generation": 18,
        },
        {
            "startTime": "2026-10-21T00:00:00Z",
            "publishTime": "2026-10-21T00:00:00Z",
            "generation": 999,
        },
    ]


def mock_data(monkeypatch, actuals=None, forecasts=None):
    async def fake_actuals(**kwargs):
        return sample_actuals() if actuals is None else actuals

    async def fake_forecasts(**kwargs):
        return sample_forecasts() if forecasts is None else forecasts

    monkeypatch.setattr(main, "fetch_wind_actuals", fake_actuals)
    monkeypatch.setattr(main, "fetch_wind_forecasts", fake_forecasts)


def test_accuracy_uses_latest_forecast_published_before_target(monkeypatch):
    mock_data(monkeypatch)

    response = client.get(
        "/api/analysis/wind-accuracy",
        params={
            "settlement_date_from": "2026-10-21",
            "settlement_date_to": "2026-10-21",
        },
    )

    assert response.status_code == 200
    result = response.json()

    assert result["matchedPeriods"] == 1
    assert result["data"][0]["forecast"] == 18
    assert result["data"][0]["actual"] == 15
    assert result["data"][0]["publishTime"] == "2026-10-20T23:00:00+00:00"


def test_accuracy_metrics_are_calculated_correctly(monkeypatch):
    mock_data(monkeypatch)

    response = client.get(
        "/api/analysis/wind-accuracy",
        params={
            "settlement_date_from": "2026-10-21",
            "settlement_date_to": "2026-10-21",
        },
    )

    metrics = response.json()["metrics"]

    assert metrics["mae"] == 3
    assert metrics["rmse"] == 3
    assert metrics["mapePercent"] == 20


def test_incomplete_hour_is_not_matched(monkeypatch):
    actuals = sample_actuals()[:1]
    mock_data(monkeypatch, actuals=actuals)

    response = client.get(
        "/api/analysis/wind-accuracy",
        params={
            "settlement_date_from": "2026-10-21",
            "settlement_date_to": "2026-10-21",
        },
    )

    assert response.status_code == 200
    assert response.json()["matchedPeriods"] == 0
    assert response.json()["metrics"]["mae"] is None


def test_reversed_date_range_returns_400():
    response = client.get(
        "/api/analysis/wind-accuracy",
        params={
            "settlement_date_from": "2026-10-22",
            "settlement_date_to": "2026-10-21",
        },
    )

    assert response.status_code == 400


def test_zero_actual_does_not_crash_mape(monkeypatch):
    actuals = [
        {
            "settlementDate": "2026-10-21",
            "startTime": "2026-10-21T00:00:00Z",
            "generation": 0,
        },
        {
            "settlementDate": "2026-10-21",
            "startTime": "2026-10-21T00:30:00Z",
            "generation": 0,
        },
    ]
    mock_data(monkeypatch, actuals=actuals)

    response = client.get(
        "/api/analysis/wind-accuracy",
        params={
            "settlement_date_from": "2026-10-21",
            "settlement_date_to": "2026-10-21",
        },
    )

    assert response.status_code == 200
    assert response.json()["metrics"]["mae"] == 18
    assert response.json()["metrics"]["mapePercent"] is None
