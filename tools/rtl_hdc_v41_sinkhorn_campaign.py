#!/usr/bin/env python3
"""RTL campaign for the V4.1 decode core's hyper-connection SINKHORN unit
(rtl/hdc/v41/ot_hdc_sinkhorn.sv and its arithmetic, ot_hdc_sk_arith.sv).

Every expected output comes from tools/hdc_golden_v41.py:

* the unit's function is the tail of `Model.hc_mixes` after the exponential --
  row softmax normalisation + eps, then columns, then (iters - 1) x (rows,
  columns), every sum `seqsum` (sequential, index order), every operation
  `add` / `div` (binary32 RNE, canonical +0).  `sinkhorn_reference` below is
  that code, vectorised over cases; on the real data it must reproduce the
  golden's own `hc_mixes` output bit for bit, so the vectors are the model's;
* REAL data: the golden decodes the oracle workload's prompt and generated
  tokens (then continues greedily); every sublayer's e = exp(comb - rowmax)
  and the golden's resulting comb are captured (2 per layer per position);
* RANDOM Sinkhorns (softmax-shaped, wide-range raw patterns, subnormal,
  tiny-with-one, eps-dominated, tie-rich few-bit significands, zeros and -0,
  near-overflow rows, and fail-closed cases: NaN, +/-Inf, negative, zero row,
  overflowing row);
* ARITHMETIC alone (tb_hdc_sk_arith, one operation per clock): millions of
  positive adds (also in the chained form, the running sum's exponent
  arriving as a late increment), general divides (subnormal operands and
  results, exact ties) and steady-step divides, against hdc_golden add / div,
  plus DIRECTED divides at the two corners of the multiply-and-check proof
  (quotients just below an integer where an unbiased seed would overshoot,
  just above a midpoint where the seed undershoots most), found by searching
  with the integer model of tools/gen_hdc_sinkhorn_recip_rom.py.

The whole unit runs under Verilator 4.038 in parallel shards (back to back
and with idle gaps / early presentation), a slice under Icarus; the output
latency must equal 2 ITERS + 1 clock edges on every case.  A mutation check
applies single deliberate defects to copies of the RTL and requires the
checkers to reject every one, except mutants recorded as EQUIVALENT with the
reason (a margin of the design that the data cannot reach, or a true
equivalence), which are run and reported but not counted.  tools/gen_hdc_sinkhorn_recip_rom.py --check
(the seed's exhaustive one-sided bound and the integer model) runs too.
Writes results/rtl/hdc_v41_sinkhorn_campaign.json with the sha256 of every input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_hdc_sinkhorn_recip_rom as GEN  # noqa: E402
import hdc_golden_v41 as G  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_sinkhorn_campaign.json"
TOP = ROOT / "rtl/hdc/v41/ot_hdc_sinkhorn.sv"
ARITH = ROOT / "rtl/hdc/v41/ot_hdc_sk_arith.sv"
ROM = ROOT / "rtl/hdc/v41/ot_hdc_sk_recip_rom.sv"
TB = ROOT / "rtl/test/tb_hdc_sinkhorn.sv"
HARNESS = ROOT / "rtl/test/hdc_sinkhorn_harness.cpp"
RTL = [TOP, ARITH, ROM]
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py", ROOT / "tools/gen_hdc_sinkhorn_recip_rom.py",
         Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED")
UNIT_LINE = re.compile(r"SINKHORN ITERS=(\d+) cases=(\d+) outputs=(\d+) errors=(\d+) word_errors=(\d+) faults=(\d+) "
                       r"lat_min=(-?\d+) lat_max=(-?\d+) lat_expect=(\d+) cycles=(\d+)")
ARITH_LINE = re.compile(r"SKARITH ops=(\d+) add=(\d+) div=(\d+) div_steady=(\d+) add_chained=(\d+) errors=(\d+)")
F = np.float32
EPS = F(1e-6)
ITERS = 20
REAL_POSITIONS = 48


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def b32(v):
    return np.asarray(v, np.float32).view(np.uint32).astype(np.int64)


def f32(b):
    return np.asarray(b, np.int64).astype(np.uint32).view(np.float32)


# -- the golden's Sinkhorn, vectorised over cases ------------------------------------------------
def sinkhorn_reference(e, iters=ITERS, eps=EPS):
    """e: [n, 4, 4] binary32 (exp(comb - rowmax)).  Returns (comb [n, 4, 4], fault [n]) with the
    golden's arithmetic; `fault` is the unit's fail-closed contract: an input that is negative
    (nonzero) or nonfinite, or any sum / quotient that is not a finite number, or a zero row sum."""
    e = np.asarray(e, F)
    bits = b32(e)
    bad = (((bits >> 31) & 1) == 1) & ((bits & 0x7FFFFFFF) != 0)
    bad |= ((bits >> 23) & 0xFF) == 0xFF
    bad = bad.reshape(len(e), -1).any(axis=1)
    e = np.where(((bits & 0x7FFFFFFF) == 0).reshape(e.shape), F(0), e).astype(F)   # -0 reads as +0
    h = e.shape[1]
    with np.errstate(all="ignore"):
        rs = G.seqsum([e[:, :, k] for k in range(h)])
        bad |= (~np.isfinite(rs) | (rs == 0)).any(axis=1)
        comb = G.add(G.div(e, rs[:, :, None]), eps)

        def cols(cm):
            cs = G.add(G.seqsum([cm[:, j, :] for j in range(h)]), eps)
            return G.div(cm, cs[:, None, :]), ~np.isfinite(cs).all(axis=1)

        def rows(cm):
            rs_ = G.add(G.seqsum([cm[:, :, k] for k in range(h)]), eps)
            return G.div(cm, rs_[:, :, None]), ~np.isfinite(rs_).all(axis=1)

        comb, b = cols(comb)
        bad |= b
        for _ in range(iters - 1):
            comb, b1 = rows(comb)
            comb, b2 = cols(comb)
            bad |= b1 | b2
        bad |= ~np.isfinite(comb).reshape(len(e), -1).all(axis=1)
    comb = np.where(bad[:, None, None], F(0), comb).astype(F)
    return comb, bad


# -- real reduced-model data -----------------------------------------------------------------------
def real_cases(positions):
    """Stream the golden decode and capture every sublayer's Sinkhorn input e and output comb."""
    model = G.Model()
    caps = []
    orig = G.Model.hc_mixes

    def hooked(self, x, L, which):
        pre, post, comb = orig(self, x, L, which)
        fn, scale, base = (self.lw(L, f"hc_{which}_{s}") for s in ("fn", "scale", "base"))
        flat = x.reshape(-1)
        r = G.rsqrt(G.add(G.div(G.reduce_rows(G.mul(flat, flat)[None, :])[0], F(flat.size)), self.eps))
        mixes = G.mul(G.matvec_fp32(fn, flat), r)
        hc = self.hc
        cm = G.add(G.mul(mixes[2 * hc:], scale[2]), base[2 * hc:]).reshape(hc, hc)
        m = np.max(cm, axis=1, keepdims=True)
        e = G.exp(G.add(cm, G.neg(m)))
        caps.append((np.asarray(e, F), np.asarray(comb, F), L, which))
        return pre, post, comb

    G.Model.hc_mixes = hooked
    try:
        prompt, gen = G.prompt_and_expected()
        state = model.new_state()
        seq = list(prompt) + list(gen)
        for p in range(positions):
            logits = model.decode_token(seq[p], p, state)
            if p + 1 >= len(seq):
                seq.append(int(np.argmax(logits)))
    finally:
        G.Model.hc_mixes = orig
    e = np.stack([c[0] for c in caps])
    golden = np.stack([c[1] for c in caps])
    ref, bad = sinkhorn_reference(e, model.sinkhorn_iters, model.hc_eps)
    assert not bad.any(), "a real Sinkhorn faulted"
    assert np.array_equal(b32(ref), b32(golden)), "vectorised reference differs from the golden's hc_mixes"
    meta = {"positions": positions, "tokens": seq[:positions + 1], "sublayers_per_position": 2 * model.L,
            "sinkhorn_iters": model.sinkhorn_iters, "hc_eps_bits": hex(int(b32(model.hc_eps))),
            "cases": int(len(e)), "reference_equals_golden_hc_mixes": True}
    return e, meta


