#!/usr/bin/env python3
"""The S81 Engram slab master (dsfd_engram_c, engine 10) on the REAL 1M token (s81-functional-token r4, 2026-10-14).

tools/s81_svceng/engram_c_gate.py runs the slab on random windows over a synthetic table (one splitmix row model).
This tool runs the same bench (rtl/test/tb_dsfd_engram_c.sv: idwin -> 2 layers x 4 ranks of dsfd_engram_c -> TP4
all-gather -> sinks -> slot read through the master's VM port) with the token's own window and the RELEASED table rows:

  golden   the 1M token's history (w17 golden_ctx1048576_0-39.json) -> hdc_golden_v41.EngramTables (released config +
           tokenizer compressed map) -> the 24 hash rows of layers 1 and 14 (asserted == the rows the golden checkpoint
           subset carries, SUBSET.json engram_rows) -> codes [24, 256] E4M3 + exponents [24, 8] UE8M0 read from the
           checkpoint -> decode_engram_rows (the golden's own decode) = the expected BF16 rows;
           the shipped hash unit's model (hdc_v41_engram_shipped.hashes on the compressed window) is asserted to give
           the same row ids.
  vectors  4 tokens of one user (first = the oldest): the newest token's official window is the real 4-gram window;
           the 48 real rows go to the bench's HBM model by +REAL (byte 0..255 codes, 256..263 exponents; CRC by the
           bench); the 3 warm-up tokens hit synthetic rows (row_bytes8) and are checked against the synthetic model.
  verdict  every dump of every token exact (rank 0 buffer, 4 ranks identical), the real token's 2 x 24 rows equal the
           golden decode element for element.

    python3 tools/s81_ftok/engram_real.py golden --work DIR      # checkpoint host (OT_V41_FLASH_SNAPSHOT)
    python3 tools/s81_ftok/engram_real.py run --work DIR [--mut]
--mut builds the lookup with OT_ENGRAM_MUT_ONESCALE (block 0's exponent on every beat = the pre-F13 decode): the
negative control, must FAIL on the real rows.  Verdict line: ENGRAM_REAL PASS|FAIL <tag>.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81_svceng"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
CTX = 1048576
LAYERS = (1, 14)


def cmd_golden(a):
    import hdc_golden_v41 as V
    import hdc_v41_engram_shipped as ES
    import rtl_v41_fullshape_layer_campaign as LC
    w = Path(a.work)
    w.mkdir(parents=True, exist_ok=True)
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=True)
    hist = [int(x) for x in json.loads((GOLD / f"golden_ctx{CTX}_0-39.json").read_text())["history"]]
    cids = [int(m.engram.token_map[h]) for h in hist[-4:]]             # oldest first
    t = ES.shipped_tables()
    hs = ES.hashes(t, cids)
    snap = Path(os.environ["OT_V41_FLASH_SNAPSHOT"])
    sub = json.loads((snap / "SUBSET.json").read_text()).get("engram_rows", {})
    rec = dict(history_len=len(hist), last4_raw=hist[-4:], last4_compressed=cids, layers={})
    real, words = [], {}
    for li, L in enumerate(LAYERS):
        ids = [int(x) for x in m.engram.hashes(hist, li)]
        assert ids == hs[li], ("shipped hash model != golden EngramTables", L)
        if sub:
            assert sorted(ids) == sorted(int(x) for x in sub[f"layers.{L}.engram.embed.weight"]), ("subset rows", L)
        codes = np.asarray(ck.rows(f"layers.{L}.engram.embed.weight", ids), np.uint8)            # [24, 256]
        exps = np.asarray(ck.rows(f"layers.{L}.engram.embed.scale", ids), np.int64)             # [24, 8] (-127)
        assert codes.shape == (24, 256) and exps.shape == (24, 8)
        gold = V.decode_engram_rows(codes, exps, np.arange(24))
        gbits = (V.bits(np.asarray(gold, V.F)) >> 16).astype(np.int64)
        model = ES.decode_rows8(codes, exps + 127)
        assert np.array_equal(model, gbits), "decode_rows8 != golden decode_engram_rows"
        nonuni = int(sum(len(set(r.tolist())) > 1 for r in exps))
        for j, r in enumerate(ids):
            b = bytes(codes[j].tolist()) + bytes((exps[j] + 127).tolist())
            real.append(f"{li} {r} {int.from_bytes(b, 'little'):x}\n")
        words[li] = ES.words_of_rows(gbits)
        rec["layers"][str(L)] = dict(rows=ids, rows_with_nonuniform_block_exponents=nonuni,
                                     one_exponent_decode_mismatching_elements=int(
                                         (ES.decode_rows8(codes, np.repeat(exps[:, :1] + 127, 8, axis=1)) != gbits).sum()))
    (w / "real_rows.txt").write_text("".join(real))
    (w / "expected.json").write_text(json.dumps({str(k): v for k, v in words.items()}))
    (w / "golden.json").write_text(json.dumps(rec, indent=1))
    print("ENGRAM_REAL_GOLDEN", json.dumps({L: {k: v for k, v in r.items() if k != "rows"} for L, r in rec["layers"].items()}))
    return 0


def cmd_run(a):
    import engram_c_gate as EG
    C = EG.C
    w = Path(a.work)
    rec = json.loads((w / "golden.json").read_text())
    exp_real = {int(k): v for k, v in json.loads((w / "expected.json").read_text()).items()}
    cids = rec["last4_compressed"]
    ev = [(0, 0, 1 if i == 0 else 0, 0, c) for i, c in enumerate(cids)]
    wins = C.official_windows(ev)
    assert wins[-1] == [cids[3], cids[2], cids[1], cids[0]], wins[-1]
    real_ids = {(li, r) for li, L in enumerate(LAYERS) for r in rec["layers"][str(L)]["rows"]}
    t = C.ES.shipped_tables()
    for tk in range(3):
        for li in range(2):
            rows = C.ES.hashes(t, list(reversed(wins[tk])))[li]
            assert not real_ids & {(li, int(r)) for r in rows}, "warm-up token hits a real row"
    syn = C.expected

    def expected(tt, win, li):
        return exp_real[li] if win == wins[-1] else syn(tt, win, li)
    C.expected = expected
    if a.mut:
        EG.EXTRA_VL = ["+define+OT_ENGRAM_MUT_ONESCALE"]
    tag = "mut_onescale" if a.mut else "base"
    exe = EG.build(w / f"obj_{tag}", {})
    out = {}
    for name, args in (("ideal_hbm_200ns", dict(LAT=240)), ("stressed", EG.STRESS)):
        args = dict(args, REAL=str((w / "real_rows.txt").resolve()))
        r = C.run_mode(exe, w, t, ev, wins, f"{tag}_{name}", args, None)
        out[name] = {k: r.get(k) for k in ("pass", "tokens", "dumps_compared", "elements_compared", "element_mismatches",
                                           "all_dumps_present", "window_errors", "xrank_errors", "engine_faults", "cycles",
                                           "latency_cycles_window_to_slot_ready", "log")}
        print(tag, name, "pass" if r.get("pass") else "FAIL", "mismatches", r.get("element_mismatches"), flush=True)
    ok = all(v["pass"] for v in out.values())
    res = dict(tag=tag, verdict="PASS" if ok else "FAIL", modes=out, golden=rec)
    (w / f"result_{tag}.json").write_text(json.dumps(res, indent=1, default=str))
    print("ENGRAM_REAL", "PASS" if ok else "FAIL", tag)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("golden", "run"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--mut", action="store_true")
    a = ap.parse_args()
    return cmd_golden(a) if a.step == "golden" else cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
