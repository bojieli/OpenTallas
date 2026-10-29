# DIE-KV-23: move the composed event (run dir ev/event) into results/die_kv_23_1028/event0 (pins_file paths re-based),
# then pv_pair_lc_plan (DIE-KV-19 b2, copied) -> results/die_kv_23_1028/event/plan.json; other event files copied.
import json, os, shutil, sys
from pathlib import Path
src = Path(sys.argv[1]); W = Path(sys.argv[2]); R = W / "results/die_kv_23_1028"
e0 = R / "event0"; e0.mkdir(parents=True, exist_ok=True)
p = json.load(open(src / "plan.json")); n = 0
for t in p["partition_types"].values():
    for h in t.get("hard_cores", []):
        pf = h.get("pins_file")
        if pf and not Path(pf).is_absolute():
            a = (src / pf).resolve(); assert a.is_file(), a
            h["pins_file"] = os.path.relpath(a, e0); n += 1
(e0 / "plan.json").write_text(json.dumps(p, indent=1) + "\n")
for f in ("sidecar.json", "regions_ca.json", "straps.json"):
    shutil.copy(src / f, e0 / f)
shutil.copytree(src / "latency", e0 / "latency", dirs_exist_ok=True)
print("rebased pins_file", n)
