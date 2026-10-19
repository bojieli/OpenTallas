#!/usr/bin/env python3
"""PL-TP192 (10-18): tools/ref_tile spec of the landed TKM TP192 sub-cluster ot_hgi_coll_tkm_m_tp192_lp.

Children = 32 e86 tiles at the gen_tkm_seg.py sites on the 43.2-um lattice: pitch 302.4 (259.2 tile + 43.2 channel),
array origin (86.4, 86.4), outline 1944 x 1944 (45 x 43.2).  Even columns MX (chain runs up: ins / up_out on S), odd
columns R0 (chain runs down).  ctl (soft) + landing halves (soft) between; buffer SRAMs (2 x 1024x256) at site (2,0).
Clock: PL-KIT landed-cluster form (origin/main 112f518d5): clock "multiple_cts_roots", one TritonCTS tree per region root
ck_SW (core) / NW / NE / SE, "landed_record" = the lp.py record (ref_tile emits the 14 landing multicycles itself: no
sdc_extra), related_same_frequency same_pll_fixed_phase; every e86 clock pin (clk, clk_r0..r3) is a sink of its region
root, judged at e86 flops via its insertion.json (pre_route_gate per root, TT AND FF <= 80 ps).  All IO is in SW.  Pins: del_* + cfg S (ingress from
coll_SW), w_* + status W (egress to coll_SW vmwrite), region clocks beside each region's register mass.

    kit_spec.py [--view DIR]   (default: the diagnostic stand-in physical/ref_tile/hcoll_v7_tkm_m_tp192_lp/standin/...;
                                pass the CLOSED e86 view dir once hcoll_v7_tkm_tile_e86 routes)
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = "hcoll_v7_tkm_m_tp192_lp"
P, O, TILE = 302.4, 86.4, 259.2
C = "rtl/hbm_accel/generic/collective/tkm"
STANDIN = f"physical/ref_tile/{NAME}/standin/ot_hgi_coll_tkm_tile_e86"
REC = "results/arch/pl_tp192_1018/ot_hgi_coll_tkm_m_tp192_lp_record.json"
INS = ["rst_n", "start", "arg_mode", "cfg_n", "cfg_k", "cfg_nout", "cfg_g", "cfg_gbase", "cfg_pf", "cfg_obase", "cfg_rbase",
       "cfg_has_r", "del_slot", "del_valid", "del_flit"]
OUTS = ["w_v", "w_addr", "w_mask", "w_data", "busy", "done", "fault", "stat_cycles"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", default=STANDIN)
    a = ap.parse_args()
    lp = json.loads((ROOT / "tools/tkm_lp_1018/tkm_m_tp192_seg_lp.json").read_text())
    sites = lp["plan"]["sites"]
    standin = a.view == STANDIN
    kids = []
    for inst, (c, r) in sorted(sites.items(), key=lambda kv: int(kv[0][3:])):
        kids.append(dict(view=a.view, count=1, inst=inst, at=[round(O + c * P, 3), round(O + r * P, 3)],
                         orient="MX" if c % 2 == 0 else "R0"))
    sram = "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2"
    pins = {"S": ["del_flit", "del_valid", "del_slot", "start", "arg_mode", "rst_n", "cfg_n", "cfg_k", "cfg_nout", "cfg_g",
                  "cfg_gbase", "cfg_pf", "cfg_obase", "cfg_rbase", "cfg_has_r", "ck_SE"],
            "W": ["w_v", "w_addr", "w_mask", "w_data", "ck_SW", "busy", "done", "fault", "stat_cycles"],
            "N": ["ck_NW", "ck_NE"], "E": []}
    rng = {"del_flit": [90.0, 640.0], "del_valid": [645.0, 650.0], "del_slot": [652.0, 657.0], "start": [660.0, 661.0],
           "arg_mode": [662.0, 663.0], "rst_n": [664.0, 665.0], "cfg_n": [670.0, 700.0], "cfg_k": [702.0, 730.0],
           "cfg_nout": [732.0, 760.0], "cfg_g": [762.0, 780.0], "cfg_gbase": [782.0, 800.0], "cfg_pf": [802.0, 840.0],
           "cfg_obase": [842.0, 940.0], "cfg_rbase": [942.0, 1040.0], "cfg_has_r": [1042.0, 1043.0],
           "ck_SE": [1446.0, 1446.3],
           "w_v": [100.0, 101.0], "w_addr": [105.0, 200.0], "w_mask": [205.0, 245.0], "w_data": [250.0, 520.0],
           "ck_SW": [539.0, 539.3], "busy": [560.0, 561.0], "done": [563.0, 564.0], "fault": [566.0, 567.0],
           "stat_cycles": [570.0, 650.0], "ck_NW": [539.0, 539.3], "ck_NE": [1446.0, 1446.3]}
    spec = dict(
        name=NAME, top="ot_hgi_coll_tkm_m_tp192_lp", kind="cluster", diagnostic=standin,
        sources=[f"{C}/lp/ot_hgi_coll_tkm_m_tp192_lp.sv", f"{C}/ot_hgi_coll_tkm_ctl.sv", f"{C}/ot_hgi_coll_tkm_buffer.sv",
                 "rtl/lib/ot_rst_relay.sv", "rtl/common/landed_parent/ot_pl_land.sv", f"{sram}/ot_sram_1r1w_1024x256_m2_r2c2_bb.v",
                 f"{a.view}/ot_hgi_coll_tkm_tile_e86_bb.v" if standin else f"{C}/ot_hgi_coll_tkm_static.sv"],
        params={}, clock="multiple_cts_roots", clock_port="ck_SW", clock_ports=["ck_SW", "ck_NW", "ck_NE", "ck_SE"],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dict(
            core=dict(ratio=[1, 1], ports=["ck_SW"], inputs=[p for p in INS], outputs=[p for p in OUTS]),
            **{r: dict(ratio=[1, 1], ports=[f"ck_{r}"], inputs=[], outputs=[]) for r in ("NW", "NE", "SE")}),
        landed_record=REC, reset_ports=["rst_n"],
        outline=dict(w=1944.0, h=1944.0, exact=True), child_lattice_um=43.2, children=kids,
        macros=[dict(view=sram, count=1, at=[734.4, 108.0]), dict(view=sram, count=1, at=[734.4, 216.0])],
        pins=pins, pin_ranges=rng,
        route=dict(pd=0.5, threads=32, peak_ram_gb=256, pin_v="M5", pin_h="M4 M6", macro_halo_um=5.4, hold_margin_ns=0.03,
                   io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="every port is registered in the ctl leaf (del_flit beat / cfg capture / w_* "
                                           "output regs) or is a region clock / reset"),
        structural_change="PL-TP192 10-18 landed-regions standard: tkm_static's 32-tile chain + buffer + calendar body "
                          "re-built as a landed parent (lp.py): 4 quadrant regions (842-um, one TritonCTS tree each), 7 "
                          "chain seams pre-scheduled in the ctl calendar (SETTLE+42, per-segment conv strobes) and LANDED "
                          "(14 landings, 4-slot, +3 edges, no backpressure); flat lockstep + golden benches",
        job=dict(owner="Claude PL-TP192 1018", branch="claude/pl-tp192-1018", tag="pl1018",
                 purpose="HBM d4g tkm_SW sub-cluster (TP192 top-k merge, 32 x e86) as a landed parent",
                 submit=not standin, extra_paths=[str(Path(REC).parent)],   # the landed_record (ref_tile reads it in the loop)
                 **({"hold_merge": "diagnostic: e86 stand-in abstract (standin_from_gate.py) until "
                                                       "hcoll_v7_tkm_tile_e86 closes"} if standin else {}),
                 benches=[dict(name="tkm_tp192_lp_lockstep", expect="pass",
                               cmd="LP_ROOT=$PWD SIM=verilator MAKEFLAGS='--eval=.NOTPARALLEL: hier_build' LP_VFLAGS='--timing --hierarchical rtl/hbm_accel/generic/"
                                   "collective/tkm/tkm_tp192_hier.vlt -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT' "
                                   f"bash {C}/lp/ot_hgi_coll_tkm_m_tp192_lp_bench.sh bench_out/lockstep"),
                          dict(name="tkm_tp192_seg_golden", expect="pass", cmd=f"bash {C}/run_tp192_seg.sh bench_out/golden")]),
        inter=[])
    out = ROOT / f"tools/tkm_lp_1018/{NAME}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out, len(kids), "children", "STANDIN (diagnostic)" if standin else a.view)


if __name__ == "__main__":
    main()
