# Resume only composition after actual CA/ECTLTABLE passed and missing input pin files were staged.
import json,sys,os
from pathlib import Path
W=Path("/srv/opentallas-scratch2/claude/wt/codex-kv-ectl-1028")
sys.path.insert(0,"/srv/opentallas-scratch2/claude/codex-kv-1028/mixed_source/tools/die_plan")
import count_align_bind as CB
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=True)
b=json.load(open("/srv/opentallas-scratch2/claude/codex-kv-1028/event24/bind.json"))
import clock_landing_plan as LP, gen
I = W / "results/die_kv_7_1028/input"; E = O / "event"; E.mkdir(exist_ok=True)
raw = json.load(open(I / "hm_r26q15d.json")); raw["die"]["io"] = json.load(open(I / "die_io.json"))
table = CB.annotate_table(json.load(open(I / "l128_table.json")), b, strap_form=True)
(E / "regions_ca.json").write_text(json.dumps(table, indent=1) + "\n")
observer = dict(module="qkd_seq_core_static_s", instance_suffix="u_seq_u_core", fault_port="hf", ready_port="lp_run")
plan, side = LP.compose(raw, table, plan_path=I / "hm_r26q15d.json", observer_part="hub_C", observer=observer, monitor="reset",
                        band_reserve="live", forward_source="clk")
for typ in plan["partition_types"].values():
    for h in typ.get("hard_cores", []):
        if h.get("pins_file") and not Path(h["pins_file"]).is_absolute():
            h["pins_file"] = os.path.relpath((I / h["pins_file"]).resolve(), E)
plan["note"] = plan.get("note", "") + " | CODEX-KV-24: actual physical tree c and measured both-edge mixed-clock START graph + core_tx 164.16 + ECTL RT equalisation"
(E / "plan.json").write_text(json.dumps(plan, indent=1) + "\n"); (E / "sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
gen.write_latency(plan, E / "latency", E / "plan.json")
st = CB.strap_ties(side["count_aligned"], plan); (E / "straps.json").write_text(json.dumps(st, indent=1) + "\n")
print("COMPOSE", json.dumps(dict(types=len(plan["partition_types"]), parts=len(plan["partitions"]), straps=st["summary"],
      placement_failures=len(side.get("collector", {}).get("placement_failures", side.get("placement_failures", []))))), flush=True)
