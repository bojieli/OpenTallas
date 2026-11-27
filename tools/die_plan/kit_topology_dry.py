#!/usr/bin/env python3
"""kit_topology_dry: run the kit_rtl + kit_topology stages on EVERY type of a candidate plan, before the plan is adopted
(C-ISTATION-PACKED-DELAY, COORD FLOW-1047 item 1; S81-INT-R3-PARAM 11-27).

The publish gate's dry_gen ran the whole kit chain on ONE pilot item.  An adopted plan could therefore hold types whose kit_topology stage
dies (S81 c085: t27 / t36 and 7 more leaves, `packed delay does not preserve exact face epoch/data connection`: kit_relay_depth rewrote the
packed receiver D to rdk_*_out), found only when each type was launched.  This tool runs, per type, exactly the two stages the wave runs
before synthesis and stops there (no gen, no preflight, no P&R):

    bind.py kit-rtl PLAN --out BIND_OUT --asbuilt AB --type T --src-tree TREE --kit WORK/T/rtl      (real kit RTL: narrow buses, dead
    kit_topology.py prepare-stations PLAN T WORK/T/rtl --native-plan PLAN --asbuilt AB               inputs, relay_depth, reset trees)

  python3 -I tools/die_plan/kit_topology_dry.py run --plan P --bind-out B --asbuilt AB --tree TREE --work DIR
        [--jobs N] [--tools DIR] [--types T ...] [--type-timeout S] [--out RESULT.json]          exit 0 PASS, 1 FAIL (type list), 2 unusable input

Types: every partition_types key that is a bound type of BIND_OUT (bind_report.json; exact key, or a `key__...` variant), has a topology
(kit_topology.has_topology) and is not a hard core without RTL.  Others are listed under `skipped` with the reason, never silently.
Reuse (paid artifacts): a type whose inputs are unchanged since a PASS is not re-run: key = sha256 of its plan type JSON, the plan reset /
asbuilt clock sections, the bound module's bytes, the as-built manifest and this tool dir's kit_rtl/kit_topology generators; the cache lives
in WORK/cache (PASS records only; a FAIL is always re-run).  Fail closed: a type whose stage cannot run (timeout, crash) is a FAIL of that type.
Parallel: --jobs workers (default $OT_TOPO_DRY_JOBS, else 8); each kit-rtl admits itself through ot-run, so memory is the bound."""
import argparse
import concurrent.futures as CF
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_ID = "opentallas.kit_topology_dry.v1"
GENERATORS = ("kit_topology.py", "kit_istations.py", "kit_relay_depth.py", "bind.py")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def tool_sha(tools=HERE):
    h = hashlib.sha256()
    for n in GENERATORS:
        p = Path(tools) / n
        h.update(n.encode() + (_sha(p.read_bytes()).encode() if p.is_file() else b"-"))
    return h.hexdigest()


def bound_key(report_types, tn):
    """-> key of tn in the bind report: exact, else the first `tn__...` variant, else None"""
    if tn in report_types:
        return tn
    return next((k for k in sorted(report_types) if k.startswith(tn + "__")), None)


def select_types(raw, report, wanted=None, has_topology=None):
    """-> (types to run, {type: skip reason}).  has_topology(raw, t) -> bool (kit_topology.has_topology)."""
    rt = (report or {}).get("types") or {}
    run, skipped = [], {}
    for tn in sorted(raw.get("partition_types") or {}):
        if wanted and tn not in wanted:
            continue
        if bound_key(rt, tn) is None:
            skipped[tn] = "not a bound type of the bind (hard core / planned / no RTL)"
        elif has_topology is not None and not has_topology(raw, tn):
            skipped[tn] = "no topology (kit_topology has nothing to prepare)"
        else:
            run.append(tn)
    return run, skipped


def cache_key(raw, tn, report_types, bind_out, asbuilt, tsha):
    k = bound_key(report_types, tn)
    mod = (report_types.get(k) or {}).get("module")
    bound = Path(bind_out) / "rtl" / f"{mod}.sv"
    parts = [json.dumps((raw.get("partition_types") or {}).get(tn), sort_keys=True), json.dumps(raw.get("reset"), sort_keys=True),
             _sha(bound.read_bytes()) if bound.is_file() else "no-bound-rtl",
             _sha(Path(asbuilt).read_bytes()) if asbuilt and Path(asbuilt).is_file() else "no-asbuilt", tsha, tn]
    return _sha("\x00".join(parts).encode())


