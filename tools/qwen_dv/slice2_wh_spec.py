#!/usr/bin/env python3
"""QK-SLICE 10-18 (coordinator 0gs(c): slice2 is HIERARCHICAL, the die grants M1-M7 inside the slice region):
write physical/ref_tile/qfd_dv_slice2_wh/spec.json, the hierarchical pathfinding kit of the qfd_dv_slice2_w master.

One cluster level inside the die grant (children M5-capped, parent straps M6, cluster PG M7):
  * 8 SU lanes at SU_LT = 1: per lane the hard qfd_dv_lane_h (STAND-IN until its gate closes) + the CLOSED
    ot_hdc_sfu_{exp,rcp,rsq}_t leaves, arranged as the qfd_dv_su_lane kit (tools/ref_tile/specs_qdv_slice) re-gridded to the 43.2 child lattice;
    the su_lane IREG / OREG pin flops are soft parent logic beside each lane group;
  * the heads at HD_W130 = 1: 32 ot_qfd_xs_leaf (STAND-IN = the closed w130 view re-layered to M5, M6 E/W pins -> M4;
    the M5 xs_leaf re-kit qfd_xs_leaf_w130m5 is the real view) at the qfd_dv_heads_w130 kit's relative positions;
    the xhead / tap glue is soft parent logic;
  * 22 VM SRAM macros (10 x 1024x256, 8 x 128x256, 4 x 256x256) in two rows between the two lane rows;
  * reducer / stream / scalar / redstn2 / chains: soft parent logic.
Pins / outline: the flat qfd_dv_slice2_w kit (dv2f14bn die abstract).  Diagnostic: never submitted (CRITICAL prefix).

    python3 tools/qwen_dv/slice2_wh_spec.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KD = "physical/ref_tile/qfd_dv_slice2_wh"
SI = f"{KD}/standin"
LANE = [("qfd_dv_lane_h", f"{SI}/qfd_dv_lane_h", "u_head", (0.0, 0.0)),
        ("ot_hdc_sfu_rcp_t", "physical/ref_tile/qfd_su_sfu_rcp/views/ot_hdc_sfu_rcp_t", "u_rcp", (216.0, 0.0)),
        ("ot_hdc_sfu_exp_t", "physical/ref_tile/qfd_su_sfu_exp/views/ot_hdc_sfu_exp_t", "u_exp", (0.0, 172.8)),
        ("ot_hdc_sfu_rsq_t", "physical/ref_tile/qfd_su_sfu_rsq/views/ot_hdc_sfu_rsq_t", "u_rsq", (172.8, 172.8))]
LANE_X0, LANE_DX = 432.0, 432.0            # 4 lane groups (324 x 324 on the 43.2 lattice) a row, 108 um channels
LANE_Y = (86.4, 648.0)                     # row 0 / row 1; the VM rows sit between them
HEADS_XY = (864.0, 1080.0)                 # qfd_dv_heads_w130 footprint 734.4 x 1296 (centred in x)
VM_A = ("physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2", 174.744, 10)
VM_S = ("physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2", 94.824, 8)
VM_B = ("physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2", 172.824, 4)


# MU-SLICE-GATE 10-19: the deployed 4-user LM-head argmax (MU-QWEN R4, qfd_dv_amax_mu; root merge restart + mixed-user
# fault in qfd_dv_scalar2, MU-ADOPT-SLICE2 a540f1f9f / MU-QW-AMIX 95074c8a3); the gated RTL is claude/mu-slice-gate-1019
MU_NU = 4
RG = "results/rtl/mu_qwen_1018/adopt_slice/runs_gate"


def _b(name, case, expect, rx):
    b = {"name": name, "cmd": f"bash rtl/test/qwen_dv/run_mu_slice_gate.sh {case} {{RUN}}/bench/{name}", "expect": expect, "threads": 16,
         "peak_ram_gb": 64, "needs": ["verilator"]}
    if expect == "pass":
        b["pass_regex"] = rx
    else:
        b["fail_regex"], b["fail_witness"] = rx, f"{RG}/{case}.out"
    return b


# the W/E face chain at the kit configuration (SU_LT 1, HD_W130 1, MU_NU 4) and the head slice's MU benches (f j m n o)
BENCHES = [_b("faces_m0", "faces0", "pass", "FACES MUT=0: PASS"),
           _b("faces_m11", "faces11", "fail", "FACES MUT=11: FAIL"),
           _b("b2_mu4", "b2", "pass", "# exit 0"),
           _b("b2k_m14", "b2k14", "fail", r"bench2 \(k\) MUT=14: FAIL"),
           _b("b2n_am7", "b2n7", "fail", r"bench2 \(n\) MUT=0: FAIL")]


def r(v):
    return round(v, 4)


def main():
    flat = json.loads((ROOT / "physical/ref_tile/qfd_dv_slice2_w/spec.json").read_text())
    heads = json.loads((ROOT / "physical/ref_tile/qfd_dv_heads_w130/spec.json").read_text())
    ch = []
    for row in range(2):
        for k in range(4):
            l = row * 4 + k
            ox, oy = LANE_X0 + k * LANE_DX, LANE_Y[row]
            for _m, view, inst, (dx, dy) in LANE:
                ch.append({"view": view, "count": 1, "inst": f"*g_lane?{l}?*{inst}", "at": [r(ox + dx), r(oy + dy)],
                           "orient": "R0", "at_exact": True})
    for c in heads["children"]:
        inst = c["inst"].replace("u_hd.", "", 1)
        for a, b in (("[", "?"), ("]", "?")):
            inst = inst.replace(a, b)
        ch.append({"view": f"{SI}/ot_qfd_xs_leaf", "count": 1, "inst": "*" + inst,
                   "at": [r(HEADS_XY[0] + c["at"][0]), r(HEADS_XY[1] + c["at"][1])], "orient": c.get("orient", "R0"),
                   "at_exact": True})
    mac = []
    x = 216.0
    for _ in range(VM_A[2]):
        mac.append({"view": VM_A[0], "count": 1, "at": [r(x), 453.6]})
        x += VM_A[1] + 21.6
    x = 302.4
    for view, w, n in ((VM_S[0], VM_S[1], 4), (VM_B[0], VM_B[1], 2), (VM_S[0], VM_S[1], 4), (VM_B[0], VM_B[1], 2)):
        for _ in range(n):
            mac.append({"view": view, "count": 1, "at": [r(x), 561.6]})
            x += w + 21.6
    s = {
        "name": "qfd_dv_slice2_wh",
        "top": "qfd_dv_slice2_w",
        "kind": "cluster",
        "diagnostic": True,
        "sources": flat["sources"] + ["rtl/qwen_dv/qfd_dv_su_lane.sv"] +
                   [x for x in ["rtl/qwen_dv/mu/qfd_dv_amax_mu.sv"] if x not in flat["sources"]],
        "params": {"SU_LT": 1, "HD_W130": 1, "MU_NU": MU_NU},
        "defines": ["OT_DV_SU_LANE_HARD", "OT_DV_HEADS_HARD"],
        "hard_define": "OT_DV_HEADS_HARD",   # the define the hard-child #() lint checks (OT_DV_SU_LANE_HARD: no #() on lane_h / SFU)
        "clock_port": flat["clock_port"],
        "reset_ports": flat["reset_ports"],
        "outline": flat["outline"],
        "child_lattice_um": 43.2,
        "pins": flat["pins"],
        "pin_ranges": flat["pin_ranges"],
        "children": ch,
        "macros": mac,
        "inter": [],
        "recipe": flat.get("recipe", 2),
        "route": dict(flat["route"], io_hold_margin_ns=0.03),
        "pin_regs": flat["pin_regs"],
        "io_flop_at_pins": flat["io_flop_at_pins"],
        "inhold": flat["inhold"], "outhold": flat["outhold"], "keep_pin_regs": flat["keep_pin_regs"],
        "pin_reg_split": flat["pin_reg_split"], "hold_pad": flat["hold_pad"],
        "structural_change": ("QK-SLICE 10-18 (coordinator 0gs(c)): HIERARCHICAL pathfinding kit of the qfd_dv_slice2_w "
                              "master inside the die's M1-M7 grant (cluster: children M5, straps M6, PG M7). Hard children: "
                              "8 x (qfd_dv_lane_h STAND-IN + closed ot_hdc_sfu_exp/rcp/rsq_t), 32 x ot_qfd_xs_leaf M5 "
                              "STAND-IN (closed w130 view, M6 E/W pins re-layered to M4); 22 VM SRAMs; glue soft. RTL "
                              "SU_LT 1 / HD_W130 1 (benched opt-in configuration, bench_h1), MU_NU 4 (MU-SLICE-GATE 10-19: 4-user "
                              "LM-head argmax qfd_dv_amax_mu + root merge restart / mixed-user fault). Diagnostic: stand-ins are "
                              "never bindable; CRITICAL prefix, no REVIEW/submit. Landed regions: the slice RTL has one "
                              "clock port today; the per-region ck_<r> ports + landed crossings need the slice core split "
                              "into a wires-only parent (tools/landed_parent/lp.py) -- owed, see PARTITION.md."),
        "job": {"owner": "Claude:MU-SLICE-GATE", "branch": "claude/mu-slice-gate-1019", "tag": "wh2mu", "submit": False,
                "purpose": "qfd_dv_slice2_w hierarchical pathfinding (die grant M1-M7), critical: gate only",
                "hold_merge": "QK-SLICE diagnostic: lane_h + xs_leaf stand-ins", "benches": BENCHES},
    }
    out = ROOT / KD / "spec.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(s, indent=1) + "\n")
    print(out, len(ch), "children", len(mac), "macros")


if __name__ == "__main__":
    main()
