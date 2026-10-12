#!/usr/bin/env python3
"""closed-archive-1011: archive the final physical-design files of CLOSED closure-loop jobs onto the fleet-viz host.

  archive.py jobs NAME...      archive these jobs (element resolved from the registry; used by the post-record hook)
  archive.py scope [--hosts H] archive every job in _tools/scope.json (bulk)
  archive.py index             rebuild INDEX.json from the per-job manifests

Layout: $CLOSED_ARCHIVE (default /home/ubuntu/closed_archive)/<element>/<job>/
  run/<path relative to the job's run dir>   copied files (.odb/.spef/.v/.lib > 8 MB stored zstd-compressed as <name>.zst)
  final/                                     symlinks to the accepted final views (6_final.odb[.zst], .def, .gds, ...)
  job.json spec.json commit.txt manifest.json
Never deletes anything on fleet hosts (read-only rsync from them).
"""
import concurrent.futures as cf
import datetime as dt
import fcntl
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.environ.get("CLOSED_ARCHIVE", "/home/ubuntu/closed_archive")
TOOLS = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.expanduser("~/.local/state/closure_loop/jobs")
OVR = "/home/ubuntu/claude-takeover-20261007/element_overrides.json"
LOG = "/home/ubuntu/claude-takeover-20261007/closed-archive-1011.log"
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=30"]
COMPRESS_EXT = (".odb", ".spef", ".v", ".lib", ".def", ".gds", ".lef")
COMPRESS_MIN = 1 << 20
FREE_MARGIN = 40 << 30
SLOW_HOSTS = {"ot-epyc1tb", "ot-epyc2"}   # load 500-800: lighter remote compression


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def log(msg):
    line = f"{now()} {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(s or "unknown"))


def load_job(name):
    return json.load(open(os.path.join(JOBS, name + ".json")))


_REG = []


def registry():
    if not _REG:
        try:
            _REG.append(json.load(urllib.request.urlopen("http://127.0.0.1:8765/api/elements", timeout=60)))
        except Exception:  # noqa: BLE001
            _REG.append({"rows": []})
    return _REG[0]


def resolve_element(j):
    """(element, why): the counted row whose best is this job, else the row owning the block (or a variant fold)"""
    rows = registry()["rows"]
    blk = j["spec"].get("block")
    for r in rows:
        if (r.get("best") or {}).get("job") == j["name"]:
            return r["element"], "best"
    for r in rows:
        if r["element"] == blk:
            return r["element"], "block"
    for r in rows:
        if blk in (r.get("variants") or []):
            return r["element"], "variant:" + blk
    try:
        v = json.load(open(OVR)).get("variants", {}).get(blk)
        if v:
            return v["of"], "variant:" + blk
    except (OSError, ValueError):
        pass
    return blk, "block"


def job_metrics(j):
    m = j.get("metrics") or {}
    out = dict(setup_ps=m.get("ss_ps"), setup_corner=m.get("setup_corner") or "tt", ff_hold_ps=m.get("ff_ps"),
               ss_sensitivity_ps=m.get("ss_sensitivity_ps"), drc=m.get("drc"), reason=(j.get("reason") or "")[:400])
    mm = re.search(r"TT ([+-]?[\d.]+) / FF ([+-]?[\d.]+) ps DRC (\d+)", j.get("reason") or "")
    if mm:
        out.update(tt_ps=float(mm.group(1)), ff_ps=float(mm.group(2)), drc=int(mm.group(3)))
    else:
        out.update(tt_ps=m.get("ss_ps"), ff_ps=m.get("ff_ps"))
    return out


def inventory(host, items):
    """items: [{job, run, orfs_dir, block}] -> {job: inv} (runs inventory_remote.py on the host)"""
    code = open(os.path.join(TOOLS, "inventory_remote.py")).read()
    cmd = f"OT_INV={shlex.quote(json.dumps(items))} python3 - <<'INVPY'\n{code}\nINVPY\n"
    for attempt in range(3):
        try:
            if host == "localhost":
                p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=1800)
            else:
                p = subprocess.run(SSH + [host, "bash -s"], input=cmd, capture_output=True, text=True, timeout=1800)
            for line in p.stdout.splitlines():
                if line.startswith("INV_JSON"):
                    return json.loads(line[8:])
            err = p.stderr[-500:]
        except subprocess.TimeoutExpired as e:
            err = str(e)[:300]
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"inventory failed on {host}: {err}")


