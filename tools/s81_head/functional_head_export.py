#!/usr/bin/env python3
"""Remove only portless physical TAP cells from an ODB Verilog export for LEC."""
import json
import re
import sys
from pathlib import Path

source, out = map(Path, sys.argv[1:3])
t = source.read_text()
pat = r"(?m)^\s*TAPCELL_ASAP7_75t_R\s+\S+\s*\(\s*\);\s*$"
clean, count = re.subn(pat, "", t)
if "TAPCELL_ASAP7_75t_R" in clean:
    raise SystemExit("Refusing a TAP cell with a functional port or unexpected form")
out.write_text(clean)
out.with_suffix(".physical_only.json").write_text(json.dumps(dict(
    source=str(source), portless_tap_instances_removed=count,
    functional_cells_or_nets_changed=0), indent=1)+"\n")
print("PORTLESS_TAP_EXPORT", count, "functional changes 0")
