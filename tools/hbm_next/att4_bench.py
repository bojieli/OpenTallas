#!/usr/bin/env python3
"""HBM-NEXT-ATT4: bit-exact bench of the KV-line-stationary 4-query attention slice (rtl/hbm_next/att/ot_hnx_att4_slice)
against 4 single-query goldens, at the DS production shape (head dim 512, window 128 KV8 rows + top-512 KV4 rows a query,
T = 640 a query, 4 query lanes at consecutive positions = the MTP verify / DSpark rows).

Record: lane l (position p + l) attends its window (positions p+l-127 .. p+l, oldest first) and its own top-512 of the
compressed rows (ascending); selections share a base score + sigma x lane noise (sigma sets the overlap; sigma < 0 =
disjoint lanes, the multi-user case).  Golden per lane ALONE: s_l = att_qk(q_l, K_l), p_l = bf16(softmax e), node =
csum8 chunk run of the lane's own list (tools/hgi_sim/lib.py, == tools/hdc_golden_v41.py dots under chunk8).
SM jobs (E1 'aligned' plan): job s = every lane's aligned run s (ordinals [32 s, 32 s + 32)); the job's rows = the sorted
UNION of those lines, each with its lane mask; one QK op + one PV op a job on ONE slice (4 lanes share every beat).
Checks: every lane's scores (by lane ordinal), every lane's run node, and the cross-SM pairwise merge of each lane's
nodes == att_pv(p_l, K_l).  Cycles: union op spans vs the same slice running each lane alone (P = 1 equivalent).

  att4_bench.py run --work DIR --out R.json [--sigma 0.3] [--imut N | --pvmut N | --kvmut N] [--only q0,p0,...] [--p1]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib.util
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

_spec = importlib.util.spec_from_file_location("sm_attn_bench", ROOT / "tools/hbm_sm_attention/sm_attn_bench.py")
SB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SB)

F = np.float32
NLN, W, K, HD = 3, 128, 512, 512   # NLN = query lanes = SM lanes P (P3 default, owner 10-19; --nl 1..4)
SRC = ["physical/hbm_next/att4/macros/hnx_sram_1r1w_128x256_r43/hnx_sram_1r1w_128x256_r43.v", "rtl/hdc/ot_hdc_prefix.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/gpu/ot_gpu_tree.sv",
       "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
       "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
       "rtl/hbm_next/att/ot_hnx_att_kv_line.sv", "rtl/hbm_next/att/ot_hnx_att4_issue.sv",
       "rtl/hbm_next/att/ot_hnx_att_pv_merge.sv", "rtl/hbm_next/att/ot_hnx_att_tcpv_col.sv",
       "rtl/hbm_next/att/ot_hnx_att_stack_flop.sv", "rtl/hbm_next/att/ot_hnx_att4_smerge.sv",
       "rtl/hbm_next/att/ot_hnx_att4_slice.sv", "rtl/hbm_next/att/tb_hnx_att4.sv"]
# A1 merge variants (2026-10-19): base = per-lane merges on the 64x512 macro (LV 4, step 1); shared = ONE shared 4-lane
# merge a column (ot_hnx_att4_smerge, LV 3 flop rings, PRIMARY); flop = per-lane merges on LV 3 flop stacks (fallback)
VARIANTS = {"base": dict(SHARED=0, STORE=0, LV=4), "shared": dict(SHARED=1, STORE=0, LV=3),
            "flop": dict(SHARED=0, STORE=1, LV=3)}
SAFE_RESET = os.environ.get("HNX_ATT_SAFE_RESET") == "1"
VERILATOR = os.environ.get("VERILATOR") or next(
    (c for c in (os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"),) if os.path.exists(c)),
    "verilator")


def make_record(seed, sigma, ncomp=2048):
    rng = np.random.default_rng(seed)
    pos0 = 4 * ncomp + 1000
    win = {p: SB.kv8_row(rng.standard_normal(HD).astype(F) * F(rng.choice([0.05, 1.0, 9.0])))
           for p in range(pos0 - W + 1, pos0 + NLN)}
    comp = [SB.kv4_row(rng.standard_normal(HD).astype(F) * F(rng.choice([0.05, 1.0, 9.0]))) for _ in range(ncomp)]
    base = rng.standard_normal(ncomp)
    lanes = []
    for l in range(NLN):
        if sigma < 0:
            sc = np.full(ncomp, -np.inf)
            seg = ncomp // NLN
            sc[l * seg:(l + 1) * seg] = rng.standard_normal(seg)
        else:
            sc = base + sigma * rng.standard_normal(ncomp)
        sel = sorted(int(i) for i in V.topk_lowest_index(sc, K))
        rows = [("w", p) for p in range(pos0 + l - W + 1, pos0 + l + 1)] + [("c", i) for i in sel]
        q = V.to_bf16(rng.standard_normal(HD).astype(F) * F(0.6))
        Kl = np.stack([(win[i] if k == "w" else comp[i])[2] for k, i in rows]).astype(F)
        s = A.att_qk(q, Kl)
        e, Z, m = A.softmax_e_z(s, F(1.0 / np.sqrt(HD)))
        p = V.to_bf16(e)
        lanes.append(dict(rows=rows, q=q, K=Kl, s=s, p=p, pv=A.att_pv(p, Kl)))
    union = sorted(set(r for ln in lanes for r in ln["rows"]), key=lambda r: (r[0] != "w", r[1]))
    return dict(win=win, comp=comp, lanes=lanes, union=union, sigma=sigma, seed=seed)


def plan(rec, single=None):
    """jobs: (name, kind, kv4, union rows [row keys], {lane: (run_start, run rows)}).  single=l: lane l alone (P=1)."""
    T = len(rec["lanes"][0]["rows"])
    nch = -(-T // 8)
    nrun = 1
    while -(-nch // nrun) > 32:
        nrun *= 2
    jobs = []
    lanes = range(NLN) if single is None else [single]
    for s in range(-(-nch // nrun)):
        a, b = 8 * nrun * s, min(T, 8 * nrun * (s + 1))
        runs = {l: (a, rec["lanes"][l]["rows"][a:b]) for l in lanes}
        rows = sorted(set(r for _, rr in runs.values() for r in rr), key=lambda r: (r[0] != "w", r[1]))
        kv4 = 1 if rows[0][0] == "c" else 0
        assert all((r[0] == "c") == bool(kv4) for r in rows), "job mixes formats"
        tag = "" if single is None else f"_l{single}"
        jobs.append((f"q{s}{tag}", "qk", kv4, rows, runs, nrun))
        jobs.append((f"p{s}{tag}", "pv", kv4, rows, runs, nrun))
    return jobs


def op_files(rec, job, d):
    name, kind, kv4, rows, runs, nrun = job
    blob = b""
    for k, i in rows:
        codes, sc, _ = rec["win"][i] if k == "w" else rec["comp"][i]
        blob += SB.canon_row(codes, sc, kv4)
    lines = SB.stream_lines(blob)
    xs = [0] * (NLN * 128)
    masks = [0] * 16
    for l, (a, rr) in runs.items():
        ln = rec["lanes"][l]
        if kind == "qk":
            qb = SB.bf16b(ln["q"])
            for t in range(8):
                xs[128 * l + t] = sum(int(qb[8 * j + t]) << (16 * j) for j in range(64))
        else:
            pb = SB.bf16b(ln["p"])
            for o in range(len(rr)):
                xs[128 * l + o] = int(pb[a + o])
        sset = set(rr)
        for u, r in enumerate(rows):
            if r in sset:
                masks[u // 16] |= 1 << (4 * (u % 16) + l)       # fixed R10 layout (4 b a row) at every NL
    lf, xf, mf = d / f"{name}.lines.hex", d / f"{name}.x.hex", d / f"{name}.m.hex"
    lf.write_text("".join(f"{w:0272x}\n" for w in lines))
    xf.write_text("".join(f"{w:0256x}\n" for w in xs))
    mf.write_text("".join(f"{w:016x}\n" for w in masks))
    return lf, xf, mf, len(lines)


def build(work, imut, pvmut, kvmut, variant="base", smut=0):
    vtag = ("" if variant == "base" and not smut else f"_{variant}_s{smut}") + ("" if NLN == 4 else f"_nl{NLN}")
    obj = work / f"obj_i{imut}_p{pvmut}_k{kvmut}{vtag}"
    exe = obj / "Vtb_hnx_att4"
    if SAFE_RESET:
        obj = Path(str(obj) + "_safe")
        exe = obj / exe.name
    if exe.exists():
        return exe
    cmd = [VERILATOR] + (["-DOT_HNX_ATT_SAFE_RESET", "-DOT_FP_DATA_NORST"] if SAFE_RESET else []) + ["--binary", "-j", "16", "-O1", "-CFLAGS", "-O1", "--x-assign", "fast", "-Wno-fatal", "-Wno-lint",
           "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "128", "--top-module", "tb_hnx_att4",
           f"-GIMUT={imut}", f"-GPVMUT={pvmut}", f"-GKVMUT={kvmut}", f"-GSMUT={smut}", f"-GNLN={NLN}"] + \
          [f"-G{k}={v}" for k, v in VARIANTS[variant].items()] + ["--Mdir", str(obj)] + [str(ROOT / s) for s in SRC]
    for attempt in range(2):                           # one retry on a precompiled-header race
        r = subprocess.run(cmd, capture_output=True, text=True)
        (work / f"build_i{imut}_p{pvmut}_k{kvmut}{vtag}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr)
        if r.returncode == 0:
            return exe
    raise SystemExit(f"build failed (see {work}/build_i{imut}_p{pvmut}_k{kvmut}{vtag}.log)")


def run_job(exe, rec, job, d):
    name, kind, kv4, rows, runs, nrun = job
    lf, xf, mf, nl = op_files(rec, job, d)
    want = sum(len(rr) for _, rr in runs.values()) if kind == "qk" else 8 * len(runs)
    args = [str(exe), f"+LINES={lf}", f"+X={xf}", f"+M={mf}", f"+NL={nl}", f"+ROWS={len(rows)}",
            f"+QK={1 if kind == 'qk' else 0}", f"+KV4={kv4}", f"+N8={0 if kv4 else len(rows)}", f"+WANT={want}"]
    r = subprocess.run(args, capture_output=True, text=True, timeout=3600)
    out = r.stdout + r.stderr
    (d / f"{name}.log").write_text(out)
    res = dict(name=name, kind=kind, kv4=kv4, union_rows=len(rows), lane_rows={l: len(rr) for l, (_, rr) in runs.items()},
               rc=r.returncode, fault="FAULT" in out)
    cyc = [ln for ln in out.splitlines() if ln.startswith("CYCLES")]
    if cyc:
        res["cycles"] = {k: int(v) for k, v in (t.split("=") for t in cyc[0].split()[1:])}
    mism, got_n, extra = 0, 0, 0
    nodes = {}
    if kind == "qk":
        seen = set()
        for ln in out.splitlines():
            if ln.startswith("SC "):
                _, l, o, hx = ln.split()
                l, o = int(l), int(o)
                got_n += 1
                if l not in runs or o >= len(runs[l][1]) or (l, o) in seen:
                    extra += 1
                    continue
                seen.add((l, o))
                a = runs[l][0]
                if int(hx, 16) != int(SB.bits32(rec["lanes"][l]["s"][a + o])):
                    mism += 1
        mism += extra + (want - len(seen))
    else:
        got = {l: np.full(HD, -1, dtype=np.int64) for l in runs}
        for ln in out.splitlines():
            if ln.startswith("PV "):
                _, l, b, k, hx = ln.split()
                l, b, k, v = int(l), int(b), int(k), int(hx, 16)
                got_n += 1
                if l not in runs:
                    extra += 1
                    continue
                for j in range(16):
                    idx = 8 * (16 * k + j) + b
                    if got[l][idx] >= 0:
                        extra += 1
                    got[l][idx] = (v >> (32 * j)) & 0xFFFFFFFF
        for l, (a, rr) in runs.items():
            ln = rec["lanes"][l]
            cs = SB.chunk_sums(ln["p"][a:a + len(rr)], ln["K"][a:a + len(rr)])
            node = A.pairwise([cs[i] for i in range(cs.shape[0])] + [np.zeros_like(cs[0])] * (nrun - cs.shape[0]))
            mm = int(np.sum(got[l] != SB.bits32(node).astype(np.int64)))
            mism += mm
            nodes[l] = got[l].astype(np.uint32).view(F).tolist() if mm == 0 else None
        mism += extra // 4
        want = 4 * want
    res.update(results=got_n, expected=want, mismatches=mism, nodes=nodes)
    res["pass"] = r.returncode == 0 and not res["fault"] and mism == 0 and got_n == want
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=1019)
    p.add_argument("--sigma", type=float, default=0.3)
    p.add_argument("--imut", type=int, default=0)
    p.add_argument("--pvmut", type=int, default=0)
    p.add_argument("--kvmut", type=int, default=0)
    p.add_argument("--variant", choices=sorted(VARIANTS), default="base", help="A1 merge variant")
    p.add_argument("--smut", type=int, default=0, help="shared-merge mutant (variant shared)")
    p.add_argument("--only", default="")
    p.add_argument("--p1", action="store_true", help="also run every lane alone on the same slice (P = 1 spans)")
    p.add_argument("--jobs", type=int, default=16)
    p.add_argument("--nl", type=int, default=3, help="query lanes = SM lanes P (P3 production default 3; 4 = old P4)")
    p.add_argument("--topk", type=int, default=512, help="top-k a lane (512 = DS; other values give partial last runs: "
                   "T mod 32 in (0,8] / (8,16] / (16,24] -> a last run of 1 / 2 / 3 chunks, the merge flush paths)")
    a = ap.parse_args(argv)
    global K, NLN
    K, NLN = a.topk, a.nl
    if not 1 <= NLN <= 4:
        ap.error("--nl 1..4")
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = make_record(a.seed, a.sigma)
    jobs = plan(rec)
    if a.p1:
        for l in range(NLN):
            jobs += plan(rec, single=l)
    if a.only:
        jobs = [j for j in jobs if j[0] in a.only.split(",")]
    if not jobs:
        ap.error("--only matched no job")
    exe = build(work, a.imut, a.pvmut, a.kvmut, a.variant, a.smut)
    vec = work / f"vec_k{K}_s{a.sigma}_i{a.imut}_p{a.pvmut}_k{a.kvmut}_{a.variant}_s{a.smut}"
    vec.mkdir(exist_ok=True)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: run_job(exe, rec, j, vec), jobs))
    mut = a.imut or a.pvmut or a.kvmut or a.smut
    summ = dict(nl=NLN, seed=a.seed, sigma=a.sigma, topk=K, imut=a.imut, pvmut=a.pvmut, kvmut=a.kvmut, variant=a.variant, smut=a.smut,
                verilator=VERILATOR, safe_reset=SAFE_RESET,
                union_lines=len(rec["union"]), lane_lines=[len(ln["rows"]) for ln in rec["lanes"]],
                ops=len(res), passed=sum(r["pass"] for r in res), wall_s=round(time.time() - t0, 1))
    main_jobs = [r for r in res if "_l" not in r["name"]]
    pv = [r for r in main_jobs if r["kind"] == "pv"]
    if pv and not a.only and all(r["pass"] for r in pv):
        ok = True
        for l in range(NLN):
            nodes = [np.asarray(r["nodes"][l], dtype=F) for r in sorted(pv, key=lambda r: int(r["name"][1:]))]
            ok &= bool(np.array_equal(SB.bits32(A.pairwise(nodes)), SB.bits32(rec["lanes"][l]["pv"])))
        summ["pv_cross_sm_merge_equals_att_pv_every_lane"] = ok
    if not a.only:
        summ["qk_scores_checked"] = sum(r["results"] for r in main_jobs if r["kind"] == "qk" and r["pass"])
    for kind in ("qk", "pv"):
        cy = [r for r in main_jobs if r["kind"] == kind and "cycles" in r]
        if cy:
            summ[f"{kind}_span_max"] = max(r["cycles"]["span"] for r in cy)
            summ[f"{kind}_union_rows_max"] = max(r["union_rows"] for r in cy)
        c1 = [r for r in res if "_l" in r["name"] and r["kind"] == kind and "cycles" in r]
        if c1:
            per_job = {}
            for r in c1:
                s = r["name"].split("_")[0][1:]
                per_job[s] = per_job.get(s, 0) + r["cycles"]["span"]
            summ[f"{kind}_p1_4lanes_span_max"] = max(per_job.values())
            summ[f"{kind}_p1_single_span_max"] = max(r["cycles"]["span"] for r in c1)
    summ["verdict"] = "PASS" if summ["passed"] == len(res) and summ.get("pv_cross_sm_merge_equals_att_pv_every_lane",
                                                                            True) else "FAIL"
    if mut:
        summ["mutant_detected"] = summ["verdict"] == "FAIL"
    for r in res:
        r.pop("nodes", None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, ops=res), indent=1))
    print(("PASS" if summ["verdict"] == "PASS" else "FAIL") + " HNX_ATT4 " + json.dumps(summ))
    return 0 if summ["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
