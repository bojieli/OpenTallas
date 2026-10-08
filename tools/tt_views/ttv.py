#!/usr/bin/env python3
"""TT-VIEWS dependency chains (OWNER 2026-10-07: launch every remaining TT route; macro views first).

A VIEW is <name>.lef + <name>_{ss,ff,tt}.lib from ONE routed database.  Views live in a local store
(STORE/<name>/, with PRODUCED.json) and are pushed to every host at TTV/<name>/ (TTV = the first of
/srv/opentallas-scratch2/scratch/claude/ttviews, /srv/opentallas-scratch/claude/ttviews that the host has).
Detached shell processes run these; no agent polls.

  ttv.py produce --name N (--host H | --loop-job J) --orfs DIR [--view-src DIR] [--ready DIR] [--interface-sdc F]
                 [--mv NAME ...] [--wait-file F]
      waits for the route (loop job: event 'route done (rc=0)'; or --wait-file on the host), then on the host:
      --ready DIR   : DIR already holds the 4 files (a job's own SS/FF/TT export) -> pull them;
      --view-src DIR: DIR holds LEF/SS/FF from hbm_fmax_attn_abstract.py of the same route -> add TT (view_export.py
                      --corners tt, same --interface-sdc), pull;
      neither       : view_export.py ss,ff,tt + LEF from the route.   DIR / --orfs / --wait-file may use {RUN} (loop run dir).
      --mv NAME: sub-macro view from the store (pushed to the host first; its _tt.lib is read in the TT pass).
  ttv.py queue --spec FILE --view REPO_DIR=NAME [...] [--hosts-prefer ...]
      waits for every NAME in the store, pushes them to the spec's hosts, prefixes the calibrate / route commands with
      ttv_install.sh (copies the 4 files into {SRC}/REPO_DIR, overwriting the job commit's view so LEF and all three
      Liberty corners come from one route), and drops the spec into the closure-loop inbox.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORE = Path("/home/ubuntu/claude-takeover-20261007/tt-views/store")
INBOX = Path("/tmp/claude-review-20261003/closure_jobs")
LOOPJOBS = Path.home() / ".local/state/closure_loop/jobs"
LOOPCODE = Path("/home/ubuntu/wt-codex-closure-reliability/tools/closure_loop/closure_loop.py")
ROOTS = ["/srv/opentallas-scratch2/scratch/claude", "/srv/opentallas-scratch/claude"]
TTV_FIND = ("$(ls -d /srv/opentallas-scratch2/scratch/claude/ttviews/ttv_install.sh "
            "/srv/opentallas-scratch/claude/ttviews/ttv_install.sh 2>/dev/null | head -1)")
POLL = 300


def log(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def sh(host, cmd, timeout=None, **kw):
    try:
        return subprocess.run(["ssh", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", host, cmd],
                              capture_output=True, text=True, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([], 255, "", "timeout")


def ttv_root(host):
    """the host's TTV dir (created); same choice rule as ttv_install.sh lookup: scratch2 first."""
    r = sh(host, "for r in " + " ".join(ROOTS) + "; do [ -d $r ] && mkdir -p $r/ttviews && echo $r/ttviews && exit 0; done; exit 1",
           timeout=60)
    if r.returncode:
        raise RuntimeError(f"{host}: no scratch root ({r.stderr.strip()[:200]})")
    return r.stdout.split()[0]


def push_install(host, root):
    subprocess.run(["scp", "-q", str(HERE / "ttv_install.sh"), str(HERE / "view_export.py"), f"{host}:{root}/"], check=True)


def push_view(host, name):
    root = ttv_root(host)
    push_install(host, root)
    subprocess.run(["rsync", "-a", f"{STORE / name}/", f"{host}:{root}/{name}/"], check=True)
    return root


