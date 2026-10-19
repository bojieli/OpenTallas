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

TW2-COLLAR (10-19): --ar128 -> tools/ref_tile/specs_hbm_d4g/hcoll_<v>_lp_ar128.json for ot_hfd_coll_<v>_lp_ar (XDIE-HBM4
  AR_ITER 1 / ROWS 128, lp spec spec_<v>_ar.json): issuer 6 SRAMs (3 banks x u_sram + g128.u_sram_hi, the yosys names) in
  ONE column E (x 1080, y 43.2 .. 510), qo13 / qo14 moved to (1209.6, 561.6) / (950.4, 691.2); fj #(ROWS 128) has
  no closed view (hcoll_v5_fj*_r128 gate only) -> soft; u_ariter (soft, region sw) beside u_reduce / u_control.
  The default output (no option) is unchanged.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIANT = "q2"
AR = False          # TW2-COLLAR --ar128
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
    if not AR:                                            # ROWS 128 fj: no closed view -> soft (TW2-COLLAR)
        add("fj", "u_fj", 8, 1)                           # 345.6, 43.2
    for s in range(9):
        add("qc", f"u_qc{s}", 4 + 2 * s, 9)               # row y 388.8 (25.92 x 129.6), x 172.8 .. 864
    for k in range(9):
        add("qo32", f"u_qo{k}", 4 + 2 * k, 13)            # row y 561.6 (23.76 x 101.52)
    for k in range(9, 12):
        add("qo32", f"u_qo{k}", 22 + 2 * (k - 9), 13)     # x 950.4 / 1036.8 / 1123.2
    for k in range(12, 15):
        if AR:      # the 6-SRAM issuer column (x 1080..1251, y 43.2..510) takes the qo13/qo14 slots (a 1-lattice pitch
            # leaves a 19.4-um channel < 20): qo12 stays (950.4, 388.8), qo13 -> E end of the qo row (1209.6, 561.6),
            # qo14 -> above qo9 (950.4, 691.2; clear of the q3 argmax at x >= 1036.8)
            add("qo32", f"u_qo{k}", *{12: (22, 9), 13: (28, 13), 14: (22, 16)}[k])
        else:
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


