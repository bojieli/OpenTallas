#!/usr/bin/env python3
"""C7: compare the real-core collective stage against the stub-producer stage bench.

The real-core stage (results/rtl/v41x_real_core_collective_stage.json, main 95b9b782) runs one adopted V4.1x
vector core as rank 0's producer and consumer around four one-shot all-reduce engines, at 8 words of 16 FP32
lanes, receive FIFO depth 2 and producer queue depth 2, at cross-package link delays of 142 and 228 cycles.
Its logs print the cycle every rank receives each reduced word and the cycle the core finishes consuming each
word; they print no producer-output cycle, so the tail measured here is last reduced word -> last consumed word
plus the collective's wave period and span.

The stub campaigns (results/rtl/v41_stage_collective_campaign.json, v41_collective_levers_campaign.json) measure
the all-reduce at 40 words of 128 lanes, depth >= 8 and LAT 142 only, so no committed stub case matches the
real-core size.  ``--run-stub`` therefore runs the unchanged stub bench (rtl/test/tb_v41_stage_collective.sv, the
same ot_rom_oneshot_die engine and ot_v41sb_link model) at the real-core configuration: 8 words, 16 lanes,
DEPTH=2, QTX=2, LAT_X in {142, 228}, ranks starting 3 cycles apart from cycle 20 as the real-core bench's
synthetic ranks do.  Without ``--run-stub`` the matched stub results are reused from the existing output.

This is evidence for a later re-pricing decision; it changes no model input and no headline figure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/v41_c7_realcore_vs_stub.json"
REAL = ROOT / "results/rtl/v41x_real_core_collective_stage.json"
STAGE = ROOT / "results/rtl/v41_stage_collective_campaign.json"
LEVERS = ROOT / "results/rtl/v41_collective_levers_campaign.json"
LANES_JSON = ROOT / "results/arch/v41_lanes.json"
CLOCK = 1.087e9

RED = re.compile(r"REDUCED rank=(\d+) word=(\d+) cyc=(\d+)")
CON = re.compile(r"CONSUMED word=(\d+) cyc=(\d+)")
SUM = re.compile(r"REAL_STAGE_SUMMARY cyc=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def real_core() -> dict:
    rec = json.loads(REAL.read_text())
    out = {}
    for c in rec["configurations"]:
        log = ROOT / c["full_log"]
        assert sha(log) == c["full_log_sha256"], log
        txt = log.read_text()
        red = [tuple(map(int, m.groups())) for m in RED.finditer(txt)]
        con = {int(w): int(t) for w, t in CON.findall(txt)}
        words = rec["word_count"]
        per_word = {k: max(t for r, w, t in red if w == k) for k in range(words)}   # all ranks hold word k
        rank0 = {w: t for r, w, t in red if r == 0}
        waves = [per_word[k + rec["input_queue_depth"]] - per_word[k] for k in range(0, words - rec["input_queue_depth"],
                                                                                     rec["input_queue_depth"])]
        lat = c["cross_package_link_delay_cycles"]
        out[str(lat)] = dict(
            lat_x=lat, words=words, lanes=rec["lanes_per_word"], rx_depth=rec["receive_fifo_depth"],
            tx_queue=rec["input_queue_depth"], status=rec["status"], mismatches=c["checker"]["mismatches"],
            total_cycles=int(SUM.search(txt).group(1)),
            first_reduced_all_ranks=per_word[0], last_reduced_all_ranks=per_word[words - 1],
            last_reduced_rank0=rank0[words - 1], last_consumed=con[words - 1],
            reduced_cycles_by_rank={str(q): [t for r, w, t in sorted(red, key=lambda x: x[1]) if r == q] for q in range(4)},
            collective_span_cycles=per_word[words - 1] - per_word[0],
            wave_period_cycles=sorted(set(waves)),
            consumer_back_to_back_cycles=sorted({con[k + 1] - con[k] for k in range(0, words, 2)}),
            consumer_tail_after_last_reduced_all=con[words - 1] - per_word[words - 1],
            consumer_tail_after_last_reduced_rank0=con[words - 1] - rank0[words - 1],
            producer_stall_cycles={str(r["rank"]): r["stall"] for r in c["checker"]["ranks"]},
            fifo_qmax={str(r["rank"]): r["qmax"] for r in c["checker"]["ranks"]},
            log=c["full_log"])
    return out


def run_stub(scratch: Path) -> dict:
    os.environ["OT_SB_LANES"] = "16"
    sys.path.insert(0, str(ROOT / "tools"))
    import rtl_v41_stage_collective_campaign as S  # noqa: E402
    assert S.LANES == 16
    res = {}
    for lat in (142, 228):
        params = dict(LANES=16, DEPTH=2, QTX=2, PKG_DIES=2, LAT_U=11, BPC_U=3864, LAT_X=lat, BPC_X=15758,
                      BPC_X_DEN=100, FLIT_OVH=0)
        exe = S.build(scratch, "tb_v41_stage_collective", params)
        vec = scratch / f"vec_matched_{lat}"
        S.vectors(vec, 8, [[0] * 8] * S.N, 0, 7000 + lat)
        txt = S.sh([str(exe), f"+VEC={vec}", "+WORDS=8", "+START=20", "+SKEW=3", "+MODE=0", "+TIMEOUT=60000"])
        arr = [tuple(map(int, m.groups())) for m in S.ARR.finditer(txt)]
        dn = S.DONE.search(txt)
        sbs = [dict(zip(("die", "start", "ref", "pushed_last", "stall", "hold", "qmax", "first", "last", "fault",
                         "code"), map(int, m.groups()))) for m in S.SB.finditer(txt)]
        per_word = {k: max(t for d, w, t in arr if w == k) for k in range(8)}
        res[str(lat)] = dict(
            lat_x=lat, params=params, plusargs=dict(WORDS=8, START=20, SKEW=3, MODE=0, ready="all words at t=0"),
            passed=dn.group(5) == "PASS", mismatches=int(dn.group(2)),
            first_reduced_all_ranks=per_word[0], last_reduced_all_ranks=per_word[7],
            reduced_cycles_by_rank={str(q): [t for d, w, t in sorted(arr, key=lambda x: x[1]) if d == q] for q in range(4)},
            collective_span_cycles=per_word[7] - per_word[0],
            wave_period_cycles=sorted({per_word[k + 2] - per_word[k] for k in (0, 2, 4)}),
            producer_stall_cycles={str(s["die"]): s["stall"] for s in sbs},
            fifo_qmax={str(s["die"]): s["qmax"] for s in sbs})
    res["sources_sha256"] = {rel(p): sha(p) for p in (S.ENGINE, S.TB, S.ADDER, ROOT / "tools/rtl_v41_stage_collective_campaign.py")}
    return res


def model_side() -> dict:
    lanes = json.loads(LANES_JSON.read_text())["collective_exposure"]
    st = json.loads(STAGE.read_text())["summary"]["patterns"]["allreduce_wo_b"]
    lv = lanes["levers"]
    return dict(
        stub_baseline_tail_cycles=st["measured_exposed_tail_cycles"],
        stub_baseline_case=dict(words=40, lanes=128, rx_depth=64, lat_x=142, record=rel(STAGE)),
        stub_depth_sweep_d8=st["depth_sweep"]["8"],
        adopted_lever_tail_cycles=lv["tails"]["allreduce_wo_b"],
        adopted_lever_record=rel(LEVERS),
        model_exposed_cycles=round(lv["per_pattern"]["allreduce_wo_b"]["model_exposed_cycles"], 2),
        all_reduce_residual_cycles_priced=round(lv["terms"]["all_reduce"]["residual_cycles"], 2),
        priced_by=rel(LANES_JSON) + " collective_exposure.levers")


def sensitivity(added: dict) -> dict:
    """First-order, NOT a model run: add a fixed exposure to every on-path all-reduce and rescale the design point's
    token and MTP verify times.  On-path all-reduce count from the stage campaign's design-point dump."""
    pats = json.loads(STAGE.read_text())["patterns"]
    n = pats["allreduce_wo_b"]["on_path"] + pats["allreduce_down"]["on_path"]
    dp = json.loads(LANES_JSON.read_text())["design_point"]
    out = dict(on_path_all_reduces=n, on_path_source=rel(STAGE) + " patterns.*.on_path", cases={})
    for name, cyc in added.items():
        dt = n * cyc / CLOCK * 1e6
        row = dict(added_cycles_per_all_reduce=cyc, added_us_per_token=round(dt, 3))
        for ctx, v in dp.items():
            row[ctx] = dict(ar_now=round(v["ar"]), ar_if_unpriced=round(1e6 / (v["T_us"] + dt)),
                            mtp_now=round(v["mtp"]), mtp_if_unpriced=round(v["mtp"] * v["verify_us"] / (v["verify_us"] + dt)))
        out["cases"][name] = row
    return out


