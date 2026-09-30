#!/usr/bin/env python3
"""W11: position-interleaved MTP verify on the V4.1 attention engine (ot_hdc_v41x_attn ILV = 1).

Verify case: 6 query positions k = 0..5 over one staged KV row set.  Causal rule: the rows are ordered with the
verify positions' own rows last, and position k attends rows [0, T_k) with T_k = T_max - (5 - k) (at full
geometry T_max = 640: 635 .. 640).  Job 0 streams its T_0 rows; jobs 1..5 carry the reuse flag (jobs.hex T field
bit 16 -> engine job_t[15]) and append only their one new row.  Every position has its own q and probabilities
and is checked against its own golden (Job.expected on rows [0, T_k): scores dots(q, kvm), pv dots(p, kvm.T)).
The serial reference (ILV = 0, today's engine) runs the same jobs with every job re-streaming its T_k rows.

SU model (bench): position k's softmax chain starts at max(its last score, the end of position k-1's
probability stream); its first probability word is offered L0 cycles later, then PWORDS words per cycle.
Serial engine: +pdelay=L0 after the job's last score (one job at a time, so the chain order is implied).

  vectors  --cfg NAME --out DIR                write the 6-job vectors (+ manifest.json)
  reduced  --cfg NAME --scratch DIR --out JSON  build ILV 0/1 benches (+define+OT_ATTN_SETCHECK), run L0 values
  run      --exe EXE --vectors DIR --ilv N --l0 L --out JSON   run one full-geometry executable
  negative --cfg h4d64 --scratch DIR --out JSON  the guard is tight: relaxing the p-load threshold by one cycle
           (a copy of the engine with P_THR + 1) must raise set-checker violations and numeric errors
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_attn_campaign as C  # noqa: E402

NPOS = 6
CFGS = {
    "full": dict(H=16, D=512, TD=32, NL=4, TROWS=640, TMAX=640, WIN=128),
    "h8d64": dict(H=8, D=64, TD=16, NL=4, TROWS=80, TMAX=80, WIN=16),
    "h4d64": dict(H=4, D=64, TD=16, NL=1, TROWS=72, TMAX=72, WIN=16),
    "h4d32n4": dict(H=4, D=32, TD=16, NL=4, TROWS=40, TMAX=39, WIN=8),
}
POS_RE = re.compile(r"V41XPOS job=(\d+) accept=(-?\d+) su_start=(-?\d+) p_first=(-?\d+) p_last=(-?\d+)")
ILV_RE = re.compile(r"V41XILV su_l0=(\d+) qk_beats=(\d+) pv_beats=(\d+) busy=(\d+) cycles=(\d+)")
SCK_RE = re.compile(r"V41XSETCHK loads=(\d+) reads=(\d+) errors=(\d+)")


def vectors_model(cfg_name: str, d: Path, seed=20261002):
    """Model-order verify rows (Model.forward_positions): position k attends its own row list, its sliding
    window (WIN rows ending at its own row, oldest first) followed by its OWN selection of compressed rows
    (NSEL rows drawn per position).  No row set is shared, so no reuse flag; golden = Job.expected on the list."""
    cfg = CFGS[cfg_name]
    H, D, TD, TMAX, W = cfg["H"], cfg["D"], cfg["TD"], cfg["TMAX"], cfg["WIN"]
    nsel = TMAX - W
    rng = np.random.default_rng(seed)
    win = C.random_job(rng, H, D, W + NPOS - 1, W + NPOS - 1, "coarse")        # FP8 window rows
    pool = C.random_job(rng, H, D, 4 * nsel + 1, 0, "coarse")                   # FP4 compressed rows
    jobs = []
    for k in range(NPOS):
        sel = np.sort(rng.choice(pool.T, size=nsel, replace=False)) if nsel else np.zeros(0, dtype=int)
        rows = [(win, k + i) for i in range(W)] + [(pool, int(i)) for i in rng.permutation(sel)]
        fmt = np.array([j.fmt[i] for j, i in rows], dtype=np.int64)
        codes = np.stack([j.codes[i] for j, i in rows])
        scales = np.stack([j.scales[i] for j, i in rows])
        q = C.from_bf16(C.rand_bf16(rng, (H, D), "coarse"))
        p = C.from_bf16(C.rand_bf16(rng, (H, len(rows)), "coarse"))
        jobs.append(C.Job(q, fmt, codes, scales, p, f"verify position {k}: window [{k}, {k + W}) + own selection"))
    counts, stats = C.write_jobs(d, jobs, H, D, TD)
    man = dict(scope=(f"MTP verify in model row order: {NPOS} positions, each its own row list (sliding {W}-row "
                      f"window oldest first, then its own {nsel} selected compressed rows); synthetic golden inputs"),
               config=cfg_name, parameters=cfg, seed=seed, order="model", T=[j.T for j in jobs], counts=counts,
               expected=stats, images={x.name: C.sha(x) for x in sorted(d.glob("*.hex"))})
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def vectors(cfg_name: str, d: Path, seed=20261001):
    cfg = CFGS[cfg_name]
    H, D, TD, TMAX = cfg["H"], cfg["D"], cfg["TD"], cfg["TMAX"]
    rng = np.random.default_rng(seed)
    base = C.random_job(rng, H, D, TMAX, cfg["WIN"], "coarse")
    jobs = []
    for k in range(NPOS):
        T = TMAX - (NPOS - 1 - k)
        q = C.from_bf16(C.rand_bf16(rng, (H, D), "coarse"))
        p = C.from_bf16(C.rand_bf16(rng, (H, T), "coarse"))
        jobs.append(C.Job(q, base.fmt[:T], base.codes[:T], base.scales[:T], p, f"verify position {k}, rows [0, {T})"))
    counts, stats = C.write_jobs(d, jobs, H, D, TD)
    # reuse flag on jobs 1..5 (T field bit 16); ILV = 0 benches ignore it
    lines = (d / "jobs.hex").read_text().split()
    lines = [f"{int(x, 16) | ((1 << 16) if i else 0):0{len(x)}x}" for i, x in enumerate(lines)]
    (d / "jobs.hex").write_text("\n".join(lines) + "\n")
    man = dict(scope=f"MTP verify: {NPOS} positions over one KV row set, position k attends rows [0, T_k), "
                     f"T_k = {TMAX} - (5 - k); synthetic golden inputs", config=cfg_name, parameters=cfg, seed=seed,
               T=[j.T for j in jobs], counts=counts, expected=stats,
               images={x.name: C.sha(x) for x in sorted(d.glob("*.hex"))})
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def parse(out: str, man: dict, rc: int):
    m = C.ENG_RE.search(out)
    assert m, out[-3000:]
    njob, scc, sce, pvc, pve, flt, _, _, _, cyc, tmo = map(int, m.groups())
    per = [dict(zip(("job", "T", "qk_first", "qk_last", "qk_beats", "pv_first", "pv_last", "pv_beats",
                     "last_score", "last_p", "last_pv"), map(int, g.groups()))) for g in C.JOB_RE.finditer(out)]
    pos = {int(g.group(1)): dict(zip(("accept", "su_start", "p_first", "p_last"), map(int, g.groups()[1:])))
           for g in POS_RE.finditer(out)}
    prev = 0
    for pj in per:
        pj["qk_window"] = pj["qk_last"] - pj["qk_first"] + 1
        pj["pv_window"] = pj["pv_last"] - pj["pv_first"] + 1
        pj["position_cycles"] = pj["last_pv"] - prev
        prev = pj["last_pv"]
        pj.update(pos.get(pj["job"], {}))
    ex = man["expected"]
    r = dict(jobs=njob, scores_checked=scc, score_errors=sce, pv_checked=pvc, pv_errors=pve, faults=flt,
             total_cycles=cyc, timeout=bool(tmo), per_position=per)
    il = ILV_RE.search(out)
    qkb = sum(p["qk_beats"] for p in per)
    pvb = sum(p["pv_beats"] for p in per)
    r["tile_issue_beats"] = qkb + pvb
    r["tile_utilisation"] = round((qkb + pvb) / cyc, 4) if cyc else None
    if il:
        r["ilv_line"] = dict(zip(("su_l0", "qk_beats", "pv_beats", "busy", "cycles"), map(int, il.groups())))
    sk = SCK_RE.search(out)
    if sk:
        r["setcheck"] = dict(zip(("loads", "reads", "errors"), map(int, sk.groups())))
    r["exact"] = (rc == 0 and sce == 0 and pve == 0 and njob == NPOS and scc == ex["scores"] and pvc == ex["pv"]
                  and flt == ex["score_faults"] + ex["pv_faults"] and not tmo
                  and (not sk or r["setcheck"]["errors"] == 0))
    return r


def run_exe(exe: Path, d: Path, ilv: int, l0: int, extra=()):
    man = json.loads((d / "manifest.json").read_text())
    for n, h in man["images"].items():
        assert C.sha(d / n) == h, n
    arg = f"+su_l0={l0}" if ilv else f"+pdelay={l0}"
    t0 = time.time()
    p = subprocess.run([str(exe), f"+dir={d.resolve()}", f"+njob={NPOS}", "+seed=20261001", arg, *extra],
                       capture_output=True, text=True, timeout=14400)
    r = parse(p.stdout, man, p.returncode)
    r.update(ILV=ilv, L0=l0, plusargs=[arg, *extra], executable_sha256=C.sha(exe),
             manifest_sha256=C.sha(d / "manifest.json"), wall_seconds=round(time.time() - t0, 1))
    return r, p.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["vectors", "reduced", "run", "negative"])
    ap.add_argument("--cfg", default="h8d64")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--scratch", type=Path)
    ap.add_argument("--vectors", type=Path)
    ap.add_argument("--exe", type=Path)
    ap.add_argument("--ilv", type=int, default=1)
    ap.add_argument("--l0", type=int, action="append")
    ap.add_argument("--pwords", type=int, default=2)
    ap.add_argument("--bub", type=int, default=0)
    ap.add_argument("--repl", type=int, default=0, help="engine REPL for the ILV = 1 bench")
    ap.add_argument("--nstage", type=int, default=1, help="engine NSTAGE for the ILV = 1 bench")
    ap.add_argument("--order", choices=["synthetic", "model"], default="synthetic")
    a = ap.parse_args()
    if a.mode == "vectors":
        print(json.dumps((vectors_model if a.order == "model" else vectors)(a.cfg, a.out)))
        return
    if a.mode == "run":
        res = []
        for l0 in a.l0 or [0]:
            r, out = run_exe(a.exe, a.vectors, a.ilv, l0)
            (a.out.parent / f"{a.out.stem}_l{l0}.log").write_text(out)
            print(json.dumps({k: v for k, v in r.items() if k != "per_position"}), flush=True)
            res.append(r)
        a.out.write_text(json.dumps(dict(runs=res), indent=1) + "\n")
        raise SystemExit(0 if all(r["exact"] for r in res) else 1)
    if a.mode == "negative":
        a.scratch.mkdir(parents=True, exist_ok=True)
        vd = a.scratch / f"vec_{a.cfg}"
        man = vectors(a.cfg, vd)
        cfg = CFGS[a.cfg]
        eng = a.scratch / "ot_hdc_v41x_attn_relaxed.sv"
        src = C.RTL_ENG.read_text()
        tight = "localparam integer P_THR = GUARD_Q - GUARD_P + 1;"
        assert src.count(tight) == 1
        eng.write_text(src.replace(tight, "localparam integer P_THR = GUARD_Q - GUARD_P + 2;"))
        cap = {("NJOBMAX" if k == "NJOB" else k): 1 << max(4, int(v - 1).bit_length()) for k, v in man["counts"].items()}
        prm = {**{k: cfg[k] for k in ("H", "D", "TD", "NL", "TROWS")}, **cap, "PWORDS": a.pwords, "ILV": 1}
        exe = C.verilator_build(C.TB_ENG, "tb_hdc_v41x_attn", [C.RTL_TILE, eng, C.RTL_STAGE, C.SRAM_MODEL, *C.LIB],
                                a.scratch / "obj_relaxed", prm)
        res = []
        for l0 in a.l0 or [0]:
            r, out = run_exe(exe, vd, 1, l0)
            res.append(r)
            print(json.dumps({k: v for k, v in r.items() if k != "per_position"}), flush=True)
        caught = all(r["setcheck"]["errors"] > 0 and (r["score_errors"] + r["pv_errors"]) > 0 for r in res)
        a.out.write_text(json.dumps(dict(config=a.cfg, relaxation="P_THR + 1 (one cycle less write-after-read guard)",
                                         engine_source_sha256=C.sha(C.RTL_ENG), runs=res, caught=caught), indent=1) + "\n")
        raise SystemExit(0 if caught else 1)
    # reduced: build with the set checker, run ILV 0 and 1 at each L0
    a.scratch.mkdir(parents=True, exist_ok=True)
    vd = a.scratch / f"vec_{a.cfg}"
    man = (vectors_model if a.order == "model" else vectors)(a.cfg, vd)
    cfg = CFGS[a.cfg]
    res = []
    for ilv in (0, 1):
        extra = {"PWORDS": a.pwords, "ILV": ilv, "BUB": a.bub, **({"REPL": a.repl} if ilv and a.repl else {}),
                 **({"NSTAGE": a.nstage} if ilv and a.nstage != 1 else {})}
        exe = C.build_engine(a.scratch, {k: cfg[k] for k in ("H", "D", "TD", "NL", "TROWS")}, man["counts"], extra)
        for l0 in a.l0 or [0]:
            r, out = run_exe(exe, vd, ilv, l0)
            r.update(config=a.cfg, PWORDS=a.pwords, BUB=a.bub, REPL=a.repl if ilv else 0,
                     NSTAGE=a.nstage if ilv else 1, order=a.order)
            (a.scratch / f"{a.cfg}_ilv{ilv}_l{l0}_b{a.bub}.log").write_text(out)
            print(json.dumps({k: v for k, v in r.items() if k != "per_position"}), flush=True)
            res.append(r)
    a.out.write_text(json.dumps(dict(config=a.cfg, manifest=man, runs=res,
                                     vl_extra=os.environ.get("OT_ATTN_VL_EXTRA")), indent=1) + "\n")
    raise SystemExit(0 if all(r["exact"] for r in res) else 1)


if __name__ == "__main__":
    main()