def select_files(inv):
    """dedupe (basename, size) across the job's copies; drop pre-ECO views; final base first"""
    fb = inv.get("final_base") or "\0"

    def prio(f):
        if f.startswith(fb + "/"):
            return 0
        if re.match(r"routes/[^/]+/views?/", f):
            return 1
        if f.startswith("record/"):
            return 2
        return 3
    seen, keep = set(), {}
    for f in sorted(inv["files"], key=lambda f: (prio(f), f)):
        if ".pre_eco" in f or "/view.pre_" in f:
            continue
        sz = inv["files"][f]
        if sz < 0:
            continue
        b = os.path.basename(f)
        if b.endswith((".lib", ".lef", ".v", ".odb", ".spef", ".def", ".gds")) and sz > (1 << 20):
            if (b, sz) in seen:
                continue
            seen.add((b, sz))
        keep[f] = sz
    return keep


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def role_of(f, inv, block):
    fb = inv.get("final_base") or "\0"
    b = os.path.basename(f)
    if f.startswith(fb + "/"):
        if b in ("6_final.odb", "6_final.def", "6_final.gds", "6_final.v", "6_final.sdc", "6_final.spef", "6_1_merged.gds"):
            return "final_merged_gds" if b == "6_1_merged.gds" else "final_" + b.split(".", 1)[1]
    if block and b == f"{block}.lef":
        return "abstract_lef"
    for c in ("tt", "ff", "ss"):
        if block and b in (f"{block}_{c}.lib", f"{block}_{c}.lib.gz"):
            return "lib_" + c
    if b.endswith(".rpt"):
        return "report"
    if b.endswith(".log"):
        return "log"
    if b.endswith(".sdc"):
        return "sdc"
    return None


