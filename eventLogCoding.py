CRITICAL_ALARMS: dict = {
    0x800: "Battery Low",
    0x801: "Shutdown start (AC fail)",
    0x802: "Shutdown start by Special day schedule action",
    0x803: "Shutdown start by Every month schedule action",
    0x804: "Shutdown start by Every week schedule action",
    0x805: "Shutdown start by Shutdown immediately",
    0x806: "Run External command",
    0x807: "Close App start",
    0x808: "OS shutdown start",
    0x809: "UPS hardware is abnormal",
    0x80A: "Output over voltage",
    0x80B: "DC bus voltage abnormal",
    0x80C: "Over Load Time out",
    0x80D: "Output short",
    0x80E: "Battery Over charge",
    0x80F: "Battery under charge",
    0x810: "Over Temperature",
    0x811: "FAN Fail",
    0x812: "TX Fail",
    0x813: "Battery Weak",
    0x814: "Self test(Function Test): NG(Battery Weak)",
    0x815: "Self test(Function Test): NG(UPS hardware abnormal)",
    0x816: "Battery Auto Test: NG(Battery Weak)",
    0x817: "Battery Auto Test: NG(UPS hardware abnormal)",
}

WARNING_ALARMS: dict = {
    0x400: "AC line failure",
    0x401: "Schedule Shutdown Warning Start(Special Day)",
    0x402: "Schedule Shutdown Warning Start(Every Month)",
    0x403: "Schedule Shutdown Warning Start(Every Week)",
    0x404: "Shutdown Pause",
    0x405: "Over Load",
    0x406: "Output condition (Boost up / down)",
    0x407: "Battery Disconnect",
    0x408: "Bypass",
    0x409: "Communication error",
}

