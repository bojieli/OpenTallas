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
    ap.add_argument("--name", default=NAME, help="kit name (fallback: hcoll_v7_tkm_m_tp192_lpw)")
    ap.add_argument("--pitch", type=float, default=P, help="child pitch um (fallback 345.6: 86.4-um channels)")
    ap.add_argument("--tile", type=float, default=TILE, help="child outline um (259.2 e86v4; 302.4 e86v4b)")
    a = ap.parse_args()
    P_, TILE_ = a.pitch, a.tile
    W_ = round(2 * O + 5 * P_ + TILE_, 3)
    sc = P_ / P
    lp = json.loads((ROOT / "tools/tkm_lp_1018/tkm_m_tp192_seg_lp.json").read_text())
    sites = lp["plan"]["sites"]
    standin = a.view == STANDIN
    kids = []
    for inst, (c, r) in sorted(sites.items(), key=lambda kv: int(kv[0][3:])):
        kids.append(dict(view=a.view, count=1, inst=inst, at=[round(O + c * P_, 3), round(O + r * P_, 3)],
                         orient="MX" if c % 2 == 0 else "R0"))
    sram = "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2"
    # HBM-TP192 10-20: every IO port on the S face under the SW core region (tkm_SW's die neighbour coll_SW is S), in
    # data-flow order: egress (w_*, status) beside tile 0 / the output cell, ingress (del_*), then start / cfg.  The ctl
    # registers every port at the face (face flops), so no register has two far fixed terminals (gate4: 754 um).
    pins = {"S": ["w_data", "w_mask", "w_addr", "w_v", "busy", "done", "fault", "stat_cycles", "del_flit", "del_valid",
                  "del_slot", "start", "arg_mode", "rst_n", "cfg_n", "cfg_k", "cfg_nout", "cfg_g", "cfg_gbase", "cfg_pf",
                  "cfg_obase", "cfg_rbase", "cfg_has_r", "ck_SE"],
            "W": ["ck_SW"], "N": ["ck_NW", "ck_NE"], "E": []}
    rng = {"w_data": [90.0, 250.0], "w_mask": [252.0, 258.0], "w_addr": [260.0, 276.0], "w_v": [277.0, 277.5],
           "busy": [278.0, 278.5], "done": [279.0, 279.5], "fault": [280.0, 280.5], "stat_cycles": [282.0, 298.0],
           "del_flit": [305.0, 845.0], "del_valid": [847.0, 849.0], "del_slot": [850.0, 852.0], "start": [853.0, 853.5],
           "arg_mode": [854.0, 854.5], "rst_n": [855.0, 855.5], "cfg_n": [857.0, 863.0], "cfg_k": [864.0, 871.0],
           "cfg_nout": [872.0, 879.0], "cfg_g": [880.0, 884.0], "cfg_gbase": [885.0, 889.0], "cfg_pf": [890.0, 898.0],
           "cfg_obase": [899.0, 919.0], "cfg_rbase": [920.0, 940.0], "cfg_has_r": [941.0, 941.5],
           "ck_SE": [round(1446.0 * sc, 1), round(1446.0 * sc, 1) + 0.3], "ck_SW": [round(453.0 * sc, 1), round(453.0 * sc, 1) + 0.3],
           "ck_NW": [round(539.0 * sc, 1), round(539.0 * sc, 1) + 0.3], "ck_NE": [round(1446.0 * sc, 1), round(1446.0 * sc, 1) + 0.3]}
    spec = dict(
        name=a.name, top="ot_hgi_coll_tkm_m_tp192_lp", kind="cluster", diagnostic=standin,
        sources=[f"{C}/lp/ot_hgi_coll_tkm_m_tp192_lp.sv", f"{C}/ot_hgi_coll_tkm_ctl.sv", f"{C}/ot_hgi_coll_tkm_buffer.sv",
                 "rtl/lib/ot_rst_relay.sv", "rtl/common/landed_parent/ot_pl_land.sv", f"{sram}/ot_sram_1r1w_1024x256_m2_r2c2_bb.v",
                 f"{a.view}/ot_hgi_coll_tkm_tile_e86_bb.v" if standin else f"{C}/ot_hgi_coll_tkm_static.sv"],
        params={}, clock="multiple_cts_roots", clock_port="ck_SW", clock_ports=["ck_SW", "ck_NW", "ck_NE", "ck_SE"],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dict(
            core=dict(ratio=[1, 1], ports=["ck_SW"], inputs=[p for p in INS], outputs=[p for p in OUTS]),
            **{r: dict(ratio=[1, 1], ports=[f"ck_{r}"], inputs=[], outputs=[]) for r in ("NW", "NE", "SE")}),
        landed_record=REC, reset_ports=["rst_n"], reset_landing=dict(enable=True, stages=2, clock="ck_SW"),
        outline=dict(w=W_, h=W_, exact=True), child_lattice_um=43.2, children=kids,
        macros=[dict(view=sram, count=1, at=[round(O + 2 * P_ + 43.2, 3), 108.0]), dict(view=sram, count=1, at=[round(O + 2 * P_ + 43.2, 3), 216.0])],
        pins=pins, pin_ranges=rng,
        route=dict(pd=0.5, threads=32, peak_ram_gb=256, pin_v="M5", pin_h="M4 M6", pin_balance=dict(h="M4 M6", v="M5", group_max=1), macro_halo_um=5.4, hold_margin_ns=0.03,
                   io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="HBM-TP192 10-20: every data/control port has a face flop inside the ctl leaf "
                                           "(ot_hgi_coll_tkm_ctl pin stage: in + out); the rest are region clocks / reset"),
        structural_change="PL-TP192 10-18 landed-regions standard: tkm_static's 32-tile chain + buffer + calendar body "
                          "re-built as a landed parent (lp.py): 4 quadrant regions (842-um, one TritonCTS tree each), 7 "
                          "chain seams pre-scheduled in the ctl calendar (SETTLE+42, per-segment conv strobes) and LANDED "
                          "(14 landings, 4-slot, +3 edges, no backpressure); flat lockstep + golden benches. HBM-TP192 "
                          "10-20 after gate4 FAIL 8: ctl face flops on every port + all IO on the S face (reach), ctl "
                          "ingress/re-read pipeline PIPE 4 (depth), kept registered enables/selects (4,226-load capture net). "
                          "HBM-DIEGAP/TP192 10-21: child = e86v4b (302.4 sq, the route the daemon runs); outline ENLARGED "
                          "so every child keeps a channel (main 345.6 pitch / 43.2-um channels, fallback 388.8 / 86.4-um) "
                          "instead of abutting at 302.4; e86 internal-only roots clk_r1/clk_r2 measured on their region "
                          "root (landed internal entries) instead of the hand-edited check-only SDC (OT_LANDED 96/160)",
        job=dict(owner="Claude HBM-DIEGAP/TP192 1021", branch="claude/hbm-tp192-1021", tag="tp192_1021",
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
    out = ROOT / f"tools/tkm_lp_1018/{a.name}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out, len(kids), "children", "STANDIN (diagnostic)" if standin else a.view)


if __name__ == "__main__":
    main()
