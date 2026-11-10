"""Analyze parsed UPS log data for a toolset and forward results to UPSLogToCsv for output."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

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

# The eventlog table/raw CSV and self-test detection only look at this trailing window.
EVENTLOG_ANALYSIS_WINDOW = timedelta(days=14)

# Window around each detected self-test event (alarm code 47) used to sample battery level and shade graphs.
SELF_TEST_WINDOW_TOLERANCE = timedelta(minutes=10)

# Battery level considered "recovered"/de-energizing-event-over after a dip.
BATTERY_RECOVERY_THRESHOLD_PCT = 95.0

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

LIMITS_FILE = Path(__file__).parent / "UPSLogLimits.csv"


@dataclass
class MetricRange:
    """Green/yellow bounds for one gauged metric; a bound of None means no limit on that side."""

    green_min: Optional[float]
    green_max: Optional[float]
    yellow_min: Optional[float]
    yellow_max: Optional[float]


def _parse_bound(raw: str) -> Optional[float]:
    raw = raw.strip()
    return float(raw) if raw else None


def load_metric_limits(path: Path = LIMITS_FILE) -> Dict[str, MetricRange]:
    """Read the green/yellow bounds CSV, skipping blank lines and '#' comments."""
    limits: Dict[str, MetricRange] = {}
    if not path.is_file():
        return limits

    with path.open(newline="", encoding="utf-8") as f:
        data_lines = [line for line in f if line.strip() and not line.lstrip().startswith("#")]
    for row in csv.DictReader(data_lines):
        metric = (row.get("metric") or "").strip()
        if not metric:
            continue
        limits[metric] = MetricRange(
            green_min=_parse_bound(row.get("green_min") or ""),
            green_max=_parse_bound(row.get("green_max") or ""),
            yellow_min=_parse_bound(row.get("yellow_min") or ""),
            yellow_max=_parse_bound(row.get("yellow_max") or ""),
        )
    return limits


# Loaded once at import time; edit UPSLogLimits.csv and restart to pick up changes.
METRIC_LIMITS = load_metric_limits()


def classify_metric(value: Optional[float], limits: Optional[MetricRange]) -> Optional[str]:
    """Return 'green'/'yellow'/'red' for a gauged metric, or None if it isn't gauged."""
    if value is None or limits is None:
        return None

    green_min = limits.green_min if limits.green_min is not None else float("-inf")
    green_max = limits.green_max if limits.green_max is not None else float("inf")
    if green_min <= value <= green_max:
        return "green"

    yellow_min = limits.yellow_min if limits.yellow_min is not None else float("-inf")
    yellow_max = limits.yellow_max if limits.yellow_max is not None else float("inf")
    if yellow_min <= value <= yellow_max:
        return "yellow"

    return "red"


def compute_datalog_gauges(summary: Optional["DatalogSummary"]) -> Dict[str, str]:
    """Classify each gauged field of a datalog summary as green/yellow/red per UPSLogLimits.csv."""
    if summary is None:
        return {}
    gauges = {}
    for metric, limits in METRIC_LIMITS.items():
        color = classify_metric(getattr(summary, metric, None), limits)
        if color is not None:
            gauges[metric] = color

    # The weekly self-test discharge is often the toolset's single lowest battery reading, so
    # min_discharged_value frequently equals battery_level_min_scheduled_test_pct; when it does,
    # gauge it with that metric's (usually stricter) thresholds instead of its own.
    if (
        summary.battery_level_min_scheduled_test_pct is not None
        and summary.min_discharged_value == summary.battery_level_min_scheduled_test_pct
    ):
        test_color = classify_metric(
            summary.min_discharged_value, METRIC_LIMITS.get("battery_level_min_scheduled_test_pct")
        )
        if test_color is not None:
            gauges["min_discharged_value"] = test_color

    return gauges


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
    min_discharged_value: float
    longest_deenergize_duration_min: Optional[float] = None
    battery_level_min_scheduled_test_pct: Optional[float] = None


@dataclass
class SdxAnalysis:
    sdx: str
    sample_count: int
    alarm_count: int
    datalog_summary: Optional[DatalogSummary] = None
    datalog_rolling_24h: Optional[pd.DataFrame] = None
    datalog_gauges: Dict[str, str] = field(default_factory=dict)
    scheduled_test_windows: List[Tuple[datetime, datetime]] = field(default_factory=list)
    self_test_recovery_minutes: List[Tuple[datetime, Optional[float]]] = field(default_factory=list)
    self_test_alert: Optional[str] = None
    analysis_window_start: Optional[datetime] = None
    datalog_entries: List["DataLogEntry"] = field(default_factory=list)
    eventlog_entries: List["EventLogEntry"] = field(default_factory=list)


