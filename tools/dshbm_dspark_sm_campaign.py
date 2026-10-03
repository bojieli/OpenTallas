#!/usr/bin/env python3
"""DSpark on the V4.1 HBM comparator: every SM matvec of a speculative step on the SM element RTL, bit for bit.

    HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_sm_campaign.py reduced --ops DIR/sm_ops.pkl --out PART.json
    HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_sm_campaign.py fullshape --out PART.json

REDUCED.  tools/dshbm_dspark_trace.py --sm-steps N captures, during the golden's own speculative step, every matvec
the SM element executes (linear_q FP8 / FP4 block dots, mv / linear_bf16 BF16 csum, the grouped wo_a) together with
its input and the golden's output.  Calls of one weight in one command form ONE SM pass with one MMA column per
position (verify: the gamma + 1 positions; DSpark stages: the 5 block slots; a routed expert: the positions / slots
that selected it -- the expert union streams each expert once); the Markov head runs one column a step (serial).
Each pass runs on W13's V4.1 SM macro top rtl/gpu/ot_gpu_sm_v.sv (Icarus, via tools/w19_sm_real_ops.smv_real, which
packs operands exactly as W19 did) with up to 256 rows a simulation, and every column's FP32 accumulators must equal
the golden's csum bit for bit and the rounded output must equal the golden function's output.  Hyper-connection
mixes (FP32 weights, not an exact BF16 MMA) and the attention dots stay on their dedicated units (as in W19).

FULLSHAPE.  The three DSpark SM shapes the speculation price (d2aff19ef) took from the line rate because no RTL had
run them, on the RELEASED checkpoint's weights (synthetic BF16 activations, labelled), on the busiest SM of a TP-96
die (rows split 96 ways, then 32 SMs): the Markov head (129,280 x rank, 1 column: one serial step), the shared LM
head on the 5 block slots (5 columns), main_proj (5 or 6 columns).  Measured start-to-done cycles vs the model's
line-rate price.
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

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "build/models/deepseek-v4.1-flash-reduced-v2").exists():
    os.environ.setdefault("OPENTALLAS_BUILD", "/home/ubuntu/OpenTallas/build")
os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import rtl_gpu_sm_exact as S  # noqa: E402
import w19_sm_real_ops as WS  # noqa: E402

F = np.float32
RCHUNK = 256
# W13's SM source list, plus the prefix adders ot_hdc_fp32_add_lat.sv now instantiates (rtl_gpu_sm_exact.SMV_SRC
# predates that dependency; it is left untouched and the list is completed here).  The adders come from
# rtl/test/ot_hdc_prefix_sim.sv, the repository's SAT-proved behavioural stand-ins for rtl/hdc/ot_hdc_prefix.sv: with
# the (* keep *) Kogge-Stone file Icarus did not finish elaborating the SM bench in > 20 CPU-minutes.
SMV_SRC = S.SMV_SRC[:-1] + ["rtl/test/ot_hdc_prefix_sim.sv", S.SMV_SRC[-1]]
_EXE, _LOCK = {}, __import__("threading").Lock()
_KLOCK: dict = {}
EXE_DIR = os.environ.get("DSHBM_SM_EXE", "/tmp/claude-1000/dshbm/smexe")


def exe_for(params):
    """One compiled bench per parameter set, cached on disk by the parameters and the sources' digest (compiles of
    different sets run in parallel)."""
    key = tuple(sorted(params.items()))
    tag = hashlib.sha256((repr(key) + "".join(S.sha(s) for s in SMV_SRC)).encode()).hexdigest()[:16]
    with _LOCK:
        lk = _KLOCK.setdefault(tag, __import__("threading").Lock())
    with lk:
        if tag not in _EXE:
            d = Path(EXE_DIR) / tag
            exe = d / "sim.vvp"
            if not exe.exists():
                d.mkdir(parents=True, exist_ok=True)
                S.compile_tb(SMV_SRC, "tb_gpu_sm_v", params, d)
            _EXE[tag] = exe
    return _EXE[tag]


def sim_runner(params, d):
    exe = exe_for(params)
    return S.run_sim(exe, d, 0)
SCHEMA = "opentallas.rtl.dshbm_dspark_sm.v1"


def ckpt_dtypes(path):
    import struct
    with open(path, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        h = json.loads(fh.read(n))
    return {k: v["dtype"] for k, v in h.items() if k != "__metadata__"}


def group_ops(steps):
    """(step, ctx, weight) -> the columns of one SM pass, in call order."""
    groups = {}
    for st in steps:
        for op in st["ops"]:
            ctx = tuple(op["ctx"]) if op["ctx"] else ("?", 0)
            if op["name"] == "head.weight" and ctx[0] in ("V", "SEED"):
                ctx = ("VH", 0)
            groups.setdefault((st["step"], ctx, op["fn"], op["name"]), []).append(op)
    return groups


def fmt_of(fn, name, w, dts):
    if fn == "linear_q":
        return "v41_fp4" if dts.get(name) == "I8" else "v41_fp8"
    return "v41_bf16"


def run_group(key, ops, w, fmt, workdir):
    step, ctx, fn, name = key
    X = [o["x"] for o in ops]
    if fmt == "v41_bf16":
        wd = np.asarray(w, dtype=F)
        if not np.array_equal(G.bits(G.to_bf16(wd)), G.bits(wd)):
            return dict(step=step, ctx=list(ctx), fn=fn, weight=name, cols=len(X), skipped="weight not BF16-valued")
        R = wd.shape[0]
    else:
        R = w.q.shape[0]
    res = []
    for r0 in range(0, R, RCHUNK):
        r1 = min(R, r0 + RCHUNK)
        wc = np.asarray(w, dtype=F)[r0:r1] if fmt == "v41_bf16" else V.Q8(w.q[r0:r1], w.e[r0:r1])
        acc, gold, meta = WS.smv_real(f"{name}:{r0}", fmt, wc, X, workdir=workdir, sim_runner=sim_runner)
        mism_acc = mism_out = 0
        for n, o in enumerate(ops):
            a, g = acc[n], gold[n]
            mism_acc += int(np.sum(G.bits(a) != G.bits(g))) + int(np.isnan(a).sum())
            got = G.to_bf16(a) if fn == "linear_q" else a
            mism_out += int(np.sum(G.bits(np.asarray(got, dtype=F)) != G.bits(o["y"][r0:r1])))
        res.append(dict(rows=[r0, r1], accumulator_mismatches=mism_acc, output_mismatches=mism_out,
                        cycles=meta.get("cycles_start_to_done"), fault=meta.get("fault"), timeout=bool(meta.get("timeout"))))
    ok = all(r["accumulator_mismatches"] == 0 and r["output_mismatches"] == 0 and not r["timeout"] and r["fault"] == 0
             for r in res)
    K = (np.asarray(w).shape[1] if fmt == "v41_bf16" else w.q.shape[1])
    return dict(step=step, ctx=list(ctx), fn=fn, weight=name, fmt=fmt, rows=int(R), K=int(K), cols=len(X),
                chunks=res, exact=bool(ok))


def model_weights():
    """The reduced checkpoint's tensors by name exactly as hdc_golden_v41.Model holds them (Q8 blocks, the dense BF16
    wo_a), without building the Engram tables (which need the tokenizer)."""
    t = V.load_checkpoint(V.CHECKPOINT)
    w = {}
    for name, v in t.items():
        if name.endswith(".scale"):
            continue
        sc = name[:-len(".weight")] + ".scale" if name.endswith(".weight") else None
        w[name] = V._blocked(v, t[sc], name) if sc in t and not name.endswith("engram.embed.weight") else v
    for k in [k for k in w if k.endswith("attn.wo_a.weight")]:
        w[k] = V.to_bf16(w[k].dense())
    return w


def cmd_reduced(a):
    d = pickle.loads(Path(a.ops).read_bytes())

    class _M:
        w = model_weights()
    m = _M
    dts = ckpt_dtypes(V.CHECKPOINT)
    groups = group_ops(d["steps"])
    jobs = []
    for key, ops in sorted(groups.items(), key=lambda kv: str(kv[0])):
        fn, name = key[2], key[3]
        w = d["anon"][name] if name.startswith("anon:") else m.w[name]
        jobs.append((key, ops, w, fmt_of(fn, name, w, dts)))
    os.makedirs(a.workdir, exist_ok=True)
    print(f"{len(jobs)} SM passes", flush=True)
    with ThreadPoolExecutor(a.jobs) as pool:
        out = list(pool.map(lambda j: run_group(*j, a.workdir), jobs))
    for r in out:
        if "skipped" in r:
            print("SKIP", r["ctx"], r["weight"], r["skipped"])
    ran = [r for r in out if "skipped" not in r]
    passed = all(r["exact"] for r in ran)
    by_phase = {}
    for r in ran:
        ph = r["ctx"][0]
        b = by_phase.setdefault(ph, dict(passes=0, sims=0, exact=0, cols=set()))
        b["passes"] += 1
        b["sims"] += len(r["chunks"])
        b["exact"] += int(r["exact"])
        b["cols"].add(r["cols"])
    for b in by_phase.values():
        b["cols"] = sorted(b["cols"])
    rec = dict(part="reduced", status="pass" if passed else "fail", sm_passes=len(ran),
               simulations=sum(len(r["chunks"]) for r in ran), skipped=[r for r in out if "skipped" in r],
               by_phase=by_phase, ops_pickle_sha256=hashlib.sha256(Path(a.ops).read_bytes()).hexdigest(), cases=ran)
    return rec, passed


# ---------------------------------------------------------------------------------------------------- fullshape
def cmd_fullshape(a):
    import rtl_v41_fullshape_layer_campaign as LC
    ck = LC.Checkpoint()
    cfg = json.loads((LC.HF / "config.json").read_text())
    rng = np.random.default_rng(20261003)
    TP, NSM = 96, 32

    def busiest(R):
        die = -(-R // TP)
        return -(-die // NSM)

    def load(name):
        raw, dt, shape = ck.raw(name)
        if dt == "BF16":
            return G.from_bits(np.frombuffer(bytes(raw), dtype=np.uint16).astype(np.uint32) << 16).reshape(shape)
        raise ValueError(dt)

    cases = []
    jobs = []
    names = list(ck.map)
    mk = next(n for n in names if n.endswith("markov_head.head.weight"))
    head = "head.weight"
    mp = next(n for n in names if n.endswith("main_proj.weight"))
    # markov head: one column (a serial step), the input is a real embed row of the Markov head
    wmk = load(mk)
    emb = load(next(n for n in names if n.endswith("markov_head.embed.weight")))
    R = busiest(wmk.shape[0])
    jobs.append(("markov_head", "v41_bf16", wmk[:R], [emb[21946]], "real weights, real input (embed row of token 21946)"))
    # LM head on the 5 block slots: synthetic normed activations (BF16), real weights
    wh = load(head)
    R = busiest(wh.shape[0])
    X = [G.to_bf16(rng.standard_normal(wh.shape[1]).astype(F)) for _ in range(5)]
    jobs.append(("lm_head_5slots", "v41_bf16", wh[:R], X, "real weights, synthetic BF16 activations"))
    # main_proj (FP8, the 3 target layers' main hidden parts concatenated): 6 columns (seeded per verified position)
    m_raw, m_dt, m_shape = ck.raw(mp)
    sc = next(n for n in names if n == mp[:-len(".weight")] + ".scale")
    s_raw, s_dt, s_shape = ck.raw(sc)
    q = V._blocked(np.frombuffer(bytes(m_raw), dtype=np.uint8).reshape(m_shape),
                   np.frombuffer(bytes(s_raw), dtype=np.uint8).astype(np.int32).reshape(s_shape) - 127, mp)
    R = busiest(m_shape[0])
    X = [G.to_bf16(rng.standard_normal(m_shape[1]).astype(F)) for _ in range(6)]
    jobs.append(("main_proj_6pos", "v41_fp8", V.Q8(q.q[:R], q.e[:R]), X, "real weights, synthetic BF16 activations"))
    os.makedirs(a.workdir, exist_ok=True)

    def one(j):
        tag, fmt, w, X, src = j
        acc, gold, meta = WS.smv_real(tag, fmt, w, X, workdir=a.workdir, xdepth=a.xdepth, sim_runner=sim_runner)
        mism = sum(int(np.sum(G.bits(x) != G.bits(g))) + int(np.isnan(x).sum()) for x, g in zip(acc, gold))
        K = np.asarray(w).shape[1] if fmt == "v41_bf16" else w.q.shape[1]
        R = np.asarray(w).shape[0] if fmt == "v41_bf16" else w.q.shape[0]
        return dict(case=tag, fmt=fmt, K=int(K), sm_rows=int(R), cols=len(X), operands=src,
                    accumulator_mismatches=mism, exact=mism == 0 and meta.get("fault", 1) == 0 and not meta.get("timeout"),
                    rtl=meta)
    with ThreadPoolExecutor(3) as pool:
        cases = list(pool.map(one, jobs))
    for c in cases:
        print(c["case"], c["fmt"], "K", c["K"], "R", c["sm_rows"], "cols", c["cols"], "EXACT" if c["exact"] else "MISMATCH",
              "cycles", c["rtl"].get("cycles_start_to_done"), flush=True)
    passed = all(c["exact"] for c in cases)
    return dict(part="fullshape", status="pass" if passed else "fail", checkpoint=str(LC.HF),
                dim=cfg.get("text_config", {}).get("hidden_size"), cases=cases), passed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("part", choices=("reduced", "fullshape"))
    ap.add_argument("--ops", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workdir", default="/tmp/claude-1000/dshbm/sm")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--xdepth", type=int, default=128)
    a = ap.parse_args()
    V.set_arith("chunk8")
    rec, passed = cmd_reduced(a) if a.part == "reduced" else cmd_fullshape(a)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sim = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
    srcs = sorted(set(SMV_SRC + ["tools/dshbm_dspark_sm_campaign.py", "tools/w19_sm_real_ops.py",
                                   "tools/rtl_gpu_sm_exact.py", "tools/hdc_golden_v41.py", "tools/dshbm_dspark_trace.py"]))
    rec.update(schema=SCHEMA, generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               source_commit=head, simulator=sim, source_sha256={s: S.sha(s) for s in srcs})
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print("PASS" if passed else "FAIL", a.out)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
