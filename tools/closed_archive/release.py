#!/usr/bin/env python3
"""Archive-then-release (coordinator 10-11 ~22:00, overrides read-only for VERIFIED-ARCHIVED CLOSED job files only).

  release.py pipeline HOST [--par N]   archive every CLOSED job on HOST, generate its GDS if missing, then release
  release.py release JOB...            release already-archived jobs

Release deletes on the fleet host ONLY:
  * files under the job's run dir whose sha256 equals a sha256 recorded in the job's archive manifest (content-identical
    to an archived, integrity-tested copy) -- record/ and the run-dir skeleton (logs, reports, json, sdc) are kept;
  * the synced repo copy: run/src (only when src/SOURCE_COMMIT == the job's commit) and run/bench_src*.
Never: a non-CLOSED job, a run dir shared with a non-terminal job, a run dir with a live process, a .keep dir, a path
that origin/main receipts or any live job's spec name (/srv/... references), a viz-elem export still running.
Every release writes <run>/ARCHIVE_RELEASED.json (what went, where the archive is) and manifest.release.
"""
import concurrent.futures as cf
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402
import gen_gds  # noqa: E402

REPO = "/home/ubuntu/OpenTallas"
TERMINAL = {"CLOSED", "CANCELLED", "NEEDS_RTL", "NEEDS_HUMAN", "NEEDS_BUDGET", "REFUSED", "INVALID", "FLOORPLAN_MARGIN",
            "PREROUTE_MARGIN", "SMOKE_OK"}

GENERIC = {"orfs", "work", "base", "routes", "cl", "eco", "eco-r2", "eco-r3", "pass1", "pass2", "pass3", "route",
           "results", "logs", "reports", "asap7"}

REMOTE = r'''
import hashlib, json, os, shutil, stat, sys
a = json.loads(os.environ["OT_REL"])
R = a["run"].rstrip("/")
if not os.path.isdir(R):
    print("REL_JSON" + json.dumps(dict(freed=0, note="no run dir"))); sys.exit(0)
for p in os.listdir("/proc"):
    if not p.isdigit():
        continue
    try:
        cwd = os.readlink("/proc/%s/cwd" % p)
        argv = open("/proc/%s/cmdline" % p, "rb").read().decode(errors="replace")
    except OSError:
        continue
    if cwd == R or cwd.startswith(R + "/") or (R + "/") in argv or argv.endswith(R) or (R + "\0") in argv:
        print("REL_JSON" + json.dumps(dict(freed=0, note="live pid %s" % p))); sys.exit(0)
if os.path.exists(os.path.join(R, ".keep")):
    print("REL_JSON" + json.dumps(dict(freed=0, note=".keep"))); sys.exit(0)
prot = [r.rstrip("/") for r in a["protect"]]
prot += [dp for dp, dn, fn in os.walk(R) if ".keep" in fn]
isprot = lambda p: any(p == r or p.startswith(r + "/") for r in prot)
anc = lambda p: any(r.startswith(p + "/") for r in prot)
sums = set(a["sha"])
sizes = set(a["sizes"])
EXT = (".odb", ".def", ".spef", ".v", ".gds", ".lib", ".lef", ".oas")
def blocks(p):
    try:
        st = os.lstat(p)
        return st.st_blocks * 512 if stat.S_ISREG(st.st_mode) else 0
    except OSError:
        return 0
gone, freed, kept_prot, denied = [], 0, 0, []
for dp, dn, fn in os.walk(R):
    rel = os.path.relpath(dp, R)
    top = rel.split("/")[0]
    if top in ("src", "record") or top.startswith("bench_src") or isprot(dp):
        dn[:] = []
        continue
    for f in fn:
        p = os.path.join(dp, f)
        if not f.endswith(EXT) or os.path.islink(p):
            continue
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        if sz < (1 << 20) or sz not in sizes:
            continue
        h = hashlib.sha256()
        try:
            with open(p, "rb") as fh:
                for b in iter(lambda: fh.read(8 << 20), b""):
                    h.update(b)
            if h.hexdigest() in sums:
                b = blocks(p)
                os.unlink(p)
                freed += b
                gone.append(os.path.relpath(p, R))
        except OSError:
            denied.append(os.path.relpath(p, R))
def rm_tree(p):
    b = sum(blocks(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs)
    shutil.rmtree(p, ignore_errors=True)
    return b
for top in sorted(os.listdir(R)):
    tp = os.path.join(R, top)
    if not os.path.isdir(tp) or os.path.islink(tp) or isprot(tp) or anc(tp):
        continue
    if top == "src":
        try:
            ok = bool(a["commit"]) and open(os.path.join(tp, "SOURCE_COMMIT")).read().strip() in (a["commit"], a["commit"][:12])
        except OSError:
            ok = False
        if ok:
            freed += rm_tree(tp); gone.append("src/")
    elif top.startswith("bench_src"):
        freed += rm_tree(tp); gone.append(top + "/")
marker = dict(by="closed-archive-1011", at=a["at"], archive=a["archive"], deleted=gone, freed_bytes=freed,
              denied=denied, rule="deleted only files content-identical (sha256) to the verified archive copy, plus the synced repo copy")
try:
    old = json.load(open(os.path.join(R, "ARCHIVE_RELEASED.json")))
    marker["deleted"] = sorted(set(old.get("deleted", [])) | set(gone))
    marker["freed_bytes"] += old.get("freed_bytes", 0)
except (OSError, ValueError):
    pass
json.dump(marker, open(os.path.join(R, "ARCHIVE_RELEASED.json"), "w"), indent=1)
print("REL_JSON" + json.dumps(dict(freed=freed, n=len(gone), denied=len(denied))))
'''

