#!/usr/bin/env python3
"""Exact bench of the ROUTED DeepSeek-V4.1 ROM q-element ot_v41_rom_elem_q_qxpq_w10 (S81, x1,280 a die) at its routed
parameters (PQ 1, QM 5, QS 5, QX 10, ...), with a parameter probe, and its mutant (s81-qelem 2026-10-13).

The closure job's own bench (bench_qs5_source_bound) is a source-bound receipt of the QX gate tools/dsrom_qx_exact.py,
which instantiates the module at PQ = 0 only (rtl/test/tb_dsrom_qx_exact.sv QX_DUT_PQ0); the route is PQ = 1.  The PQ = 1
bit-exact harness is tools/dsrom_combined_l20.py `field --cfg pq1_q10`: the S81 L20 field (every node, every region of
the rank-0 die at the golden 1M token, released-checkpoint rows) on the closed PQ spine with the element inside the
pair FILE SWAP rtl/v41die/swap/ot_v41_pair_pq_w17w10_qelem.sv, every row checked bit for bit against
tools/hdc_golden_v41.  This wrapper runs that harness UNCHANGED from a source tree at the routed commit and adds:

  * rtl/test/dsrom_sys/ot_v41_q_param_probe.sv (bind, no RTL edit): every elaborated element instance prints its
    parameters in every run; `summary` requires every printed line to equal the route's --param list (read from
    the route's launch receipt) and every run to carry the lines;
  * the identity of the element RTL: sha256 of every --source of the route's receipt, in the benched tree;
  * one verdict line and return code: `--expect pass` (0 failed runs, none missing, probe as routed) or
    `--expect fail` (the mutant: caught = at least one run of the sample is not bit-exact; counts are recorded).

    OT_PQQ_QM=5 OT_PQQ_QS=5 OT_PQQ_DEFINES=QP_CHECK,QT_CHECK python3 tools/dsrom_qelem_cl/pq1_routed_bench.py \
        --work W/exact --plan-pq PLANV --receipt RECEIPT --expect pass [--jobs 48]
    OT_PQQ_QM=5 OT_PQQ_QS=5 OT_PQQ_DEFINES=QS5_MUTANT_WEN python3 tools/dsrom_qelem_cl/pq1_routed_bench.py \
        --work W/mut_wen --plan-pq PLANV --receipt RECEIPT --expect fail --sample 96
PLANV: tools/dsrom_1m_field.py plan + extract, then tools/dsrom_recovery_field.py variant (S81 + R93).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
PROBE = ROOT / "rtl/test/dsrom_sys/ot_v41_q_param_probe.sv"
TOP = "ot_v41_rom_elem_q_qxpq_w10"
CFG = "pq1_q10"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def routed(receipt: Path):
    """(parameters, sources) of the closed route from its launch receipt (driver_args)."""
    a = json.loads(receipt.read_text())["driver_args"]
    assert a[a.index("--top") + 1] == TOP, "receipt is not the q-element route"
    par = dict(x.split("=") for i, x in enumerate(a) if i and a[i - 1] == "--param")
    par = {k: int(v) for k, v in par.items()}
    par.setdefault("FRONT_PAR", 0)           # not passed by the route: the module default
    return par, [x for i, x in enumerate(a) if i and a[i - 1] == "--source"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--plan-pq", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--expect", choices=("pass", "fail"), required=True)
    ap.add_argument("--jobs", type=int, default=48)
    ap.add_argument("--layers", default="20")
    ap.add_argument("--sample", type=int, default=0, help="runs per mode (0 = every run; the mutant uses a sample)")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    import dsrom_combined_l20 as C
    import dsrom_field_spine as FS
    par, srcs = routed(a.receipt)
    work = a.work.resolve() / f"field_{CFG}"
    work.mkdir(parents=True, exist_ok=True)
    cfg = C.FIELD_CFGS[CFG]
    C._qelem_swap(cfg, work)
    FS.DIE = list(FS.DIE) + [PROBE]                       # the bind file: elaborated with the vehicle
    FS.SOURCES = sorted(set(FS.SOURCES) | {PROBE})
    env = {k: os.environ.get(k, "") for k in ("OT_PQQ_QM", "OT_PQQ_QS", "OT_PQQ_QW", "OT_PQQ_DEFINES")}
    rcs = {}
    if not a.summary_only:
        if not (work / "build" / "tb").exists():
            FS.cmd_build(argparse.Namespace(work=work, pq=cfg["pq"], gap=cfg["gap"], guard=cfg["guard"],
                                            gslack=cfg["gslack"], jobs=min(a.jobs, 32)))
        for mode in ("phase", "node"):
            rcs[mode] = FS.cmd_run(argparse.Namespace(
                work=work, plan_dir=a.plan_pq, mode=mode, single_only=False, layers=a.layers, regions="",
                only_nodes="", sample=a.sample, keep=False, positions=1, force=False, jobs=a.jobs))
    # ---- summary
    runs = sorted((work / "runs").glob("*/r*/result.json"))
    n_pass = n_fail = rows = bad_rows = 0
    probe_lines, probe_bad, noprobe, tails = 0, [], 0, {}
    want0 = dict(par)
    seen = set()
    for rj in runs:
        r = json.loads(rj.read_text())
        n_pass += bool(r["pass_"])
        n_fail += not r["pass_"]
        rows += r["rows"]
        bad_rows += r["mismatched"] + r["extra"]
        t = r.get("tail") or [""]
        t = t[0] if isinstance(t, list) else str(t)
        key = " ".join(t.split()[:1 if r["pass_"] else 2]) or "(no output)"
        tails[key] = tails.get(key, 0) + 1
        got = [ln for ln in (rj.parent / "sim.log").read_text().splitlines() if ln.startswith("QPROBE ")]
        noprobe += not got
        for ln in got:
            probe_lines += 1
            kv = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", ln.split(" inst=")[0])}
            lvl, bf = kv.pop("lvl"), kv.pop("BF16")
            seen.add(json.dumps(dict(kv, lvl=lvl, BF16=bf), sort_keys=True))
            if kv != want0 or bf != 0:
                probe_bad.append(ln)
    per_run = probe_lines / len(runs) if runs else 0
    probe_ok = bool(runs) and not probe_bad and not noprobe and probe_lines > 0
    plan = json.loads((a.plan_pq / "plan.json").read_text())
    exp_runs = None
    if not a.sample:
        g = {k: v for k, v in FS.groups_all(plan).items() if str(k[0]) in a.layers.split(",")}
        exp_runs = sum(len(ph["regions"]) for v in g.values() for ph in v) + \
            sum(len({r for ph in v for r in ph["regions"]}) for v in g.values() if len(v) >= 2)
    if a.expect == "pass":
        ok = probe_ok and n_fail == 0 and n_pass > 0 and (exp_runs is None or n_pass == exp_runs)
    else:
        ok = probe_ok and n_fail > 0                  # caught: at least one run of the sample is not bit-exact
    build = json.loads((work / "build" / "build.json").read_text())
    rec = dict(
        schema="opentallas.dsrom.qelem_pq1_routed_bench.v1", block=TOP, expect=a.expect,
        verdict=("PASS" if n_fail == 0 and n_pass else "FAIL"), as_expected=ok,
        harness="tools/dsrom_combined_l20.py field --cfg pq1_q10 (tools/dsrom_field_spine.py build/run, unchanged) + parameter probe",
        env=env, defines=(work / "qelem_defines.sv").read_text().split("\n"), vehicle_params=build["params"],
        simulator=build["simulator"], tb_sha256=build["tb_sha256"], layers=a.layers, sample=a.sample,
        runs=len(runs), runs_expected=exp_runs, runs_pass=n_pass, runs_fail=n_fail, rows_checked=rows,
        rows_mismatched_or_extra=bad_rows, fail_tails=tails,
        probe=dict(file=str(PROBE.relative_to(ROOT)), sha256=sha(PROBE), routed_params=par, lines=probe_lines,
                   instances_per_run=per_run, runs_without_probe=noprobe, lines_not_routed=len(probe_bad),
                   first_not_routed=probe_bad[:3], distinct_elaborations=sorted(seen), ok=probe_ok),
        routed_sources_sha256={s: sha(ROOT / s) for s in srcs if (ROOT / s).exists()},
        swap_pair_sha256=sha(C.SWAP_PAIR), plan_dir=str(a.plan_pq), plan_sha256=sha(a.plan_pq / "plan.json"),
        x_sha256=sha(a.plan_pq / "x.npz"), run_rc=rcs)
    out = a.out or (a.work.resolve() / "summary.json")
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print("QELEM_PQ1_PROBE", "OK" if probe_ok else "BAD", f"lines={probe_lines} per_run={per_run:g} not_routed={len(probe_bad)} "
          f"runs_without={noprobe}", " ".join(f"{k}={v}" for k, v in sorted(par.items())))
    print(f"QELEM_PQ1_BENCH {rec['verdict']} expect={a.expect} defines={env['OT_PQQ_DEFINES'] or '-'} QM={env['OT_PQQ_QM']} "
          f"QS={env['OT_PQQ_QS']} runs={len(runs)}/{exp_runs if exp_runs is not None else 'sample'} pass={n_pass} "
          f"fail={n_fail} rows={rows} bad_rows={bad_rows} tails={tails}")
    print("QELEM_PQ1_GATE", "AS_EXPECTED" if ok else "NOT_AS_EXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
