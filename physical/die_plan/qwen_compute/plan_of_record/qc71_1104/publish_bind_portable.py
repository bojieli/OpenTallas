#!/usr/bin/env python3
"""DIE-QC-71 11-04 (COORD): make a published bind output host-independent. bind.py writes absolute source paths into its
out dir, so kit-rtl on a host without that worktree stops: 'preferred HDL source missing' (bind_tip_i57, 5 rows on intel1).
Repo-relative paths need no tool change: bind.py resolves them against the plan's base (prefer, bindf_prefer), and
kit_wave runs kit-rtl from the source tree. Also drops the worktree prefix from bound RTL source comments.

    publish_bind_portable.py OUT WORKTREE
"""
import sys
from pathlib import Path

out, root = Path(sys.argv[1]), sys.argv[2].rstrip("/") + "/"
tot = 0
for f in [out / n for n in ("bind.f", "bind_report.json", "asbuilt_sources.json", "asbuilt.json", "asbuilt.ys")] + sorted((out / "rtl").glob("*.sv")):
    t = f.read_text(errors="surrogateescape")
    n = t.count(root)
    if n:
        f.write_text(t.replace(root, ""), errors="surrogateescape")
    tot += n
    print(f.name, n) if not f.suffix == ".sv" else None
print("replaced", tot)
