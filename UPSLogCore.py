"""Analyze parsed UPS log data for a toolset and forward results to UPSLogToCsv for output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, List, Optional

import pandas as pd

import eventLogCoding
import UPSLogToCsv

if TYPE_CHECKING:
    from UPSLogFinder import DataLogEntry, EventLogEntry

# Stress thresholds used by the datalog statistical summary (overridable per call).
TEMP_CRITICAL_THRESHOLD_C = 50.0
LOAD_OVERLOAD_THRESHOLD_PCT = 90.0
NOMINAL_FREQUENCY_HZ = 60.0

# Both the summary and the rolling graph only look at the trailing 7 days of datalog samples.
DATALOG_ANALYSIS_WINDOW = timedelta(days=7)

DATALOG_METRIC_COLUMNS = [
    "input_voltage",
    "output_voltage",
    "input_freq",
    "output_freq",
    "load_level",
    "temp",
    "battery_voltage",
    "battery_level",
]


@dataclass
class DatalogSummary:
    """Magnitude/extreme-focused statistical summary for one toolset's datalog (see time_series_summary_specification)."""

    sdx: str
    sample_count: int
    input_voltage_min: float
    input_voltage_max: float
    input_voltage_p1: float
    input_voltage_p99: float
    input_voltage_rms: float
    output_voltage_min: float
    output_voltage_max: float
    output_voltage_p1: float
    output_voltage_p99: float
    output_voltage_rms: float
    input_freq_max_deviation_hz: float
    output_freq_max_deviation_hz: float
    temp_max_c: float
    temp_time_above_threshold_min: float
    load_p95_pct: float
    load_time_in_overload_min: float
    battery_voltage_min: float
    battery_level_net_delta_pct: float
    battery_level_max_discharge_rate_pct_per_hr: float


@dataclass
class SdxAnalysis:
    sdx: str
    sample_count: int
    alarm_count: int
    datalog_summary: Optional[DatalogSummary] = None
    datalog_rolling_24h: Optional[pd.DataFrame] = None
    datalog_entries: List["DataLogEntry"] = field(default_factory=list)
    eventlog_entries: List["EventLogEntry"] = field(default_factory=list)


def decode_eventlog_entries(eventlog_entries: List["EventLogEntry"]) -> List["EventLogEntry"]:
    """Set each entry's severity (C/W/I) and replace its raw numeric alarm code with its description."""
    for entry in eventlog_entries:
        entry.severity = eventLogCoding.classify_alarm_severity(entry.alarm_code)
        entry.alarm_code = eventLogCoding.decode_alarm_code(entry.alarm_code)
    return eventlog_entries


def _datalog_frame(datalog_entries: List["DataLogEntry"], window: timedelta = DATALOG_ANALYSIS_WINDOW) -> pd.DataFrame:
    """Build a sorted datalog frame limited to the trailing `window` of samples."""
    df = pd.DataFrame([e.__dict__ for e in datalog_entries]).sort_values("timestamp").reset_index(drop=True)
    if not df.empty:
        cutoff = df["timestamp"].max() - window
        df = df[df["timestamp"] >= cutoff].reset_index(drop=True)
    return df


def _rms(series: pd.Series) -> float:
    return float((series.pow(2).mean()) ** 0.5)


def _duration_above_threshold_min(df: pd.DataFrame, column: str, threshold: float) -> float:
    """Minutes spent above threshold, weighting each sample by the time until the next sample."""
    if df.empty:
        return 0.0
    minutes_to_next = df["timestamp"].diff().shift(-1).dt.total_seconds().fillna(0) / 60.0
    above = df[column] > threshold
    return float(minutes_to_next[above].sum())


def _max_discharge_rate_pct_per_hr(df: pd.DataFrame) -> float:
    """Largest drop in battery level per hour between consecutive samples."""
    hours = df["timestamp"].diff().dt.total_seconds() / 3600.0
    drop_pct = -df["battery_level"].diff()
    rates = (drop_pct / hours).replace([float("inf"), float("-inf")], pd.NA).dropna()
    positive_rates = rates[rates > 0]
    return float(positive_rates.max()) if not positive_rates.empty else 0.0