# -- random Sinkhorns ------------------------------------------------------------------------------
def random_cases(rng, n):
    """n random e matrices across the classes below; returns (e [n,4,4] as bit patterns, class labels)."""
    classes = ["softmax", "unit", "raw", "subnormal", "tiny_with_one", "eps_dominated", "ties", "zeros",
               "near_overflow", "faults"]
    weights = np.array([30, 10, 10, 6, 10, 10, 10, 6, 3, 5], float)
    lab = rng.choice(len(classes), n, p=weights / weights.sum())
    out = np.zeros((n, 16), np.int64)
    for ci, name in enumerate(classes):
        idx = np.nonzero(lab == ci)[0]
        k = len(idx)
        if k == 0:
            continue
        if name == "softmax":
            sig = rng.choice([0.05, 0.5, 2.0, 8.0, 40.0], k)[:, None, None]
            comb = (rng.standard_normal((k, 4, 4)) * sig).astype(F)
            m = np.max(comb, axis=2, keepdims=True)
            v = G.exp(G.add(comb, G.neg(m)))
            out[idx] = b32(v).reshape(k, 16)
        elif name == "unit":
            v = rng.random((k, 16), dtype=np.float32)
            out[idx] = b32(v)
        elif name == "raw":                               # any positive finite pattern, rows scaled apart
            e = rng.integers(1, 255, (k, 16))
            base = rng.integers(0, 200, (k, 1))
            e = np.clip(base + (e % 40), 0, 254)
            out[idx] = (e << 23) | rng.integers(0, 1 << 23, (k, 16))
        elif name == "subnormal":
            out[idx] = rng.integers(0, 1 << 23, (k, 16)) >> rng.integers(0, 22, (k, 16))
            out[idx, rng.integers(0, 16, k)] |= 1         # no all-zero case
        elif name == "tiny_with_one":
            e = rng.integers(0, 110, (k, 16))
            out[idx] = (e << 23) | rng.integers(0, 1 << 23, (k, 16))
            for r in range(4):
                out[idx, 4 * r + rng.integers(0, 4, k)] = 0x3F800000
        elif name == "eps_dominated":
            v = (rng.random((k, 16)) * 10.0 ** rng.uniform(-9, -4, (k, 1))).astype(F)
            out[idx] = b32(v)
        elif name == "ties":                              # few significand bits, nearby exponents
            e = 127 + rng.integers(-6, 3, (k, 1)) + rng.integers(-3, 4, (k, 16))
            mbits = rng.integers(0, 8, (k, 16)) << rng.integers(18, 23, (k, 16))
            out[idx] = (e << 23) | (mbits & 0x7FFFFF)
        elif name == "zeros":
            v = b32(rng.random((k, 16), dtype=np.float32))
            z = rng.random((k, 16)) < 0.4
            v = np.where(z, np.where(rng.random((k, 16)) < 0.5, 0, 0x80000000), v)
            for r in range(4):                            # keep every row nonzero
                v[np.arange(k), 4 * r] = np.where(v[np.arange(k), 4 * r] & 0x7FFFFFFF == 0, 0x3F000000,
                                                  v[np.arange(k), 4 * r])
            out[idx] = v
        elif name == "near_overflow":
            e = 252 + rng.integers(0, 3, (k, 16))
            out[idx] = (e << 23) | rng.integers(0, 1 << 23, (k, 16))
        elif name == "faults":
            v = b32(rng.random((k, 16), dtype=np.float32))
            kind = rng.integers(0, 6, k)
            pos = rng.integers(0, 16, k)
            special = np.array([0x7FC00000, 0x7F800000, 0xFF800000, 0xBF800000, 0x80000001, 0x7F800001])
            v[np.arange(k), pos] = special[kind]
            zr = rng.random(k) < 0.25                     # a zero row instead
            row = rng.integers(0, 4, k)
            for c in range(4):
                v[np.nonzero(zr)[0], 4 * row[zr] + c] = 0
            out[idx] = v
    return out.reshape(n, 4, 4), [classes[i] for i in lab]


