"""Analyze parsed UPS log data for a toolset and forward results to UPSLogToCsv for output."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import TYPE_CHECKING, List, Optional

import UPSLogToCsv

if TYPE_CHECKING:
    from UPSLogFinder import DataLogEntry, EventLogEntry


@dataclass
class SdxAnalysis:
    sdx: str
    sample_count: int
    alarm_count: int
    battery_level_min: Optional[float] = None
    battery_level_max: Optional[float] = None
    battery_level_avg: Optional[float] = None
    battery_voltage_min: Optional[float] = None
    battery_voltage_max: Optional[float] = None
    backup_time_min: Optional[float] = None
    temp_max: Optional[float] = None
    datalog_entries: List["DataLogEntry"] = field(default_factory=list)
    eventlog_entries: List["EventLogEntry"] = field(default_factory=list)


def analyze_sdx_logs(
    sdx: str,
    datalog_entries: List["DataLogEntry"],
    eventlog_entries: List["EventLogEntry"],
) -> SdxAnalysis:
    """Compute summary health metrics for a toolset, then hand off for CSV output."""
    analysis = SdxAnalysis(
        sdx=sdx,
        sample_count=len(datalog_entries),
        alarm_count=len(eventlog_entries),
        datalog_entries=datalog_entries,
        eventlog_entries=eventlog_entries,
    )

    if datalog_entries:
        battery_levels = [e.battery_level for e in datalog_entries]
        battery_voltages = [e.battery_voltage for e in datalog_entries]
        backup_times = [e.backup_time for e in datalog_entries]
        temps = [e.temp for e in datalog_entries]

        analysis.battery_level_min = min(battery_levels)
        analysis.battery_level_max = max(battery_levels)
        analysis.battery_level_avg = mean(battery_levels)
        analysis.battery_voltage_min = min(battery_voltages)
        analysis.battery_voltage_max = max(battery_voltages)
        analysis.backup_time_min = min(backup_times)
        analysis.temp_max = max(temps)

    UPSLogToCsv.write_report(analysis)
    return analysis
