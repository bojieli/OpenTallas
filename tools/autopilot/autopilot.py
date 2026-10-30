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
import fnmatch
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
import auto_geom as AG  # noqa: E402
import kit_wave as KW  # noqa: E402

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
# ot-run's signal log (tools/fleet/ot-run log_signal): an explicit `ot-run --cancel` SIGTERMs the client, which then
# exits 143 like an OOM kill; this log tells the two apart (FLOW-GEN-1 10-28, AP 5474a1c7a4cf resubmitted at 48 GB)
OT_RUN_SIGNALS = Path(os.environ.get("AP_OT_RUN_SIGNALS", str(HOME / ".local/state/ot-run/signals.log")))
IMAGE = os.environ.get("AP_IMAGE", "openroad/orfs:asap7lock")
ARCHIVE_ROOT = "/srv/opentallas-scratch2/claude/autopilot/closed"
REVIEW_ROOT = "/srv/opentallas-scratch2/claude/autopilot/review"
# EPYC1-RETIRE 2026-10-26: the hub moves epyc1 -> intel2.  OT_HUB_NAME (set in the hub units) names the host this runs on;
# that host is "localhost" for ssh, every other alias (incl. a retired/old hub) is a plain worker.
HUB_NAME = os.environ.get("OT_HUB_NAME", "epyc1")
HUB_ALIASES = {"epyc1": ("epyc1", "tender-ray", "ubuntu-epyc1"), "intel2": ("intel2", "tolerant-swine")}
if HUB_NAME == "epyc1":
    MIRROR = {"intel2": "localhost"}                   # archive mirror host per source host (default intel2)
    MIRROR_DEFAULT = "intel2"                           # EPYC3-RETIRE 2026-10-25: was epyc3 (terminated); intel2 = hub standby
else:
    MIRROR = {"localhost": "intel1", HUB_NAME: "intel1"}   # the hub's own archives mirror to intel1
    MIRROR_DEFAULT = "localhost"                        # every other host's archives mirror to the hub
CELL_CAP = 400_000
NEAR_WNS_PS = -30.0
NEAR_DRC_MAX = 50
RENDER_MEM_GB = 8
ORPHAN_IDLE_S = 3 * 3600
CHAIN_VERSION = 2
MAX_SUBMIT_PER_TICK = int(os.environ.get("AP_MAX_SUBMIT", "12"))
MAX_NOTRUN = 3                                          # 'NOT RUN' (never admitted) resubmits
KIT_RE = re.compile(r"^([A-Za-z0-9_.-]+):(/srv/opentallas-scratch2?/claude/[A-Za-z0-9_./+=-]+)$")
SRC_RE = re.compile(r"^[A-Za-z0-9_./-]+@[0-9a-f]{7,40}$")
GEOM_OK = ("PASS", "PASS-COND")
QCOLS = ["die", "type", "kit", "src", "geom", "geom_ref", "mem_gb", "cells", "lane", "goal", "runner", "threads", "mode", "canary_fix",
         "flow"]
# PER-DIE FLOW RELEASES (METHODOLOGY 12.9e, OWNER 2026-10-26): flow-YYYYMMDD-a|b covers every die;
# flow-YYYYMMDD-a|b-<die tag> covers only that die (route holds / provenance lift per die; a die whose canary is
# pending keeps its previous tag).
FLOW_TAG_RE = re.compile(r"^flow-\d{8}-[a-z](?:-(qc|s81|head|kv|hbm))?$")
DIE_FLOW_TAG = {"qwen_compute": "qc", "s81": "s81", "cp1": "s81", "s81_head": "head", "qwen_kvsys": "kv", "kv": "kv",
                "hbm": "hbm"}


def tag_covers(tag, die=None):
    """True when flow release tag `tag` covers die `die` (die None = any tag counts)"""
    m = FLOW_TAG_RE.match(tag or "")
    if not m:
        return False
    return die is None or m.group(1) is None or DIE_FLOW_TAG.get(die) == m.group(1)
FLOW_TAGS_CHECKED = 30                                   # newest release tags compared with a src commit
# queue/job states that are re-judged every tick (never submitted yet)
WAITS = (None, "WAIT-GEOM", "WAIT-CANARY", "WAIT-PATH-GATE", "WAIT-PLAN-DELTA", "REJECTED", "WITHDRAWN")
# closure order (owner 2026-10-25 18:45): release-tree die key -> path name in lanes/PATH-FREEZE.md
DIE_PATH = {"s81": "S81", "s81_head": "S81", "cp1": "S81", "qwen_compute": "QC", "qwen_kvsys": "KV", "hbm": "HBM"}
GATE_ITEMS = ("GRT0", "CLOCK-ROUTE", "PATH-STA")
# Rule 1 amendment (owner 2026-10-25 ~21:00): 'FROZEN <NAME> plan@sha' in lanes/PATH-FREEZE.md freezes that DIE's plan and
# ALL its tiles (path and non-path) route to sign-off.  FROZEN name -> release-tree die key (explicit, no guessing):
FROZEN_DIE = {"QC": "qwen_compute", "S81-HEAD": "s81_head", "S81": "s81", "KV": "qwen_kvsys", "HBM": "hbm"}
TSV_HEAD = {
    "signed.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tarchive\tmirror\ttt_wns_ps\tff_wns_ps\tlane\tsrc_commit\tflow_tag",
    "unversioned.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tarchive\ttt_wns_ps\tff_wns_ps\twhy\tlane",
    "trial.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tclass\ttt_wns_ps\tff_wns_ps\tgate\tlane",
    "review.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tclass\treasons\treview_dir\tpng\tpaths\tlane",
    "structural.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tclass\treasons\treview_dir\tlane",
    "provisional.tsv": "time\tid\tdie\ttype\tsrc\thost\tkit\tlocal_verdict\treasons\tlane",
    "geom_alerts.tsv": "time\tid\tdie\ttype\tsrc\tkit\tstatus\tunit\tgeom_was\tverdict\tlane",
    AG.AG_TSV: AG.AG_HEAD,
}
GEOM_TEXT = ""                                         # lanes/GEOM-REVIEW.md of this tick (AUTO-GEOM revocation)
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
    return "localhost" if host == "localhost" or host in HUB_ALIASES.get(HUB_NAME, (HUB_NAME,)) else host


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


def _kit_ident(r):
    return (r["type"], r["kit"], r["src"].split("@")[-1], r["id"])


def geom_groups(rows):
    """{GEOM tag: [(type, kit, src sha, row id), ...]} over the valid queued rows: a verdict applies to a row only when
    the reply names its type / kit dir / row id, or a sha / __suffix no other row of the tag shares (2026-10-25
    btab_s7 + prog_s7 share PATH-QC-SRAMIF-S7 and @90bf56dfa)"""
    out = {}
    for r in rows.values():
        if r["error"] or r.get("mode") == "withdraw" or not r["geom_ref"]:
            continue
        tag = geom_tag(r["geom_ref"])
        if tag:
            out.setdefault(tag, []).append(_kit_ident(r))
    return out


def resolve_geom(rows, geom_text):
    """GEOM PASS -> submit within one tick: a row queued before its verdict (geom REQ/WAIT, geom_ref = the GEOM REQ
    tag) takes the verdict from lanes/GEOM-REVIEW.md once a REPLY/VERDICT of that tag names the kit (by type, kit dir
    basename or row id; the shared branch sha alone never names one of several rows under the tag -> AMBIGUOUS-GEOM).
    Re-resolved EVERY tick and the LATEST verdict of that tag naming the kit wins (LG.geom_verdicts keeps the newest
    reply after the newest REQ), so a later FAIL demotes an earlier PASS-COND (2026-10-25: R5 9a237c656129 got a
    plan-only PASS-COND 09:59, post-CTS FAIL 10:06).  A row queued as PASS/PASS-COND by hand with a tagged geom_ref is
    checked too, but only ever DEMOTED (latest verdict FAIL), never changed by a PASS.  admit_new never demotes a job
    that is already submitted: it records a geom_alerts.tsv row + a LOOP-GAPS line for the coordinator instead."""
    groups = geom_groups(rows)
    for r in rows.values():
        if r["error"] or r.get("mode") == "withdraw" or not r["geom_ref"]:
            continue
        tag = geom_tag(r["geom_ref"])
        if not tag:
            continue
        v = LG.geom_verdicts(geom_text, tag, r["type"], _kit_ident(r)[2], kit=r["kit"], rid=r["id"],
                             others=[g for g in groups.get(tag, []) if g[3] != r["id"]])
        if not v:
            continue
        queued_ok = r["geom"].upper() in GEOM_OK
        if queued_ok and v[0] in GEOM_OK:
            continue                                   # a hand-entered PASS stays exactly as the lane wrote it
        r["geom_auto"] = f"{v[0]} {time.strftime('%Y-%m-%d %H:%M', time.localtime(v[1]))}: {v[2].strip()[:200]}"
        if queued_ok:
            r["geom_queued"] = r["geom"]
        r["geom"] = v[0]
        r["geom_ref"] = f"GEOM-REVIEW [{tag}] {time.strftime('%m-%d %H:%M', time.localtime(v[1]))}"


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
    if r["goal"] not in ("", "auto", "route", "finish", "cts", "grt"):
        return "goal must be route|finish|auto|cts|grt"
    if r["goal"] in ("cts", "grt") and not r["runner"]:
        return f"{r['goal']} diagnostic goal requires an explicit {r['goal'].upper()}-only runner"
    if r["threads"] and not r["threads"].isdigit():
        return "threads not an integer"
    if r["runner"] and not r["runner"].startswith("/"):
        return "runner must be an absolute path"
    if r["mode"] not in ("", "submit", "adopt", "withdraw", "trial"):
        return "mode must be submit|adopt|withdraw|trial"
    if r["flow"] and not FLOW_TAG_RE.match(r["flow"]):
        return "flow must be a flow release tag flow-YYYYMMDD-a|b[-qc|s81|head|kv|hbm] (or empty: derived from src)"
    if r["mode"] == "withdraw" and not r["geom_ref"].strip():
        return "withdraw requires an explicit reason/evidence in geom_ref"
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
    if not new:
        upgrade_header(p, TSV_HEAD[name])
    with open(p, "a") as f:
        if new:
            f.write(TSV_HEAD[name] + "\n")
        f.write("\t".join([now_s(), jid] + [str(x).replace("\t", " ").replace("\n", " ") for x in fields]) + "\n")