def _latest_timestamp(entries: List) -> Optional[datetime]:
    return max((e.timestamp for e in entries), default=None)


def _has_recent_activity(
    datalog_entries: List["DataLogEntry"],
    eventlog_entries: List["EventLogEntry"],
    window: timedelta = DATALOG_ANALYSIS_WINDOW,
) -> bool:
    """True if the toolset's newest datalog or eventlog entry falls within the trailing `window` of now."""
    latest = _latest_timestamp(datalog_entries + eventlog_entries)
    return latest is not None and latest >= datetime.now() - window


def decode_eventlog_entries(eventlog_entries: List["EventLogEntry"]) -> List["EventLogEntry"]:
    """Set each entry's severity (C/W/I) and replace its raw numeric alarm code with its description."""
    for entry in eventlog_entries:
        entry.severity = eventLogCoding.classify_alarm_severity(entry.alarm_code)
        entry.always_include = eventLogCoding.is_reportable_info_alarm(entry.alarm_code)
        entry.alarm_code = eventLogCoding.decode_alarm_code(entry.alarm_code)
    return eventlog_entries


def clear_output() -> None:
    """Clear prior output files before a run, so a toolset that no longer produces a report leaves none behind."""
    UPSLogToCsv.clear_output_dir()


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


def _battery_level_min_near_self_tests(
    df: pd.DataFrame,
    self_test_timestamps: List[datetime],
    tolerance: timedelta = SELF_TEST_WINDOW_TOLERANCE,
) -> Optional[float]:
    """Lowest battery level within +/- tolerance of any detected self-test event."""
    if not self_test_timestamps:
        return None
    ts = df["timestamp"]
    in_window = pd.Series(False, index=df.index)
    for test_ts in self_test_timestamps:
        in_window |= (ts - test_ts).abs() <= tolerance
    levels = df.loc[in_window, "battery_level"]
    return float(levels.min()) if not levels.empty else None


def _time_to_recover(
    df: pd.DataFrame, start_time: datetime, recovery_threshold_pct: float = BATTERY_RECOVERY_THRESHOLD_PCT
) -> Optional[float]:
    """Minutes from start_time until battery_level first reaches recovery_threshold_pct, or None if it never does."""
    after = df[df["timestamp"] >= start_time]
    recovered = after[after["battery_level"] >= recovery_threshold_pct]
    if recovered.empty:
        return None
    return float((recovered["timestamp"].iloc[0] - start_time).total_seconds() / 60.0)


def _battery_dip_troughs(
    df: pd.DataFrame, recovery_threshold_pct: float = BATTERY_RECOVERY_THRESHOLD_PCT
) -> List[datetime]:
    """Timestamp of the lowest point in each contiguous run where battery_level dips below recovery_threshold_pct."""
    below = df["battery_level"] < recovery_threshold_pct
    troughs: List[datetime] = []
    start_idx = None
    for i, is_below in enumerate(below):
        if is_below and start_idx is None:
            start_idx = i
        elif not is_below and start_idx is not None:
            segment = df.iloc[start_idx:i]
            trough_idx = segment["battery_level"].idxmin()
            troughs.append(df.at[trough_idx, "timestamp"])
            start_idx = None
    return troughs


def _longest_deenergize_duration_min(
    df: pd.DataFrame, recovery_threshold_pct: float = BATTERY_RECOVERY_THRESHOLD_PCT
) -> Optional[float]:
    """Longest time from a battery dip's lowest point back up to recovery_threshold_pct, across the window."""
    durations = [
        duration
        for duration in (
            _time_to_recover(df, trough, recovery_threshold_pct)
            for trough in _battery_dip_troughs(df, recovery_threshold_pct)
        )
        if duration is not None
    ]
    return max(durations) if durations else None


