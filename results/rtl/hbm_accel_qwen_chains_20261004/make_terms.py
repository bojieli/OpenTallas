#!/usr/bin/env python3
"""Collect the measured terms (runs/*/token_result.json or token.log) into terms.json for
tools/qwen_hbmacc_chain_compose.py.  Run from this directory."""
import json, re
from pathlib import Path
H = Path(__file__).resolve().parent
HA8 = H.parent / "hbm_accel_ha8_20261004"


def cyc(run, stage):
    t = (H / "runs" / run / "token.log").read_text()
    return int(re.search(rf"STAGE {stage} done cycles=(\d+)", t).group(1))


def ex(run):
    r = H / "runs" / run / "token_result.json"
    if r.exists():
        return json.loads(r.read_text())["status"] == "pass"
    chk = json.loads((H / "runs" / "tp4_ar_exactness.json").read_text())["checks"]
    return all(v["mismatches"] == 0 for k, v in chk.items() if k.startswith(run + "/"))


def m(run, stage, note=""):
    return {"cycles": cyc(run, stage), "source": f"runs/{run}", "exact": ex(run), "measured": True, "note": note}


ha8 = lambda d: int(re.search(r"STAGE head done cycles=(\d+)", (HA8 / d / "head/token.log").read_text()).group(1))  # noqa: E731
T = {
    "a_L0_sram": m("a_L0_itr", "L0", "TP2 L0 SRAM-resident (HA8 placement), P8191"),
    "a_L1_partial": {"cycles": 27112, "source": "results/rtl/qwen_hbmacc_p8191_20261004/measured_composition.json (a w224 L1)",
                     "exact": True, "measured": True, "note": "TP2 L1, 106 of 992 code words SRAM, w224, preroll 5000"},
    "a_L_hbm": m("a_L2_itr", "L2", "TP2 HBM layer w224 (= sibling 33,051)"),
    "a_head_p1": {"cycles": 4634, "source": "results/rtl/qwen_hbmacc_p8191_20261004 (a head at P8191, token 18 exact)", "exact": True, "measured": True},
    "a_L_spread": m("a_L2_spread", "L2", "TP2 HBM layer, 31 leading code words SRAM (spread)"),
    "b_L0_sram": m("b_L0_itr", "L0", "TP4 L0 SRAM-resident, P8191"),
    "b_L5_partial": {"cycles": 11611, "source": "results/rtl/qwen_hbmacc_p8191_20261004 (b w224 L5)", "exact": True, "measured": True},
    "b_L6_first_hbm": {"cycles": 13105, "source": "results/rtl/qwen_hbmacc_p8191_20261004 (b w224 L6; = runs/b_L6eq 13,105)", "exact": True, "measured": True},
    "b_L_hbm": m("b_L2h_itr", "L2", "TP4 HBM layer, preroll 1000"),
    "b_head_p1": {"cycles": 2999, "source": "results/rtl/qwen_hbmacc_p8191_20261004 (b head at P8191, token 18 exact)", "exact": True, "measured": True},
    "b_L_spread": m("b_L2_spread", "L2", "TP4 HBM layer, 75 leading code words SRAM (spread)"),
    "a_verify_layer": m("v2_hw_w1024_tail", "L0", "TP2 verify p=4 block 8187..8190, w1024, spread, synthesizable release, preroll = verify tail"),
    "a_verify_head_p4": m("v2_head", "head", "TP2 verify head p=4 (positions 0..3; lm_head is position-independent)"),
    "a_drafter_layer": {"cycles": None, "source": "UNVALIDATED: no TP2 drafter images; proxy = a_verify_layer x (b_drafter_layer / b_verify_layer)",
                        "exact": False, "measured": False},
    "a_ingest_markov": {"cycles": 7875, "source": "results/rtl/qwen_dspark_system_20261004 (priced ROM TP4 terms, not RTL)", "exact": False, "measured": False},
    "b_verify_layer": m("v4_hw_w320_tail", "L0", "TP4 verify p=4 block 8187..8190, w320, spread, synthesizable release, preroll = verify tail"),
    "b_verify_head_p4": {"cycles": 11993, "source": "results/rtl/qwen_dspark_system_20261004/ctx8k/c_H1.json (ROM VPRM, identical W12 TP4 datapath and head images; HA8 TP4 p1 head == ROM c_H0 2,999)",
                         "exact": True, "measured": True},
    "b_drafter_layer": m("d4_hw_tail", "L0", "TP4 DSpark drafter layer D0, S=3 at 8188, real-magnitude window, weights+KV streamed, synthesizable release"),
    "b_ingest_markov": {"cycles": 7875, "source": "results/rtl/qwen_dspark_system_20261004 (priced, not RTL)", "exact": False, "measured": False},
    "commit": {"cycles": 65, "source": "results/rtl/qwen_dspark_system_20261004 (accept unit within 64 edges + 1)", "exact": True, "measured": True},
}
T["a_drafter_layer"]["cycles"] = round(T["a_verify_layer"]["cycles"] * T["b_drafter_layer"]["cycles"] / T["b_verify_layer"]["cycles"])
(H / "terms.json").write_text(json.dumps(T, indent=1) + "\n")
print({k: v["cycles"] for k, v in T.items()})
