#!/usr/bin/env python3
"""HA2 composition: put the RTL-measured direct-link all-reduce (tb_ha2_ar) in place of the modelled one in the HBM
accelerator ladder (results/uarch/hbm_accelerator_study_20261003/ladder_model.py, study a3ed9c36d), and price the
per-user rate gain.

    python3 tools/ha2_ar_compose.py --measured RECORD.json [--out OUT.json]

RECORD.json (written by the campaign) holds, per shape, the worst-seed issue -> last-commit latency in ns.

What is replaced, and only that:
  * the DS all-reduce share of rung R2 (40 o-group all-reduces a token: model AR fixed 823.6 -> 608.8 ns) AND the
    all-reduce share of rung R3a (cut-through, 40 x 67.4 ns): the measured endpoint is cut-through, so R3a's AR share
    must not be counted twice.  Baseline per op is what the W19 ablation token actually charges for this op
    (W15b NVLS P=48 SS fit at the op's payload: 988.74 + 6.0696 x ceil(32,768 / 749.7) cycles at 1.2005 GHz).
  * Nothing else: the 225 gather-like collectives keep the model's R2/R3a terms (listed as EXCLUDED, unmeasured).
Qwen3-8B: the model hides the TP-2 exchange under the weight stream (154 exposed cycles a token, Q3 REJECTED at 0);
the measured TP-2 all-reduce is reported against the W15 measured UCIe exchange it would replace, and the exposed
share is bounded.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LADDER = ROOT / "results/uarch/hbm_accelerator_study_20261003/ladder_model.py"


def load_ladder():
    spec = importlib.util.spec_from_file_location("ladder_model", LADDER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def compose(meas: dict) -> dict:
    M = load_ladder()
    fit = M.W19_COLL_FIT
    hz = fit["hz"]
    n_ar = M.W19_COLL_COUNT["all_reduce"]
    ar_bytes = 8192 * 4 * 8 // 8                       # w19_hbm_tp96_isa.py all_reduce op bytes
    slot = 749.7                                       # W19 record collective_model.slot (0.9 TB/s x period)
    words = math.ceil(1 * ar_bytes / slot)
    ar_base_ns = (fit["ar_fixed_cyc"] + 6.0696 * words) / hz * 1e9
    ar_model_old_fixed = fit["ar_fixed_cyc"] / hz * 1e9
    ar_model_new_fixed = 2 * M.INPKG_STEP_NS + 2 * M.C1_REDUCE_NS
    ar_model_new_ns = ar_base_ns - (ar_model_old_fixed - ar_model_new_fixed) - M.CUT_THROUGH_NS_PER_COLL
    ar_meas = meas["ds"]["lat_ns_worst"]
    model_save_us = n_ar * (ar_base_ns - ar_model_new_ns) * 1e-3          # R2 + R3a AR share, model
    meas_save_us = n_ar * (ar_base_ns - ar_meas) * 1e-3                   # same, measured

    out = dict(ar_op=dict(baseline_w19_ns=round(ar_base_ns, 1), baseline_words=words,
                          baseline_source="W19 AR token collective_model: W15b hbm_p48_ss all_reduce fit "
                                          "(988.74 fixed + 6.0696/word) at 32,768 B, slot 749.7 B",
                          model_accel_ns=round(ar_model_new_ns, 1),
                          model_accel_basis="R2 fixed 823.6->608.8 ns (2 x 83.4 in-package + 2 x 221.0 C1 reduce) "
                                            "and R3a 67.4 ns cut-through, slope kept",
                          measured_ns=round(ar_meas, 1),
                          measured_minus_model_ns=round(ar_meas - ar_model_new_ns, 1),
                          ops_per_token=n_ar),
               saved_us=dict(model=round(model_save_us, 2), measured=round(meas_save_us, 2)))

    # rates: honest ablation (R0c) and the firm composed accelerator, AR at 1M, with the AR share swapped
    res = {}
    for ctx, k in (("1M", 1.0), ("200K", M.CTX_200K_RATIO)):
        t = M.T(M.VERIFY_PARTS[1])
        steps = dict(M.ds_pass_us(1, include_conditional=False))
        t_r0c = steps["R0c"]
        t_firm = steps["R5b"]                       # last firm rung (R6a is 0 at P = 1)
        t_firm_meas = t_firm + model_save_us - meas_save_us
        res[ctx] = dict(
            ablation_honest_r0c_us=round(t_r0c * k, 2), ablation_honest_r0c_tok_s=round(1e6 / (t_r0c * k), 1),
            ha2_ar_only_on_r0c_tok_s=round(1e6 / ((t_r0c - meas_save_us) * k), 1),
            ha2_ar_gain_pct_on_r0c=round(100 * (t_r0c / (t_r0c - meas_save_us) - 1), 2),
            model_firm_ar_us=round(t_firm * k, 2), model_firm_ar_tok_s=round(1e6 / (t_firm * k), 1),
            firm_with_measured_ar_us=round(t_firm_meas * k, 2),
            firm_with_measured_ar_tok_s=round(1e6 / (t_firm_meas * k), 1),
            ha2_ar_gain_pct_in_firm_composition=round(100 * ((t_firm_meas + meas_save_us) / t_firm_meas - 1), 2),
            w19_ablation_us=round(t * k, 2))
    out["ds_rates"] = res

    q = meas.get("qwen")
    if q:
        # W15 measured TP-2 UCIe exchange (results/rtl/w15_collectives.json, q256d64: 71 cycles a reduce at the
        # Qwen ROM clock); the HBM ablation's token exposes 154 cycles over its whole weight stream.
        out["qwen"] = dict(measured_tp2_ar_ns=round(q["lat_ns_worst"], 1),
                           ars_per_token=72,
                           model_exposed_us_per_token=M.Q_ABL_BOUNDARY_US,
                           model_ar_tok_s=None,
                           note="Qwen AR is hidden under the weight stream in the model (Q3 REJECTED at 0 gain); the "
                                "direct link cannot change a hidden term. Upper bound if every AR were exposed: "
                                f"{72 * q['lat_ns_worst'] * 1e-3:.1f} us a token, which is the ablation's own "
                                "in-package link term as well (both designs use the same direct UCIe pair)")
    # gather sensitivity: the same endpoint as an all-gather (NC = 1) at two payloads -> fixed + slope, against the
    # model's R2 + R3a gather fixed term (not the HA2 all-reduce claim; the 225 gather-like ops stay modelled)
    g1, g4 = meas.get("dsgather"), meas.get("dsgather512")
    if g1 and g4:
        b1, b4 = 128, 512                                      # bytes a rank
        slope = (g4["lat_ns_worst"] - g1["lat_ns_worst"]) / (b4 - b1)
        fixed = g1["lat_ns_worst"] - slope * b1
        ag_old = M.W19_COLL_FIT["ag_fixed_cyc"] / hz * 1e9
        ag_model = M.INPKG_STEP_NS + 2 * M.C1_GATHER_NS - M.CUT_THROUGH_NS_PER_COLL
        out["gather_sensitivity"] = dict(
            measured_ns={"128B_per_rank": round(g1["lat_ns_worst"], 1), "512B_per_rank": round(g4["lat_ns_worst"], 1)},
            measured_fixed_ns=round(fixed, 1), measured_slope_ns_per_B_rank=round(slope, 4),
            w15_nvls_ag_fixed_ns=round(ag_old, 1), model_accel_ag_fixed_ns=round(ag_model, 1),
            codex_snapshot_gather_last_ns=2158.392,
            note="all 96 dies, 64 / 256 BF16 a rank, exact; fixed by two-point extrapolation to 0 B")
    out["area_power"] = area_power()
    out["ladder_sha256"] = hashlib.sha256(LADDER.read_bytes()).hexdigest()
    return out


def area_power(ports=20, lanes_per_port=2, pwt=537, rxd=32, qd=32, wstg=14, hubw=35, inj=2, dele=4, fw=512,
               nc=8, of=8, lanes=16, levels=3):
    """Per-die price of the HA2 endpoint as built (tb_ha2_ar DS parameters) and of its SerDes, against the die
    ledger (results/floorplan/hbm_gpu/v41_hbm_die.json fabric_serdes reservation 18 mm2, ASSUMED; tools/uarch_model
    0.4 mm2 a 112G lane; technology.json link_j_per_bit.board_serdes_112g 6.5 pJ/b, 0.73 W always-on a lane)."""
    nl = 15
    bits = dict(rx_buffers=ports * rxd * pwt,
                tx_queues=(2 * ports + nl) * qd * pwt,
                delivery_queues=2 * qd * pwt,
                cdc_afifos=2 * ports * rxd * pwt,
                port_wire_stages=2 * ports * wstg * pwt,
                hub_wire_stages=inj * (16 + fw) * hubw + dele * pwt * hubw,
                operand_slots=nc * of * fw)
    total = sum(bits.values())
    dff_um2 = 0.2274433344e6 / 779984          # Codex price_r1 dff_cell_mm2 / its register bits (ASAP7 DFF)
    adders = (nc - 1) * lanes
    add_um2 = 517.4                             # nm_fadd7 cell area (w11_fp_latency_sweep, LAT 7 closed SS 1.2 GHz)
    logic_mm2 = (total * dff_um2 + adders * add_um2) / 1e6
    lanes_die = ports * lanes_per_port
    serdes = dict(lanes=lanes_die, mm2_at_0p4=round(0.4 * lanes_die, 2), mm2_codex_18_over_42=round(18 / 42 * lanes_die, 2),
                  ledger_reservation_mm2=18.0, fits=0.4 * lanes_die <= 18.0 and 18 / 42 * lanes_die <= 18.0,
                  always_on_w=round(lanes_die * 112e9 * 6.5e-12, 2),
                  always_on_w_band=[round(lanes_die * 112e9 * 5.6e-12, 2), round(lanes_die * 112e9 * 7.5e-12, 2)],
                  codex_w=31.43, budget_w=33.0, grade="ESTIMATE (no PHY view; transferred per-lane constants)")
    return dict(endpoint_register_bits=bits, endpoint_register_bits_total=total,
                endpoint_cell_mm2=round(logic_mm2, 3), endpoint_floorplan_mm2_at_70pct=round(logic_mm2 / 0.7, 3),
                fp32_adders=adders, serdes=serdes,
                die_core_mm2=660.08, die_used_before_mm2="sm 74.2 + l2 4.96 + hub 112.7 + io 28 (v41_hbm_die.json)",
                note="queues as flops are an upper bound (SRAM macros would hold the 32-deep FIFOs); the endpoint "
                     "replaces the NVLS port logic, whose area is not credited")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--measured", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    r = compose(json.loads(a.measured.read_text()))
    s = json.dumps(r, indent=1)
    if a.out:
        a.out.write_text(s + "\n")
    print(s)