def entry_domains(cks):
    """IO domain per port = the region that owns it in the lp.py SDC (ck_wr / ck_rg set_*_delay lines); the rest = core
    (ck_sw, the first region).  Literal base names (PL-KIT refuses wildcards)."""
    import re
    top = f"ot_hfd_coll_{VARIANT}_lp" + ("_ar" if AR else "")
    d = ROOT / "rtl/hbm_accel/generic/collective/p2p/landed"
    sv = (d / f"{top}.sv").read_text()
    sdc = (d / f"{top}.sdc").read_text()
    head = sv[sv.index(f"module {top}"):sv.index(");")]
    # QF-COLLQ 10-18: every port of the ANSI header, incl. continuation lines ("    pr_ccw_i," after "input wire [279:0]
    # pr_cw_i,"), which the first-name-only regex dropped from every domain (lpk1: 15 q3 ports had no IO budget)
    io, last = [], None
    for ln in head.splitlines()[1:]:
        m = re.match(r"\s*(input|output)\s+(?:wire|logic|reg)?\s*(?:\[[^\]]*\]\s*)?(.*)", ln)
        if m:
            last, rest = m.group(1), m.group(2)
        elif last and re.match(r"\s*\w", ln):
            rest = ln
        else:
            continue
        io += [(last, n) for n in re.findall(r"\b([A-Za-z_]\w*)\b", rest.split("//")[0])]
    own = {m.group(2): m.group(1) for m in re.finditer(r"-clock (ck_\w+) \[get_ports \{(\w+)", sdc)}
    own.setdefault("qid_rg", "ck_rg")      # identity strap copy beside u_rctl (static: no lp.py IO delay line)
    own.setdefault("qid_wr", "ck_wr")      # TW-HBM-COLLP 10-19: identity strap copy beside u_writer (static)
    name = {cks[0]: "core", "ck_wr": "wr", "ck_rg": "rg"}
    out = {name[c]: {"ratio": [1, 1], "ports": [c], "inputs": [], "outputs": []} for c in cks}
    for kind, p in io:
        if p in cks:
            continue
        out[name[own.get(p, cks[0])]]["inputs" if kind == "input" else "outputs"].append(p)
    return out


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
        # TW-HBM-COLLP 10-19: qid_wr = the writer region's own copy of the quadrant identity strap, beside ck_wr / u_writer
        "W": ["vm_rq", "vm_rr", "ck_wr", "qid_wr", "vm_kq"] + (TKX_W if VARIANT == "q3" else []),
        # QF-COLLQ 10-18: rc_v / rc_tag (read only by u_control, region sw, S row at x 172.8) moved N -> S: on N they reached
        # u_control 1,179 um combinationally (textbook wire_reach REFUSE > 500 um); rc_d stays on N (-> isa_lp_data on N).
        # qid_rg: the ring region's own copy of the quadrant identity strap, beside ck_rg / u_rctl (S qid reached u_rctl.qid
        # 1,146-1,200 um); the die ties both qid pins to the same constant
        "N": ["pr_cw_i", "pr_ccw_o", "isa_ring", "isa_lp_data", "rc_d"] + ra[:15] + ["ck_rg", "qid_rg"] + ra[15:]
             + ["rr_v", "rr_tag", "rr_d", "ag_v", "ag_src", "ag_tag", "ag_d", "pr_ccw_i", "pr_cw_o"]
             + (TKX_OUT if VARIANT == "q3" else []),
        "E": ["inj_rd", "inj_idx", "hgi_inj_addr", "inj_d", "del_valid", "del_flit", "hgi_del_obase"],
        "S": ["rc_v", "rc_tag", "cfg_v", "cfg_target", "cfg_addr", "cfg_data", "desc_v", "desc_base", "desc_limit", "desc_loops", "launch_v",
              "program_configured", "program_init_busy", "program_fault", "rst_n", "qid", "ck_sw", "hgi_busy", "hgi_done",
              "hgi_fault", "fault", "fault_cause", "done", "stat_cycles", "phy_up", "tx_pin_v", "tx_pin_flit", "rx_pin_v",
              "rx_pin_flit", "retry_requested"],
    }
    if AR:      # ROWS 128: bank b = u_sram (rows 0-63) + g128.u_sram_hi (64-127), stacked lo/hi per bank
        macros = [{"view": SRAM, "count": 1, "inst": f"u_issuer.u_issuer.g_mem[{i // 2}].u_bank." + ("g128.u_sram_hi" if i % 2 else "u_sram"),
                   "at": [1080.0, round(43.2 + i * 77.808, 3)], "at_exact": True} for i in range(6)]
    else:
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
        # PL-KIT landed-cluster form (main 112f518d5): one TritonCTS root per region, child clock pins are sinks judged at
        # the child flops, landing multicycles from the record; IO timed against the region that owns each port
        # (spine + sdc_extra form: lp1/lp2 stalled 4 h in CTS hold repair, I2R 3,080 @ -638 ps vs a 0.9-1.8 ns spine)
        "clock": "multiple_cts_roots",
        "clock_port": cks[0],
        "clock_ports": cks,
        "clock_data_paths": "related_same_frequency",
        "clock_relationship": {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
        "clock_entry_domains": entry_domains(cks),
        "landed_record": "results/arch/landed_parent_1018/collq/ot_hfd_coll_q2_lp_record.json",
        "reset_ports": ["rst_n"],
        "reset_landing": {"enable": False, "reason": "the lp.py RTL lands it: rst_n -> u_lpr_root (1 stage, ck_sw) -> u_lpr_<r> regional runs (depth 3) -> per-child u_lprc_* pads; the port net has ONE sink (TW2-COLLP 10-19, ROOT-RST rule satisfied in RTL)"},
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
            "tag": "lpk2",
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


def spec_ar128(s):
    """TW2-COLLAR: the q2 kit (spec()) re-targeted at ot_hfd_coll_q2_lp_ar (AR_ITER 1 / ROWS 128)"""
    t = json.dumps(s)
    for a, b in (("landed/ot_hfd_coll_q2_lp.sv", "landed/ot_hfd_coll_q2_lp_ar.sv"), ('"ot_hfd_coll_q2_lp"', '"ot_hfd_coll_q2_lp_ar"'),
                 ("ot_hfd_coll_q2_lp_record.json", "ot_hfd_coll_q2_lp_ar_record.json"), ("run_q2_lp_all", "run_q2_lp_ar_all"),
                 ("bench/q2lp", "bench/q2lpar"), ("hcoll_q2_lp_1018", "hcoll_q2_lp_ar128")):
        assert a in t, a
        t = t.replace(a, b)
    s = json.loads(t)
    s["route"]["io_hold_margin_ns"] = 0.025
    s["structural_change"] = ("TW2-COLLAR (10-19): " + s["structural_change"] + "; XDIE-HBM4 AR_ITER 1 / ROWS 128: issuer 6 "
                              "SRAMs (u_sram + g128.u_sram_hi per bank), fj ROWS 128 soft, u_ariter leaf (sw)")
    s["job"].update(owner="Claude:TW2-COLLAR", branch="claude/tw2-collar-1019", tag="ar128", submit=False,
                    purpose=s["job"]["purpose"] + " -- XDIE-HBM4 AR_ITER 1 / ROWS 128 re-gate (gate + PNG review only)")
    s["job"]["hold_merge"] += "; fj ROWS 128 soft (no closed r128 view yet)"
    s["job"]["benches"][0].update(name="q2lpar_lockstep", min_count_regex="Q2_LP_AR_ALL_EXIT (0)", peak_ram_gb=96)
    return s


def spec_q3():
    """q3 (SW) kit = the q2 kit with the q3 lp outputs, the n2s1 / TP192 views, capture leaf 9 + argmax, TKM pins"""
    t = json.dumps(spec_ar128(spec()) if AR else spec())
    for a, b in (("ot_hfd_coll_q2_lp", "ot_hfd_coll_q3_lp"), ("run_q2_lp", "run_q3_lp"), ("q2lp", "q3lp"),
                 ("Q2_LP_AR_ALL", "Q3_LP_AR_ALL"), ("hcoll_q2_lp_1018", "hcoll_q3_lp_1018"), ("hcoll_q2_lp_ar128", "hcoll_q3_lp_ar128"), ("ot_hfd_coll_q2_hard_v8g", "ot_hfd_coll_q3_hard_v8x"),
                 ("COLL q2 quadrant parent", "COLL q3 (SW, NLINK 2, TP 192) quadrant parent"),
                 ("COLL q2 quadrant engine parent (SE/NW/NE)", "COLL q3 quadrant engine parent (SW, TP 192)"),
                 ("ot_hgi_coll_ctl_v5_q2 leaf", "ot_hgi_coll_ctl_v5_n2s1 leaf")):
        t = t.replace(a, b)
    return json.loads(t)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    AR = "--ar128" in args
    for v in ([a for a in args if a != "--ar128"] or ["q2", "q3"]):
        VARIANT = v
        LP = json.loads((ROOT / f"results/arch/landed_parent_1018/collq/spec_{v}{'_ar' if AR else ''}.json").read_text())
        out = ROOT / f"tools/ref_tile/specs_hbm_d4g/hcoll_{v}_lp_{'ar128' if AR else '1018'}.json"
        sp = (spec_ar128(spec()) if AR else spec()) if v == "q2" else spec_q3()
        out.write_text(json.dumps(sp, indent=1) + "\n")
        print("wrote", out)
