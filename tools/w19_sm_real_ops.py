#!/usr/bin/env python3
"""The V4.1 HBM comparator's SM element (W13's ot_gpu_sm_v) on the REAL operands of the TP-96 token (W19 B4/B6).

    python3 tools/w19_sm_real_ops.py --dump DUMP.pkl [--mtp-dump MTP.pkl] [--record results/rtl/w19_sm_real_ops.json]

DUMP.pkl is written by tools/w19_hbm_tp96_isa.py --dump: for every matvec op of the chosen layers, die 0's output
rows [r0, r1), its input vector and its golden-exact outputs (the executor is bit-exact against the golden).  This
tool gives one SM of that die (SM 0 of 32, holding the first ceil((r1 - r0) / 32) rows: the busiest SM of the die, as
the rows are split evenly) the real weight rows from the released checkpoint and the real input, runs W13's V4.1 SM
macro top rtl/gpu/ot_gpu_sm_v.sv (bulk copy, SRAM ring, SRAM x store, exact block-dot / BF16 lanes, the golden tree),
and checks every result bit for bit: linear_q / linear_bf16 / wo_a results after their BF16 rounding against the
executor's outputs, and the FP32 accumulator against the golden's own csum.  With --mtp-dump the same ops run with
the 6 verify positions as 6 MMA columns (one weight pass).  The SM's measured cycles (start -> done, drain) are the
per-op element cycles of the runtime composition.

W13 owns the SM RTL and its bench; this tool only supplies operands (the packing is rtl_gpu_sm_exact.smv_case's).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import rtl_gpu_sm_exact as S  # noqa: E402
import rtl_v41_fullshape_layer_campaign as LC  # noqa: E402

F = np.float32
N_SM = 32
SCHEMA = "opentallas.rtl.w19_sm_real_ops.v1"


def sm_rows(r0, r1):
    return r0, r0 + -(-(r1 - r0) // N_SM)


def smv_real(name, fmt, w, X, gs=True, SUB=4, LBS=2, LSB=16, xdepth=128, rmax=256, lev=4, workdir=None,
             exe_cache={}, sim_runner=None):
    """rtl_gpu_sm_exact.smv_case with given weights and inputs.  w: Q8 (FP8/FP4) or BF16 array; X: NC inputs.
    Returns (FP32 accumulators [NC][R] from the RTL or None, golden FP32 [NC][R], meta)."""
    e4m3_codes, e2m1_codes = S._codes()
    NC = len(X)
    LB, LF = SUB * LBS, SUB * LSB
    XC = LB * 266 + LF * 16
    c = 8
    if fmt == "v41_bf16":
        w = np.asarray(w, dtype=F)
        R, K = w.shape
        C = -(-K // 8)
        LA = LF
        gold = [V.csum(G.mul(w, G.to_bf16(x)[None, :])) for x in X]
        wb = S.bf16_bits(w).astype(np.int64)
        xb = [S.bf16_bits(x) for x in X]
    else:
        fp4 = fmt == "v41_fp4"
        R, K = w.shape
        nb = K // 32
        C = -(-nb // c)
        LA = LB if fp4 else LB // 2
        wv = w.q
        wcode = (e2m1_codes if fp4 else e4m3_codes)(wv.reshape(-1)).reshape(R, K)
        we = w.e
        gold, xqs = [], []
        for x in X:
            xq, xe = V.quant_fp8(x)
            terms = np.stack([np.ldexp((wv[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F),
                                       we[:, b] + xe[b]).astype(F) for b in range(nb)], axis=-1)
            gold.append(V.csum(terms))
            xqs.append((e4m3_codes(xq), xe))
    Gn = -(-C // LA)
    assert Gn * c <= xdepth, (name, Gn, c, xdepth)
    lines = []
    for r, g, t in S.issue_order(R, Gn, c, gs):
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
        lines.append(f"{word:0272x}")
    xw = []
    for a in range(xdepth):
        g, t = divmod(a, c)
        word = 0
        for n in range(NC):
            for j in range(LA):
                ch = g * LA + j
                if g >= Gn or ch >= C:
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
        xw.append(f"{word:0{(NC * XC + 3) // 4}x}")
    d = Path(tempfile.mkdtemp(prefix="s_", dir=workdir))
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    fmt_code = {"v41_bf16": 0, "v41_fp8": 1, "v41_fp4": 2}[fmt]
    (d / "cfg.hex").write_text("\n".join(f"{v:08x}" for v in (R, c, Gn, fmt_code, len(lines), int(gs), 0, 0)) + "\n")
    params = dict(SUB=SUB, LBS=LBS, LSB=LSB, NC=NC, XDEPTH=xdepth, RMAX=rmax, LEV=lev)
    key = ("v",) + tuple(sorted(params.items()))
    if sim_runner is None:
        if key not in exe_cache:
            exe_cache[key] = S.compile_tb(S.SMV_SRC, "tb_gpu_sm_v", params, tempfile.mkdtemp(prefix="b_", dir=workdir))
        res, meta = S.run_sim(exe_cache[key], d, 0)
    else:
        res, meta = sim_runner(params, d)
    acc = [np.full(R, np.nan, dtype=F) for _ in range(NC)]
    for r in range(R):
        h = res.get(r)
        if h is None:
            continue
        v = int(h, 16)
        for n in range(NC):
            acc[n][r] = G.from_bits(np.array([(v >> (32 * n)) & 0xFFFFFFFF], dtype=np.uint32))[0]
    meta.update(lines=len(lines), groups=Gn, active_lanes=LA, rows=R, K=K, cols=NC)
    return acc, gold, meta


FMT = {"fp8": "v41_fp8", "fp4": "v41_fp4", "bf16": "v41_bf16"}


def case(m, key, ents, workdir, sim_runner=None):
    """One op on SM 0 of die 0: ents = the op's dump entries (one per position)."""
    e0 = ents[0]
    r0, r1 = e0["rows"]
    s0, s1 = sm_rows(r0, r1)
    fn = e0["fn"]
    names = e0["w"] if isinstance(e0["w"], list) else [e0["w"]]
    if fn == "wo_a":                                  # grouped: rank 0's rows lie in o-group 0
        assert s1 <= 1024
        w = m.w[names[0]][s0:s1]
        X = [e["x"][:4096] for e in ents]
    elif fn == "wo_a_part":                          # die 0 = head 0: o-group 0's rows, the head's 512 columns
        w = np.asarray(m.w[names[0]][s0:s1, 0:512], dtype=F)
        X = [e["x"] for e in ents]
    else:
        full = [m.w[nm] for nm in names]
        if len(full) > 1:                             # fused (compressor wkv|wgate): rank 0 rows lie in the first
            assert s1 <= full[0].shape[0]
        w0 = full[0]
        w = V.Q8(w0.q[s0:s1], w0.e[s0:s1]) if isinstance(w0, V.Q8) else np.asarray(w0[s0:s1], dtype=F)
        X = [e["x"] for e in ents]
    fmt = FMT[e0["fmt"]]
    if fmt != "v41_bf16" and not isinstance(w, V.Q8):
        fmt = "v41_bf16"
    acc, gold, meta = smv_real(key, fmt, w, X, workdir=workdir, sim_runner=sim_runner)
    rnd = fn in ("linear_q", "linear_bf16", "wo_a")
    mism_acc = mism_out = 0
    for n, e in enumerate(ents):
        a, g = acc[n], gold[n]
        mism_acc += int(np.sum(G.bits(a) != G.bits(g))) + int(np.isnan(a).sum())
        want = e["out"][:s1 - s0]
        got = G.to_bf16(a) if rnd else a
        mism_out += int(np.sum(G.bits(np.asarray(got, dtype=F)) != G.bits(want)))
    ok = mism_acc == 0 and mism_out == 0 and not meta.get("timeout") and meta.get("fault", 1) == 0
    return dict(op=key, tag=e0["tag"], fn=fn, fmt=fmt, matrix=names, die_rows=[r0, r1], sm_rows=[s0, s1],
                K=int(e0["k"]), cols=len(ents), accumulator_mismatches=mism_acc, output_mismatches=mism_out,
                exact=bool(ok), rtl=meta)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--mtp-dump", type=Path)
    ap.add_argument("--record", type=Path)
    ap.add_argument("--workdir", default="/tmp/claude-1000/w19/sm")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    V.set_arith("chunk8")
    os.makedirs(a.workdir, exist_ok=True)
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    out = {}
    for label, path in (("ar", a.dump), ("mtp", a.mtp_dump)):
        if path is None:
            continue
        dump = pickle.loads(path.read_bytes())
        groups = {}
        for k, e in dump.items():
            op, _, p = k.rpartition(".p")
            # MTP: a routed-expert slot holds a different expert per position; the SM pass of one expert's
            # weights carries the columns (positions) that routed to it
            w = e["w"] if isinstance(e["w"], str) else "|".join(e["w"])
            key = op if label == "ar" else f"{op}:{w.split('.')[-3] if '.experts.' in w else ''}"
            groups.setdefault(key, []).append((int(p), e))
        jobs = [(op, [e for _, e in sorted(v, key=lambda t: t[0])]) for op, v in sorted(groups.items())]
        # every weight the cases need, loaded once (not thread-safe to load lazily in parallel)
        for _, ents in jobs:
            for nm in (ents[0]["w"] if isinstance(ents[0]["w"], list) else [ents[0]["w"]]):
                m.w[nm]
        with ThreadPoolExecutor(a.jobs) as pool:
            res = [r for r in pool.map(lambda j: case(m, j[0], j[1], a.workdir), jobs) if r is not None]
        out[label] = res
        for r in res:
            print(f"{label} {r['op']:22s} {r['tag'][:40]:40s} rows {r['sm_rows'][1] - r['sm_rows'][0]:3d} "
                  f"K {r['K']:5d} cols {r['cols']} {'EXACT' if r['exact'] else 'MISMATCH'} "
                  f"cycles {r['rtl'].get('cycles_start_to_done')}", flush=True)
    passed = all(r["exact"] for v in out.values() for r in v)
    if a.record:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        srcs = sorted(set(S.SMV_SRC + ["tools/w19_sm_real_ops.py", "tools/rtl_gpu_sm_exact.py",
                                       "tools/w19_hbm_tp96_isa.py", "tools/hdc_golden_v41.py"]))
        sim = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
        rec = dict(schema=SCHEMA, status="pass" if passed else "fail",
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   source_commit=head, simulator=sim,
                   claim_boundary="RTL simulation (Icarus) of W13's V4.1 SM macro top on the real TP-96 operands of "
                                  "die 0's busiest SM (SM 0 of 32) for every matvec op of the dumped layers; bulk-copy "
                                  "latency is the bench's behavioural LAT/JIT, not the DRAM model. No P&R.",
                   dumps={k: dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                          for k, p in (("ar", a.dump), ("mtp", a.mtp_dump)) if p},
                   cases=out, source_sha256={s: S.sha(s) for s in srcs})
        if a.record.exists():
            old = json.loads(a.record.read_text())
            if old.get("status") == "fail":
                rec["failed_runs"] = old.get("failed_runs", []) + [old]
        a.record.write_text(json.dumps(rec, indent=1, default=int) + "\n")
        print("wrote", a.record)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