INFO_ALARMS: dict = {
    0x000: "Recovery of input power supply",
    0x001: "Establishment of communication",
    0x002: "Agent Start",
    0x003: "Agent Stop",
    0x004: "Self test: OK",
    0x005: "Battery Auto Test result: OK",
    0x006: "Setting for 'Select UPS Outlet' changed",
    0x007: "Setting for 'AC Fail Delay Time' changed",
    0x008: "Setting for 'Shutdown Start Delay Time' changed",
    0x009: "Setting for 'Shutdown Need Time' changed",
    0x00A: "Setting for 'Outlet Output Stop Delay Time' changed",
    0x00B: "Setting for 'Outlet Delay Time of UPS Boot Up' changed",
    0x00C: "Setting for 'Select OS Shutdown Mode' changed",
    0x00D: "Setting for 'UPS Auto Reboot' changed",
    0x00E: "Setting for 'First Warning Message' changed",
    0x00F: "Setting for 'Warning Interval' changed",
    0x010: "Setting for 'Schedule Action Start Warning' changed",
    0x011: "Setting for 'Maximum Event Log Record Time' changed",
    0x012: "Setting for 'Maximum Data Log Record Time' changed",
    0x013: "Setting for 'Record Interval Time(On Line)' changed",
    0x014: "Setting for 'Record Interval Time(On Battery)' changed",
    0x015: "Setting for 'Communication Port' added",
    0x016: "Setting for 'Communication Port' deleted",
    0x017: "Setting related to 'Network Port Address' changed",
    0x018: "Setting for 'SMTP Mail' changed",
    0x019: "Setting for 'Schedule Action (Special Day)' added",
    0x01A: "Setting for 'Schedule Action (Monthly)' added",
    0x01B: "Setting for 'Schedule Action (Weekly)' added",
    0x01C: "Setting for 'Schedule Action (Special Day)' changed",
    0x01D: "Setting for 'Schedule Action (Monthly)' changed",
    0x01E: "Setting for 'Schedule Action (Weekly)' changed",
    0x01F: "Setting for 'Schedule Action (Special Day)' deleted",
    0x020: "Setting for 'Schedule Action (Monthly)' deleted",
    0x021: "Setting for 'Schedule Action (Weekly)' deleted",
    0x022: "Setting for 'Run External Command Executed Time' changed",
    0x023: "Setting for 'External Command' added",
    0x024: "Setting for 'External Command' deleted",
    0x025: "Setting for 'Notification To User' changed",
    0x026: "Setting for 'Battery use date (Battery Changed Date)' updated",
    0x027: "Default value for 'Shutdown Parameter' set",
    0x028: "Default value set for 'UPS Boot/Reboot'",
    0x029: "Default value set for 'Log'",
    0x02A: "Default value for 'Communication Setting' set",
    0x02B: "Setting for 'Event Information' changed",
    0x02C: "Setting for 'Notification' changed",
    0x02E: "'Buzzer Test' executed",
    0x02F: "'Self Test' executed",
    0x030: "Setting for 'Buzzer' changed",
    0x031: "Setting for 'Battery Auto Test' changed",
    0x032: "'Backup Time Test' started",
    0x033: "'Backup Time Test' completed",
    0x034: "'Backup Time Test' canceled",
    0x035: "Output from 'Outlet B(Control)' started",
    0x036: "Output from 'Outlet B(Control)' stopped",
    0x037: "Output from 'Outlet C(Control)' started",
    0x038: "Output from 'Outlet C(Control)' stopped",
    0x039: "Setting for 'Input/Output Setting' changed",
    0x03A: "Setting 'Battery Unit' added",
    0x03B: "Resuming shutdown",
    0x065: "Setting for 'UPS Auto Stop' changed",
    0x066: "Setting for 'Page Refresh Rate' changed",
    0x067: "Setting for 'Redundant Power Supply Setting' changed",
    0x068: "'Syslog function' enabled",
    0x069: "'Syslog function' disabled",
    0x06A: "Setting for 'Syslog Setting' changed",
    0x06B: "Setting for 'Priority Setting' changed",
    0x06C: "Setting for 'Syslog Language Setting' changed",
    0x06D: "Setting for 'Setting' changed",
    0x06E: "Setting for 'Transmission Timing' changed",
    0x06F: "Setting for 'Wake On LAN Destination' added",
    0x070: "Setting for 'Wake On LAN Destination' modified",
    0x071: "Setting for 'Wake On LAN Destination' deleted",
    0x072: "Stopping output from Outlet A due to non-conformance with ping monitor judgment criteria",
    0x073: "Stopping output from Outlet B due to non-conformance with ping monitor judgment criteria",
    0x074: "Stopping output from Outlet C due to non-conformance with ping monitor judgment criteria",
    0x075: "Stopping/starting output from Outlet A due to non-conformance with ping monitor judgment criteria",
    0x076: "Stopping/starting output from Outlet B due to non-conformance with ping monitor judgment criteria",
    0x077: "Stopping/starting output from Outlet C due to non-conformance with ping monitor judgment criteria",
    0x078: "Restarting the monitoring of output from Outlet A due to conformance with ping monitor judgment criteria",
    0x079: "Restarting the monitoring of output from Outlet B due to conformance with ping monitor judgment criteria",
    0x07A: "Restarting the monitoring of output from Outlet C due to conformance with ping monitor judgment criteria",
    0x07B: "No response to ping from several devices connected to Outlet A",
    0x07C: "No response to ping from several devices connected to Outlet B",
    0x07D: "No response to ping from several devices connected to Outlet C",
    0x07E: "Stopping the UPS due to non-conformance with ping monitor judgment criteria",
    0x07F: "Rebooting the UPS due to non-conformance with ping monitor judgment criteria",
    0x080: "Remote computer shut down by a Ping Monitor script",
    0x081: "SNMP service started",
    0x082: "SNMP service stopped",
    0x083: "SNMP V1 started",
    0x084: "SNMP V1 stopped",
    0x085: "SNMP V3 started",
    0x086: "SNMP V3 stopped",
    0x087: "SNMP V1 Access Right added",
    0x088: "SNMP V1 Access Right deleted",
    0x089: "SNMP V1 Access Right changed",
    0x08A: "SNMP V3 Access Right added",
    0x08B: "SNMP V3 Access Right deleted",
    0x08C: "SNMP V3 Access Right changed",
    0x08D: "SNMP V1 TRAP added",
    0x08E: "SNMP V1 TRAP deleted",
    0x08F: "SNMP V1 TRAP changed",
    0x090: "SNMP V3 TRAP added",
    0x091: "SNMP V3 TRAP deleted",
    0x092: "SNMP V3 TRAP changed",
    0x093: "Script Shutdown setting added",
    0x094: "Script Shutdown setting deleted",
    0x095: "Script Shutdown setting changed",
    0x096: "Setting for 'Logoff Time' changed",
    0x097: "Maximum backup time changed",
    0x098: "UPS Start Delay Time setting changed",
    0x099: "USP Cold Start setting changed",
    0x09A: "Send Output Delay Command setting changed",
    0x09B: "UPS reboot condition changed",
    0x09C: "Notification Delay Time setting changed",
    0x09D: "POP Before SMTP setting changed",
    0x09E: "Administrator setting changed",
    0x09F: "Script Shutdown started",
    0x0A0: "VMware end processing started",
    0x0A1: "Broadcast setting changed",
    0x0A2: "Ping setting changed",
}

# Raw eventlog alarm codes are decimal values (variable digit length) whose hex
# form encodes the lookup key in the low 3 hex digits, e.g. 2147484672 -> 0x80000800 -> 0x800.
ALARM_CODE_MASK = 0xFFF


def decode_alarm_code(code: str | int) -> str:
    """Resolve a raw eventlog alarm code to its alarm description string."""
    try:
        value = int(code)
    except (TypeError, ValueError):
        return str(code)

    hex_code = value & ALARM_CODE_MASK
    return (
        CRITICAL_ALARMS.get(hex_code)
        or WARNING_ALARMS.get(hex_code)
        or INFO_ALARMS.get(hex_code)
        or f"Unknown alarm code 0x{hex_code:03X}"
    )


SEVERITY_CRITICAL = "C"
SEVERITY_WARNING = "W"
SEVERITY_INFO = "I"
SEVERITY_UNKNOWN = "?"


def classify_alarm_severity(code: str | int) -> str:
    """Return 'C', 'W', or 'I' based on which alarm table the code's hex key falls under."""
    try:
        value = int(code)
    except (TypeError, ValueError):
        return SEVERITY_UNKNOWN

    hex_code = value & ALARM_CODE_MASK
    if hex_code in CRITICAL_ALARMS:
        return SEVERITY_CRITICAL
    if hex_code in WARNING_ALARMS:
        return SEVERITY_WARNING
    if hex_code in INFO_ALARMS:
        return SEVERITY_INFO
    return SEVERITY_UNKNOWN