#!/usr/bin/env python3
"""HEAD-94 pre-check (plan geometry vs kit band / PDN), advisory class check run before kits launch.
 usage: precheck.py PLAN.json REPO [--types t1,t2]
 A. every site/rect/xy of a type lies inside its outline (landing_status_anchors, bands, stages, taps, sink sites ...)
    -> 'OT_CLAND no legal nonoverlapping row/site in reserved band' when an anchor/band is outside or off the band.
 B. every hard-core LEF has sparse (not solid) M6/M7 OBS: a single OBS rect covering >50% of the macro on M6 or M7 blocks the
    die PDN M6/M7 straps from the core's M5 PG stripes ('PDN-0006 VDD on M5 is blocked by obstructions on M6, M7')."""
import json, re, sys
from pathlib import Path
plan = json.load(open(sys.argv[1])); repo = Path(sys.argv[2])
only = sys.argv[sys.argv.index("--types") + 1].split(",") if "--types" in sys.argv else list(plan["partition_types"])
SKIP = {"outline_um", "origin_um", "die_islands_um", "window_um", "track_offset_um", "span_um", "range_um"}
bad = 0
def num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
for tn in only:
    t = plan["partition_types"][tn]; W, H = t["outline_um"]
    out = []
    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in SKIP: continue
                walk(v, p + "/" + k)
        elif isinstance(o, list):
            if len(o) == 2 and all(num(x) for x in o) and re.search(r"(xy|_um|sites|anchors|stages|taps)", p):
                x, y = o
                if x < -0.01 or y < -0.01 or x > W + 0.01 or y > H + 0.01: out.append((p, o))
            elif len(o) == 4 and all(num(x) for x in o) and p.endswith("rect_um"):
                x0, y0, x1, y1 = o
                if x0 < -0.01 or y0 < -0.01 or x1 > W + 0.01 or y1 > H + 0.01: out.append((p, o))
            else:
                for i, v in enumerate(o): walk(v, p + "[]")
    walk(t, "")
    for p, o in out[:12]:
        print(f"A-FAIL {tn} outside outline {W}x{H}: {p} {o}")
    bad += len(out)
    for h in t.get("hard_cores", []):
        lef = repo / h["lef"]
        if not lef.is_file(): continue
        txt = lef.read_text()
        if "OBS" not in txt: continue
        sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt); area = float(sz[1]) * float(sz[2])
        cur = None; ar = {}
        for ln in txt[txt.index("OBS"):].splitlines():
            m = re.match(r"\s*LAYER (\w+)", ln)
            if m: cur = m[1]; continue
            r = re.match(r"\s*RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)", ln)
            if r and cur in ("M6", "M7"):
                a = list(map(float, r.groups())); ar[cur] = max(ar.get(cur, 0), (a[2] - a[0]) * (a[3] - a[1]) / area)
        if any(v > 0.5 for v in ar.values()):
            print(f"B-FAIL {tn} {h['module']} LEF {h['lef']}: largest single M6/M7 OBS rect {ar} of the macro (solid): PDN-0006"); bad += 1
print("PRECHECK", "FAIL" if bad else "PASS", bad)