def archive_job(name, element=None, why=None, inv=None, force=False):
    j = load_job(name)
    if j.get("status") != "CLOSED":
        log(f"SKIP {name}: status {j.get('status')}")
        return None
    if element is None:
        element, why = resolve_element(j)
    dest = os.path.join(ROOT, safe(element), safe(name))
    man_p = os.path.join(dest, "manifest.json")
    if not force and os.path.exists(man_p):
        try:
            if json.load(open(man_p)).get("status") in ("archived", "missing", "rerouting"):
                return man_p
        except ValueError:
            pass
    host, run = j.get("host"), (j.get("run") or "").rstrip("/")
    m = j.get("metrics") or {}
    if inv is None:
        inv = inventory(host, [dict(job=name, run=run, orfs_dir=m.get("orfs_dir"), block=j["spec"].get("block"))])[name]
    os.makedirs(dest, exist_ok=True)
    json.dump(j, open(os.path.join(dest, "job.json"), "w"), indent=1)
    json.dump(j["spec"], open(os.path.join(dest, "spec.json"), "w"), indent=1)
    open(os.path.join(dest, "commit.txt"), "w").write((j.get("commit_full") or "") + "\n")
    blk = j["spec"].get("block")
    man = dict(schema="closed-archive/1", job=name, element=element, scope=why, block=blk, host=host, run_dir=run,
               orfs_dir=m.get("orfs_dir"), final_base=inv.get("final_base"), commit=j.get("commit_full"),
               owner=j["spec"].get("owner"), record=j["spec"].get("record"), publish=j.get("publish"),
               closed_at=j.get("finished_at") or j.get("updated"), deep_released=j.get("deep_released"),
               metrics=job_metrics(j), archived_at=None, files=[], gds=None, status=None)
    has_odb = inv.get("final_base") and (inv["final_base"] + "/6_final.odb") in inv["files"]
    if not inv.get("run_exists") or not has_odb:
        man.update(status="missing", missing_reason="run dir gone" if not inv.get("run_exists") else "no 6_final.odb in run dir",
                   archived_at=now())
        json.dump(man, open(man_p, "w"), indent=1)
        log(f"MISSING {name} ({element}): {man['missing_reason']} on {host}:{run}")
        return man_p
    keep = select_files(inv)
    need = sum(keep.values()) // 3
    free = shutil.disk_usage(ROOT).free
    if free - need < FREE_MARGIN:
        raise RuntimeError(f"disk: {free >> 30} GB free, job needs {need >> 30} GB + {FREE_MARGIN >> 30} GB margin")
    rd = os.path.join(dest, "run")
    os.makedirs(rd, exist_ok=True)
    # skip files already stored (resume): raw or compressed present with manifest-less partial run
    heavy = [f for f in keep if f.endswith(COMPRESS_EXT) and keep[f] >= COMPRESS_MIN]
    light = [f for f in keep if f not in heavy and not (os.path.exists(os.path.join(rd, f)) and os.path.getsize(os.path.join(rd, f)) == keep[f])]
    if light:
        lst = os.path.join(dest, ".files-from")
        open(lst, "w").write("\n".join(light) + "\n")
        src = (run + "/") if host == "localhost" else f"{host}:{run}/"
        cmd = ["rsync", "-a", "-L", "--partial", "--files-from=" + lst]
        if host != "localhost":
            cmd += ["-e", " ".join(SSH)]
        for attempt in range(3):
            p = subprocess.run(cmd + [src, rd + "/"], capture_output=True, text=True, timeout=6 * 3600)
            if p.returncode in (0, 23, 24):
                break
            time.sleep(10 * (attempt + 1))
        if p.returncode not in (0, 23, 24):
            raise RuntimeError(f"rsync {name}: rc {p.returncode} {p.stderr[-300:]}")
        os.unlink(lst)
    hstate_p = os.path.join(dest, ".heavy.json")
    hstate = json.load(open(hstate_p)) if os.path.exists(hstate_p) else {}
    todo_h = [f for f in heavy if not (f in hstate and os.path.exists(os.path.join(rd, f) + ".zst"))]
    if todo_h:
        # sha256 of the uncompressed file, computed on the fleet host (read-only)
        q = " ".join(shlex.quote(os.path.join(run, f)) for f in todo_h)
        c = f"sha256sum -- {q}"
        p = subprocess.run(["bash", "-c", c] if host == "localhost" else SSH + [host, c], capture_output=True, text=True, timeout=7200)
        sums = {}
        for line in p.stdout.splitlines():
            h, _, path = line.partition("  ")
            sums[os.path.relpath(path, run)] = h
        lvl = "-6" if host in SLOW_HOSTS else "-10"
        for f in todo_h:
            out = os.path.join(rd, f) + ".zst"
            os.makedirs(os.path.dirname(out), exist_ok=True)
            # stream-compress on the fleet host (link is ~10 MB/s per stream; data is ~6x smaller compressed)
            rc = f"zstd -q -c {lvl} -T4 -- {shlex.quote(os.path.join(run, f))}"
            for attempt in range(3):
                with open(out + ".part", "wb") as fo:
                    r = subprocess.run(["bash", "-c", rc] if host == "localhost" else SSH + [host, rc], stdout=fo,
                                       stderr=subprocess.PIPE, timeout=6 * 3600)
                if r.returncode == 0:
                    break
                time.sleep(10 * (attempt + 1))
            if r.returncode != 0:
                raise RuntimeError(f"zstd stream {name}:{f}: rc {r.returncode} {r.stderr[-200:]}")
            v = subprocess.run(f"zstd -q -dc -- {shlex.quote(out + '.part')} | sha256sum", shell=True, capture_output=True, text=True)
            got = v.stdout.split()[0] if v.stdout else ""
            if sums.get(f) and got != sums[f]:
                raise RuntimeError(f"sha mismatch {name}:{f} (file changed during copy?)")
            os.replace(out + ".part", out)
            hstate[f] = dict(sha256=got, raw_size=keep[f], stored_size=os.path.getsize(out))
            json.dump(hstate, open(hstate_p, "w"))
    files = []
    for f, sz in sorted(keep.items()):
        p = os.path.join(rd, f)
        if f in heavy:
            h = hstate.get(f)
            if not h:
                files.append(dict(path=f, raw_size=sz, missing=True))
                continue
            files.append(dict(path=f, raw_size=h["raw_size"], sha256=h["sha256"], stored=f + ".zst",
                              stored_size=h["stored_size"], compression="zstd", role=role_of(f, inv, blk)))
            continue
        if not os.path.exists(p):
            files.append(dict(path=f, raw_size=sz, missing=True))
            continue
        files.append(dict(path=f, raw_size=os.path.getsize(p), sha256=sha256(p), stored=f,
                          stored_size=os.path.getsize(p), role=role_of(f, inv, blk)))
    man["files"] = files
    # final/ symlinks
    fd = os.path.join(dest, "final")
    os.makedirs(fd, exist_ok=True)
    finals = {}
    for e in files:
        if e.get("missing") or not e.get("role"):
            continue
        if e["role"].startswith("final_") or e["role"] in ("abstract_lef", "lib_tt", "lib_ff", "lib_ss"):
            ln = os.path.join(fd, os.path.basename(e["stored"]))
            if not os.path.lexists(ln):
                os.symlink(os.path.relpath(os.path.join(rd, e["stored"]), fd), ln)
            finals[e["role"]] = "final/" + os.path.basename(e["stored"])
    man["final"] = finals
    gds = finals.get("final_gds") or finals.get("final_merged_gds")
    man["gds"] = dict(path=gds, source="flow") if gds else dict(path=None, source="pending-generation")
    man["total_stored_bytes"] = sum(e.get("stored_size", 0) for e in files)
    man["missing_files"] = [e["path"] for e in files if e.get("missing")]
    man["status"] = "archived"
    man["archived_at"] = now()
    json.dump(man, open(man_p + ".tmp", "w"), indent=1)
    os.replace(man_p + ".tmp", man_p)
    log(f"ARCHIVED {name} -> {dest} ({man['total_stored_bytes'] / 1e9:.2f} GB stored, {len(files)} files, gds={'yes' if gds else 'pending'})")
    return man_p


