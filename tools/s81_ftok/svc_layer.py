#!/usr/bin/env python3
"""The S81 scan service (dsfd_svc_c, engine svc) on the REAL attention of a 1M-token layer (s81-functional-token r3,
2026-10-14).

tools/v41_ckv_sel_attn_vectors.py builds the slab-pin gate's vectors (rtl/dsrom_sys/s81_ph/svc/h/tb_dsfd_svc_c.sv,
run_svc_c_bench.sh) from RANDOM latents; this tool writes the same files from one layer's golden attention, captured
by tools/dsrom_1m_su.py golden (snap_LXX.pkl: attend.kvm = the T rows the golden attends to, window rows oldest first
then the selected compressed rows; attn_rows = window count, the selection ids into the KV source's compressed rows,
the source's row count; q = the die's 16 post-RoPE heads; e = the softmax numerators, P = BF16(e)):
  window rows      stored as the golden's FP8 E4M3 codes + UE8M0 scales of the row (C.fp8_row_codes);
  selected rows    stored as the 288-B main-KV row (E2M1 + E4M3 per 16, pack_main_row) in the HBM image of the
                   owner die / stack of their id; decoy neighbours (id +- 1, +- 256) with other content;
  expected         sc = dots(q, kvm), pv = dots(P, kvm.T): ASSERTED equal to the layer's golden s_raw and pv.
Every stored-format row is asserted to dequantise to the golden row bit for bit (Job.kvm()).

    python3 tools/s81_ftok/svc_layer.py --snap snap_LXX.pkl --out DIR/LXX
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import v41_ckv_sel_attn_vectors as VV  # noqa: E402

C, V = VV.C, VV.V
F = np.float32
H, D, TD = VV.H, VV.D, VV.TD


def _exact_codes(fmt, x):
    """Stored codes of ONE golden row that dequantise to it bit for bit.  The golden's own encoder re-run on an
    already quantised row is tried first; a quantise-dequantise is not always idempotent (the scale comes from the
    block amax, which the rounding can lower), so per block the scale is otherwise SEARCHED: FP8 every UE8M0
    exponent, FP4 every E4M3 scale, keeping the first under which every element has a code."""
    x = np.asarray(x, F)
    if fmt == 0:
        codes, sc16 = C.fp8_row_codes(x)
    else:
        codes, sc16 = VV.fp4_codes(x)
    f = np.full(D, fmt, dtype=np.int64)
    if np.array_equal(V.bits(C.deq_value(f, codes, np.repeat(sc16, 16))), V.bits(x)):
        return np.asarray(codes, np.int64), np.asarray(sc16, np.int64)
    codes, sc16 = np.array(codes, np.int64), np.array(sc16, np.int64)
    blk = 32 if fmt == 0 else 16
    cand = range(256) if fmt == 0 else sorted({C.e4m3_code(v) for v in V.E4M3 if np.isfinite(v) and v > 0})
    ncode = 256 if fmt == 0 else 16
    for b0 in range(0, D, blk):
        xb = x[b0:b0 + blk]
        fb = np.full(blk, fmt, dtype=np.int64)
        done = False
        for s in cand:
            sb = np.full(blk, s, dtype=np.int64)
            table = {}
            for c in range(ncode):
                vv = C.deq_value(fb[:1], np.array([c]), sb[:1])[0]
                table.setdefault(int(V.bits(np.asarray([vv], F))[0]), c)
            want = V.bits(xb)
            if all(int(w) in table for w in want):
                codes[b0:b0 + blk] = [table[int(w)] for w in want]
                if fmt == 0:
                    sc16[b0 // 16:b0 // 16 + 2] = s
                else:
                    sc16[b0 // 16] = s
                done = True
                break
        assert done, (fmt, b0)
    assert np.array_equal(V.bits(C.deq_value(f, codes, np.repeat(sc16, 16))), V.bits(x))
    return codes, sc16


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snap", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20261014)
    a = ap.parse_args()
    V.set_arith("chunk8")
    s = pickle.loads(a.snap.read_bytes())
    at, ar = s["hc"]["attend"], s["attn_rows"]
    kvm = np.asarray(at["kvm"], F)
    T = kvm.shape[0]
    wcount, sel = int(ar["window"]), [int(g) for g in ar["sel"]]
    n = max(int(ar["ncomp"]), 1)
    assert wcount + len(sel) == T, (wcount, len(sel), T)
    assert T <= 640
    rng = np.random.default_rng(a.seed)
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    win_codes, win_scales, win_words = [], [], []
    for r in range(wcount):
        codes, sc16 = _exact_codes(0, kvm[r])
        win_codes.append(codes)
        win_scales.append(sc16)
        w = sum(int(c) << (8 * e) for e, c in enumerate(codes))
        w |= sum(int(sc16[2 * g]) << (4096 + 8 * g) for g in range(16))
        win_words.append(w)
    ids = set(sel)
    decoys = {g + dd for g in sel for dd in (-256, -1, 1, 256) if 0 <= g + dd < n} - ids
    rows = {}
    for t, g in enumerate(sel):
        codes, scales = _exact_codes(1, kvm[wcount + t])
        rows[g] = (kvm[wcount + t], codes, scales)
    for g in sorted(decoys):
        x = VV.latent(rng, D)
        codes, scales = VV.fp4_codes(x)
        rows[g] = (V.qdq_fp4_e4m3(x, 16), codes, scales)
    max_local = ((n - 1) >> 8 << 4) + 15
    base = [1_000_003 * (k + 1) for k in range(4)]
    count = [9 * (max_local + 1)] * 4
    hkey, hdat = [], []
    for g in sorted(rows):
        die, stack, local = VV.owner(g)
        packed = VV.pack_main_row([int(c) for c in rows[g][1]], [int(x) for x in rows[g][2]])
        for k in range(9):
            hkey.append((die << 32) | (stack << 30) | (base[stack] + 9 * local + k))
            hdat.append(int.from_bytes(packed[32 * k:32 * (k + 1)], "little"))
    fmt = np.array([0] * wcount + [1] * len(sel), dtype=np.int64)
    codes = np.array(win_codes + [rows[g][1] for g in sel], dtype=np.int64).reshape(T, D)
    scales = np.array(win_scales + [rows[g][2] for g in sel], dtype=np.int64).reshape(T, D // 16)
    q = np.asarray(at["q"], F)[:H]
    p = V.to_bf16(np.asarray(at["e"], F)[:H])
    job = C.Job(q, fmt, codes, scales, p, f"s81ftok {a.snap.stem}")
    checks = dict(stored_rows_equal_golden_rows=bool(np.array_equal(V.bits(job.kvm()), V.bits(kvm))),
                  q_is_q_rope_out=bool(np.array_equal(V.bits(q), V.bits(np.asarray(s["q_rope"]["out"], F)[:H]))),
                  sc_equals_golden_s_raw=bool(np.array_equal(V.bits(V.dots(q, kvm)), V.bits(np.asarray(at["s_raw"], F)[:H]))),
                  pv_equals_golden_pv=bool(np.array_equal(V.bits(V.dots(p, kvm.T)), V.bits(np.asarray(at["pv"], F)[:H]))))
    assert all(checks.values()), checks
    counts, stats = C.write_jobs(out, [job], H, D, TD)
    C.write_hex(out / "sel.hex", sel or [0], 32)
    C.write_hex(out / "win.hex", win_words or [0], 4224)
    C.write_hex(out / "hkey.hex", hkey, 64)
    C.write_hex(out / "hdat.hex", hdat, 256)
    qc = VV.quarters(n, sel)
    cfg = [wcount, len(sel), n, len(hkey), T, *qc, *base, *count]
    C.write_hex(out / "cfg.hex", cfg + [0] * (32 - len(cfg)), 32)
    rec = dict(snap=str(a.snap), layer=s.get("layer", s.get("ftok_name")), T=T, window=wcount, n_sel=len(sel),
               compressed_rows=n, decoys=len(decoys), checks=checks, counts=counts, expected=stats,
               owners_die_stack=sorted({VV.owner(g)[:2] for g in sel}))
    (out / "case.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps({k: rec[k] for k in ("layer", "T", "window", "n_sel", "checks")}, default=str))


if __name__ == "__main__":
    main()