_PROT = {}


def protect_refs():
    """/srv/... paths named by origin/main receipts and by every live (non-terminal) job's spec/state"""
    if _PROT.get("t", 0) > time.time() - 1800:
        return _PROT["refs"]
    out = subprocess.run(["git", "-C", REPO, "grep", "-h", "-o", "-I", "-E", r"/srv/[A-Za-z0-9_./+-]+", "origin/main"],
                         capture_output=True, text=True, timeout=900).stdout
    refs = {x.split(":", 1)[-1].rstrip("/.") for x in out.split()}
    for f in glob.glob(os.path.join(archive.JOBS, "*.json")):
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            continue
        if d.get("status") in TERMINAL or str(d.get("status", "")).startswith("EARLY_FAIL"):
            continue
        txt = json.dumps(d.get("spec", {}))
        refs |= {x.rstrip("/.") for x in re.findall(r"/srv/[A-Za-z0-9_./+-]+", txt)}
    _PROT.update(t=time.time(), refs=sorted(refs))
    return _PROT["refs"]


def verify_local(m, dest):
    """every stored file present; zstd frames test clean; plain files re-hash to the manifest"""
    for e in m["files"]:
        if e.get("missing") or not e.get("sha256"):
            continue
        p = os.path.join(dest, "run", e["stored"]) if not e.get("generated") else os.path.join(dest, e["stored"])
        if not os.path.exists(p):
            return f"absent {e['stored']}"
        if e.get("compression") == "zstd":
            if subprocess.run(["zstd", "-q", "-t", p], capture_output=True).returncode != 0:
                return f"zstd test failed {e['stored']}"
        elif archive.sha256(p) != e["sha256"]:
            return f"sha mismatch {e['stored']}"
    return None


