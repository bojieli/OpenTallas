# DIE-HEAD-11 compose start-pin slice: HEAD case (inv2 r200 measured-stage CA bind ca_g5st) -> compose (region monitor)
import json, sys, collections
from pathlib import Path
T = Path(sys.argv[1]); sys.path.insert(0, str(T / "tools/die_plan")); sys.path.insert(0, str(T / "tools/s81_head"))
import count_align_bind as CB, clock_landing_plan as LP, clock_landings as CL
C = Path("/srv/opentallas-scratch2/claude/codex-head-die-1028-0405")
PL = Path("/srv/opentallas-scratch2/claude/wt/codex-head-die-1028-0405/physical/die_plan/s81_head/die_plan.json")
O = Path(sys.argv[2]); O.mkdir(parents=True, exist_ok=True)
b = json.load(open("/srv/opentallas-scratch2/claude/die-head-11/inv/ca_g5st/bind.json"))
tab0 = json.load(open(C / "regions_straps.json")); tab0.pop("count_aligned", None); b = CB.bind_parts(b, CB.table_parts(tab0)); v = CB.verify(b, samples=200); print("VERIFY", v["identity_and_loop_errors"][:3], v["sim_window_violations"])
table = CB.annotate_table(tab0, b, strap_form=True)
plan = json.load(open(PL))
raw, side = LP.compose(plan, table, str(PL), observer_part="ctl", monitor="region")
L = CL.Landings(raw, side)
sp = side["count_aligned"]["start_pins"]
(O / "landed_plan.json").write_text(json.dumps(raw, indent=1) + "\n"); (O / "landed_sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
print("HEAD", json.dumps(dict(types=len(raw["partition_types"]), parts=len(raw["partitions"]),
      start_pins={k: len(v) for k, v in sp.items() if isinstance(v, (list, dict))}, split=L.ca_type_split,
      roles=collections.Counter(c["role"][0] for c in L.ca_type.values()),
      tstart_edges=sum(1 for e in raw["clock"]["landing_network"]["edges"] if e["id"].startswith("cland_tstart__")),
      placement_failures=len(side["collector"]["placement_failures"]))))
