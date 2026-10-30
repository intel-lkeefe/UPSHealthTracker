"""Write UPS toolset health analysis results to per-toolset CSV files and graphs."""
from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import pandas as pd

    from UPSLogCore import DatalogSummary, SdxAnalysis

OUTPUT_DIR = Path("output")

EVENTLOG_FIELDS = [
    "timestamp",
    "severity",
    "alarm_code",
    "message",
]

EVENTLOG_ROLLING_WINDOW = timedelta(days=7)
# "I" (informational) is decoded like the rest but left out of the CSV until it's needed.
EVENTLOG_REPORT_SEVERITIES = {"C", "W"}


def write_eventlog_report(analysis: "SdxAnalysis", output_dir: Path = OUTPUT_DIR) -> Path:
    """Write the toolset's warning/critical eventlog entries from the trailing 7 days to a per-SDX CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    eventlog_path = output_dir / f"{analysis.sdx}_eventlog.csv"

    entries = analysis.eventlog_entries
    if entries:
        cutoff = max(e.timestamp for e in entries) - EVENTLOG_ROLLING_WINDOW
        entries = [e for e in entries if e.timestamp >= cutoff]
    entries = [e for e in entries if e.severity in EVENTLOG_REPORT_SEVERITIES]

    with eventlog_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVENTLOG_FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "timestamp": entry.timestamp,
                    "severity": entry.severity,
                    "alarm_code": entry.alarm_code,
                    "message": entry.message,
                }
            )

    return eventlog_path


DATALOG_SUMMARY_FIELDS = [
    "sdx",
    "sample_count",
    "input_voltage_min",
    "input_voltage_max",
    "input_voltage_p1",
    "input_voltage_p99",
    "input_voltage_rms",
    "output_voltage_min",
    "output_voltage_max",
    "output_voltage_p1",
    "output_voltage_p99",
    "output_voltage_rms",
    "input_freq_max_deviation_hz",
    "output_freq_max_deviation_hz",
    "temp_max_c",
    "temp_time_above_threshold_min",
    "load_p95_pct",
    "load_time_in_overload_min",
    "battery_voltage_min",
    "battery_level_net_delta_pct",
    "battery_level_max_discharge_rate_pct_per_hr",
]


def write_datalog_summary(summary: "DatalogSummary", output_dir: Path = OUTPUT_DIR) -> Path:
    """Write one toolset's datalog statistical summary to its own CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"{summary.sdx}_datalog_summary.csv"

    row = {name: getattr(summary, name) for name in DATALOG_SUMMARY_FIELDS}
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DATALOG_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(row)

    return summary_path


# (subplot title, [(dataframe column, series label), ...]) - one panel per metric category
ROLLING_GRAPH_PANELS = [
    ("Voltage (V)", [("input_voltage", "Input"), ("output_voltage", "Output")]),
    ("Frequency (Hz)", [("input_freq", "Input"), ("output_freq", "Output")]),
    ("Load (%)", [("load_level", "Load")]),
    ("Temperature (C)", [("temp", "Temp")]),
    ("Battery Voltage (V)", [("battery_voltage", "Battery V")]),
    ("Battery Level (%)", [("battery_level", "Battery %")]),
]


def write_datalog_rolling_graph(sdx: str, rolling_24h: "pd.DataFrame", output_dir: Path = OUTPUT_DIR) -> Path:
    """Render the toolset's 24-hour rolling datalog summary as one figure with a panel per metric."""
    output_dir.mkdir(parents=True, exist_ok=True)
    graph_path = output_dir / f"{sdx}_datalog_rolling_24h.png"

    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharex=True)
    fig.suptitle(f"{sdx} - 24 Hour Rolling Summary")

    for ax, (title, series) in zip(axes.flat, ROLLING_GRAPH_PANELS):
        for column, label in series:
            ax.plot(rolling_24h["timestamp"], rolling_24h[column], label=label)
        ax.set_title(title)
        ax.legend(loc="best", fontsize="small")
        ax.tick_params(axis="x", rotation=45)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(str(graph_path))
    plt.close(fig)

    return graph_path