# -- arithmetic operands -----------------------------------------------------------------------------
def arith_operands(rng, kind, size):
    if kind == "raw":
        return rng.integers(0, 0x7F800000, size)
    if kind == "subnormal":
        return rng.integers(0, 0x00800000, size) >> rng.integers(0, 23, size)
    if kind == "near":
        e = rng.integers(100, 140, size)
        return (e << 23) | rng.integers(0, 1 << 23, size)
    if kind == "unit":
        return b32(rng.random(size, dtype=np.float32) * F(1.5))
    if kind == "sparse":
        e = rng.integers(1, 254, size)
        m = rng.integers(0, 16, size) << rng.integers(0, 20, size)
        return (e << 23) | (m & 0x7FFFFF)
    if kind == "eps":
        return np.where(rng.random(size) < 0.5, int(b32(EPS)),
                        b32((rng.random(size) * 10.0 ** rng.uniform(-9, -3, size)).astype(F)))
    if kind == "top":
        e = rng.integers(240, 255, size)
        return (e << 23) | rng.integers(0, 1 << 23, size)
    raise ValueError(kind)


KINDS = ("raw", "subnormal", "near", "unit", "sparse", "eps", "top")


def arith_vectors(rng, per_pair):
    """Lines "<op> a b expected flag" for tb_hdc_sk_arith, with counts per op."""
    lines, counts = [], {"add": 0, "div": 0, "div_steady": 0, "add_chained": 0}
    for ka in KINDS:
        for kb in KINDS:
            a, b = arith_operands(rng, ka, per_pair), arith_operands(rng, kb, per_pair)
            with np.errstate(all="ignore"):
                s = G.add(f32(a), f32(b))
            fl = ~np.isfinite(s)
            ex = np.where(fl, 0, b32(s))
            lines += [f"0 {x:x} {y:x} {z:x} {int(f)}\n" for x, y, z, f in zip(a, b, ex, fl)]
            counts["add"] += per_pair
            # the chained form of the same add (a's exponent as field - 1 plus a late increment)
            ch = ((a >> 23) & 0xFF) >= 2
            lines += [f"3 {x:x} {y:x} {z:x} {int(f)}\n" for x, y, z, f, c in zip(a, b, ex, fl, ch) if c]
            counts["add_chained"] += int(ch.sum())
            b = np.where((b & 0x7FFFFFFF) == 0, 1, b)
            with np.errstate(all="ignore"):
                q = G.div(f32(a), f32(b))
            fl = ~np.isfinite(q)
            ex = np.where(fl, 0, b32(q))
            lines += [f"1 {x:x} {y:x} {z:x} {int(f)}\n" for x, y, z, f in zip(a, b, ex, fl)]
            counts["div"] += per_pair
            # steady divide: normal operands; flag = the quotient is not normal (or sits at the bottom binade)
            an = np.where((a >> 23) == 0, a | (1 << 23), a)
            bn = np.where((b >> 23) == 0, b | (1 << 23), b)
            with np.errstate(all="ignore"):
                q = G.div(f32(an), f32(bn))
            qb = b32(q)
            fld = (qb >> 23) & 0xFF
            keep = fld != 1                                    # the bottom binade is ambiguous by design
            fl = (fld == 0) | (fld == 255)
            ex = np.where(fl, 0, qb)
            lines += [f"2 {x:x} {y:x} {z:x} {int(f)}\n"
                      for x, y, z, f, kp in zip(an, bn, ex, fl, keep) if kp]
            counts["div_steady"] += int(keep.sum())
    return lines, counts