def build_index():
    rows = []
    for mp in sorted(glob.glob(os.path.join(ROOT, "*", "*", "manifest.json"))):
        try:
            m = json.load(open(mp))
        except ValueError:
            continue
        rows.append(dict(element=m.get("element"), job=m.get("job"), block=m.get("block"), scope=m.get("scope"),
                         status=m.get("status"), dir=os.path.relpath(os.path.dirname(mp), ROOT), host=m.get("host"),
                         run_dir=m.get("run_dir"), commit=m.get("commit"), metrics=m.get("metrics"),
                         final=m.get("final"), gds=m.get("gds"), stored_bytes=m.get("total_stored_bytes", 0),
                         reroute=m.get("reroute"), archived_at=m.get("archived_at")))
    tot = sum(r["stored_bytes"] or 0 for r in rows)
    idx = dict(schema="closed-archive-index/1", root=ROOT, generated_at=now(), jobs=len(rows),
               archived=sum(r["status"] == "archived" for r in rows), total_stored_bytes=tot,
               by_status={s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}, rows=rows)
    with open(os.path.join(ROOT, ".index.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        json.dump(idx, open(os.path.join(ROOT, "INDEX.json.tmp"), "w"), indent=1)
        os.replace(os.path.join(ROOT, "INDEX.json.tmp"), os.path.join(ROOT, "INDEX.json"))
    return idx


def run_scope(hosts=None, per_host=3, total=16):
    S = json.load(open(os.path.join(TOOLS, "scope.json")))["scope"]
    if hosts:
        S = [s for s in S if s["host"] in hosts]
    # cheapest first per host so many jobs land early
    inv_all = {}
    try:
        inv_all = json.load(open(os.path.join(TOOLS, "inventory.json")))
    except (OSError, ValueError):
        pass
    S.sort(key=lambda s: sum((inv_all.get(s["job"]) or {}).get("files", {}).values()))
    byh = {}
    for s in S:
        byh.setdefault(s["host"], []).append(s)
    import threading
    sems = {h: threading.Semaphore(per_host) for h in byh}

    def one(s):
        with sems[s["host"]]:
            try:
                return archive_job(s["job"], s["element"], s["why"], inv=inv_all.get(s["job"]))
            except Exception as e:  # noqa: BLE001
                log(f"ERROR {s['job']}: {e}")
                return None
    with cf.ThreadPoolExecutor(total) as ex:
        list(ex.map(one, S))
    idx = build_index()
    log(f"scope pass done: {idx['by_status']} total {idx['total_stored_bytes'] / 1e9:.1f} GB")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "jobs":
        for n in a[1:]:
            try:
                archive_job(n)
            except Exception as e:  # noqa: BLE001
                log(f"ERROR {n}: {e}")
        build_index()
    elif a[0] == "scope":
        hosts = a[a.index("--hosts") + 1].split(",") if "--hosts" in a else None
        run_scope(hosts)
    elif a[0] == "index":
        print(json.dumps({k: v for k, v in build_index().items() if k != "rows"}))
