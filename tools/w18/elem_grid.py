#!/usr/bin/env python3
"""W18: element-level power-grid sweep -- how much of the V4.1 ROM pair's own IR drop a denser or wider grid
removes, measured with OpenROAD pdngen + PSM on a synthetic logic window at the pair's measured power density.

The routed W10 p5 pair cannot be re-gridded after routing, so the sweep uses a W x H window of standard-cell
rows with the pair's grid construction (M1/M2 followpins, M5/M6 straps, optionally M7 straps as the new top
power layer) and uniformly spread load cells (TAPCELLs carrying set_pdnsim_inst_power) at the pair's logic power
density.  Sources are the top-layer straps (STRAPS), as in the pair PSM.  The baseline configuration is checked
against the routed pair's measured worst drop; each variant reports its drop and its track cost.

    python3 tools/w18/elem_grid.py --run-dir D --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
PAIR = ROOT / "results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json"
LOGIC_UM2 = 210.012 * 127.44          # the pair's logic strip (W10 p5 floorplan)
VARIANTS = {
    "base":        dict(m5=(0.12, 5.4), m6=(0.288, 5.4), m7=None),
    "m5x2":        dict(m5=(0.12, 2.7), m6=(0.288, 5.4), m7=None),
    "m6x2":        dict(m5=(0.12, 5.4), m6=(0.288, 2.7), m7=None),
    "m5m6x2":      dict(m5=(0.12, 2.7), m6=(0.288, 2.7), m7=None),
    "m6wide":      dict(m5=(0.12, 5.4), m6=(0.544, 5.4), m7=None),
    "m7top":       dict(m5=(0.12, 5.4), m6=(0.288, 5.4), m7=(0.544, 10.8)),
    "m5m6x2_m7":   dict(m5=(0.12, 2.7), m6=(0.288, 2.7), m7=(0.544, 10.8)),
    "m5x2_m6w_m7": dict(m5=(0.12, 2.7), m6=(0.544, 5.4), m7=(0.544, 5.4)),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tcl(v: dict, w: float, h: float, watts: float, step: float) -> str:
    top = "M7" if v["m7"] else "M6"
    lines = [f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef", f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef",
             f"read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz",
             "read_def /run/top.def", "set block [ord::get_db_block]",
             f"initialize_floorplan -die_area {{0 0 {w} {h}}} -core_area {{0 0 {w} {h}}} -site asap7sc7p5t",
             f"source {PLAT}/openRoad/make_tracks.tcl",
             "set master [[ord::get_db] findMaster TAPCELL_ASAP7_75t_R]", "set n 0",
             "foreach r [$block getRows] {",
             "  set y [lindex [$r getOrigin] 1]; set o [$r getOrient]",
             f"  for {{set x 1000}} {{$x < {int(w * 1000) - 2000}}} {{incr x {int(step * 1000)}}} {{",
             "    set i [odb::dbInst_create $block $master t$n]; $i setOrient $o; $i setLocation $x $y; $i setPlacementStatus FIRM; incr n } }",
             'puts "OT_CELLS $n"',
             "add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power",
             "add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground",
             "set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}",
             f"define_pdn_grid -name {{g}} -voltage_domains {{CORE}} -pins {{{top}}}",
             "add_pdn_stripe -grid {g} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins",
             "add_pdn_stripe -grid {g} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins",
             f"add_pdn_stripe -grid {{g}} -layer {{M5}} -width {{{v['m5'][0]}}} -spacing {{{v['m5'][1] / 2 - v['m5'][0]:.3f}}} -pitch {{{v['m5'][1]}}} -offset {{0.3}}",
             f"add_pdn_stripe -grid {{g}} -layer {{M6}} -width {{{v['m6'][0]}}} -spacing {{{v['m6'][1] / 2 - v['m6'][0]:.3f}}} -pitch {{{v['m6'][1]}}} -offset {{0.513}}",
             "add_pdn_connect -grid {g} -layers {M1 M2}", "add_pdn_connect -grid {g} -layers {M2 M5}",
             "add_pdn_connect -grid {g} -layers {M5 M6}"]
    if v["m7"]:
        lines += [f"add_pdn_stripe -grid {{g}} -layer {{M7}} -width {{{v['m7'][0]}}} -spacing {{{v['m7'][1] / 2 - v['m7'][0]:.3f}}} -pitch {{{v['m7'][1]}}} -offset {{1.0}}",
                  "add_pdn_connect -grid {g} -layers {M6 M7}"]
    lines += ['if {[catch {pdngen} err]} { puts "OT_PDN FAIL $err" } else { puts "OT_PDN PASS" }',
              "set_cmd_units -power W", f"source {PLAT}/setRC.tcl",
              f"set per [expr {{{watts} / $n}}]",
              "foreach i [$block getInsts] { set_pdnsim_inst_power -inst [$i getName] -power $per }",
              "foreach net {VDD VSS} { set_pdnsim_net_voltage -net $net -voltage [expr {$net eq \"VDD\" ? 0.7 : 0.0}]",
              "  if {[catch {analyze_power_grid -net $net -source_type STRAPS -allow_reuse} err]} { puts \"OT_IR $net FAIL $err\" } }",
              "exit"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--window-um", type=float, default=108.0)
    ap.add_argument("--pair-w", type=float, default=0.2663, help="busy pair W at 1.2 GHz")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    a = ap.parse_args(argv)
    pr = json.loads(PAIR.read_text())
    macro_w = pr["power_w_per_pair"]["breakdown"]["busy_in0p5"]["macro"]["total_w"] * 1.16
    density = (a.pair_w - macro_w) / LOGIC_UM2                   # W per um2 of logic
    wv = a.window_um
    watts = density * wv * wv
    run = a.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=True)
    res = {}
    procs = {}
    for k in a.variants.split(","):
        d = run / k
        d.mkdir(exist_ok=True)
        (d / "run.tcl").write_text(tcl(VARIANTS[k], wv, wv, watts, 2.16))
        (d / "top.def").write_text("VERSION 5.8 ;\nDIVIDERCHAR \"/\" ;\nBUSBITCHARS \"[]\" ;\nDESIGN w18_eg ;\n"
                                   f"UNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( {int(wv * 1000)} {int(wv * 1000)} ) ;\n"
                                   "END DESIGN\n")
        procs[k] = subprocess.Popen(["docker", "run", "--rm", "--memory=20g", "-v", f"{d}:/run", IMAGE, "bash", "-c",
                                     f"{OPENROAD} -exit -no_init /run/run.tcl > /run/openroad.log 2>&1"])
    for k, p in procs.items():
        p.wait()
        log = (run / k / "openroad.log").read_text()
        worst = re.findall(r"Worstcase IR drop\s*:\s*([-0-9.eE+]+)", log)
        avg = re.findall(r"Average IR drop\s*:\s*([-0-9.eE+]+)", log)
        v = VARIANTS[k]
        tracks = {"M5": round(2 * v["m5"][0] / v["m5"][1], 3), "M6": round(2 * v["m6"][0] / v["m6"][1], 3),
                  "M7": round(2 * v["m7"][0] / v["m7"][1], 3) if v["m7"] else 0.0}
        res[k] = dict(grid=v, power_track_share=tracks,
                      worst_mv=dict(VDD=round(float(worst[0]) * 1e3, 2) if worst else None,
                                    VSS=round(float(worst[1]) * 1e3, 2) if len(worst) > 1 else None),
                      average_mv=dict(VDD=round(float(avg[0]) * 1e3, 3) if avg else None),
                      pdn="PASS" if "OT_PDN PASS" in log else "FAIL", cells=re.findall(r"OT_CELLS (\d+)", log))
    rec = dict(schema="opentallas.v41.w18_element_grid_sweep.v1", window_um=[wv, wv], watts=round(watts, 5),
               logic_power_density_w_per_mm2=round(density * 1e6, 2), pair_w=a.pair_w,
               measured_pair_worst_mv=pr["ir"]["VDD"]["worst_ir_drop_v"] * 1e3 * a.pair_w /
               pr["power_w_per_pair"]["scenarios"]["default"],
               variants=res, pair_record_sha256=sha(PAIR), tool_sha256=sha(Path(__file__)),
               basis="synthetic window: uniform load at the pair's measured logic power density, grid built as the "
                     "ORFS asap7 M1-M2-M5-M6 strategy the pair uses; sources on the top power layer (the pair's pins)")
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: (v["worst_mv"], v["power_track_share"], v["pdn"]) for k, v in res.items()}, indent=1),
          "measured pair", rec["measured_pair_worst_mv"])


if __name__ == "__main__":
    main()
