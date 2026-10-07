#!/usr/bin/env python3
"""Pipelined-issue (PQ) prototype measurement of the DS HBM SM element: ot_hbm_accel_sm_pq (rtl/hbm_accel/sm/) running
the busiest SM's op sequences of the matched HBM reference (tools/dshbm_matched_sm_seq.py: same ops, same golden, same
seed) with the PQ protocol (rtl/test/tb_hbm_accel_sm_pq_seq.sv): an independent op is loaded into the x-store ring and
posted while earlier ops still issue / drain; a DEPENDENT op (the first matvec after a collective or local op in the
program: its input comes from earlier results) waits until every earlier op completed, as in the serial bench.

Every result of every op is compared bit for bit with the golden; the tool exits nonzero on ANY mismatch, missing
result, fault or unconsumed line.  `--serial` flags every op dependent (the serial protocol on the PQ element).
`--expect-fail` inverts the exit status (the HAZ = 0 negative test must fail).

    python3 tools/dshbm_sm_pq_seq.py run --seq ar_l20 --nc 8 --active 1 --out R.json --workdir W
    python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 1 --haz 0 --expect-fail --out R.json
    python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 8 --smh --out R.json   # hierarchical element
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
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_matched_sm_seq as MS  # noqa: E402
import hdc_golden as G  # noqa: E402
import numpy as np  # noqa: E402

TB = "tb_hbm_accel_sm_pq_seq"
SRC = [s for s in MS.SRC if s != "rtl/test/tb_hbm_accel_sm_v_seq.sv"] + [
    "rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv", "rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv",
    "rtl/test/tb_hbm_accel_sm_pq_seq.sv"]
SMH_SRC = ["rtl/hbm_accel/sm/ot_hbm_accel_stack.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv",
           "rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv",
           "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv"]   # --smh: the hierarchical element (ot_hbm_accel_smh)
XDEPTH = MS.XDEPTH
NW = 10

# dependency flags of the matched sequences (1 = first matvec after a collective / local op in program.json layer 20;
# the routed gate/up run, the shared-expert pair and the 7 w2 matvecs are independent within their runs)
DEP_L20 = {"wq_a": 1, "wq_b": 1, "indexer.wq_b": 1, "wo_a": 1, "wo_b": 1, "router gate": 1, "expert slot 0 w1": 1,
           "expert slot 0 w2": 1}
# falling-D stress (independent ops, every retire-order transition the hazard check guards: BF16 -> block-dot, deep
# stack level -> shallow, multi-row after single-row, x reuse, ring wrap)
STRESS = [("s bf16 K5120 R1 (G10)", "bf16", 5120, 1, 1), ("s fp4 K2304 R2 (G2)", "fp4", 2304, 2, 1),
          ("s bf16 K512 R32 (G1)", "bf16", 512, 32, 1), ("s fp8 K8192 R2 (G8)", "fp8", 8192, 2, 1),
          ("s fp4 K5120 R1 (G3)", "fp4", 5120, 1, 1), ("s bf16 K5120 R3 (G10)", "bf16", 5120, 3, 1),
          ("s fp8 K1280 R16 (G2)", "fp8", 1280, 16, 1), ("s fp8 K1280 R2 reuse", "fp8", 1280, 2, 0),
          ("s bf16 K5120 R1 (G10) b", "bf16", 5120, 1, 1), ("s fp8 K2304 R2 (G3)", "fp8", 2304, 2, 1),
          ("s fp4 K2304 R2 (G2) b", "fp4", 2304, 2, 1), ("s bf16 K512 R32 (G1) b", "bf16", 512, 32, 1)]

# directed retire-order hazard (the HAZ = 0 negative must fail on the deeper smh pipeline): a deep-D op (BF16 G10:
# D = DBF + 4 SLAT = 39) followed at once by a SINGLE-ROW shallow one (block-dot G1: D = 0, 8 lines), whose row
# drains ~81 cycles after its last line: 15 + 8 + 81 < 120, inside the BF16 row's drain.  (sim15: with R8 / R4
# followers the eight interleaved rows finished with the op's last line, after the BF16 row, and HAZ = 0 passed.)
HAZSEQ = [("h bf16 K5120 R1 (G10)", "bf16", 5120, 1, 1), ("h fp8 K512 R1 (G1)", "fp8", 512, 1, 1),
          ("h bf16 K5120 R1 (G10) b", "bf16", 5120, 1, 1), ("h fp4 K512 R1 (G1)", "fp4", 512, 1, 1),
          ("h bf16 K5120 R2 (G10)", "bf16", 5120, 2, 1), ("h fp8 K512 R1 (G1) b", "fp8", 512, 1, 1)]


def seq_ops(name, serial):
    base = name[3:] if name.startswith("p6_") else name
    if base == "ar_l20" or base == "l20":
        ops = MS.WARM + MS.L20
        dep = [1] + [DEP_L20.get(t, 0) for t, *_ in MS.L20]
    elif base == "wg":
        ops = MS.WG
        dep = [1, 1, 0, 0]
    elif base == "other":
        ops = MS.OTHER
        dep = [1] * len(ops)
    elif base == "stress":
        ops = MS.WARM + STRESS
        dep = [1] + [0] * len(STRESS)
    elif base == "haz":
        ops = MS.WARM + HAZSEQ
        dep = [1] + [0] * len(HAZSEQ)
    else:
        raise SystemExit(f"unknown sequence {name}")
    if serial:
        dep = [1] * len(ops)
    return ops, dep


def cmd_run(a):
    import hdc_golden_v41 as V2
    V2.set_arith("chunk8")
    seqname = a.seq
    ops, dep = seq_ops(seqname, a.serial)
    rng = np.random.default_rng(20261005)
    d = Path(a.workdir) / (seqname + ("_serial" if a.serial else "") + f"_haz{a.haz}_g{a.g1asb}" +
                           (f"_smh_a{a.active}" if a.smh else ""))
    d.mkdir(parents=True, exist_ok=True)
    xb = -(-a.active * MS.XC // 2048)
    gens, seq, lines, xw = [], [], [], []
    fw = (a.nc * MS.XC + 2048 + 3) // 4
    resident, rbase, ptr = None, 0, 0
    for (tag, fmt, K, R, load), dp in zip(ops, dep):
        if load:
            g = MS.gen_op("v41_" + fmt, R, K, a.nc, rng)
            resident = g
            foot = g["Gn"] * g["c"]
            rbase, ptr = ptr, (ptr + foot) % XDEPTH
        else:
            assert resident is not None and resident["fmt"] == {"bf16": 0, "fp8": 1, "fp4": 2}[fmt] and \
                len(resident["X"][0]) == K, (tag, "a reused context needs the same vector, format and K")
            g = MS.gen_op("v41_" + fmt, R, K, a.nc, rng, X=resident["X"])
            assert g["Gn"] == resident["Gn"]
        gens.append(g)
        seq += [R, g["c"], g["Gn"], g["fmt"], len(g["lines"]), 1, load, g["Gn"] * g["c"], dp, rbase]
        lines += [f"{w:0272x}" for w in g["lines"]]
        if load:
            xw += [f"{w:0{fw}x}" for w in g["xw"]]
    (d / "seq.hex").write_text("\n".join(f"{v:08x}" for v in seq) + "\n")
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    params = dict(SUB=MS.SUB, LBS=MS.LBS, LSB=MS.LSB, NC=a.nc, XDEPTH=XDEPTH, RMAX=MS.RMAX, LEV=MS.LEV, XB=xb,
                  HAZ=a.haz, G1ASB=a.g1asb)
    if a.req_credit:
        params["REQCR"] = 1
    bdir = Path(a.workdir) / (f"build_pq_{a.sim}_nc{a.nc}_xb{xb}_haz{a.haz}_g{a.g1asb}" + ("_smh" if a.smh else "")
                              + ("_negflip" if a.neg_flip else "") + ("_muts1w" if a.mut_s1w else "") + ("_mutbf" if a.mut_bfdly else "")
                              + ("_rc" if a.req_credit else "") + ("_movf" if a.mut_reqovf else "") + ("_mleak" if a.mut_reqleak else ""))
    run, cmd = compile_bench(a.sim, params, bdir, a.build_jobs, smh=a.smh, neg=a.neg_flip, mut=a.mut_s1w, mutbf=a.mut_bfdly,
                             extra_defs=(["-DOT_SMH_MUT_REQOVF"] if a.mut_reqovf else []) + (["-DOT_SMH_MUT_REQLEAK"] if a.mut_reqleak else []))
    with (d / "runtime.log").open("w") as log:
        subprocess.run(run + [f"+DIR={d}", f"+NOPS={len(ops)}"] + (["+REQ_STALLS"] if a.req_stalls else []) + (["+TRACE", f"+TRACE_FROM={a.trace_from}", f"+TRACE_TO={a.trace_to}"] if a.trace else []), check=True, cwd=d,
                       stdout=log,
                       stderr=subprocess.STDOUT)
    res, meta, total, timeout = {}, {}, None, None
    for line in (d / "out.txt").read_text().splitlines():
        if line.startswith("# op"):
            t = line[2:].split()
            meta[int(t[1])] = {t[k]: int(t[k + 1]) for k in range(2, len(t) - 1, 2)}
        elif line.startswith("# total_cycles"):
            total = int(line.split()[-1])
        elif line.startswith("#"):
            if "TIMEOUT" in line:
                timeout = line[2:]
        else:
            o, r, h = line.split()
            res.setdefault(int(o), {})[int(r)] = h
    rows, bad = [], 0
    for i, ((tag, fmt, K, R, load), g, dp) in enumerate(zip(ops, gens, dep)):
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
        m = meta.get(i, {})
        exact = mism == 0 and len(got) == R and m.get("fault", 1) == 0 and m.get("consumed") == m.get("lines") \
            and m.get("results") == R
        bad += 0 if exact else 1
        rows.append(dict(op=i, tag=tag, fmt=fmt, K=K, rows=R, groups=g["Gn"], x_load=bool(load), dep=bool(dp),
                         x_base=seq[i * NW + 9], x_addresses=g["Gn"] * 8 if load else 0, lines=len(g["lines"]),
                         mismatches=mism, results=len(got), exact=exact, rtl=m))
    status = "pass" if bad == 0 and timeout is None else "fail"
    out = dict(schema="opentallas.dshbm.sm_pq_seq.v1", seq=seqname, serial=a.serial, haz=a.haz, g1_asbuilt=a.g1asb,
               element=("ot_hbm_accel_smh (hierarchical: front / identical leaf tiles / column back ends; pipelined "
                        "issue, G1 select by the producing column)" if a.smh else
                        "ot_hbm_accel_sm_pq (pipelined issue) on ot_hbm_accel_sm_v ENABLE=1 leaves"), nc=a.nc,
               active_columns=a.active, x_beats_per_address=xb, simulator=a.sim, bench_clock_ns=1.0, status=status,
               mismatching_ops=bad, total_cycles=total, timeout=timeout, ops=rows, req_stalls=a.req_stalls,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               build_command=cmd, source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                                                 for s in SRC + (SMH_SRC if a.smh else []) + ["tools/dshbm_sm_pq_seq.py",
                                                                 "tools/dshbm_matched_sm_seq.py",
                                                                 "tools/rtl_gpu_sm_exact.py"]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        m = r["rtl"]
        print(f"{r['op']:2d} {r['tag'][:30]:30s} {r['fmt']:4s} K{r['K']:5d} R{r['rows']:3d} dep {int(r['dep'])} "
              f"load0 {m.get('t_load0', -1):6d} post {m.get('t_post', -1):6d} first_line {m.get('t_firstline', -1):6d} "
              f"last_line {m.get('t_lastline', -1):6d} done {m.get('t_done', -1):6d} exact {r['exact']}")
    print(status.upper(), "total_cycles", total, a.out)
    ok = status == "pass"
    if a.expect_fail:
        print("EXPECTED FAIL:", "yes" if not ok else "NO (negative test did not fail)")
        return 0 if not ok else 1
    return 0 if ok else 1


def compile_bench(sim, params, outdir, jobs, smh=False, neg=False, mut=False, mutbf=False, extra_defs=()):
    src = SRC + (SMH_SRC if smh else [])
    defs = (["-DOT_SMH"] if smh else []) + (["-DOT_SMH_NEG_FLIP"] if neg else []) + (["-DOT_SMH_MUT_S1W"] if mut else []) + (["-DOT_SMH_MUT_BFDLY"] if mutbf else []) + list(extra_defs)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if sim == "verilator":
        exe = outdir / ("V" + TB)
        cmd = ["verilator", "--binary", "--timing", "-O2", "-Wno-fatal", "--top-module", TB, "--Mdir", str(outdir),
               "-j", str(jobs), *defs, *[f"-G{k}={v}" for k, v in params.items()], *[str(ROOT / s) for s in src]]
        if not exe.is_file():
            with (outdir / "build.log").open("w") as log:
                subprocess.run(cmd, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        return [str(exe)], cmd
    exe = outdir / "sim.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", TB] + defs + [f"-P{TB}.{k}={v}" for k, v in params.items()] + \
        [str(ROOT / s) for s in src]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return ["vvp", "-n", str(exe)], cmd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("run",))
    ap.add_argument("--seq", required=True, help="ar_l20 | p6_l20 | wg | p6_wg | other | p6_other | stress | p6_stress")
    ap.add_argument("--nc", type=int, default=8)
    ap.add_argument("--active", type=int, default=1)
    ap.add_argument("--haz", type=int, default=1)
    ap.add_argument("--g1asb", type=int, default=0, help="1 = as-built leaf G1 select (negative test)")
    ap.add_argument("--serial", action="store_true")
    ap.add_argument("--smh", action="store_true", help="DUT = the hierarchical element ot_hbm_accel_smh")
    ap.add_argument("--expect-fail", action="store_true")
    ap.add_argument("--mut-s1w", action="store_true", help="--smh negative control: compile-time RTL mutant, bit 3 of "
                    "the front's s1 line register inverted (+define+OT_SMH_MUT_S1W in ot_hbm_accel_smh.sv)")
    ap.add_argument("--mut-bfdly", action="store_true", help="--smh: compile-time mutant, BF16 column output 64 cycles "
                    "late with the issue's DBF raised to match (+define+OT_SMH_MUT_BFDLY): HAZ = 1 must pass, HAZ = 0 fail")
    ap.add_argument("--neg-flip", action="store_true", help="negative control: bit 3 of every returned line flipped at the response port (+define+OT_SMH_NEG_FLIP)")
    ap.add_argument("--trace", action="store_true", help="issue / retire trace in <workdir>/<seq>/runtime.log")
    ap.add_argument("--req-stalls", action="store_true", help="deterministic hub request backpressure (+REQ_STALLS)")
    ap.add_argument("--req-credit", action="store_true", help="--smh: request port with ready latency 2 (REQCR = 1); the "
                    "bench receiver loses any beat sent without its ready two cycles earlier")
    ap.add_argument("--mut-reqovf", action="store_true", help="REQCR negative control: beats shown without permission")
    ap.add_argument("--mut-reqleak", action="store_true", help="REQCR negative control: one request in 64 popped, never shown")
    ap.add_argument("--trace-from", type=int, default=0)
    ap.add_argument("--trace-to", type=int, default=0)
    ap.add_argument("--sim", choices=("verilator", "iverilog"), default="verilator")
    ap.add_argument("--build-jobs", type=int, default=8)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    a.workdir = a.workdir or tempfile.mkdtemp(prefix="smpq_")
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
