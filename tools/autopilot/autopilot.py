#!/usr/bin/env python3
"""autopilot.py -- deterministic (non-LLM) kit chain on the ot-run hub (epyc1), lane AUTOPILOT 2026-10-25.

Why: closure moved only when an agent handed each step on (kit -> route -> sign-off -> archive); usage limits and
Claude<->Codex handovers stalled that chain for hours (KIT-CENSUS: 1,709 run-hours, 21 sign-offs).  This service keeps
the chain moving with no agent involved.  It is built only from existing tools: the kit's own run_kit*.sh (which ends in
tools/die_plan/signoff.py), ot-run (memory-only admission), signoff.json, tools/ref_tile/layout_dump.tcl+layout_png.py.

OWNER RULE (2026-10-25): the autopilot NEVER alters a design.  It may only
  (a) submit queued kits that carry a GEOM PASS (ot-run, honest --mem from the queue row, <= 400k cells),
  (b) classify finished runs: SIGNED / NEAR-MISS / STRUCTURAL / CRASH,
  (c) resubmit ONCE a run that crashed for infra reasons (OOM kill, host / ssh lost, never admitted),
  (d) archive SIGNED runs (closed copy + MD5SUMS + mirror) and append autopilot/signed.tsv,
  (e) send NEAR-MISS runs to autopilot/review.tsv and STRUCTURAL / non-infra CRASH runs to autopilot/structural.tsv,
      both for the die lanes (visual review + structural fix); routed failures get a review bundle (routed layout PNG
      with the failing paths drawn + the path reports),
  (f) delete the bulk data (run/results, run/objects) of failed runs it launched, as soon as their record is complete.
No ECO, no tweak, no retry of a design failure, no gate change.  A DRT/tool segfault is a CRASH of the design flow,
not infra: it is marked, never resubmitted as-is.  Nothing is killed (ot-run jobs end on their own).

Queue: coord/state autopilot/queue.tsv (lanes append through coord-commit.sh or tools/autopilot/enqueue.py), read on the
hub as `git show origin/coord/state:autopilot/queue.tsv` after a fetch (the hub checkout is never modified).
Columns (TAB separated; '#' lines are comments):
  die  type  kit  src  geom  geom_ref  mem_gb  cells  lane  [goal]  [runner]  [threads]
  kit     HOST:/srv/opentallas-scratch*/claude/<lane>/.../<kit>   (a FRESH kit dir: config.mk, no run/ yet)
  src     branch@sha the kit was generated from
  geom    PASS | PASS-COND (GEOM-REVIEW verdict; anything else waits) ; geom_ref = where the verdict is recorded
  mem_gb  honest ot-run --mem (peak of a comparable run + margin) ; cells = expected std cells (<= 400000)
  goal    route (default for run_kit.sh) | finish (default for run_kit_kv.sh / run_kit_hbm.sh)
  runner  path of the run script on the kit host (default: KIT/run_kit*.sh, else KIT/../run_kit*.sh)
The last row for an id wins (id = sha1(kit|src|goal)); a new src for the same kit is a new job.

Outputs (hub ~/coord/autopilot/, rsynced to rtx-pro): log.txt, state.json, signed.tsv, review.tsv, structural.tsv,
jobs/<id>/*.log.  Idempotent and restart-safe: one flock per tick, state saved after every transition, every TSV append
is skipped when the id is already in the file, ot-run clients run in their own transient systemd --user units.

    autopilot.py tick [--dry-run]      one pass (the timer runs this every 10 min)
    autopilot.py status                table of jobs
    autopilot.py classify HOST:KIT [--since EPOCH]   read-only classification of a kit (debug / dry tests)
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loopgaps as LG  # noqa: E402
import ownership as OWN  # noqa: E402

HERE = Path(__file__).resolve().parent
HOME = Path.home()
AP_DIR = Path(os.environ.get("AP_DIR", str(HOME / "coord" / "autopilot")))
COORD = Path(os.environ.get("AP_COORD", str(HOME / "coord")))
QUEUE_REF = os.environ.get("AP_QUEUE_REF", "origin/coord/state:autopilot/queue.tsv")
QUEUE_FILE = os.environ.get("AP_QUEUE_FILE")          # tests / manual: a local queue file instead of the git ref
COORD_FILES = os.environ.get("AP_COORD_FILES")        # tests / manual: a dir holding lanes/*.md instead of the git ref
REPO = Path(os.environ.get("AP_REPO", str(HOME / "OpenTallas")))   # hub checkout: origin/main read with git show only
REPO_FILES = os.environ.get("AP_REPO_FILES")          # tests / manual: a dir mirroring origin/main paths
RELEASE_CACHE = Path(os.environ.get("AP_RELEASE_CACHE",
                                    str(HOME / ".local/state/fleet-viz/release_tree_plan_cache.json")))
OT_RUN = os.environ.get("AP_OT_RUN", str(HOME / ".local/bin/ot-run"))
IMAGE = os.environ.get("AP_IMAGE", "openroad/orfs:asap7lock")
ARCHIVE_ROOT = "/srv/opentallas-scratch2/claude/autopilot/closed"
REVIEW_ROOT = "/srv/opentallas-scratch2/claude/autopilot/review"
MIRROR = {"epyc3": "localhost"}                        # archive mirror host per source host (default epyc3)
MIRROR_DEFAULT = "epyc3"
CELL_CAP = 400_000
NEAR_WNS_PS = -30.0
NEAR_DRC_MAX = 50
RENDER_MEM_GB = 8
ORPHAN_IDLE_S = 3 * 3600
MAX_SUBMIT_PER_TICK = int(os.environ.get("AP_MAX_SUBMIT", "12"))
MAX_NOTRUN = 3                                          # 'NOT RUN' (never admitted) resubmits
KIT_RE = re.compile(r"^([A-Za-z0-9_.-]+):(/srv/opentallas-scratch2?/claude/[A-Za-z0-9_./+=-]+)$")
SRC_RE = re.compile(r"^[A-Za-z0-9_./-]+@[0-9a-f]{7,40}$")
GEOM_OK = ("PASS", "PASS-COND")
QCOLS = ["die", "type", "kit", "src", "geom", "geom_ref", "mem_gb", "cells", "lane", "goal", "runner", "threads", "mode"]
TSV_HEAD = {
    "signed.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tarchive\tmirror\ttt_wns_ps\tff_wns_ps\tlane",
    "review.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tclass\treasons\treview_dir\tpng\tpaths\tlane",
    "structural.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tclass\treasons\treview_dir\tlane",
}
DRY = False


# ------------------------------------------------------------------------------------------------ small helpers
def now_s():
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg):
    line = f"{now_s()} AUTOPILOT: {msg}"
    print(("[dry] " if DRY else "") + line, flush=True)
    if DRY:
        return
    AP_DIR.mkdir(parents=True, exist_ok=True)
    with open(AP_DIR / "log.txt", "a") as f:
        f.write(line + "\n")


def sh(cmd, timeout=300, input=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def ssh_host(host):
    return "localhost" if host in ("epyc1", "tender-ray", "localhost", "ubuntu-epyc1") else host


def rpy(host, code, args, timeout=600):
    """run python code on host (read-mostly probes) with JSON args on argv; returns parsed JSON or {'error': ...}"""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ControlPath=none", ssh_host(host),
           "python3", "-I", "-", shlex.quote(json.dumps(args))]
    rc, out, err = sh(cmd, timeout=timeout, input=code)
    for line in reversed(out.splitlines()):
        if line.startswith("AP_JSON "):
            return json.loads(line[8:])
    return {"error": f"probe rc {rc}: {(err or out).strip()[-400:]}"}


def rbash(host, script, timeout=1800):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ControlPath=none", ssh_host(host),
           "bash", "-s"]
    return sh(cmd, timeout=timeout, input=script)


def job_id(kit, src, goal):
    return hashlib.sha1(f"{kit}|{src}|{goal}".encode()).hexdigest()[:12]


# ------------------------------------------------------------------------------------------------ queue
def read_queue_text():
    if QUEUE_FILE:
        try:
            return Path(QUEUE_FILE).read_text()
        except FileNotFoundError:
            return ""
    sh(["git", "-C", str(COORD), "fetch", "-q", "origin", "coord/state"], timeout=120)
    rc, out, _ = sh(["git", "-C", str(COORD), "show", QUEUE_REF], timeout=60)
    return out if rc == 0 else ""


def read_coord(rel):
    """a coord/state file (lanes/GEOM-REVIEW.md ...) as of the last fetch; '' if missing (read-only)"""
    if COORD_FILES:
        try:
            return (Path(COORD_FILES) / rel).read_text(errors="replace")
        except OSError:
            return ""
    rc, out, _ = sh(["git", "-C", str(COORD), "show", f"origin/coord/state:{rel}"], timeout=60)
    return out if rc == 0 else ""


def geom_tag(ref):
    m = re.search(r"\[([^\]]+)\]", ref or "")
    return LG.tag_of(m.group(1) if m else (ref or ""))


def resolve_geom(rows, geom_text):
    """GEOM PASS -> submit within one tick: a row queued before its verdict (geom REQ/WAIT, geom_ref = the GEOM REQ
    tag) takes the verdict from lanes/GEOM-REVIEW.md once a REPLY/VERDICT of that tag names the kit"""
    for r in rows.values():
        if r["error"] or r["geom"].upper() in GEOM_OK or not r["geom_ref"]:
            continue
        v = LG.geom_verdicts(geom_text, geom_tag(r["geom_ref"]), r["type"], r["src"].split("@")[-1])
        if v:
            r["geom_auto"] = f"{v[0]} {time.strftime('%Y-%m-%d %H:%M', time.localtime(v[1]))}: {v[2].strip()[:200]}"
            r["geom"] = v[0]
            r["geom_ref"] = f"GEOM-REVIEW [{geom_tag(r['geom_ref'])}] {time.strftime('%m-%d %H:%M', time.localtime(v[1]))}"


def parse_queue(text):
    """-> {id: row} (last row per id wins), rows carry 'line' and 'error' (validation)"""
    rows = {}
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        f = raw.rstrip("\n").split("\t")
        if f[0] == "die":
            continue                                   # header
        r = {k: (f[i].strip() if i < len(f) else "") for i, k in enumerate(QCOLS)}
        r["line"] = n
        r["error"] = validate_row(r)
        if not r["error"]:
            r["goal"] = r["goal"] or "auto"
            r["threads"] = int(r["threads"] or 8)
            r["mode"] = r["mode"] or "submit"
            r["mem_gb"] = int(float(r["mem_gb"]))
            r["cells"] = int(float(r["cells"]))
            h, p = KIT_RE.match(r["kit"]).groups()
            r["host"], r["path"] = h, p.rstrip("/")
        rid = job_id(r["kit"], r["src"], r.get("goal") or "auto")
        r["id"] = rid
        rows[rid] = r
    return rows


def validate_row(r):
    if not r["die"] or not r["type"]:
        return "die/type missing"
    if not KIT_RE.match(r["kit"]) or ".." in r["kit"]:
        return "kit must be HOST:/srv/opentallas-scratch{,2}/claude/<lane>/... (absolute, no ..)"
    if not SRC_RE.match(r["src"]):
        return "src must be branch@sha"
    try:
        m = float(r["mem_gb"])
        if not 1 <= m <= 512:
            return "mem_gb out of range 1..512"
    except ValueError:
        return "mem_gb not a number (honest --mem required)"
    try:
        c = float(r["cells"])
    except ValueError:
        return "cells not a number (expected std cells required)"
    if c > CELL_CAP:
        return f"cells {int(c)} > {CELL_CAP} (OpenROAD cap per run)"
    if r["goal"] not in ("", "auto", "route", "finish"):
        return "goal must be route|finish|auto"
    if r["threads"] and not r["threads"].isdigit():
        return "threads not an integer"
    if r["runner"] and not r["runner"].startswith("/"):
        return "runner must be an absolute path"
    if r["mode"] not in ("", "submit", "adopt"):
        return "mode must be submit|adopt"
    return ""


# ------------------------------------------------------------------------------------------------ state
def load_state():
    try:
        return json.loads((AP_DIR / "state.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"jobs": {}}


def save_state(st):
    if DRY:
        return
    AP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = AP_DIR / f".state.json.{os.getpid()}"
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True))
    os.replace(tmp, AP_DIR / "state.json")


def set_status(st, j, status, why=""):
    if j.get("status") != status:
        j.setdefault("history", []).append([now_s(), status, why[:300]])
    j["status"] = status
    j["updated"] = time.time()
    save_state(st)


def tsv_append(name, jid, fields):
    """append one row unless the id is already in the file (idempotent across crashes/restarts)"""
    if DRY:
        log(f"would append {name}: {jid}")
        return
    p = AP_DIR / name
    if p.exists() and any(l.split("\t")[1:2] == [jid] for l in p.read_text().splitlines()):
        return
    new = not p.exists()
    with open(p, "a") as f:
        if new:
            f.write(TSV_HEAD[name] + "\n")
        f.write("\t".join([now_s(), jid] + [str(x).replace("\t", " ").replace("\n", " ") for x in fields]) + "\n")


# ------------------------------------------------------------------------------------------------ host probes
PROBE_KIT = r'''
import json, os, sys, glob, re, time
a = json.loads(sys.argv[1]); K = a["kit"]; out = {"kit": K, "exists": os.path.isdir(K)}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
if not out["exists"]: done()
out["config"] = os.path.isfile(os.path.join(K, "config.mk"))
out["has_run"] = os.path.isdir(os.path.join(K, "run"))
out["signoff_dirs"] = sorted(os.path.basename(p) for p in glob.glob(os.path.join(K, "signoff*")) if os.path.isdir(p))
B = os.path.join(K, "run", "results", "asap7", "*", "base")
out["routed"] = sorted(os.path.basename(p) for p in glob.glob(os.path.join(B, "5_*.odb")) + glob.glob(os.path.join(B, "6_*.odb")))
out["fail_marks"] = [f for f in ("FAIL_PREFLOOR", "FAIL_POSTCTS") if os.path.exists(os.path.join(K, f))]
lm = [os.path.getmtime(p) for p in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "*")) +
      glob.glob(os.path.join(K, "*.log"))]
out["log_age_s"] = time.time() - max(lm) if lm else None
try:
    import subprocess
    ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60).stdout.split()
    busy = False
    if ids:
        js = json.loads(subprocess.run(["docker", "inspect"] + ids, capture_output=True, text=True, timeout=120).stdout)
        st = [c.get("State", {}).get("StartedAt", "") for c in js
              if any(m.get("Source", "").rstrip("/") == K.rstrip("/") for m in c.get("Mounts", []))]
        busy = bool(st)
        out["started"] = sorted(x for x in st if x)
    out["busy"] = busy
except Exception as e:
    out["busy"] = "docker check failed: %s" % e
r = a.get("runner") or ""
if not r:
    for d in (K, os.path.dirname(K)):
        c = sorted(glob.glob(os.path.join(d, "run_kit*.sh")))
        if c: r = c[0]; break
out["runner"] = r if r and os.path.isfile(r) else ""
done()
'''

PROBE_CLASSIFY = r'''
import json, os, sys, glob, re, time
a = json.loads(sys.argv[1]); K = a["kit"]; since = a.get("since", 0) - 120; goal = a.get("goal", "route")
out = {"kit": K, "exists": os.path.isdir(K)}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
def rd(p, n=None):
    try:
        with open(p, errors="replace") as f:
            t = f.read()
        return t if n is None else t[-n:]
    except Exception:
        return ""
def jl(p):
    try:
        return json.load(open(p))
    except Exception:
        return None
if not out["exists"]: done()
# newest signoff record written by this run
so = [p for p in glob.glob(os.path.join(K, "signoff*", "signoff.json")) if os.path.getmtime(p) >= since]
so.sort(key=os.path.getmtime)
if so:
    d = jl(so[-1]) or {}
    c = d.get("checks") or {}
    out["signoff"] = {"path": so[-1], "verdict": d.get("verdict"), "reasons": d.get("reasons"),
        "fails": sorted(k for k, v in c.items() if isinstance(v, dict) and v.get("verdict") == "FAIL"),
        "tt_wns": (c.get("setup_tt") or {}).get("wns_ps"), "ff_wns": (c.get("hold_ff") or {}).get("wns_ps"),
        "drc": (c.get("drc") or {}).get("count"), "antenna": (c.get("antenna") or {}).get("count"),
        "base": (d.get("inputs") or {}).get("base"), "odb": (d.get("inputs") or {}).get("odb")}
    try:
        out["signoff"]["odb_bytes"] = os.path.getsize(out["signoff"]["odb"])
    except Exception:
        out["signoff"]["odb_bytes"] = 0
for f in ("FAIL_PREFLOOR", "FAIL_POSTCTS"):
    p = os.path.join(K, f)
    if os.path.isfile(p) and os.path.getmtime(p) >= since:
        out[f] = rd(p)[-400:].strip()
logs = sorted(glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "*.log")), key=os.path.getmtime)
out["last_log"] = os.path.basename(logs[-1]) if logs else ""
out["last_log_mtime"] = os.path.getmtime(logs[-1]) if logs else 0
txt = "\n".join(rd(p, 200000) for p in logs if os.path.getmtime(p) >= since)
runlog = rd(os.path.join(K, "run_%s.log" % goal), 400000)
alltxt = txt + "\n" + runlog
out["runlog_tail"] = runlog[-600:]
pat = {"hold_structural": r"OT_HOLD_STRUCTURAL[^\n]*", "congestion": r"GRT-0116[^\n]*|[Rr]outing congestion too high[^\n]*",
       "segfault": r"Segmentation fault[^\n]*|Signal 11 received[^\n]*|SIGSEGV[^\n]*|core dumped[^\n]*",
       "oom": r"Error 137[^\n]*|\bKilled\b[^\n]*|[Oo]ut of memory[^\n]*|std::bad_alloc[^\n]*|OOMKilled[^\n]*",
       "orfs_error": r"\[ERROR [A-Z]+-\d+\][^\n]*"}
for k, p in pat.items():
    m = re.search(p, alltxt)
    if m: out[k] = m.group(0)[:300]
cells = 0
for js in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "*.json")):
    d = jl(js) or {}
    for k, v in d.items():
        if k.endswith("__design__instance__count__stdcell") and isinstance(v, (int, float)):
            cells = max(cells, int(v))
out["cells"] = cells
g = rd(next(iter(glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "5_1_grt.log"))), ""))
tot = re.findall(r"^Total\s+.*?(\d+)\s*$", g, re.M)
out["grt_overflow"] = int(tot[-1]) if tot else None
done()
'''

PROBE_DELETE = r'''
import json, os, sys, glob, shutil, subprocess
a = json.loads(sys.argv[1]); K = os.path.realpath(a["kit"]); out = {"kit": K, "deleted": [], "errors": []}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
if not (K.startswith("/srv/opentallas-scratch") and "/claude/" in K and os.path.isfile(os.path.join(K, "config.mk"))):
    out["errors"].append("refused: not a kit under /srv/opentallas-scratch*/claude"); done()
try:
    ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60).stdout.split()
    srcs = []
    if ids:
        js = json.loads(subprocess.run(["docker", "inspect"] + ids, capture_output=True, text=True, timeout=120).stdout)
        srcs = [m.get("Source", "") for c in js for m in c.get("Mounts", [])]
    if any(s == K or s.startswith(K + "/") or K.startswith(s.rstrip("/") + "/") and len(s) > 25 for s in srcs):
        out["errors"].append("refused: a running container mounts the kit"); done()
except Exception as e:
    out["errors"].append("refused: docker check failed %s" % e); done()
for sub in ("run/results", "run/objects"):
    p = os.path.join(K, sub)
    if os.path.isdir(p) and not os.path.islink(p):
        if a.get("dry"):
            out["deleted"].append(p + " (dry)"); continue
        shutil.rmtree(p, ignore_errors=True)
        if os.path.exists(p):
            out["errors"].append("could not fully remove " + p)
        else:
            out["deleted"].append(p)
done()
'''

PROBE_ARCHIVE = r'''
import json, os, sys, glob, shutil, hashlib
a = json.loads(sys.argv[1]); K = a["kit"]; A = a["dest"]; base = a["base"]; so = a["signoff_dir"]
out = {"dest": A, "files": 0, "errors": []}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
if os.path.exists(os.path.join(A, "MD5SUMS")):
    out["exists"] = True; done()
os.makedirs(A, exist_ok=True)
def cp(src, rel):
    dst = os.path.join(A, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src): shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=False)
    else: shutil.copy2(src, dst)
for f in sorted(os.listdir(base)):
    if f.startswith(("6_final", "5_route", "5_2_route", "1_synth", "1_2_yosys")) or f.endswith((".lef", ".lib")):
        cp(os.path.join(base, f), os.path.join("base", f))
for f in sorted(os.listdir(K)):
    p = os.path.join(K, f)
    if os.path.isfile(p) and (f.endswith((".json", ".mk", ".sdc", ".log", ".txt")) or f.startswith("run_")):
        cp(p, os.path.join("kit", f))
for d in ("views",):
    if os.path.isdir(os.path.join(K, d)): cp(os.path.join(K, d), os.path.join("kit", d))
cp(so, os.path.join("kit", os.path.basename(so)))
for p in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base")):
    cp(p, "logs")
with open(os.path.join(A, "AUTOPILOT.json"), "w") as f:
    json.dump(a["record"], f, indent=1)
lines = []
for dp, dn, fn in os.walk(A):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        if f == "MD5SUMS": continue
        h = hashlib.md5()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
        lines.append("%s  %s" % (h.hexdigest(), os.path.relpath(p, A)))
with open(os.path.join(A, "MD5SUMS"), "w") as f:
    f.write("\n".join(sorted(lines, key=lambda l: l[34:])) + "\n")
out["files"] = len(lines)
done()
'''

PROBE_MD5CHECK = r'''
import json, os, sys, hashlib
a = json.loads(sys.argv[1]); A = a["dest"]; out = {"ok": False, "bad": []}
try:
    for line in open(os.path.join(A, "MD5SUMS")):
        h, rel = line.rstrip("\n").split("  ", 1)
        m = hashlib.md5()
        with open(os.path.join(A, rel), "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""): m.update(b)
        if m.hexdigest() != h: out["bad"].append(rel)
    out["ok"] = not out["bad"]
except Exception as e:
    out["bad"].append(str(e))
print("AP_JSON " + json.dumps(out))
'''


# ------------------------------------------------------------------------------------------------ classification
def classify(c, client):
    """pure function: (classify-probe result, client outcome) -> (class, kind, reasons)
    class: SIGNED | NEAR-MISS | STRUCTURAL | CRASH ; kind refines it (infra / tool / ...)"""
    so = c.get("signoff")
    if so:
        if so.get("verdict") == "SIGNED":
            return "SIGNED", "signed", "SIGNED"
        reasons = "; ".join(so.get("reasons") or []) or "NOT SIGNED"
        fails = set(so.get("fails") or [])
        tt, ff = so.get("tt_wns"), so.get("ff_wns")
        drc = so.get("drc") or 0
        ov = c.get("grt_overflow")
        structural_fail = fails & {"clock", "sdc_lint", "face_guard", "unconstrained", "antenna"}
        timing_ok = all(w is None or w >= NEAR_WNS_PS for w in (tt, ff))
        timing_neg = any(w is not None and w < 0 for w in (tt, ff))
        if (not structural_fail and timing_ok and (ov in (None, 0)) and drc <= NEAR_DRC_MAX
                and (timing_neg or drc > 0 or "drv" in fails)):
            return "NEAR-MISS", "routed", reasons
        return "STRUCTURAL", "routed-not-signed", reasons
    if c.get("FAIL_PREFLOOR"):
        return "STRUCTURAL", "preflight", "FAIL_PREFLOOR " + c["FAIL_PREFLOOR"]
    if c.get("FAIL_POSTCTS"):
        return "STRUCTURAL", "post-cts-hold", "FAIL_POSTCTS " + c["FAIL_POSTCTS"]
    if c.get("hold_structural"):
        return "STRUCTURAL", "hold-structural", c["hold_structural"]
    if c.get("congestion"):
        return "STRUCTURAL", "grt-overflow", c["congestion"]
    if c.get("cells", 0) > CELL_CAP:
        return "STRUCTURAL", "cell-cap", f"{c['cells']} std cells > {CELL_CAP}"
    if c.get("segfault"):
        return "CRASH", "tool-segfault", c["segfault"]
    if client.get("not_run"):
        return "CRASH", "infra-notrun", client.get("msg", "ot-run NOT RUN")
    if client.get("not_completed"):
        return "CRASH", "infra-lost", client.get("msg", "ot-run NOT COMPLETED")
    if c.get("oom") or client.get("exit") in (137, 143):
        return "CRASH", "infra-oom", c.get("oom") or f"exit {client.get('exit')}"
    if client.get("exit") == 0:
        return "CRASH", "no-signoff", "flow exit 0 but no signoff.json"
    return "CRASH", "flow-error", c.get("orfs_error") or (c.get("runlog_tail") or "")[-300:] or f"exit {client.get('exit')}"


INFRA_KINDS = ("infra-oom", "infra-lost", "infra-notrun", "infra-orphan")


def parse_client_log(text):
    """ot-run client log (+ our AP_RC line) -> outcome dict"""
    o = {}
    m = re.findall(r"ot-run: RAN on ([^\s:(]+)(?: \(unit [^)]*\))?:? exit (\d+)", text)
    if m:
        o["ran_on"], o["exit"] = m[-1][0], int(m[-1][1])
    if "ot-run: NOT RUN" in text and "ran_on" not in o:
        o["not_run"] = True
        o["msg"] = [l for l in text.splitlines() if "NOT RUN" in l][-1][:300]
    if "ot-run: NOT COMPLETED" in text:
        o["not_completed"] = True
        o["msg"] = [l for l in text.splitlines() if "NOT COMPLETED" in l][-1][:300]
    m = re.findall(r"^AP_RC=(\d+)", text, re.M)
    if m:
        o["ap_rc"] = int(m[-1])
        o.setdefault("exit", o["ap_rc"])
    return o


# ------------------------------------------------------------------------------------------------ units
def unit_active(unit):
    rc, out, _ = sh(["systemctl", "--user", "is-active", unit], timeout=30)
    return out.strip() in ("active", "activating", "reloading")


def launch_unit(unit, logfile, argv):
    """run argv detached in a transient systemd --user unit; stdout+stderr -> logfile, then 'AP_RC=<rc>'"""
    inner = " ".join(shlex.quote(a) for a in argv)
    script = f"echo AP_START $(date +%s) {shlex.quote(unit)}; {inner}; echo AP_RC=$?"
    cmd = ["systemd-run", "--user", "--quiet", "--collect", f"--unit={unit}",
           f"--setenv=PATH={HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin", f"--setenv=HOME={HOME}",
           "--property=TimeoutStopSec=120", "/bin/bash", "-c", f"exec >> {shlex.quote(str(logfile))} 2>&1; {script}"]
    if DRY:
        log(f"would launch {unit}: {inner}")
        return True
    Path(logfile).parent.mkdir(parents=True, exist_ok=True)
    rc, out, err = sh(cmd, timeout=60)
    if rc != 0:
        log(f"systemd-run {unit} failed rc {rc}: {err.strip()[:300]}")
    return rc == 0


# ------------------------------------------------------------------------------------------------ actions
def hub_procs(path):
    """processes on the hub (ot-run clients, local docker run / run_kit.sh) whose command line names the kit dir
    -> [(pid, elapsed_s)]; ot-run clients always run here, also when the job itself spilled to another host"""
    rc, out, _ = sh(["ps", "-eo", "pid=,etimes=,args="], timeout=60)
    pat = re.compile(re.escape(path.rstrip("/")) + r"(?=[/\s]|$)")
    me = os.getpid()
    res = []
    for line in out.splitlines():
        f = line.split(None, 2)
        if len(f) == 3 and f[0].isdigit() and int(f[0]) != me and pat.search(f[2]) and "autopilot" not in f[2] \
                and not f[2].startswith(("ssh ", "python3 -I -")):
            res.append((int(f[0]), int(f[1])))
    return res


def iso_epoch(s):
    try:
        return datetime.datetime.fromisoformat(re.sub(r"(\.\d{6})\d*", r"\1", s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def adopt(st, j, p):
    """a run the lane already launched by hand: no submit, the autopilot only watches, classifies and records it"""
    hp = hub_procs(j["path"])
    starts = [time.time() - e for _, e in hp] + [t for t in (iso_epoch(x) for x in p.get("started") or []) if t]
    j.update(adopted=True, unit=None, attempts=0, started=min(starts) if starts else 0)
    set_status(st, j, "RUNNING", "adopted: " + (f"live since {time.strftime('%H:%M', time.localtime(min(starts)))}"
                                                if starts else "not live (classify what is there)"))
    log(f"ADOPT {j['id']} {j['die']}/{j['type']} {j['kit']}: lane-launched run, autopilot classifies + records it "
        f"({len(hp)} hub procs, containers {p.get('busy')})")


def poll_adopted(st, j):
    if hub_procs(j["path"]):
        return
    c = probe_job(j)
    if c is None:
        return
    if not c.get("signoff"):
        p = rpy(j["host"], PROBE_KIT, {"kit": j["path"], "runner": j.get("runner", "")}, timeout=120)
        la = p.get("log_age_s")
        if p.get("error") or p.get("busy") is not False or (la is not None and la < 900):
            return
    j.setdefault("client_done_at", time.time())
    finish(st, j, c, {"adopted": True})


def default_goal(runner):
    return "route" if os.path.basename(runner) == "run_kit.sh" else "finish"


def submit(st, j, attempt_note=""):
    n = j.get("attempts", 0) + 1
    unit = f"ap-{j['id']}-a{n}"
    logf = AP_DIR / "jobs" / j["id"] / f"a{n}.log"
    kit, runner, mem, thr = j["path"], j["runner"], j["mem_gb"], j["threads"]
    argv = [OT_RUN, "--mem", str(mem), "--threads", str(thr), "--dir", kit, "--stage", kit]
    if not runner.startswith(kit + "/"):
        argv += ["--stage", runner]
    argv += ["--", "bash", runner, kit, j["goal"], str(mem), str(thr)]
    if DRY:
        log(f"would SUBMIT {j['id']} {j['die']}/{j['type']} {attempt_note}: {' '.join(argv)}")
        return
    if launch_unit(unit, logf, argv):
        j.pop("client_done_at", None)
        j.update(attempts=n, unit=unit, client_log=str(logf), started=time.time())
        set_status(st, j, "RUNNING", f"attempt {n} {attempt_note}".strip())
        log(f"SUBMIT {j['id']} {j['die']}/{j['type']} {j['kit']} goal {j['goal']} --mem {mem} attempt {n} "
            f"{attempt_note} (src {j['src']}, geom {j['geom']} {j['geom_ref']})")


def admit_new(st, rows):
    submitted = 0
    for rid, r in sorted(rows.items(), key=lambda kv: kv[1]["line"]):
        j = st["jobs"].get(rid)
        if j and j.get("status") not in (None, "WAIT-GEOM", "REJECTED"):
            continue                                   # already handled; the queue never restarts a job
        if j and j.get("status") == "REJECTED" and j.get("queue_line") == r["line"]:
            continue                                   # re-judged only when the row is re-appended
        if r["error"]:
            if not j:
                j = st["jobs"][rid] = {"id": rid, "kit": r["kit"], "queue_line": r["line"]}
                log(f"REJECT queue line {r['line']} ({r['kit']}): {r['error']}")
                set_status(st, j, "REJECTED", r["error"])
            continue
        if r["mode"] != "adopt" and (r["geom"].upper() not in GEOM_OK or not r["geom_ref"]):
            if not j:
                j = st["jobs"][rid] = dict(r)
                log(f"WAIT {rid} {r['die']}/{r['type']}: GEOM '{r['geom']}' (needs PASS + geom_ref)")
                set_status(st, j, "WAIT-GEOM", r["geom"])
            if r.get("geom_auto") and j.get("geom_auto") != r["geom_auto"]:
                j["geom_auto"] = r["geom_auto"]
                log(f"WAIT {rid} {r['die']}/{r['type']}: GEOM verdict {r['geom_auto']} -- not submitted")
                set_status(st, j, "WAIT-GEOM", r["geom_auto"])
            continue
        if r.get("geom_auto") and (not j or j.get("geom_auto") != r["geom_auto"]):
            log(f"GEOM {rid} {r['die']}/{r['type']}: verdict from lanes/GEOM-REVIEW.md -> {r['geom_auto']}")
        if submitted >= MAX_SUBMIT_PER_TICK:
            break
        p = rpy(r["host"], PROBE_KIT, {"kit": r["path"], "runner": r["runner"]}, timeout=120)
        j = st["jobs"].setdefault(rid, {})
        j.update({k: v for k, v in r.items() if k not in ("error",)})
        j["queue_line"] = r["line"]
        if p.get("error"):
            log(f"HOLD {rid}: kit probe on {r['host']} failed ({p['error'][:200]}); retry next tick")
            continue
        # a placed kit (GEOM review is done on 3_place) continues in its run dir: run_kit.sh's make is incremental.
        # A kit that already routed, signed off or failed a gate is never relaunched: that needs a fresh kit.
        la = p.get("log_age_s")
        why = ("kit dir missing" if not p["exists"] else "no config.mk" if not p.get("config") else
               f"kit already routed / signed off ({', '.join(p.get('routed', []) + p.get('signoff_dirs', []))}); "
               "enqueue a fresh kit" if p.get("routed") or p.get("signoff_dirs") else
               f"kit carries {'+'.join(p['fail_marks'])} from an earlier run; enqueue a fresh kit"
               if p.get("fail_marks") else "no run_kit*.sh runner found" if not p.get("runner") else "")
        if r["mode"] == "adopt":
            why = "kit dir missing" if not p["exists"] else "no config.mk" if not p.get("config") else ""
        busy = p.get("busy") is not False or (la is not None and la < 900) or bool(hub_procs(r["path"]))
        if not why and busy and r["mode"] != "adopt":
            log(f"HOLD {rid} {r['die']}/{r['type']}: kit busy (container: {p.get('busy')}, logs "
                f"{'none' if la is None else f'{la / 60:.0f} min old'}); retry next tick")
            continue
        if why:
            log(f"REJECT {rid} {r['die']}/{r['type']} {r['kit']}: {why}")
            set_status(st, j, "REJECTED", why)
            continue
        j["runner"] = p["runner"]
        if j.get("goal") in ("", "auto", None):
            j["goal"] = default_goal(p["runner"])
        if j.get("mode") == "adopt":
            adopt(st, j, p)
            continue
        submit(st, j)
        submitted += 1


def probe_job(j):
    """classify-probe on the kit host, falling back to the host ot-run ran it on"""
    hosts = [j["host"]] + ([j["ran_on"]] if j.get("ran_on") and ssh_host(j["ran_on"]) != ssh_host(j["host"]) else [])
    best = None
    for h in hosts:
        c = rpy(h, PROBE_CLASSIFY, {"kit": j["path"], "since": j.get("started", 0), "goal": j["goal"]})
        if c.get("error"):
            continue
        c["probe_host"] = h
        if c.get("signoff") or c.get("last_log_mtime", 0) >= j.get("started", 0) or best is None:
            best = c
            if c.get("signoff"):
                break
    return best


def poll_running(st):
    for j in list(st["jobs"].values()):
        if j.get("status") not in ("RUNNING", "ORPHAN"):
            continue
        if j.get("adopted"):
            poll_adopted(st, j)
            continue
        if j.get("unit") and unit_active(j["unit"]):
            continue
        j.setdefault("client_done_at", time.time())
        text = ""
        try:
            text = Path(j["client_log"]).read_text(errors="replace")
        except (OSError, KeyError):
            pass
        client = parse_client_log(text)
        if client.get("ran_on"):
            j["ran_on"] = client["ran_on"]
        if "ap_rc" not in client and not client.get("not_completed"):
            # client gone without a result (hub reboot / unit killed): the remote job may still run
            c = probe_job(j)
            if c and c.get("signoff"):
                finish(st, j, c, client)
                continue
            idle = time.time() - max((c or {}).get("last_log_mtime", 0), j.get("started", 0))
            if idle < ORPHAN_IDLE_S:
                if j["status"] != "ORPHAN":
                    log(f"ORPHAN {j['id']}: ot-run client ended without a result; watching the kit logs")
                    set_status(st, j, "ORPHAN", "client gone")
                continue
            client = {"orphan": True, "msg": f"client lost, kit logs idle {idle / 3600:.1f} h"}
        if client.get("not_completed"):
            c = probe_job(j)
            if c and not c.get("signoff") and time.time() - c.get("last_log_mtime", 0) < ORPHAN_IDLE_S:
                if j["status"] != "ORPHAN":
                    log(f"ORPHAN {j['id']}: {client['msg']}; remote job may still run, watching its logs")
                    set_status(st, j, "ORPHAN", client["msg"])
                continue
        else:
            c = probe_job(j)
        if c is None:
            log(f"HOLD {j['id']}: classify probe failed on every host; retry next tick")
            continue
        finish(st, j, c, client)


def finish(st, j, c, client):
    cls, kind, reasons = classify(c, client)
    if client.get("orphan") and cls == "CRASH" and kind not in ("tool-segfault",):
        kind, reasons = "infra-orphan", client["msg"]
    j.update(cls=cls, kind=kind, reasons=reasons[:600], probe=c.get("probe_host"),
             signoff=c.get("signoff"), finished=time.time())
    log(f"CLASSIFY {j['id']} {j['die']}/{j['type']} -> {cls} ({kind}): {reasons[:240]}")
    if cls == "CRASH" and kind in INFRA_KINDS and not j.get("adopted"):
        notrun = kind == "infra-notrun"
        if notrun and j.get("notrun_retries", 0) < MAX_NOTRUN:
            j["notrun_retries"] = j.get("notrun_retries", 0) + 1
            submit(st, j, f"(resubmit: never admitted, {j['notrun_retries']}/{MAX_NOTRUN})")
            return
        if not notrun and not j.get("infra_retry"):
            j["infra_retry"] = True
            if kind == "infra-oom":
                j["mem_gb"] = min(512, int(j["mem_gb"] * 1.5 + 0.999))
            submit(st, j, f"(resubmit once after {kind}; resumes the run dir; --mem {j['mem_gb']})")
            return
    set_status(st, j, cls, f"{kind}: {reasons[:200]}")
    after_class(st, j)


def after_class(st, j):
    cls = j["status"]
    if cls == "SIGNED":
        archive(st, j)
    elif cls in ("NEAR-MISS", "STRUCTURAL", "CRASH"):
        if (j.get("signoff") or {}).get("odb"):
            start_review(st, j)
        else:
            record_failure(st, j)


def archive(st, j):
    host = ssh_host(j.get("probe") or j["host"])
    so = j["signoff"]
    sha = j["src"].split("@")[1][:10]
    dest = f"{ARCHIVE_ROOT}/{j['die']}/{j['type']}__{sha}"
    rec = {k: j.get(k) for k in ("id", "die", "type", "kit", "src", "geom", "geom_ref", "lane", "goal", "mem_gb")}
    rec.update(signoff=so, archived=now_s(), host=host)
    if DRY:
        log(f"would archive {j['id']} {host}:{j['path']} -> {dest} + mirror")
        return
    r = rpy(host, PROBE_ARCHIVE, {"kit": j["path"], "dest": dest, "base": so["base"],
                                  "signoff_dir": os.path.dirname(so["path"]), "record": rec}, timeout=3600)
    if r.get("error") or r.get("errors"):
        log(f"ARCHIVE FAILED {j['id']}: {r.get('error') or r.get('errors')}; retry next tick")
        set_status(st, j, "SIGNED", "archive pending")
        return
    mhost = MIRROR.get(host, MIRROR_DEFAULT)
    pdir = os.path.dirname(dest)
    rc, _, err = sh(["bash", "-c",
                     f"ssh -o BatchMode=yes -o ControlPath=none {host} tar -C {shlex.quote(pdir)} -cf - "
                     f"{shlex.quote(os.path.basename(dest))} | ssh -o BatchMode=yes -o ControlPath=none {mhost} "
                     f"'mkdir -p {shlex.quote(pdir)} && tar -C {shlex.quote(pdir)} -xf -'"], timeout=7200)
    m = rpy(mhost, PROBE_MD5CHECK, {"dest": dest}, timeout=3600) if rc == 0 else {"ok": False, "bad": [err[-200:]]}
    mirror = f"{mhost}:{dest}" if m.get("ok") else f"MIRROR-FAILED({(m.get('bad') or m.get('error'))})"
    j["archive"] = f"{host}:{dest}"
    j["mirror"] = mirror
    tsv_append("signed.tsv", j["id"], [j["die"], j["type"], j["src"], host, j["kit"], j["archive"], mirror,
                                       so.get("tt_wns"), so.get("ff_wns"), j.get("lane", "")])
    log(f"ARCHIVED {j['id']} {j['die']}/{j['type']} -> {j['archive']} ({r.get('files')} files, MD5SUMS) mirror {mirror}")
    set_status(st, j, "ARCHIVED", j["archive"])


def render_mem_gb(odb_bytes):
    """layout_dump.tcl holds every instance as Tcl strings: budget 10x the ODB size + 4 GB (1.87 GB ODB OOM at 8 GB)"""
    return min(256, math.ceil(max(RENDER_MEM_GB, 10 * odb_bytes / 2**30 + 4)))


def start_review(st, j):
    """review bundle for a routed failure: layout PNG + failing paths (ot-run job, reads the routed ODB)"""
    host = ssh_host(j.get("probe") or j["host"])
    rev = f"{REVIEW_ROOT}/{j['id']}"
    so = j["signoff"]
    if DRY:
        log(f"would render review {j['id']} on {host}: {so['odb']} -> {rev}")
        return
    tools = [HERE / "render_review.sh", HERE / "render_review.py"]
    rt = HERE.parent / "ref_tile"
    tools += [rt / "layout_dump.tcl", rt / "layout_png.py", rt / "layout_review.tcl"]
    rc, _, err = rbash(host, f"mkdir -p {shlex.quote(rev)}/tools", timeout=60)
    ok = rc == 0
    for t in tools:
        if ok and t.exists():
            rc, _, err = sh(["scp", "-q", "-o", "BatchMode=yes", "-o", "ControlPath=none", str(t),
                             f"{host}:{rev}/tools/"], timeout=120)
            ok = rc == 0
    if not ok:
        log(f"REVIEW setup failed {j['id']} on {host}: {err.strip()[-200:]}; recording without render")
        record_failure(st, j)
        return
    mem = render_mem_gb(so.get("odb_bytes") or 0)
    meta = {"id": j["id"], "kit": j["path"], "odb": so["odb"], "signoff": so["path"], "image": IMAGE, "mem_gb": mem,
            "title": f"{j['die']}/{j['type']} {j['status']} {j['src']}"}
    rbash(host, f"cat > {shlex.quote(rev)}/review.json <<'EOF'\n{json.dumps(meta)}\nEOF\n", timeout=60)
    unit = f"ap-{j['id']}-review"
    logf = AP_DIR / "jobs" / j["id"] / "review.log"
    argv = [OT_RUN, "--mem", str(mem), "--threads", "2", "--dir", rev, "--no-spill", "--",
            "bash", f"{rev}/tools/render_review.sh", rev]
    if launch_unit(unit, logf, argv):
        j.update(review_dir=f"{host}:{rev}", review_unit=unit, review_log=str(logf), review_started=time.time())
        set_status(st, j, "REVIEW-" + j["status"], "render job")
        log(f"REVIEW {j['id']} render job -> {host}:{rev}")
    else:
        record_failure(st, j)


def poll_reviews(st):
    for j in list(st["jobs"].values()):
        if not str(j.get("status", "")).startswith("REVIEW-"):
            continue
        if unit_active(j["review_unit"]) and time.time() - j["review_started"] < 4 * 3600:
            continue
        j["status_cls"] = j["status"][7:]
        try:
            txt = Path(j["review_log"]).read_text(errors="replace")
        except OSError:
            txt = ""
        j["png"] = ";".join(sorted(set(re.findall(r"AP_REVIEW_PNG (\S+)", txt))))
        j["paths"] = ";".join(sorted(set(re.findall(r"AP_REVIEW_PATHS (\S+)", txt))))
        if not j["png"]:
            log(f"REVIEW render {j['id']} produced no PNG (see {j['review_log']}); recording paths only")
        j["status"] = j["status_cls"]
        record_failure(st, j)


def record_failure(st, j):
    cls = j["status"]
    host = ssh_host(j.get("probe") or j["host"])
    if cls == "NEAR-MISS":
        tsv_append("review.tsv", j["id"], [j["die"], j["type"], j["src"], host, j["kit"], cls, j.get("reasons", ""),
                                           j.get("review_dir", ""), j.get("png", ""), j.get("paths", ""),
                                           j.get("lane", "")])
    else:
        tsv_append("structural.tsv", j["id"], [j["die"], j["type"], j["src"], host, j["kit"],
                                               f"{cls}/{j.get('kind', '')}", j.get("reasons", ""),
                                               j.get("review_dir", ""), j.get("lane", "")])
    log(f"RECORDED {j['id']} {j['die']}/{j['type']} {cls} -> {'review' if cls == 'NEAR-MISS' else 'structural'}.tsv")
    if j.get("kind") == "no-signoff":
        log(f"KEEP {j['id']}: flow exit 0 without signoff.json (sign-off tool problem?) -- data kept for a GOAL=post re-sign")
        set_status(st, j, "DONE-" + cls, j.get("reasons", "")[:200])
        return
    # owner rule: failed job data deleted at once (logs, reports, signoff records and the review bundle stay)
    d = rpy(host, PROBE_DELETE, {"kit": j["path"], "dry": DRY}, timeout=1800)
    if d.get("error") or d.get("errors"):
        log(f"DELETE {j['id']} on {host}: {d.get('error') or d.get('errors')}; retry next tick")
        j["delete_pending"] = True
    else:
        j["delete_pending"] = False
        log(f"DELETED {j['id']} bulk data on {host}: {', '.join(d.get('deleted') or ['nothing left'])}")
    set_status(st, j, "DONE-" + cls, j.get("reasons", "")[:200])


def retry_pending(st):
    for j in list(st["jobs"].values()):
        if j.get("status") == "SIGNED" and not DRY:
            archive(st, j)
        elif str(j.get("status", "")).startswith("DONE-") and j.get("delete_pending"):
            host = ssh_host(j.get("probe") or j["host"])
            d = rpy(host, PROBE_DELETE, {"kit": j["path"], "dry": DRY}, timeout=1800)
            if not (d.get("error") or d.get("errors")):
                j["delete_pending"] = False
                log(f"DELETED {j['id']} bulk data on {host}: {', '.join(d.get('deleted') or ['nothing left'])}")
                save_state(st)


# ------------------------------------------------------------------------------------------------ commands
def tick(args):
    global DRY
    DRY = args.dry_run
    AP_DIR.mkdir(parents=True, exist_ok=True)
    lockf = open(AP_DIR / ".tick.lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("autopilot: previous tick still running", file=sys.stderr)
        return 0
    st = load_state()
    rows = parse_queue(read_queue_text())
    geom_text = read_coord("lanes/GEOM-REVIEW.md")
    resolve_geom(rows, geom_text)
    poll_running(st)
    poll_reviews(st)
    retry_pending(st)
    admit_new(st, rows)
    save_state(st)
    try:
        write_loop_gaps(st, rows, geom_text)
    except Exception as e:                             # the gap report must never stop the chain
        log(f"LOOP-GAPS failed: {type(e).__name__}: {e}")
    counts = {}
    for j in st["jobs"].values():
        counts[j.get("status")] = counts.get(j.get("status"), 0) + 1
    print(f"{now_s()} autopilot tick done: queue {len(rows)} rows; " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))))
    return 0


def read_tsv_rows(name):
    out = []
    try:
        lines = (AP_DIR / name).read_text().splitlines()
    except OSError:
        return out
    head = lines[0].split("\t") if lines else []
    for line in lines[1:]:
        f = dict(zip(head, line.split("\t")))
        if f.get("id"):
            out.append({"t": LG.parse_ts(f.get("time", "")), "id": f["id"], "type": f.get("type", ""),
                        "lane": f.get("lane", ""), "file": name, "die": f.get("die", ""), "cls": f.get("class", ""),
                        "review_dir": f.get("review_dir", "")})
    return out


def write_loop_gaps(st, rows, geom_text):
    """LOOP-GAPS.txt (owner 2026-10-25: the design -> review -> route -> review -> design loop must never sit idle);
    read-only apart from the GEOM PASS auto-submit done by resolve_geom + admit_new"""
    now = time.time()
    jobs = list(st["jobs"].values())
    submitted_tags = {geom_tag(j.get("geom_ref", "")) for j in jobs
                      if j.get("status") not in ("WAIT-GEOM", "REJECTED", None) and (j.get("attempts") or j.get("adopted"))}
    gaps = LG.gaps_geom(geom_text, now, submitted_tags)
    gaps += LG.gaps_runs([j for j in jobs if j.get("status") == "RUNNING" or str(j.get("status")).startswith("REVIEW-")
                          or j.get("status") == "SIGNED"], now)
    trows = read_tsv_rows("review.tsv") + read_tsv_rows("structural.tsv")
    lanes = {r["lane"] for r in trows if r["lane"]}
    lane_texts = {}
    for ln in lanes:
        t = read_coord(f"lanes/{ln}.md")
        lane_texts[ln] = t if t else None
    gaps += LG.gaps_review(trows, lane_texts, geom_text, now)
    gaps += LG.gaps_ready(read_coord("lanes/COORD-REVIEW-QUEUE.md"), now)
    waiting = [r for r in rows.values() if not r["error"] and
               (st["jobs"].get(r["id"]) or {}).get("status") in (None, "WAIT-GEOM")]
    rc, out, _ = sh([OT_RUN, "--status"], timeout=120)
    if rc == 0:
        gaps += LG.gaps_hosts(out, len(waiting), now)
    else:
        gaps.append((now, f"OT-RUN-STATUS unavailable (rc {rc}); host idleness not checked"))
    head = []
    try:                                               # OWNERSHIP table (owner 2026-10-25); never stops the gap report
        orows, ogaps, head = OWN.build(ownership_inputs(st, geom_text, trows), now)
        gaps += ogaps
        write_file("OWNERS.tsv", OWN.to_tsv(orows, now))
    except Exception as e:
        log(f"OWNERS failed: {type(e).__name__}: {e}")
        head = [f"# OWNERSHIP unavailable this tick: {type(e).__name__}: {str(e)[:200]}"]
    text = LG.render(gaps, now, head)
    if DRY:
        print(text, end="")
        return
    tmp = AP_DIR / f".LOOP-GAPS.txt.{os.getpid()}"
    tmp.write_text(text)
    os.replace(tmp, AP_DIR / "LOOP-GAPS.txt")


def write_file(name, text):
    if DRY:
        print(f"[dry] {name}: {len(text.splitlines())} lines")
        return
    tmp = AP_DIR / f".{name}.{os.getpid()}"
    tmp.write_text(text)
    os.replace(tmp, AP_DIR / name)


def read_repo(rel):
    """a file of origin/main on the hub checkout (read-only: git show); '' if missing"""
    if REPO_FILES:
        try:
            return (Path(REPO_FILES) / rel).read_text(errors="replace")
        except OSError:
            return ""
    rc, out, _ = sh(["git", "-C", str(REPO), "show", f"origin/main:{rel}"], timeout=60)
    return out if rc == 0 else ""


def list_tree(rel, coord=False):
    """file names under a dir of origin/main (or of origin/coord/state when coord)"""
    base = COORD_FILES if coord else REPO_FILES
    if base:
        d = Path(base) / rel
        return sorted(p.name for p in d.iterdir() if p.is_file()) if d.is_dir() else []
    git = COORD if coord else REPO
    ref = "origin/coord/state" if coord else "origin/main"
    rc, out, _ = sh(["git", "-C", str(git), "ls-tree", "--name-only", f"{ref}:{rel}"], timeout=60)
    return out.split() if rc == 0 else []


def _json(text):
    try:
        return json.loads(text) if text.strip() else None
    except ValueError:
        return None


def hub_otrun_clients():
    """live ot-run clients on the hub (every ot-run client runs here) -> [(pid, elapsed_s, args)]"""
    rc, out, _ = sh(["ps", "-eo", "pid=,etimes=,args="], timeout=60)
    res = []
    for line in out.splitlines():
        f = line.split(None, 2)
        if len(f) == 3 and f[0].isdigit() and re.search(r"(^|/)ot-run --mem ", f[2]) and "--status" not in f[2]:
            res.append((int(f[0]), int(f[1]) if f[1].isdigit() else 0, f[2]))
    return res


def ownership_inputs(st, geom_text, trows):
    if not REPO_FILES:
        sh(["git", "-C", str(REPO), "fetch", "-q", "origin", "main"], timeout=180)
    plans, proto = {}, {}
    gnames = list_tree("results/proto_1025/geom")
    rnames = list_tree("results/proto_1025/g2")
    for die, pdir, pname in OWN.DIES:
        plans[die] = _json(read_repo(f"physical/die_plan/{pdir}/die_plan.json"))
        proto[die] = {
            "geom": {n: _json(read_repo(f"results/proto_1025/geom/{n}")) for n in gnames
                     if n.endswith(".json") and n.startswith(pname)},
            "g2": {n: _json(read_repo(f"results/proto_1025/g2/{n}")) for n in rnames
                   if n.endswith(".json") and n.startswith("res_" + pname)}}
    try:
        cache = json.loads(RELEASE_CACHE.read_text())
    except (OSError, ValueError):
        cache = None
    lane_texts = {}
    for n in list_tree("lanes", coord=True):
        if n.endswith(".md"):
            lane_texts[n[:-3]] = read_coord(f"lanes/{n}")
    lane_texts.pop("GEOM-REVIEW", None)               # read once, as geom_text
    return dict(plans=plans, proto=proto, cache=cache, jobs=list(st["jobs"].values()), trows=trows,
                geom_text=geom_text, lane_texts=lane_texts, live=hub_otrun_clients())


def status(args):
    st = load_state()
    for j in sorted(st["jobs"].values(), key=lambda j: j.get("updated", 0)):
        print(f"{j.get('id')}  {str(j.get('status')):22s} {j.get('die', '')}/{j.get('type', '')}  {j.get('kit')}  "
              f"{(j.get('history') or [['', '', '']])[-1][2][:80]}")
    return 0


def classify_cmd(args):
    host, path = args.kit.split(":", 1)
    c = rpy(host, PROBE_CLASSIFY, {"kit": path, "since": args.since, "goal": args.goal})
    print(json.dumps(c, indent=1)[:4000])
    if not c.get("error"):
        print("CLASS", *classify(c, {"exit": args.exit}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("tick")
    t.add_argument("--dry-run", action="store_true")
    sp.add_parser("status")
    c = sp.add_parser("classify")
    c.add_argument("kit")
    c.add_argument("--since", type=float, default=0)
    c.add_argument("--goal", default="route")
    c.add_argument("--exit", type=int, default=None)
    a = ap.parse_args(argv)
    return {"tick": tick, "status": status, "classify": classify_cmd}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
