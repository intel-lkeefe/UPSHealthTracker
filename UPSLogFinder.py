"""Locate and parse UPS datalog/eventlog files for SDX toolsets, then hand them off for analysis."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import UPSLogCore

BASE_LOG_PATH = Path(r"\\al4file1.ra.intel.com\sdx\event\SDxLogs\SDE_ELOGS")

UPS_LOGS_DIRNAME = "UPSLogs"
DATALOG_DIRNAME = "datalog"
EVENTLOG_DIRNAME = "eventlog"

DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"


@dataclass
class DataLogEntry:
    sdx: str
    timestamp: datetime
    input_voltage: float
    output_voltage: float
    input_freq: float
    output_freq: float
    load_level: float
    temp: float
    backup_time: float
    battery_voltage: float
    battery_level: float


@dataclass
class EventLogEntry:
    sdx: str
    timestamp: datetime
    alarm_code: str
    message: str
    severity: str = ""  # C/W/I, set by UPSLogCore once the alarm code is decoded


def get_ups_logs_dir(sdx: str, base_path: Path = BASE_LOG_PATH) -> Path:
    return base_path / sdx / UPS_LOGS_DIRNAME


def get_datalog_dir(sdx: str, base_path: Path = BASE_LOG_PATH) -> Path:
    return get_ups_logs_dir(sdx, base_path) / DATALOG_DIRNAME


def get_eventlog_dir(sdx: str, base_path: Path = BASE_LOG_PATH) -> Path:
    return get_ups_logs_dir(sdx, base_path) / EVENTLOG_DIRNAME


def list_sdx_toolsets(base_path: Path = BASE_LOG_PATH) -> List[str]:
    """Return the names of all SDX toolset directories under base_path."""
    if not base_path.is_dir():
        return []
    return sorted(p.name for p in base_path.iterdir() if p.is_dir() and p.name.upper().startswith("SDX"))


def list_log_files(directory: Path) -> List[Path]:
    """Return fileXX.csv entries sorted numerically by XX, since names aren't chronological."""
    if not directory.is_dir():
        return []

    def sort_key(path: Path) -> int:
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return int(digits) if digits else 0

    return sorted(directory.glob("file*.csv"), key=sort_key)


def parse_datalog_file(path: Path, sdx: str) -> List[DataLogEntry]:
    """Parse a datalog fileXX.csv: datetime,inV,outV,inHz,outHz,load%,tempC,backupMin,battV,batt%."""
    entries: List[DataLogEntry] = []
    with path.open("r", newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.reader(f):
            if len(row) < 10:
                continue
            try:
                entries.append(
                    DataLogEntry(
                        sdx=sdx,
                        timestamp=datetime.strptime(row[0].strip(), DATETIME_FORMAT),
                        input_voltage=float(row[1]),
                        output_voltage=float(row[2]),
                        input_freq=float(row[3]),
                        output_freq=float(row[4]),
                        load_level=float(row[5]),
                        temp=float(row[6]),
                        backup_time=float(row[7]),
                        battery_voltage=float(row[8]),
                        battery_level=float(row[9]),
                    )
                )
            except ValueError:
                continue
    return entries


def parse_eventlog_file(path: Path, sdx: str) -> List[EventLogEntry]:
    """Parse an eventlog fileXX.csv: 'YYYY/MM/DD HH:MM:SS alarmCode embedded text'."""
    entries: List[EventLogEntry] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=3)
            if len(parts) < 3:
                continue
            date_str, time_str, alarm_code = parts[0], parts[1], parts[2]
            message = parts[3] if len(parts) > 3 else ""
            try:
                timestamp = datetime.strptime(f"{date_str} {time_str}", DATETIME_FORMAT)
            except ValueError:
                continue
            entries.append(EventLogEntry(sdx=sdx, timestamp=timestamp, alarm_code=alarm_code, message=message))
    return entries


def gather_sdx_logs(sdx: str, base_path: Path = BASE_LOG_PATH) -> Tuple[List[DataLogEntry], List[EventLogEntry]]:
    """Parse all datalog and eventlog files found for a single SDX toolset."""
    datalog_entries: List[DataLogEntry] = []
    for file_path in list_log_files(get_datalog_dir(sdx, base_path)):
        datalog_entries.extend(parse_datalog_file(file_path, sdx))

    eventlog_entries: List[EventLogEntry] = []
    for file_path in list_log_files(get_eventlog_dir(sdx, base_path)):
        eventlog_entries.extend(parse_eventlog_file(file_path, sdx))

    return datalog_entries, eventlog_entries


def process_sdx(sdx: str, base_path: Path = BASE_LOG_PATH) -> UPSLogCore.SdxAnalysis:
    """Parse logs for one toolset and hand the data off to UPSLogCore for analysis."""
    datalog_entries, eventlog_entries = gather_sdx_logs(sdx, base_path)
    return UPSLogCore.analyze_sdx_logs(sdx, datalog_entries, eventlog_entries)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find and parse UPS logs for SDX toolsets.")
    parser.add_argument("sdx", nargs="*", help="SDX toolset name(s), e.g. SDX202. Omit to process all toolsets found.")
    parser.add_argument("--base-path", type=Path, default=BASE_LOG_PATH, help="Root SDE_ELOGS directory.")
    args = parser.parse_args()

    sdx_list = args.sdx or list_sdx_toolsets(args.base_path)
    if not sdx_list:
        print(f"No SDX toolsets found under {args.base_path}")
        return

    for sdx in sdx_list:
        print(f"Processing {sdx}...")
        process_sdx(sdx, args.base_path)


if __name__ == "__main__":
    main()
