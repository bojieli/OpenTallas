#!/usr/bin/env python3
"""S81 layer vehicle, seam S6 (HBM -> svc -> VM): tb_dsfd_svc_c vectors from the HGI exporter's 1M-token export.

Same files / format as tools/v41_ckv_sel_attn_vectors.py (cfg / sel / win / hkey / hdat / jobs / q / p / sc / pv hex),
but every operand is the exporter's rank-0 data of DeepSeek-V4.1-Flash at position 1,048,575 (context 1,048,576):
  window rows    the 128 window KV rows the attention reads: hbm.bin at the doorbell + the layer's own hbmw.bin
                 writes (window_row_append), FP32 qdq_fp8 values -> E4M3 codes + UE8M0 scales (exact decomposition);
  selected rows  the 512 compressed-KV ids of the layer's index merge (vm_final, the TOPK_MERGE output) and their rows
                 (the ROW_GATHER output in hbmw.bin), FP32 qdq_fp4_e4m3 values -> E2M1 codes + E4M3 scales (exact
                 decomposition), stored as main-KV rows in the HBM image of their owner die / stack (the HBM-side TLM);
  q, p           rank 0's head: q = the qk record's A operand, p = attend.bf16_p's output (vm_final);
  expected       the golden engine products s = q.kvm, pv = p.kvm^T (C.Job.expected), and cross-checked BIT-EXACT
                 against the exporter's own s (qk record O) and pv (pv record O) of the released-checkpoint golden.
Rank 0 owns one head; the slab's H = 16 head lanes all carry that head (stated, not hidden).  Decoy neighbour rows
(id +- 1, +- 256) hold other real selected rows, so an addressing error reads a present but wrong row.
Usage: svc_1m_vectors.py --vec <export dir> --out <case dir> [--name real1m_L2]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
_sp = importlib.util.spec_from_file_location("ckvsel", ROOT / "tools/v41_ckv_sel_attn_vectors.py")
G = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(G)
C, V, F = G.C, G.V, np.float32
H, D, TD = G.H, G.D, G.TD
WIN_BASE, CKV_SEL = 17179895072, 34359738368


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ranges(path: Path):
    b = path.read_bytes()
    o, out = 0, []
    while o < len(b):
        a, n = struct.unpack_from("<QQ", b, o)
        out.append((a, b[o + 16:o + 16 + n]))
        o += 16 + n
    return out


class Hbm:
    def __init__(self, vec: Path):
        self.m = {}
        for a, dat in ranges(vec / "hbm.bin"):
            self.put(a, dat)
        for a, dat in ranges(vec / "hbmw.bin"):        # the layer's own writes (window append, row gather)
            self.put(a, dat)

    def put(self, a, dat):
        for i in range(0, len(dat), 4):
            self.m[a + i] = dat[i:i + 4]

    def f32(self, a, n):
        miss = [a + 4 * i for i in range(n) if a + 4 * i not in self.m]
        assert not miss, f"HBM read outside the exported ranges at {miss[0]:#x}"
        return np.frombuffer(b"".join(self.m[a + 4 * i] for i in range(n)), "<f4").astype(F)


def fp8_codes_exact(x):
    """E4M3 codes + per-32 UE8M0 scale codes whose dequant is x bit-exactly (golden fp8_row_codes on the qdq value)."""
    qx = V.qdq_fp8(x)
    nz = (V.bits(x) == 0x80000000)                     # the exporter keeps -0.0 where the golden qdq writes +0.0
    assert np.array_equal(V.bits(qx)[~nz], V.bits(x)[~nz]) and np.all(qx[nz] == 0), "window row not a qdq_fp8 fixed point"
    codes, sc = C.fp8_row_codes(x)
    codes = np.where(nz, 0x80, codes)                  # E4M3 -0 code: the stored row dequantises to x bit-exactly
    return codes, sc


def fp4_codes_exact(x):
    """E2M1 codes + E4M3 scales per 16 with deq == x bit-exactly; the golden's own quantiser when x is its fixed
    point, else the largest E4M3 scale that represents the block exactly."""
    if np.array_equal(V.bits(V.qdq_fp4_e4m3(x, 16)), V.bits(x)):
        return G.fp4_codes(x)
    codes, scales = [], []
    grid = np.array([0, .5, 1, 1.5, 2, 3, 4, 6], dtype=np.float64)
    for blk in np.asarray(x, dtype=np.float64).reshape(-1, 16):
        amax = np.max(np.abs(blk))
        best = None
        for c in grid[::-1][:-1] if amax > 0 else []:
            s = amax / c
            if s > 448 or V._e4m3_round(s) != s:
                continue
            k = np.abs(blk) / s
            idx = np.searchsorted(grid, k)
            if np.all(idx < 8) and np.all(grid[np.minimum(idx, 7)] == k):
                best = (s, idx)
                break
        if best is None:
            assert amax == 0, "compressed row block has no exact E2M1 x E4M3 decomposition"
            best = (V._e4m3_round(V.FP4_AMAX_FLOOR_E4M3 / V.FP4_MAX), np.zeros(16, dtype=np.int64))
        s, idx = best
        codes += list(idx + 8 * np.signbit(blk))
        scales.append(C.e4m3_code(s))
    return np.array(codes, dtype=np.int64), np.array(scales, dtype=np.int64)


def find(meta, op, tag_sub):
    for r in meta["records"]:
        if r["op"] == op and tag_sub in r["tag"]:
            return r
    raise KeyError((op, tag_sub))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", default="real1m")
    a = ap.parse_args()
    V.set_arith("chunk8")
    meta = json.loads((a.vec / "meta.json").read_text())
    vmf = np.frombuffer((a.vec / "vm_final.bin").read_bytes(), "<u4")
    vf = lambda o, n: vmf[o:o + n].view("<f4").astype(F)
    hbm = Hbm(a.vec)
    qk, bp, pvr = find(meta, "QK", "attend.qk"), find(meta, "VOP", "attend.bf16_p"), find(meta, "PV", "attend.pv")
    T = qk["eff"]["O"][1]
    wcount = qk["eff"]["B"][2]
    assert qk["eff"]["B"][0] == WIN_BASE and qk["eff"]["B"][1] == 128
    nsel = T - wcount
    n = (meta["position"] + 1) // 4            # compressed rows at the position (ratio 4)
    # window rows (oldest first, as the exporter's B operand rows)
    stride = qk["eff"]["B"][3]
    win_vals, win_codes, win_scales, win_words = [], [], [], []
    for r in range(wcount):
        x = hbm.f32(WIN_BASE + r * stride, D)
        codes, sc16 = fp8_codes_exact(x)
        win_vals.append(x); win_codes.append(codes); win_scales.append(sc16)
        w = sum(int(c) << (8 * e) for e, c in enumerate(codes))
        w |= sum(int(sc16[2 * g]) << (4096 + 8 * g) for g in range(16))
        win_words.append(w)
    # selected compressed rows: ids (TOPK_MERGE output) + gathered rows
    sel, rows = [], {}
    if nsel:
        mg = find(meta, "TOPK_MERGE", "index merge")
        ids = vmf[mg["eff"]["O"][0]:mg["eff"]["O"][0] + nsel].astype(np.int64)
        assert np.all(np.diff(ids) > 0), "merged ids not strictly increasing (golden sel = sorted top-k)"
        sel = [int(g) for g in ids]
        for i, g in enumerate(sel):
            x = hbm.f32(CKV_SEL + i * stride, D)
            rows[g] = (x,) + fp4_codes_exact(x)
    decoys = sorted({g + dd for g in sel for dd in (-256, -1, 1, 256) if 0 <= g + dd < n} - set(sel))
    for i, g in enumerate(decoys):                               # present but wrong: another real row
        rows[g] = rows[sel[(i * 7 + 3) % len(sel)]]
    max_local = ((n - 1) >> 8 << 4) + 15
    base = [1_000_003 * (s + 1) for s in range(4)]
    count = [9 * (max_local + 1)] * 4
    hkey, hdat = [], []
    for g in sorted(rows):
        die, stack, local = G.owner(g)
        packed = G.pack_main_row([int(c) for c in rows[g][1]], [int(s) for s in rows[g][2]])
        for k in range(9):
            addr = base[stack] + 9 * local + k
            hkey.append((die << 32) | (stack << 30) | addr)
            hdat.append(int.from_bytes(packed[32 * k:32 * (k + 1)], "little"))
    fmt = np.array([0] * wcount + [1] * nsel, dtype=np.int64)
    codes = np.array(win_codes + [rows[g][1] for g in sel], dtype=np.int64).reshape(T, D)
    scales = np.array(win_scales + [rows[g][2] for g in sel], dtype=np.int64).reshape(T, D // 16)
    q1 = vf(qk["eff"]["A"][0], D)
    p1 = vf(bp["eff"]["O"][0], T)
    qb, pb = V.to_bf16(q1), V.to_bf16(p1)
    q_bf16_exact = bool(np.array_equal(V.bits(qb), V.bits(q1)))
    assert np.array_equal(V.bits(pb), V.bits(p1)), "p is not BF16 (attend.bf16_p output)"
    job = C.Job(np.tile(qb, (H, 1)), fmt, codes, scales, np.tile(p1, (H, 1)), f"s81lv {a.name} P1048575")
    golden_rows = np.stack(win_vals + [rows[g][0] for g in sel]).astype(F)
    assert np.array_equal(V.bits(job.kvm()), V.bits(golden_rows)), "stored-format rows differ from the exported rows"
    sc, pv = job.expected()
    exp_s, exp_pv = vf(qk["eff"]["O"][0], T), vf(pvr["eff"]["O"][0], D)
    s_exact = int(np.sum(V.bits(sc[0]) == V.bits(exp_s)))
    pv_exact = int(np.sum(V.bits(pv[0]) == V.bits(exp_pv)))
    a.out.mkdir(parents=True, exist_ok=True)
    counts, stats = C.write_jobs(a.out, [job], H, D, TD)
    C.write_hex(a.out / "sel.hex", sel or [0], 32)
    C.write_hex(a.out / "win.hex", win_words or [0], 4224)
    C.write_hex(a.out / "hkey.hex", hkey, 64)
    C.write_hex(a.out / "hdat.hex", hdat, 256)
    qc = G.quarters(n, sel)
    cfg = [wcount, nsel, n, len(hkey), T, *qc, *base, *count]
    C.write_hex(a.out / "cfg.hex", cfg + [0] * (32 - len(cfg)), 32)
    rec = dict(name=a.name, export=str(a.vec), export_vehicle=meta["vehicle"], layer=meta["layer"],
               position=meta["position"], rank=meta["rank"], token=meta["token"],
               export_sha256={f: sha(a.vec / f) for f in ("meta.json", "hbm.bin", "hbmw.bin", "vm_final.bin")},
               window_rows=wcount, compressed_rows=n, n_sel=nsel, T=T, quarter_counts=qc,
               owned_rows_per_die=[sum(1 for g in sel if G.owner(g)[0] == d) for d in range(4)],
               hbm_sectors=len(hkey), decoy_rows=len(decoys), q_bf16_exact=q_bf16_exact,
               golden_vs_export=dict(scores_bit_exact=f"{s_exact}/{T}", pv_bit_exact=f"{pv_exact}/{D}"),
               heads="rank 0's one head on all 16 head lanes", counts=counts, expected=stats,
               sources={s: sha(ROOT / s) for s in G.GOLDEN + ["tools/s81_lv/svc_1m_vectors.py"]},
               images={x.name: sha(x) for x in sorted(a.out.glob("*.hex"))})
    (a.out / "manifest.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("name", "T", "n_sel", "q_bf16_exact", "golden_vs_export", "owned_rows_per_die")}))


if __name__ == "__main__":
    main()
