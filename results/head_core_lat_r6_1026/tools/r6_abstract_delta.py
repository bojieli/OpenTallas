#!/usr/bin/env python3
"""HEAD-CORE-LAT-R6: elemB die-abstract delta (for the S81-HEAD plan owner to fold in).
usage: r6_abstract_delta.py KIT_R6 OLD_PINS_JSON(die cores/elemB_pins.json) DEAD_JSON OUTDIR
Writes OUTDIR/elemB_pins_r6.json (die pins-file format, kit outline 285.12 coordinates, incl. the 9 12.2a1 island
feed-through ports) and OUTDIR/abstract_delta.json (what changes vs the die-bound 458-port abstract)."""
import json, re, sys
from pathlib import Path
kit, oldp, dead, out = map(Path, sys.argv[1:5])
out.mkdir(parents=True, exist_ok=True)
nm = lambda p: p["bus"] if p["bus"] in ("go", "o_v", "fault", "b_v", "rst_n", "clk") else f'{p["bus"]}[{p["bit"]}]'
pins = json.loads((kit / "pins.json").read_text())
new = [dict(name=nm(p), layer=p["layer"], x=p["x"], y=p["y"]) for p in pins]
ft = []
for l in (kit / "io.tcl").read_text().splitlines():
    m = re.search(r"-pin_name \{(ft_\w+|rst_n|clk)\} -layer (\S+) -location \{(\S+) (\S+)\}", l)
    if m:
        ft.append(dict(name=m[1], layer=m[2], x=float(m[3]), y=float(m[4])))
names = {p["name"] for p in new}
new += [p for p in ft if p["name"] not in names]
old = json.loads(oldp.read_text())["pins"]
on, nn = {p["name"] for p in old}, {p["name"] for p in new}
(out / "elemB_pins_r6.json").write_text(json.dumps(dict(
    source="HEAD-CORE-LAT-R6 kit elemB_r6 io.tcl (outline 285.12; not yet a built abstract)", pins=sorted(new, key=lambda p: p["name"])), indent=1) + "\n")
d = json.loads(dead.read_text())
delta = dict(
    schema="opentallas.s81_head.elemB_abstract_delta.v1", numbers="UNCHECKED",
    module="ot_s81hd_elemB_cv", outline_um=[285.12, 285.12], outline_die_plan_now=[277.652, 277.652],
    ports_old=len(on), ports_new=len(nn),
    removed=sorted(on - nn), added=sorted(nn - on),
    island_ft_ports_12_2a1=[p for p in ft if p["name"].startswith("ft_")],
    clk_note="12.2a1 pushdown: the core clock enters on ft_mstrap_i (island root); the RTL clk port is replaced by the "
             "island, so clk is not a die-abstract pin of the built macro (as elemA v4q).",
    moved_N_to_S=json.loads((kit / "R6_KIT.json").read_text())["moved_to_S"],
    dead_inputs=dict(ports=d["ports"], proof="results/head_core_lat_r6_1026/elemB/dead_inputs.json",
                     method=d["method"], verdict=d["verdict"],
                     parent_tie="ot_s81hd_bundle g_cvb.u_eB .row0(17'd0) .b_v(1'b0) .b_d(32'd0)"),
    views="LEF/liberty physical/die_plan/s81_head/cores/views/ot_s81hd_elemB_cv must be REGENERATED from the R6 elemB "
          "built abstract (no hand-edited timing for ft ports); die_plan.json hd_tile hard_cores[u_eB] outline/pins_file "
          "-> plan owner")
(out / "abstract_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
print("old", len(on), "new", len(nn), "removed", len(on - nn), "added", sorted(nn - on))
