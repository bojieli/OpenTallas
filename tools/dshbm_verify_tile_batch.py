#!/usr/bin/env python3
"""DS V4.1 HBM accelerator, MTP verify (P = 6) at 1M: the attention tile jobs of the 6 verify positions run on the
position-interleaved verify mode (ILV = 1) of the W11 attention engine -- the ROM's exact mechanism -- instead of 6
serial single-position jobs.

Baseline (results/rtl/dshbm_baseline_measured_20261004, tools/dshbm_baseline_measure.py): verify attention of a
T = 640 layer = the measured SU softmax chain at P = 6 (op-major, 392 cycles at 0.9 GHz) + 6 x the measured
single-position tile job (609 cycles at 1.2 GHz, results/rtl/v41_full_attention_numeric, PWORDS = 1, ILV = 0).

Lever: one ILV = 1 engine pass over the 6 positions (front job q.k overlapped with the back job's p.v, two ping-pong
staging buffers NSTAGE = 2, two p words a handshake PWORDS = 2, REPL = 2), MEASURED in RTL at full geometry
(H16 D512 TD32 NL4 TROWS640), each position on its OWN 640-row list in model order (its 128-row sliding window
oldest first, then its own 512 selected compressed rows): no row is shared, so the figure is the zero-overlap
(conservative) case and does not depend on how the 6 selections overlap.  Bit-exact per position (61,440 scores,
49,152 p.v outputs, set checker clean): results/rtl/w11_controller_recovery_20261001/ilv1.remote.json, on engine
sources byte-identical to main (checked here).  The SU softmax enters the engine run through its measured first-
probability latency L0 (+su_l0); three runs: L0 = 0, 188 (0.9-GHz cycles), 218 (engine cycles).

Composition (minimum-component rule; the attention job is data-independent in time at fixed T = 640, which every
T = 640 layer has at position 1,048,575):
  headline  (conservative) tile term = the L0 = 218 run (the SU's softmax latency in the loop for every position)
            AND the full SU P = 6 attend chain still charged serially, as in the baseline (double-counts the
            softmax start, never credits overlap);
  consistent tile term = the L0 = 0 run (p available as the baseline's 609-cycle job assumes) + the SU chain.
T = 128 (window-only) layers keep 6 x 225 (ILV not measured at T = 128).

    python3 tools/dshbm_verify_tile_batch.py --record results/rtl/dshbm_verify_tile_batch_20261004/record.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_baseline_measure as B  # noqa: E402

BASE = ROOT / "results/rtl/dshbm_baseline_measured_20261004"
ILV_REC = ROOT / "results/rtl/w11_controller_recovery_20261001/ilv1.remote.json"
ILV_BUILD = ROOT / "results/rtl/w11_controller_recovery_20261001/full_a.build.json"
SU1 = BASE / "su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_v2.json"
SU6 = BASE / "su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_p6om.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ilv_runs():
    rec = json.loads(ILV_REC.read_text())
    out = {}
    for r in rec["runs"]:
        l0 = int(r["plusargs"][0].split("=")[1])
        assert r["exact"] and r["score_errors"] == 0 and r["pv_errors"] == 0 and r["faults"] == 0 and \
            r["setcheck"]["errors"] == 0 and r["jobs"] == 6 and all(p["T"] == 640 for p in r["per_position"])
        out[l0] = dict(total_cycles=r["total_cycles"], tile_utilisation=r["tile_utilisation"],
                       scores_checked=r["scores_checked"], pv_checked=r["pv_checked"],
                       position_cycles=[p["position_cycles"] for p in r["per_position"]])
    return out


def source_currency():
    b = json.loads(ILV_BUILD.read_text())
    rows = {p: dict(build=h, main=sha(ROOT / p)) for p, h in b["source_sha256"].items()}
    for v in rows.values():
        v["identical"] = v["build"] == v["main"]
    return dict(params=b["params"], pwords=b["pwords"], files=rows, all_identical=all(v["identical"] for v in rows.values()))


def compose(tile640_p6):
    """The baseline's mtp_and_accelerator walk with the P = 6 T = 640 tile term replaced."""
    import w19_hbm_token_compose as WC
    prog = json.loads((BASE / "program.json").read_text())
    sm_new = json.loads((BASE / "sm_real_ops.json").read_text())
    sm_old = json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text())
    sm = WC.SMTable([sm_old, sm_new], "ar")
    w15 = json.loads((ROOT / "results/rtl/w15_hbm_nvls.json").read_text())
    coll = WC.w15_prod(w15, "hbm_p48_ss")
    coll["select_cycles"] = 419
    su1, su6 = json.loads(SU1.read_text()), json.loads(SU6.read_text())
    base = dict(prog=prog, sm=sm, coll=coll, su=B.su_table(su1), WC=WC)
    orig = B.price_local
    if tile640_p6 is not None:
        def price_local(op, su, f_ser, flags, WC_, m, P=1):
            us, hw = orig(op, su, f_ser, flags, WC_, m, P)
            if op["fn"] == "attend" and P == 6 and op.get("yarn") and hw.startswith("SU measured + tile"):
                us += (tile640_p6 - B.TILE_JOBS(P) * B.ATT_TILE[640]) / B.F_FAST * 1e6
                hw = "SU measured + ILV tile (measured RTL, 6 positions, T=640)"
            return us, hw
        B.price_local = price_local
    try:
        return B.mtp_and_accelerator(prog, base, su1, su6)
    finally:
        B.price_local = orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    a = ap.parse_args()
    runs = ilv_runs()
    cur = source_currency()
    base = compose(None)["measured"]
    ref = json.loads((BASE / "measured.json").read_text())["mtp_and_accelerator"]["measured"]
    assert abs(base["mtp_tok_s"] - ref["mtp_tok_s"]) < 0.05, (base["mtp_tok_s"], ref["mtp_tok_s"])
    serial = 6 * B.ATT_TILE[640]
    rows = {}
    for name, l0 in (("headline_conservative_L0_218", 218), ("consistent_L0_0", 0), ("L0_188", 188)):
        t = runs[l0]["total_cycles"]
        m = compose(t)["measured"]
        rows[name] = dict(tile_cycles_6pos=t, saved_cycles_per_T640_layer=serial - t,
                          verify_p6_us=m["mtp"]["verify_p6_us"], step_us=m["mtp"]["step_us"],
                          mtp_tok_s=m["mtp_tok_s"], ar_tok_s=m["ar_tok_s"],
                          verify_local_us=m["mtp"]["verify_parts_us"]["local"],
                          per_user_gain_pct=round(100 * (m["mtp_tok_s"] / base["mtp_tok_s"] - 1), 2))
    h = rows["headline_conservative_L0_218"]
    verdict = ("ADOPT-ELIGIBLE (G-exact, G-latency, G-gain pass; G-timing/G-area NOT closed -- shared with the ROM "
               "engine)" if h["per_user_gain_pct"] >= 1.0 else "REJECT (<1% per-user)")
    rec = dict(
        schema="opentallas.rtl.dshbm_verify_tile_batch.v1", generated_utc=B.now(), source_commit=B.git_head(),
        lever="DS V4.1 HBM accelerator, MTP verify P=6 at 1M: the 6 positions' attention tile jobs on the W11 "
              "attention engine's position-interleaved verify mode (ILV=1, NSTAGE=2, PWORDS=2, REPL=2), the ROM's "
              "exact mechanism, instead of 6 serial single-position jobs",
        exactness="bit-exact per position against the golden (Model.attend, R-ARITH chunk8 order) on each position's "
                  "own 640-row list in model order; p.v reduces each position over its own rows only (no masked "
                  "union rows, which would change the chunk8 tree and is NOT exact)",
        measured_rtl=dict(source=str(ILV_REC.relative_to(ROOT)), runs_by_su_l0=runs,
                          geometry="H16 D512 TD32 NL4 TROWS640, NJOBMAX 6, 6 jobs x T 640", source_currency=cur,
                          overlap="none used: each position streams its own 640 rows (zero-overlap, conservative)"),
        baseline=dict(tile_cycles_6pos_serial=serial, single_job_cycles=B.ATT_TILE[640],
                      su_attend_T640_p6_cycles=B.su_table(json.loads(SU6.read_text()))["attend.T640"],
                      mtp_tok_s=base["mtp_tok_s"], verify_p6_us=base["mtp"]["verify_p6_us"],
                      step_us=base["mtp"]["step_us"], ar_tok_s=base["ar_tok_s"]),
        composed=rows, verdict=verdict,
        gates=dict(G_exact="PASS (6/6 positions, 61,440 scores + 49,152 p.v, set checker 0 errors, 3 L0 values)",
                   G_latency="PASS on the serial verify path (tile term replaced, SU chain still charged in full)",
                   G_gain=f"{h['per_user_gain_pct']}% per-user MTP (conservative); "
                          f"{rows['consistent_L0_0']['per_user_gain_pct']}% consistent",
                   G_area="NOT closed: +1 stationary bank, second 640-row staging buffer (+68 ASAP7 256x256 macros, "
                          "339,200 B), p skid (results/rtl/w11_attn_verify6_model.json storage)",
                   G_timing="NOT closed: no SS/FF closure of the ILV/REPL=2 controller exists; the one WC 0.833 ns "
                            "attempt (results/physical_abi3/asap7/chip/w11_attn_eng_ctl/wc833_cts) ended at CTS "
                            "WNS -1,204.62 ps and the r2c recovery aborted on its flop guard. The same engine is the "
                            "ROM's, so the ROM-vs-HBM comparison carries it on both sides or on neither."),
        unvalidated=["T = 128 window-only layers keep 6 x 225 cycles (ILV not run at T = 128)",
                     "the engine bench's SU model supplies probabilities at PWORDS = 2 words a cycle after L0; the "
                     "HBM die's SU at N 1,024 / M 256 writes >= 192 values per engine cycle against the 8 needed "
                     "for one head (rank 0 holds one head), so supply is not binding",
                     "AR (P = 1) unchanged here: the PWORDS = 2 single job (449 vs 609 cycles, "
                     "results/rtl/w11_attn_ploader.json) was measured on the REPL = 1 engine, not re-run"],
        inputs={str(p.relative_to(ROOT)): sha(p) for p in (ILV_REC, ILV_BUILD, SU1, SU6, BASE / "program.json",
                                                          BASE / "sm_real_ops.json", BASE / "measured.json")},
        tool_sha256=sha(Path(__file__)))
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(baseline=rec["baseline"], composed=rows, verdict=verdict, currency=cur["all_identical"]),
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