def upgrade_header(p, head):
    """a TSV whose header is a prefix of the current one (columns appended, e.g. signed.tsv src_commit/flow_tag
    2026-10-25) gets the new header line in place; rows are never rewritten"""
    lines = p.read_text().splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") == head or not head.startswith(lines[0].rstrip("\n") + "\t"):
        return
    tmp = p.with_name(f".{p.name}.{os.getpid()}")
    tmp.write_text(head + "\n" + "".join(lines[1:]))
    os.replace(tmp, p)


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
# only real route outputs count as routed (ORFS 5_route / 5_2_route / 5_3_fillcell / 6_*): 5_1_grt and the GRT hold
# step's 5_hold_batch_*.odb checkpoints are placed-kit state, not a route (2026-10-25 PATH-QC had to move them aside)
ROUTED = re.compile(r"^(?:5_route|5_2_route|5_3_fillcell|6_[0-9A-Za-z_]+)\.odb$")
out["routed"] = sorted({os.path.basename(p) for p in glob.glob(os.path.join(B, "*.odb"))
                        if ROUTED.match(os.path.basename(p))})
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
# CRASH-TRIAGE 10-25 (4 rows: dsfd_qbank_N, SRAMIF btab_s8/prog_s8b/rp1_f62): the kit's signoff.py was copied without
# the helpers it reads/imports -> the route finished and sign-off died (FileNotFoundError / ModuleNotFoundError).
def _txt(p):
    try:
        with open(p, errors="replace") as f: return f.read()
    except Exception: return ""
st = _txt(os.path.join(K, "signoff.py"))
need = {"pair_skew.tcl": '"pair_skew.tcl"' in st, "sdc_lint.py": "import sdc_lint" in st,
        "face_guard.py": "import face_guard" in st, "io_hold_qualification.py": "io_hold_qualification import" in st}
out["signoff_missing"] = sorted(n for n, v in need.items() if v and not os.path.isfile(os.path.join(K, n)))
if not os.path.isfile(os.path.join(K, "lec.py")): out["signoff_missing"].append("lec.py")
# the goals on which the runner runs signoff.py (the 'if' guarding the signoff.py call); macro kits without GDS
rt = _txt(out["runner"]).splitlines() if out["runner"] else []
goals = set()
for i, line in enumerate(rt):
    if "signoff.py" in line and not line.lstrip().startswith("#"):
        for w in rt[max(0, i - 3):i + 1]:
            goals.update(re.findall(r'\$\{?GOAL\}?"?\s*=\s*"?(\w+)', w))
out["signoff_goals"] = sorted(goals)
out["route_runs_finish"] = any("do-finish" in l and "route" in l for l in rt)
cfg = _txt(os.path.join(K, "config.mk"))
out["gds_gap"] = bool(re.search(r"^export ADDITIONAL_LEFS", cfg, re.M)) and "ADDITIONAL_GDS" not in cfg
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
    out["signoff"] = {"path": so[-1], "verdict": d.get("verdict"), "local_verdict": d.get("local_verdict"),
        "release_qualified": d.get("release_qualified"), "parent_qualification": d.get("parent_qualification"), "reasons": d.get("reasons"),
        "fails": sorted(k for k, v in c.items() if isinstance(v, dict) and v.get("verdict") == "FAIL"),
        "tt_wns": (c.get("setup_tt") or {}).get("wns_ps"), "ff_wns": (c.get("hold_ff") or {}).get("wns_ps"),
        "drc": (c.get("drc") or {}).get("count"), "antenna": (c.get("antenna") or {}).get("count"),
        "pg": (c.get("pg") or {}).get("verdict"),
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
       "oom": r"Error 137[^\n]*|\] Error 247[^\n]*|\bKilled\b[^\n]*|[Oo]ut of memory[^\n]*|std::bad_alloc[^\n]*|OOMKilled[^\n]*",
       # design gates that print their verdict but write no FAIL_PREFLOOR/FAIL_POSTCTS marker (custom runners)
       "gate_fail": r"(?m)^(?:CORE_PREFLIGHT|KIT_PREFLIGHT|RP1_GATE|SDC_LINT|S6_GRT_GATE|OT_HOLD_GATE) FAIL\b[^\n]*",
       "orfs_error": r"\[ERROR [A-Z]+-\d+\][^\n]*"}
for k, p in pat.items():
    if k == "orfs_error":
        # Hold repair catches bounded RSZ errors and continues. Diagnose the
        # terminal tool error rather than an earlier caught repair chunk.
        errors = re.findall(p, runlog) or re.findall(p, txt)
        if errors:
            out[k] = errors[-1][:300]
            out["orfs_errors"] = [e[:300] for e in errors[-5:]]
    else:
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
out["goal"] = goal
chain_records = glob.glob(os.path.join(K, "autopilot_chain*.json"))
out["chain"] = jl(max(chain_records, key=os.path.getmtime)) if chain_records else None
cts = [p for p in glob.glob(os.path.join(K, "run", "results", "asap7", "*", "base", "4_cts.odb")) if os.path.getmtime(p) >= since]
if cts: out["cts_odb"] = max(cts, key=os.path.getmtime)
grt = [p for p in glob.glob(os.path.join(K, "run", "results", "asap7", "*", "base", "5_1_grt.odb")) if os.path.getmtime(p) >= since]
if grt: out["grt_odb"] = max(grt, key=os.path.getmtime)
route = [p for p in glob.glob(os.path.join(K, "run", "results", "asap7", "*", "base", "*.odb"))
         if re.match(r"^(?:5_route|5_2_route|5_3_fillcell|6_[0-9A-Za-z_]+)\.odb$", os.path.basename(p))]
if route: out["route_odb"] = max(route, key=os.path.getmtime)
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
for p in glob.glob(os.path.join(K, "lec_routed_autopilot_*")):
    if os.path.isdir(p):
        for f in ("lec.json", "lec.log"):
            if os.path.isfile(os.path.join(p, f)):
                cp(os.path.join(p, f), os.path.join("kit", os.path.basename(p), f))
for p in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base")):
    cp(p, "logs")
with open(os.path.join(A, "AUTOPILOT.json"), "w") as f:
    json.dump(a["record"], f, indent=1)
V = a.get("view") or {}
if V.get("module"):
    vd = os.path.join(A, "view", V["module"])
    os.makedirs(vd, exist_ok=True)
    for rel, src in sorted((V.get("files") or {}).items()):
        shutil.copy2(src, os.path.join(vd, rel))
    if V.get("core"):
        with open(os.path.join(vd, V["module"] + ".core.json"), "w") as f: json.dump(V["core"], f, indent=1)
    with open(os.path.join(vd, "provenance.json"), "w") as f: json.dump(V["provenance"], f, indent=1)
    with open(os.path.join(vd, "gates.json"), "w") as f: json.dump(V["gates"], f, indent=1)
    out["view"] = vd
if V.get("gates"):
    with open(os.path.join(A, "gates.json"), "w") as f: json.dump(V["gates"], f, indent=1)
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

PROBE_VIEW_READ = r"""
import json, os, sys, glob, hashlib
a = json.loads(sys.argv[1]); K = a["kit"]; B = a["base"]; S = a["signoff_dir"]; out = {}
def jl(p):
    try:
        return json.load(open(p))
    except Exception:
        return None
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
out["core"] = jl(os.path.join(K, "core.json")); out["freeze"] = jl(os.path.join(K, "freeze.json"))
pf = os.path.join(K, "pins.json")
out["pins"] = jl(pf); out["pins_kit_sha256"] = sha(pf) if os.path.isfile(pf) else None
mod = None
for d in (out["freeze"], out["core"]):
    if isinstance(d, dict) and (d.get("module") or d.get("design")):
        mod = d.get("module") or d.get("design"); break
if not mod:
    lefs = [f for f in glob.glob(os.path.join(B, "*.lef")) if not f.endswith(("_bloated.lef", "_pershape.lef"))]
    mod = os.path.basename(lefs[0])[:-4] if len(lefs) == 1 else None
out["module"] = mod
files = {}
if mod:
    for rel, cands in ((mod + ".lef", [os.path.join(K, "views", mod + ".lef"), os.path.join(B, mod + ".lef")]),
                       (mod + "_tt.lib", [os.path.join(K, "views", mod + "_tt.lib"), os.path.join(S, mod + "_tt.lib")]),
                       (mod + "_ff.lib", [os.path.join(K, "views", mod + "_ff.lib"), os.path.join(S, mod + "_ff.lib")])):
        for c in cands:
            if os.path.isfile(c):
                files[rel] = c; break
out["files"] = files
print("AP_JSON " + json.dumps(out))
"""


PIN_CANON = None


def pins_canon(pins_doc, outline):
    """die_sta_related.canon_sha256(canon_pins()) -- the shared die STA model's own pin identity (no fork)"""
    global PIN_CANON
    if PIN_CANON is None:
        sys.path.insert(0, str(HERE.parent / "die_plan"))
        import die_sta_related as DSR
        PIN_CANON = DSR
    return PIN_CANON.canon_sha256(PIN_CANON.canon_pins(pins_doc, outline))


def pins_doc(raw):
    """kit pins.json -> the {'pins': [{'name': ...}]} doc canon_pins reads; kit lists carry bus/bit instead of name"""
    rows = raw.get("pins") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("pins.json has no pin list")
    out = []
    for p in rows:
        p = dict(p)
        if "name" not in p and "bus" in p:
            p["name"] = p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]"
        out.append(p)
    doc = dict(raw) if isinstance(raw, dict) else {}
    doc["pins"] = out
    return doc


