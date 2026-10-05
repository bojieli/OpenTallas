#!/usr/bin/env python3
"""Vectors for the selected-CKV path bench (rtl/test/tb_chip_v41x_ckv_sel_attn.sv).

One indexed DeepSeek-V4.1 attention job per case, built with the golden's own functions
(tools/hdc_golden_v41.py):
  * window rows      qdq_fp8(latent) of random BF16 latents, stored as E4M3 codes + UE8M0 per 32;
  * compressed rows  qdq_fp4_e4m3(latent, 16) of random BF16 latents (magnitudes 2^-12 .. 2^12, one saturating
                     row), stored as the 288-B main-KV row of runtime/prefill/v41_main_kv_row.py
                     (512 E2M1 nibbles low first + 32 E4M3 scales) in the HBM image of the owning die/stack;
  * selection        sel = sorted(topk_lowest_index(s, min(512, n))) over indexer scores s of n compressed rows
                     (Model.indexer's last line), emitted on the final select's four quarter ports;
  * rows             window rows oldest first + ckv[i] for i in sel (Model.attention), T = wcount + n_sel;
  * expected         s = dots(q, kvm) and pv = dots(p, kvm.T) (Model.attend's two engine products, as
                     tools/v41_full_attention_numeric_prepare.py) on the golden-stored rows.
The stored-format rows the engine dequantises are checked equal (bitwise) to the golden qdq values here.
Owner placement (ot_chip_v41x_ckv_selected_dma): die = id[5:4], stack = id[7:6],
local = (id >> 8) * 16 + id % 16, sector = base[stack] + 9 * local + k.  Neighbouring rows (id +- 1, id +- 256)
are also written with different content, so an addressing error reads a wrong but present row.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _campaign():
    path = ROOT / "tools/rtl_hdc_v41x_attn_campaign.py"
    sp = importlib.util.spec_from_file_location("attn_campaign", path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


C = _campaign()
V = C.V
F = np.float32
from runtime.prefill.v41_main_kv_row import pack_main_row  # noqa: E402

GOLDEN = ["tools/hdc_golden_v41.py", "tools/rtl_hdc_v41x_attn_campaign.py", "runtime/prefill/v41_main_kv_row.py",
          "tools/v41_ckv_sel_attn_vectors.py"]
H, D, TD = 16, 512, 32
TOPK = 512

# cases: (name, window rows, compressed rows n, selection kind)
CASES = [
    ("full1m", 128, 262144, "random"),      # 1M context (ratio 4): T = 128 + 512, ids over all 16 owners
    ("short300", 128, 300, "random"),       # n_sel = n = 300 < 512
    ("skew1m", 128, 262144, "die3"),        # every selected row owned by one remote die (die 3, board link)
    ("tail46", 37, 9, "random"),            # early context: partial window beat completed by CKV rows
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def owner(g):
    return (g >> 4) & 3, (g >> 6) & 3, ((g >> 8) << 4) | (g & 15)


def latent(rng, n, scale_exp=None):
    x = rng.standard_normal(n).astype(np.float64)
    x *= 2.0 ** (rng.integers(-12, 13) if scale_exp is None else scale_exp)
    x[rng.random(n) < 0.02] = 0.0
    return V.to_bf16(x.astype(F))


def fp4_codes(x):
    """(E2M1 codes 0..15, E4M3 scale codes) of the golden's qdq_fp4_e4m3(x, 16): its own lines, incl. the
    min(., 448) scale saturation."""
    x = np.asarray(x, dtype=F).reshape(-1, 16)
    amax = np.maximum(np.max(np.abs(x), axis=1), V.FP4_AMAX_FLOOR_E4M3).astype(F)
    s = np.minimum(V._e4m3_round(amax.astype(np.float64) / V.FP4_MAX), 448.0)
    a = np.abs(x.astype(np.float64))
    code = np.zeros(a.shape, dtype=np.int64)
    for i, m in enumerate(V.E2M1_MIDPOINTS):
        t = m * s[:, None]
        code = np.where((a > t) | ((a == t) & ((i + 1) % 2 == 0)), i + 1, code)
    code = code + 8 * np.signbit(x)
    return code.reshape(-1), np.array([C.e4m3_code(v) for v in s], dtype=np.int64)


def selection(rng, n, kind):
    k = min(TOPK, n)
    if kind == "random":
        s = V.to_bf16(rng.standard_normal(n).astype(F))              # BF16 scores: many ties (lower index wins)
    else:
        s = V.to_bf16(rng.standard_normal(n).astype(F)).astype(np.float64)
        ids = np.arange(n)
        s = np.where(((ids >> 4) & 3) == 3, s + 64.0, s)             # die-3 groups outrank every other
    sel = sorted(int(i) for i in V.topk_lowest_index(np.asarray(s, dtype=np.float64), k))
    return sel


def quarters(n, sel):
    qs = 8 * (n // 32)
    bounds = [0, qs, 2 * qs, 3 * qs, n]
    return [sum(1 for g in sel if bounds[q] <= g < bounds[q + 1]) for q in range(4)]


def make_case(out: Path, name, wcount, n, kind, seed):
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    sel = selection(rng, n, kind)
    nsel = len(sel)
    T = wcount + nsel
    # window rows (golden qdq_fp8)
    win_vals, win_codes, win_scales, win_words = [], [], [], []
    for _ in range(wcount):
        x = latent(rng, D)
        codes, sc16 = C.fp8_row_codes(x)
        win_vals.append(V.qdq_fp8(x))
        win_codes.append(codes)
        win_scales.append(sc16)
        w = sum(int(c) << (8 * e) for e, c in enumerate(codes))
        w |= sum(int(sc16[2 * g]) << (4096 + 8 * g) for g in range(16))
        win_words.append(w)
    # compressed rows: every selected row plus decoy neighbours
    ids = set(sel)
    decoys = {g + dd for g in sel for dd in (-256, -1, 1, 256) if 0 <= g + dd < n} - ids
    rows = {}
    for i, g in enumerate(sorted(ids | decoys)):
        x = latent(rng, D, scale_exp=13 if (g in ids and i % 97 == 5) else None)   # a few saturating rows
        codes, scales = fp4_codes(x)
        rows[g] = (V.qdq_fp4_e4m3(x, 16), codes, scales)
    max_local = ((n - 1) >> 8 << 4) + 15
    base = [1_000_003 * (s + 1) for s in range(4)]
    count = [9 * (max_local + 1)] * 4
    hkey, hdat = [], []
    for g in sorted(rows):
        die, stack, local = owner(g)
        packed = pack_main_row([int(c) for c in rows[g][1]], [int(s) for s in rows[g][2]])
        for k in range(9):
            addr = base[stack] + 9 * local + k
            hkey.append((die << 32) | (stack << 30) | addr)
            hdat.append(int.from_bytes(packed[32 * k:32 * (k + 1)], "little"))
    # the golden's rows and the stored-format job
    fmt = np.array([0] * wcount + [1] * nsel, dtype=np.int64)
    codes = np.array(win_codes + [rows[g][1] for g in sel], dtype=np.int64).reshape(T, D)
    scales = np.array(win_scales + [rows[g][2] for g in sel], dtype=np.int64).reshape(T, D // 16)
    q = C.from_bf16(C.rand_bf16(rng, (H, D), "wide"))
    p = C.from_bf16(C.rand_bf16(rng, (H, T), "prob"))
    job = C.Job(q, fmt, codes, scales, p, f"ckvsel {name}")
    golden_rows = np.stack(win_vals + [rows[g][0] for g in sel]).astype(F)
    kvm = job.kvm()
    assert np.array_equal(V.bits(kvm), V.bits(golden_rows)), "stored-format rows differ from the golden qdq rows"
    assert np.all(C.deq_in_domain(np.repeat(fmt[:, None], D, 1), codes, np.repeat(scales, 16, 1)))
    counts, stats = C.write_jobs(out, [job], H, D, TD)
    C.write_hex(out / "sel.hex", sel or [0], 32)
    C.write_hex(out / "win.hex", win_words or [0], 4224)
    C.write_hex(out / "hkey.hex", hkey, 64)
    C.write_hex(out / "hdat.hex", hdat, 256)
    qc = quarters(n, sel)
    cfg = [wcount, nsel, n, len(hkey), T, *qc, *base, *count]
    C.write_hex(out / "cfg.hex", cfg + [0] * (32 - len(cfg)), 32)
    owners = sorted({owner(g)[:2] for g in sel})
    return dict(name=name, window_rows=wcount, compressed_rows=n, n_sel=nsel, T=T, selection=kind, seed=seed,
                quarter_counts=qc, owners_die_stack=[list(o) for o in owners],
                owned_rows_per_die=[sum(1 for g in sel if owner(g)[0] == d) for d in range(4)],
                hbm_sectors=len(hkey), decoy_rows=len(decoys), first_ids=sel[:8], last_ids=sel[-4:],
                counts=counts, expected=stats,
                images={x.name: sha(x) for x in sorted(out.glob("*.hex"))})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cases", default="")
    a = ap.parse_args()
    V.set_arith("chunk8")
    cases = []
    for i, (name, w, n, kind) in enumerate(CASES):
        if a.cases and name not in a.cases.split(","):
            continue
        cases.append(make_case(a.out / name, name, w, n, kind, 20260930 + i))
        print(name, cases[-1]["T"], cases[-1]["owned_rows_per_die"], len(cases[-1]["owners_die_stack"]), flush=True)
    rec = dict(scope="Synthetic golden inputs at H16 D512 TD32 NL4 T<=640 through the selected-CKV path; "
                     "rows are the golden's qdq_fp8 / qdq_fp4_e4m3 rows, selection is the golden's top-k.",
               parameters=dict(H=H, D=D, TD=TD, NL=4, TROWS=640, TOPK=TOPK),
               golden_sources={g: sha(ROOT / g) for g in GOLDEN}, cases=cases)
    (a.out / "manifest.json").write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
