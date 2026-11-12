"""ftposcheck.py PLAN TYPE KIT : prove the plan's ft station bit sites survived kit gen (kit ft_bit_sites.tcl stage j = plan
bit_sites_um[j-1]), plus hard-core origins in macro_place.tcl, flow_tag, grt_transition_mode and the run_kit image."""
import json, re, sys
from pathlib import Path

plan, typ, kit = sys.argv[1], sys.argv[2], Path(sys.argv[3])
t = json.load(open(plan))["partition_types"][typ]
txt = (kit / "ft_bit_sites.tcl").read_text()
kd = {}
for m in re.finditer(r"dict set ff_bit_sites \{(\w+),(\d+),(\d+)\} \{([-\d.]+) ([-\d.]+)\}", txt):
    kd[(m.group(1), int(m.group(2)), int(m.group(3)))] = (float(m.group(4)), float(m.group(5)))
tot = bad = miss = 0
per = {}
for f in t["ft_slots"]:
    for j, st in enumerate(f.get("bit_sites_um") or []):
        pts = [p for p in st if isinstance(p, list) and len(p) == 2]
        for b, p in enumerate(pts):
            tot += 1
            k = kd.get((f["name"], j + 1, b))
            if k is None:
                miss += 1; per.setdefault(f["name"], [0, 0])[1] += 1
            elif abs(k[0] - p[0]) > 0.01 or abs(k[1] - p[1]) > 0.01:
                bad += 1; per.setdefault(f["name"], [0, 0])[0] += 1
print(f"FT_SITES plan {tot} kit {len(kd)} mismatch {bad} missing {miss} per-slot {per}")
mp = (kit / "macro_place.tcl").read_text() if (kit / "macro_place.tcl").exists() else ""
cb = 0
for c in t.get("hard_cores", []):
    x, y = c["origin_um"]
    m = re.search(r"[._{]%s\}[^\n]*?-location \{([-\d.]+) ([-\d.]+)\}" % re.escape(c["inst"]), mp)
    if not m or abs(float(m.group(1)) - x) > 0.01 or abs(float(m.group(2)) - y) > 0.01:
        cb += 1; print("CORE_MISMATCH", c["inst"], (x, y), m.group(0)[:160] if m else None)
print(f"CORES {len(t.get('hard_cores', []))} mismatch {cb}")
for fn in ("flow_tag", "grt_transition_mode"):
    p = kit / fn
    print(fn.upper(), p.read_text().strip() if p.exists() else "MISSING")
rk = kit.parent / "run_kit.sh"
imgs = sorted(set(re.findall(r"opentallas/orfs:[\w.-]+|openroad/orfs:[\w.-]+", rk.read_text()))) if rk.exists() else []
print("RUN_KIT_IMAGES", imgs)
print("VERDICT", "PASS" if bad == 0 and miss == 0 and cb == 0 else "FAIL")
