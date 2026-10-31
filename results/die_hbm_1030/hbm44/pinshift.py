#!/usr/bin/env python3
"""DIE-HBM-44 freeze-event one-block delta: shift the seam pin window of a ft slot pair (out of type A, in of type B)
so the FF->seam pin->FF hop is the direct Manhattan hop. Window width/layers/order unchanged; shift is a multiple of
0.576 um (= 12 x M4 0.048 = 9 x M6 0.064 pitch). Writes OUT/die_plan.json (+ symlinks) and pinshift_report.json.
usage: pinshift.py PLAN_DIR OUT_DIR TYPE_A:SLOT:out:TYPE_B:SLOT:in:DELTA_UM ..."""
import json, sys, os, hashlib
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
p = json.loads((src / "die_plan.json").read_text()); T = p["partition_types"]
rep = {"schema": "opentallas.die_hbm_44.pinshift.v1", "base_sha256": hashlib.sha256((src / "die_plan.json").read_bytes()).hexdigest(), "moves": []}
def wins(t):
    for kind in ("buses", "ft_slots", "spare_slots"):
        for s in t.get(kind, []):
            if "face" in s and "window_um" in s: yield s["face"], s["window_um"], s["name"]
            for io in ("in", "out"):
                if s.get(io + "_face") and s.get(io + "_window_um"): yield s[io + "_face"], s[io + "_window_um"], s["name"] + "." + io
for spec in sys.argv[3:]:
    ta, sa, ia, tb, sb, ib, d = spec.split(":"); d = float(d)
    assert abs(d / 0.576 - round(d / 0.576)) < 1e-6, d
    for tn, sn, io in ((ta, sa, ia), (tb, sb, ib)):
        s = [x for x in T[tn]["ft_slots"] if x["name"] == sn][0]
        assert "bit_sites_um" not in s
        old = list(s[io + "_window_um"]); new = [round(old[0] + d, 4), round(old[1] + d, 4)]
        face = s[io + "_face"]; L = T[tn]["outline_um"][1 if face in ("E", "W") else 0]
        assert 0 <= new[0] and new[1] <= L, (tn, sn, new, L)
        clash = [(n, w) for f, w, n in wins(T[tn]) if f == face and n != sn + "." + io and w[1] + 2.0 > new[0] and w[0] - 2.0 < new[1]]
        assert not clash, (tn, sn, clash)
        s[io + "_window_um"] = new
        s["note"] = s.get("note", "") + f" | DIE-HBM-44 freeze fold: {io} window {old} -> {new} (seam hop to direct)"
        rep["moves"].append(dict(type=tn, slot=sn, io=io, face=face, old=old, new=new, delta_um=d))
out.mkdir(parents=True, exist_ok=True)
for f in os.listdir(src):
    if f in ("die_plan.json", "pinshift_report.json") or (out / f).exists(): continue
    os.symlink(os.path.realpath(src / f), out / f)
(out / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
rep["plan_sha256"] = hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()
(out / "pinshift_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep, indent=1))
