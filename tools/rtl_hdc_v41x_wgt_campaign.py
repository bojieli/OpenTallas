#!/usr/bin/env python3
"""Bit-exact + performance RTL campaign of the V4.1x weight engines (block `wgt`).

The two weight engines of the re-specified DeepSeek-V4.1-Flash decode die
(docs/ARCH_SPEC_V41.md 6 item 3), rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv:

* KIND 0, the quantised engine: tools/hdc_golden_v41.linear_q under R-ARITH
  (HDC_V41_ARITH=chunk8): FP8 activation (act_quant per 32-block), FP8 E4M3 or
  FP4 E2M1 weights with a UE8M0 scale per row x 32-block, exact block dots
  rounded once and scaled, the block values combined by csum, BF16 out;
* KIND 1, the BF16/FP32 engine: hdc_golden_v41.matvec_c under chunk8
  (csum(mul(w, bf16(x)))), FP32 and BF16 out.

Vectors come from the golden only: RANDOM (seeded; shipped K and edge
distributions: subnormal / overflowing scaled blocks, NaN codes, cancellation)
and REAL -- every linear the golden applies while it decodes prompt positions
of the reduced vehicle (build/models/deepseek-v4.1-flash-reduced-v2), captured
by wrapping the golden's own linear_q / matvec_c.  Expected values are the
golden functions' outputs; where the golden result is not finite the tile must
raise its fault instead.

For every tile configuration the Verilator bench (rtl/test/tb_hdc_v41x_wgt.sv)
runs three times: back to back (throughput: one beat of L lanes x M positions
per cycle, sustained across rows and ops), with throttled output credits
(functional), and one op at a time (latency: descriptor to last result,
asserted against the spec's ceil(rows*K/lanes) + 60 + 3*ceil(log2(K/32/8))
[quantised] or + 60 + 3*ceil(log2(K/8)) [BF16/FP32]).  Writes
results/rtl/hdc_v41x_wgt_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

V.set_arith("chunk8")
F = np.float32
OUT = ROOT / "results/rtl/hdc_v41x_wgt_campaign.json"
RTL = [ROOT / f"rtl/hdc/v41x/{n}.sv" for n in ("ot_hdc_v41x_wgt_bdot", "ot_hdc_v41x_wgt_red", "ot_hdc_v41x_wgt_mac",
                                                  "ot_hdc_v41x_wgt_tile")]
LIB = [ROOT / "rtl/hdc/ot_hdc_delay.sv", ROOT / "rtl/hdc/ot_hdc_fastfp.sv"]
TB = ROOT / "rtl/test/tb_hdc_v41x_wgt.sv"
HARNESS = ROOT / "rtl/test/hdc_v41x_wgt_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py", Path(__file__).resolve()]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
_V5 = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
VERILATOR = str(_V5) if _V5.exists() else "verilator"
CLOCK_HZ = 1.0339e9
SPEC = {"weight_macs_per_cycle": 231936, "bf16_macs_per_cycle": 31360, "rom_bytes_per_cycle": 301904,
        "lane_mult_design_point": 2, "depth_formula_q": "60 + 3*ceil(log2(K/32/8))",
        "depth_formula_m": "60 + 3*ceil(log2(K/8))",
        "latency_formula": "ceil(rows*K/lanes) + depth", "source": "docs/ARCH_SPEC_V41.md 5-6; results/arch/arch_budget_v41.json"}

SUM = re.compile(r"V41XWGT ops=(\d+) events=(\d+) checked=(\d+) errors=(\d+) faults=(\d+) cycles=(\d+) beats=(\d+) "
                 r"first_beat=(-?\d+) last_beat=(-?\d+) last_out=(-?\d+) start=(\d+)")
LAT = re.compile(r"V41XWGT_LAT op=(\d+) cycles=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def u32(x):
    return V.bits(np.asarray(x, dtype=F)).astype(np.int64)


# -- code tables ------------------------------------------------------------------------------------
_E4 = {}
for _c in range(256):
    if (_c & 0x7F) != 0x7F:
        _E4[(float(abs(V.E4M3[_c])), _c >> 7)] = _c


def e4m3_codes(vals):
    v = np.asarray(vals, dtype=np.float64).reshape(-1)
    return np.array([_E4[(abs(float(a)), int(np.signbit(a)))] for a in v], dtype=np.int64).reshape(np.shape(vals))


def e2m1_codes(vals):
    v = np.asarray(vals, dtype=np.float64)
    idx = np.searchsorted(V.E2M1_VALUES, np.abs(v))
    assert np.all(V.E2M1_VALUES[np.minimum(idx, 7)] == np.abs(v))
    return (idx + 8 * np.signbit(v)).astype(np.int64)


# -- ops -----------------------------------------------------------------------------------------------
@dataclass
class Op:
    """One matvec on one tile: rows x nb terms (KIND 0: nb 32-blocks; KIND 1: nb weights), M positions."""
    kind: int
    name: str
    nrows: int
    nb: int
    wcode: np.ndarray            # KIND 0: [rows, nb*32] codes (E4M3 bytes / E2M1 nibbles); KIND 1: [rows, nb] fp32 bits
    wexp: np.ndarray | None      # KIND 0: [rows, nb] UE8M0 bytes
    fp4: bool
    xw: list                     # per position: KIND 0 ([nb*32] codes, [nb] UE8M0 bytes); KIND 1 [nb] bf16 bits
    y32: np.ndarray              # [M, rows] fp32 bits
    ybf: np.ndarray              # [M, rows] bf16 bits
    yf: np.ndarray               # [M, rows] fault expected
    plg: int = 0
    experts: list = field(default_factory=list)   # indirect: other experts' (wcode, wexp) sharing the table
    eid: int = 0
    source: str = "random"


def qe_expect(wq, we, x):
    """linear_q (chunk8) of one position: FP32 csum, BF16 (== linear_q), fault."""
    xq, xe = V.quant_fp8(x)
    n, k = wq.shape
    with np.errstate(over="ignore", invalid="ignore"):
        blocks = [np.ldexp((wq[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F), we[:, b] + xe[b]).astype(F)
                  for b in range(k // 32)]
        acc = V.csum(np.stack(blocks, axis=-1)) if blocks else np.zeros(n, F)
        y = V.linear_q(V.Q8(wq, we), x)
    fin = np.isfinite(acc)
    assert np.array_equal(u32(V.to_bf16(acc))[fin], u32(y)[fin])
    return acc, y, fin, xq, xe


def make_qe(name, wq, we, xs, source="random"):
    """wq float64 values [rows, K] (E4M3 or E2M1), we int unbiased exponents [rows, K/32], xs list of fp32 x."""
    rows, k = wq.shape
    nb = k // 32
    fp4 = bool(np.all(np.isin(np.abs(wq[np.isfinite(wq)]), V.E2M1_VALUES))) and np.all(np.isfinite(wq))
    if fp4:
        codes = e2m1_codes(wq)
    else:
        codes = np.zeros(wq.shape, np.int64)
        nanm = ~np.isfinite(wq)
        codes[~nanm] = e4m3_codes(wq[~nanm])
        codes[nanm] = 0x7F
    y32, ybf, yf, xw = [], [], [], []
    for x in xs:
        acc, y, fin, xq, xe = qe_expect(wq, we, x)
        y32.append(np.where(fin, u32(acc), 0))
        ybf.append(np.where(fin, u32(y) >> 16, 0))
        yf.append((~fin).astype(np.int64))
        xw.append((e4m3_codes(xq), (np.asarray(xe) + 127).astype(np.int64)))
    return Op(0, name, rows, nb, codes, (np.asarray(we) + 127).astype(np.int64), fp4, xw, np.array(y32),
              np.array(ybf), np.array(yf), source=source)


def make_me(name, w, xs, source="random"):
    w = np.asarray(w, dtype=F)
    rows, k = w.shape
    y32, ybf, yf, xw = [], [], [], []
    for x in xs:
        with np.errstate(over="ignore", invalid="ignore"):
            acc = V.matvec_c(w, np.asarray(x, F), 1)
        fin = np.isfinite(acc)
        y32.append(np.where(fin, u32(acc), 0))
        ybf.append(np.where(fin, u32(V.to_bf16(acc)) >> 16, 0))
        yf.append((~fin).astype(np.int64))
        xw.append(u32(V.to_bf16(np.asarray(x, F))) >> 16)
    return Op(1, name, rows, k, u32(w), None, False, xw, np.array(y32), np.array(ybf), np.array(yf), source=source)


# -- random operands -------------------------------------------------------------------------------------
def rand_x(rng, k, style="normal"):
    x = rng.standard_normal(k).astype(np.float64)
    if style == "wide":
        x *= np.exp2(rng.integers(-30, 30, k))
    elif style == "blocks":
        x *= np.repeat(np.exp2(rng.integers(-20, 20, -(-k // 32))), 32)[:k]
    elif style == "tiny":
        x *= 2.0 ** -120
    x[rng.random(k) < 0.03] = 0.0
    return V.to_bf16(x.astype(F))


def rand_qw(rng, rows, k, fp4, style="normal"):
    nb = k // 32
    if fp4:
        codes = rng.integers(0, 16, (rows, k))
        wq = V.E2M1[codes].astype(np.float64)
    else:
        codes = rng.integers(0, 256, (rows, k))
        codes[(codes & 0x7F) == 0x7F] ^= 1                      # no NaN unless asked
        if style == "nan":
            r, c = rng.integers(0, rows), rng.integers(0, k)
            codes[r, c] = 0x7F
        wq = V.E4M3[codes].astype(np.float64)
    if style == "sub":
        we = rng.integers(-127, -100, (rows, nb))
    elif style == "ovf":
        we = rng.integers(100, 129, (rows, nb))
    elif style == "cancel":
        wq[:, 16:32] = -wq[:, 0:16]
        we = rng.integers(-8, 8, (rows, nb))
    else:
        we = rng.integers(-12, 4, (rows, nb))
    return wq, we


def rand_mw(rng, rows, k, fp32, style="normal"):
    w = rng.standard_normal((rows, k)) * (0.05 if style == "normal" else 1.0)
    if style == "wide":
        w *= np.exp2(rng.integers(-40, 40, (rows, k)))
    if style == "ovf":
        w *= 2.0 ** 125
    if style == "sub":
        w *= 2.0 ** -126
    w = w.astype(F)
    return w if fp32 else V.to_bf16(w)


# -- real operands (the reduced vehicle) ---------------------------------------------------------------
def capture_real(positions=2):
    """Every linear_q / matvec_c the golden applies while decoding `positions` prompt positions, keyed by the
    weight's storage (so position p of the same weight pairs for the lane multiplier)."""
    m = V.Model()
    lq, mc = V.linear_q, V.matvec_c
    calls = {}

    def lq2(w, x):
        key = ("q", w.q.__array_interface__["data"][0], w.q.shape)
        calls.setdefault(key, {"w": w, "xs": []})["xs"].append(np.asarray(x, F).copy())
        return lq(w, x)

    def mc2(w, x, s):
        w = np.asarray(w)
        key = ("m", w.__array_interface__["data"][0], w.shape)
        calls.setdefault(key, {"w": w, "xs": []})["xs"].append(np.asarray(x, F).copy())
        return mc(w, x, s)

    V.linear_q, V.matvec_c = lq2, mc2
    try:
        prompt, _ = V.prompt_and_expected()
        st = m.new_state()
        for p in range(positions):
            m.decode_token(prompt[p], p, st)
    finally:
        V.linear_q, V.matvec_c = lq, mc
    return calls


