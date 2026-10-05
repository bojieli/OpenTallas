#!/usr/bin/env python3
"""DS-ROM field SPINE redesign (Claude:dsrom-field-spine, 2026-10-04): the ROM-field matvec nodes re-measured on the
TIMING-CLOSED spine rtl/v41die/ot_v41_spine_pqc_w17w10 (vehicle ot_v41_fieldtop_pqc_w17w10), for BOTH configurations
of the DS-ROM decision gate, bit-exact against the golden at the 1M token:

  baseline  PQ = 0 (one op in flight, the pinned sequencing), S81 canonical placement (the as-built plan): every phase
            of every node, every region, one op a run -- the as-built measurement (tools/dsrom_1m_field.py, record
            results/rtl/dsrom_1m_allmeasured_20261004/field.json) with the pinned spine replaced by the closed one,
            composed by the as-built rule (sum over the node's phases of go -> idle + 1, + go -> last row write of the
            last; each phase at the max over the die's regions; S81 floorplan wire stages per phase).
  pq        PQ = 1 (pipelined phases), S81 + R93 placement (tools/dsrom_recovery_field.py `variant`): every
            multi-phase node, every region, its phases issued back to back (tools/dsrom_recovery_field.py vehicle and
            composition: spine issue rule measured on every consecutive op pair, wire once a node); single-phase
            nodes one op a run on the same build and placement.

    python3 tools/dsrom_field_spine.py build  --work W --pq 0|1 [--jobs 16]
    python3 tools/dsrom_field_spine.py run    --work W --plan-dir P --mode phase|node [--single-only] [--jobs 48]
                                              [--layers ..] [--regions ..] [--only-nodes ..] [--sample N]
                                              [--positions N]   (MTP self-test: every op with N positions)
    python3 tools/dsrom_field_spine.py record --work W --plan-dir P --config baseline|pq [--record OUT]
    python3 tools/dsrom_field_spine.py lever  --config baseline|pq --record REC [--ssff SSFF] [--verdict ADOPT]

The runs, images, golden and checks are tools/dsrom_recovery_field.py's (run_one / node_image) and the test bench is
its rtl/test/dsrom_sys/tb_dsrom_recovery_field_pq.cpp (the closed fieldtop has the same ports); only the spine, the
fieldtop and the build parameter PQ differ.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_field as F1  # noqa: E402
import dsrom_recovery_field as F  # noqa: E402
import hdc_golden_v41 as G  # noqa: E402

TOP = "ot_v41_fieldtop_pqc_w17w10"
DIE = [ROOT / f"rtl/v41die/{n}.sv" for n in ("ot_v41_retn_w17w10", "ot_v41_pair_pq_ld", "ot_v41_pair_pq_w17w10",
                                             "ot_v41_field_pq_w17w10", "ot_v41_spine_pqc_w17w10", TOP)] + [ROOT / "rtl/v41rom/ot_v41_kreg.sv"]
SOURCES = sorted(set(F.RTL + DIE + F1.ROMS + [F.TB, Path(__file__)] + F.TOOLS))
OUT = ROOT / "results/rtl/dsrom_field_spine_20261004"
LEVERS = ROOT / "results/rtl/dsrom_recovery_20261004/levers"
CLK = F.CLK


def sha(p) -> str:
    return F1.sha(p)


def cmd_build(a):
    out = (a.work / "build").resolve()
    out.mkdir(parents=True, exist_ok=True)
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([F1.VERILATOR, "-V"], text=True)).group(1)
    params = ["-GFAST=1", "-GPP=1", "-GBP=0", f"-GNP={F.NP}", f"-GR={F.NR}", f"-GNBF={F.NBF}", f"-GPHW={F.PHW}",
              f"-GVAW={F.VAW}", f"-GPQ={a.pq}", f"-GGAP={a.gap}", f"-GGUARD={a.guard}", f"-GGSLACK={a.gslack}"]
    mdir = out / "pq"
    steps = []
    for name, cmd in (
            ("verilate", [F1.VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
                          "--top-module", TOP, "--prefix", "Vpq", "--Mdir", str(mdir), *params,
                          *map(str, DIE + F1.ROMS + F.RTL)]),
            ("make", ["make", "-C", str(mdir), "-f", "Vpq.mk", f"-j{a.jobs}", "Vpq__ALL.a", "OPT_FAST=-O2",
                      "OPT_SLOW=-O1"]),
            ("link", ["g++", "-std=c++20", "-O2", f"-DNR={F.NR}", f"-DVAW={F.VAW}", f"-I{vroot}/include",
                      f"-I{vroot}/include/vltstd", f"-I{mdir}", str(F.TB), str(mdir / "Vpq__ALL.a"),
                      f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                      "-pthread", "-o", str(out / "tb")])):
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append(dict(name=name, seconds=round(time.time() - t0, 1), returncode=p.returncode))
        print(name, steps[-1], flush=True)
        if p.returncode:
            raise SystemExit(f"{name} failed: {(p.stdout + p.stderr)[-3000:]}")
    (out / "build.json").write_text(json.dumps(dict(
        steps=steps, params=params, pq=a.pq, top=TOP, tb_sha256=sha(out / "tb"),
        simulator=subprocess.check_output([F1.VERILATOR, "--version"], text=True).strip(),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in SOURCES}), indent=1) + "\n")
    return 0


# ------------------------------------------------------------------------------------------------ runs
def groups_all(plan):
    """{(layer, node, stage): [phases in plan order]} -- every node (as-built grouping)."""
    g = {}
    for ph in plan["phases"]:
        g.setdefault((ph["layer"], ph["node"], ph["stage"]), []).append(ph)
    return g


def phase_key(key, i):
    L, n, s = key
    return (L, f"{n}#p{i}", s)


def tasks_for(a, plan):
    rb, bfs = plan["region_bounds"], set(plan["bf_sites"])
    g = groups_all(plan)
    if a.layers:
        g = {k: v for k, v in g.items() if k[0] in {int(x) for x in a.layers.split(",")}}
    if a.only_nodes:
        g = {k: v for k, v in g.items() if k[1] in set(a.only_nodes.split(","))}
    if a.single_only:
        g = {k: v for k, v in g.items() if len(v) == 1}
    regsel = set(map(int, a.regions.split(","))) if a.regions else None
    tasks = []
    work, pdir = str(a.work.resolve()), str(a.plan_dir.resolve())
    for key, phs in g.items():
        if a.mode == "phase":
            for i, ph in enumerate(phs):
                for reg in ph["regions"]:
                    if regsel is None or reg in regsel:
                        tasks.append((work, pdir, phase_key(key, i), [ph], reg, rb, bfs, a.keep, a.positions))
        else:
            if len(phs) < 2:
                continue
            for reg in sorted({r for ph in phs for r in ph["regions"]}):
                if regsel is None or reg in regsel:
                    tasks.append((work, pdir, key, [ph for ph in phs if reg in ph["regions"]], reg, rb, bfs,
                                  a.keep, a.positions))
    tasks.sort(key=lambda t: (F.gname(t[2]), t[4]))
    if a.sample:
        step = max(1, len(tasks) // a.sample)
        tasks = tasks[::step][:a.sample]
    if not a.force:
        rdir = "runs" if a.positions == 1 else f"runs_np{a.positions}"
        tasks = [t for t in tasks if not (a.work / rdir / F.gname(t[2]) / f"r{t[4]:03d}" / "result.json").exists()]
    return tasks


def cmd_run(a):
    plan = json.loads((a.plan_dir / "plan.json").read_text())
    tasks = tasks_for(a, plan)
    print(f"{len(tasks)} runs ({a.mode})", flush=True)
    bad = 0
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for i, r in enumerate(ex.map(F.run_one, tasks, chunksize=2)):
            bad += not r["pass_"]
            if not r["pass_"] or i % 200 == 0:
                print(i, r["group"], r["region"], "PASS" if r["pass_"] else "FAIL", r["rows"], r["node"],
                      r["tail"], r["first_mismatch"], flush=True)
    print("failed", bad, flush=True)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ record
def load(work, key, reg):
    f = work / "runs" / F.gname(key) / f"r{reg:03d}" / "result.json"
    return json.loads(f.read_text()) if f.exists() else None


def phase_stats(work, key, i, ph):
    rs = [load(work, phase_key(key, i), reg) for reg in ph["regions"]]
    complete = all(r is not None for r in rs)
    rs = [r for r in rs if r]
    ok = complete and bool(rs) and all(r["pass_"] for r in rs)
    gi = [r["node"]["idle"] - r["node"]["go"] for r in rs if r["node"]]
    gw = [r["node"]["last_w"] - r["node"]["go"] for r in rs if r["node"] and r["node"]["last_w"] >= 0]
    return dict(phase=ph["phase"], regions=len(ph["regions"]), regions_run=len(rs), exact=ok,
                rows_checked=sum(r["rows"] for r in rs), rows_mismatched=sum(r["mismatched"] + r["extra"] for r in rs),
                go_to_idle_cycles=max(gi) if gi and complete else None,
                go_to_last_row_cycles=max(gw) if gw and complete else None,
                region_spread_go_to_last_row=[min(gw), max(gw)] if gw else None)


def cmd_record(a):
    work, pdir = a.work.resolve(), a.plan_dir.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    build = json.loads((work / "build" / "build.json").read_text())
    assert build["pq"] == (1 if a.config == "pq" else 0), build["pq"]
    fp = json.loads((ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json").read_text())["trunk_stages"]
    W_S81 = 2 * fp["stages_at_504"]["field_one_way"] - F1.BST_IN_VEHICLE
    asb = json.loads(F.ASBUILT.read_text())
    asb_nodes = {(n["node"], n["die_stage"]): n for n in asb["nodes"]}
    old_pq = json.loads((F.REC_DIR / "field_pq.json").read_text())
    old_pq_nodes = {(n["node"], n["die_stage"]): n for n in old_pq["nodes"]}
    groups = groups_all(plan)
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    k_rule = None
    if a.config == "pq":
        runs = {}
        for key, phs in multi.items():
            regs = sorted({r for ph in phs for r in ph["regions"]})
            runs[key] = (regs, [load(work, key, reg) for reg in regs])
        k_rule = F.spine_rule([[r for r in rs if r] for regs, rs in runs.values()])
        print("spine rule", k_rule)
    out_nodes, allx = [], True
    for key, phs in sorted(groups.items()):
        L, node, st = key
        mname = node if node.startswith("E1.") else f"L{L}.{node}"
        ab = asb_nodes.get((mname, st))
        if a.config == "pq" and len(phs) > 1:
            regs, rs = runs[key]
            complete = all(r is not None for r in rs)
            rs = [r for r in rs if r]
            exact = complete and all(r["pass_"] for r in rs)
            c = F.compose(phs, rs, k_rule) if exact else None
            meas = c["cycles"] if c else None
            wire = W_S81
            n_rows = sum(r["rows"] for r in rs)
            nbad = sum(r["mismatched"] + r["extra"] for r in rs)
            rule = "PQ: die composition of the region runs with the measured spine issue rule; S81 wire once a node"
            detail = dict(composition=c, regions_run=len(rs), regions=len(regs))
        else:
            pst = [phase_stats(work, key, i, ph) for i, ph in enumerate(phs)]
            exact = all(p["exact"] for p in pst)
            meas = (sum(p["go_to_idle_cycles"] + 1 for p in pst[:-1]) + pst[-1]["go_to_last_row_cycles"]) \
                if exact and all(p["go_to_last_row_cycles"] is not None for p in pst) else None
            wire = W_S81 * len(phs)
            n_rows = sum(p["rows_checked"] for p in pst)
            nbad = sum(p["rows_mismatched"] for p in pst)
            rule = ("as-built rule: sum over the node's sequential phases (go -> idle + 1) + go -> last VM row write "
                    "of the last phase, each phase at the max over the die's regions; S81 wire per phase")
            detail = dict(phases_detail=pst)
        allx &= exact
        tot = meas + wire if meas is not None else None
        out_nodes.append(dict(
            node=mname, layer=L, die_stage=st, phases=[ph["phase"] for ph in phs], exact=exact, rows_checked=n_rows,
            rows_mismatched=nbad, measured_cycles=meas, measured_definition=rule,
            wire_stage_cycles_s81_floorplan=wire, total_cycles=tot,
            total_us_s81_floorplan_wire=tot / CLK * 1e6 if tot is not None else None,
            asbuilt_measured_cycles=ab["measured_cycles"] if ab else None,
            asbuilt_total_us_s81_floorplan_wire=ab["total_us_s81_floorplan_wire"] if ab else None,
            old_pq_total_cycles=(old_pq_nodes.get((mname, st)) or {}).get("total_cycles"),
            model_us=ab["model_us"] if ab else None, **detail))
    summary = {}
    for n in out_nodes:
        summary.setdefault(n["node"], []).append(n)
    node_summary = []
    for name, ns in summary.items():
        top = max(ns, key=lambda n: n["total_cycles"] or 0)
        asum = next((x for x in asb["node_summary"] if x["node"] == name), {})
        node_summary.append(dict(node=name, layer=top["layer"], dies=[n["die_stage"] for n in ns],
                                 total_cycles=top["total_cycles"],
                                 total_us_s81_floorplan_wire=top["total_us_s81_floorplan_wire"],
                                 us=top["total_us_s81_floorplan_wire"],
                                 asbuilt_us=asum.get("total_us_s81_floorplan_wire"), model_us=asum.get("model_us"),
                                 rows_checked=sum(n["rows_checked"] for n in ns), exact=all(n["exact"] for n in ns)))
    rec = dict(
        schema="opentallas.dsrom.field_spine.v1", config=a.config, status="pass" if allx else "fail",
        claim_boundary=("RTL measurement (Verilator, 2-state) of the S81 rank-0 dies' ROM-field matvec nodes on the "
                        "timing-closed spine ot_v41_spine_pqc_w17w10, one region at full shape, every region, bit-exact "
                        "vs the golden; die-level node time composed from the region runs; S81 floorplan wire stages "
                        "(504 um a stage) added analytically."),
        vehicle=dict(top=f"{TOP} (PQ={build['pq']}, flat)", NP_slots=F.NP, R=F.NR, NBF_slots=F.NBF, PHW=F.PHW,
                     VAW=F.VAW, FAST=1, PP=1, BP=0, BST=F1.BST_IN_VEHICLE, build_params=build["params"]),
        placement=("S81 canonical (as-built plan)" if a.config == "baseline" else
                   "S81 canonical + R93 re-placement (tools/dsrom_recovery_field.py variant)"),
        spine_rule=k_rule, wire_stages_s81_floorplan_per_crossing=W_S81,
        plan_dir=str(pdir), plan_sha256=sha(pdir / "plan.json"), x_sha256=sha(pdir / "x.npz"),
        golden=dict(token_position=1048575, context=1048576, experts=plan["experts"], gold_vm=plan["gold_vm"],
                    arith="chunk8 (tools/hdc_golden_v41)"),
        node_summary=node_summary, nodes=out_nodes, simulator=build["simulator"], tb_sha256=build["tb_sha256"],
        build_source_sha256=build["source_sha256"],
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
        git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1) + "\n")
    for n in node_summary:
        print(f"{n['node']:24s} {n['total_cycles']} cyc {n['us'] and round(n['us'], 4)} us (as-built "
              f"{n['asbuilt_us'] and round(n['asbuilt_us'], 4)}) exact {n['exact']}")
    print("status", rec["status"])
    return 0 if allx else 1


def cmd_lever(a):
    """Lever record (opentallas.dsrom-recovery.lever.v1) over every S81 graph node the record measures, with the
    as-built adapter's representative-layer mapping (tools/dsrom_1m_allmeasured_adapters.field_rows)."""
    import dsrom_1m_allmeasured_adapters as AD
    import dsrom_1m_measure as M
    rec = json.loads(a.record.read_text())
    ssff = json.loads(a.ssff.read_text()) if a.ssff and a.ssff.exists() else None
    g, _, _ = M.s58_graph()
    rows = AD.field_rows(g, rec)
    tag = "closed baseline spine (PQ=0)" if rec["config"] == "baseline" else "closed PQ spine (PQ=1, S81+R93)"
    nodes = {}
    for name, (sec, src, cls, _mod) in rows.items():
        nodes[name] = dict(us=round(sec * 1e6, 6), cls=cls, source=f"{tag}: " + src)
    out = dict(
        schema="opentallas.dsrom-recovery.lever.v1", lever=a.lever, verdict=a.verdict,
        exact=rec["status"] == "pass", ss_ff=ssff, nodes=nodes,
        measurement=dict(record=str(a.record.resolve().relative_to(ROOT)), record_sha256=sha(a.record),
                         config=rec["config"], vehicle=rec["vehicle"]["top"], placement=rec["placement"],
                         node_summary=[{k: n[k] for k in ("node", "dies", "total_cycles", "us", "asbuilt_us",
                                                          "rows_checked", "exact")} for n in rec["node_summary"]],
                         rtl=sorted(k for k in rec["source_sha256"] if k.startswith(("rtl/", "physical/")))),
        note=a.note)
    out_path = a.lever_out or (LEVERS / f"{a.lever}.json")
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(len(nodes), "nodes ->", out_path)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("build", "run", "record", "lever"))
    ap.add_argument("--work", type=Path)
    ap.add_argument("--plan-dir", type=Path)
    ap.add_argument("--pq", type=int, default=0)
    ap.add_argument("--gap", type=int, default=12)
    ap.add_argument("--guard", type=int, default=180)
    ap.add_argument("--gslack", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--mode", choices=("phase", "node"), default="phase")
    ap.add_argument("--single-only", action="store_true")
    ap.add_argument("--layers", default="")
    ap.add_argument("--regions", default="")
    ap.add_argument("--only-nodes", default="")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--positions", type=int, default=1, help="run: MTP positions per op (np = N - 1 self-test, not recorded)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--config", choices=("baseline", "pq"), default="baseline")
    ap.add_argument("--record", type=Path)
    ap.add_argument("--ssff", type=Path)
    ap.add_argument("--lever", default="field_spine")
    ap.add_argument("--lever-out", type=Path)
    ap.add_argument("--verdict", default="ADOPT")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    if a.record is None:
        a.record = OUT / f"field_{a.config}.json"
    G.set_arith("chunk8")
    return {"build": cmd_build, "run": cmd_run, "record": cmd_record, "lever": cmd_lever}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
