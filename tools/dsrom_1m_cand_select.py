#!/usr/bin/env python3
"""DS-ROM layer-20 candidate-block select (graph nodes L20.attn.cand.topk_local / .merge / .final) MEASURED in
full-shape RTL at the 1M target token (position 1,048,575) on the golden 1M index scores.

TP4 placement, as tools/dsrom_1m_measure.py `select` does the index select: rank r owns position quarter r
(262,144 scores = 32,768 blocks of 8); its four HBM stacks are the four sub-quarters (65,536 positions each) of
the unit's four ports.

  local  ot_hdc_v41x_sel_cand (Q 4 x SL 16 = 64 scores/cycle, K 2,048, AW 10: the shipped_1m configuration of
         tools/rtl_hdc_v41x_sel_cand_campaign.py) per rank on its slice: block max over 8, the slice's newest
         block pinned to +inf, local top-2,048 blocks.  Checked bit-exact against hdc_golden_v41
         `Model.candidate_blocks` on that slice (cand_b 8, k 2,048).
  merge  4-die all-gather of 2,048 block records per die (byte count only; collectives are measured elsewhere).
  final  ot_hdc_v41x_sel (Q 4 x W 16, IW 17 block index, K 2,048, AW 7 = 2,048 records a quarter, no overflow)
         over the 4 x 2,048 gathered records (rank r on port r): value = the block's TRUE BF16 max, the global
         newest block (131,071) pinned to +inf, top-2,048 by (value desc, block asc).  Checked bit-exact against
         hdc_golden_v41 `topk_lowest_index` on those records, and the kept set against the golden's own candidate
         mask (ctx1048576_cand.npz, positions -> blocks) and the golden's `candidate_blocks` on all 1,048,576 scores.

Cycles = last - first + 1 + tail (as the campaigns compute), us at the 1.2 GHz streaming clock.

  python3 tools/dsrom_1m_cand_select.py --gold DIR --work DIR [--record results/rtl/.../cand_select.json]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41x_sel_campaign as S  # noqa: E402
import rtl_hdc_v41x_sel_cand_campaign as C  # noqa: E402
from dsrom_1m_measure import _segment as sel_segment  # noqa: E402

GOLD_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/cand_select.json"
CLK = 1.2e9
TP, NQ, CB, KB = 4, 4, 8, 2048
PINF = 0x7F80


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def golden_cand(s, k=KB, b=CB):
    """hdc_golden_v41 Model.candidate_blocks(s, len(s)) -> kept block indices (relative to s), ascending."""
    keep = G.Model.candidate_blocks(types.SimpleNamespace(cand_b=b, cand_k=k), s, len(s))[::b]
    return np.nonzero(keep)[0]


def local_segment(bits, lo, n, SL=16):
    """One rank: per-sub-quarter dense beats of (bits, GLOBAL position), expected GLOBAL kept blocks."""
    kept = golden_cand(S.vals_of(bits)) + lo // CB
    cuts = [lo + (n * q) // NQ for q in range(NQ + 1)]
    beats, exps = [], []
    for q in range(NQ):
        a, z = cuts[q], cuts[q + 1]
        bq = [[(int(bits[i - lo]), i) if i < z else None for i in range(b0, b0 + SL)] for b0 in range(a, z, SL)]
        beats.append(bq)
        exps.append([int(x) for x in kept if a <= x * CB < z])
    return (beats, KB, exps, {"n": n, "blocks": n // CB}), [int(x) for x in kept]


def cycles(ps):
    c = ps["last"] - ps["first"] + 1 + ps["tail"]
    return dict(cycles=c, us=round(c / CLK * 1e6, 4), ingest_cycles=ps["last"] - ps["first"] + 1, tail=ps["tail"],
                ovf=ps["ovf"], replays=ps["replays"], stall=ps["stall"], k=ps["k"], nhead=ps["nhead"], n2=ps["n2"],
                n3=ps["n3"])


def run(a):
    G.set_arith("chunk8")
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = np.load(a.gold / "ctx1048576_L20.npz")["L20.index_scores"]
    cand = np.load(a.gold / "ctx1048576_cand.npz")["cand"]
    n_all = len(s)
    assert n_all == 1048576 and cand.shape == (n_all,)
    bits_all = S.bf16_bits(s)
    bf16_exact = bool(np.array_equal(S.vals_of(bits_all), s))
    golden_blocks = np.nonzero(cand[::CB])[0]
    mask_block_uniform = bool(np.array_equal(np.repeat(cand[::CB], CB), cand))
    gold_full = golden_cand(s)                                  # golden's candidate_blocks on all 1M scores
    per = n_all // TP
    segs, labels, local = [], [], []
    for r in range(TP):
        lo = r * per
        seg, kept = local_segment(bits_all[lo:lo + per], lo, per)
        segs.append(seg)
        labels.append(f"L20_cand_rank{r}")
        local.append(kept)
    # block maxima (BF16 bits; the BF16 key order is the value order) of every block
    bmax = S.bf16_bits(s.reshape(-1, CB).max(axis=1))
    newest = (n_all - 1) // CB
    recs_b = np.concatenate([np.asarray(x) for x in local])
    recs_v = bmax[recs_b].copy()
    recs_v[recs_b == newest] = PINF                             # the GLOBAL pin only
    fcuts = np.cumsum([0] + [len(x) for x in local]).tolist()
    segx, gsel = sel_segment(S, G, recs_v, recs_b, fcuts, KB, 16)
    # the same final with the four ranks' local +inf pins carried through (what the local unit's values say)
    pv = recs_v.copy()
    for r in range(TP):
        pv[recs_b == (r + 1) * per // CB - 1] = PINF
    pinned_sel = sorted(int(recs_b[i]) for i in G.topk_lowest_index(S.vals_of(pv), KB))
    print(f"vectors: bf16_exact={bf16_exact} golden_blocks={len(golden_blocks)} local={[len(x) for x in local]} "
          f"final_ref_eq_mask={sorted(gsel) == golden_blocks.tolist()}", flush=True)

    t0 = time.time()
    with cf.ThreadPoolExecutor(3) as ex:
        fl = ex.submit(C.run_config, "cand_local", 4, 16, 20, KB, 10, segs, labels, work, ((0, 0, 1),))
        ff = ex.submit(S.run_config, "cand_final", 4, 16, 17, KB, 7, [segx], ["L20_cand_final"], work, ((0, 0, 1),))
        # sensitivity (not the as-built unit): line memory of a whole sub-quarter (8,192 blocks), no overflow replay
        fa = ex.submit(C.run_config, "cand_local_aw12", 4, 16, 20, KB, 12, segs, labels, work, ((0, 0, 1),))
        cl, cx, ca = fl.result(), ff.result(), fa.result()
    wall = round(time.time() - t0, 1)
    rl, rx = cl["runs"][0], cx["runs"][0]
    per_rank = []
    for r, ps in enumerate(rl.get("per_segment", [])):
        g_slice = golden_cand(s[r * per:(r + 1) * per]) + r * per // CB
        per_rank.append(dict(rank=r, positions=[r * per, (r + 1) * per - 1], kept_blocks=len(local[r]),
                             golden_blocks_in_rank=int(((golden_blocks >= r * per // CB) &
                                                        (golden_blocks < (r + 1) * per // CB)).sum()),
                             pinned_block=(r + 1) * per // CB - 1,
                             pinned_block_in_global_golden=bool(((r + 1) * per // CB - 1) in set(golden_blocks.tolist())),
                             expected_equals_golden_slice=bool(np.array_equal(g_slice, np.asarray(local[r]))),
                             **cycles(ps)))
    fin = cycles(rx["per_segment"][0]) if rx.get("per_segment") else None
    worst = max(per_rank, key=lambda x: x["cycles"]) if per_rank else None
    final_eq_mask = sorted(gsel) == golden_blocks.tolist()
    final_eq_full = sorted(gsel) == gold_full.tolist()
    local_ok = bool(cl["pass"] and len(per_rank) == TP and all(x["expected_equals_golden_slice"] for x in per_rank))
    final_ok = bool(cx["pass"] and fin is not None)
    status = "pass" if local_ok and final_ok and final_eq_mask and final_eq_full and bf16_exact else "fail"
    # merge: each die sends its 2,048 records = (BF16 block max, block index within the rank: 15 bits; the rank is
    # the sender) -> 31 bits, one 4-byte word a record
    rec_bytes = 4
    srcs = {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(C.RTL + S.RTL + [C.TB, C.HARNESS, S.TB, S.HARNESS]))}
    srcs.update({p: sha(ROOT / p) for p in ("tools/hdc_golden_v41.py", "tools/rtl_hdc_v41x_sel_campaign.py",
                                            "tools/rtl_hdc_v41x_sel_cand_campaign.py", "tools/dsrom_1m_measure.py",
                                            "tools/dsrom_1m_cand_select.py")})
    ver = subprocess.run([S.VERILATOR, "--version"], capture_output=True, text=True).stdout.strip()
    out = dict(
        schema="opentallas.dsrom-1m.cand-select.v1",
        scope="DS-ROM L20 candidate-block select at position 1,048,575 (1M), TP4, golden 1M index scores; graph nodes "
              "L20.attn.cand.topk_local (local), L20.attn.cand.merge (all-gather, bytes only), L20.attn.cand.final",
        status=status, simulator=ver, simulator_path=S.VERILATOR, clock_hz=CLK, wall_s=wall,
        golden_shards={"ctx1048576_L20.npz": sha(a.gold / "ctx1048576_L20.npz"),
                       "ctx1048576_cand.npz": sha(a.gold / "ctx1048576_cand.npz")},
        golden=dict(scores=n_all, blocks=n_all // CB, cand_b=CB, cand_k=KB, arith="chunk8",
                    scores_bf16_exact=bf16_exact, cand_mask_block_uniform=mask_block_uniform,
                    golden_mask_blocks=int(len(golden_blocks)),
                    candidate_blocks_full_equals_mask=bool(gold_full.tolist() == golden_blocks.tolist()),
                    golden_mask_blocks_per_rank=[int(((golden_blocks // (per // CB)) == r).sum()) for r in range(TP)],
                    golden_blocks_sha256=hashlib.sha256(json.dumps(golden_blocks.tolist()).encode()).hexdigest()),
        local=dict(unit="ot_hdc_v41x_sel_cand", params=dict(Q=4, SL=16, IWP=20, K=KB, AW=10),
                   placement="rank r = positions [r*262144, (r+1)*262144); port q = stack sub-quarter of 65,536",
                   rtl_pass=cl["pass"], exact_vs_golden_slice=local_ok, per_rank=per_rank,
                   worst_rank=worst and dict(rank=worst["rank"], cycles=worst["cycles"], us=worst["us"]),
                   overflow_note="AW 10 holds 2 x 1,024 = 2,048 block records a sub-quarter; at 1M every rank "
                                 "overflows and the unit asks the source to re-stream the rank's 262,144 scores "
                                 "twice (tail = 2 rescans), as in the committed campaign's shipped_1m rows",
                   sensitivity_aw12=dict(note="NOT the as-built unit: AW 12 (8,192 blocks a sub-quarter, cannot "
                                              "overflow); same vectors", rtl_pass=ca["pass"],
                                         per_rank=[dict(rank=i, **cycles(ps)) for i, ps in
                                                   enumerate(ca["runs"][0].get("per_segment", []))]),
                   vectors_sha256=cl.get("vectors_sha256"), errors=rl.get("errors"), log=None if cl["pass"] else rl.get("log")),
        merge=dict(kind="4-die all-gather of the local kept-block records", records_per_die=KB,
                   record="BF16 block max (16 b) + block index within the sender's rank (15 b) = 31 b -> 4 B",
                   bytes_per_die_sent=KB * rec_bytes, bytes_per_die_received=(TP - 1) * KB * rec_bytes,
                   bytes_on_links_total=TP * (TP - 1) * KB * rec_bytes,
                   gathered_bytes_per_die=TP * KB * rec_bytes),
        final=dict(unit="ot_hdc_v41x_sel", params=dict(Q=4, W=16, IW=17, K=KB, AW=7),
                   input="4 x 2,048 records (rank r on port r, block ascending), value = true BF16 block max, "
                         "block 131,071 (the newest) pinned +inf",
                   rtl_pass=cx["pass"], errors=rx.get("errors"), log=None if cx["pass"] else rx.get("log"),
                   vectors_sha256=cx.get("vectors_sha256"), **(fin or {}),
                   kept_blocks=len(gsel), equals_golden_cand_mask=final_eq_mask,
                   equals_golden_candidate_blocks_full=final_eq_full,
                   newest_block_kept=newest in set(gsel)),
        semantics=dict(
            local_pin="the local unit pins its slice's newest block (golden candidate_blocks on the slice does the same); "
                      "the global golden pins only block 131,071, so ranks 0-2 each force one extra block "
                      "(32,767 / 65,535 / 98,303) into their local list",
            local_pin_harmless_here=all(x["golden_blocks_in_rank"] <= KB - 1 for x in per_rank[:3]) if per_rank else None,
            final_must_use_true_maxima="the final must rank ranks 0-2's pinned blocks by their TRUE block max: with the "
                                       "local +inf pins carried into the final it keeps those three blocks",
            final_with_local_pins_equals_golden=pinned_sel == golden_blocks.tolist(),
            final_with_local_pins_diff=dict(extra=sorted(set(pinned_sel) - set(golden_blocks.tolist())),
                                            missing=sorted(set(golden_blocks.tolist()) - set(pinned_sel))),
            rtl_gap="ot_hdc_v41x_sel_cand exports block indices only (out_blk; u_sel's out_val is not brought out) and "
                    "its front end overwrites the pinned block's max with +inf, so as built the merge records' values "
                    "(and the true max of ranks 0-2's pinned blocks) are not available from the unit; the final here "
                    "takes them from the golden scores"),
        source_sha256=srcs)
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(out, indent=1, default=int) + "\n")
    print(json.dumps(dict(status=status, local=[(x["rank"], x["cycles"], x["us"]) for x in per_rank],
                          final=fin and (fin["cycles"], fin["us"]), final_eq_mask=final_eq_mask), default=int))
    return 0 if status == "pass" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    ap.add_argument("--work", type=Path, required=True, help="vectors + Verilator builds (bulk; compute host)")
    ap.add_argument("--record", type=Path, default=REC)
    sys.exit(run(ap.parse_args()))


if __name__ == "__main__":
    main()
