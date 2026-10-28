"""DIE-KV-4: METHODOLOGY 12.15b spice-calibrated clock for die STA: copy a die_sta_related PROOF dir with every clock-network
arrival (tap late/early, abs_*, node_late/early, cppr_node_range) multiplied by the per-corner OpenSTA->ngspice factor
(opentools/mscts/data/asap7_bufx24_spice_cal.json: TT 1.0485, FF 1.0552).  Data paths untouched (droop derate applies in
die_sta_related as usual).  scale_proof.py SRC DST TT_FACTOR FF_FACTOR"""
import json, shutil, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
fac = dict(TT=float(sys.argv[3]), FF=float(sys.argv[4]))
dst.mkdir(parents=True, exist_ok=True)
for f in src.iterdir():
    if not f.name.startswith("tap_arrivals_"):
        shutil.copy(f, dst / f.name)
for c, s in fac.items():
    d = json.loads((src / f"tap_arrivals_{c}.json").read_text())
    for t in d["taps"]:
        for k in ("late_ps", "early_ps", "abs_late_ps", "abs_early_ps"):
            if k in t:
                t[k] = t[k] * s
    for k in ("node_late_ps", "node_early_ps", "cppr_node_range_ps"):
        if k in d:
            d[k] = {n: v * s for n, v in d[k].items()}
    d["spice_scale"] = dict(factor=s, source="opentools/mscts/data/asap7_bufx24_spice_cal.json (OSS-CLOCK-2 285ba72636)",
                            rule="METHODOLOGY 12.15b")
    (dst / f"tap_arrivals_{c}.json").write_text(json.dumps(d))
print("scaled", fac)