def loop_state(job):
    p = LOOPJOBS / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def wait_loop_route(job):
    """block until the loop job's route stage finished rc=0; return (host, run)."""
    t0 = time.time()
    while True:
        st = loop_state(job)
        if st:
            ev = st.get("events", [])
            done = [e for e in ev if "route done (rc=0)" in e]
            if done and st.get("host") and st.get("run"):
                return st["host"], st["run"]
            if time.time() - t0 > 6 * 86400:
                raise SystemExit(f"{job}: no 'route done (rc=0)' after 6 days (status {st.get('status')})")
        time.sleep(POLL)


def produce(a):
    out = STORE / a.name
    if (out / "PRODUCED.json").exists():
        log(f"{a.name}: already in the store")
        return
    host, run = a.host, ""
    if a.loop_job:
        log(f"{a.name}: waiting for loop job {a.loop_job} route")
        host, run = wait_loop_route(a.loop_job)
    sub = lambda s: s.replace("{RUN}", run) if s else s
    orfs, view_src, ready, wait_file = sub(a.orfs), sub(a.view_src), sub(a.ready), sub(a.wait_file)
    # the route must have its 6_final odb/spef (+ the optional marker) on the host
    probe = (f"b=$(ls -d {orfs}/results/asap7/*/base 2>/dev/null | head -1); [ -n \"$b\" ] && [ -s $b/6_final.odb ] && "
             f"[ -s $b/6_final.spef ]" + (f" && ls {wait_file} >/dev/null 2>&1" if wait_file else "")
             + (f" && [ -s {ready}/{a.name}_tt.lib ] && [ -s {ready}/{a.name}.lef ]" if ready else "")
             + (f" && [ -s {view_src}/{a.name}.lef ] && [ -s {view_src}/{a.name}_ss.lib ]" if view_src else ""))
    t0 = time.time()
    while sh(host, probe, timeout=120).returncode:
        if time.time() - t0 > 6 * 86400:
            raise SystemExit(f"{a.name}: route products never appeared on {host}")
        log(f"{a.name}: waiting on {host} for {orfs} {wait_file or ''} {ready or ''}")
        time.sleep(POLL)
    root = ttv_root(host)
    push_install(host, root)
    w = f"{root}/_work/{a.name}"
    if ready:
        src = ready
    else:
        mvs = []
        for m in a.mv:
            if not (STORE / m / "PRODUCED.json").exists():
                log(f"{a.name}: waiting for sub-macro view {m}")
                while not (STORE / m / "PRODUCED.json").exists():
                    time.sleep(POLL)
            mvs.append(f"{push_view(host, m)}/{m}")
        cmd = f"rm -rf {w} && mkdir -p {w}/view && "
        corners = "ss,ff,tt"
        if view_src:
            cmd += f"cp {view_src}/{a.name}.lef {view_src}/{a.name}_ss.lib {view_src}/{a.name}_ff.lib {w}/view/ && "
            cmd += f"(cp {view_src}/abstract.json {w}/view/ 2>/dev/null; true) && "
            corners = "tt"
        cmd += (f"python3 {root}/view_export.py --orfs-dir {orfs} --name {a.name} --out {w}/view --corners {corners} "
                f"--tmp-dir {w}/tmp" + (f" --interface-sdc {a.interface_sdc}" if a.interface_sdc else "")
                + "".join(f" --macro-view {m}" for m in mvs) + f" > {w}/export.log 2>&1")
        log(f"{a.name}: exporting on {host}: {cmd}")
        r = sh(host, cmd)
        if r.returncode:
            tail = sh(host, f"tail -5 {w}/export.log").stdout
            raise SystemExit(f"{a.name}: export failed on {host}: {tail}")
        src = f"{w}/view"
    out.mkdir(parents=True, exist_ok=True)
    files = [f"{a.name}.lef"] + [f"{a.name}_{c}.lib" for c in ("ss", "ff", "tt")]
    subprocess.run(["scp", "-q"] + [f"{host}:{src}/{f}" for f in files] + [str(out) + "/"], check=True)
    for extra in ("abstract.json", "export.json", "export_tt.tcl", "export_tt.log"):
        subprocess.run(["scp", "-q", f"{host}:{src}/{extra}", str(out) + "/"], capture_output=True)
    rec = dict(name=a.name, host=host, orfs=orfs, src=src, loop_job=a.loop_job, run=run,
               method="ready (job export)" if ready else ("view_export tt on the existing LEF/SS/FF" if view_src
                                                          else "view_export ss,ff,tt + LEF"),
               interface_sdc=a.interface_sdc, mv=a.mv, at=datetime.now().isoformat(timespec="seconds"),
               files={f: hashlib.sha256((out / f).read_bytes()).hexdigest() for f in files})
    (out / "PRODUCED.json").write_text(json.dumps(rec, indent=1) + "\n")
    log(f"{a.name}: PRODUCED {rec['method']} from {host}:{src}")