def real_ops(calls, kind, M, max_rows, per_shape, rng):
    """Up to per_shape weights of every distinct (shape, format), rows subsampled to max_rows, M positions (the
    same weight's operands at M decode positions; a weight seen once repeats its operand)."""
    seen = {}
    ops = []
    for key, c in calls.items():
        if (key[0] == "q") != (kind == 0):
            continue
        w = c["w"]
        shp = w.q.shape if kind == 0 else w.shape
        fp4 = kind == 0 and bool(np.all(np.isin(np.abs(w.q), V.E2M1_VALUES)))
        sk = (shp, fp4)
        if seen.get(sk, 0) >= per_shape:
            continue
        seen[sk] = seen.get(sk, 0) + 1
        rows = shp[0]
        sel = np.sort(rng.choice(rows, size=min(rows, max_rows), replace=False))
        xs = [c["xs"][min(p, len(c["xs"]) - 1)] for p in range(M)]
        nm = f"real_{'fp4' if fp4 else ('fp8' if kind == 0 else 'mv')}_{shp[0]}x{shp[1]}"
        if kind == 0:
            ops.append(make_qe(nm, w.q[sel], w.e[sel], xs, source="real"))
        else:
            ops.append(make_me(nm, np.asarray(w, F)[sel], xs, source="real"))
    return ops