def edge_arith_lines():
    """Hand-picked operands: exact ties, carries into the next binade, max finite, min subnormal."""
    pairs = [(0x3F800000, 0x33800000), (0x3F800000, 0x33800001), (0x3F800001, 0x33800000), (0x3FFFFFFF, 0x34000000),
             (0x7F7FFFFF, 0x7F7FFFFF), (0x7F7FFFFF, 0x73000000), (0x00000001, 0x00000001), (0x007FFFFF, 0x00000001),
             (0x00000000, 0x00000000), (0x00000000, 0x3F800000), (0x358637BD, 0x3F800000), (0x3F800000, 0x358637BD),
             (0x00800000, 0x3F800000), (0x00000001, 0x7F7FFFFF), (0x3F800000, 0x7F7FFFFF), (0x00400000, 0x40000000),
             (0x00000003, 0x40000000), (0x00000001, 0x40000000), (0x00000001, 0x3F000000), (0x7F7FFFFF, 0x00000001),
             (0x3F7FFFFF, 0x3F800000), (0x3F800000, 0x3F7FFFFF), (0x40400000, 0x3FC00000), (0x3EAAAAAB, 0x3F800000)]
    lines = []
    for a, b in pairs:
        with np.errstate(all="ignore"):
            s = G.add(f32([a]), f32([b]))[0]
            q = G.div(f32([a]), f32([b if b else 1]))[0]
        lines.append(f"0 {a:x} {b:x} {0 if not np.isfinite(s) else int(b32(s)):x} {int(not np.isfinite(s))}\n")
        lines.append(f"1 {a:x} {b:x} {0 if not np.isfinite(q) else int(b32(q)):x} {int(not np.isfinite(q))}\n")
    return lines


def directed_arith_lines(rng, n, keep):
    """Divides at the corners of the multiply-and-check proof (GEN.directed_quotients): every pair that
    separates a defective variant, plus `keep` near-boundary pairs per class, as op 1 and op 2 lines."""
    hits, cand, tried = GEN.directed_quotients(rng, n)
    lines = []
    sim = {}
    for cls in cand:
        x = np.concatenate([hits[cls][0], cand[cls][0][:keep]])
        t = np.concatenate([hits[cls][1], cand[cls][1][:keep]])
        with np.errstate(all="ignore"):
            q = b32(G.div(f32(x), f32(t)))
        for op in (1, 2):
            lines += [f"{op} {a:x} {b:x} {c:x} 0\n" for a, b, c in zip(x, t, q)]
        sim[cls] = int(len(x))
    rec = {"classes": {c: {"pairs_tried": tried[c], "pairs_separating_the_defective_variant": int(len(hits[c][0])),
                           "pairs_simulated": sim[c]} for c in cand},
           "note": "seed_overshoot: q' just below an integer over significands where an unbiased seed exceeds 1/T; "
                   "second_threshold: q' just above a midpoint over the seed's deepest undershoots with X' near 4"}
    return lines, rec


# -- simulation ----------------------------------------------------------------------------------------
def write_unit_vectors(path: Path, e_bits, iters=ITERS):
    e_bits = np.asarray(e_bits, np.int64).reshape(len(e_bits), 16)
    ref, bad = sinkhorn_reference(f32(e_bits).reshape(-1, 4, 4), iters)
    rb = b32(ref).reshape(len(e_bits), 16)
    with path.open("w") as fh:
        for i in range(len(e_bits)):
            fh.write(" ".join(f"{int(x):x}" for x in e_bits[i]) + "  " +
                     " ".join(f"{int(x):x}" for x in rb[i]) + f"  {int(bad[i])}\n")
    return int(bad.sum())


def build_verilator(obj: Path, top: str, sources, iters=ITERS, arith=False):
    cmd = ["verilator", "--cc", "--exe", "--build", "-O3", "-Wno-fatal", "--top-module", top,
           "-Mdir", str(obj), *map(str, sources), str(TB), str(HARNESS), "-CFLAGS", "-O1"]
    if not arith:
        cmd[6:6] = [f"-GITERS={iters}"]
    else:
        cmd += ["-CFLAGS", "-DSK_ARITH"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)[-3000:], cmd


def parse_unit(out):
    m = UNIT_LINE.search(out)
    if not m:
        return {"pass": False, "log": out[-2000:]}
    it, cases, outs, err, werr, flt, lmin, lmax, lexp, cyc = map(int, m.groups())
    return {"cases": cases, "outputs": outs, "errors": err, "word_errors": werr, "faults": flt, "latency_min": lmin,
            "latency_max": lmax, "latency_expected": lexp, "cycles": cyc,
            "pass": "PASS" in out and err == 0 and lmin == lexp and lmax == lexp}


