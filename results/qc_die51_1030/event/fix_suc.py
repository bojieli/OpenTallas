"""DIE-QC-51 fix: re-derive su_c landing data AFTER the BTAB P8eco apply (compose_qc52 ran derive before btab apply,
so the stored collector trees of the 3 BTAB types missed the new core outline / rst_n pin).  Same derive/apply."""
import json, sys
from pathlib import Path
EV = Path("results/qc_die51_1030/event/compose_qc52.py")
src = EV.read_text().split("\nap = argparse.ArgumentParser()")[0]
g = {"__file__": str(EV.resolve()), "__name__": "compose_qc52_lib"}; exec(compile(src, str(EV), "exec"), g)
S, RT = g["S"], g["RT"]
plan = Path(sys.argv[1]); raw = json.loads(plan.read_text())
P = S.Plan(json.loads(plan.read_text()), plan.parent / "die_plan.json")
rep = {}
for T in ("sle_su_c", "slw_su_c__cl92142dac", "slw_su_c__cl19bb38ef"):
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    old = json.dumps(lc, sort_keys=True); oldt = lc["collector_tree"]
    d = g["derive"](P, raw, T); g["apply"](raw, T, d)
    new = lc["collector_tree"]
    rep[T] = dict(changed=old != json.dumps(lc, sort_keys=True), relays=[len(oldt["relays"]), len(new["relays"])],
                  depth=[oldt.get("depth"), new.get("depth")], max_hop=[oldt.get("max_hop_um"), new.get("max_hop_um")],
                  children=[c["node"] for c in lc.get("collector_children", [])], rects=list((lc.get("group_rects_um") or {})))
plan.write_text(json.dumps(raw) + "\n")
print(json.dumps(rep, indent=1))