def _run(cmd, cwd, timeout):
    """-> (rc, output tail).  A timeout or a crash is rc != 0 (fail closed)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or ""))
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout:.0f} s"
    except OSError as e:
        return 127, f"{type(e).__name__}: {e}"


def _why(txt):
    lines = [ln for ln in txt.strip().splitlines() if ln.strip()]
    err = [ln for ln in lines if "Error" in ln or "KIT_TOPOLOGY" in ln or "kit-rtl" in ln.lower() and "fail" in ln.lower()]
    return (err[-1] if err else (lines[-1] if lines else "no output"))[:400]


def check_type(tn, plan, bind_out, asbuilt, tree, work, tools=HERE, timeout=3600, runner=None):
    """kit-rtl then prepare-stations for one type -> dict(type, verdict, stage, why, seconds)"""
    runner = runner or _run
    t0 = time.time()
    kit = Path(work) / "types" / tn / "rtl"
    if kit.parent.exists():
        import shutil
        shutil.rmtree(kit.parent)                   # own scratch dir of this tool only
    kit.parent.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    kr = [py, "-I", str(Path(tools) / "bind.py"), "kit-rtl", plan, "--out", bind_out, "--type", tn, "--src-tree", tree, "--kit", str(kit)]
    if asbuilt:
        kr += ["--asbuilt", asbuilt]
    rc, txt = runner(kr, tree, timeout)
    if rc:
        return dict(type=tn, verdict="FAIL", stage="kit_rtl", why=_why(txt), seconds=round(time.time() - t0, 1))
    kt = [py, "-I", str(Path(tools) / "kit_topology.py"), "prepare-stations", plan, tn, str(kit), "--native-plan", plan]
    if asbuilt:
        kt += ["--asbuilt", asbuilt]
    rc, txt = runner(kt, tree, timeout)
    if rc:
        return dict(type=tn, verdict="FAIL", stage="kit_topology", why=_why(txt), seconds=round(time.time() - t0, 1))
    return dict(type=tn, verdict="PASS", stage="kit_topology", seconds=round(time.time() - t0, 1))


def run_all(plan, bind_out, asbuilt, tree, work, tools=HERE, jobs=None, wanted=None, timeout=3600, runner=None, has_topology=None):
    """-> result dict (verdict PASS | FAIL, failed [{type, stage, why}], counts, seconds)"""
    t0 = time.time()
    raw = json.loads(Path(plan).read_text())
    try:
        report = json.loads((Path(bind_out) / "bind_report.json").read_text())
    except (OSError, ValueError) as e:
        return dict(schema=SCHEMA_ID, verdict="FAIL", why=f"bind_report.json of {bind_out} unreadable: {type(e).__name__}", failed=[])
    if has_topology is None:
        sys.path.insert(0, str(tools))
        import kit_topology
        ab = asbuilt or None
        has_topology = lambda r, t: kit_topology.has_topology(r, t, ab)
    types, skipped = select_types(raw, report, wanted, has_topology)
    tsha = tool_sha(tools)
    cdir = Path(work) / "cache"
    cdir.mkdir(parents=True, exist_ok=True)
    rtypes = report.get("types") or {}
    jobs = max(1, int(jobs or os.environ.get("OT_TOPO_DRY_JOBS") or 8))
    results, cached = [], 0

    def one(tn):
        key = cache_key(raw, tn, rtypes, bind_out, asbuilt, tsha)
        cf = cdir / (key + ".json")
        if cf.is_file():
            return dict(type=tn, verdict="PASS", stage="cache", seconds=0.0), True
        r = check_type(tn, plan, bind_out, asbuilt, tree, work, tools, timeout, runner)
        if r["verdict"] == "PASS":
            tmp = cf.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(dict(type=tn, tool_sha=tsha, t=time.time())))
            os.replace(tmp, cf)
        return r, False

    with CF.ThreadPoolExecutor(max_workers=jobs) as ex:
        for r, hit in ex.map(one, types):
            results.append(r)
            cached += bool(hit)
    failed = [dict(type=r["type"], stage=r["stage"], why=r.get("why", "")) for r in results if r["verdict"] != "PASS"]
    return dict(schema=SCHEMA_ID, verdict="FAIL" if failed else "PASS", n_types=len(types), n_pass=len(types) - len(failed),
                n_cached=cached, n_skipped=len(skipped), failed=failed, skipped=skipped, jobs=jobs, tool_sha=tsha,
                seconds=round(time.time() - t0, 1), slowest=sorted(((r["seconds"], r["type"]) for r in results), reverse=True)[:5])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--plan", required=True)
    r.add_argument("--bind-out", required=True)
    r.add_argument("--asbuilt")
    r.add_argument("--tree", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--jobs", type=int)
    r.add_argument("--tools", default=str(HERE), help="tools/die_plan dir whose bind.py / kit_topology.py run (default: this file's dir)")
    r.add_argument("--types", nargs="*")
    r.add_argument("--type-timeout", type=float, default=3600)
    r.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        res = run_all(a.plan, a.bind_out, a.asbuilt, a.tree, a.work, tools=a.tools, jobs=a.jobs, wanted=set(a.types or []) or None, timeout=a.type_timeout)
    except (OSError, ValueError, KeyError) as e:
        print(f"kit_topology_dry: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"TOPOLOGY-DRY {res['verdict']} types {res.get('n_types')} pass {res.get('n_pass')} cached {res.get('n_cached')} "
          f"skipped {res.get('n_skipped')} jobs {res.get('jobs')} {res.get('seconds')} s")
    for f in res["failed"]:
        print(f"FAIL TOPOLOGY-DRY {f['type']} [{f['stage']}] {f['why']}")
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
