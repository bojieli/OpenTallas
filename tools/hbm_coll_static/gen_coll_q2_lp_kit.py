#!/usr/bin/env python3
"""PL-COLLQ (PARENTS-LANDED 10-18): ref_tile spec for the landed q2 COLL quadrant parent ot_hfd_coll_q2_lp (lp.py output).

Regions (lp spec results/arch/landed_parent_1018/collq/spec_q2.json): sw (switch: fj, ctl, qslots capture x9 + switch
slices x18, issuer, upipe, vmasm, links, reduce) / wr (VM writer, W face beside the VM pins) / rg (ring A: ctl + 8 state +
8 soft add lanes, N face beside the ring lanes and the gather master).  Clock entries: ck_sw on S (host / link face, beside the
switch register mass), ck_wr on W beside the writer, ck_rg on N beside the ring.
Hard children = the CLOSED views (fj_q2, ctl_v5_q2, qcap, qso_q2_b32 / b1, vmwrite roots v6, ring_ag ctl, state-capture
) on the 43.2-um lattice, grouped by region.  Soft (no closed view yet, or pure register slices): issuer_m
(+ its 3 SRAM macros, kit hcoll_v5_issuer still gating), link_e x2 (no view; 4 SRAM banks each, placed), reduce_static (hybrid, no view), the 16+16
upipe / vmasm register slices, the 8 ring add lanes, the landing rings / reads and reset runs.  Outline 1296 x 1036.8 (exact): the 1080 x 880
d4g slot cannot hold these children with 20-um channels on the 43.2 lattice (lattice footprint ~0.65 mm2 hard + soft).

  python3 tools/hbm_coll_static/gen_coll_q2_lp_kit.py [q2|q3]  -> tools/ref_tile/specs_hbm_d4g/hcoll_<v>_lp_1018.json
  q3 (SW, ot_hfd_coll_q3_hard_v8x #(NLINK 2, TP 192)): n2s1 ctl / fj / qso views, capture leaf 9 + TP192 argmax E of
  the ring row, TKM interface pins (tkx_* out on N, tkx_w_* into the writer on W).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIANT = "q2"
LP = json.loads((ROOT / "results/arch/landed_parent_1018/collq/spec_q2.json").read_text())
V = {
    "fj": "physical/ref_tile/hcoll_v5_fj2/views/ot_hgi_coll_fj_q2",
    "ctl": "physical/ref_tile/hcoll_v5_ctl2/views/ot_hgi_coll_ctl_v5_q2",
    "qc": "physical/ref_tile/hcoll_v5_qcap/views/ot_hgi_coll_qslots_capture_pin_v2",
    "qo32": "physical/ref_tile/hcoll_v5_qso2w/views/ot_hgi_coll_qso_q2_b32",
    "qo1": "physical/ref_tile/hcoll_v5_qso2n/views/ot_hgi_coll_qso_q2_b1",
    "wr": "physical/ref_tile/hcoll_vmwrite_static_v6_roots_fsw/views/ot_hgi_coll_static_vmwrite_roots_v6_physical",
    "rctl": "physical/ref_tile/hcoll_ring_ag_ctl_1017/views/ot_hgi_coll_ring_ag_ctl",
    "rst": "physical/ref_tile/hcoll_ring_state_capture_1417/views/ot_hgi_coll_pring_static_state_capture_lane",
    "radd": "physical/ref_tile/hgi_coll_ring_add_r1/views/ot_hgi_coll_pring_static_add_lane",
}
V3 = dict(V, **{   # q3 (SW, SOLO 1, NLINK 2, TP 192): the n2s1 masters + the TP192 argmax leaf
    "fj": "physical/ref_tile/hcoll_v5_fj3/views/ot_hgi_coll_fj_n2s1",
    "ctl": "physical/ref_tile/hcoll_v5_ctl3/views/ot_hgi_coll_ctl_v5_n2s1",
    "qo32": "physical/ref_tile/hcoll_v5_qso3w/views/ot_hgi_coll_qso_n2s1_b32",
    "qo1": "physical/ref_tile/hcoll_v5_qso3n/views/ot_hgi_coll_qso_n2s1_b1",
    "arg": "physical/ref_tile/hcoll_v7_arg_tp192/views/ot_hgi_coll_argmax_m_tp192",
})
TKX_OUT = ["tkx_start", "tkx_arg_mode", "tkx_cfg_n", "tkx_cfg_k", "tkx_cfg_nout", "tkx_cfg_g", "tkx_cfg_gbase", "tkx_cfg_pf",
           "tkx_cfg_obase", "tkx_cfg_rbase", "tkx_cfg_has_r", "tkx_del_slot", "tkx_del_valid", "tkx_del_flit",
           "tkx_busy", "tkx_done", "tkx_fault"]
TKX_W = ["tkx_w_v", "tkx_w_addr", "tkx_w_mask", "tkx_w_data"]
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2"
G = 43.2


def lat(i):
    return round(i * G, 4)


def children():
    c = []
    VV = V3 if VARIANT == "q3" else V
    add = lambda v, inst, x, y: c.append({"view": VV[v], "count": 1, "inst": inst, "at": [lat(x), lat(y)]})
    # sw: switch register mass in the middle; control + fj beside the S host face
    add("ctl", "u_control", 4, 1)                         # 172.8, 43.2 (108 x 280.8)
    add("fj", "u_fj", 8, 1)                               # 345.6, 43.2
    for s in range(9):
        add("qc", f"u_qc{s}", 4 + 2 * s, 9)               # row y 388.8 (25.92 x 129.6), x 172.8 .. 864
    for k in range(9):
        add("qo32", f"u_qo{k}", 4 + 2 * k, 13)            # row y 561.6 (23.76 x 101.52)
    for k in range(9, 12):
        add("qo32", f"u_qo{k}", 22 + 2 * (k - 9), 13)     # x 950.4 / 1036.8 / 1123.2
    for k in range(12, 15):
        add("qo32", f"u_qo{k}", 22 + 2 * (k - 12), 9)     # row y 388.8 E part
    add("qo32", "u_qo15", 8, 5)                           # 345.6, 216
    add("qo32", "u_qo16", 10, 5)                          # 432, 216
    add("qo1", "u_qo17", 12, 5)                           # 518.4, 216
    # wr: the VM writer on the W face (VM banks)
    add("wr", "u_writer", 1, 8)                           # 43.2, 345.6 (103.68 x 388.8)
    # rg: ring A on the N face: state-capture lanes row, control root, add lanes
    for l in range(8):
        add("rst", f"u_rst{l}", 4 + 2 * l, 18)            # row y 777.6 (64.8^2)
    add("rctl", "u_rctl", 13, 20)                         # 561.6, 864 (216 x 129.6)
    if VARIANT == "q3":
        # argmax (reads switch sinks 10-13, its result is capture source 9) + capture leaf 9, E of the ring row, below
        # the E switch slices (qo9-11 end at y 667.4)
        add("arg", "u_arg", 24, 16)                       # 1036.8, 691.2 (95.04 x 47.52)
        add("qc", "u_qc9", 27, 16)                        # 1166.4, 691.2 (25.92 x 129.6)
    # the 8 ring add lanes stay SOFT: their closed view (hgi_coll_ring_add_r1) is also the master of the 16 add lanes
    # inside the soft reduce_static, which instantiates it with #(.LAT(8)) (a hard view takes no overrides)
    return c


def spec():
    srcs = ["rtl/hbm_accel/generic/collective/p2p/landed/ot_hfd_coll_q2_lp.sv", "rtl/common/landed_parent/ot_pl_land.sv"]
    srcs += [f for f in LP["child_sources"] if "asap7_memory_macros/" not in f]
    srcs += [f"{SRAM}/ot_sram_1r1w_64x512_m1_r2c2_bb.v"]
    cks = ["ck_sw", "ck_wr", "ck_rg"]
    ra = ["ra_lp_we", "ra_lp_tag", "ra_lp_data", "ra_state_read_add", "ra_state_read_tx", "ra_state_read_rr",
          "ra_state_add_tag", "ra_state_tx_tag", "ra_state_rr_tag", "ra_state_add_src", "ra_state_add_rhs_acc",
          "ra_state_tx_acc", "ra_add_v", "ra_add_tag", "ra_add_src", "ra_add_rhs_acc", "ra_tx_inject", "ra_tx_forward",
          "ra_tx_tag", "ra_tx_dst", "ra_tx_result", "ra_tx_acc", "ra_tx_gather", "ra_tx_ttl", "ra_rx_slot", "ra_rx_kind",
          "ra_rx_src", "ra_rx_tag", "ra_rr_local", "ra_rr_local_tag"]
    pins = {
        "W": ["vm_rq", "vm_rr", "ck_wr", "vm_kq"] + (TKX_W if VARIANT == "q3" else []),
        "N": ["pr_cw_i", "pr_ccw_o", "isa_ring", "isa_lp_data", "rc_v", "rc_tag", "rc_d"] + ra[:15] + ["ck_rg"] + ra[15:]
             + ["rr_v", "rr_tag", "rr_d", "ag_v", "ag_src", "ag_tag", "ag_d", "pr_ccw_i", "pr_cw_o"]
             + (TKX_OUT if VARIANT == "q3" else []),
        "E": ["inj_rd", "inj_idx", "hgi_inj_addr", "inj_d", "del_valid", "del_flit", "hgi_del_obase"],
        "S": ["cfg_v", "cfg_target", "cfg_addr", "cfg_data", "desc_v", "desc_base", "desc_limit", "desc_loops", "launch_v",
              "program_configured", "program_init_busy", "program_fault", "rst_n", "qid", "ck_sw", "hgi_busy", "hgi_done",
              "hgi_fault", "fault", "fault_cause", "done", "stat_cycles", "phy_up", "tx_pin_v", "tx_pin_flit", "rx_pin_v",
              "rx_pin_flit", "retry_requested"],
    }
    macros = [{"view": SRAM, "count": 1, "inst": f"u_issuer.u_issuer.g_mem[{i}].u_bank.u_sram",
               "at": [1080.0, round(43.2 + i * 77.808, 3)], "at_exact": True} for i in range(3)]
    # link_e x2 (soft) each keep 4 retry-store SRAM banks (g_bank[0..3].u_store.u_native.u_sram): two stacked columns
    # beside the S link pins (tx/rx), between qo17 (x <= 537.8) and the issuer column (x >= 1080); top 354.4 < qc row 388.8
    for l, x in ((0, 561.6), (1, 777.6)):
        macros += [{"view": SRAM, "count": 1, "inst": f"u_link{l}.g_bank[{b}].u_store.u_native.u_sram",
                    "at": [x, round(43.2 + b * 77.808, 3)], "at_exact": True} for b in range(4)]
    w = "results/rtl/landed_parent_1018/collq/bench_witness"
    bench = "bash rtl/hbm_accel/generic/collective/p2p/landed/run_q2_lp_all.sh {RUN}/bench/q2lp"
    return {
        "name": "hcoll_q2_lp_1018",
        "top": "ot_hfd_coll_q2_lp",
        "kind": "cluster",
        "sources": srcs,
        "params": {},
        "clock": "spine",
        "child_clock_ref": "pin",
        "clock_port": cks[0],
        "clock_ports": cks,
        "orfs_vars": {"OT_SPINE_PORTS": ",".join(cks), "OT_SPINE_MACRO_LEAF": "1", "OT_SPINE_MACRO_PIN_LEAF": "1"},
        "sdc_extra": ["rtl/hbm_accel/generic/collective/p2p/landed/ot_hfd_coll_q2_lp.sdc"],
        "reset_ports": ["rst_n"],
        "outline": {"w": 1296.0, "h": 1036.8, "exact": True},
        "macros": macros,
        "children": children(),
        "pins": pins,
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 128, "period_ps": 833.333333, "macro_halo_um": 5.4,
                  "hold_margin_ns": 0.03},
        "structural_change": "PL-COLLQ (PARENTS-LANDED 10-18): the HBM COLL q2 quadrant parent as a LANDED-REGION cluster "
                             "(lp.py): 3 local clock regions sw / wr / rg, 10 landed writer crossings (2,258 b) + 2 loose "
                             "(sticky fault) landings, 1-bit reset runs only; replaces the never-kitted single-tree "
                             "ot_hfd_coll_q2_hard_v8g die SYNTH binding",
        "job": {
            "owner": "Claude:PL-COLLQ",
            "branch": "claude/pl-collq-1018",
            "tag": "lp1",
            "purpose": "HBM COLL q2 quadrant engine parent (SE/NW/NE) as landed regions; contains the critical "
                       "ot_hgi_coll_ctl_v5_q2 leaf: coordinator PNG review before any submit",
            "hold_merge": "critical (ot_hgi_coll_ctl_v5 prefix inside): gate + PNG review only; issuer / link_e / reduce "
                          "views missing (soft here)",
            "submit": False,
            "benches": [
                {"name": "q2lp_lockstep", "cmd": bench, "expect": "pass",
                 "min_count_regex": "Q2_LP_ALL_EXIT (0)", "threads": 16, "peak_ram_gb": 48, "needs": ["verilator"]},
            ],
            "extra_paths": ["results/arch/landed_parent_1018/collq", w],
        },
    }


def spec_q3():
    """q3 (SW) kit = the q2 kit with the q3 lp outputs, the n2s1 / TP192 views, capture leaf 9 + argmax, TKM pins"""
    t = json.dumps(spec())
    for a, b in (("ot_hfd_coll_q2_lp", "ot_hfd_coll_q3_lp"), ("run_q2_lp_all", "run_q3_lp_all"), ("q2lp", "q3lp"),
                 ("hcoll_q2_lp_1018", "hcoll_q3_lp_1018"), ("ot_hfd_coll_q2_hard_v8g", "ot_hfd_coll_q3_hard_v8x"),
                 ("COLL q2 quadrant parent", "COLL q3 (SW, NLINK 2, TP 192) quadrant parent"),
                 ("COLL q2 quadrant engine parent (SE/NW/NE)", "COLL q3 quadrant engine parent (SW, TP 192)"),
                 ("ot_hgi_coll_ctl_v5_q2 leaf", "ot_hgi_coll_ctl_v5_n2s1 leaf")):
        t = t.replace(a, b)
    return json.loads(t)


if __name__ == "__main__":
    import sys
    for v in (sys.argv[1:] or ["q2", "q3"]):
        VARIANT = v
        LP = json.loads((ROOT / f"results/arch/landed_parent_1018/collq/spec_{v}.json").read_text())
        out = ROOT / f"tools/ref_tile/specs_hbm_d4g/hcoll_{v}_lp_1018.json"
        out.write_text(json.dumps(spec() if v == "q2" else spec_q3(), indent=1) + "\n")
        print("wrote", out)