def summarize_datalog(
    datalog_entries: List["DataLogEntry"],
    *,
    temp_threshold_c: float = TEMP_CRITICAL_THRESHOLD_C,
    load_threshold_pct: float = LOAD_OVERLOAD_THRESHOLD_PCT,
    nominal_freq_hz: float = NOMINAL_FREQUENCY_HZ,
) -> Optional[DatalogSummary]:
    """Build the magnitude/extremes-focused statistical summary for one toolset's datalog."""
    if not datalog_entries:
        return None

    df = _datalog_frame(datalog_entries)
    if df.empty:
        return None
    sdx = datalog_entries[0].sdx

    return DatalogSummary(
        sdx=sdx,
        sample_count=len(df),
        input_voltage_min=float(df["input_voltage"].min()),
        input_voltage_max=float(df["input_voltage"].max()),
        input_voltage_p1=float(df["input_voltage"].quantile(0.01)),
        input_voltage_p99=float(df["input_voltage"].quantile(0.99)),
        input_voltage_rms=_rms(df["input_voltage"]),
        output_voltage_min=float(df["output_voltage"].min()),
        output_voltage_max=float(df["output_voltage"].max()),
        output_voltage_p1=float(df["output_voltage"].quantile(0.01)),
        output_voltage_p99=float(df["output_voltage"].quantile(0.99)),
        output_voltage_rms=_rms(df["output_voltage"]),
        input_freq_max_deviation_hz=float((df["input_freq"] - nominal_freq_hz).abs().max()),
        output_freq_max_deviation_hz=float((df["output_freq"] - nominal_freq_hz).abs().max()),
        temp_max_c=float(df["temp"].max()),
        temp_time_above_threshold_min=_duration_above_threshold_min(df, "temp", temp_threshold_c),
        load_p95_pct=float(df["load_level"].quantile(0.95)),
        load_time_in_overload_min=_duration_above_threshold_min(df, "load_level", load_threshold_pct),
        battery_voltage_min=float(df["battery_voltage"].min()),
        battery_level_net_delta_pct=float(df["battery_level"].iloc[-1] - df["battery_level"].iloc[0]),
        battery_level_max_discharge_rate_pct_per_hr=_max_discharge_rate_pct_per_hr(df),
    )


def compute_rolling_24h(datalog_entries: List["DataLogEntry"]) -> Optional[pd.DataFrame]:
    """24-hour rolling mean of each datalog metric over the trailing 7 days, used for the rolling summary graph."""
    if not datalog_entries:
        return None

    df = _datalog_frame(datalog_entries)
    if df.empty:
        return None
    rolling = df.set_index("timestamp")[DATALOG_METRIC_COLUMNS].rolling("24h").mean()
    return rolling.reset_index()


def analyze_sdx_logs(
    sdx: str,
    datalog_entries: List["DataLogEntry"],
    eventlog_entries: List["EventLogEntry"],
) -> SdxAnalysis:
    """Compute summary health metrics for a toolset, then hand off for per-toolset CSV/graph output."""
    decode_eventlog_entries(eventlog_entries)

    analysis = SdxAnalysis(
        sdx=sdx,
        sample_count=len(datalog_entries),
        alarm_count=len(eventlog_entries),
        datalog_summary=summarize_datalog(datalog_entries),
        datalog_rolling_24h=compute_rolling_24h(datalog_entries),
        datalog_entries=datalog_entries,
        eventlog_entries=eventlog_entries,
    )

    UPSLogToCsv.write_eventlog_report(analysis)
    if analysis.datalog_summary is not None:
        UPSLogToCsv.write_datalog_summary(analysis.datalog_summary)
    if analysis.datalog_rolling_24h is not None:
        UPSLogToCsv.write_datalog_rolling_graph(sdx, analysis.datalog_rolling_24h)
    return analysis