# -- tile configuration, layout, bench --------------------------------------------------------------------
@dataclass
class Cfg:
    kind: int
    G: int
    M: int
    LB: int
    PMIN_LG: int = 0
    RL: int = 2

    @property
    def L(self):
        return 8 * self.G

    @property
    def NC(self):
        return self.G >> self.PMIN_LG

    @property
    def LG(self):
        return int(math.log2(self.G))

    def key(self):
        return f"k{self.kind}_g{self.G}_m{self.M}_lb{self.LB}_p{self.PMIN_LG}_rl{self.RL}"


def pick_plg(cfg: Cfg, op: Op, mode="best"):
    """Segment size for an op: the fewest beats x row groups (then the smallest P); `mode` an int forces it."""
    if isinstance(mode, int):
        return mode
    best = None
    for plg in range(cfg.PMIN_LG, cfg.LG + 1):
        P = 1 << plg
        nbeat = -(-op.nb // (8 * P))
        if nbeat > (1 << cfg.LB):
            continue
        nrg = -(-op.nrows // (cfg.G >> plg))
        c = nrg * nbeat
        if best is None or c < best[0]:
            best = (c, plg)
    assert best is not None, (op.name, op.nb)
    return best[1]


def geometry(cfg, op):
    P = 1 << op.plg
    nbeat = -(-op.nb // (8 * P))
    nrg = -(-op.nrows // (cfg.G >> op.plg))
    return P, nbeat, nrg


def hexline(v, bits):
    return format(int(v), "0%dx" % (-(-bits // 4)))


def word_q(codes_row, e, fp4, lo, hi):
    """264-bit ROM word of one 32-block: {we, codes}; FP4 nibbles packed in the low 128 bits."""
    acc = 0
    blk = codes_row[lo:hi]
    if fp4:
        for i, c in enumerate(blk):
            acc |= int(c) << (4 * i)
    else:
        for i, c in enumerate(blk):
            acc |= int(c) << (8 * i)
    return acc | (int(e) << 256)


def write_run(cfg: Cfg, ops, d: Path):
    """ROM image, activation memory, op list and expected result events for one bench run."""
    d.mkdir(parents=True, exist_ok=True)
    L, M, WW, XW = cfg.L, cfg.M, (264 if cfg.kind == 0 else 32), (264 if cfg.kind == 0 else 16)
    rom_words = {}
    xmem = []
    opw = []
    exp = []
    a_next = 0
    for i, op in enumerate(ops):
        P, nbeat, nrg = geometry(cfg, op)
        per = nrg * nbeat
        mats = [(op.wcode, op.wexp)] + list(op.experts)
        # indirect ops: the op's own matrix is expert `eid` of a table of len(mats) experts at stride `per`
        order = list(range(1, len(mats)))
        order.insert(op.eid, 0)
        wbase = a_next
        for slot, mi in enumerate(order):
            wc, wx = mats[mi]
            base = wbase + slot * per
            for rg in range(nrg):
                for q in range(nbeat):
                    a = base + rg * nbeat + q
                    for j in range(L):
                        row = rg * (cfg.G >> op.plg) + (j >> (3 + op.plg))
                        t = q * 8 * P + (j % (8 * P))
                        if row >= op.nrows or t >= op.nb:
                            continue
                        if cfg.kind == 0:
                            rom_words[a * L + j] = word_q(wc[row], wx[row, t], op.fp4, 32 * t, 32 * t + 32)
                        else:
                            rom_words[a * L + j] = int(wc[row, t]) & 0xFFFFFFFF
        a_next = wbase + len(mats) * per
        xbase = len(xmem)
        for t in range(op.nb):
            for p in range(M):
                if cfg.kind == 0:
                    codes, ex = op.xw[p]
                    acc = 0
                    for k, cde in enumerate(codes[32 * t:32 * t + 32]):
                        acc |= int(cde) << (8 * k)
                    xmem.append(acc | (int(ex[t]) << 256))
                else:
                    xmem.append(int(op.xw[p][t]))
        ind = 1 if op.experts else 0
        opw += [op.plg, op.nb, op.nrows, wbase, ind, op.eid if ind else 0, per if ind else 0, int(op.fp4), xbase, nrg]
        for rg in range(nrg):
            nseg = cfg.G >> op.plg
            mask = 0
            vals = []
            for s in range(cfg.NC):
                row = rg * nseg + s
                real = s < nseg and row < op.nrows
                mask |= int(real) << s
                for p in range(M):
                    if real:
                        vals += [int(op.y32[p, row]), int(op.ybf[p, row]), int(op.yf[p, row])]
                    else:
                        vals += [0, 0, 0]
            exp += [rg, i % 16, mask] + vals
    romd = max(rom_words) + 1 if rom_words else 1
    with open(d / "rom.hex", "w") as f:
        f.write("\n".join(hexline(rom_words.get(a, 0), WW) for a in range(romd)) + "\n")
    with open(d / "xmem.hex", "w") as f:
        f.write("\n".join(hexline(v, XW) for v in xmem) + "\n")
    with open(d / "ops.hex", "w") as f:
        f.write("\n".join(hexline(v, 32) for v in opw) + "\n")
    with open(d / "exp.hex", "w") as f:
        f.write("\n".join(hexline(v, 32) for v in exp) + "\n")
    return {"rom_depth": romd, "xmem": len(xmem), "exp": len(exp), "ops": len(ops)}


def pow2(n):
    return 1 << max(4, int(n - 1).bit_length())


def build(cfg: Cfg, sizes, obj: Path):
    obj.mkdir(parents=True, exist_ok=True)
    params = [f"-GKIND={cfg.kind}", f"-GG={cfg.G}", f"-GM={cfg.M}", f"-GLB={cfg.LB}", f"-GPMIN_LG={cfg.PMIN_LG}",
              f"-GRL={cfg.RL}", f"-GNBW={10 if cfg.kind == 0 else 14}", f"-GMAXOPS={max(16, sizes['ops'])}", f"-GROMD={pow2(sizes['rom_depth'])}",
              f"-GXMD={pow2(sizes['xmem'])}", f"-GEXPD={pow2(sizes['exp'])}"]
    stamp = obj / "params.txt"
    if (obj / "Vtb").exists() and stamp.exists() and stamp.read_text() == " ".join(params):
        return obj / "Vtb"
    subprocess.run([VERILATOR, "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "--top-module", "tb_hdc_v41x_wgt", "--prefix", "Vtb", "-Mdir", str(obj), *params,
                    *map(str, LIB), *map(str, RTL), str(TB), str(HARNESS), "-CFLAGS", "-O1"],
                   check=True, capture_output=True)
    stamp.write_text(" ".join(params))
    return obj / "Vtb"


def run_bench(exe: Path, d: Path, nops: int, gap: int, throttle: int):
    r = subprocess.run([str(exe), f"+ops={d / 'ops.hex'}", f"+rom={d / 'rom.hex'}", f"+xmem={d / 'xmem.hex'}",
                        f"+exp={d / 'exp.hex'}", f"+nops={nops}", f"+gap={gap}", f"+throttle={throttle}"],
                       capture_output=True, text=True, check=True)
    m = SUM.search(r.stdout)
    if not m:
        raise RuntimeError(r.stdout[-3000:])
    g = list(map(int, m.groups()))
    lat = {int(a): int(b) for a, b in LAT.findall(r.stdout)}
    errs = [ln for ln in r.stdout.splitlines() if ln.startswith("V41XWGT_ERR")][:8]
    return {"ops": g[0], "events": g[1], "checked": g[2], "errors": g[3], "faults_expected_and_raised": g[4],
            "cycles": g[5], "beats": g[6], "first_beat": g[7], "last_beat": g[8], "last_out": g[9], "start": g[10],
            "latency": lat, "error_lines": errs}


def spec_depth(cfg, op):
    nc = max(1, -(-op.nb // 8))
    return 60 + 3 * math.ceil(math.log2(nc)) if nc > 1 else 60


def budget(cfg, op):
    return -(-op.nrows * op.nb // cfg.L) + spec_depth(cfg, op)


# -- suites ----------------------------------------------------------------------------------------------
SHIPPED_Q = [("wq_a", 5120), ("wq_b", 1280), ("wo_b", 8192), ("experts_w2", 2304)]
SHIPPED_M = [("router_gate_fp32", 5120, True), ("wo_a_group", 4096, False), ("cmp_wk", 512, False)]


def suite(cfg: Cfg, rng, real_calls, quick=False):
    """(throughput ops, latency ops) for a tile configuration."""
    M = cfg.M
    ops = []
    lat = []
    if cfg.kind == 0:
        # random, shipped K; rows fill several row groups
        for name, k in (SHIPPED_Q[:2] if quick else SHIPPED_Q):
            for fp4 in (False, True):
                wq, we = rand_qw(rng, 2 * cfg.G * 8 if not quick else cfg.G * 2, k, fp4)
                ops.append(make_qe(f"shipped_{name}_{'fp4' if fp4 else 'fp8'}_K{k}", wq, we,
                                   [rand_x(rng, k, "blocks") for _ in range(M)]))
        # edge distributions at small K
        for st in (("sub", "ovf", "cancel", "nan") if not quick else ("sub", "nan")):
            for fp4 in (False, True):
                if st == "nan" and fp4:
                    continue
                k = 32 * int(rng.integers(1, 40))
                wq, we = rand_qw(rng, int(rng.integers(1, 3 * cfg.G + 2)), k, fp4, st)
                ops.append(make_qe(f"edge_{st}_{'fp4' if fp4 else 'fp8'}_K{k}", wq, we,
                                   [rand_x(rng, k, "wide" if st != "cancel" else "normal") for _ in range(M)]))
        # indirect (routed expert): 4 experts in a table, the op picks one by id
        k = 2304 if not quick else 256
        rows = 4 * cfg.G if not quick else cfg.G
        mats = [rand_qw(rng, rows, k, True) for _ in range(4)]
        op = make_qe(f"routed_expert_indirect_fp4_K{k}", mats[2][0], mats[2][1], [rand_x(rng, k) for _ in range(M)])
        op.experts = [(e2m1_codes(m[0]), (m[1] + 127).astype(np.int64)) for i, m in enumerate(mats) if i != 2]
        op.eid = 2
        ops.append(op)
        if real_calls is not None:
            ops += real_ops(real_calls, 0, M, 64 if not quick else 16, 1 if quick else 2, rng)
        # latency ops: shipped K, rows = two full passes of the tile
        for name, k in (SHIPPED_Q if not quick else SHIPPED_Q[1:2]):
            wq, we = rand_qw(rng, cfg.G * 8, k, False)
            lat.append(make_qe(f"lat_{name}_K{k}", wq, we, [rand_x(rng, k) for _ in range(M)]))
        wq, we = rand_qw(rng, 1, 32, False)
        lat.append(make_qe("lat_single_block_row", wq, we, [rand_x(rng, 32) for _ in range(M)]))
    else:
        for name, k, fp32 in (SHIPPED_M if not quick else SHIPPED_M[2:]):
            w = rand_mw(rng, 2 * cfg.G if not quick else cfg.G, k, fp32)
            ops.append(make_me(f"shipped_{name}_K{k}", w, [rand_x(rng, k) for _ in range(M)]))
        for st in (("wide", "ovf", "sub") if not quick else ("wide",)):
            for fp32 in (False, True):
                k = int(rng.integers(1, 300))
                w = rand_mw(rng, int(rng.integers(1, 3 * cfg.G + 2)), k, fp32, st)
                ops.append(make_me(f"edge_{st}_{'fp32' if fp32 else 'bf16'}_K{k}", w,
                                   [rand_x(rng, k, "wide") for _ in range(M)]))
        if real_calls is not None:
            ops += real_ops(real_calls, 1, M, 64 if not quick else 16, 1 if quick else 2, rng)
        for name, k, fp32 in (SHIPPED_M if not quick else SHIPPED_M[2:]):
            w = rand_mw(rng, 4 * cfg.G, k, fp32)
            lat.append(make_me(f"lat_{name}_K{k}", w, [rand_x(rng, k) for _ in range(M)]))
        w = rand_mw(rng, 1, 8, True)
        lat.append(make_me("lat_single_chunk_row", w, [rand_x(rng, 8) for _ in range(M)]))
    return ops, lat


def assign_plg(cfg, ops, rng, vary):
    """Best segment size per op; with `vary`, every other op takes a random legal size (exercises every tap)."""
    for i, op in enumerate(ops):
        op.plg = pick_plg(cfg, op)
        if vary and i % 2 == 1:
            legal = [p for p in range(cfg.PMIN_LG, cfg.LG + 1) if -(-op.nb // (8 << p)) <= (1 << cfg.LB)]
            op.plg = int(rng.choice(legal))


def run_cfg(cfg: Cfg, scratch: Path, seed: int, real_calls, quick=False):
    rng = np.random.default_rng(seed)
    ops, lat = suite(cfg, rng, real_calls, quick)
    assign_plg(cfg, ops, rng, vary=True)
    assign_plg(cfg, lat, rng, vary=False)
    d1, d2 = scratch / cfg.key() / "tp", scratch / cfg.key() / "lat"
    s1, s2 = write_run(cfg, ops, d1), write_run(cfg, lat, d2)
    sizes = {k: max(s1[k], s2[k]) for k in s1}
    exe = build(cfg, sizes, scratch / cfg.key() / "obj")
    tp = run_bench(exe, d1, len(ops), 0, 0)
    th = run_bench(exe, d1, len(ops), 0, 3)
    la = run_bench(exe, d2, len(lat), 1, 0)
    beats = sum(geometry(cfg, o)[1] * geometry(cfg, o)[2] for o in ops)
    useful = sum(o.nrows * o.nb for o in ops)
    macs_item = 32 if cfg.kind == 0 else 1
    issue_span = tp["last_beat"] - tp["first_beat"] + 1
    lat_rows = []
    for i, o in enumerate(lat):
        P, nbeat, nrg = geometry(cfg, o)
        lat_rows.append({"op": o.name, "rows": o.nrows, "K": o.nb * macs_item, "plg": o.plg, "beats": nbeat * nrg,
                         "measured_cycles": la["latency"][i], "spec_budget_cycles": budget(cfg, o),
                         "depth_measured": la["latency"][i] - nbeat * nrg,
                         "depth_budget": spec_depth(cfg, o), "meets": la["latency"][i] <= budget(cfg, o)})
    ok = (tp["errors"] == 0 and th["errors"] == 0 and la["errors"] == 0 and tp["events"] == sum(geometry(cfg, o)[2] for o in ops)
          and issue_span == beats and tp["beats"] == beats and all(r["meets"] for r in lat_rows))
    return {
        "config": {"kind": ["quantised FP8/FP4 block-dot", "BF16/FP32"][cfg.kind], "G": cfg.G, "lanes": cfg.L,
                   "M_POS": cfg.M, "LB": cfg.LB, "PMIN_LG": cfg.PMIN_LG, "RL": cfg.RL,
                   "macs_per_cycle": cfg.L * macs_item * cfg.M},
        "status": "pass" if ok else "fail",
        "vectors": {"ops": len(ops), "rows": int(sum(o.nrows for o in ops)),
                    "results_checked": tp["checked"], "faults_expected_and_raised": tp["faults_expected_and_raised"],
                    "real_ops": [o.name for o in ops if o.source == "real"],
                    "random_ops": [o.name for o in ops if o.source != "real"],
                    "plg_used": sorted({o.plg for o in ops})},
        "throughput": {"beats": beats, "issue_span_cycles": issue_span, "beats_per_cycle": round(beats / issue_span, 4),
                       "no_bubble": issue_span == beats, "useful_lane_items": useful,
                       "lane_utilisation": round(useful / (beats * cfg.L), 4),
                       "macs_per_cycle_sustained": round(useful * macs_item * cfg.M / issue_span, 1),
                       "total_cycles_incl_fill_drain": tp["cycles"], "errors": tp["errors"]},
        "throttled_credits": {"errors": th["errors"], "checked": th["checked"], "cycles": th["cycles"]},
        "latency": lat_rows,
        "error_lines": tp["error_lines"] + th["error_lines"] + la["error_lines"],
    }


CONFIGS = {
    # quantised engine: the routed tile (one chunk unit, 8 block-dot lanes = 256 MACs), MTP m = 2, and G = 8
    "q_g1_m1": Cfg(0, 1, 1, 5), "q_g1_m2": Cfg(0, 1, 2, 5), "q_g8_m1": Cfg(0, 8, 1, 5), "q_g8_m2": Cfg(0, 8, 2, 5),
    # BF16/FP32 engine: the routed tile (64 MAC lanes), m = 2, and the spec tile (256 lanes)
    "m_g8_m1": Cfg(1, 8, 1, 7, PMIN_LG=1), "m_g8_m2": Cfg(1, 8, 2, 7, PMIN_LG=1), "m_g32_m1": Cfg(1, 32, 1, 5, PMIN_LG=2),
}


def die_mapping(depth_q, depth_m):
    """Per-die latency of the shipped matrices on the per-die tile count, from the measured tile depth
    (the spec's own shapes, results/arch/arch_budget_v41.json layer 20 op inventory)."""
    qops = {"wq_a": (1280, 160), "wkv": (512, 160), "wq_b": (32768, 40), "idx.wq_b": (4096, 40), "wo_b": (5120, 256),
            "shared_w13": (4608, 160), "shared_w2": (5120, 72), "experts_w13": (27648, 160), "experts_w2": (30720, 72)}
    mops = {"wo_a": (2048, 4096), "router_gate": (96, 5120), "idx.weights_proj": (32, 5120), "cmp.wkv": (512, 5120),
            "cmp.wk": (128, 512)}
    import heapq
    out = {"model": "each matrix alone on the die's tiles. A row's padded chunk tree (NP = pow2(chunks)) may be "
                    "cut into 2^s ALIGNED parts (s = 0: whole rows); a part is a row of a tile op (the tile's FP32 "
                    "o_y is the part's subtree root) and the parts' top s tree levels are added by the output "
                    "collector (3 cycles per level + COLLECT_HOP). Parts are packed into tile row groups of "
                    "G/P parts of equal length and the row groups scheduled longest-first onto the tiles. "
                    "latency = makespan (beats) + measured tile depth + collector levels.",
           "collect_hop_cycles": 2}
    hop = 2
    for label, ops, lanes_die, G, T, depth, per, pmin in (
            ("quantised: 906 tiles x 8 block-dot lanes (G=1)", qops, 7248, 1, 906, depth_q, 8, 0),
            ("bf16: 123 tiles x 256 MAC lanes (G=32)", mops, 31360, 32, 123, depth_m, 1, 2)):
        rows = []
        for n, (r, nb) in ops.items():
            nc = -(-nb // 8)
            NP = 1 << max(0, (nc - 1).bit_length())
            bud = -(-r * nb // lanes_die) + 60 + 3 * math.ceil(math.log2(nc))
            best = None
            for s in range(0, NP.bit_length()):
                S = NP >> s                                 # chunks per part
                lens = [min(S, nc - i * S) for i in range(-(-nc // S))]
                for plg in range(pmin, int(math.log2(G)) + 1):
                    P = 1 << plg
                    k = G >> plg                            # parts per row group
                    groups = []
                    for ln in set(lens):
                        cnt = r * lens.count(ln)
                        beats = -(-ln // P)
                        if beats > 32:                     # LB = 5 combiner levels
                            groups = None
                            break
                        groups += [beats] * (-(-cnt // k))
                    if groups is None:
                        continue
                    groups.sort(reverse=True)
                    if len(groups) <= T:
                        mk = groups[0]
                    else:
                        heap = [0] * T
                        for gcost in groups:
                            heapq.heapreplace(heap, heap[0] + gcost)
                        mk = max(heap)
                    lat = mk + depth + (3 * s + hop if s else 0)
                    if best is None or lat < best["latency_cycles"]:
                        best = {"k_split_parts": 1 << s, "segment_P": P, "issue_cycles": mk, "latency_cycles": lat}
            rows.append({"matrix": n, "rows_per_die": r, "terms_per_row": nb * per, **best, "budget_cycles": bud,
                         "meets": best["latency_cycles"] <= bud})
        out[label] = rows
    return out


def run(seed, configs, real, quick=False, scratch=None):
    real_calls = capture_real(2) if real else None
    own = scratch is None
    tmp = tempfile.TemporaryDirectory() if own else None
    s = Path(tmp.name) if own else Path(scratch)
    try:
        lint = {}
        for k in sorted({CONFIGS[c].kind for c in configs}):
            r = subprocess.run([VERILATOR, "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_v41x_wgt_tile",
                                f"-GKIND={k}", "-GG=2", "-GM=2", *map(str, LIB), *map(str, RTL)],
                               capture_output=True, text=True)
            lint[f"kind{k}_g2_m2"] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:20]}
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=max(1, len(configs))) as ex:
            fut = {c: ex.submit(run_cfg, CONFIGS[c], s, seed + i, real_calls, quick) for i, c in enumerate(configs)}
            res = {c: f.result() for c, f in fut.items()}
    finally:
        if own:
            tmp.cleanup()
    ok = all(v["returncode"] == 0 for v in lint.values()) and all(r["status"] == "pass" for r in res.values())
    return res, lint, ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--seed", type=int, default=4141)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--no-real", action="store_true")
    ap.add_argument("--scratch", type=Path, default=None)
    a = ap.parse_args()
    configs = a.configs.split(",")
    res, lint, ok = run(a.seed, configs, not a.no_real, scratch=a.scratch)
    dq = [r["depth_measured"] for c, v in res.items() if v["config"]["G"] == 1 and "quantised" in v["config"]["kind"]
          for r in v["latency"] if r["op"] == "lat_single_block_row"]
    dm = [r["depth_measured"] for c, v in res.items() if v["config"]["G"] == 32 for r in v["latency"]
          if r["op"] == "lat_single_chunk_row"]
    ckpt = V.CHECKPOINT
    rec = {
        "schema": "opentallas.hdc-v41x-wgt-campaign.v1",
        "status": "pass" if ok else "fail",
        "block": "wgt (weight engines: quantised FP8/FP4 block-dot + BF16/FP32)",
        "claim_boundary": "bit-exact cycle simulation (Verilator) of the weight-engine TILE against "
                          "tools/hdc_golden_v41.linear_q / matvec_c under R-ARITH chunk8, with a behavioural banked "
                          "ROM + activation-broadcast model answering the tile's read requests; throughput and "
                          "latency are measured at tile level. The per-die figures are tile count x measured tile "
                          "(die_mapping); the die-level read network, activation buffer and cross-tile wiring are "
                          "not simulated. Clock rate: results/physical_abi3/asap7/hdc/v41x.",
        "spec": SPEC,
        "arith": "chunk8",
        "seed": a.seed,
        "real_operands": {"enabled": not a.no_real, "positions_decoded": 2,
                          "checkpoint": str(ckpt.relative_to(V.BUILD)) if not a.no_real else None,
                          "checkpoint_sha256": sha(ckpt) if not a.no_real else None},
        "configs": res,
        "die_mapping": die_mapping(dq[0] - 1 if dq else 51, dm[0] - 1 if dm else 61) if (dq or dm) else None,
        "verilator_lint": {"flags": list(LINT_FLAGS), "tops": lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*RTL, *LIB, TB, HARNESS, *TOOLS)},
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    for c, v in res.items():
        print(c, v["status"], v["throughput"]["beats_per_cycle"], v["throughput"]["lane_utilisation"],
              [(r["op"], r["measured_cycles"], r["spec_budget_cycles"]) for r in v["latency"]], v["error_lines"][:3])
    print("status", rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
