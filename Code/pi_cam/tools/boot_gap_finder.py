#!/usr/bin/env python3
"""
Pretty-prints each boot period from `journalctl --list-boots` and annotates gaps between boots.
"""

import subprocess
import re
from datetime import datetime

# Threshold in seconds to report a gap (e.g., hours * 3600)
GAP_THRESHOLD = 60*3  # 1 minute for demo; adjust as needed


def parse_boots():
    """
    Parses `journalctl --list-boots`, returning a list of tuples:
      (start_datetime, end_datetime, raw_range_str)
    """
    output = subprocess.check_output(["journalctl", "--list-boots"], encoding="utf-8")
    boots = []
    for line in output.strip().splitlines():
        # Extract the part after the boot ID (e.g., Mon 2025-06-09...)
        m = re.match(r'^\s*[-0-9]+\s+[0-9a-f]+\s+(.+)$', line)
        if not m or '—' not in m.group(1):
            continue
        raw_range = m.group(1).strip()
        start_str, end_str = raw_range.split('—', 1)
        # Drop timezone (last token) to avoid parsing issues
        def to_dt(s):
            parts = s.strip().split()
            # parts: ['Mon', '2025-06-09', '14:33:12', 'EDT']
            date_part = parts[1]
            time_part = parts[2]
            # Combine date & time
            return datetime.strptime(f"{parts[0]} {date_part} {time_part}", "%a %Y-%m-%d %H:%M:%S")
        try:
            start_dt = to_dt(start_str)
            end_dt   = to_dt(end_str)
            boots.append((start_dt, end_dt, raw_range))
        except Exception:
            continue
    # Sort by start time
    return sorted(boots, key=lambda x: x[0])


def pretty_report(boots, threshold=GAP_THRESHOLD):
    """
    Prints each boot window and inserts a gap annotation when downtime exceeds threshold.
    """
    if not boots:
        print("No boots found.")
        return

    # Print first boot
    first = boots[0]
    print(first[2])  # raw_range

    # Iterate subsequent boots
    for prev, curr in zip(boots, boots[1:]):
        prev_end = prev[1]
        curr_start = curr[0]
        gap_secs = (curr_start - prev_end).total_seconds()
        if gap_secs > threshold:
            hours = gap_secs / 3600
            print(f"[Gap of {hours:.2f} hours]")
        print(curr[2])


def main():
    boots = parse_boots()
    pretty_report(boots)


if __name__ == '__main__':
    main()
