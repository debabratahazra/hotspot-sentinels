import logging
import math
import os
from typing import Literal, TypedDict

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import bigquery
from requests.exceptions import RequestException

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# Not GOOGLE_CLOUD_REGION: a BigQuery job must run where its data lives, and
# bigquery-public-data.noaa_gsod is US multi-region. Pinning asia-southeast1 fails every lookup.
BIGQUERY_LOCATION = os.getenv("BIGQUERY_LOCATION", "US")
GSOD_YEAR = os.getenv("NOAA_GSOD_YEAR", "2024")
FALLBACK_TEMP_C = 38.5
FALLBACK_AVG_TEMP_C = 32.5
QUERY_SUBMISSION_TIMEOUT_S = 5.0
QUERY_RESULT_TIMEOUT_S = 10.0
logger = logging.getLogger(__name__)
_client: bigquery.Client | None = None


class _ClimateClientError(RuntimeError):
    """BigQuery client configuration is unavailable."""


class TemperatureReading(TypedDict):
    station_id: str
    observation_date: str | None
    max_temp_c: float
    avg_temp_c: float
    source: Literal["bigquery", "fallback"]


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        try:
            _client = bigquery.Client(project=PROJECT_ID, location=BIGQUERY_LOCATION)
        except OSError:
            raise _ClimateClientError("BigQuery client configuration is unavailable.") from None
    return _client


def get_latest_temperature(station_id: str = "486980") -> TemperatureReading:
    """Return a JSON-ready GSOD reading with Celsius temperatures and provenance.

    NOAA_GSOD_YEAR selects the historical table (default 2024).
    The default station is Singapore Changi Airport.
    Fallback readings retain the requested station but have no observation date.
    Expected cloud failures degrade to fallback; programming errors propagate.
    """
    query = """
        SELECT stn AS station_id, max, temp,
               DATE(CAST(year AS INT64), CAST(mo AS INT64),
                    CAST(da AS INT64)) AS observation_date
        FROM `bigquery-public-data.noaa_gsod.gsod*`
        WHERE _TABLE_SUFFIX = @table_year
          AND stn = @station_id
          AND max IS NOT NULL
          AND max != 9999.9
                    AND temp IS NOT NULL
                    AND temp != 9999.9
                    AND NOT IS_NAN(max) AND NOT IS_INF(max)
                    AND NOT IS_NAN(temp) AND NOT IS_INF(temp)
                ORDER BY observation_date DESC
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("station_id", "STRING", station_id),
            bigquery.ScalarQueryParameter("table_year", "STRING", GSOD_YEAR),
        ]
    )
    fallback_reason = "empty_result"
    try:
        query_job = _get_client().query(
            query,
            job_config=job_config,
            timeout=QUERY_SUBMISSION_TIMEOUT_S,
            retry=None,
            job_retry=None,
        )
        for row in query_job.result(
            timeout=QUERY_RESULT_TIMEOUT_S, retry=None, job_retry=None
        ):
            if row.max is None or row.temp is None:
                fallback_reason = "null_temperature"
                continue
            try:
                max_f = float(row.max)
                avg_f = float(row.temp)
            except (ValueError, OverflowError) as error:
                fallback_reason = type(error).__name__
                continue
            if any(
                math.isclose(value, 9999.9, rel_tol=0, abs_tol=1e-6)
                for value in (max_f, avg_f)
            ):
                fallback_reason = "sentinel_temperature"
                continue
            if not all(math.isfinite(value) for value in (max_f, avg_f)):
                fallback_reason = "non_finite_temperature"
                continue
            if row.observation_date is None:
                fallback_reason = "missing_observation_date"
                continue
            reading: TemperatureReading = {
                "station_id": row.station_id,
                "observation_date": row.observation_date.isoformat(),
                "max_temp_c": round((max_f - 32) * 5.0 / 9.0, 1),
                "avg_temp_c": round((avg_f - 32) * 5.0 / 9.0, 1),
                "source": "bigquery",
            }
            logger.info("Fetched BigQuery telemetry: %.1f C", reading["max_temp_c"])
            return reading
    except (
        GoogleAPIError,
        GoogleAuthError,
        RequestException,
        _ClimateClientError,
        TimeoutError,
    ) as error:
        fallback_reason = type(error).__name__

    logger.warning(
        "Using fallback demo telemetry (%s): %.1f C", fallback_reason, FALLBACK_TEMP_C
    )
    return {
        "station_id": station_id,
        "observation_date": None,
        "max_temp_c": FALLBACK_TEMP_C,
        "avg_temp_c": FALLBACK_AVG_TEMP_C,
        "source": "fallback",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reading = get_latest_temperature()
    logger.info(
        "Ambient temperature: %.1f C (source=%s)",
        reading["max_temp_c"],
        reading["source"],
    )