def view_payload(r, j, so):
    """(view dict for PROBE_ARCHIVE, gates dict, problems): publication of the signed view the die STA consumes
    (view/<module>/{lef, _tt/_ff lib, core.json, provenance.json(kit.pins_canon_sha256), gates.json})"""
    fz = r.get("freeze") if isinstance(r.get("freeze"), dict) else {}
    core = r.get("core") if isinstance(r.get("core"), dict) else {}
    kitblk = dict(fz or {k: core.get(k) for k in ("module", "type", "outline_um", "plan_sha256", "pins_file",
                                                    "pins_sha256", "kit_hash", "period_ps") if k in core})
    outline = kitblk.get("outline_um") or core.get("outline_um")
    problems = []
    canon, basis = kitblk.get("pins_canon_sha256"), "kit freeze record"
    if not canon and r.get("pins"):
        try:
            canon = pins_canon(pins_doc(r["pins"]), outline)
            basis = ("kit pins.json = plan pins file (sha256 match)" if r.get("pins_kit_sha256") and
                     r.get("pins_kit_sha256") == kitblk.get("pins_sha256") else "kit pins.json")
        except Exception as e:                       # noqa: BLE001 -- recorded, the view is then incomplete
            problems.append(f"pins_canon_sha256: {type(e).__name__}: {e}")
    if not canon:
        problems.append("no pins_canon_sha256 (kit has no pins.json / freeze pins_canon_sha256)")
    kitblk.update(pins_canon_sha256=canon, pins_canon_basis=basis, outline_um=outline)
    mod = r.get("module")
    files = r.get("files") or {}
    for need in ((mod or "?") + ".lef", (mod or "?") + "_tt.lib", (mod or "?") + "_ff.lib"):
        if need not in files:
            problems.append(f"view file {need} not found in kit/views, base or signoff dir")
    chain = j.get("chain") or {}
    gates = dict(schema="opentallas.autopilot.gates.v1", id=j["id"], die=j["die"], type=j["type"], src=j["src"],
                 geom=f"{j.get('geom')} {j.get('geom_ref', '')}".strip(), preflight="PASS (kit_preflight before runner)",
                 signoff=so.get("verdict"), signoff_record=so.get("path"), tt_wns_ps=so.get("tt_wns"),
                 ff_wns_ps=so.get("ff_wns"), gates=chain.get("gates") or {}, routed_lec=chain.get("lec_verdict"),
                 routed_lec_all_shown=chain.get("lec_all_shown"), routed_lec_record=chain.get("lec"),
                 lec_tool=chain.get("lec_tool"), admission_tools_sha256=j.get("admission_tools_sha256"),
                 view_complete=not problems, view_problems=problems)
    prov = dict(kit=kitblk, verdict="SIGNED (autopilot: signoff.py + routed LEC EQUIVALENT all_shown)",
                views_status="signoff" if not problems else "incomplete: " + "; ".join(problems),
                src=j["src"], src_commit=j.get("src_commit"), flow_tag=j.get("flow_tag"), autopilot_id=j["id"])
    if core:
        core = dict(core)
        cl = (so.get("core_latency") or {}).get("measured")
        if cl:
            core["clock_latency_measured"] = cl
    return dict(module=mod, files=files, core=core or None, provenance=prov, gates=gates), gates, problems


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
    if client.get("cancelled"):
        # an explicit ot-run --cancel (exit 143 = SIGTERM): an operator decision, never an infra crash or a resubmit
        return "CANCELLED", "cancelled", client["cancelled"]
    """pure function: (classify-probe result, client outcome) -> (class, kind, reasons)
    class: SIGNED | NEAR-MISS | STRUCTURAL | CRASH ; kind refines it (infra / tool / ...)"""
    if client.get("admission_tools_fail"):
        return "CRASH", "admission-tools", client["admission_tools_fail"]
    if client.get("preflight_fail"):
        return "STRUCTURAL", "preflight", client["preflight_fail"]
    so = c.get("signoff")
    if c.get("goal") == "grt" and (so or c.get("route_odb")):
        return "STRUCTURAL", "diagnostic-overrun", "GRT-only runner produced detailed-route/signoff output; no release scope"
    if so:
        if so.get("verdict") == "LOCAL_PASS_NEEDS_PARENT" and so.get("local_verdict") == "SIGNED":
            return "WAIT-PARENT", "parent-receipt-pending", "; ".join(so.get("reasons") or []) or "matching actual parent seam receipt required"
        if so.get("verdict") == "SIGNED" and so.get("pg") != "PASS":
            # FLOW 10-26 PG: a sign-off without a passing supply-binding census of its ODB is not a sign-off
            # (s8b d73a0fbb938f: 108 dont_touch spine buffers with VDD/VSS open; kit signoff.py predates the check)
            return "STRUCTURAL", "pg-unbound", f"pg: {so.get('pg') or 'NOT RUN'} (supply-binding census of the signed ODB)"
        if so.get("verdict") == "SIGNED":
            return "SIGNED", "signed", "SIGNED"
        reasons = "; ".join(so.get("reasons") or []) or "NOT SIGNED"
        fails = set(so.get("fails") or [])
        tt, ff = so.get("tt_wns"), so.get("ff_wns")
        drc = so.get("drc") or 0
        ov = c.get("grt_overflow")
        structural_fail = fails & {"clock", "sdc_lint", "face_guard", "unconstrained", "antenna", "pg"}
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
    if c.get("gate_fail"):
        # CRASH-TRIAGE 10-25: 8 rows (CORE_PREFLIGHT shared, RP1_GATE FF hold, SDC_LINT) were design verdicts
        # filed as CRASH because the runner printed the gate line without a FAIL_* marker file
        return "STRUCTURAL", "gate", c["gate_fail"]
    if c.get("segfault"):
        return "CRASH", "tool-segfault", c["segfault"]
    if client.get("not_run"):
        return "CRASH", "infra-notrun", client.get("msg", "ot-run NOT RUN")
    if client.get("not_completed"):
        return "CRASH", "infra-lost", client.get("msg", "ot-run NOT COMPLETED")
    if c.get("oom") or client.get("exit") in (137, 143):
        return "CRASH", "infra-oom", c.get("oom") or f"exit {client.get('exit')}"
    if client.get("exit") == 0 and c.get("goal") == "grt" and c.get("grt_odb"):
        if c.get("grt_overflow") not in (None, 0):
            return "STRUCTURAL", "grt-overflow", f"GRT-only overflow {c['grt_overflow']}"
        return "GRT-DONE", "grt-only", (f"GRT-only diagnostic finished: {c['grt_odb']}; overflow {c.get('grt_overflow')} "
                                        "-- no sign-off scope; collect routed-RC timing/clock and review before DRT")
    if client.get("exit") == 0 and c.get("goal") == "cts" and c.get("cts_odb"):
        return "CTS-DONE", "cts-only", (f"CTS-only diagnostic finished: {c['cts_odb']} -- no sign-off scope; collect "
                                        "placement / clock / reset images and review before the next scope")
    if client.get("exit") == 0:
        return "CRASH", "no-signoff", "flow exit 0 but no signoff.json"
    if client.get("exit") is None and not c.get("last_log") and not c.get("runlog_tail"):
        # adopted run that was not live and left no logs: nothing ran here, not a flow error
        return "CRASH", "infra-lost", "no client exit and no run logs (adopted run not live / run data gone)"
    return "CRASH", "flow-error", c.get("orfs_error") or (c.get("runlog_tail") or "")[-300:] or f"exit {client.get('exit')}"


INFRA_KINDS = ("infra-oom", "infra-lost", "infra-notrun", "infra-orphan")


def parse_client_log(text):
    """ot-run client log (+ our AP_RC line) -> outcome dict"""
    o = {}
    for key, prefix in (("admission_tools_fail", "ADMISSION_TOOLS FAIL:"), ("preflight_fail", "KIT_PREFLIGHT FAIL")):
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                o[key] = "\n".join(lines[index:index+6])[:600]
                break
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
    m = [l for l in text.splitlines() if l.startswith("ot-run: interrupted (signal ") and "ot-run --cancel" in l]
    if m:
        o["cancelled"] = m[-1][:300]
    return o


def signals_cancel(j):
    """the ot-run signals.log line recording an explicit `ot-run --cancel` of this job's client (signal from an
    `ot-run --cancel` sender to the ot-run whose --dir is the job's kit, at or after this attempt started), or None"""
    try:
        lines = OT_RUN_SIGNALS.read_text(errors="replace").splitlines()
    except OSError:
        return None
    since = j.get("started", 0) - 60
    for line in reversed(lines):
        if "ot-run --cancel" not in line or not re.search(r" signal \d+ from ", line) \
                or f" dir {j['path']}: " not in line:
            continue
        try:
            t = datetime.datetime.strptime(line.split(" ", 1)[0], "%Y-%m-%dT%H:%M:%S%z").timestamp()
        except ValueError:
            continue
        if t >= since:
            return line[:300]
    return None


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
def process_uses_kit(argv, path):
    """A parent staging directory owns its nested kits even when ot-run spills to another host."""
    path = path.rstrip("/")
    if re.search(re.escape(path) + r"(?=[/\s]|$)", argv):
        return True
    try:
        words = shlex.split(argv)
    except ValueError:
        return True  # malformed live client: retain data until it can be identified
    if not any(w.rsplit("/", 1)[-1] == "ot-run" for w in words):
        return False
    for i, word in enumerate(words):
        candidate = None
        if word in ("--dir", "--stage") and i + 1 < len(words):
            candidate = words[i + 1]
        elif word.startswith(("--dir=", "--stage=")):
            candidate = word.split("=", 1)[1]
        if candidate and candidate.startswith("/srv/opentallas-scratch") and "/claude/" in candidate:
            if path.startswith(candidate.rstrip("/") + "/"):
                return True
    return False


def hub_procs(path):
    """processes on the hub (ot-run clients, local docker run / run_kit.sh) whose command line names the kit dir
    -> [(pid, elapsed_s)]; ot-run clients always run here, also when the job itself spilled to another host"""
    rc, out, _ = sh(["ps", "-eo", "pid=,etimes=,args="], timeout=60)
    pat = re.compile(re.escape(path.rstrip("/")) + r"(?=[/\s]|$)")
    me = os.getpid()
    res = []
    for line in out.splitlines():
        f = line.split(None, 2)
        if len(f) == 3 and f[0].isdigit() and int(f[0]) != me and process_uses_kit(f[2], path) and "autopilot" not in f[2] \
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
    p = rpy(j.get("probe") or j["host"], PROBE_KIT,
            {"kit": j["path"], "runner": j.get("runner", "")}, timeout=120)
    if p.get("exists") is False:
        if j.get("status") != "ORPHAN" or j.get("orphan_kind") != "kit-missing":
            why = f"adopted kit missing on {j['host']}:{j['path']}; no physical verdict or restart inferred"
            log(f"ORPHAN {j['id']}: {why}")
            j["orphan_kind"] = "kit-missing"
            set_status(st, j, "ORPHAN", why)
        return
    if c is None:
        return
    la = p.get("log_age_s")
    if p.get("error") or p.get("busy") is not False or (la is not None and la < 900):
        return
    j.setdefault("client_done_at", time.time())
    finish(st, j, c, {"adopted": True})


def default_goal(runner):
    return "route" if os.path.basename(runner) == "run_kit.sh" else "finish"


