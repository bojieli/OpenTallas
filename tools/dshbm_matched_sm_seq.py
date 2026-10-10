#!/usr/bin/env python3
"""Op-sequence measurement of the DS HBM SM element for the matched HBM reference (results/rtl/dshbm_matched_reference_20261005).

The inherited composition (tools/dshbm_1m_allmeasured.py) prices a flush group of matvecs as the sum of the ops' weight
LINES plus ONE drain (consecutive expert slots batched), and charges no activation (x-store) load.  The DS ROM review
(reports/DeepSeek_ROM_Architecture_Review.md, evidence reports/deepseek_rom_review_evidence/) names the three omissions:
unused issue slots (the partial last wave of 8 items), separate operation drains (the issue accepts `start` only when
not busy) and activation loading (the x store is written before t0 in every single-op bench).  This tool measures all
three in RTL on the minimum component -- one SM element (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv, ENABLE = 1, the 1.2 GHz
successor, whose own added drain / start latency is therefore inside every cycle count) -- running the busiest SM's op
sequence of a representative layer back to back (rtl/test/tb_hbm_accel_sm_v_seq.sv), bit-exact against the golden for
every result of every op.  Matvec cycles depend on the op shape only (format, K, rows on the busiest SM), not on the
position; the shapes are those of the 1M program at position 1,048,575 (results/rtl/dshbm_baseline_measured_20261004/
program.json).

    python3 tools/dshbm_matched_sm_seq.py run --seq ar_l20 --nc 8 --active 1 --out R.json --workdir W
    python3 tools/dshbm_matched_sm_seq.py run --seq p6_l20 --nc 8 --active 6 --out R.json --workdir W
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import rtl_gpu_sm_exact as S  # noqa: E402

F = np.float32
SRC = ["rtl/hdc/ot_hdc_prefix.sv"] + [s for s in S.SMV_SRC if s != "rtl/test/tb_gpu_sm_v.sv"] + [
    "rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv",
    "physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v",
    "rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv", "rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv",
    "rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv", "rtl/test/tb_hbm_accel_sm_v_seq.sv"]
TB = "tb_hbm_accel_sm_v_seq"
SUB, LBS, LSB, XDEPTH, RMAX, LEV = 4, 2, 16, 128, 256, 4
XC = SUB * LBS * 266 + SUB * LSB * 16          # 3,152 x bits per column

# The busiest SM's matvec sequence of one layer of each matvec TYPE (program.json order; rows = ceil(rows on the die / 32
# SMs), as tools/dshbm_1m_allmeasured.walk prices them).  load = the op's x is not resident (rule: an op reuses the
# resident x context only when it consumes the SAME vector in the SAME format and K as the op before it on this SM).
#   (tag, fmt, K, rows, load)
L20 = [("wq_a", "fp8", 5120, 1, 1), ("wkv", "fp8", 5120, 1, 0), ("compressor.wkv", "bf16", 5120, 1, 1),
       ("indexer.weights_proj", "bf16", 5120, 1, 0), ("wq_b", "fp8", 1280, 16, 1), ("indexer.wq_b", "fp8", 1280, 2, 0),
       ("wo_a", "bf16", 512, 32, 1), ("wo_b", "fp8", 8192, 2, 1), ("router gate", "bf16", 5120, 1, 1)] + \
      [(f"expert slot {s} w{w}", "fp4", 5120, 1, int(s == 0 and w == 1)) for s in range(6) for w in (1, 3)] + \
      [("expert slot 6 w1", "fp8", 5120, 1, 1), ("expert slot 6 w3", "fp8", 5120, 1, 0)] + \
      [(f"expert slot {s} w2", "fp4", 2304, 2, 1) for s in range(6)] + [("expert slot 6 w2", "fp8", 2304, 2, 1)]
# expert workgroup (the shared exact lever): the 12 routed gate/up matrices (6 experts x w1, w3; one input x, FP4,
# K 5,120) as ONE row set: 12 x 24 rows a die = 288 rows over 24 SMs, 12 contiguous rows of ONE matrix per SM (one
# static descriptor per SM, no gather), 8 SMs idle; per-row arithmetic and every result bit unchanged.
# Every sequence starts with a warm-up op (a record's first op is issued before the bench's weight ring has run ahead;
# the reference composition does not use a record's first op when the shape occurs again).
WARM = [("warm-up (router gate shape)", "bf16", 5120, 1, 1)]
WG = WARM + [("routed gate/up workgroup (12 matrices)", "fp4", 5120, 12, 1), ("expert slot 6 w1", "fp8", 5120, 1, 1),
      ("expert slot 6 w3", "fp8", 5120, 1, 0)]
# the remaining shapes of the token (other layer types and the head)
OTHER = WARM + [("L0/L1 wq_a-class fp8 K6144 (9 rows)", "fp8", 6144, 9, 1), ("ratio-2 indexer.wq_b fp8 K1280 (2 rows)", "fp8",
                                                                      1280, 2, 1),
         ("head bf16 K5120 (43 rows)", "bf16", 5120, 43, 1)]
SEQS = dict(ar_l20=L20, wg=WG, other=OTHER, p6_l20=L20, p6_wg=WG, p6_other=OTHER)


def gen_op(fmt, R, K, NC, rng, X=None, *, released_fp4=None):
    """Weight lines in the element's group-slot issue order, x-store fragment words (used addresses only) and the
    golden per column -- the same construction as tools/rtl_gpu_sm_exact.smv_case (gs = True)."""
    e4m3_codes, e2m1_codes = S._codes()
    LB, LF = SUB * LBS, SUB * LSB
    if released_fp4 is not None and (fmt != "v41_fp4" or X is None):
        raise ValueError("released FP4 rows require actual supplied activation X")
    if X is None:                                    # a reused context passes the resident op's x
        X = [rng.standard_normal(K).astype(F) * F(rng.choice([0.1, 1.0, 8.0])) for _ in range(NC)]
    c = 8
    int8 = fmt == "v41_int8"                         # hbm-forks CF-SM: signed INT8 codes; the fmt0 image = their BF16
    if int8:
        fmt = "v41_bf16"
    if fmt == "v41_bf16":
        C = -(-K // 8)
        LA = LF
        if int8:
            codes8 = rng.integers(-128, 128, size=(R, K))
            codes8[0, :] = -128                      # CF-SM rows: -128, 127, 0
            if R > 1:
                codes8[1, :] = 127
            if R > 2:
                codes8[2, :] = 0
            w = codes8.astype(F)
        else:
            w = G.to_bf16(rng.standard_normal((R, K)).astype(F) * F(0.02))
        gold = [V.csum(G.mul(w, G.to_bf16(x)[None, :])) for x in X]
        wb = S.bf16_bits(w).astype(np.int64)
        xb = [S.bf16_bits(x) for x in X]
    else:
        fp4 = fmt == "v41_fp4"
        nb = K // 32
        C = -(-nb // c)
        LA = LB if fp4 else LB // 2
        if fp4:
            if released_fp4 is None:
                mag = rng.integers(0, 8, size=(R, K))
                wv = V.E2M1_VALUES[mag] * np.where(rng.random((R, K)) < 0.5, -1.0, 1.0)
                wcode = e2m1_codes(wv.reshape(-1)).reshape(R, K)
                we = rng.integers(-6, 0, size=(R, nb))
            else:
                packed, scale_bytes = released_fp4
                if (packed.dtype != np.uint8 or packed.shape != (R, K // 2)
                        or scale_bytes.dtype != np.uint8 or scale_bytes.shape != (R, nb)):
                    raise ValueError("released FP4 packed rows/scales do not match SM shape")
                wcode = np.empty((R, K), dtype=np.uint8)
                wcode[:, 0::2], wcode[:, 1::2] = packed & 15, packed >> 4
                wv = V.E2M1_VALUES[wcode & 7] * np.where(wcode & 8, -1.0, 1.0)
                we = scale_bytes.astype(np.int64) - 127
        else:
            cc = rng.integers(0, 256, size=(R, K))
            cc = np.where((cc & 0x7F) == 0x7F, cc ^ 0x01, cc)
            wv = V.E4M3[cc].astype(np.float64)
            wcode = e4m3_codes(wv.reshape(-1)).reshape(R, K)
            we = rng.integers(-14, -8, size=(R, nb))
        wq = V.Q8(wv, we.astype(np.int64))
        gold, xqs = [], []
        for x in X:
            xq, xe = V.quant_fp8(x)
            terms = np.stack([np.ldexp((wq.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F),
                                       wq.e[:, b] + xe[b]).astype(F) for b in range(nb)], axis=-1)
            gold.append(V.csum(terms))
            xqs.append((e4m3_codes(xq), xe))
    Gn = -(-C // LA)
    assert Gn * c <= XDEPTH, (Gn, c, XDEPTH)
    lines = []
    for r, g, t in S.issue_order(R, Gn, c, True):
        word = 0
        for j in range(LA):
            ch = g * LA + j
            if fmt == "v41_bf16":
                k = ch * c + t
                if ch < C and k < K:
                    word |= int(wb[r, k]) << (16 * j)
            else:
                b = ch * c + t
                if ch < C and b < nb:
                    codes = wcode[r, b * 32:(b + 1) * 32]
                    if fp4:
                        for i, cd in enumerate(codes):
                            word |= (int(cd) & 0xF) << (128 * j + 4 * i)
                    else:
                        for i, cd in enumerate(codes):
                            word |= (int(cd) & 0xFF) << (256 * j + 8 * i)
                    word |= ((int(we[r, b]) + 127) & 0xFF) << (1024 + 8 * j)
        lines.append(word)
    xw = []
    for a in range(Gn * c):                          # used addresses only
        g, t = divmod(a, c)
        word = 0
        for n in range(NC):
            for j in range(LA):
                ch = g * LA + j
                if ch >= C:
                    continue
                if fmt == "v41_bf16":
                    k = ch * c + t
                    if k < K:
                        word |= int(xb[n][k]) << (n * XC + LB * 266 + 16 * j)
                else:
                    b = ch * c + t
                    if b < nb:
                        codes, xe = xqs[n]
                        f = 0
                        for i, cd in enumerate(codes[b * 32:(b + 1) * 32]):
                            f |= (int(cd) & 0xFF) << (8 * i)
                        f |= (int(xe[b]) & 0x3FF) << 256
                        word |= f << (n * XC + 266 * j)
        xw.append(word)
    if int8:                                         # fmt3 line = two consecutive BF16 beats' lanes as INT8 codes
        assert len(lines) % 2 == 0, "fmt3 needs an even BF16 beat count"
        def codes(word):
            out = 0
            for j in range(64):
                b = (word >> (16 * j)) & 0xFFFF
                v = int(np.array([b << 16], dtype=np.uint32).view(np.float32)[0])
                out |= (v & 0xFF) << (8 * j)
            return out
        lines = [codes(lines[2 * i]) | (codes(lines[2 * i + 1]) << 512) for i in range(len(lines) // 2)]
    return dict(R=R, c=c, Gn=Gn, fmt=3 if int8 else {"v41_bf16": 0, "v41_fp8": 1, "v41_fp4": 2}[fmt], lines=lines,
                xw=xw, gold=gold, X=X)


def compile_bench(sim, params, outdir, jobs):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if sim == "verilator":
        exe = outdir / ("V" + TB)
        cmd = ["verilator", "--binary", "--timing", "-O2", "-Wno-fatal", "--top-module", TB, "--Mdir", str(outdir),
               "-j", str(jobs), *[f"-G{k}={v}" for k, v in params.items()], *[str(ROOT / s) for s in SRC]]
        if not exe.is_file():                         # one build per parameter key, reused by later sequences
            with (outdir / "build.log").open("w") as log:
                subprocess.run(cmd, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        return [str(exe)], cmd
    exe = outdir / "sim.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", TB] + [f"-P{TB}.{k}={v}" for k, v in params.items()] + \
        [str(ROOT / s) for s in SRC]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return ["vvp", "-n", str(exe)], cmd


def cmd_run(a):
    import hdc_golden_v41 as V2
    V2.set_arith("chunk8")
    ops = SEQS[a.seq]
    rng = np.random.default_rng(20261005)
    d = Path(a.workdir) / a.seq
    d.mkdir(parents=True, exist_ok=True)
    nbeat = -(-a.nc * XC // 2048)
    xb = -(-a.active * XC // 2048)               # beats a used address needs for the active columns
    gens, seq, lines, xw = [], [], [], []
    fw = (a.nc * XC + 2048 + 3) // 4
    resident = None
    for tag, fmt, K, R, load in ops:
        if load:
            g = gen_op("v41_" + fmt, R, K, a.nc, rng)
            resident = g
        else:
            assert resident is not None and resident["fmt"] == {"bf16": 0, "fp8": 1, "fp4": 2}[fmt] and \
                len(resident["X"][0]) == K, (tag, "a reused context needs the same vector, format and K")
            g = gen_op("v41_" + fmt, R, K, a.nc, rng, X=resident["X"])
            assert g["Gn"] == resident["Gn"]
        gens.append(g)
        seq += [R, g["c"], g["Gn"], g["fmt"], len(g["lines"]), 1, load, g["Gn"] * g["c"]]
        lines += [f"{w:0272x}" for w in g["lines"]]
        if load:
            xw += [f"{w:0{fw}x}" for w in g["xw"]]
    (d / "seq.hex").write_text("\n".join(f"{v:08x}" for v in seq) + "\n")
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    params = dict(ENABLE=a.enable, SUB=SUB, LBS=LBS, LSB=LSB, NC=a.nc, XDEPTH=XDEPTH, RMAX=RMAX, LEV=LEV, XB=xb)
    run, cmd = compile_bench(a.sim, params, Path(a.workdir) / f"build_{a.sim}_nc{a.nc}_xb{xb}_en{a.enable}",
                             a.build_jobs)
    with (d / "runtime.log").open("w") as log:
        subprocess.run(run + [f"+DIR={d}", f"+NOPS={len(ops)}"], check=True, cwd=d, stdout=log,
                       stderr=subprocess.STDOUT)
    res, meta = {}, {}
    for line in (d / "out.txt").read_text().splitlines():
        if line.startswith("# op"):
            t = line[2:].split()
            m = {t[k]: int(t[k + 1]) for k in range(2, len(t) - 1, 2)}
            meta[int(t[1])] = m
        elif line.startswith("#"):
            if "TIMEOUT" in line:
                raise SystemExit("TIMEOUT")
        else:
            o, r, h = line.split()
            res.setdefault(int(o), {})[int(r)] = h
    rows, total_mism = [], 0
    for i, ((tag, fmt, K, R, load), g) in enumerate(zip(ops, gens)):
        mism = 0
        got = res.get(i, {})
        for r in range(R):
            h = got.get(r)
            if h is None:
                mism += a.active
                continue
            v = int(h, 16)
            for n in range(a.active):
                if ((v >> (32 * n)) & 0xFFFFFFFF) != int(G.bits(g["gold"][n][r])):
                    mism += 1
        m = meta[i]
        exact = mism == 0 and len(got) == R and m["fault"] == 0 and m["consumed"] == m["lines"]
        total_mism += mism if mism else (0 if exact else 1)
        span = issue_span(R, g["Gn"])
        rows.append(dict(op=i, tag=tag, fmt=fmt, K=K, rows=R, groups=g["Gn"], x_load=bool(load),
                         x_addresses=g["Gn"] * 8 if load else 0, x_beats=g["Gn"] * 8 * xb if load else 0,
                         lines=m["lines"], issue_span_formula=span, mismatches=mism, results=len(got), exact=exact,
                         rtl=m))
    out = dict(schema="opentallas.dshbm.matched_sm_seq.v1", seq=a.seq, element="ot_hbm_accel_sm_v ENABLE=%d" % a.enable,
               nc=a.nc, active_columns=a.active, x_beats_per_address=xb, fragment_beats_all_columns=nbeat,
               simulator=a.sim, bench_clock_ns=1.0, status="pass" if total_mism == 0 else "fail",
               mismatching_ops=sum(1 for r in rows if not r["exact"]), ops=rows,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               build_command=cmd, source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                                                 for s in SRC + ["tools/dshbm_matched_sm_seq.py",
                                                                 "tools/rtl_gpu_sm_exact.py"]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        m = r["rtl"]
        print(f"{r['op']:2d} {r['tag'][:34]:34s} {r['fmt']:4s} K{r['K']:5d} R{r['rows']:3d} load {m['load_cycles']:4d} "
              f"s2d {m['start_to_done']:5d} s2last {m['start_to_last']:5d} lines {r['lines']:5d} "
              f"drain {m['drain_last_line_to_last_result']:4d} exact {r['exact']}")
    print(out["status"].upper(), a.out)
    return 0 if out["status"] == "pass" else 1


def issue_span(R, Gn, il=8):
    """Analytical first-to-last issue span of the group-slot schedule (for the decomposition only)."""
    M = R * Gn
    p = 1 + ((M - 1) % il)
    waves = -(-M // il)
    return (waves - 1) * 64 + 56 + p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("run",))
    ap.add_argument("--seq", choices=sorted(SEQS), required=True)
    ap.add_argument("--nc", type=int, default=8)
    ap.add_argument("--active", type=int, default=1)
    ap.add_argument("--enable", type=int, default=1)
    ap.add_argument("--sim", choices=("verilator", "iverilog"), default="verilator")
    ap.add_argument("--build-jobs", type=int, default=8)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    a.workdir = a.workdir or tempfile.mkdtemp(prefix="smseq_")
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
