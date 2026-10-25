
import asyncio
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

from elexon import fetch_wind_actuals, fetch_wind_forecasts
from main import get_wind_accuracy, parse_timestamp


START_DATE = date(2026, 10, 21)
END_DATE = date(2026, 10, 22)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


async def main():
    # 1. Run the existing accuracy calculation.
    result = await get_wind_accuracy(
        settlement_date_from=START_DATE,
        settlement_date_to=END_DATE,
    )

    section("CURRENT ACCURACY RESULTS")
    print("Date range:", START_DATE, "to", END_DATE)
    print("Forecast records:", result["forecastRecordsReceived"])
    print("Actual records:", result["actualRecordsReceived"])
    print("Matched periods:", result["matchedPeriods"])
    print("Metrics:", result["metrics"])

    if result.get("message"):
        print("Message:", result["message"])

    # 2. Fetch raw actuals and forecasts for independent checks.
    section("FETCHING RAW DATA")

    actuals = await fetch_wind_actuals(
        settlement_date_from=START_DATE.isoformat(),
        settlement_date_to=END_DATE.isoformat(),
    )

    publish_from = datetime.combine(
        START_DATE,
        datetime.min.time(),
        tzinfo=timezone.utc,
    ).isoformat().replace("+00:00", "Z")

    publish_to = datetime.combine(
        END_DATE,
        datetime.max.time(),
        tzinfo=timezone.utc,
    ).isoformat().replace("+00:00", "Z")

    forecasts = await fetch_wind_forecasts(
        publish_date_from=publish_from,
        publish_date_to=publish_to,
    )

    print("Raw actual records:", len(actuals))
    print("Raw forecast records in publication window:", len(forecasts))

    # 3. Check the actual readings and interval coverage.
    section("ACTUAL DATA CHECKS")

    actual_by_time = {}

    for row in actuals:
        start_time = row.get("startTime")
        generation = row.get("generation")

        if not start_time or generation is None:
            continue

        try:
            timestamp = parse_timestamp(start_time)
            value = float(generation)
        except (ValueError, TypeError):
            continue

        actual_by_time.setdefault(timestamp, []).append(value)

    duplicate_actual_times = {
        timestamp: values
        for timestamp, values in actual_by_time.items()
        if len(values) > 1
    }

    print("Unique actual timestamps:", len(actual_by_time))
    print("Timestamps with duplicate records:", len(duplicate_actual_times))

    if duplicate_actual_times:
        for timestamp, values in list(duplicate_actual_times.items())[:5]:
            print("Duplicate:", timestamp.isoformat(), values)

    actual_minutes = Counter(
        timestamp.minute for timestamp in actual_by_time
    )
    print("Actual timestamp minute distribution:", dict(actual_minutes))

    print("\nFirst 6 actual records:")
    for row in actuals[:6]:
        print({
            "settlementDate": row.get("settlementDate"),
            "settlementPeriod": row.get("settlementPeriod"),
            "startTime": row.get("startTime"),
            "generation": row.get("generation"),
        })

    # 4. Check forecast publication timing and duplicate versions.
    section("FORECAST TIMING CHECKS")

    valid_forecasts = []
    invalid_forecasts = 0

    for row in forecasts:
        if (
            not row.get("startTime")
            or not row.get("publishTime")
            or row.get("generation") is None
        ):
            invalid_forecasts += 1
            continue

        try:
            target = parse_timestamp(row["startTime"])
            published = parse_timestamp(row["publishTime"])
            generation = float(row["generation"])
        except (ValueError, TypeError):
            invalid_forecasts += 1
            continue

        valid_forecasts.append({
            "target": target,
            "published": published,
            "generation": generation,
        })

    versions_by_target = defaultdict(list)

    for row in valid_forecasts:
        versions_by_target[row["target"]].append(row)

    duplicate_targets = {
        target: versions
        for target, versions in versions_by_target.items()
        if len(versions) > 1
    }

    before_target = [
        row for row in valid_forecasts
        if row["published"] < row["target"]
    ]

    at_or_after_target = [
        row for row in valid_forecasts
        if row["published"] >= row["target"]
    ]

    print("Valid forecast records:", len(valid_forecasts))
    print("Records missing/invalid required fields:", invalid_forecasts)
    print("Unique forecast target timestamps:", len(versions_by_target))
    print("Targets with multiple forecast versions:", len(duplicate_targets))
    print("Published before target:", len(before_target))
    print("Published at/after target:", len(at_or_after_target))

    if duplicate_targets:
        print("\nExamples of targets with multiple versions:")
        for target, versions in list(duplicate_targets.items())[:5]:
            print({
                "target": target.isoformat(),
                "versions": len(versions),
                "publishTimes": [
                    item["published"].isoformat()
                    for item in sorted(
                        versions,
                        key=lambda item: item["published"],
                    )[:5]
                ],
            })

    if at_or_after_target:
        print("\nExamples published at/after target:")
        for row in at_or_after_target[:5]:
            print({
                "startTime": row["target"].isoformat(),
                "publishTime": row["published"].isoformat(),
                "generation": row["generation"],
            })

    # 5. Validate the records actually used by the accuracy calculation.
    section("MATCHED PERIOD VALIDATION")

    matched = result.get("data", [])
    matched_targets = set()
    bad_matched_rows = []

    for row in matched:
        try:
            target = parse_timestamp(row["startTime"])
            published = parse_timestamp(row["publishTime"])
            forecast = float(row["forecast"])
            actual = float(row["actual"])

            if published >= target:
                bad_matched_rows.append({
                    "reason": "Forecast was not published before target",
                    "row": row,
                })

            if not all(
                value == value and abs(value) != float("inf")
                for value in (forecast, actual)
            ):
                bad_matched_rows.append({
                    "reason": "Non-finite forecast or actual",
                    "row": row,
                })

            if target in matched_targets:
                bad_matched_rows.append({
                    "reason": "Duplicate matched target",
                    "row": row,
                })

            matched_targets.add(target)

        except (KeyError, ValueError, TypeError):
            bad_matched_rows.append({
                "reason": "Missing or invalid matched field",
                "row": row,
            })

    print("Matched rows checked:", len(matched))
    print("Unique matched targets:", len(matched_targets))
    print("Matched rows with validation issues:", len(bad_matched_rows))

    for item in bad_matched_rows[:10]:
        print(item)

    print("\nFirst 5 matched periods:")
    for row in matched[:5]:
        print(row)

    # 6. Summarize what the diagnostic establishes.
    section("DIAGNOSTIC SUMMARY")

    print(
        "PASS: Every matched forecast was published before its target."
        if matched and not any(
            item["reason"] == "Forecast was not published before target"
            for item in bad_matched_rows
        )
        else "CHECK: Review forecast timing validation above."
    )

    print(
        "PASS: No duplicate matched target timestamps."
        if len(matched_targets) == len(matched) and not any(
            item["reason"] == "Duplicate matched target"
            for item in bad_matched_rows
        )
        else "CHECK: Review duplicate or invalid matched rows above."
    )

    print(
        "NOTE: This diagnostic does not establish whether averaging "
        "half-hourly actuals is the correct comparison for WINDFOR."
    )


if __name__ == "__main__":
    asyncio.run(main())
