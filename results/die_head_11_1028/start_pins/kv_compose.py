# DIE-HEAD-11 compose start-pin slice: KV second test case (DIE-KV-13 ev1 bind -> compose -> straps -> landing RTL)
import json, sys, os
from pathlib import Path
T = Path(sys.argv[1]); sys.path.insert(0, str(T / "tools/die_plan"))
import count_align_bind as CB, clock_landing_plan as LP, clock_landings as CL
W = Path("/srv/opentallas-scratch2/claude/wt/die-kv-6"); I = W / "results/die_kv_7_1028/input"
K = Path("/srv/opentallas-scratch2/claude/die-kv-13-1028"); O = Path(sys.argv[2]); O.mkdir(parents=True, exist_ok=True)
b = json.load(open(K / "ev1/bind.json"))
raw = json.load(open(I / "hm_r26q9d.json")); raw["die"]["io"] = json.load(open(I / "die_io.json"))
table = CB.annotate_table(json.load(open(I / "l128_table.json")), b, strap_form=True)
observer = dict(module="qkd_seq_core_static_s", instance_suffix="u_seq_u_core", fault_port="hf", ready_port="lp_run")
plan, side = LP.compose(raw, table, plan_path=I / "hm_r26q9d.json", observer_part="hub_C", observer=observer, monitor="reset",
                        band_reserve="live")
st = CB.strap_ties(side["count_aligned"], plan)
sp = side["count_aligned"]["start_pins"]
(O / "plan.json").write_text(json.dumps(plan, indent=1) + "\n"); (O / "sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
(O / "straps.json").write_text(json.dumps(st, indent=1) + "\n")
L = CL.ClockLandings(plan, side) if hasattr(CL, "ClockLandings") else None
print("COMPOSE", json.dumps(dict(types=len(plan["partition_types"]), parts=len(plan["partitions"]), straps=st["summary"],
      start_pins={k: len(v) for k, v in sp.items() if isinstance(v, (list, dict))},
      tstart_plan_ports=sum(1 for p in plan["ports"] if p["id"].startswith("cland_tstart__")))))