def parse_arith(out):
    m = ARITH_LINE.search(out)
    if not m:
        return {"pass": False, "log": out[-2000:]}
    ops, na, nd, ns, nc, err = map(int, m.groups())
    return {"ops": ops, "add": na, "div": nd, "div_steady": ns, "add_chained": nc, "errors": err,
            "pass": "PASS" in out and err == 0}


def run_unit(exe: Path, vec: Path, gap=0, early=0, seed=1):
    t = time.time()
    out = subprocess.run([str(exe), f"+IN={vec}", f"+GAP={gap}", f"+EARLY={early}", f"+SEED={seed}"],
                         capture_output=True, text=True).stdout
    rec = parse_unit(out)
    rec.update({"gap_percent": gap, "early_percent": early, "seed": seed, "seconds": round(time.time() - t, 1)})
    return rec


def run_icarus(s: Path, real_vec: Path, lines, n_cases, n_arith):
    """The first real cases through the whole unit and the first arithmetic lines (the hand-picked edge pairs
    lead) under Icarus Verilog."""
    out = {}
    iv = s / "icarus_real.vec"
    iv.write_text("".join(real_vec.read_text().splitlines(keepends=True)[:n_cases]))
    vvp = s / "unit.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_sinkhorn", "-o", str(vvp), str(TB), *map(str, RTL)],
                   check=True, capture_output=True)
    t = time.time()
    rec = parse_unit(subprocess.run(["vvp", "-n", str(vvp), f"+IN={iv}", "+GAP=30", "+EARLY=50", "+SEED=3"],
                                    capture_output=True, text=True).stdout)
    rec["seconds"] = round(time.time() - t)
    out["unit_real_slice"] = rec
    ia = s / "icarus_arith.vec"
    ia.write_text("".join(lines[:n_arith]))
    avvp = s / "arith.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_sk_arith", "-o", str(avvp), str(TB), *map(str, RTL)],
                   check=True, capture_output=True)
    t = time.time()
    rec = parse_arith(subprocess.run(["vvp", "-n", str(avvp), f"+IN={ia}"], capture_output=True, text=True).stdout)
    rec["seconds"] = round(time.time() - t)
    out["arith_slice"] = rec
    return out