def runner_goal(goal, p):
    """CRASH-TRIAGE 10-25: the goal the runner actually signs off on.  gq_rk19 ran GOAL=route through run_kit_hbm.sh
    (sign-off only on finish/post) -> 'flow exit 0 but no signoff.json'; elemB_cv / s81sl_vq ran GOAL=finish = ORFS
    'make finish' = GDS merge of macro LEFs without GDS -> crash after the route.  cts stays cts."""
    sg = p.get("signoff_goals") or []
    if goal in ("cts", "grt") or not sg:
        return goal
    if goal == "finish" and p.get("gds_gap") and "route" in sg and p.get("route_runs_finish"):
        return "route"
    if goal not in sg:
        return "route" if "route" in sg else "finish" if "finish" in sg else goal
    return goal


ADMISSION_BOOTSTRAP = r'''
import base64,json,os,shlex,subprocess,sys,tempfile
from pathlib import Path
meta=json.loads(base64.b64decode(sys.argv[1]))
dest=Path(meta["dir"])
def ready():
    try:
        return json.loads((dest/"BUNDLE.json").read_text())["sha256"] == meta["sha256"]
    except (OSError,ValueError,KeyError):
        return False
try:
    if not ready():
        if dest.exists():
            raise RuntimeError("existing admission bundle is incomplete or differs; retained for diagnosis")
        if not str(dest).startswith("/srv/opentallas-scratch") or "/claude/" not in str(dest):
            raise RuntimeError("admission bundle must be under an owned scratch lane")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".fetch-",dir=dest.parent) as temporary:
            target=Path(temporary)/"bundle";target.mkdir()
            command="tar -C "+shlex.quote(str(dest))+" -cf - ."
            source=subprocess.Popen(["ssh","-o","BatchMode=yes","-o","ControlPath=none",meta["source_host"],command],
                                    stdin=subprocess.DEVNULL,stdout=subprocess.PIPE)
            try:
                extracted=subprocess.run(["tar","-C",str(target),"-xf","-"],stdin=source.stdout)
            finally:
                source.stdout.close()
            if source.wait() or extracted.returncode:
                raise RuntimeError("admission tool transfer failed; physical runner not started")
            manifest=json.loads((target/"BUNDLE.json").read_text())
            if manifest.get("sha256") != meta["sha256"]:
                raise RuntimeError("admission tool version differs; physical runner not started")
            if not dest.exists():target.rename(dest)
        if not ready():raise RuntimeError("admission tool installation incomplete")
    print("ADMISSION_TOOLS READY "+meta["sha256"],flush=True)
    os.execv(sys.executable,[sys.executable,str(dest/"signoff_chain.py"),"--preflight",
                           str(dest/"die_plan/kit_preflight.py"),"--lec",str(dest/"die_plan/lec.py")]+sys.argv[2:])
except Exception as error:
    print("ADMISSION_TOOLS FAIL: "+str(error),flush=True)
    sys.exit(3)
'''


def stage_admission_tools(source_chain=None, source_tools=None, root=None):
    """Own immutable scratch bundle: never rsync tools into another repo checkout."""
    import hashlib
    import tempfile
    chain = Path(source_chain or Path(__file__).with_name("signoff_chain.py")).resolve()
    tools = Path(source_tools or Path(__file__).resolve().parents[1] / "die_plan").resolve()
    root = Path(root or Path(ARCHIVE_ROOT).parent / "admission_tools")
    files = [p for p in tools.rglob("*") if p.is_file() and
             not any(x in ("__pycache__", ".pytest_cache", ".git") for x in p.relative_to(tools).parts)]
    chain_bytes = chain.read_bytes()
    payload = {path.relative_to(tools): path.read_bytes() for path in sorted(files)}
    digest = hashlib.sha256(chain_bytes)
    for relative, content in payload.items():
        digest.update(str(relative).encode()+b"\0")
        digest.update(content)
    version = digest.hexdigest()
    dest = root / version[:20]
    if not dest.exists() and not DRY:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=root) as temporary:
            temp = Path(temporary) / "bundle"
            (temp / "die_plan").mkdir(parents=True)
            (temp / "signoff_chain.py").write_bytes(chain_bytes)
            for relative, content in payload.items():
                target = temp / "die_plan" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            (temp / "BUNDLE.json").write_text(json.dumps(dict(sha256=version, source=str(tools),
                note="current scheduler admission tools; frozen kit source/tools untouched"), indent=1)+"\n")
            # One scheduler tick submits serially; a second process may already
            # have installed the same immutable content while we copied it.
            if not dest.exists():
                temp.rename(dest)
    return dict(dir=str(dest), chain=str(dest / "signoff_chain.py"),
                preflight=str(dest / "die_plan/kit_preflight.py"), sha256=version)


def submit(st, j, attempt_note=""):
    n = j.get("attempts", 0) + 1
    unit = f"ap-{j['id']}-a{n}"
    logf = AP_DIR / "jobs" / j["id"] / f"a{n}.log"
    kit, runner, mem, thr = j["path"], j["runner"], j["mem_gb"], j["threads"]
    argv = [OT_RUN, "--mem", str(mem), "--threads", str(thr), "--dir", kit, "--stage", kit]
    if not runner.startswith(kit + "/"):
        argv += ["--stage", runner]
    if j["goal"] not in ("cts", "grt"):
        import base64
        bundle = stage_admission_tools()
        bundle["source_host"] = os.environ.get("AP_ADMISSION_HUB", "hub")
        encoded = base64.b64encode(json.dumps(bundle).encode()).decode()
        # --stage is spill-only. Fetch the immutable tool bundle on the
        # actual selected worker before executing any frozen kit runner.
        argv += ["--", "python3", "-c", ADMISSION_BOOTSTRAP, encoded,
                 runner, kit, j["goal"], str(mem), str(thr)]
        # chain v2 (AUTOPILOT-SIGNOFF-2): main lec.py + all_shown + mtime proof, FAILED notice + data delete.
        # Jobs launched by an earlier chain keep the earlier rules (no retroactive demotion or deletion).
        j.update(chain_required=True, admission_tools_sha256=bundle["sha256"], chain_version=CHAIN_VERSION)
    else:
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


def real_geom_fail(r):
    """the row's geom is a FAIL verdict read from lanes/GEOM-REVIEW.md by resolve_geom (LG.geom_verdicts: a REPLY of the
    row's tag that names its type / kit dir / row id), never a hand-entered queue FAIL"""
    return (not r["error"] and r["mode"] != "adopt" and r["geom"].upper() == "FAIL"
            and (r.get("geom_auto") or "").startswith("FAIL "))


def geom_fail_after_submit(st, j, r):
    """a GEOM verdict that is no longer PASS for a job already submitted / running / finished: never demoted or
    cancelled here (owner: the autopilot does not stop runs on its own); warn once per verdict in log.txt, add a
    geom_alerts.tsv row (rsynced to rtx-pro) and keep a GEOM-FAIL-AFTER-SUBMIT line in LOOP-GAPS while it runs"""
    if not real_geom_fail(r):
        # only a FAIL verdict parsed from lanes/GEOM-REVIEW.md that names this row's type / kit / row id counts; a
        # hand-written queue FAIL (2026-10-25 e0cca96daff3: queue line 389 'FAIL WITHDRAWN obsolete recipe ... existing
        # live job preserved') is a lane's withdrawal of the row, not a review verdict.  A stale alert is dropped.
        if j.get("geom_fail_alert") and not r["error"]:
            log(f"CLEAR GEOM-FAIL-AFTER-SUBMIT {j['id']} {r['die']}/{r['type']}: queue line {r['line']} carries no "
                f"GEOM-REVIEW FAIL verdict (was: {j['geom_fail_alert'][:160]})")
            j.pop("geom_fail_alert", None)
            j.pop("geom_fail_alert_t", None)
            save_state(st)
        return
    if not (j.get("geom") or "").upper() in GEOM_OK:
        return
    key = r["geom_auto"]
    if j.get("geom_fail_alert") == key:
        return
    j["geom_fail_alert"] = key
    j["geom_fail_alert_t"] = time.time()
    log(f"WARN GEOM-FAIL-AFTER-SUBMIT {j['id']} {r['die']}/{r['type']} status {j.get('status')} unit "
        f"{j.get('unit', '-')}: submitted on GEOM {j.get('geom')} ({j.get('geom_ref')}), now {r['geom']} -- NOT demoted "
        f"or cancelled by the autopilot; COORD/owner decide (cancel: systemctl --user stop {j.get('unit', '<unit>')}) "
        f"-- {key[:200]}")
    tsv_append("geom_alerts.tsv", j["id"], [r["die"], r["type"], r["src"], r["kit"], j.get("status"),
                                            j.get("unit", ""), f"{j.get('geom')} {j.get('geom_ref')}", key[:300],
                                            r["lane"]])
    save_state(st)


# ------------------------------------------------------------------------------------------------ closure order
# OWNER 2026-10-25 18:45 (lanes/_LANE_PREAMBLE.md "Closure order"):
#  rule 1: until a path's die gate (lanes/PATH-FREEZE.md: GRT0 + CLOCK-ROUTE + PATH-STA PASS, or a FROZEN line) passes,
#          its parts get trial builds only -- the autopilot never submits a sign-off run of a path part (WAIT-PATH-GATE;
#          a row with mode 'trial' runs, and its result is recorded in trial.tsv, never as a sign-off);
#  rule 3: a sign-off counts only when it names its source commit + the flow release tag it used (signed.tsv
#          src_commit / flow_tag, AUTOPILOT.json + PROVENANCE.json in the archive); otherwise SIGNED-UNVERSIONED;
#  rule 4: no kit run for a part a pending lanes/PLAN-DELTA.md delta touches (WAIT-PLAN-DELTA).
CLOSURE = {}                                           # per tick: parsed PATH-FREEZE / PLAN-DELTA + flow tags


def canonical_die(die):
    """Use the same canonical die for closure guards and legacy queue canaries."""
    return {"kv": "qwen_kvsys"}.get(die, die)


