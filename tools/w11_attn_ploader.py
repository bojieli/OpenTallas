#!/usr/bin/env python3
"""W11: two-word probability loader (PWORDS) of the V4.1 attention engine -- reduced RTL evidence.

Proposal: results/rtl/v41_attention_elaboration_archive/PV_TWO_WORD_PROPOSAL.md.  This tool runs the
Verilator benches that do not need the full-geometry hierarchical flow:

  tile     ot_hdc_v41x_attn_tile at H16/TD32 with PWORDS=2, NBANK=4: random pair/single p loads (the
           high word of an unpaired load is random garbage that must write nothing), q loads with a
           random ld_w2v (q mode must ignore it), issues from every bank; every output bit-exact vs the
           golden csum.  The same program shape at PWORDS=1/NBANK=3 is the control.
  engine   ot_hdc_v41x_attn at reduced width H16/D128/TD32/NL4 (the full tile geometry, DPT=8, 16 words
           per 32-row block: the same 50% loader cap as the full die) and H8/D64/TD16/NL4, jobs with full
           and partial last blocks (odd word counts), PWORDS=1 vs 2 and upstream supply 1 vs 2 words/cycle.

  verify6  MTP verify at full geometry: 6 query positions back to back (6 jobs of T=640, 6 q loads of 16 words)
           over the same KV rows (the staging buffer is re-filled per job: the engine has no KV-reuse mode) with
           distinct q and probabilities.  --part verify6 --vectors DIR writes the vectors; --part verify6 --exe EXE
           runs a full-geometry build with NJOBMAX=6 NKV=3840 NP=1920 NSC=3840 NPV=3072 and records every job.

The full-geometry gate (H16/D512/TD32/NL4/T640) runs through tools/v41_full_attention_numeric_{build,
link,run}.py.  Output JSON goes to --out (scratch); tools/w11_attn_ploader_record.py assembles the record.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_attn_campaign as C  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402

F = np.float32


def tile_vectors(rng, H, TD, nbeats, nbank, pwords):
    """Random load/issue program for one tile (PWORDS 1 or 2) and its expected outputs."""
    R = TD // H
    BW = 2
    base = TD * 16 + 12 + TD * 18 + BW + 1           # WIN0 of the tile bench
    A = np.zeros((nbank, H, TD), dtype=np.int64)
    stim, exp = [], []
    prog = [("load", b, int(rng.integers(0, 2))) for b in range(nbank)]
    kinds = ["wide", "coarse", "prob"]
    for i in range(nbeats):
        if rng.random() < 0.25:
            prog.append(("load", int(rng.integers(0, nbank)), int(rng.integers(0, 2))))
        prog.append(("issue", int(rng.integers(0, nbank)), kinds[i % 3]))
    busy_until = [-1] * nbank
    cyc = 0
    stats = {"pair_loads": 0, "single_p_loads": 0, "unpaired_high_garbage": 0, "q_loads_w2v_set": 0}
    for op in prog:
        if op[0] == "load":
            _, b, mode = op
            kind = kinds[int(rng.integers(0, 3))]
            words = C.rand_bf16(rng, (H, TD), kind)
            if rng.random() < 0.1:
                words[int(rng.integers(0, H)), int(rng.integers(0, TD))] = 0x7F80 | int(rng.integers(0, 2)) << 15
            # p mode at PWORDS 2: pairs (g, g+1); sometimes the block ends early (odd word count) and the last
            # word goes alone with a garbage high word -> the rows of the skipped groups keep their old value
            if mode == 1 and pwords == 2:
                ngrp = H if rng.random() < 0.6 else int(rng.integers(1, H + 1))
                groups = [(g, g + 1 < ngrp) for g in range(0, ngrp, 2)]
            else:
                groups = [(g, False) for g in range(H)]
            for g, two in groups:
                while cyc <= busy_until[b] + 1:
                    stim.append(0)
                    cyc += 1
                sel = [g, g + 1] if two else [g]
                for gg in sel:
                    w = words[gg]
                    if mode == 0:
                        A[b, gg, :] = w
                    else:
                        for j in range(R):
                            for h in range(H):
                                A[b, h, R * gg + j] = w[j * H + h]
                word = 0
                for k in range(TD):
                    word |= int(words[g][k]) << (16 * k)
                word |= (g << (TD * 16)) | (b << (TD * 16 + 8)) | (mode << (TD * 16 + 10)) | (1 << (TD * 16 + 11))
                if pwords == 2:
                    if two:
                        hi, w2v = words[g + 1], 1
                        stats["pair_loads"] += 1
                    else:
                        hi = rng.integers(0, 1 << 16, TD)          # garbage: must not be written
                        w2v = int(rng.integers(0, 2)) if mode == 0 else 0
                        if mode == 1:
                            stats["single_p_loads"] += 1
                            stats["unpaired_high_garbage"] += 1
                        elif w2v:
                            stats["q_loads_w2v_set"] += 1
                    hw = 0
                    for k in range(TD):
                        hw |= int(hi[k]) << (16 * k)
                    word |= (hw << base) | (w2v << (base + TD * 16))
                stim.append(word)
                cyc += 1
        else:
            _, b, kind = op
            f, c, s = C.rand_kv_elems(rng, (TD,), None, "wide" if kind != "coarse" else "coarse")
            pad = (rng.random(TD) < 0.05).astype(np.int64)
            if rng.random() < 0.05:
                k = int(rng.integers(0, TD))
                f[k], c[k], s[k], pad[k] = 0, 0x7F, 127, 0
            bv = C.deq_value(f, c, s)
            bv = np.where(pad == 1, F(0), bv).astype(F)
            av = C.from_bf16(A[b])
            with np.errstate(over="ignore", invalid="ignore"):
                prod = V.mul(av, bv[None, :])
            prod = np.where(pad[None, :] == 1, F(0), prod).astype(F)
            with np.errstate(over="ignore", invalid="ignore"):
                y = V.csum(prod)
            ew = 0
            for h in range(H):
                fin = bool(np.isfinite(y[h]))
                ew |= ((0 if fin else 1) << 32 | (int(C.u32(y[h])) if fin else 0)) << (33 * h)
            exp.append(ew)
            ib = 0
            for k in range(TD):
                ib |= C.elem_word(pad[k], f[k], c[k], s[k]) << (18 * k)
            word = ib << (TD * 16 + 12)
            word |= (b << (TD * 16 + 12 + TD * 18)) | (1 << (TD * 16 + 14 + TD * 18))
            stim.append(word)
            busy_until[b] = cyc + 18
            cyc += 1
    win = base + (TD * 16 + 1 if pwords == 2 else 0)
    return stim, exp, win, stats


def run_tile(scratch: Path, H, TD, nbeats, seed, pwords, nbank):
    rng = np.random.default_rng(seed)
    stim, exp, win, stats = tile_vectors(rng, H, TD, nbeats, nbank, pwords)
    d = scratch / f"tile_h{H}_td{TD}_p{pwords}_s{seed}"
    d.mkdir(parents=True, exist_ok=True)
    C.write_hex(d / "in.hex", stim, win)
    C.write_hex(d / "exp.hex", exp, 33 * H)
    prm = {"H": H, "TD": TD, "NCYC": len(stim), "NOUT": len(exp), "PWORDS": pwords, "NBANK": nbank}
    obj = d / ("obj_" + C.src_digest([C.RTL_TILE, *C.LIB, C.TB_TILE], prm))
    exe = obj / "Vtb"
    if not exe.is_file():
        C.verilator_build(C.TB_TILE, "tb_hdc_v41x_attn_tile", [C.RTL_TILE, *C.LIB], obj, prm)
    out = subprocess.run([str(exe), f"+in={d / 'in.hex'}", f"+exp={d / 'exp.hex'}"], capture_output=True,
                         text=True, check=True).stdout
    m = C.TILE_RE.search(out)
    assert m, out
    beats, checked, errors, faults, fo, lo = map(int, m.groups())
    return {"H": H, "TD": TD, "PWORDS": pwords, "NBANK": nbank, "seed": seed, "beats": beats,
            "expected_beats": len(exp), "checked": checked, "errors": errors, "faults_expected_and_raised": faults,
            "load_stats": stats, "status": "pass" if errors == 0 and beats == len(exp) else "fail"}


def run_engine(scratch: Path, name, cfg, jobs, pwords, psup):
    d = scratch / name
    counts, stats = C.write_jobs(d, jobs, cfg["H"], cfg["D"], cfg["TD"])
    exe = C.build_engine(scratch, cfg, counts, {"PWORDS": pwords})
    t0 = time.time()
    out = subprocess.run([str(exe), f"+dir={d}", "+seed=1", f"+njob={counts['NJOB']}", f"+psup={psup}"],
                         capture_output=True, text=True, check=True).stdout
    m = C.ENG_RE.search(out)
    assert m, out[-3000:]
    njob, scc, sce, pvc, pve, flt, lsmax, lsmin, lpmax, cyc, tmo = map(int, m.groups())
    per = [dict(zip(("job", "T", "qk_first", "qk_last", "qk_beats", "pv_first", "pv_last", "pv_beats",
                     "last_score", "last_p", "last_pv"), map(int, g.groups()))) for g in C.JOB_RE.finditer(out)]
    for pj in per:
        pj["qk_window"] = pj["qk_last"] - pj["qk_first"] + 1
        pj["pv_window"] = pj["pv_last"] - pj["pv_first"] + 1
    exact = (sce == 0 and pve == 0 and njob == len(jobs) and scc == stats["scores"] and pvc == stats["pv"]
             and flt == stats["score_faults"] + stats["pv_faults"] and not tmo)
    return {"name": name, "config": cfg, "PWORDS": pwords, "psup": psup, "T": [j.T for j in jobs],
            "jobs": njob, "scores_checked": scc, "score_errors": sce, "pv_checked": pvc, "pv_errors": pve,
            "faults": flt, "expected": stats, "cycles": cyc, "timeout": bool(tmo), "per_job": per,
            "sim_seconds": round(time.time() - t0, 1), "exact": exact}


VERIFY6 = dict(NJOBMAX=6, NKV=6 * 640, NP=6 * 320, NSC=6 * 640, NPV=6 * 512)


def verify6_vectors(d: Path):
    rng = np.random.default_rng(20260930)
    base = C.random_job(rng, 16, 512, 640, 128, "coarse")
    jobs = [base]
    for i in range(1, 6):
        q = C.from_bf16(C.rand_bf16(rng, (16, 512), "coarse"))
        pp = C.from_bf16(C.rand_bf16(rng, (16, 640), "coarse"))
        jobs.append(C.Job(q, base.fmt, base.codes, base.scales, pp, f"verify position {i}, KV of position 0"))
    counts, stats = C.write_jobs(d, jobs, 16, 512, 32)
    assert all(counts[k] <= VERIFY6[("NJOBMAX" if k == "NJOB" else k)] for k in counts), counts
    man = dict(scope="MTP verify: 6 queries x T=640 over the same KV rows, H16 D512 TD32 NL4; synthetic golden inputs",
               seed=20260930, counts=counts, expected=stats,
               images={x.name: C.sha(x) for x in sorted(d.glob("*.hex"))})
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def verify6_run(d: Path, exe: Path, psup: int):
    man = json.loads((d / "manifest.json").read_text())
    for n, h in man["images"].items():
        assert C.sha(d / n) == h, n
    t0 = time.time()
    r = subprocess.run([str(exe), f"+dir={d.resolve()}", "+njob=6", "+seed=20260929", f"+psup={psup}"],
                       capture_output=True, text=True, timeout=7200)
    out = r.stdout
    m = C.ENG_RE.search(out)
    assert m, out[-3000:]
    njob, scc, sce, pvc, pve, flt, lsmax, lsmin, lpmax, cyc, tmo = map(int, m.groups())
    per = [dict(zip(("job", "T", "qk_first", "qk_last", "qk_beats", "pv_first", "pv_last", "pv_beats",
                     "last_score", "last_p", "last_pv"), map(int, g.groups()))) for g in C.JOB_RE.finditer(out)]
    prev = 0
    for pj in per:
        pj["qk_window"] = pj["qk_last"] - pj["qk_first"] + 1
        pj["pv_window"] = pj["pv_last"] - pj["pv_first"] + 1
        pj["position_cycles"] = pj["last_pv"] - prev       # from the previous position's last p.v result
        prev = pj["last_pv"]
    ex = man["expected"]
    exact = (r.returncode == 0 and sce == 0 and pve == 0 and njob == 6 and scc == ex["scores"] and pvc == ex["pv"]
             and flt == ex["score_faults"] + ex["pv_faults"] and not tmo)
    return {"psup": psup, "jobs": njob, "scores_checked": scc, "score_errors": sce, "pv_checked": pvc,
            "pv_errors": pve, "faults": flt, "total_cycles": cyc, "timeout": bool(tmo), "per_position": per,
            "executable_sha256": C.sha(exe), "manifest_sha256": C.sha(d / "manifest.json"),
            "wall_seconds": round(time.time() - t0, 1), "exact": exact}


ENGINE_CFGS = {
    "h16d128": (dict(H=16, D=128, TD=32, NL=4, TROWS=160), (160, 129, 33, 1, 2, 64), 32),
    "h8d64": (dict(H=8, D=64, TD=16, NL=4, TROWS=80), (80, 17, 1, 33), 16),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--part", choices=["tile", "engine", "verify6"], required=True)
    ap.add_argument("--cfg", default="h16d128")
    ap.add_argument("--vectors", type=Path)
    ap.add_argument("--exe", type=Path)
    ap.add_argument("--pwords", type=int)
    ap.add_argument("--psup", type=int, default=2)
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    res = []
    if a.part == "verify6" and a.exe is None:
        print(json.dumps(verify6_vectors(a.vectors)))
        return
    if a.part == "verify6":
        r = verify6_run(a.vectors, a.exe, a.psup)
        r["PWORDS"] = a.pwords
        print(json.dumps({k: v for k, v in r.items() if k != "per_position"}), flush=True)
        res.append(r)
    elif a.part == "tile":
        for pw, nb in ((2, 4), (1, 3)):
            for seed in (1, 2, 3):
                r = run_tile(a.scratch, 16, 32, 400, seed, pw, nb)
                print(json.dumps({k: v for k, v in r.items()}), flush=True)
                res.append(r)
    else:
        cfg, Ts, win = ENGINE_CFGS[a.cfg]
        rng = np.random.default_rng(20260929)
        jobs = [C.random_job(rng, cfg["H"], cfg["D"], T, min(T, win), "wide" if i % 2 else "coarse")
                for i, T in enumerate(Ts)]
        for pw, ps in ((1, 1), (2, 2), (2, 1)):
            r = run_engine(a.scratch, f"{a.cfg}", cfg, jobs, pw, ps)
            print(json.dumps({k: v for k, v in r.items() if k != "per_job"}), flush=True)
            res.append(r)
    srcs = [C.RTL_TILE, C.RTL_ENG, C.RTL_STAGE, C.SRAM_MODEL, *C.LIB, C.TB_TILE, C.TB_ENG, C.HARNESS,
            Path(__file__), ROOT / "tools/rtl_hdc_v41x_attn_campaign.py", ROOT / "tools/hdc_golden_v41.py"]
    a.out.write_text(json.dumps({"part": a.part, "cfg": a.cfg if a.part == "engine" else None,
                                 **({"verify6_params": VERIFY6} if a.part == "verify6" else {}),
                                 "sources": {str(p.relative_to(ROOT)): C.sha(p) for p in srcs},
                                 "verilator": C.VERILATOR, "results": res}, indent=1) + "\n")
    ok = all(r.get("status") == "pass" or r.get("exact") for r in res)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