# -- mutations --------------------------------------------------------------------------------------------
MUTATIONS = (
    {"id": "add_round_drops_sticky", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "no-carry round-up ignores the sticky bit (round-half-even applied to every half-ulp-or-more)",
     "before": "wire rnc = g & (st | s0[0]);", "after": "wire rnc = g & s0[0];"},
    {"id": "add_carry_round_ignores_shifted_out", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "carry-case round-up ignores the shifted-out bits",
     "before": "wire rc  = s0[0] & (any | s0[1]);", "after": "wire rc  = s0[0] & s0[1];"},
    {"id": "add_overflow_unflagged", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "an exponent reaching 255 no longer fails closed",
     "before": "assign ovf = up & (eg1[7:0] == 8'hFF);", "after": "assign ovf = 1'b0;"},
    {"id": "seed_bias_removed", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "drop the one-unit bias: the seed may exceed 1/T and M' may be M + 1",
     "before": "assign rows[30*W +: W] = 48'd14 - 48'd262144;", "after": "assign rows[30*W +: W] = 48'd14;",
     "equivalent": "a margin, not load-bearing here: without the bias the seed exceeds 1/T by under one unit of 2^-28 on some significands, but the truncated X*R product (columns below 2^20 dropped) lowers M' by more than that overshoot lifts it; the directed search (seed_overshoot) found no operand pair where the unbiased seed changes a quotient"},
    {"id": "seed_c2_term_dropped", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "the seed loses its quadratic term: R overshoots 1/T by up to 2^-20",
     "before": "ot_hdc_sk_sq_rom u_sq (.dmh(dm[12:4]), .sq(sq));", "after": "assign sq = 14'd0;"},
    {"id": "quot_single_threshold", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "ignore the second remainder: never M' + 2",
     "before": "wire [24:0] mf = inc2 ? mplus2 : (inc1 ? mplus1 : {1'b0, ms});",
     "after": "wire [24:0] mf = inc1 ? mplus1 : {1'b0, ms};",
     "equivalent": "a margin, not load-bearing here: M' + 2 needs the seed's undershoot to push M' a unit low while the quotient's fraction exceeds 1/2, i.e. an undershoot above 1/2 unit of M'; the exhaustive seed bound (max 2.72 x 2^-28) plus the truncation allow at most 0.53, and the directed search (second_threshold) found no pair that reaches it -- the second remainder is kept so the proof needs only the 2^-26 window"},
    {"id": "quot_midpoint_at_candidate", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "the first remainder tests q' against M' instead of M' + 1/2 (drops the -T row)",
     "before": "assign rows[25*W +: W] = ~{3'b000, tm};", "after": "assign rows[25*W +: W] = {W{1'b1}};"},
    {"id": "quot_ties_never_up", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "an exact tie (only reachable on a subnormal grid) never rounds to the odd side",
     "before": "wire inc1 = (!neg1 & !z1) | (z1 & ms[0]);", "after": "wire inc1 = (!neg1 & !z1);"},
    {"id": "quot_truncation_too_deep", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "truncate the X*R array below column 27 instead of 20: M' can fall two units short",
     "before": ".DROP(20)) u_xr", "after": ".DROP(27)) u_xr"},
    {"id": "quot_subnormal_grid_off_by_one", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "subnormal results rounded on the wrong grid",
     "before": "wire signed [10:0] sfull = -11'sd126 - E;", "after": "wire signed [10:0] sfull = -11'sd125 - E;"},
    {"id": "steady_eps_dropped", "source": "rtl/hdc/v41/ot_hdc_sinkhorn.sv",
     "description": "the steady step divides by the bare sum (no + eps)",
     "before": "ot_hdc_sk_add u_ae (.ea(g3), .ua(u3), .ma(m3), .eb(EPS_E), .mb(EPS_M),",
     "after": "ot_hdc_sk_add u_ae (.ea(g3), .ua(u3), .ma(m3), .eb(8'd1), .mb(24'd0),"},
    {"id": "steady_sum_order_swapped", "source": "rtl/hdc/v41/ot_hdc_sinkhorn.sv",
     "description": "the steady sum adds the third term before the second: ((a + c) + b) + d",
     "before": "ot_hdc_sk_add u_s1 (.ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),",
     "after": "ot_hdc_sk_add u_s1 (.ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[2]), .mb(mm[2]),",
     "before2": "ot_hdc_sk_add u_s2 (.ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),",
     "after2": "ot_hdc_sk_add u_s2 (.ea(g1), .ua(u1), .ma(m1), .eb(ee[1]), .mb(mm[1]),"},
    {"id": "chain_late_increment_ignored", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "the chained add ignores the late exponent increment when ordering the operands",
     "before": "wire        a_ge  = ua ? age_c[1] : age_c[0];", "after": "wire        a_ge  = age_c[0];",
     "equivalent": "a true equivalent mutant: the two orders differ only when a's incremented exponent equals b's, where the alignment distance is 0 either way and the sum is the same"},
    {"id": "chain_alignment_ignores_increment", "source": "rtl/hdc/v41/ot_hdc_sk_arith.sv",
     "description": "the chained add aligns the early operand for the un-incremented running-sum exponent",
     "before": "wire [24:0] shb   = ua ? shb_c[1] : shb_c[0];", "after": "wire [24:0] shb   = shb_c[0];"},
    {"id": "no_transpose", "source": "rtl/hdc/v41/ot_hdc_sinkhorn.sv",
     "description": "the steady step writes rows back untransposed (normalises rows twice)",
     "before": "assign s_out[4*c + r] = {1'b0, q};", "after": "assign s_out[4*r + c] = {1'b0, q};"},
    {"id": "zero_row_unflagged", "source": "rtl/hdc/v41/ot_hdc_sinkhorn.sv",
     "description": "a zero row sum (0/0) no longer fails closed",
     "before": "assign a_bad_sum[r] = o1 | o2 | o3 | tz;", "after": "assign a_bad_sum[r] = o1 | o2 | o3;"},
    {"id": "one_iteration_short", "source": "rtl/hdc/v41/ot_hdc_sinkhorn.sv",
     "description": "19 Sinkhorn iterations instead of 20",
     "before": "localparam integer STEPS = 2 * ITERS - 1;", "after": "localparam integer STEPS = 2 * ITERS - 3;"},
)


def mutant_sources(spec, d: Path):
    src = ROOT / spec["source"]
    text = src.read_text()
    for bk, ak in (("before", "after"), ("before2", "after2")):
        if bk in spec:
            assert text.count(spec[bk]) == 1, (spec["id"], bk, text.count(spec[bk]))
            text = text.replace(spec[bk], spec[ak])
    out = d / f"mut_{spec['id']}_{src.name}"
    out.write_text(text)
    return [out if p == src else p for p in RTL]


def run_mutation(spec, d: Path, unit_vec: Path, arith_vec: Path):
    srcs = mutant_sources(spec, d)
    res = {"id": spec["id"], "source": spec["source"], "description": spec["description"]}
    if "equivalent" in spec:
        res["equivalent"] = spec["equivalent"]
    caught_by = []
    rc, log, _ = build_verilator(d / f"obj_mu_{spec['id']}", "tb_hdc_sinkhorn", srcs)
    if rc == 0:
        r = run_unit(d / f"obj_mu_{spec['id']}" / "Vtb_hdc_sinkhorn", unit_vec)
        res["unit"] = {k: r.get(k) for k in ("errors", "word_errors", "latency_min", "latency_max", "pass")}
        if not r["pass"] and "errors" in r:
            caught_by.append("unit")
    if spec["source"].endswith("ot_hdc_sk_arith.sv"):
        rc2, _, _ = build_verilator(d / f"obj_ma_{spec['id']}", "tb_hdc_sk_arith", srcs, arith=True)
        if rc2 == 0:
            out = subprocess.run([str(d / f"obj_ma_{spec['id']}" / "Vtb_hdc_sk_arith"), f"+IN={arith_vec}"],
                                 capture_output=True, text=True).stdout
            a = parse_arith(out)
            res["arith"] = {k: a.get(k) for k in ("ops", "errors", "pass")}
            if not a["pass"] and "errors" in a:
                caught_by.append("arith")
    res["compiled"] = rc == 0
    res["caught_by"] = caught_by
    res["caught"] = rc == 0 and bool(caught_by)
    return res