def parse_path_freeze(text):
    """-> ({PATH: {"pass": bool, "why": str, "items": {item: state}}}, {PATH: set(types)})
    lines 'PATH | GRT0 / CLOCK-ROUTE / PATH-STA | PASS|FAIL|RUNNING|NOT RUN ... | evidence | date' (latest line per
    item wins), 'FROZEN <PATH> plan@sha' (gate PASS until a later FAIL line of that path), and
    'PATH-PARTS <PATH> type[,type ...]' (path-part types beyond the PATH-* lane / GEOM tag rows).  Fail closed: a path
    with no lines is not PASS."""
    gates, parts = {}, {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        m = re.match(r"^FROZEN\s+([A-Za-z0-9_-]+)\s+\S*@[0-9a-f]{7,40}", line)
        if m:
            g = gates.setdefault(m.group(1).upper(), {"items": {}, "frozen": False})
            g["frozen"], g["frozen_line"] = True, line[:160]
            continue
        m = re.match(r"^PATH-PARTS\s+([A-Za-z0-9_-]+)\s+(.+)$", line)
        if m:
            parts.setdefault(m.group(1).upper(), set()).update(t for t in re.split(r"[\s,]+", m.group(2)) if t)
            continue
        f = [x.strip() for x in line.split("|")]
        if len(f) < 3 or not re.match(r"^[A-Z0-9_-]+$", f[0]):
            continue
        state = (f[2].split() or [""])[0].upper()
        items = [x.strip().upper() for x in re.split(r"\s*/\s*", f[1])]
        g = gates.setdefault(f[0].upper(), {"items": {}, "frozen": False})
        for it in items:
            if it in GATE_ITEMS:
                g["items"][it] = state
        if state == "FAIL" and any(it in GATE_ITEMS for it in items):
            g["frozen"] = False
    for name, g in gates.items():
        ok = g["frozen"] or all(g["items"].get(it) == "PASS" for it in GATE_ITEMS)
        g["pass"] = ok
        g["why"] = (g.get("frozen_line") if g["frozen"] else
                    " ".join(f"{it} {g['items'].get(it, 'NOT RECORDED')}" for it in GATE_ITEMS))
    return gates, parts


def parse_plan_delta(text):
    """-> {(die, type): delta id} of PENDING deltas: lines 'PENDING-DELTA <id> <die> type[,type ...]', closed by
    'CLOSED-DELTA <id>' / 'MERGED-DELTA <id>' / 'DROPPED-DELTA <id>' (later lines win)"""
    pend = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        m = re.match(r"^PENDING-DELTA\s+(\S+)\s+(\S+)\s+(\S+)", line)
        if m:
            pend[m.group(1)] = (canonical_die(m.group(2)), {t for t in m.group(3).split(",") if t})
            continue
        m = re.match(r"^(?:CLOSED|MERGED|DROPPED)-DELTA\s+(\S+)", line)
        if m:
            pend.pop(m.group(1), None)
    out = {}
    for did, (die, types) in pend.items():
        for t in types:
            out[(die, t)] = did
    return out


def load_closure():
    CLOSURE.clear()
    CLOSURE["gates"], CLOSURE["parts"] = parse_path_freeze(read_coord("lanes/PATH-FREEZE.md"))
    CLOSURE["delta"] = parse_plan_delta(read_coord("lanes/PLAN-DELTA.md"))


def _base_type(t):
    return (t or "").split("__")[0]


def path_of(r):
    """the path name of a queue row / job when it is a path part, else None"""
    path = DIE_PATH.get(canonical_die(r.get("die") or ""))
    if not path:
        return None
    lane = (r.get("lane") or "").upper()
    tag = (geom_tag(r.get("geom_ref") or "") or "").upper()
    listed = CLOSURE.get("parts", {}).get(path, set())
    if lane.startswith("PATH-") or tag.startswith("PATH-") or r.get("type") in listed or _base_type(r.get("type")) in listed:
        return path
    return None


def die_frozen(die):
    """the FROZEN line of the die's plan when lanes/PATH-FREEZE.md freezes it (no later FAIL gate line of that name)"""
    gates = CLOSURE.get("gates", {})
    die = canonical_die(die)
    for name, key in FROZEN_DIE.items():
        g = gates.get(name)
        if key == die and g and g.get("frozen"):
            return g.get("frozen_line") or name
    return ""


def path_gate_hold(r):
    """'' when the path part may route to sign-off, else why it is limited to trial builds.  A row whose DIE is FROZEN
    passes regardless of its path (rule 1 amendment: e.g. s81_head rows on path S81 once 'FROZEN S81-HEAD' is recorded)"""
    path = path_of(r)
    if not path or die_frozen(r.get("die") or ""):
        return ""
    g = CLOSURE.get("gates", {}).get(path)
    if g and g["pass"]:
        return ""
    return (f"path {path} die gate not PASS in lanes/PATH-FREEZE.md ({(g or {}).get('why', 'no gate line')[:160]}); "
            f"path parts get trial builds only (closure order rule 1): enqueue --mode trial")


def plan_delta_hold(r):
    die = canonical_die(r.get("die"))
    did = CLOSURE.get("delta", {}).get((die, r.get("type"))) or \
        CLOSURE.get("delta", {}).get((die, _base_type(r.get("type"))))
    return (f"pending plan delta {did} in lanes/PLAN-DELTA.md touches {r.get('die')}/{r.get('type')} "
            f"(closure order rule 4: no kit run until the delta is CLOSED/MERGED/DROPPED)") if did else ""


def closure_hold(r):
    """(status, why) that keeps a row from being submitted, or (None, '')"""
    if r.get("mode") in ("trial", "adopt", "withdraw"):
        return None, ""
    why = "" if r.get("goal") in ("cts", "grt") else path_gate_hold(r)   # scope-only diagnostics are trial builds
    if why:
        return "WAIT-PATH-GATE", why
    why = plan_delta_hold(r)
    if why:
        return "WAIT-PLAN-DELTA", why
    return None, ""


def flow_watch():
    try:
        return json.loads(read_repo("tools/flow_canary/canaries.json"))["watch"]
    except Exception:                                  # unreadable -> no provenance (fail closed)
        return None


def flow_exclude():
    """canaries.json 'watch_exclude' (tests, docs, logs, results ...): never part of the flow fingerprint"""
    try:
        return json.loads(read_repo("tools/flow_canary/canaries.json")).get("watch_exclude") or []
    except Exception:
        return []


def flow_plans():
    """canaries.json 'die_plans' {canary die: [own physical/die_plan trees]} (another die's plan files are not this
    die's flow, tools/flow_canary/flow_watch.py); unreadable -> {} (fail closed: every plan tree counts)"""
    try:
        return json.loads(read_repo("tools/flow_canary/canaries.json")).get("die_plans") or {}
    except Exception:
        return {}


CANARY_DIE = {"cp1": "s81", "kv": "qwen_kvsys"}     # queue die -> canaries.json die_plans key
PLAN_ROOT = "physical/die_plan/"


def _all_flow_tags():
    """newest-first [(tag, creator unix time)] of every flow release tag on origin, fetched once per tick"""
    if "all_tags" not in CLOSURE:
        sh(["git", "-C", str(REPO), "fetch", "-q", "origin", "+refs/tags/flow-*:refs/tags/flow-*"], timeout=120)
        rc, out, _ = sh(["git", "-C", str(REPO), "for-each-ref", "--sort=-creatordate",
                         "--format=%(refname:short) %(creatordate:unix)", "refs/tags/flow-*"], timeout=60)
        tags = []
        for line in (out.splitlines() if rc == 0 else []):
            parts = line.split()
            if len(parts) == 2 and FLOW_TAG_RE.match(parts[0]) and parts[1].isdigit():
                tags.append((parts[0], int(parts[1])))
        CLOSURE["all_tags"] = tags
    return CLOSURE["all_tags"]


def flow_tags(die=None):
    """newest-first flow release tags on origin covering `die` (ROOT-MERGE tags flow-YYYYMMDD-a/b for all dies,
    flow-YYYYMMDD-a/b-<qc|s81|head|kv|hbm> per die), at most FLOW_TAGS_CHECKED"""
    return [t for t, _ in _all_flow_tags() if tag_covers(t, die)][:FLOW_TAGS_CHECKED]


LEGACY_TAG = "SIGNED-LEGACY"   # GRANDFATHER (COORD ruling 2026-10-25 19:13): flow_tag value of a pre-first-tag sign-off


def first_flow_tag_ts(die=None):
    """unix time of the oldest flow release tag on origin covering `die` (None: no flow release for it yet)"""
    ts = [t for tag, t in _all_flow_tags() if tag_covers(tag, die)]
    return min(ts) if ts else None


def apply_legacy(j):
    """GRANDFATHER: a run STARTED before the first flow tag (or while none exists) that names its source commit (or
    its archive run dir) and has no flow tag counts as SIGNED-LEGACY; runs started after the first tag need a real
    flow tag.  Sets j['flow_tag'] = LEGACY_TAG and returns True when it applies."""
    if j.get("flow_tag") or not (j.get("src_commit") or j.get("archive")):
        return False
    first = first_flow_tag_ts(j.get("die"))
    started = float(j.get("started") or 0)
    if first is not None and not (0 < started < first):
        return False
    j.update(flow_tag=LEGACY_TAG, legacy=True)
    return True


def resolve_provenance(src, flow="", die=None):
    """-> {src_commit, flow_tag} or {..., error}: the full source commit of branch@sha (fetched on the hub repo when
    missing) and the flow release tag whose watched flow files (tools/flow_canary/canaries.json 'watch') are identical
    to the commit's -- the named --flow tag, else the newest matching one.  Only tags covering `die` count
    (per-die releases, 12.9e).  Never guessed: no match -> error."""
    branch, sha = src.rsplit("@", 1)
    rev = lambda: sh(["git", "-C", str(REPO), "rev-parse", "-q", "--verify", sha + "^{commit}"], timeout=60)
    rc, out, _ = rev()
    if rc or not out.strip():
        sh(["git", "-C", str(REPO), "fetch", "-q", "origin", branch], timeout=300)
        rc, out, _ = rev()
    if rc or not out.strip():
        return {"src_commit": "", "flow_tag": "", "error": f"src commit {sha} not found on origin ({branch}): push it"}
    full = out.strip().split()[0]
    watch = flow_watch()
    if not watch:
        return {"src_commit": full, "flow_tag": "", "error": "flow watch list tools/flow_canary/canaries.json unreadable"}
    exclude = flow_exclude()
    own = flow_plans().get(CANARY_DIE.get(die, die)) if die else None
    tags = flow_tags(die)
    if flow and flow not in tags:
        if flow in flow_tags():
            return {"src_commit": full, "flow_tag": "", "error": f"flow tag {flow} does not cover die {die}"}
        return {"src_commit": full, "flow_tag": "", "error": f"flow tag {flow} not found on origin"}
    for t in ([flow] if flow else tags):
        rc, out, _ = sh(["git", "-C", str(REPO), "diff", "--name-only", t, full], timeout=120)
        if rc:
            continue
        changed = [p for p in out.splitlines() if any(fnmatch.fnmatch(p, w) for w in watch)
                   and not any(fnmatch.fnmatch(p, x) for x in exclude)
                   and not (own is not None and p.startswith(PLAN_ROOT) and p[len(PLAN_ROOT):].split("/", 1)[0] not in own)]
        if not changed:
            return {"src_commit": full, "flow_tag": t}
        if flow:
            return {"src_commit": full, "flow_tag": "",
                    "error": f"src flow differs from {flow} in {len(changed)} watched files (e.g. {changed[0]})"}
    return {"src_commit": full, "flow_tag": "",
            "error": "no flow release tag carries this commit's flow" + ("" if tags else " (no flow-* tag on origin yet)")}


PROBE_PROVENANCE = r'''
import json, os, sys
a = json.loads(sys.argv[1]); out = {}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
try:
    p = os.path.join(a["dest"], "PROVENANCE.json"); t = p + ".tmp"
    with open(t, "w") as f: json.dump(a["prov"], f, indent=1)
    os.replace(t, p); out["ok"] = True
except Exception as e:
    out["error"] = str(e)
done()
'''


def write_provenance(host, dest, j):
    prov = {k: j.get(k) for k in ("id", "die", "type", "src", "src_commit", "flow_tag", "lane")}
    prov.update(schema="opentallas.provenance.v1", verdict="SIGNED" if j.get("flow_tag") and j.get("src_commit")
                else "SIGNED-UNVERSIONED", why=j.get("prov_error", ""), written=now_s())
    return rpy(host, PROBE_PROVENANCE, {"dest": dest, "prov": prov}, timeout=120)


def record_signed(st, j, host, so):
    """signed.tsv only with src_commit + flow_tag (rule 3); else unversioned.tsv + SIGNED-UNVERSIONED"""
    if j.get("src_commit") and j.get("flow_tag"):
        tsv_append("signed.tsv", j["id"], [j["die"], j["type"], j["src"], host, j["kit"], j["archive"], j["mirror"],
                                           so.get("tt_wns"), so.get("ff_wns"), j.get("lane", ""), j["src_commit"],
                                           j["flow_tag"]])
        set_status(st, j, "ARCHIVED", f"{j['archive']} src {j['src_commit'][:12]} flow {j['flow_tag']}")
        return True
    tsv_append("unversioned.tsv", j["id"], [j["die"], j["type"], j["src"], host, j["kit"], j["archive"],
                                            so.get("tt_wns"), so.get("ff_wns"), j.get("prov_error", ""), j.get("lane", "")])
    set_status(st, j, "SIGNED-UNVERSIONED", f"{j['archive']}: not counted as signed off: {j.get('prov_error', '')}"[:300])
    return False


def retry_unversioned(st):
    """an archived SIGNED-UNVERSIONED run is promoted once a flow release tag carries exactly its flow"""
    for j in st["jobs"].values():
        if j.get("status") != "SIGNED-UNVERSIONED" or not j.get("archive"):
            continue
        prov = resolve_provenance(j["src"], j.get("flow", ""), j.get("die"))
        if prov.get("error"):
            j["prov_error"] = prov["error"]
            if not apply_legacy(j):
                continue
            prov = {"src_commit": prov.get("src_commit") or j.get("src_commit", ""), "flow_tag": LEGACY_TAG}
        j.update(src_commit=prov["src_commit"], flow_tag=prov["flow_tag"], prov_error="")
        host, dest = j["archive"].split(":", 1)
        if DRY:
            log(f"would PROMOTE {j['id']} {j['die']}/{j['type']}: flow {j['flow_tag']}")
            continue
        w = write_provenance(host, dest, j)
        if w.get("error"):
            log(f"PROVENANCE write failed {j['id']}: {w['error'][:200]}; retry next tick")
            continue
        record_signed(st, j, host, j.get("signoff") or {})
        log(f"PROMOTE {j['id']} {j['die']}/{j['type']}: SIGNED-UNVERSIONED -> signed.tsv (src {j['src_commit'][:12]}, "
            f"flow {j['flow_tag']})")


def canary_wave_gate(row):
    import canary_gate
    root = os.environ.get("AP_CANARY_ROOT", "/srv/opentallas-scratch2/claude/flow-canary/runs")
    repo = HOME / "OpenTallas"
    result = canary_gate.assess(row, root, repo, sh)
    # The wave gate precedes resolve_provenance (which normally fetches the
    # queued branch). A new published kit source may therefore be absent here.
    # Recover the exact object, then run the SAME gate; never turn an error or
    # measured regression into an advisory result.
    if not result[0] and result[1].startswith("source integrity error:"):
        src = row.get("src", "")
        if "@" in src:
            branch, sha = src.rsplit("@", 1)
            if branch and not branch.startswith("-") and re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
                cmd = ["git", "-C", str(repo), "rev-parse", "-q", "--verify", sha + "^{commit}"]
                rc, obj, _ = sh(cmd, timeout=60)
                if rc or not obj.strip():
                    fetched, _, _ = sh(["git", "-C", str(repo), "fetch", "-q", "origin", branch], timeout=300)
                    rc, obj, _ = sh(cmd, timeout=60)
                    if not fetched and not rc and obj.strip():
                        return canary_gate.assess(row, root, repo, sh)
    return result


def withdraw_unqueued(st, rows):
    """A WAIT-GEOM / WAIT-CANARY job whose queue row is gone (line commented out '# WITHDRAWN ...' / '# SUPERSEDED',
    or deleted) can never be admitted: mark it WITHDRAWN so it stops counting as a held row (FLOW-CANARY 10-25: 3 of
    the 9 WAIT-CANARY rows were commented-out queue lines).  Never on an empty parse (unreadable queue); a row put
    back into the queue is re-admitted normally (admit_new re-evaluates WITHDRAWN)."""
    if not rows:
        return
    for jid, j in st["jobs"].items():
        if j.get("status") in ("WAIT-GEOM", "WAIT-CANARY", "WAIT-PATH-GATE", "WAIT-PLAN-DELTA") and jid not in rows:
            log(f"WITHDRAWN {jid} {j.get('die')}/{j.get('type')}: queue row gone (commented out or removed); was "
                f"{j.get('status')}")
            set_status(st, j, "WITHDRAWN", f"queue row gone (was {j.get('status')} at line {j.get('queue_line') or j.get('line')})")


# OWNER 10-27 closure speed-up (4): admission order by the 10-29 gate -- KV, QC first, then HEAD, S81, HBM
DIE_PRIORITY = ("qwen_kvsys", "qwen_compute", "s81_head", "s81", "hbm")


def die_priority(die):
    d = canonical_die(die or "")
    return DIE_PRIORITY.index(d) if d in DIE_PRIORITY else len(DIE_PRIORITY)


def admit_new(st, rows):
    submitted = 0
    withdraw_unqueued(st, rows)
    for rid, r in sorted(rows.items(), key=lambda kv: (die_priority(kv[1].get("die")), kv[1]["line"])):
        j = st["jobs"].get(rid)
        if not r["error"] and r.get("mode") == "withdraw":
            # Append-only withdrawal is queue control, never a cancellation or a
            # replacement of an existing physical verdict.
            j = st["jobs"].setdefault(rid, dict(r))
            why = r["geom_ref"]
            if j.get("status") in WAITS:
                if j.get("status") != "WITHDRAWN" or j.get("withdraw_requested") != why:
                    j.update({k: v for k, v in r.items() if k != "error"})
                    j.update(queue_line=r["line"], withdraw_requested=why)
                    log(f"WITHDRAWN {rid}: {why}; no job launched or evidence removed")
                    set_status(st, j, "WITHDRAWN", why)
            elif j.get("withdraw_requested") != why:
                j["withdraw_requested"] = why
                log(f"WITHDRAW-REQUESTED {rid}: {why}; {j.get('status')} state and job preserved")
            continue
        if j and j.get("status") not in WAITS:
            geom_fail_after_submit(st, j, r)
            continue                                   # already handled; the queue never restarts a job
        if j and j.get("status") == "REJECTED" and j.get("queue_line") == r["line"]:
            continue                                   # re-judged only when the row is re-appended
        if r["error"]:
            if not j:
                j = st["jobs"][rid] = {"id": rid, "kit": r["kit"], "queue_line": r["line"]}
                log(f"REJECT queue line {r['line']} ({r['kit']}): {r['error']}")
                set_status(st, j, "REJECTED", r["error"])
            continue
        if r["mode"] != "adopt" and r["geom"].upper() == "AUTO":
            # AUTO-GEOM (owner 2026-10-25): a registered template replica gets the rule check; the verdict is
            # applied by AG.prepare on the next tick (PASS -> submit, FAIL -> visual REQ on its AUTO-GEOM tag)
            note = AG.step(sys.modules[__name__], st, r, GEOM_TEXT)
            j = st["jobs"].setdefault(rid, dict(r))
            if j.get("status") != "WAIT-GEOM" or j.get("auto_geom_note") != note:
                j["auto_geom_note"] = note
                set_status(st, j, "WAIT-GEOM", note)
            continue
        if r["mode"] != "adopt" and (r["geom"].upper() not in GEOM_OK or not r["geom_ref"]):
            if not j:
                j = st["jobs"][rid] = dict(r)
                log(f"WAIT {rid} {r['die']}/{r['type']}: GEOM '{r['geom']}' (needs PASS + geom_ref)")
                set_status(st, j, "WAIT-GEOM", r["geom"])
            was = j.get("geom") or ""
            if was.upper() in GEOM_OK or j.get("status") != "WAIT-GEOM":
                why = r.get("geom_auto") or f"queue line {r['line']}: geom '{r['geom']}' geom_ref '{r['geom_ref']}'"
                log(f"DEMOTE {rid} {r['die']}/{r['type']}: GEOM {was or '?'} -> {r['geom']} ({j.get('status')} -> "
                    f"WAIT-GEOM; not submitted) -- {why}")
                j.update(geom=r["geom"], geom_ref=r["geom_ref"], queue_line=r["line"])
                j["geom_auto"] = r.get("geom_auto", "")
                set_status(st, j, "WAIT-GEOM", f"demoted: {why}")
            elif r.get("geom_auto") and j.get("geom_auto") != r["geom_auto"]:
                j["geom_auto"] = r["geom_auto"]
                j.update(geom=r["geom"], geom_ref=r["geom_ref"])
                log(f"WAIT {rid} {r['die']}/{r['type']}: GEOM verdict {r['geom_auto']} -- not submitted")
                set_status(st, j, "WAIT-GEOM", r["geom_auto"])
            continue
        if r.get("geom_auto") and (not j or j.get("geom_auto") != r["geom_auto"]):
            log(f"GEOM {rid} {r['die']}/{r['type']}: verdict from lanes/GEOM-REVIEW.md -> {r['geom_auto']}")
        hold, hold_why = closure_hold(r)
        if hold:
            j = st["jobs"].setdefault(rid, dict(r))
            j.update(r)
            if j.get("status") != hold or j.get("hold_why") != hold_why:
                log(f"HOLD {rid} {r['die']}/{r['type']}: {hold_why}")
                j["hold_why"] = hold_why
                set_status(st, j, hold, hold_why)
            continue
        allowed, canary_why = canary_wave_gate(r)
        if not allowed:
            j = st["jobs"].setdefault(rid, dict(r))
            j.update(r)
            set_status(st, j, "WAIT-CANARY", canary_why)
            log(f"HOLD {rid} {r['die']}/{r['type']}: {canary_why}")
            continue
        if r.get("canary_fix"):
            log(f"CORRECTIVE {rid} {r['die']}/{r['type']}: {canary_why}")
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
        if not why and p.get("signoff_missing") and r.get("goal") not in ("cts", "grt"):
            why = (f"kit signoff.py lacks {', '.join(p['signoff_missing'])} (sign-off would crash after the route); "
                   "stage the whole bundle: tools/die_plan/signoff.py copy_signoff_bundle(kit)")
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
        j.pop("hold_why", None)
        trial_why = ("mode trial" if r["mode"] == "trial" else f"goal {r.get('goal')} (diagnostic)" if r.get("goal") in ("cts", "grt")
                     else path_gate_hold(r))
        if trial_why:
            j["trial"] = trial_why                        # rule 1: never recorded as a sign-off
        if j.get("goal") in ("", "auto", None):
            j["goal"] = default_goal(p["runner"])
        g = runner_goal(j["goal"], p)
        if g != j["goal"]:
            log(f"GOAL {rid} {r['die']}/{r['type']}: {j['goal']} -> {g} (runner signs off on "
                f"{'/'.join(p.get('signoff_goals') or [])}{'; no ADDITIONAL_GDS for macros' if p.get('gds_gap') else ''})")
            j["goal"] = g
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
        if not client.get("cancelled"):
            sig = signals_cancel(j)
            if sig:
                client["cancelled"] = sig
        if client.get("cancelled"):
            j.update(cls="CANCELLED", kind="cancelled", reasons=client["cancelled"][:600], finished=time.time())
            log(f"CLASSIFY {j['id']} {j['die']}/{j['type']} -> CANCELLED (explicit ot-run --cancel; not resubmitted): "
                f"{client['cancelled'][:240]}")
            set_status(st, j, "CANCELLED", f"cancelled: {client['cancelled'][:200]}")
            continue
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
    if j.get("chain_required") and cls in ("SIGNED", "WAIT-PARENT"):
        chain = c.get("chain") or {}
        if chain.get("verdict") == "LEC_OOM":
            cls, kind, reasons = "CRASH", "proof-oom", str(chain.get("reason"))
        elif (chain.get("started", 0) < j.get("started", 0) - 120
                or chain.get("verdict") != "PASS" or chain.get("lec_verdict") != "EQUIVALENT"
                or chain.get("lec_exit") != 0 or (j.get("chain_version", 1) >= 2 and chain.get("lec_all_shown") is not True)):
            cls, kind, reasons = "STRUCTURAL", "routed-lec", "autopilot chain incomplete: " + str(chain.get("reason") or "missing current routed LEC")
    if client.get("orphan") and cls == "CRASH" and kind not in ("tool-segfault",):
        kind, reasons = "infra-orphan", client["msg"]
    j.update(cls=cls, kind=kind, reasons=reasons[:600], probe=c.get("probe_host"),
             signoff=c.get("signoff"), finished=time.time())
    if c.get("chain"):
        j["chain"] = {k: c["chain"].get(k) for k in ("verdict", "reason", "gates", "lec", "lec_verdict",
                                                   "lec_all_shown", "lec_tool", "signoff", "netlist")}
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
    if cls in ("CTS-DONE", "GRT-DONE"):
        j["delete_pending"] = False
        tsv_append("trial.tsv", j["id"], [j["die"], j["type"], j["src"], ssh_host(j.get("probe") or j["host"]), j["kit"],
                                          cls, "", "", j.get("reasons", "")[:300], j.get("lane", "")])
        log(f"{cls} {j['id']} {j['die']}/{j['type']}: {j.get('reasons', '')[:200]}; checkpoint kept, trial.tsv")
        return
    if cls == "SIGNED":
        trial = j.get("trial") or path_gate_hold(j)
        if trial:
            so = j.get("signoff") or {}
            j["delete_pending"] = False
            tsv_append("trial.tsv", j["id"], [j["die"], j["type"], j["src"], ssh_host(j.get("probe") or j["host"]),
                                              j["kit"], "SIGNED", so.get("tt_wns"), so.get("ff_wns"), trial, j.get("lane", "")])
            set_status(st, j, "TRIAL-SIGNED", f"trial build, not a sign-off (closure order rule 1): {trial}"[:300])
            log(f"TRIAL {j['id']} {j['die']}/{j['type']}: local SIGNED kept as a trial result (trial.tsv), not archived "
                f"as a sign-off -- {trial[:200]}")
            return
        archive(st, j)
    elif cls == "WAIT-PARENT":
        j["delete_pending"] = False
        tsv_append("provisional.tsv", j["id"], [j["die"], j["type"], j["src"],
                   ssh_host(j.get("probe") or j["host"]), j["kit"],
                   (j.get("signoff") or {}).get("local_verdict"), j.get("reasons", ""), j.get("lane", "")])
        log(f"KEEP {j['id']} local physical PASS needs actual parent receipt; no release archive or failure cleanup")
    elif cls in ("NEAR-MISS", "STRUCTURAL", "CRASH"):
        if j.get("kind") == "proof-oom":
            record_failure(st, j)  # proof admission failure; no geometry reroute
        elif (j.get("signoff") or {}).get("odb"):
            start_review(st, j)
        else:
            record_failure(st, j)


def archive(st, j):
    host = ssh_host(j.get("probe") or j["host"])
    so = j["signoff"]
    sha = j["src"].split("@")[1][:10]
    dest = f"{ARCHIVE_ROOT}/{j['die']}/{j['type']}__{sha}"
    prov = resolve_provenance(j["src"], j.get("flow", ""), j.get("die"))
    j.update(src_commit=prov.get("src_commit", ""), flow_tag=prov.get("flow_tag", ""), prov_error=prov.get("error", ""))
    rec = {k: j.get(k) for k in ("id", "die", "type", "kit", "src", "geom", "geom_ref", "lane", "goal", "mem_gb",
                                 "src_commit", "flow_tag", "prov_error")}
    rec.update(signoff=so, archived=now_s(), host=host)
    view = {}
    if j.get("chain_version", 1) >= 2:
        vr = rpy(host, PROBE_VIEW_READ, {"kit": j["path"], "base": so["base"],
                                         "signoff_dir": os.path.dirname(so["path"])}, timeout=300)
        if vr.get("error"):
            log(f"VIEW read failed {j['id']}: {vr['error'][:200]}; retry next tick")
            set_status(st, j, "SIGNED", "archive pending (view read)")
            return
        view, gates, problems = view_payload(vr, j, so)
        rec["gates"] = gates
        j["view_problems"] = problems
    if DRY:
        log(f"would archive {j['id']} {host}:{j['path']} -> {dest} + mirror"
            + (f" + view/{view.get('module')} ({'complete' if not j.get('view_problems') else j['view_problems']})"
               if view else ""))
        return
    r = rpy(host, PROBE_ARCHIVE, {"kit": j["path"], "dest": dest, "base": so["base"],
                                  "signoff_dir": os.path.dirname(so["path"]), "record": rec, "view": view},
            timeout=3600)
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
    apply_legacy(j)
    w = write_provenance(host, dest, j)
    if w.get("error"):
        log(f"PROVENANCE write failed {j['id']}: {w['error'][:200]} (AUTOPILOT.json carries the same fields)")
    versioned = record_signed(st, j, host, so)
    if versioned and j.get("chain_version", 1) >= 2:
        coord_append("lanes/SIGN-RATE.tsv",
                     f"{now_s()}\tAUTOPILOT +1 {j['die']}/{j['type']} signed off (signoff + routed LEC EQUIVALENT "
                     f"all_shown) archive {j['archive']} view {r.get('view') or 'none'}"
                     f"{' INCOMPLETE ' + '; '.join(j.get('view_problems') or []) if j.get('view_problems') else ''}")
    log(f"ARCHIVED {j['id']} {j['die']}/{j['type']} -> {j['archive']} ({r.get('files')} files, MD5SUMS) mirror {mirror}"
        + (f" src {j['src_commit'][:12]} flow {j['flow_tag']}" if versioned else
           f" -- SIGNED-UNVERSIONED, not counted as signed off: {j['prov_error'][:200]}"))


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
    if j.get("chain_version", 1) >= 2 and not j.get("adopted"):
        # AUTOPILOT-SIGNOFF-2 (owner speed-up 10-27): stop the kit, tell the owning lane + COORD, delete the failed
        # run data at once (logs, reports, review bundle and receipts kept), never retry it blindly
        failed_notice(j, cls, host)
        if j.get("kind") == "proof-oom":
            j["delete_pending"] = False              # completed route kept for the measured --proof-only re-admission
        else:
            d = rpy(host, PROBE_DELETE, {"kit": j["path"], "dry": DRY}, timeout=1800)
            if d.get("error") or d.get("errors"):
                log(f"DELETE deferred {j['id']} on {host}: {d.get('error') or d.get('errors')}")
            else:
                j.update(delete_pending=False, data_deleted=not DRY)
                log(f"DELETED {j['id']} failed run data on {host} (logs kept): "
                    f"{', '.join(d.get('deleted') or ['nothing left'])}")
        set_status(st, j, "DONE-" + cls, j.get("reasons", "")[:200])
        return
    # Keep the physical checkpoint until the owning lane has diagnosed the failure.
    # A signoff/log summary cannot replace the ODB/netlist for structural path analysis.
    j["delete_pending"] = False
    log(f"KEEP {j['id']} failed physical checkpoints for owner diagnosis; no automatic bulk deletion")
    set_status(st, j, "DONE-" + cls, j.get("reasons", "")[:200])


def coord_append(rel, line):
    """append one line to a coord/state append-only file in the hub checkout; hub_git_sync commits it next tick"""
    if DRY:
        log(f"would append {rel}: {line[:300]}")
        return
    if COORD_FILES:
        return                                       # tests / manual runs never write the real coord tree
    p = COORD / rel
    try:
        with open(p, "a") as f:
            f.write(line.rstrip("\n") + "\n")
    except OSError as e:
        log(f"coord append {rel} failed: {e}")


def failed_notice(j, cls, host):
    lane = re.sub(r"[^A-Za-z0-9_.-]", "", j.get("lane") or "") or "AUTOPILOT"
    rev = j.get("review_dir") or "no review bundle"
    msg = (f"{now_s()} AUTOPILOT -> {lane}: FAILED {j['id']} {j['die']}/{j['type']} ({cls}/{j.get('kind', '')}): "
           f"{(j.get('reasons') or '')[:300]} | kit {host}:{j['path']} src {j['src']} | review {rev} | "
           f"run data deleted (logs kept); kit stopped, NOT retried -- fix structurally and enqueue a fresh kit")
    if (COORD / "lanes" / f"{lane}.md").exists() or COORD_FILES:
        coord_append(f"lanes/{lane}.md", msg)
    coord_append("lanes/COORD-REVIEW-QUEUE.md", f"FAILED [AUTOPILOT {j['id']}] " + msg)


def failure_resolutions():
    """Owner releases bulk data only after diagnosis/evidence consumption: id TAB DELETE TAB evidence."""
    resolved = {}
    for line in read_coord("autopilot/failure-resolved.tsv").splitlines():
        if line.lstrip().startswith("#"):
            continue
        f = line.split("\t", 2)
        if len(f) == 3 and f[1].strip() == "DELETE" and f[2].strip():
            resolved[f[0].strip()] = f[2].strip()
    return resolved


def retry_pending(st):
    released = failure_resolutions()
    for j in list(st["jobs"].values()):
        if j.get("status") == "SIGNED" and not DRY:
            after_class(st, j)                         # trial check (rule 1) before an archive retry
        elif j.get("status") == "DONE-CRASH" and j.get("kind") == "proof-oom":
            if hub_procs(j["path"]):
                continue
            c = probe_job(j)
            chain = (c or {}).get("chain") or {}
            if chain.get("verdict") == "PASS" and chain.get("started", 0) > j.get("finished", 0):
                finish(st, j, c, {"proof_only_resume": True})
        elif j.get("status") == "WAIT-PARENT":
            if hub_procs(j["path"]):
                continue
            c = probe_job(j)
            so = (c or {}).get("signoff") or {}
            if so and so.get("verdict") != "LOCAL_PASS_NEEDS_PARENT":
                finish(st, j, c, {"parent_receipt_recheck": True})
        elif str(j.get("status", "")).startswith("DONE-") and not j.get("data_deleted"):
            if j["id"] not in released or hub_procs(j["path"]):
                continue
            host = ssh_host(j.get("probe") or j["host"])
            d = rpy(host, PROBE_DELETE, {"kit": j["path"], "dry": DRY}, timeout=1800)
            if not (d.get("error") or d.get("errors")):
                j.update(delete_pending=False, data_deleted=not DRY, diagnostic_evidence=released[j["id"]])
                log(f"DELETED {j['id']} diagnosed failure bulk data on {host}: "
                    f"{released[j['id']]}: {', '.join(d.get('deleted') or ['nothing left'])}")
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
    global GEOM_TEXT
    GEOM_TEXT = geom_text
    # Resolve explicit visual verdicts before promoting pending requests to measured checks.
    # Resolve again after prepare to apply a later reviewer FAIL on an AUTO-GEOM result.
    resolve_geom(rows, geom_text)
    AG.prepare(sys.modules[__name__], st, rows)
    resolve_geom(rows, geom_text)
    load_closure()
    poll_running(st)
    poll_reviews(st)
    retry_pending(st)
    retry_unversioned(st)
    admit_new(st, rows)
    save_state(st)
    if os.environ.get("AP_KIT_WAVE", "1") != "0":      # KIT-WAVE-1 (owner 10-30 (A)); inert without autopilot/kit_wave.json
        try:
            KW.step(sys.modules[__name__])
        except Exception as e:                         # the wave must never stop the chain
            log(f"KIT-WAVE failed: {type(e).__name__}: {e}")
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
    gaps = LG.gaps_geom(geom_text, now, submitted_tags, LG.parse_resolved(read_coord("autopilot/resolved.tsv")))
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
    gaps += LG.gaps_geom_ambiguous(geom_text, geom_groups(rows), now)
    gaps += AG.gaps(st, now, geom_text)
    cleared = LG.geom_fail_cleared(read_coord("autopilot/resolved.tsv"), read_coord("lanes/COORD-REVIEW-QUEUE.md"))
    for j in jobs:                                     # oldest-first render; keeps the line while the run is live
        if j["id"] in cleared and (cleared[j["id"]] is None or cleared[j["id"]] >= (j.get("geom_fail_alert_t") or 0)
                                   - 60):
            continue                                   # COORD ruled KEEP / CANCEL (or a resolved.tsv row) on this alert
        if j.get("geom_fail_alert") and j.get("status") == "RUNNING":
            gaps.append((j.get("geom_fail_alert_t") or now,
                         f"GEOM-FAIL-AFTER-SUBMIT {j['id']} {j.get('die')}/{j.get('type')} unit {j.get('unit', '-')}: "
                         f"submitted on {j.get('geom')}, later verdict {j['geom_fail_alert'][:160]} -- COORD: cancel or "
                         f"keep (autopilot never cancels)"))
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
        try:
            KW.overlay_owners(orows, KW.load_state(AP_DIR))  # wave items: owner KIT-WAVE-1, live unit, class + evidence
        except Exception as e:
            log(f"KIT-WAVE overlay failed: {type(e).__name__}: {e}")
        write_file("OWNERS.tsv", OWN.to_tsv(orows, now))
    except Exception as e:
        log(f"OWNERS failed: {type(e).__name__}: {e}")
        head = [f"# OWNERSHIP unavailable this tick: {type(e).__name__}: {str(e)[:200]}"]
    text = hub_sync_banner(now) + LG.render(gaps, now, head)
    if DRY:
        print(text, end="")
        return
    tmp = AP_DIR / f".LOOP-GAPS.txt.{os.getpid()}"
    tmp.write_text(text)
    os.replace(tmp, AP_DIR / "LOOP-GAPS.txt")


HUB_SYNC_STALE_S = 45 * 60      # hub_git_sync.sh runs before every tick (10 min); 45 min without a success is a failure


def hub_sync_banner(now):
    """first line of LOOP-GAPS.txt while the hub checkout sync fails (10-25: the hub sat at 08:29 for 86 min, silently):
    autopilot/HUB-SYNC-FAILED (written by hub_git_sync.sh) or a HUB-SYNC-OK older than HUB_SYNC_STALE_S"""
    try:
        f = (AP_DIR / "HUB-SYNC-FAILED").read_text().splitlines()
    except OSError:
        f = None
    if f is not None:
        since = f[0][6:].strip() if f and f[0].startswith("since ") else "?"
        why = " ".join(l.strip() for l in f[1:] if l.strip())
        return f"HUB-SYNC-FAILED since {since}: {why or 'see hub_git_sync.sh output'}\n"
    ok = AP_DIR / "HUB-SYNC-OK"
    try:
        age = now - ok.stat().st_mtime
        last = ok.read_text().split("\n", 1)[0].strip()
    except OSError:
        return ""                                      # never synced by hub_git_sync.sh (tests, manual runs)
    if age > HUB_SYNC_STALE_S:
        return (f"HUB-SYNC-FAILED since {last.rsplit(' ', 1)[0] if ' ' in last else last}: "
                f"no successful hub checkout sync for {age / 60:.0f} min (hub_git_sync.sh not running?)\n")
    return ""


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


def read_repo_many(rels):
    """{rel: text} of many origin/main files in one git cat-file --batch ('' / absent when missing)"""
    rels = sorted(set(rels))
    if REPO_FILES or not rels:
        return {r: read_repo(r) for r in rels}
    try:
        r = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"], capture_output=True, timeout=300,
                           input="".join(f"origin/main:{x}\n" for x in rels).encode())
    except subprocess.TimeoutExpired:
        return {}
    out, buf, i = {}, r.stdout, 0
    for rel in rels:
        nl = buf.find(b"\n", i)
        if nl < 0:
            break
        head = buf[i:nl].split()
        i = nl + 1
        if len(head) == 3 and head[1] == b"blob":
            n = int(head[2])
            out[rel] = buf[i:i + n].decode(errors="replace")
            i += n + 1
        elif len(head) == 3:                             # tree / other object: skip its body
            i += int(head[2]) + 1
    return out


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
    core_pins, bound_rtl = {}, {}
    for die, pdir, pname in OWN.DIES:
        plans[die] = _json(read_repo(f"physical/die_plan/{pdir}/die_plan.json"))
        pf = {h.get("pins_file") for t in ((plans[die] or {}).get("partition_types") or {}).values()
              if isinstance(t, dict) for h in t.get("hard_cores") or [] if h.get("pins_file")}
        texts = read_repo_many(f"physical/die_plan/{pdir}/{f}" for f in pf)
        core_pins[die] = {f: texts.get(f"physical/die_plan/{pdir}/{f}") for f in pf}
        cand = OWN.bound_rtl_paths(pdir, plans[die])
        texts = read_repo_many(c for cs in cand.values() for c in cs)
        bound_rtl[die] = {k: next((texts[c] for c in cs if texts.get(c)), None) for k, cs in cand.items()}
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
                geom_text=geom_text, lane_texts=lane_texts, live=hub_otrun_clients(), core_pins=core_pins, bound_rtl=bound_rtl,
                canonical=_json(read_repo(OWN.CANONICAL_SPLIT)),
                retired=OWN.parse_retired(read_coord("autopilot/OWNERS-RETIRED.tsv")))


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