def compare(real: dict, stub: dict, model: dict) -> dict:
    rows = {}
    for lat in ("142", "228"):
        r, s = real[lat], stub[lat]
        rows[lat] = dict(
            per_rank_delta_cycles={q: sorted({a - b for a, b in zip(r["reduced_cycles_by_rank"][q],
                                                                 s["reduced_cycles_by_rank"][q])})
                                   for q in r["reduced_cycles_by_rank"]},
            first_reduced_delta_cycles=r["first_reduced_all_ranks"] - s["first_reduced_all_ranks"],
            last_reduced_delta_cycles=r["last_reduced_all_ranks"] - s["last_reduced_all_ranks"],
            wave_period_real=r["wave_period_cycles"], wave_period_stub=s["wave_period_cycles"],
            wave_period_equals_2lat_plus_2=r["wave_period_cycles"] == [2 * int(lat) + 2],
            real_core_added_consumer_tail_cycles=r["consumer_tail_after_last_reduced_all"])
    added = max(v["real_core_added_consumer_tail_cycles"] for v in rows.values())
    added_r0 = max(r["consumer_tail_after_last_reduced_rank0"] for r in real.values())
    return dict(
        collective_wave_period_identical=all(v["wave_period_real"] == v["wave_period_stub"] for v in rows.values()),
        constant_offset_cycles=sorted({v["first_reduced_delta_cycles"] for v in rows.values()}
                                      | {v["last_reduced_delta_cycles"] for v in rows.values()}),
        remote_rank_offset_cycles=sorted({d for v in rows.values() for q in ("2", "3")
                                          for d in v["per_rank_delta_cycles"][q]}),
        local_rank_offset_cycles=sorted({d for v in rows.values() for q in ("0", "1")
                                         for d in v["per_rank_delta_cycles"][q]}),
        offset_reading=("Ranks 0 and 1 (the real core's package) receive every reduced word on exactly the stub's cycle; "
                        "ranks 2 and 3 receive each a constant offset later (remote_rank_offset_cycles), because rank 0's core emits its first "
                        "word later than the synthetic ranks start and that word crosses the package link to them. "
                        "The wave period is identical, so the collective adds no tail beyond the stub; the offset is "
                        "producer compute, not collective exposure."),
        sensitivity_upper_bound=sensitivity(dict(consumer_after_last_reduced_all_ranks=added,
                                                 consumer_after_rank0_last_reduced=added_r0)),
        per_lat=rows,
        real_core_added_tail_cycles=added,
        real_core_added_tail_after_rank0_cycles=added_r0,
        real_core_added_tail_ns=round(added / CLOCK * 1e9, 1),
        against_model=dict(
            priced_all_reduce_tail_cycles=model["adopted_lever_tail_cycles"],
            priced_residual_cycles=model["all_reduce_residual_cycles_priced"],
            if_added_to_every_all_reduce_cycles=added,
            note=("The stub tail ends at the last reduced word's arrival; the real-core bench adds the rank-0 "
                  "core's consumer, which here runs one core invocation per word after that word is committed. "
                  "The headline prices hc_post as a streaming consumer that starts on the first arriving word, "
                  "so this per-word serial consumer is an upper bound on the added exposure, not a priced term."),
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-stub", action="store_true", help="run the matched stub bench (Verilator)")
    ap.add_argument("--scratch", type=Path, default=Path(os.environ.get("TMPDIR", "/tmp")) / "c7_realcore_vs_stub")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    real = real_core()
    if a.run_stub:
        a.scratch.mkdir(parents=True, exist_ok=True)
        stub = run_stub(a.scratch)
    else:
        stub = json.loads(a.out.read_text())["matched_stub"]
    model = model_side()
    rec = dict(
        schema="v41_c7_realcore_vs_stub/1",
        tool="tools/v41_c7_realcore_vs_stub.py",
        gate="C7 (rack collective overlap)",
        claim_boundary=("Reduced 4-rank all-reduce at 8 words x 16 lanes, receive depth 2, queue depth 2; ranks 1-3 "
                        "synthetic in the real-core bench; behavioural links and vector memory. Compares timing "
                        "only; not a full-token or full-size tail and not a model input."),
        inputs={rel(p): sha(p) for p in (REAL, STAGE, LEVERS, LANES_JSON)},
        real_core=real, matched_stub=stub, model=model, comparison=compare(real, stub, model))
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["comparison"], indent=1))


if __name__ == "__main__":
    main()
