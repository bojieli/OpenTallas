#!/usr/bin/env python3
"""print type<TAB>max_nontap<TAB>stage_of_max<TAB>mtime<TAB>path for the newest HBM kit cell_census.jsonl per type"""
import glob, json, os, socket
best = {}
pats = ["/srv/opentallas-scratch*/claude/*/runs/hbm/kit-wave/hbm/*/items/*/attempt_*/gen/*/cell_census.jsonl",
        "/srv/opentallas-scratch*/claude/*/runs/hbm/kit-wave/hbm/*/items/*/gen/*/cell_census.jsonl",
        "/srv/opentallas-scratch*/claude/*/*/gen/*/cell_census.jsonl", "/srv/opentallas-scratch*/claude/*/*/*/gen/*/cell_census.jsonl"]
for pat in pats:
    for f in glob.glob(pat):
        parts = f.split("/")
        tn = parts[parts.index("items") + 1] if "items" in parts else parts[parts.index("gen") + 1]
        try:
            m = os.path.getmtime(f)
        except OSError:
            continue
        if tn in best and best[tn][0] >= m:
            continue
        mx, st = 0, ""
        try:
            for line in open(f):
                d = json.loads(line)
                v = int(d.get("nontap") or 0)
                if v >= mx:
                    mx, st = v, d.get("stage", "")
        except Exception:  # noqa: BLE001
            continue
        if mx:
            best[tn] = (m, mx, st, f)
h = socket.gethostname()
for tn, (m, mx, st, f) in sorted(best.items()):
    print(f"{tn}\t{mx}\t{st}\t{int(m)}\t{h}:{f}")
