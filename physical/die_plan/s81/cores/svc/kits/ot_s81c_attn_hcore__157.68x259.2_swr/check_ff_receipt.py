#!/usr/bin/env python3
"""Require the isolated FF pass before any cached checkpoint is reused."""
import math
import sys
from pathlib import Path
p=Path(sys.argv[1])
try:
    text=p.read_text().replace("\\t", "\t").replace("\\n", "\n")
    d=dict(line.split("\t",1) for line in text.splitlines() if "\t" in line)
    w=float(d["after_wns_ps"]); n=float(d["after_endpoints"])
    if d.get("basis")!="placement" or not math.isfinite(w) or not math.isfinite(n) or w<0 or n!=0:
        raise ValueError("isolated FF hold is not closed")
    if not p.with_name("repair_ff.odb").is_file():
        raise ValueError("repaired checkpoint missing")
except (OSError, KeyError, ValueError) as e:
    print("HCORE_FF_RECEIPT FAIL:",e);sys.exit(1)
print("HCORE_FF_RECEIPT PASS",w,n)
