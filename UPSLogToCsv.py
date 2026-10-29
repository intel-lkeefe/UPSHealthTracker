"""Write UPS toolset health analysis results to CSV."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from UPSLogCore import SdxAnalysis

OUTPUT_DIR = Path("output")

SUMMARY_FIELDS = [
    "sdx",
    "sample_count",
    "alarm_count",
    "battery_level_min",
    "battery_level_max",
    "battery_level_avg",
    "battery_voltage_min",
    "battery_voltage_max",
    "backup_time_min",
    "temp_max",
]


def write_report(analysis: "SdxAnalysis", output_dir: Path = OUTPUT_DIR) -> Path:
    """Append the toolset's summary metrics as a row in the fleet summary CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "ups_health_summary.csv"

    row = {name: getattr(analysis, name) for name in SUMMARY_FIELDS}
    write_header = not summary_path.exists()

    with summary_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return summary_path
