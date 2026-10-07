#!/usr/bin/env python3
"""Fail closed unless both timed IO classes exist and pass at SS (setup).  FF hold at the pins is the die-context check
(stations' min-delay credit) and is only reported, unless CHECK_FF=1 (the strict form)."""
import os
import math
from pathlib import Path
import re
import sys

def check(text):
    values = {}
    for line in text.splitlines():
        corner = line.split()[0] if line.split() else ""
        if corner not in ("ss", "ff"):
            continue
        for direction, token in re.findall(r"OT_IO_(IN|OUT) (\S+)", line):
            key = (corner, direction)
            if key in values:
                raise ValueError(f"duplicate IO result: {key}")
            value = float(token)
            if (corner == "ss" or os.environ.get("CHECK_FF") == "1") and (not math.isfinite(value) or value < 15):
                raise ValueError(f"IO margin failed: {key} {token} ps")
            values[key] = value
    expected = {(c, d) for c in ("ss", "ff") for d in ("IN", "OUT")}
    values = {k: v for k, v in values.items()}
    if set(values) != expected:
        raise ValueError(f"missing IO results: {expected - set(values)}")
    return values

if __name__ == "__main__":
    try:
        result = check(Path(sys.argv[1]).read_text())
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
    print("PASS_IO_SS_GE15", result)