def queue(a):
    spec = json.loads(Path(a.spec).read_text())
    views = [v.split("=", 1) for v in a.view]
    for _, n in views:
        if not (STORE / n / "PRODUCED.json").exists():
            log(f"{spec['name']}: waiting for view {n}")
        while not (STORE / n / "PRODUCED.json").exists():
            time.sleep(POLL)
    if (LOOPJOBS / f"{spec['name']}.json").exists() or (INBOX / f"{spec['name']}.json").exists():
        log(f"{spec['name']}: already in the loop / inbox; not re-queued")
        return
    hosts = []
    for h in spec["hosts"]:
        try:
            for _, n in views:
                push_view(h, n)
            hosts.append(h)
        except Exception as e:  # unreachable host: drop it from this job's list
            log(f"{spec['name']}: host {h} skipped ({e})")
    if not hosts:
        raise SystemExit(f"{spec['name']}: no host took the views")
    spec["hosts"] = hosts
    inst = f"bash {TTV_FIND} {{SRC}} " + " ".join(f"{n}={d}" for d, n in views) + " && "
    st = spec["stages"]
    for k in ("calibrate", "route"):
        if isinstance(st.get(k), dict) and st[k].get("cmd") and "ttv_install.sh" not in st[k]["cmd"]:
            st[k]["cmd"] = inst + st[k]["cmd"]
    prov = {n: json.loads((STORE / n / "PRODUCED.json").read_text()) for _, n in views}
    spec["purpose"] += (" | TT-VIEWS: macro views (LEF + SS/FF/TT Liberty from one routed db each) installed into the "
                        "snapshot by ttv_install.sh: " + "; ".join(
                            f"{d} <- {p['host']}:{p['src']} ({p['method']})" for d, (n, p) in
                            zip([d for d, _ in views], prov.items())))
    tmp = Path(a.spec).with_suffix(".queued.json")
    tmp.write_text(json.dumps(spec, indent=1) + "\n")
    v = subprocess.run([sys.executable, str(LOOPCODE), "validate", str(tmp)], capture_output=True, text=True)
    if v.returncode:
        raise SystemExit(f"{spec['name']}: loop validate failed: {v.stdout[-500:]} {v.stderr[-500:]}")
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / f"{spec['name']}.json").write_text(tmp.read_text())
    log(f"{spec['name']}: QUEUED (inbox) on hosts {hosts} with views {[n for _, n in views]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("produce")
    p.add_argument("--name", required=True)
    p.add_argument("--host")
    p.add_argument("--loop-job")
    p.add_argument("--orfs", required=True)
    p.add_argument("--view-src")
    p.add_argument("--ready")
    p.add_argument("--interface-sdc")
    p.add_argument("--mv", action="append", default=[])
    p.add_argument("--wait-file")
    q = sp.add_parser("queue")
    q.add_argument("--spec", required=True)
    q.add_argument("--view", action="append", required=True)
    a = ap.parse_args()
    if a.cmd == "produce":
        if not (a.host or a.loop_job):
            ap.error("--host or --loop-job")
        produce(a)
    else:
        queue(a)


if __name__ == "__main__":
    main()