def release(mp):
    m = json.load(open(mp))
    dest = os.path.dirname(mp)
    j = archive.load_job(m["job"])
    if j.get("status") != "CLOSED" or m.get("status") != "archived":
        return 0
    if (m.get("release") or {}).get("done"):
        return 0
    host, run = j.get("host"), (j.get("run") or "").rstrip("/")
    for f in glob.glob(os.path.join(archive.JOBS, "*.json")):
        pass
    sib = [x for x in _jobs_by_run().get((host, run), []) if x != m["job"]]
    for s in sib:
        st = archive.load_job(s).get("status")
        if st not in TERMINAL and not str(st).startswith("EARLY_FAIL"):
            archive.log(f"RELEASE SKIP {m['job']}: run dir shared with live job {s} ({st})")
            return 0
    try:
        vm = json.load(open(os.path.expanduser(f"~/.local/state/viz-elem/{m['job']}.json")))
        if vm.get("state") == "running":
            archive.log(f"RELEASE SKIP {m['job']}: viz-elem export running")
            return 0
    except (OSError, ValueError):
        pass
    if not (m.get("gds") or {}).get("path"):
        archive.log(f"RELEASE SKIP {m['job']}: no GDS archived yet (the DB is needed on the host to stream it)")
        return 0
    bad = verify_local(m, dest)
    if bad:
        archive.log(f"RELEASE SKIP {m['job']}: archive verify failed: {bad}")
        return 0
    good = [e for e in m["files"] if e.get("sha256") and not e.get("missing") and not e.get("generated")]
    arg = dict(run=run, commit=j.get("commit_full") or "", sha=sorted({e["sha256"] for e in good}),
               sizes=sorted({e["raw_size"] for e in good if e.get("raw_size")}), protect=[r for r in protect_refs() if r.startswith(run + "/") and os.path.basename(r) not in GENERIC],
               archive=f"fleet-viz host:{dest}", at=archive.now())
    cmd = f"OT_REL={shlex.quote(json.dumps(arg))} python3 - <<'RELPY'\n{REMOTE}\nRELPY\n"
    if host == "localhost":
        p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=7200)
    else:
        p = subprocess.run(archive.SSH + [host, "bash -s"], input=cmd, capture_output=True, text=True, timeout=7200)
    res = next((json.loads(x[8:]) for x in p.stdout.splitlines() if x.startswith("REL_JSON")), None)
    if res is None:
        archive.log(f"RELEASE ERROR {m['job']}: {p.stderr[-300:]}")
        return 0
    m = json.load(open(mp))
    m["release"] = dict(done=bool(res.get("n") is not None), at=archive.now(), freed_bytes=res.get("freed", 0),
                        files=res.get("n"), note=res.get("note"))
    json.dump(m, open(mp + ".tmp", "w"), indent=1)
    os.replace(mp + ".tmp", mp)
    archive.log(f"RELEASED {m['job']} on {host}: {res.get('freed', 0) / 1e9:.2f} GB freed ({res.get('n')} items){' ' + res['note'] if res.get('note') else ''}")
    return res.get("freed", 0)


_JBR = {}


def _jobs_by_run():
    if not _JBR:
        for f in glob.glob(os.path.join(archive.JOBS, "*.json")):
            try:
                d = json.load(open(f))
            except (OSError, ValueError):
                continue
            if d.get("run") and d.get("host"):
                _JBR.setdefault((d["host"], d["run"].rstrip("/")), []).append(d["name"])
    return _JBR


def manifest_of(name):
    g = glob.glob(os.path.join(archive.ROOT, "*", archive.safe(name), "manifest.json"))
    return g[0] if g else None


def pipeline(host, par=6):
    S = {s["job"]: s for s in json.load(open(os.path.join(archive.TOOLS, "scope.json")))["scope"]}
    names = []
    for f in glob.glob(os.path.join(archive.JOBS, "*.json")):
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            continue
        if d.get("host") == host and d.get("status") == "CLOSED":
            names.append((0 if (d.get("run") or "").startswith("/srv/opentallas-scratch/") else 1, d["name"]))
    names = [n for _, n in sorted(names)]
    protect_refs()
    archive.log(f"PIPELINE {host}: {len(names)} CLOSED jobs (archive -> GDS -> verify -> release)")
    gen_gds.PER_HOST[host] = par
    tot = [0]

    def one(n):
        try:
            s = S.get(n)
            mp = archive.archive_job(n, s["element"] if s else None, s["why"] if s else None)
            if not mp:
                return
            m = json.load(open(mp))
            if m.get("status") == "archived" and not (m.get("gds") or {}).get("path"):
                gen_gds.gen(mp)
            tot[0] += release(mp)
        except Exception as e:  # noqa: BLE001
            archive.log(f"PIPELINE ERROR {n}: {e}")
    with cf.ThreadPoolExecutor(par) as ex:
        list(ex.map(one, names))
    archive.build_index()
    archive.log(f"PIPELINE {host} done: released {tot[0] / 1e9:.1f} GB")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["pipeline"]:
        pipeline(a[1], int(a[a.index("--par") + 1]) if "--par" in a else 6)
    elif a[:1] == ["release"]:
        for n in a[1:]:
            mp = manifest_of(n)
            if mp:
                release(mp)
    else:
        sys.exit(__doc__)
