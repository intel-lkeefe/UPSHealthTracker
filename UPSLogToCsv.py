"""Write UPS toolset health analysis results into a single combined HTML report."""
from __future__ import annotations

import base64
import html
import io
import shutil
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import pandas as pd

    from UPSLogCore import DatalogSummary, SdxAnalysis

OUTPUT_DIR = Path("output")
REPORT_FILENAME = "ups_health_report.html"


def clear_output_dir(output_dir: Path = OUTPUT_DIR) -> None:
    """Remove any existing output files so a stale report isn't left behind."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


EVENTLOG_ROLLING_WINDOW = timedelta(days=7)
# "I" (informational) is decoded like the rest but left out of the report, except for the
# always_include exceptions (self-test results) flagged by UPSLogCore.decode_eventlog_entries.
EVENTLOG_REPORT_SEVERITIES = {"C", "W"}

SEVERITY_LABELS = {"C": "Critical", "W": "Warning", "I": "Info"}


def _eventlog_rows(analysis: "SdxAnalysis") -> list:
    """Warning/critical eventlog entries plus always_include info alarms, from the trailing 7 days, newest first."""
    entries = analysis.eventlog_entries
    if entries:
        cutoff = max(e.timestamp for e in entries) - EVENTLOG_ROLLING_WINDOW
        entries = [e for e in entries if e.timestamp >= cutoff]
    entries = [e for e in entries if e.severity in EVENTLOG_REPORT_SEVERITIES or e.always_include]
    return sorted(entries, key=lambda e: e.timestamp, reverse=True)


def _eventlog_table_html(analysis: "SdxAnalysis") -> str:
    rows = _eventlog_rows(analysis)
    if not rows:
        return '<p class="empty">No warning/critical events in the past 7 days.</p>'

    body_rows = "\n".join(
        '<tr><td>{ts}</td><td class="sev-{sev}">{sev_label}</td><td>{code}</td><td>{msg}</td></tr>'.format(
            ts=html.escape(str(entry.timestamp)),
            sev=html.escape(entry.severity),
            sev_label=html.escape(SEVERITY_LABELS.get(entry.severity) or entry.severity),
            code=html.escape(entry.alarm_code),
            msg=html.escape(entry.message),
        )
        for entry in rows
    )
    return (
        '<table class="eventlog">'
        "<thead><tr><th>Timestamp</th><th>Severity</th><th>Alarm Code</th><th>Message</th></tr></thead>"
        f"<tbody>{body_rows}</tbody></table>"
    )


DATALOG_SUMMARY_FIELDS = [
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
    "battery_level_min_scheduled_test_pct",
]


def _datalog_summary_table_html(summary: Optional["DatalogSummary"]) -> str:
    if summary is None:
        return '<p class="empty">No datalog samples in the past 7 days.</p>'

    rows = "\n".join(
        f"<tr><th>{html.escape(name)}</th><td>{html.escape(str(getattr(summary, name)))}</td></tr>"
        for name in DATALOG_SUMMARY_FIELDS
    )
    return f'<table class="datalog-summary"><tbody>{rows}</tbody></table>'


# (subplot title, [(dataframe column, series label), ...]) - one panel per metric category
ROLLING_GRAPH_PANELS = [
    ("Voltage (V)", [("input_voltage", "Input"), ("output_voltage", "Output")]),
    ("Frequency (Hz)", [("input_freq", "Input"), ("output_freq", "Output")]),
    ("Load (%)", [("load_level", "Load")]),
    ("Temperature (C)", [("temp", "Temp")]),
    ("Battery Voltage (V)", [("battery_voltage", "Battery V")]),
    ("Battery Level (%)", [("battery_level", "Battery %")]),
]


def _rolling_graph_img_html(sdx: str, rolling_24h: Optional["pd.DataFrame"]) -> str:
    """Render the rolling-24h graph to an in-memory PNG and embed it as a base64 data URI."""
    if rolling_24h is None:
        return '<p class="empty">No datalog samples to graph.</p>'

    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharex=True)
    fig.suptitle(f"{sdx} - 7 day Rolling Summary")

    for ax, (title, series) in zip(axes.flat, ROLLING_GRAPH_PANELS):
        for column, label in series:
            ax.plot(rolling_24h["timestamp"], rolling_24h[column], label=label)
        ax.set_title(title)
        ax.legend(loc="best", fontsize="small")
        ax.tick_params(axis="x", rotation=45)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<img class="rolling-graph" src="data:image/png;base64,{encoded}" alt="{html.escape(sdx)} rolling summary">'


REPORT_CSS = """
body { font-family: Arial, sans-serif; margin: 2rem; color: #222; }
h1 { margin-bottom: 0.25rem; }
.toolset { border-top: 3px solid #333; padding-top: 1rem; margin-top: 2rem; }
.toolset h2 { margin-bottom: 0.25rem; }
table { border-collapse: collapse; margin: 0.5rem 0 1rem; }
th, td { border: 1px solid #ccc; padding: 4px 8px; font-size: 0.9rem; text-align: left; }
.eventlog thead th { background: #eee; }
.sev-C { color: #b00020; font-weight: bold; }
.sev-W { color: #b36b00; font-weight: bold; }
.sev-I { color: #1a5fb4; }
.empty { color: #666; font-style: italic; }
.rolling-graph { max-width: 100%; height: auto; margin-top: 0.5rem; }
"""


def write_html_report(analyses: List["SdxAnalysis"], output_dir: Path = OUTPUT_DIR) -> Path:
    """Write every toolset's eventlog/datalog summary/graph into a single HTML report, sorted by SDX ascending."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / REPORT_FILENAME

    sections = []
    for analysis in sorted(analyses, key=lambda a: a.sdx):
        sections.append(
            '<section class="toolset">'
            f"<h2>{html.escape(analysis.sdx)}</h2>"
            "<h3>Event Log</h3>"
            f"{_eventlog_table_html(analysis)}"
            "<h3>Datalog Summary</h3>"
            f"{_datalog_summary_table_html(analysis.datalog_summary)}"
            "<h3>Rolling 7-Day Graph</h3>"
            f"{_rolling_graph_img_html(analysis.sdx, analysis.datalog_rolling_24h)}"
            "</section>"
        )

    html_doc = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>UPS Health Report</title>'
        f"<style>{REPORT_CSS}</style></head><body>"
        "<h1>UPS Health Report</h1>"
        f"{''.join(sections)}"
        "</body></html>"
    )

    report_path.write_text(html_doc, encoding="utf-8")
    return report_path