# -- campaign -------------------------------------------------------------------------------------------
def run(args) -> dict:
    t0 = time.time()
    ok = True
    gen_seed = GEN.check_seed()
    gen_model = GEN.check_model(args.model_samples)
    rom_ok = ROM.read_text() == GEN.rom_text()
    ok &= rom_ok
    print("generator checks done", round(time.time() - t0), "s", flush=True)

    e_real, real_meta = real_cases(args.positions)
    print("real cases", len(e_real), round(time.time() - t0), "s", flush=True)
    rng = np.random.default_rng(20260924)
    e_rand, labels = random_cases(rng, args.random_cases)
    class_counts = {c: labels.count(c) for c in sorted(set(labels))}

    with tempfile.TemporaryDirectory(dir=args.scratch) as scratch:
        s = Path(scratch)
        lint = {}
        for top in ("ot_hdc_sinkhorn", "ot_hdc_sk_add", "ot_hdc_sk_quot", "ot_hdc_sk_seed"):
            srcs = RTL if top == "ot_hdc_sinkhorn" else [ARITH, ROM]
            r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", top, *map(str, srcs)],
                               capture_output=True, text=True)
            lint[top] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:10]}
            ok &= r.returncode == 0

        # vectors: real first in its own file, random in shards
        real_vec = s / "real.vec"
        real_faults = write_unit_vectors(real_vec, b32(e_real))
        shards = []
        per = -(-len(e_rand) // args.shards)
        rand_faults = 0
        for i in range(args.shards):
            v = s / f"rand{i}.vec"
            chunk = e_rand[i * per:(i + 1) * per]
            if len(chunk) == 0:
                continue
            rand_faults += write_unit_vectors(v, chunk)             # already bit patterns
            shards.append((v, len(chunk)))
        arng = np.random.default_rng(7)
        lines, acounts = arith_vectors(arng, args.arith_per_pair)
        edge = edge_arith_lines()
        n_edge = len(edge)
        dlines, directed = directed_arith_lines(np.random.default_rng(11), args.directed, args.directed_keep)
        edge = edge + dlines                     # the front block: every mutation run sees all of it
        lines = edge + lines
        order = arng.permutation(len(lines))
        per_a = -(-len(lines) // args.shards)
        arith_shards = []
        for i in range(args.shards):
            v = s / f"arith{i}.vec"
            sel = order[i * per_a:(i + 1) * per_a]
            v.write_text("".join(lines[j] for j in sel))
            arith_shards.append(v)
        vec_sha = hashlib.sha256(b"".join(p.read_bytes() for p in [real_vec, *[v for v, _ in shards],
                                                                     *arith_shards])).hexdigest()
        print("vectors written", round(time.time() - t0), "s", flush=True)

        # Icarus (a second simulator, slow on this bit-level netlist): a slice, in the background
        icarus_pool = ThreadPoolExecutor(1)
        icarus_fut = icarus_pool.submit(run_icarus, s, real_vec, edge + lines[len(edge):], args.icarus_cases,
                                        args.icarus_arith) if args.icarus_cases else None

        obj_u, obj_a = s / "obj_unit", s / "obj_arith"
        with ThreadPoolExecutor(2) as ex:
            fu = ex.submit(build_verilator, obj_u, "tb_hdc_sinkhorn", RTL)
            fa = ex.submit(build_verilator, obj_a, "tb_hdc_sk_arith", RTL, ITERS, True)
            (rcu, logu, cmdu), (rca, loga, _) = fu.result(), fa.result()
        assert rcu == 0, logu
        assert rca == 0, loga
        print("built", round(time.time() - t0), "s", flush=True)
        exe_u, exe_a = obj_u / "Vtb_hdc_sinkhorn", obj_a / "Vtb_hdc_sk_arith"

        jobs = [("real_back_to_back", real_vec, 0, 0, 1), ("real_gaps_early", real_vec, 30, 50, 5)]
        jobs += [(f"random_shard{i}", v, (20 if i % 2 else 0), (40 if i % 2 else 0), 11 + i)
                 for i, (v, _) in enumerate(shards)]
        with ThreadPoolExecutor(args.jobs) as ex:
            futs = {name: ex.submit(run_unit, exe_u, v, gap, early, seed) for name, v, gap, early, seed in jobs}
            afuts = [ex.submit(lambda v: parse_arith(subprocess.run([str(exe_a), f"+IN={v}"], capture_output=True,
                                                                    text=True).stdout), v) for v in arith_shards]
            unit_runs = {k: f.result() for k, f in futs.items()}
            arith_runs = [f.result() for f in afuts]
        for k, r in unit_runs.items():
            print(k, "pass" if r["pass"] else "FAIL", r.get("cases"), r.get("errors"), r.get("seconds"), flush=True)
        ok &= all(r["pass"] for r in unit_runs.values())
        ok &= all(r["pass"] for r in arith_runs)
        unit_ok_counts = {
            "real_cases": int(len(e_real)),
            "random_cases": int(len(e_rand)),
            "random_fault_cases": rand_faults,
            "real_fault_cases": real_faults,
            "cases_checked": int(sum(r.get("cases", 0) for r in unit_runs.values())),
            "quotients_checked": int(sum(r.get("cases", 0) for r in unit_runs.values())) * 16 * 2 * ITERS,
        }
        ok &= unit_ok_counts["real_cases"] > 0
        arith_total = {k: int(sum(r.get(k, 0) for r in arith_runs)) for k in ("ops", "add", "div", "div_steady", "add_chained",
                                                                                  "errors")}
        print("arith", arith_total, flush=True)

        # mutations: a small unit set (real + every random class) and an arithmetic set
        mutations = []
        if not args.skip_mutations:
            mu_unit = s / "mut_unit.vec"
            pick = np.concatenate([np.arange(min(300, len(e_real)))])
            mu_e = [b32(e_real[pick]).reshape(len(pick), 16)]
            for c in sorted(set(labels)):
                ii = [i for i, lab in enumerate(labels) if lab == c][:120]
                mu_e.append(e_rand[ii].reshape(len(ii), 16))
            write_unit_vectors(mu_unit, np.concatenate(mu_e))
            mu_arith = s / "mut_arith.vec"
            mu_arith.write_text("".join(lines[:len(edge)] + [lines[len(edge) + j] for j in
                                                             range(0, len(lines) - len(edge), 23)]))
            with ThreadPoolExecutor(args.jobs) as ex:
                mutations = list(ex.map(lambda sp: run_mutation(sp, s, mu_unit, mu_arith), MUTATIONS))
            for m in mutations:
                print("mutation", m["id"], "caught" if m["caught"] else
                      ("not caught (equivalent)" if m.get("equivalent") else "MISSED"), m["caught_by"], flush=True)
            ok &= all(m["caught"] for m in mutations if not m.get("equivalent"))

        icarus = icarus_fut.result() if icarus_fut else {}
        icarus_pool.shutdown()
        if icarus:
            ok &= all(r["pass"] for r in icarus.values())
            print("icarus", {k: v["pass"] for k, v in icarus.items()}, flush=True)

    status = "pass" if ok else "fail"
    return {
        "schema": "opentallas.hdc-v41-sinkhorn-campaign.v1",
        "status": status,
        "claim_boundary": "functional cycle-level RTL simulation of the Sinkhorn unit and its arithmetic against "
                          "tools/hdc_golden_v41.py (add, div, seqsum, and hc_mixes' Sinkhorn tail); the clock "
                          "is not claimed here -- see results/physical_abi3/asap7/hdc/v41/ot_hdc_sinkhorn/.",
        "function": "hc_mixes after the exponential: rows softmax-normalised + eps, columns, then "
                    f"{ITERS - 1} x (rows, columns); sums sequential in index order, binary32 RNE, canonical +0",
        "fail_closed": "negative (nonzero) or nonfinite input, overflowing or zero row sum, out-of-range quotient "
                       "-> fault with out_valid and y all +0; -0 reads as +0",
        "latency_definition": "clock edges from the accepting edge to the edge that registers out_valid: 2 ITERS + 1 "
                              "(A: row sums; B: step-0 divide + eps; 2 ITERS - 1 steady steps, one per clock)",
        "latency_cycles": 2 * ITERS + 1,
        "generator": {"seed_bound": gen_seed, "model_vs_ieee_samples_per_class": args.model_samples,
                      "model_classes": len(gen_model), "rom_matches_generator": rom_ok},
        "real_data": real_meta,
        "random_classes": class_counts,
        "unit": {"counts": unit_ok_counts, "runs": unit_runs, "vectors_sha256": vec_sha},
        "arithmetic": {"generated": acounts, "edge_pairs": n_edge // 2, "directed_quotients": directed,
                       "totals": arith_total,
                       "shards": arith_runs},
        "icarus": icarus,
        "mutations": mutations,
        "verilator_lint": {"flags": list(LINT_FLAGS), "tops": lint},
        "simulators": {"verilator": subprocess.run(["verilator", "--version"], capture_output=True,
                                                   text=True).stdout.strip(),
                       "icarus": subprocess.run(["iverilog", "-V"], capture_output=True,
                                                text=True).stdout.splitlines()[0] if args.icarus_cases else None},
        "wall_seconds": round(time.time() - t0),
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*RTL, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--positions", type=int, default=REAL_POSITIONS)
    ap.add_argument("--random-cases", type=int, default=1_000_000)
    ap.add_argument("--directed", type=int, default=4_000_000, help="pairs tried per directed-quotient class")
    ap.add_argument("--directed-keep", type=int, default=100_000, help="near-boundary pairs simulated per class")
    ap.add_argument("--arith-per-pair", type=int, default=60_000)
    ap.add_argument("--model-samples", type=int, default=100_000)
    ap.add_argument("--shards", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--icarus-cases", type=int, default=2)
    ap.add_argument("--icarus-arith", type=int, default=400)
    ap.add_argument("--skip-mutations", action="store_true")
    ap.add_argument("--scratch", default=None, help="directory for the temporary build (default: system temp)")
    args = ap.parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