def summarize_datalog(
    datalog_entries: List["DataLogEntry"],
    self_test_timestamps: Optional[List[datetime]] = None,
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
        min_discharged_value=float(df["battery_level"].min()),
        longest_deenergize_duration_min=_longest_deenergize_duration_min(df),
        battery_level_min_scheduled_test_pct=_battery_level_min_near_self_tests(df, self_test_timestamps or []),
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


def scheduled_test_windows(
    self_test_timestamps: List[datetime], tolerance: timedelta = SELF_TEST_WINDOW_TOLERANCE
) -> List[Tuple[datetime, datetime]]:
    """Start/end spans around each actual self-test event timestamp, for shading on the rolling graphs."""
    return [(ts - tolerance, ts + tolerance) for ts in self_test_timestamps]


def self_test_timestamps_in_window(
    eventlog_entries: List["EventLogEntry"], window_start: Optional[datetime]
) -> List[datetime]:
    """Timestamps of 'Self Test' executed events (alarm code 47) at/after window_start."""
    if window_start is None:
        return []
    return sorted(
        e.timestamp
        for e in eventlog_entries
        if eventLogCoding.is_self_test_alarm(e.raw_code) and e.timestamp >= window_start
    )


def self_test_recovery_minutes(
    datalog_entries: List["DataLogEntry"], self_test_timestamps: List[datetime]
) -> List[Tuple[datetime, Optional[float]]]:
    """For each self-test event, minutes from its start until battery_level recovers to ~95% (None if it never does)."""
    df = _datalog_frame(datalog_entries)
    if df.empty:
        return [(ts, None) for ts in self_test_timestamps]
    return [(ts, _time_to_recover(df, ts)) for ts in self_test_timestamps]


def analysis_window_start(
    datalog_entries: List["DataLogEntry"],
    eventlog_entries: List["EventLogEntry"],
    window: timedelta = EVENTLOG_ANALYSIS_WINDOW,
) -> Optional[datetime]:
    """Start of the trailing `window` used throughout the report for this toolset.

    Anchored to the datalog's own recency (so it reflects actual logged activity, not a gap-skewed
    'now'); falls back to the eventlog's own recency when there's no datalog data at all. Eventlog
    filtering uses this instead of its own last-entry timestamp so a toolset whose eventlog has gone
    quiet (e.g. no new alarms in weeks) doesn't show a stale window as if it were the current one.
    """
    df = _datalog_frame(datalog_entries, window)
    if not df.empty:
        return df["timestamp"].min()
    latest_event = _latest_timestamp(eventlog_entries)
    return (latest_event - window) if latest_event is not None else None


def analyze_sdx_logs(
    sdx: str,
    datalog_entries: List["DataLogEntry"],
    eventlog_entries: List["EventLogEntry"],
) -> Optional[SdxAnalysis]:
    """Compute summary health metrics for a toolset, or return None if it has no recent activity."""
    decode_eventlog_entries(eventlog_entries)

    if not _has_recent_activity(datalog_entries, eventlog_entries):
        print(f"Skipping {sdx}: no datalog/eventlog activity in the past {DATALOG_ANALYSIS_WINDOW.days} days.")
        return None

    window_start = analysis_window_start(datalog_entries, eventlog_entries)
    self_test_timestamps = self_test_timestamps_in_window(eventlog_entries, window_start)
    self_test_alert = None
    if not self_test_timestamps:
        self_test_alert = f"No self-test (alarm code 47) recorded in the trailing {EVENTLOG_ANALYSIS_WINDOW.days} days."

    datalog_summary = summarize_datalog(datalog_entries, self_test_timestamps)
    return SdxAnalysis(
        sdx=sdx,
        sample_count=len(datalog_entries),
        alarm_count=len(eventlog_entries),
        datalog_summary=datalog_summary,
        datalog_rolling_24h=compute_rolling_24h(datalog_entries),
        datalog_gauges=compute_datalog_gauges(datalog_summary),
        scheduled_test_windows=scheduled_test_windows(self_test_timestamps),
        self_test_recovery_minutes=self_test_recovery_minutes(datalog_entries, self_test_timestamps),
        self_test_alert=self_test_alert,
        analysis_window_start=window_start,
        datalog_entries=datalog_entries,
        eventlog_entries=eventlog_entries,
    )


def write_html_report(analyses: List[SdxAnalysis]) -> Path:
    """Write every processed toolset's analysis into a single combined HTML report."""
    return UPSLogToCsv.write_html_report(analyses)


def write_eventlog_raw_csv(analyses: List[SdxAnalysis]) -> Path:
    """Write every processed toolset's raw (all-severity) eventlog entries into one combined CSV."""
    return UPSLogToCsv.write_eventlog_raw_csv(analyses)
