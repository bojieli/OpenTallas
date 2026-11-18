#!/usr/bin/env python3
"""bind_fast: the fast path around a strict die bind (BIND-SPEED-1118).  Plan checks (strict bind + LATCHECK + G0) cost 45-80 min; most
of that was spent finding what a minute of reading finds, running pass 1 only to rebuild R8, serial kit-rtl, and an oversubscribed host.

    bind_fast.py host   [--tree DIR] [--hosts h1,h2,..] [--min-mem-gb 64]       least-loaded host (that has the tree): prints `BEST <host>`
    bind_fast.py precheck --plan P --asbuilt M [--out BINDOUT] [--tree .] [--skip CLASS ..]
                                                       minutes: plan_gate_pre with FIXEDCYC / ROWSINK / MODULES / TOOLSTALE (+ SCHEMA INPUT TOOLS);
                                                       ROWSINK / MODULES need BINDOUT/asbuilt.json (the elab output, `bind.py elab`)
    bind_fast.py r8     --plan P --asbuilt M --out BINDOUT --r8-out NEW_TABLE      the head of the bind (no emit) -> BINDOUT/bus_groups.json +
                                                       the derived land_r8 table; then run the ONE full strict bind on NEW_TABLE
    bind_fast.py kits   --plan P --asbuilt M --out BINDOUT --types t1,t2,.. [-j N]   `bind.py kit-rtl` per type, N at a time (default 6)
    bind_fast.py phases -- <bind.py arguments>          bind_phases.py: wall / cpu per bind stage (OUT/bind_phases.json)

Order for a plan event:  host -> (bind elab) -> precheck -> r8 -> ONE strict bind (+ kits) -> LATCHECK -> G0.  Run `bind_fast.py` from the bind tree
root (cwd = tree), like bind.py.  Exit 0 ok, 1 findings / failures, 2 usage.
"""
import argparse
import concurrent.futures as cf
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_HOSTS = ("epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "intel1", "intel2")
PROBE = ('read l1 l5 l15 _ < /proc/loadavg; echo "L $l1 $l5"; echo "N $(nproc)"; '
         "awk '/MemAvailable/{print \"M\", int($2/1048576)}' /proc/meminfo; "
         'if [ -n "$1" ]; then test -d "$1" && echo "T 1" || echo "T 0"; fi; df -BG --output=avail /srv/opentallas-scratch2 2>/dev/null | tail -1 | sed "s/^ */D /;s/G//"')


def probe(host, tree):
    # the probe script is the command's stdin (so no `ssh -n`); the tree path is quoted into the remote command line
    import shlex
    cmd = ["timeout", "30", "ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host,
           "bash -s -- " + shlex.quote(tree or "")]
    try:
        r = subprocess.run(cmd, input=PROBE, capture_output=True, text=True, timeout=40)
    except (subprocess.TimeoutExpired, OSError) as e:
        return dict(host=host, error=str(e))
    d = dict(host=host)
    for ln in r.stdout.splitlines():
        k, _, v = ln.partition(" ")
        if k == "L":
            a, b = v.split()
            d["l1"], d["l5"] = float(a), float(b)
        elif k == "N":
            d["ncpu"] = int(v)
        elif k == "M":
            d["mem_gb"] = int(v)
        elif k == "T":
            d["has_tree"] = v == "1"
        elif k == "D":
            d["disk_gb"] = int(v)
    if "ncpu" not in d:
        d["error"] = (r.stderr or "no output").strip()[:80]
    return d


def cmd_host(a):
    hosts = [h for h in (a.hosts or os.environ.get("OT_BIND_HOSTS", "")).split(",") if h] or list(DEFAULT_HOSTS)
    with cf.ThreadPoolExecutor(len(hosts)) as ex:
        rows = list(ex.map(lambda h: probe(h, a.tree), hosts))
    ok = []
    for d in rows:
        if "error" in d:
            print(f"{d['host']:8s} UNREACHABLE {d['error']}")
            continue
        d["load_per_cpu"] = round(max(d["l1"], d["l5"]) / d["ncpu"], 2)
        why = []
        if a.tree and not d.get("has_tree"):
            why.append("no tree")
        if d.get("mem_gb", 0) < a.min_mem_gb:
            why.append(f"mem {d.get('mem_gb')} GB < {a.min_mem_gb}")
        if d.get("disk_gb", 1 << 30) < a.min_disk_gb:
            why.append(f"disk {d.get('disk_gb')} GB < {a.min_disk_gb}")
        print(f"{d['host']:8s} load {d['l1']:6.1f}/{d['l5']:6.1f} of {d['ncpu']:3d} cpu = {d['load_per_cpu']:5.2f}  mem {d.get('mem_gb')} GB  "
              f"disk {d.get('disk_gb')} GB  tree {d.get('has_tree')}" + ("  SKIP: " + "; ".join(why) if why else ""))
        if not why:
            ok.append(d)
    if not ok:
        print("BEST none (no host with the tree, memory and disk; run `ot-lane-clone` / src_manifest replicate on the least loaded host)")
        return 1
    best = min(ok, key=lambda d: (d["load_per_cpu"], -d.get("mem_gb", 0)))
    print(f"BEST {best['host']}")
    return 0


def cmd_precheck(a):
    sys.path.insert(0, str(HERE))
    import plan_gate_pre as G
    out = a.out
    elab = out if out and (Path(out) / "asbuilt.json").is_file() else None
    # like bind: ROWS (rows of other lanes need a passing rows proof) and GEOM (new station-in-core overlaps) only against a baseline plan
    skip = tuple(a.skip) + (() if a.baseline_plan else ("ROWS", "GEOM"))
    fs = G.check(a.tree, a.plan, asbuilt=a.asbuilt, baseline=a.baseline_plan, skip=skip, elab_dir=elab, ref_tools=a.ref_tools)
    fails = [x for x in fs if x.startswith("FAIL")]
    for x in fs:
        print(x)
    if not elab:
        print("bind_fast precheck: no OUT/asbuilt.json (elab not run): ROWSINK and the elab half of MODULES skipped")
    print(f"BIND-PRECHECK {'FAIL' if fails else 'PASS'} findings={len(fails)}")
    return 1 if fails else 0


def _bind(args, tree):
    return subprocess.run([sys.executable, "-I", "-B", str(Path(tree) / "tools/die_plan/bind.py")] + args, cwd=tree)


def cmd_r8(a):
    args = ["r8-prepass", a.plan, "--out", a.out, "--r8-out", a.r8_out]
    if a.asbuilt:
        args += ["--asbuilt", a.asbuilt]
    return _bind(args, a.tree).returncode


def cmd_kits(a):
    types = [t for t in a.types.replace(" ", ",").split(",") if t]
    log_dir = Path(a.out) / "kit_rtl_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    def one(t):
        cmd = [sys.executable, "-I", "-B", str(Path(a.tree) / "tools/die_plan/bind.py"), "kit-rtl", a.plan, "--out", a.out, "--type", t]
        if a.asbuilt:
            cmd += ["--asbuilt", a.asbuilt]
        with open(log_dir / f"{t}.log", "w") as f:
            return t, subprocess.run(cmd, cwd=a.tree, stdout=f, stderr=subprocess.STDOUT).returncode
    bad = []
    with cf.ThreadPoolExecutor(max(1, a.j)) as ex:
        for t, rc in ex.map(one, types):
            print(f"KIT_RTL {'ok' if rc == 0 else 'FAIL rc=%d' % rc} {t}", flush=True)
            if rc:
                bad.append(t)
    print(f"KIT_RTL_DONE {len(types) - len(bad)}/{len(types)} ok" + (f" failed: {','.join(bad)}" if bad else ""))
    return 1 if bad else 0


def cmd_phases(a):
    return subprocess.run([sys.executable, "-I", "-B", str(HERE / "bind_phases.py"), "--"] + a.rest, cwd=a.tree).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("host")
    h.add_argument("--tree")
    h.add_argument("--hosts")
    h.add_argument("--min-mem-gb", type=int, default=64)
    h.add_argument("--min-disk-gb", type=int, default=100)
    p = sub.add_parser("precheck")
    p.add_argument("--plan", required=True)
    p.add_argument("--asbuilt")
    p.add_argument("--out")
    p.add_argument("--tree", default=".")
    p.add_argument("--baseline-plan")
    p.add_argument("--ref-tools", default="auto")
    p.add_argument("--skip", action="append", default=[])
    r = sub.add_parser("r8")
    r.add_argument("--plan", required=True)
    r.add_argument("--asbuilt")
    r.add_argument("--out", required=True)
    r.add_argument("--r8-out", required=True)
    r.add_argument("--tree", default=".")
    k = sub.add_parser("kits")
    k.add_argument("--plan", required=True)
    k.add_argument("--asbuilt")
    k.add_argument("--out", required=True)
    k.add_argument("--types", required=True)
    k.add_argument("-j", type=int, default=6)
    k.add_argument("--tree", default=".")
    f = sub.add_parser("phases")
    f.add_argument("--tree", default=".")
    f.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    if a.cmd == "phases" and a.rest and a.rest[0] == "--":
        a.rest = a.rest[1:]
    return dict(host=cmd_host, precheck=cmd_precheck, r8=cmd_r8, kits=cmd_kits, phases=cmd_phases)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
