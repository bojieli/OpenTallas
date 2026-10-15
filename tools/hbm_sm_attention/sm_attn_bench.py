#!/usr/bin/env python3
"""Attention on the SM engines (H-SM-ATT 2026-10-15): full-shape exact bench of ATT.QK / ATT.PV on the SM BF16 datapath.

Builds tb_hbm_sm_attn (ot_hbm_sm_kv_line -> ot_hbm_sm_attn_issue -> 4 x ot_hbm_sm_tcpv_col -> N4 combine tree) once per
mutant setting, then runs every SM's share of a whole attention record and compares every result bit for bit:
  QK  scores of the SM's rows        == tools/hgi_sim/lib.py att_qk(q, K)          (csum8 over the head dim)
  PV  the SM's run node (64 x 8 dims) == pairwise node over its aligned chunk run    (csum8 over positions)
      and the pairwise merge of all SM nodes (the cross-SM reduce, padded) == att_pv(p, V) over the whole record.
The KV rows are written in the SM-KV8 / SM-KV4 layouts (see rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv); the
dequantised values are the golden qdq values (tools/hdc_golden_v41.py qdq_fp8 / qdq_fp4_e4m3), checked bitwise.

  sm_attn_bench.py run --shape ds640|ds128 [--seed N] [--mut kv1|kv2|kv3|pv1|pv2] --work DIR --out R.json [--jobs N]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
from hgi_sim import lib as A  # noqa: E402

F = np.float32
NSM = 32
SRC = ["rtl/hdc/ot_hdc_prefix.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/gpu/ot_gpu_tree.sv",
       "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
       "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_issue.sv",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_tcpv_col.sv", "rtl/test/hbm_accel/sm_attn/tb_hbm_sm_attn.sv"]


def bits32(a):
    return np.asarray(a, dtype=F).view(np.uint32)


def zbits(a):
    """bits with zeros canonical (+0): the golden's qdq keeps -0 for a negative element that rounds to zero, but every
    product with it is canonical +0 (hdc_golden mul), so -0 and +0 KV elements are the same operand."""
    a = np.asarray(a, dtype=F)
    return bits32(np.where(a == 0, F(0), a))


def bf16b(a):
    return (bits32(V.to_bf16(a)) >> 16).astype(np.uint32)


# ---------------- encoders (exact inverses of the converter's decoders) ----------------
_E4M3_VAL = {}
for _c in range(256):
    if (_c & 0x7F) == 0x7F:
        continue
    _e, _m = (_c >> 3) & 15, _c & 7
    _v = (_m / 8.0) * 2.0 ** -6 if _e == 0 else (1 + _m / 8.0) * 2.0 ** (_e - 7)
    _v = -_v if _c & 0x80 else _v
    if _v == 0 and _c != 0:
        continue
    _E4M3_VAL.setdefault(_v, _c)
E2M1 = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]


def kv8_row(x):
    """-> (codes[512] uint8, ue8m0[16] uint8, deq[512] float32 == golden qdq_fp8(x))."""
    q, e = V.quant_fp8(x)
    codes = np.array([_E4M3_VAL[float(v)] if v != 0 else 0 for v in q], dtype=np.uint8)
    deq = V.qdq_fp8(x)
    ue = (np.asarray(e, dtype=np.int64) + 127).astype(np.uint8)
    chk = np.array([(_dec8(c) * 2.0 ** (int(ue[i // 32]) - 127)) for i, c in enumerate(codes)], dtype=np.float64)
    assert np.array_equal(zbits(V.to_bf16(chk.astype(F))), zbits(deq)), "KV8 encode != golden qdq_fp8"
    return codes, ue, deq


def _dec8(c):
    e, m = (int(c) >> 3) & 15, int(c) & 7
    v = (m / 8.0) * 2.0 ** -6 if e == 0 else (1 + m / 8.0) * 2.0 ** (e - 7)
    return -v if c & 0x80 else v


def kv4_row(x):
    """-> (codes[512] (sign<<3 | idx), scales[32] E4M3 codes, deq[512] == golden qdq_fp4_e4m3(x, 16))."""
    x = np.asarray(x, dtype=F)
    deq = V.qdq_fp4_e4m3(x, 16)
    xb = x.reshape(-1, 16)
    amax = np.maximum(np.max(np.abs(xb), axis=1), V.FP4_AMAX_FLOOR_E4M3).astype(F)
    s = np.minimum(V._e4m3_round(amax.astype(np.float64) / V.FP4_MAX), 448.0)
    scodes = np.array([_E4M3_VAL[float(v)] for v in s], dtype=np.uint8)
    a = np.abs(xb.astype(np.float64))
    code = np.zeros(a.shape, dtype=np.int64)
    for i, m in enumerate(V.E2M1_MIDPOINTS):
        t = m * s[:, None]
        code = np.where((a > t) | ((a == t) & ((i + 1) % 2 == 0)), i + 1, code)
    sign = (xb < 0) & (code > 0)
    codes = (code | (sign.astype(np.int64) << 3)).reshape(-1).astype(np.uint8)
    chk = np.array([(-1 if c & 8 else 1) * E2M1[c & 7] * _dec8(scodes[i // 16]) for i, c in enumerate(codes)])
    assert np.array_equal(zbits(V.to_bf16(chk.astype(F))), zbits(deq)), "KV4 encode != golden qdq_fp4_e4m3"
    return codes, scodes, deq


def canon_row(codes, scales, kv4):
    """Canonical packed row bytes: KV8 528 B (512 E4M3 codes in dim order + 16 UE8M0); KV4 288 B (256 B of E2M1 nibbles in
    dim order, dim 2i low / 2i+1 high, + 32 E4M3 scales)."""
    if kv4:
        c = np.asarray(codes, dtype=np.uint8)
        return bytes((c[0::2] & 15) | ((c[1::2] & 15) << 4)) + bytes(np.asarray(scales, dtype=np.uint8))
    return bytes(np.asarray(codes, dtype=np.uint8)) + bytes(np.asarray(scales, dtype=np.uint8))


def stream_lines(blob):
    """The contiguous row bytes as 136-B lines (bit 8i of a line = byte i), last line zero-padded."""
    blob = blob + bytes(-len(blob) % 136)
    return [int.from_bytes(blob[i:i + 136], "little") for i in range(0, len(blob), 136)]


# ---------------- record generation ----------------
def make_record(T_win, T_cmp, seed):
    rng = np.random.default_rng(seed)
    q = V.to_bf16(rng.standard_normal(512).astype(F) * F(0.6))
    rows8 = [kv8_row(rng.standard_normal(512).astype(F) * F(rng.choice([0.05, 1.0, 9.0]))) for _ in range(T_win)]
    rows4 = [kv4_row(rng.standard_normal(512).astype(F) * F(rng.choice([0.05, 1.0, 9.0]))) for _ in range(T_cmp)]
    K = np.stack([r[2] for r in rows8 + rows4]).astype(F)
    s = A.att_qk(q, K)
    e, Z, m = A.softmax_e_z(s, F(1.0 / np.sqrt(512.0)))
    p = V.to_bf16(e)
    return dict(q=q, rows8=rows8, rows4=rows4, K=K, s=s, p=p, pv=A.att_pv(p, K))


def chunk_sums(p, Vr):
    t = A.mul(np.asarray(p, dtype=F)[:, None], Vr)
    n = t.shape[0]
    nc = -(-n // 8)
    t = np.concatenate([t, np.zeros((nc * 8 - n, t.shape[1]), dtype=F)])
    acc = np.zeros((nc, t.shape[1]), dtype=F)
    for i in range(8):
        acc = A.add(acc, t[i::8][:nc])
    return acc


def plan(rec, shape):
    """Per-SM ops: (name, kind, kv4, rows list, nrun) -- QK splits each format evenly over the 32 SMs; PV gives each SM an
    aligned power-of-two run of chunks (single format: chunk 16 = row 128 is a run boundary)."""
    T8, T4 = len(rec["rows8"]), len(rec["rows4"])
    ops = []
    for s in range(NSM):
        a8, a4 = T8 // NSM, T4 // NSM        # one QK op a SM: its window rows (SM-KV8) then its top-k rows (SM-KV4)
        ops.append((f"qk_sm{s}", "qk", 0, list(range(a8 * s, a8 * s + a8)) + list(range(T8 + a4 * s, T8 + a4 * s + a4)), 0))
    T = T8 + T4
    nch = -(-T // 8)
    nrun = 1
    while -(-nch // nrun) > NSM:
        nrun *= 2
    for s in range(-(-nch // nrun)):
        r0, r1 = 8 * nrun * s, min(T, 8 * nrun * (s + 1))
        kv4 = 1 if r0 >= T8 else 0
        assert all((r >= T8) == bool(kv4) for r in range(r0, r1)), "PV run mixes formats"
        ops.append((f"pv_sm{s}", "pv", kv4, list(range(r0, r1)), nrun))
    return ops, nrun


def op_vectors(rec, op, d):
    name, kind, kv4, rows, nrun = op[:5]
    if rec.get("qwen"):
        return qwen_vectors(rec, op, d)
    T8 = len(rec["rows8"])
    blob = b""
    for r in rows:
        codes, sc, _ = rec["rows4"][r - T8] if r >= T8 else rec["rows8"][r]
        blob += canon_row(codes, sc, 1 if r >= T8 else 0)
    lines = stream_lines(blob)
    if kind == "qk":
        qb = bf16b(rec["q"])
        xs = [sum(int(qb[8 * j + t]) << (16 * j) for j in range(64)) for t in range(8)]
    else:
        pb = bf16b(rec["p"])
        xs = [int(pb[r]) for r in rows]
    return write_vec(d, name, lines, xs, 1)


def write_vec(d, name, lines, xs, ncol):
    lf, xf = d / f"{name}.lines.hex", d / f"{name}.x.hex"
    lf.write_text("".join(f"{w:0272x}\n" for w in lines))
    xf.write_text("".join(f"{w:0{256 * ncol}x}\n" for w in xs))
    return lf, xf, len(lines), len(xs)


# ---------------- Qwen3-8B TP4 on HBM: head dim 128, 2 KV heads x 4 q heads a die, T 8192, FP8 KV ----------------
QW_KVH, QW_G, QW_HD, QW_T = 2, 4, 128, 8192


def make_qwen(seed):
    """Qwen KV = plain FP8 E4M3 rows (tools/hgi_sim/qwen_compiler.py kv_append: fp8_encode, no scale): the STANDARD
    128-B row (r2; the r3..r6 runs used a 136-B one-row line with an UE8M0 byte)."""
    rng = np.random.default_rng(seed)
    codes = rng.integers(0, 256, size=(QW_KVH, 2, QW_T, QW_HD))
    codes = np.where((codes & 0x7F) == 0x7F, codes ^ 1, codes)              # no NaN codes
    tab = np.array([_dec8(c) for c in range(256)], dtype=np.float64)
    vals = tab[codes].astype(F)
    q = V.to_bf16(rng.standard_normal((QW_KVH, QW_G, QW_HD)).astype(F) * F(0.8))
    sc, p, pv = np.zeros((QW_KVH, QW_G, QW_T), F), np.zeros((QW_KVH, QW_G, QW_T), F), np.zeros((QW_KVH, QW_G, QW_HD), F)
    for h in range(QW_KVH):
        for c in range(QW_G):
            sc[h, c] = A.att_qk(q[h, c], vals[h, 0])
            e, Z, m = A.softmax_e_z(sc[h, c], F(1.0 / np.sqrt(QW_HD)))
            p[h, c] = V.to_bf16(e)
            pv[h, c] = A.att_pv(p[h, c], vals[h, 1])
    return dict(qwen=True, codes=codes, vals=vals, q=q, s=sc, p=p, pv=pv)


def qwen_block_home(k):
    """128-row block k -> (quadrant, SM in quadrant, slot): the SU softmax slice rule (position i lives in slice
    (i mod 512) // 128, H-ELEM-B 09:21) puts block k on quadrant k % 4; within the quadrant the 16 blocks go two to a SM
    (SM (k // 4) // 2, slot (k // 4) % 2).  Pairwise levels over the 64 block nodes are then: L1, L2 = the 4-quadrant
    reduce-scatter (quadrant bits), L3 = the SM's own two blocks, L4..L6 = SM index in the quadrant."""
    return k % 4, (k // 4) // 2, (k // 4) % 2


def qwen_stored(block):
    """Stored row order of a 128-row block in the SM's own stack: stored row 4k + u = token 32u + k (the DMA append
    address rotates POS[6:0] left by 2), so the PV converter reads the 4 token streams round-robin from a contiguous run."""
    base = 128 * block
    return [base + 32 * u + k for k in range(32) for u in range(4)]


def qwen_plan(rec):
    ops = []
    nb = QW_T // 128
    homes = {}
    for k in range(nb):
        q, j, sl = qwen_block_home(k)
        homes.setdefault(8 * q + j, []).append((sl, k))
    for h in range(QW_KVH):
        for sm in range(NSM):
            blocks = [k for _, k in sorted(homes[sm])]
            ops.append((f"qk_h{h}_sm{sm}", "qk", 0, sum((qwen_stored(k) for k in blocks), []), 0, h))
            for sl, k in sorted(homes[sm]):
                ops.append((f"pv_h{h}_sm{sm}_b{k}", "pv", 0, qwen_stored(k), 4, h, k))
    return ops, 4


def qwen_lines(codes, rows):
    """Standard 128-B rows (dim-order E4M3 codes) back to back in stored order -> 136-B lines."""
    return stream_lines(b"".join(bytes(np.asarray(codes[r], dtype=np.uint8)) for r in rows))


def qwen_vectors(rec, op, d):
    name, kind, _, rows, _, h = op[:6]
    if kind == "qk":
        lines = qwen_lines(rec["codes"][h, 0], rows)
        xs = []
        for t in range(8):
            w = 0
            for c in range(QW_G):
                qb = bf16b(rec["q"][h, c])
                for lane in range(64):
                    w |= int(qb[8 * (lane % 16) + t]) << (1024 * c + 16 * lane)
            xs.append(w)
    else:
        base, n = min(rows), len(rows)
        lines = qwen_lines(rec["codes"][h, 1], rows)       # stored order = the 4 token streams round-robin
        xs = []
        for i in range(n):
            w = 0
            for c in range(QW_G):
                w |= int(bf16b(rec["p"][h, c, base + i : base + i + 1])[0]) << (1024 * c)
            xs.append(w)
    return write_vec(d, name, lines, xs, QW_G)


def build(work, kvmut, pvmut, ncol=1, native=False):
    obj = work / f"obj_kv{kvmut}_pv{pvmut}_c{ncol}_n{int(native)}"
    exe = obj / "Vtb_hbm_sm_attn"
    if exe.exists():
        return exe
    vl = os.environ.get("VERILATOR") or next((c for c in (os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"),) if os.path.exists(c)), "verilator")
    cmd = [vl, "--binary", "-j", "16", "-O3", "--x-assign", "fast", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "128", "--top-module", "tb_hbm_sm_attn",
           f"-GKVMUT={kvmut}", f"-GPVMUT={pvmut}", f"-GNCOL={ncol}", f"-GNATIVE={int(native)}", "--Mdir", str(obj)] + [str(ROOT / s) for s in SRC]
    if native:
        cmd += ["-DOT_SMH_HIER", str(ROOT / "rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv"),
                str(ROOT / "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv"),
                str(ROOT / "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_native_col.sv")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_kv{kvmut}_pv{pvmut}.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_kv{kvmut}_pv{pvmut}.log)")
    return exe


def parse(out, pb=None):
    sc, pvl = {}, []
    for ln in out.splitlines():
        if pb is not None and ln.startswith("PB "):
            _, c, q, sl, wd, hx = ln.split()
            pb.append((int(c), int(q), int(sl), int(wd), int(hx, 16)))
        if ln.startswith("SC "):
            _, c, i, hx = ln.split()
            sc[(int(c), int(i))] = int(hx, 16)
        elif ln.startswith("PV "):
            _, c, b, k, hx = ln.split()
            pvl.append((int(c), int(b), int(k), int(hx, 16)))
    return sc, pvl


def run_op(exe, rec, op, d):
    name, kind, kv4, rows, nrun = op[:5]
    qw = bool(rec.get("qwen"))
    ncol = QW_G if qw else 1
    lf, xf, nl, nx = op_vectors(rec, op, d)
    want = len(rows) * ncol if kind == "qk" else 8 * ncol
    args = [str(exe), f"+LINES={lf}", f"+X={xf}", f"+NL={nl}", f"+NX={nx}", f"+ROWS={len(rows)}",
            f"+QK={1 if kind == 'qk' else 0}", f"+KV4={kv4}", f"+H128={1 if qw else 0}", f"+WANT={want}"]
    if not qw:
        args.append(f"+N8={sum(1 for r in rows if r < len(rec['rows8']))}")
    elif kind == "pv":
        args.append("+FOLD=1")
    r = subprocess.run(args, capture_output=True, text=True, timeout=3600)
    out = r.stdout + r.stderr
    (d / f"{name}.log").write_text(out)
    res = dict(name=name, kind=kind, kv4=kv4, rows=len(rows), rc=r.returncode, fault="FAULT" in out)
    cyc = [ln for ln in out.splitlines() if ln.startswith("CYCLES")]
    if cyc:
        kv = dict(t.split("=") for t in cyc[0].split()[1:])
        res["cycles"] = {k: int(v) for k, v in kv.items()}
    fl = [ln for ln in out.splitlines() if ln.startswith("FOLD ")]
    if fl:
        kv = dict(t.split("=") for t in fl[0].split()[1:])
        res["fold_cycles"] = {k: int(v) for k, v in kv.items()}
    pb = []
    sc, pvl = parse(out, pb)
    mism, nodes = 0, None
    if kind == "qk":
        for c in range(ncol):
            want_s = bits32(rec["s"][op[5], c][rows]) if qw else bits32(rec["s"][rows])
            for i in range(len(rows)):
                if sc.get((c, i)) != int(want_s[i]):
                    mism += 1
        res.update(results=len(sc), expected=len(rows) * ncol)
    elif not qw:
        cs = chunk_sums(rec["p"][rows], rec["K"][rows])
        node = A.pairwise([cs[i] for i in range(cs.shape[0])] + [np.zeros_like(cs[0])] * (nrun - cs.shape[0]))
        got = np.full(512, -1, dtype=np.int64)
        for c, b, k, v in pvl:
            for l in range(16):
                got[8 * (16 * k + l) + b] = (v >> (32 * l)) & 0xFFFFFFFF
        mism = int(np.sum(got != bits32(node).astype(np.int64)))
        nodes = got.astype(np.uint32).view(F).tolist() if mism == 0 else None
        res.update(results=int(np.sum(got >= 0)), expected=512)
    else:
        # r2: the 4 stream nodes are folded inside the SM ((s0+s1)+(s2+s3), ot_hbm_sm_pv_merge FOLD) and only entries 0 / 1
        # (dim halves) are published: leaf k word l of entry h = dim 8 l + 4 h + k of the block's node, a q head a column
        h, base = op[5], min(rows)
        got = np.full((ncol, QW_HD), -1, dtype=np.int64)
        extra = 0
        for c, k, sl, wd, v in pb:
            if sl > 1 or got[c, 8 * wd + 4 * sl + k] >= 0:
                extra += 1
            else:
                got[c, 8 * wd + 4 * sl + k] = v
        want_n = np.zeros((ncol, QW_HD), dtype=np.int64)
        for c in range(ncol):
            tk = list(range(base, base + 128))
            cs = chunk_sums(rec["p"][h, c][tk], rec["vals"][h, 1][tk])
            want_n[c] = bits32(A.pairwise([cs[i] for i in range(cs.shape[0])])).astype(np.int64)
        mism = int(np.sum(got != want_n)) + extra
        nodes = got.astype(np.uint32).view(F).tolist() if mism == 0 else None
        res.update(results=int(np.sum(got >= 0)), expected=ncol * QW_HD, published_words=len(pb))
    res["node"] = nodes
    res["mismatches"] = mism
    res["pass"] = r.returncode == 0 and not res["fault"] and mism == 0 and res["results"] == res["expected"]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--shape", choices=["ds640", "ds128", "qwen8192"], default="ds640")
    p.add_argument("--native-column", action="store_true", help="reuse actual hardened tcl/tct arithmetic with the separate PV merge leaf")
    p.add_argument("--seed", type=int, default=1015)
    p.add_argument("--mut", default="")
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--jobs", type=int, default=16)
    p.add_argument("--only", default="", help="comma list of op name prefixes (mutant runs)")
    a = ap.parse_args(argv)
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.shape == "qwen8192":
        T8, T4 = 0, 0
        rec = make_qwen(a.seed)
        ops, nrun = qwen_plan(rec)
    else:
        T8, T4 = (128, 512) if a.shape == "ds640" else (128, 0)
        rec = make_record(T8, T4, a.seed)
        ops, nrun = plan(rec, a.shape)
    if a.only:
        ops = [o for o in ops if any(o[0].startswith(x) for x in a.only.split(","))]
    if not ops:
        ap.error("--only matched no operations; an empty run cannot qualify a component")
    kvm = int(a.mut[2:]) if a.mut.startswith("kv") else 0
    pvm = int(a.mut[2:]) if a.mut.startswith("pv") else 0
    exe = build(work, kvm, pvm, QW_G if a.shape == "qwen8192" else 1, a.native_column)
    vec = work / f"vec_{a.shape}_{a.mut or 'm0'}"
    vec.mkdir(exist_ok=True)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda o: run_op(exe, rec, o, vec), ops))
    summary = dict(shape=a.shape, native_column=a.native_column, seed=a.seed, mut=a.mut or None, T_window=T8, T_compressed=T4, pv_run_chunks=nrun,
                   ops=len(res), passed=sum(r["pass"] for r in res), wall_s=round(time.time() - t0, 1))
    pv = [r for r in res if r["kind"] == "pv"]
    if pv and all(r["pass"] for r in pv) and not a.only:
        if a.shape == "qwen8192":
            # cross-SM reduce in the COLL order: block nodes sorted by block index k (bits: quadrant, quadrant, slot, SM x3)
            # == pairwise levels L1-L2 4-quadrant reduce-scatter, L3 in-SM pair, L4-L6 SM index in the quadrant
            ok = True
            for h in range(QW_KVH):
                blk = sorted((o[6], r) for o, r in zip([o for o in ops if o[1] == "pv"], pv) if o[5] == h)
                assert [k for k, _ in blk] == list(range(QW_T // 128))
                for c in range(QW_G):
                    nodes = [np.asarray(r["node"], dtype=F)[c] for _, r in blk]
                    ok &= bool(np.array_equal(bits32(A.pairwise(nodes)), bits32(rec["pv"][h, c])))
            summary["pv_cross_sm_merge_equals_att_pv"] = ok
            summary["qwen_placement"] = "block k -> quadrant k%4, SM (k//4)//2, slot (k//4)%2; stored rows rotated (4k+u = token 32u+k)"
        else:
            nodes = [np.asarray(r["node"], dtype=F) for r in pv]
            summary["pv_cross_sm_merge_equals_att_pv"] = bool(np.array_equal(bits32(A.pairwise(nodes)), bits32(rec["pv"])))
    if not a.only:
        summary["qk_scores_checked"] = sum(r["results"] for r in res if r["kind"] == "qk" and r["pass"])
    for kind in ("qk", "pv"):
        cy = [r["cycles"] for r in res if r["kind"] == kind and "cycles" in r]
        if cy:
            summary[f"{kind}_span_max"] = max(c["span"] for c in cy)
            summary[f"{kind}_lines_max"] = max(c["lines"] for c in cy)
    summary["verdict"] = "PASS" if summary["passed"] == len(res) and summary.get("pv_cross_sm_merge_equals_att_pv", True) else "FAIL"
    for r in res:
        r.pop("node", None)
    Path(a.out).write_text(json.dumps(dict(summary=summary, ops=res), indent=1))
    print(("PASS" if summary["verdict"] == "PASS" else "FAIL") + " HBM_SM_ATTENTION " + json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
