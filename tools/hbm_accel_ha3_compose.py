#!/usr/bin/env python3
"""HA3 per-token composition against the full-shape DS-V4.1 HBM accelerator model, under the AUTHORITATIVE switch
latency record (tools/uarch_model.py hbm_switch_latency_authoritative; primary accelerator_measured_composition @
tomahawk_ultra_protocol).  Revision 2: r1 used the superseded hbm_switch_latency_range (main 75456eabf).

No double counting with the protocol transport: the Tomahawk Ultra protocol prices the collective TRANSPORT only
(2 crossings + golden-order cut-through reduce + cut-through multicast) and the authoritative firm ladder already drops
the model's R3a (endpoint cut-through) under it.  HA3 is credited NOTHING on the transport (measured issue->response
35.1 -> 35.2 cycles: the endpoint adds and removes no link latency); it is credited only the SM-side boundary in
VERIFY_PARTS["barrier"], which no transport scenario re-prices.  On the firm-ladder row the model's R3a (NVLS rows
only; TU rows already exclude it) and R3b (rejected) are undone, and R1b keeps its 31 cycles (47 residual credited).

Successor of measured.json composition.full_shape_analytic, which is WITHDRAWN: it subtracted the reduced system's
store / fence / single-SM reload / result store / reload around every collective (216-452 ns) from the W19 token,
but W19 (tools/w19_hbm_token_compose.py, 71b3ffc5) never charges those -- it lowers every collective straight from
the SMs' registers after ONE boundary (78 cycles) when a matvec run precedes it.  Credit is therefore taken only for
the term W19 charges and HA3 measurably removes: that boundary (the reduced-system sections show barrier wait -> 0
and the collective's own issue->response wait unchanged, 35.1 -> 35.2 cycles).  HA1 / R1b is REJECTED
(results/rtl/hbm_accel_ha1_20261004/verdict.json), so the whole 78-cycle boundary is HA3's; a firm-ladder row that
keeps R1b is given at the residual 47 cycles as a sensitivity.  The switch scenario moves the denominator only: the
removed work is SM side of the endpoint.

    python3 tools/hbm_accel_ha3_compose.py --out results/rtl/hbm_accel_ha3_20261004/composition_authoritative.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

PROGRAM = "results/rtl/w19_hbm_tp96_program_oreduce.json"          # the W19 AR record's program (sha pinned there)
PROGRAM_SHA = "46ee701ff29d956050db2da9b2bd9a8eff6cd87d278a35e4b181cfc2913b245b"
COLL_KINDS = ("all_gather", "all_reduce", "topk_merge", "kv_gather")
OFF_PATH_COLL = ("engram.", "candidate merge")                      # W19 compose: off the token's path
MEASURED = "results/rtl/hbm_accel_ha3_20261004/measured.json"
QWEN_HA8 = "results/rtl/hbm_accel_ha8_20261004/REPLAY.md"


def boundary_collectives():
    """W19 charges one boundary (flush of a matvec run) right before a collective iff a matvec run precedes it."""
    p = ROOT / PROGRAM
    if hashlib.sha256(p.read_bytes()).hexdigest() != PROGRAM_SHA:
        raise ValueError("W19 program changed")
    prog = json.loads(p.read_text())
    on, with_b = 0, 0
    for lay in prog["layers"]:
        pend = False
        for op in lay["ops"]:
            k = op["kind"]
            if k == "mv":
                pend = True
                continue
            if k == "local" and op.get("fn") == "swiglu":     # W19: charged once a layer, no flush
                continue
            if k in COLL_KINDS and not op["tag"].startswith(OFF_PATH_COLL):
                on += 1
                with_b += pend
            pend = False
    return on, with_b


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    import uarch_model as u
    from hbm_accelerator_model import _load_study
    m, _, _, _ = _load_study(ROOT)
    on, with_b = boundary_collectives()
    if on != m.W19_COLL_COUNT["total"]:
        raise ValueError(f"on-path collectives {on} != W19 {m.W19_COLL_COUNT['total']}")
    meas = json.loads((ROOT / MEASURED).read_text())["composition"]["measured_reduced_system"]
    b_full = m.W19_BOUNDARY_CYC / m.F_FAST * 1e6                     # us per boundary
    b_resid = (m.W19_BOUNDARY_CYC - m.W19_BARRIER_RELEASE_CYC) / m.F_FAST * 1e6
    n_draft = m.W19_COLL_COUNT["total"] * m.DRAFT_PARTS["collective"] / m.W19_AR["collective"]
    frac_b = with_b / on
    # the verify pass carries the same collectives (W19 verify_by_P: barrier term constant in P); the draft scales
    save = dict(ar=with_b * b_full, step=(with_b + n_draft * frac_b) * b_full)
    save_r1b = dict(ar=with_b * b_resid, step=(with_b + n_draft * frac_b) * b_resid)
    rng = u.hbm_switch_latency_authoritative()
    rungs = {r: s for r, s, _ in m.ds_rungs(1, include_conditional=False)}
    rungs6 = {r: s for r, s, _ in m.ds_rungs(6, include_conditional=False)}
    # firm switch row credits the model's R3b (rejected) and, on non-replaced (NVLS/w15) transports only, R3a (the
    # Tomahawk rows already exclude it: the protocol transport contains the endpoint cut-through); undo before HA3
    d_coll_frac = rungs["R3a"] / m.W19_AR["collective"]

    def undo(scen):
        r3a = 0.0 if scen in u.TU_SCEN else 1.0
        return dict(ar=r3a * rungs["R3a"] + rungs["R3b"],
                    step=r3a * (rungs6["R3a"] + m.DRAFT_PARTS["collective"] * d_coll_frac) + rungs6["R3b"])
    rows = []
    for r in rng["rows"]:
        if r["ctx"] != "1M":
            continue
        if r.get("gathers", "measured_ag") != "measured_ag" or r.get("msg", "small") != "small":
            continue
        if r["design"] not in ("accelerator_measured_composition", "ablation_w19", "accelerator_firm_switch"):
            continue
        ar, step = r["ar_us"], r["mtp_step_us"]
        s = save
        if r["design"] == "accelerator_firm_switch":
            ud = undo(r["scenario"])
            ar, step, s = ar + ud["ar"], step + ud["step"], save_r1b
        ar_n, step_n = ar - s["ar"], step - s["step"]
        rows.append(dict(design=r["design"], scenario=r["scenario"], fec=r.get("fec"), cable=r.get("cable"),
                         authoritative_default=r["authoritative_default"],
                         base_ar_us=round(ar, 2), ha3_ar_us=round(ar_n, 2),
                         base_ar_tok_s=round(1e6 / ar, 1), ha3_ar_tok_s=round(1e6 / ar_n, 1),
                         ar_gain_pct=round(100 * (ar / ar_n - 1), 3),
                         base_mtp_tok_s=round(u.TAU_OWNER6 * 1e6 / step, 1),
                         ha3_mtp_tok_s=round(u.TAU_OWNER6 * 1e6 / step_n, 1),
                         mtp_gain_pct=round(100 * (step / step_n - 1), 3)))
    prim = [x for x in rows if x["design"] == "accelerator_measured_composition"
            and (x["fec"] in (None, "board")) and x["cable"] in (None, "twinax_3m")]
    gate = {x["scenario"]: dict(ar=x["ar_gain_pct"], mtp=x["mtp_gain_pct"], authoritative_default=x["authoritative_default"],
                                pass_=min(x["ar_gain_pct"], x["mtp_gain_pct"]) >= 1.0)
            for x in prim}
    # MTP successor (hbm_mtp_both_drafts_measured: measured DS HBM draft replaces DRAFT_PARTS).  Conservative floor:
    # credit only the verify pass's boundaries (P=6 pass carries the same 168); the measured draft's 23 collectives get 0.
    mtp_succ = []
    for r in u.hbm_mtp_both_drafts_measured()["rows"]:
        if r["ctx"] != "1M" or r["design"] not in ("accelerator_measured_composition", "accelerator_firm_switch"):
            continue
        st = r["as_built"]["step_us"]
        sv = save["ar"] if r["design"] == "accelerator_measured_composition" else save_r1b["ar"]
        if r["design"] == "accelerator_firm_switch":
            st += rungs6["R3b"]                                   # firm ladder credits rejected R3b; undo (R3a: TU excl.)
        mtp_succ.append(dict(design=r["design"], scenario=r["scenario"], draft="as_built (measured)",
                             base_step_us=round(st, 2), ha3_step_us=round(st - sv, 2), credited_us=round(sv, 3),
                             base_mtp_tok_s=round(u.TAU_OWNER6 * 1e6 / st, 1),
                             ha3_mtp_tok_s=round(u.TAU_OWNER6 * 1e6 / (st - sv), 1),
                             mtp_gain_pct=round(100 * (st / (st - sv) - 1), 3)))
    rec = dict(
        schema="opentallas.hbm_accel.ha3_composition_switch_authoritative.v2",
        supersedes="composition_switch_range.json (r1, superseded hbm_switch_latency_range)",
        double_count_rule="transport credit 0 (protocol model contains the cut-through); only VERIFY_PARTS barrier "
                          "boundary credited; firm row undoes R3b and, on NVLS rows only, R3a",
        evidence="measured per-collective term (reduced-system RTL) x W19 program counts; full-shape token is MODEL",
        withdraws="measured.json composition.full_shape_analytic (credited SM-side work the W19 token never charges)",
        credited_term=dict(
            what="the one boundary W19 charges before a collective whose producer is a matvec run; COLLX contributes "
                 "from registers so no boundary is needed (measured: barrier wait 172.7/174.5 -> 0 cycles per "
                 "all-reduce section, issue->response 35.1 -> 35.2 cycles)",
            boundary_cycles=m.W19_BOUNDARY_CYC, residual_after_r1b_cycles=m.W19_BOUNDARY_CYC - m.W19_BARRIER_RELEASE_CYC,
            r1b_status="REJECTED (results/rtl/hbm_accel_ha1_20261004/verdict.json): full boundary credited to HA3",
            collectives_on_path=on, collectives_after_matvec_boundary=with_b, draft_collectives_assumed=round(n_draft, 2),
            saved_us=dict(ar=round(save["ar"], 3), mtp_step=round(save["step"], 3)),
            saved_us_if_r1b=dict(ar=round(save_r1b["ar"], 3), mtp_step=round(save_r1b["step"], 3)),
            measured_reduced_system_ns=meas["measured_ns_per_collective"],
            not_credited="store/fence/single-SM reload/result store/reload (W19 already assumes them absent: HA3 is "
                         "the hardware that makes that lowering real, so without it the W19 token is OPTIMISTIC by up "
                         "to the measured 216-452 ns per collective)",
            program=PROGRAM, program_sha256=PROGRAM_SHA),
        qwen=dict(ar_gain_pct_upper_bound=0.63, verdict="REJECT for Qwen AR",
                  basis=f"{QWEN_HA8}: the measured Qwen HBM-accelerator token is HBM-bound with collectives hidden; "
                        "HA1/HA2/HA3/HA6 together expose <= 0.63% of the token"),
        switch_src=u.SWITCH_AUTH_DIR, tau=u.TAU_OWNER6,
        primary="design accelerator_measured_composition @ tomahawk_ultra_protocol (twinax 3 m), 1M (authoritative default)",
        gain_gate_primary=gate, mtp_successor_measured_draft=mtp_succ, rows=rows)
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(credited=rec["credited_term"]["saved_us"], gate=gate, mtp_successor=mtp_succ), indent=1))


if __name__ == "__main__":
    main()
