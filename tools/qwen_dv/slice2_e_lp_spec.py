#!/usr/bin/env python3
"""OWN-QWEN/SLICE-E 10-18: write physical/ref_tile/qfd_dv_slice2_e/spec.json, the LANDED parent kit of the Qwen DV slice E
master (top qfd_dv_slice2_e_lpf_lp from tools/landed_parent/lp.py, spec tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json).

Geometry = the hierarchical slice kit qfd_dv_slice2_wh (QK-SLICE, coordinator 0gs(c): one cluster level inside the die's
M1-M7 grant -- children M5, straps M6, PG M7): the same 8 lane groups (qfd_dv_lane_h STAND-IN + closed SFU), 32 x leaves
(M5 STAND-IN), 22 VM SRAMs at the same positions (the content is not face-directional).  Pins = the dv2f14bn die abstract of
qfd_dv_slice2_e (results/arch/qwen_split_compute_1014/q_slice_1017/hardening/slicee/slice_pins_dv2f14bn.json; ss_eo / cc*_eo
are missing from that abstract and take the W master's y range on the E face), plus one clock port per region on the face
next to its region (die obligation: 10 regional clocks, related, same PLL phase).
CRITICAL prefix qfd_dv_slice2: gate only (no REVIEW.json, no submit) -> COORD-REVIEW-QUEUE.

    python3 tools/qwen_dv/slice2_e_lp_spec.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KD = "physical/ref_tile/qfd_dv_slice2_e"
REC = "results/arch/landed_parent_1018/qfd_dv_slice2_e_lpf/qfd_dv_slice2_e_lpf_lp_record.json"
PINS = "results/arch/qwen_split_compute_1014/q_slice_1017/hardening/slicee/slice_pins_dv2f14bn.json"
# region clock pins: face, centre coordinate (um along the face); all in pin-free gaps of the die abstract
CKP = {"core": ("S", 864.0), "hd": ("N", 800.0), "ef": ("E", 1250.0), "wf": ("W", 1250.0),
       "nw": ("N", 400.0), "nc": ("N", 1600.0), "ne": ("N", 2200.0),
       "sw": ("S", 400.0), "sc": ("S", 1600.0), "se": ("S", 2200.0)}


def snap(v, g=43.2):
    """the heads_w130 relative leaf rows sit 0.024 um off the 43.2 child lattice (wh kit warning): snap them on it"""
    k = round(v / g)
    return round(k * g, 4) if abs(v - k * g) < 0.1 else v


def main():
    wh = json.loads((ROOT / "physical/ref_tile/qfd_dv_slice2_wh/spec.json").read_text())
    lps = json.loads((ROOT / "tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json").read_text())
    rec = json.loads((ROOT / REC).read_text())
    ab = json.loads((ROOT / PINS).read_text())
    ab_e, ab_w = ab["qfd_dv_slice2_e"], ab["qfd_dv_slice2_w"]
    for p, q in (("ss_eo", "ss_wo"), ("ccv_eo", "ccv_wo"), ("ccm_eo", "ccm_wo"), ("ccw_eo", "ccw_wo"), ("cct_eo", "cct_wo")):
        if p not in ab_e:
            ab_e[p] = [wh["pin_ranges"][q][0], wh["pin_ranges"][q][1], "E", None, ["M4"]]
    pins = {f: [] for f in "NSEW"}
    rng = {}
    for p, v in sorted(ab_e.items(), key=lambda kv: kv[1][0]):
        if p in ("VDD", "VSS", "ck"):
            continue
        pins[v[2]].append(p)
        rng[p] = [round(v[0], 3), round(max(v[1], v[0] + 0.25), 3)]
    regions = list(rec["regions"])
    for r in regions:
        f, c = CKP[r]
        pins[f].append(f"ck_{r}")
        rng[f"ck_{r}"] = [round(c, 3), round(c + 0.25, 3)]
    preg = lps["port_regions"]
    dom = {}
    for r in regions:
        ins = sorted(p for p, rr in preg.items() if rr == r) + (["rst_n"] if r == regions[0] else [])
        outs = sorted(p for p, v in rec["compiler"]["output_port_offset_edges"].items()
                      if any(c for c in rec["regions"][r]["children"]) and p in OUTREG.get(r, []))
        dom[r] = {"ratio": [1, 1], "ports": [f"ck_{r}"], "inputs": ins, "outputs": outs}
    srcs = ["rtl/qwen_dv/lp/qfd_dv_slice2_e_lpf_lp.sv", "rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv",
            "rtl/common/landed_parent/ot_pl_land.sv"] + [s for s in wh["sources"] if s not in
                                                         ("rtl/qwen_dv/qfd_dv_slice2_faces.sv", "rtl/qwen_dv/qfd_dv_slice2.sv")]
    s = {
        "name": "qfd_dv_slice2_e",
        "top": "qfd_dv_slice2_e_lpf_lp",
        "kind": "cluster",
        "diagnostic": True,
        "sources": srcs,
        "params": {"SU_TLS": 1, "SU_LT": 1, "MU_NU": 4, "MUT": 0},
        "defines": wh["defines"],
        "hard_define": wh["hard_define"],
        "clock_port": "ck_core",
        "reset_ports": ["rst_n"],
        "outline": wh["outline"],
        "child_lattice_um": wh["child_lattice_um"],
        "pins": pins,
        "pin_ranges": rng,
        "children": [dict(c, at=[snap(v) for v in c["at"]]) for c in wh["children"]],
        "macros": wh["macros"],
        "inter": [],
        "recipe": wh.get("recipe", 2),
        "route": dict(wh["route"], io_hold_margin_ns=0.03, hold_margin_ns=0.03),
        "pin_regs": {"enable": False, "reason": ("landed parent: every input port is written into its landing ring on the face "
                                                 "region root at the pin (flop-first) and every output port is the landing read "
                                                 "register in its face region (flop-last); lp.py offsets are the compiler record")},
        "clock": "multiple_cts_roots",
        "clock_ports": [f"ck_{r}" for r in regions],
        "clock_data_paths": "related_same_frequency",
        "clock_relationship": {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
        "clock_entry_domains": dom,
        "landed_record": REC,
        "landed_note": ("OWN-QWEN/SLICE-E 10-18: die obligations: 10 regional clock ports ck_<r> (related, same PLL phase, "
                        "neighbour-relative delivery); every input on time; outputs +6 edges (cmd/hr/st/sc/ch/l9/cc chains), "
                        "+9 (cw corridor words), +12 (ss status, ag OR chain) vs the flat qfd_dv_slice2_e -> cycles_dv.py / "
                        "die GEN must re-derive the chain hop ages (cmd 2 -> 8, hr/ch 1 -> 7 edges a slice hop); reset release "
                        "+9.  MU-SLICE-GATE 10-19: MU_NU 4 (4-user LM-head argmax, root merge restart + mixed-user fault).  Residual: the 8 SU lane groups share ck_core (su8 read loop lane -> VM -> lane)."),
        "structural_change": ("OWN-QWEN/SLICE-E 10-18 (landed-regions-standard-1018): qfd_dv_slice2_e as a LANDED parent "
                              "(lp.py: 10 region roots core/hd/ef/wf/nw/nc/ne/sw/sc/se, 42 landings D4 E2, reset depth 9) "
                              "instead of one balanced tree over 2.46 x 2.59 mm. Geometry = the qfd_dv_slice2_wh hierarchical "
                              "kit (stand-in lane_h + M5 x-leaf, closed SFU, 22 SRAM). Diagnostic (stand-ins): never bindable; "
                              "CRITICAL prefix, no REVIEW/submit."),
        "job": {"owner": "Claude:MU-SLICE-GATE", "branch": "claude/mu-slice-gate-1019", "tag": "lp2mu", "submit": False,
                "purpose": "qfd_dv_slice2_e landed parent pathfinding (critical: gate only, COORD-REVIEW-QUEUE)",
                "hold_merge": "OWN-QWEN/SLICE-E diagnostic: lane_h + xs_leaf stand-ins",
                "extra_paths": ["results/arch/landed_parent_1018/qfd_dv_slice2_e_lpf"], "benches": BENCHES},
    }
    out = ROOT / KD / "spec.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(s, indent=1) + "\n")
    print(out, len(s["children"]), "children", len(s["macros"]), "macros", len(s["clock_ports"]), "region roots")


WIT = "results/arch/landed_parent_1018/qfd_dv_slice2_e_lpf/bench"


def _b(name, kind, m, expect, rx, wit=None):
    b = {"name": name, "cmd": f"bash rtl/test/qwen_dv/run_slice2_e_lpf.sh {{RUN}}/bench/{name} {kind} {m}", "expect": expect,
         "threads": 16, "peak_ram_gb": 64, "needs": ["verilator"]}
    if expect == "pass":
        b["pass_regex"] = rx
    else:
        b["fail_regex"], b["fail_witness"] = rx, wit
    return b


# eq: qfd_dv_slice2_e == the wires-only re-cut (3 stimulus modes); lp: the re-cut == the generated landed parent.
# Unobservable mutants (recorded, not benched): eq MUT 2 (cw_n1/cw_n2 swap: equal words under random stimulus) and lp MUT 4
# (u_c / u_hd reset run one stage long: both re-synchronise their reset and the random stimulus flushes the state).
RG = "results/rtl/mu_qwen_1018/adopt_slice/runs_gate"


def _g(name, case, expect, rx):
    b = {"name": name, "cmd": f"bash rtl/test/qwen_dv/run_mu_slice_gate.sh {case} {{RUN}}/bench/{name}", "expect": expect, "threads": 16,
         "peak_ram_gb": 64, "needs": ["verilator"]}
    if expect == "pass":
        b["pass_regex"] = rx
    else:
        b["fail_regex"], b["fail_witness"] = rx, f"{RG}/{case}.out"
    return b


# MU-SLICE-GATE 10-19: re-run at MU_NU 4 on claude/mu-slice-gate-1019 (witnesses in RG); + the head slice MU benches
BENCHES = [_g("eq_m0", "eq0", "pass", "EQ MUT=0: LPF_EQ PASS"),
           _g("eq_m1", "eq1", "fail", "EQ MUT=1: LPF_EQ FAIL"),
           _g("eq_m3", "eq3", "fail", "EQ MUT=3: LPF_EQ FAIL"),
           _g("lp_m0", "lp0", "pass", "LP MUT=0: LP_LOCKSTEP PASS"),
           _g("lp_m1", "lp1", "fail", "LP MUT=1: LP_LOCKSTEP FAIL"),
           _g("lp_m2", "lp2", "fail", "LP MUT=2: LP_LOCKSTEP FAIL"),
           _g("lp_m3", "lp3", "fail", "LP MUT=3: LP_LOCKSTEP FAIL"),
           _g("b2_mu4", "b2", "pass", "# exit 0"),
           _g("b2k_m14", "b2k14", "fail", r"bench2 \(k\) MUT=14: FAIL"),
           _g("b2n_am7", "b2n7", "fail", r"bench2 \(n\) MUT=0: FAIL")]

OUTREG = {
    "ef": ["st_eo", "sc_eo", "arv_eo", "art_eo", "arm_eo", "arl_eo", "ard_eo", "dd_eo", "ccv_eo", "ccm_eo", "ccw_eo", "cct_eo",
           "l9_eo", "ag_eo", "ss_eo"],
    "wf": ["cmd_wo", "hr_wo", "st_wo", "sc_wo", "rv_wo", "re_wo", "rr_wo", "rl_wo", "rd_wo", "dr_wo"],
    "nw": ["cw_n0"], "nc": ["cw_n1", "cw_n2"], "ne": ["cw_n3"], "sw": ["cw_s0"], "sc": ["cw_s1", "cw_s2"], "se": ["cw_s3"],
}

if __name__ == "__main__":
    main()
