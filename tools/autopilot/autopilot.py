#!/usr/bin/env python3
"""autopilot.py -- deterministic (non-LLM) kit chain on the ot-run hub (epyc1), lane AUTOPILOT 2026-10-25.

Why: closure moved only when an agent handed each step on (kit -> route -> sign-off -> archive); usage limits and
Claude<->Codex handovers stalled that chain for hours (KIT-CENSUS: 1,709 run-hours, 21 sign-offs).  This service keeps
the chain moving with no agent involved.  It is built only from existing tools: the kit's own run_kit*.sh (which ends in
tools/die_plan/signoff.py), ot-run (memory-only admission), signoff.json, tools/ref_tile/layout_dump.tcl+layout_png.py.

OWNER RULE (2026-10-25): the autopilot NEVER alters a design.  It may only
  (a) submit queued kits that carry a GEOM PASS (ot-run, honest --mem from the queue row, <= 517k cells),
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
  mem_gb  honest ot-run --mem (peak of a comparable run + margin) ; cells = expected std cells (<= 517000)
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
from functools import lru_cache
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
sys.path.insert(1, str(Path(__file__).resolve().parents[1] / "die_plan"))
import signoff_profile as SP  # noqa: E402  (OWNER 11-13 R-MINIMAL; OT_SIGNOFF_PROFILE=legacy keeps the old gates)
import wave_balance as WB  # noqa: E402
import auto_resign as AR  # noqa: E402
import wave_jobs as WJ  # noqa: E402
import under_use as UU  # noqa: E402  (FABLE-FLOW-0445 #2: one UNDER-USE log line per tick)

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
NEAR_WNS_PS = -30.0
NEAR_DRC_MAX = 50
RENDER_MEM_GB = 8
ORPHAN_IDLE_S = 3 * 3600
CHAIN_VERSION = 2
MAX_SUBMIT_PER_TICK = int(os.environ.get("AP_MAX_SUBMIT", "100000"))   # LAUNCH-ALL-1116 (OWNER 11-13: no per-tick caps); was 12
MAX_NOTRUN = 3                                          # 'NOT RUN' (never admitted) resubmits
# KW-FIX-46 11-12 (COORD, hbm q_mcb_ne 58ab1566e512): a container memory-cgroup OOM is the kit's --mem request, not the
# host: q_mcb_ne route peaked > 75 GB, killed at --mem 48 and again at 72 (one x1.5 step), then filed as a final CRASH.
# Two x1.5 steps (48 -> 72 -> 108) cover a 2x under-estimate; a third OOM is a real memory problem.
MAX_OOM_RESUBMITS = 2
# DIE-S81-70 11-06: any numbered scratch root (owner 11-05: every disk is scratch; kw21 wave lives on epyc5 scratch3).
KIT_RE = re.compile(r"^([A-Za-z0-9_.-]+):(/srv/opentallas-scratch[0-9]*/claude/[A-Za-z0-9_./+=-]+)$")
SRC_RE = re.compile(r"^[A-Za-z0-9_./-]+@[0-9a-f]{7,40}$")
GEOM_OK = ("PASS", "PASS-COND")
QCOLS = ["die", "type", "kit", "src", "geom", "geom_ref", "mem_gb", "cells", "lane", "goal", "runner", "threads", "mode", "canary_fix",
         "flow"]
# PER-DIE FLOW RELEASES (METHODOLOGY 12.9e, OWNER 2026-10-26): flow-YYYYMMDD-a|b covers every die;
# flow-YYYYMMDD-a|b-<die tag> covers only that die (route holds / provenance lift per die; a die whose canary is
# pending keeps its previous tag).
FLOW_TAG_RE = re.compile(r"^flow-\d{8}-[a-z]+(?:-(qc|s81|head|kv|hbm))?$")
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
    "auto_resign.tsv": "time\tid\tdie\tname\thost\ttag\tstatus\tout\tbuild_commit\twhy",
}
GEOM_TEXT = ""                                         # lanes/GEOM-REVIEW.md of this tick (AUTO-GEOM revocation)
DRY = False


# ------------------------------------------------------------------------------------------------ small helpers
def now_s():
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


_LOG_SEEN = {}                 # message -> [last written time, suppressed count]
LOG_DEDUP_S = float(os.environ.get("AP_LOG_DEDUP_S", "900"))


def log_dedup(msg, now=None):
    """FLOW-HEALTH-1 11-15 (FABLE-FLOW-1000 class 10: 1,791 of 3,023 log lines were repeats): a message identical to one written in the last
    LOG_DEDUP_S seconds is not written again; the next write of it carries '(+N identical suppressed)'.  -> the text to write, or None"""
    now = time.time() if now is None else now
    if LOG_DEDUP_S <= 0 or len(msg) > 2000:
        return msg
    e = _LOG_SEEN.get(msg)
    if e and now - e[0] < LOG_DEDUP_S:
        e[1] += 1
        return None
    n = e[1] if e else 0
    if len(_LOG_SEEN) > 5000:
        _LOG_SEEN.clear()
    _LOG_SEEN[msg] = [now, 0]
    return msg + (f" (+{n} identical suppressed)" if n else "")


def log(msg):
    msg = log_dedup(msg)
    if msg is None:
        return
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


SSH_FAILS = {}          # host -> failed ssh calls in this tick process (a tick is one process)
SSH_SKIP_AFTER = 2


def ssh_skipped(host):
    """FABLE-FLOW-0755 H (tick 556-796 s, poll_running 262 s waiting on epyc7): a host whose ssh failed (255 / timeout) twice in this tick is skipped for the rest of the tick"""
    return SSH_FAILS.get(ssh_host(host), 0) >= SSH_SKIP_AFTER


def ssh_note(host, rc, out=""):
    h = ssh_host(host)
    if rc in (255, 124) and not (out or "").strip():
        SSH_FAILS[h] = SSH_FAILS.get(h, 0) + 1
    elif rc == 0:
        SSH_FAILS.pop(h, None)


def rpy(host, code, args, timeout=600):
    """run python code on host (read-mostly probes) with JSON args on argv; returns parsed JSON or {'error': ...}"""
    if ssh_skipped(host):
        return {"error": f"probe skipped: ssh to {host} failed {SSH_SKIP_AFTER}x this tick (not checked)"}
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ControlPath=none", ssh_host(host),
           "python3", "-I", "-", shlex.quote(json.dumps(args))]
    rc, out, err = sh(cmd, timeout=timeout, input=code)
    ssh_note(host, rc, out)
    for line in reversed(out.splitlines()):
        if line.startswith("AP_JSON "):
            return json.loads(line[8:])
    return {"error": f"probe rc {rc}: {(err or out).strip()[-400:]}"}


def rbash(host, script, timeout=1800):
    if ssh_skipped(host):
        return 255, "", f"skipped: ssh to {host} failed {SSH_SKIP_AFTER}x this tick (not checked)"
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ControlPath=none", ssh_host(host),
           "bash", "-s"]
    r = sh(cmd, timeout=timeout, input=script)
    ssh_note(host, r[0], r[1])
    return r


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


import importlib.util as _ilu_cc
_cc_spec = _ilu_cc.spec_from_file_location("cell_cap", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "die_plan", "cell_cap.py"))
_cc = _ilu_cc.module_from_spec(_cc_spec)
_cc_spec.loader.exec_module(_cc)
SPLIT_CELLS = _cc.SPLIT_CELLS          # WAVE-FLOW-R2 11-17: the ONE cell limit


def cell_waiver_for(die, typ):
    """the ruling id lanes/CELL-WAIVER.tsv names for this die / type ('' = none); only rNNN counts"""
    try:
        for ln in read_coord("lanes/CELL-WAIVER.tsv").splitlines():
            f = ln.split("\t")
            if len(f) >= 3 and f[0] == die and f[1] == typ and re.fullmatch(r"r\d{3,4}", f[2].strip()):
                return f[2].strip()
    except (OSError, ValueError, AttributeError):
        pass
    return ""


def stops_off_for(die):
    """WAVE-PILOT-FIX 11-18 (COORD / OWNER r703: remove all safety stops): True when the committed kit_wave.json has stops_off true and DIE is not excluded (hbm is)"""
    try:
        cfg = json.loads((AP_DIR / "kit_wave.json").read_text())
    except (OSError, ValueError):
        return False
    import flow_guard as _FG
    return _FG.stops_off_die(cfg, die)


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


CELL_BIG_SEEN = os.environ.get("OT_CELL_BIG_SEEN") or os.path.expanduser("~/.local/state/ap-cell-big-seen.json")


def cell_big_first_today(die, typ, today=None):
    """True the first time (die, type) is noted today; the day's set lives in a small state file (enqueue runs in a fresh process every call)"""
    today = today or time.strftime("%Y-%m-%d")
    key = f"{die}/{typ}"
    try:
        d = json.loads(Path(CELL_BIG_SEEN).read_text())
        if d.get("day") != today:
            d = {}
    except (OSError, ValueError):
        d = {}
    if key in (d.get("seen") or []):
        return False
    try:
        Path(CELL_BIG_SEEN).parent.mkdir(parents=True, exist_ok=True)
        tmp = f"{CELL_BIG_SEEN}.{os.getpid()}"
        Path(tmp).write_text(json.dumps({"day": today, "seen": sorted(set(d.get("seen") or []) | {key})}))
        os.replace(tmp, CELL_BIG_SEEN)
    except OSError:
        pass
    return True


def validate_row(r):
    if not r["die"] or not r["type"]:
        return "die/type missing"
    if not KIT_RE.match(r["kit"]) or ".." in r["kit"]:
        return "kit must be HOST:/srv/opentallas-scratch[N]/claude/<lane>/... (absolute, no ..)"
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
    # WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 D): the one cell limit (die_plan/cell_cap.py) is enforced at enqueue, whatever launched the kit; waiver = a
    # ruling id in lanes/CELL-WAIVER.tsv (die<TAB>type<TAB>rNNN)
    if c > SPLIT_CELLS and stops_off_for(r.get("die")):
        if cell_big_first_today(r.get("die"), r.get("type")):      # FABLE-FLOW-0555 I: one line per item per day (it was 77% of the log)
          log(f"KIT-WAVE CELL-BIG {r.get('die')}/{r.get('type')}: {int(c)} cells > {SPLIT_CELLS} (the one cell limit): enqueued anyway (stops_off); the owner may split the type")
    elif c > SPLIT_CELLS and not cell_waiver_for(r.get("die"), r.get("type")):
        return f"SPLIT-NEEDED: cells {int(c)} > {SPLIT_CELLS} (the one cell limit); split the type or waive with a ruling id in lanes/CELL-WAIVER.tsv"
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
out["fail_marks"] = [f for f in ("FAIL_PREFLOOR", "FAIL_POSTCTS", "FAIL_route") if os.path.exists(os.path.join(K, f))]
# S81-OTHERFAIL-1 11-07: the marker's own text (e.g. a late async 'LEC NOT EQUIVALENT') goes into the REJECT reason
def _mark_text(f):
    try:
        with open(os.path.join(K, f), errors="replace") as fh:
            return " | ".join(ln.strip() for ln in fh.read().splitlines() if ln.strip())[:240]
    except Exception:
        return ""
out["fail_text"] = {f: _mark_text(f) for f in out["fail_marks"]}
lm = [os.path.getmtime(p) for p in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "*")) +
      glob.glob(os.path.join(K, "*.log"))]
out["log_age_s"] = time.time() - max(lm) if lm else None
# KW-FIX-30 11-07: the flow's own logs only; the kit's pre-route LEC writes K/lec*.log all along its run, so with
# log_age_s alone a route beside a running proof (BESIDE-PROOF) was always held as "logs recent"
lf = [m for m, p in zip(lm, glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "*")) + glob.glob(os.path.join(K, "*.log")))
      if not os.path.basename(p).startswith("lec")]
out["flow_log_age_s"] = time.time() - max(lf) if lf else None
# Physical goals may finish while their original admitted proof owner keeps running.
# Receipts are immutable per invocation; never infer completion from an ODB alone.
import hashlib
_ph=hashlib.sha256()
for _f in ('config.mk','constraint.sdc','pins.json','core.json','budget.json','clock_binding.json'):
    try:
        _b=open(os.path.join(K,_f),'rb').read(); _ph.update(_f.encode()); _ph.update(_b)
    except OSError: pass
out["physical_identity"] = _ph.hexdigest()
out["physical_starts"] = []
for _f in glob.glob(os.path.join(K,"lec_async.runs","*.json")):
    try: out["physical_starts"].append(json.load(open(_f)))
    except (OSError,ValueError): pass
out["physical_completions"] = []
for f in glob.glob(os.path.join(K, "physical_completion", "*.json")):
    try:
        r = json.load(open(f))
        start = json.load(open(os.path.join(K, "lec_async.runs", r["run_id"] + ".json")))
        if (r.get("schema") == "opentallas.physical_completion.v1" and r.get("goal") == start.get("goal")
                and r.get("started") == start.get("started") and r.get("ended", 0) >= r.get("started", 0)):
            r["path"] = f
            cp=r.get("checkpoint") or {}
            try:
                cf=os.path.join(K,cp["path"]); cs=os.stat(cf)
                r["checkpoint_current"]=(os.path.realpath(cf).startswith(os.path.realpath(K)+os.sep)
                    and cs.st_size==cp["size"] and cs.st_mtime_ns==cp["mtime_ns"] and cs.st_size>0)
            except (OSError,KeyError,TypeError): r["checkpoint_current"]=False
            out["physical_completions"].append(r)
    except (OSError, ValueError, KeyError, TypeError):
        pass
out["physical_completions"].sort(key=lambda r: r.get("ended", 0), reverse=True)
def _async_read(n):
    try: return open(os.path.join(K, "lec_async." + n)).read().strip()
    except OSError: return ""
out["async_proof"] = dict(identity=_async_read("identity"), owner=_async_read("owner"),
                          pid=_async_read("pid"), done=os.path.exists(os.path.join(K, "lec_async.done")),
                          rc=_async_read("rc"))
# A lane-adopted runner has no autopilot client process exit. Keep its honest
# current invocation receipt rather than inferring success from an ODB.
try:
    image = open(os.path.join(K, "image.txt")).read()
    starts = re.findall(r"^image .* start (\S+)$", image, re.M)
    ends = re.findall(r"^end (\S+) rc (-?\d+)$", image, re.M)
    if starts and ends:
        out["runner_exit"] = dict(start=starts[-1], end=ends[-1][0], rc=int(ends[-1][1]),
                                  path=os.path.join(K, "image.txt"))
except OSError:
    pass
try:
    import subprocess
    ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60).stdout.split()
    busy = False
    if ids:
        js = json.loads(subprocess.run(["docker", "inspect"] + ids, capture_output=True, text=True, timeout=120).stdout)
        st = [c.get("State", {}).get("StartedAt", "") for c in js
              if any(m.get("Source", "").rstrip("/") == K.rstrip("/") for m in c.get("Mounts", []))]
        busy = bool(st)
        out["active_containers"] = [c.get("Name", "").lstrip("/") for c in js
                                    if any(m.get("Source", "").rstrip("/") == K.rstrip("/")
                                           for m in c.get("Mounts", []))]
        out["started"] = sorted(x for x in st if x)
    # FLOW-TIME-1 11-07: only the kit's pre-route LEC is alive: its own unit (<owner>-lec) and/or the owner container
    # that already published its place result and now only waits for the exec-form proof.  The kit's lec_async.sh can
    # reuse that live proof for the next stage, and sign-off still waits for the verdict (lec_async.sh finish).
    owner, names = _async_read("owner"), out.get("active_containers") or []
    try:
        reuse = "LEC_ASYNC reuse proof" in open(os.path.join(K, "lec_async.sh"), errors="replace").read()
    except OSError:
        reuse = False
    def _phase_ok(n):
        try:
            return json.load(open(os.path.join(K, "physical_completion", n + ".json"))).get("rc") == 0
        except (OSError, ValueError, AttributeError):
            return False
    # KW-FIX-30 11-07: or NO container at all while the proof's own unit still waits for memory (ot-heavy queue):
    # the owner published a place receipt rc 0 and the watcher that will run the proof is alive on this host
    def _watcher_alive():
        try:
            os.kill(int(_async_read("pid")), 0)
            return True
        except PermissionError:
            return True
        except (OSError, ValueError):
            return False
    out["proof_only"] = bool(owner and reuse and os.path.exists(os.path.join(K, "lec_async.ready"))
                             and _async_read("identity") and not out["async_proof"]["done"]
                             and not out["async_proof"]["rc"] and not os.path.exists(os.path.join(K, "lec_async.stop"))
                             and all(n == owner + "-lec" or (n == owner and _phase_ok(n)) for n in names)
                             and ((busy and names) or (not names and _phase_ok(owner) and _watcher_alive())))
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
out["gds_gap"] = (bool(re.search(r"^export ADDITIONAL_LEFS", cfg, re.M)) and "ADDITIONAL_GDS" not in cfg
                  and not re.search(r"^export GDS_ALLOW_EMPTY", cfg, re.M))
# KW-RESUME-1: a kit-wave stage-resumed kit (K/resume.json: ORFS steps reused from the previous attempt) -> PROVENANCE
try:
    with open(os.path.join(K, "resume.json")) as f: rj = json.load(f)
    out["resume"] = {k: rj.get(k) for k in ("schema", "start", "reused_steps", "source", "why", "applied", "n_link",
                                            "n_copy", "bytes_link", "bytes_copy")}
except Exception:
    out["resume"] = None
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
until = float("inf")
if a.get("retained_return_to"):
    root = os.path.dirname(K)
    job = jl(os.path.join(root, ".ot-job", "job.json")) or {}
    result = jl(os.path.join(root, ".ot-job", "result.json")) or {}
    expected = ((job.get("spec") or {}).get("return") or {}).get("to")
    started = job.get("started")
    ended = result.get("ended")
    if (job.get("schema") != "opentallas.ot_job.v1" or job.get("J") != root or result.get("J") != root
            or job.get("host") != result.get("host") or expected != a["retained_return_to"]
            or not isinstance(started, (int, float)) or not isinstance(ended, (int, float))
            or started < since or ended < started
            or not any(str(err).startswith("return copy:") for err in result.get("errors") or [])):
        out["error"] = "retained return receipt does not match this job"
        done()
    # The work tree can contain a returned input snapshot. Require timing evidence newer than execution start.
    since, until = started, ended
# newest signoff record written by this run
so = [p for p in glob.glob(os.path.join(K, "signoff*", "signoff.json")) if since <= os.path.getmtime(p) <= until]
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
    ff = (d.get("corners") or {}).get("ff")
    if a.get("retained_return_to") and isinstance(ff, dict):
        out["signoff"]["corners"] = {"ff": {k: ff[k] for k in ("done", "rc", "errors", "std_min_start",
                                                             "std_wns_min", "std_nviol_min") if k in ff}}
    try:
        out["signoff"]["odb_bytes"] = os.path.getsize(out["signoff"]["odb"])
    except Exception:
        out["signoff"]["odb_bytes"] = 0
    # KW-PROV-1 11-03 (COORD 17:50 (C)): a kit built on PROVISIONAL child views (kit_wave marker
    # provisional_views.json) is never a sign-off for the count until every child is FINAL (signed child libs in
    # macros/, sha-checked) and this record is the STA-only re-sign on them (newer than the final libs):
    # SIGNED -> LOCAL_PASS_NEEDS_PARENT (WAIT-PARENT: provisional.tsv, no archive; retry_pending re-probes)
    pv = jl(os.path.join(K, "provisional_views.json"))
    if isinstance(pv, dict) and str(pv.get("schema", "")).startswith("opentallas.provisional_views"):
        import hashlib
        kids = pv.get("children") or {}
        owed = sorted(m for m, v in kids.items() if not (isinstance(v, dict) and v.get("final")))
        bad, newest = [], 0.0
        for m, v in kids.items():
            for n, h in ((v or {}).get("final_sha256") or {}).items():
                f = os.path.join(K, "macros", n)
                try:
                    ok = hashlib.sha256(open(f, "rb").read()).hexdigest() == h
                    newest = max(newest, os.path.getmtime(f))
                except Exception:
                    ok = False
                if not ok:
                    bad.append(n)
        stale = bool(newest) and os.path.getmtime(so[-1]) < newest
        s_ = out["signoff"]
        s_["provisional"] = {"status": pv.get("status"), "owed": owed, "lib_mismatch": bad, "stale_signoff": stale}
        if s_.get("verdict") == "SIGNED" and (pv.get("status") != "FINAL" or owed or bad or stale):
            why = ("provisional_child_view: built on PROVISIONAL child views " + ",".join(
                "%s:%s" % (m, (v or {}).get("source", "?")) for m, v in sorted(kids.items()))
                + (" (owed %s)" % ",".join(owed) if owed else "") + (" (lib sha mismatch %s)" % ",".join(bad) if bad else "")
                + (" (sign-off predates the final child libs)" if stale else "")
                + "; STA-only re-sign on the signed child libs owed (KW-PROV-1)")
            s_.update(verdict="LOCAL_PASS_NEEDS_PARENT", local_verdict="SIGNED", release_qualified=False,
                      reasons=list(s_.get("reasons") or []) + [why[:400]])
for f in ("FAIL_PREFLOOR", "FAIL_POSTCTS", "FAIL_route"):
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
# HOLD-FLOW-R 11-16 (closure lever 4, WARNING ONLY, never a verdict): the CTS hold-buffer count of this run against the kit's
# previous form (tools/die_plan/cts_hold_jump.py, same sum of RSZ-0032 "Inserted N hold buffers" and the same 2x / 200 rule).
# The previous count lives in K/cts_hold_count.json, advanced only when the CTS log is a new file (mtime), so re-probing the
# same run never compares it with itself.
try:
    _c = [p for p in logs if os.path.basename(p).startswith("4_1_cts")]
    if _c:
        _n = sum(int(x.replace(",", "")) for x in re.findall(r"Inserted\s+([0-9][0-9,]*)\s+hold\s+buffers?", rd(_c[-1], 4000000), re.I))
        _m = os.path.getmtime(_c[-1]); _pf = os.path.join(K, "cts_hold_count.json"); _st = (jl(_pf) or {}) if os.path.isfile(_pf) else {}
        _prev = _st.get("previous") if _st.get("mtime") == _m else _st.get("current")
        out["cts_hold"] = {"current": _n, "previous": _prev}
        if _prev and _n >= 200 and _n >= 2 * _prev:
            out["cts_hold_jump"] = "OT_CTS_HOLD_JUMP FLAG: %d CTS hold buffers vs %d in the previous form (%.1fx >= 2x): read the CTS hold scope / margin before detail route" % (_n, _prev, _n / float(_prev))
            sys.stderr.write("WARN " + out["cts_hold_jump"] + " kit=" + K + "\n")
        if _st.get("mtime") != _m:
            try:
                json.dump({"current": _n, "previous": _prev, "mtime": _m}, open(_pf, "w"))
            except OSError:
                pass
except Exception as _e:
    out["cts_hold_error"] = str(_e)[:120]
# A legacy gate can write a PASS receipt, then throw in its clock-source census.
# This is a tool failure, not a timing verdict. Require all three current-run
# witnesses; PASS/exit 1 alone must never override a real setup/hold failure.
marker = out.get("FAIL_POSTCTS", "")
p = os.path.join(K, "postcts_gate_tt.json")
q = os.path.join(K, "postcts_gate_TT.log")
if ("TT global-routing insertion gate failed: PASS exit 1" in marker
        and os.path.isfile(p) and os.path.getmtime(p) >= since
        and os.path.isfile(q) and os.path.getmtime(q) >= since
        and (jl(p) or {}).get("verdict") == "PASS"):
    m = re.search(r"(?m)^Error: grt_policy_tt\.tcl, \d+ clock [^\n]+ has no unique rise source insertion arrival\s*$", rd(q))
    if m:
        out["clock_source_error"] = m.group(0).strip()[:300]
# WF-1 11-14 (COORD: sle_st_b_v1 a7 STRUCTURAL post-cts-hold, really the TT post-CTS gate process dying, OOM on a full host): a FAIL_POSTCTS
# whose gate record postcts_gate_tt.json is missing or older than this run, or whose gate log is missing / older / has no verdict
# line, did not judge anything: infra (gate lost), never a hold verdict.
if marker:
    _lost = []
    if not os.path.isfile(p) or os.path.getmtime(p) < since:
        _lost.append("postcts_gate_tt.json " + ("missing" if not os.path.isfile(p) else "older than this run"))
    if not os.path.isfile(q) or os.path.getmtime(q) < since:
        _lost.append("postcts_gate_TT.log " + ("missing" if not os.path.isfile(q) else "older than this run"))
    elif not re.search(r"(?im)\b(PASS|FAIL|verdict|WNS|slack)\b|^Error\b", rd(q, 400000)):
        _lost.append("postcts_gate_TT.log truncated (no verdict or error line)")
    if marker and _lost:
        out["gate_lost"] = "; ".join(_lost)
# KW-FIX-44 11-10 (COORD (3)): grt183_make.sh OT_GRT_CONGESTED_FAIL (full GRT ended congested, overflow over the floor)
# is the congestion class; historical OT_GRT_TIMECAP is a retired FLOW limit, not a hardware timing verdict
pat = {"hold_structural": r"OT_HOLD_STRUCTURAL[^\n]*", "congestion": r"GRT-0116[^\n]*|[Rr]outing congestion too high[^\n]*|OT_GRT_CONGESTED_FAIL[^\n]*",
       # FAILFAST-1 11-11: failfast_rules.py progress stops (GRT / DRT no progress); a hold stop prints OT_HOLD_STRUCTURAL
       "grt_no_progress": r"OT_GRT_NO_PROGRESS[^\n]*", "drt_no_progress": r"OT_DRT_NO_PROGRESS[^\n]*",
       "grt_timecap": r"OT_GRT_TIMECAP[^\n]*",
       "segfault": r"Segmentation fault[^\n]*|Signal 11 received[^\n]*|SIGSEGV[^\n]*|core dumped[^\n]*",
       "oom": r"Error 137[^\n]*|\] Error 24[17][^\n]*|\bKilled\b[^\n]*|[Oo]ut of memory[^\n]*|std::bad_alloc[^\n]*|OOMKilled[^\n]*",
       # design gates that print their verdict but write no FAIL_PREFLOOR/FAIL_POSTCTS marker (custom runners)
       "gate_fail": r"(?m)^(?:CORE_PREFLIGHT|KIT_PREFLIGHT|RP1_GATE|SDC_LINT|S6_GRT_GATE|OT_HOLD_GATE) FAIL\b[^\n]*",
       "orfs_error": r"\[ERROR [A-Z]+-\d+\][^\n]*"}
for k, p in pat.items():
    if k == "orfs_error":
        # Hold repair catches bounded RSZ errors and continues. Diagnose the
        # terminal tool error rather than an earlier caught repair chunk.
        # WAVE-RECIPE-1 11-14 (FABLE-HARD-S81: t29, serdes t13, iqf t1, slice t40 booked "RSZ-0060 buffer-cap crash"): an RSZ-0060
        # the hold guard CAUGHT (its "OT_HOLD_GUARD_GRT chunk N:" line follows, as kit_resume.HOLD_GUARD_CAP_RE) is no error;
        # the run's real end (Error 241 OOM kill, a later tool error, a gate FAIL) is classified instead.
        caught_re = r"(?m)^\[ERROR RSZ-0060\][^\n]*\n(?=(?:[^\n]*\n){0,4}OT_HOLD_GUARD_GRT chunk \d+:)"
        caught = re.findall(caught_re, runlog) or re.findall(caught_re, txt)
        if caught:
            out["caught_errors"] = [e.strip()[:300] for e in caught[-5:]]
        errors = re.findall(p, re.sub(caught_re, "", runlog)) or re.findall(p, re.sub(caught_re, "", txt))
        if errors:
            out[k] = errors[-1][:300]
            # KW-FIX-43 11-09: a gate FAIL printed after the last tool error is what stopped the run
            # (hd_ctl: 10 caught RSZ-0060, then PIN_AUDIT FAIL).
            at = runlog.rfind(errors[-1])
            gates = re.findall(r"(?m)^[A-Z][A-Z0-9_]+ FAIL\b[^\n]*", runlog[at + len(errors[-1]):]) if at >= 0 else []
            if gates:
                out[k] = gates[-1][:300]
            out["orfs_errors"] = [e[:300] for e in errors[-5:]]
    else:
        m = re.search(p, alltxt)
        if m: out[k] = m.group(0)[:300]
# R-CLOCK (HOLD-TAP-1 / COORD 11-13 07:2x): the opt-in pre-GRT hold build fell back (tool error or its own guard):
# never a verdict (the GRT repair takes the debt), but recorded on the job, not silent
fb = re.findall(r"(?m)^PREGRT_HOLD_FALLBACK\b[^\n]*", runlog)
if fb: out["pregrt_hold_fallback"] = fb[-1][:300]
cells = 0
for js in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "*.json")):
    d = jl(js) or {}
    for k, v in d.items():
        if k.endswith("__design__instance__count__stdcell") and isinstance(v, (int, float)):
            cells = max(cells, int(v))
out["cells"] = cells
nc = jl(os.path.join(K, "native_cell_count.json")) or {}
if nc.get("schema") == "opentallas.native_cell_count.v1" and type(nc.get("stdcells")) is int:
    out["native_cells"] = nc["stdcells"]
g = rd(next(iter(glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "5_1_grt.log"))), ""))
tot = re.findall(r"^Total\s+.*?(\d+)\s*$", g, re.M)
out["grt_overflow"] = int(tot[-1]) if tot else None
# DIE-HBM-97 11-10: the last Nesterov row before each GPL-1010 (per-pass iteration cap) of this run's global placement
gl = []
for p in glob.glob(os.path.join(K, "run", "logs", "asap7", "*", "base", "3_3_place_gp*.log")):
    if os.path.getmtime(p) < since:
        continue
    last = ""
    for ln in rd(p).splitlines():
        if "GPL-1010" in ln:
            gl += ["KW_GPL " + last, "KW_GPL " + ln.strip()]
            last = ""
        elif re.match(r"^\s*\d+ \|\s+[0-9.]+ \|", ln) or re.search(r"Iter:\s*\d+\s+overflow:", ln, re.I):
            last = ln.strip()
if gl:
    out["gpl_cap"] = "\n".join(gl[-40:])
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
# ROUTED-KEEP 11-18 (COORD; QC-TYPES-R3 sle_hc0__cl929603c0 cl38badc56 / cl4baa7c9c, the S81 late-ECO near misses): a ROUTED attempt is the
# input of the late ECO, a re-sign and the export.  Its results (6_final.odb / .spef, 5_2_route.odb, config.mk) stay until it is SIGNED and
# exported or a newer routed attempt of the same type supersedes it (kit_slim strip owns that cleanup); a failed verdict never deletes them.
routed = glob.glob(os.path.join(K, "run", "results", "asap7", "*", "base", "6_final.odb"))
if routed and a.get("keep_routed", True):
    out["preserved"] = sorted(routed)
    out["reason"] = "routed attempt (6_final.odb): kept for the late ECO / re-sign / export until SIGNED+exported or superseded"
    done()
# A re-admission can fail before touching a prior GRT/CTS/route checkpoint.
# That physical input is not failed output of this attempt and must survive.
cutoff = a.get("preserve_before")
if cutoff:
    prior = [p for p in glob.glob(os.path.join(K, "run", "results", "**", "[2-6]*.odb"), recursive=True)
             if os.path.getmtime(p) <= float(cutoff)]
    if prior:
        out["preserved"] = sorted(prior)
        out["reason"] = "physical checkpoint predates this attempt; required input retained"
        done()
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
        target = os.path.join(vd, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(src, target)
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

PROBE_AUTO_EXPORT = r'''
import hashlib, json, os, socket, sys, time
a = json.loads(sys.argv[1]); out = {}
so = a["signoff"] if os.path.isfile(a["signoff"]) else a.get("fallback")
try:
    raw = open(so, "rb").read(); rec = json.loads(raw)
    if rec.get("profile") == "minimal" and rec.get("verdict") == "SIGNED":
        sha = hashlib.sha256(raw).hexdigest(); sp = os.path.expanduser("~/.local/state/ot-auto-export/spool")
        os.makedirs(sp, exist_ok=True)
        row = dict(schema="opentallas.auto_export.spool.v1", signoff=os.path.realpath(so), record=sha, host=socket.gethostname(),
                   name=rec.get("name"), generated=rec.get("generated"), queued=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   die=a.get("die"), element=a.get("element"), kind=None, via="autopilot")
        p = os.path.join(sp, sha[:16] + ".json"); t = p + ".tmp%d" % os.getpid()
        open(t, "w").write(json.dumps(row)); os.replace(t, p); out["queued"] = p
    else:
        out["error"] = "not R-MINIMAL SIGNED (%s/%s)" % (rec.get("profile"), rec.get("verdict"))
except Exception as e:
    out["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
print("AP_JSON " + json.dumps(out))
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
out["files_sha256"] = {rel: sha(path) for rel, path in files.items()}
# Passive retention only: a missing/invalid graph never becomes clock coverage.
W = a.get("clock_witness_dir") or S
wp = os.path.join(W, "child_clock_witness.json")
if os.path.isfile(wp) or a.get("clock_witness_dir"):
    try:
        wd = json.load(open(wp))
        if wd.get("schema") != "opentallas.child_clock_witness.v1" or wd.get("qualification") != "NOT_ASSERTED":
            raise ValueError("unknown child clock witness schema/qualification")
        if not {"6_final.odb", "6_final.spef", "6_final.v"}.issubset(wd.get("native", {})):
            raise ValueError("missing exact native source/ODB/SPEF identities")
        for rel, digest in wd["native"].items():
            if os.path.basename(rel) != rel or sha(os.path.join(B, rel)) != digest:
                raise ValueError("native routed fixture identity mismatch: " + rel)
        witness_files = {"child_clock_witness.json": wp}
        for corner in ("tt", "ff"):
            cr = wd["corners"][corner]
            if cr["counts"]["missing"] or cr["counts"]["refs"] < 1:
                raise ValueError("incomplete native child clock endpoints")
            required = {"child_clock_" + corner + "_" + role + ".tsv" for role in ("endpoints", "pairs", "roots", "clocks", "masters", "counts", "inputs")}
            if not required.issubset({os.path.basename(rel) for rel in cr["files"]}):
                raise ValueError("missing full native endpoint/pair/identity payload")
            if not any(os.path.basename(rel) in ("session.tcl", "export_" + corner + ".tcl") and digest == cr["extraction_tcl_sha256"] for rel, digest in cr["files"].items()):
                raise ValueError("missing exact native extraction session")
            for rel, digest in cr["files"].items():
                if os.path.isabs(rel) or ".." in rel.split(os.sep):
                    raise ValueError("unsafe witness payload path")
                path = os.path.join(W, rel)
                if sha(path) != digest:
                    raise ValueError("child clock payload identity mismatch: " + rel)
                witness_files[rel] = path
        out["clock_witness"] = {"status": "RETAINED", "path": "child_clock_witness.json", "sha256": sha(wp),
                                "qualification": "NOT_ASSERTED", "hierarchical_expansion": "NOT_ASSERTED",
                                "expected_view_lib_sha256": {c: wd["corners"][c].get("exported_liberty_sha256") for c in ("tt", "ff")}}
        files.update(witness_files)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        out["clock_witness"] = {"status": "FAILED", "error": str(exc), "qualification": "NOT_ASSERTED"}
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
    prov = dict(kit=kitblk, verdict=("SIGNED (autopilot R-MINIMAL: DRC 0, TT setup >= -42 ps, FF hold >= 0; LEC advisory)"
                                     if SP.is_minimal() else "SIGNED (autopilot: signoff.py + routed LEC EQUIVALENT all_shown)"),
                views_status="signoff" if not problems else "incomplete: " + "; ".join(problems),
                src=j["src"], src_commit=j.get("src_commit"), flow_tag=j.get("flow_tag"), autopilot_id=j["id"])
    if r.get("clock_witness"):
        witness = dict(r["clock_witness"])
        if witness.get("status") == "RETAINED":
            hashes = r.get("files_sha256") or {}
            bindings = {c: hashes.get(f"{mod}_{c}.lib") for c in ("tt", "ff")}
            expected = witness.pop("expected_view_lib_sha256", {})
            if any(not digest or (expected.get(c) and expected[c] != digest) for c, digest in bindings.items()):
                witness.update(status="FAILED", error="exported child Liberty identity is absent or mismatched")
            else:
                witness["view_lib_sha256"] = bindings
        prov["child_clock_witness"] = witness
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
    if so and SP.is_minimal():
        # R-MINIMAL: DRC 0 + TT setup >= -42 ps + FF hold >= 0 from the measured numbers; io_hold_parent (WAIT-PARENT), PG,
        # DRV, antenna, clock band ... are advisories (so a record of an older kit-frozen signoff.py is judged the same way)
        jm = SP.judge(so)
        if jm["verdict"] == "SIGNED":
            adv = "; ".join(jm["advisories"])[:300]
            return "SIGNED", "signed", (f"SIGNED (R-MINIMAL, achieved period {jm['achieved_period_ps']} ps"
                                        + (f"; advisory: {adv}" if adv else "") + ")")
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
    if client.get("publish_return"):
        return "CRASH", "infra-publish-return", client["publish_return"]["reason"]
    if c.get("FAIL_PREFLOOR"):
        return "STRUCTURAL", "preflight", "FAIL_PREFLOOR " + c["FAIL_PREFLOOR"]
    if c.get("FAIL_route"):
        fr = c["FAIL_route"]
        if re.search(r"DRT-0255", fr):
            net = re.search(r"path of net (\S+)", fr)
            return "STRUCTURAL", "drt-nopath", f"DRT-NOPATH net {net.group(1) if net else '?'}: {fr[:260]}"
        # COORD 11-19 (col_h9 r1/r2: host-guard SIGKILL in the GRT stage filed FAIL_route): a make Error 241/247 / rc 137 / 143 is the host killing the job (ot-oom-age guard, earlyoom), not a route
        # failure: infra-oom, free resubmit.  The run-log probe (c["oom"]) or the failure text itself names it.
        if c.get("oom"):
            return "CRASH", "infra-oom", c["oom"]
        km = re.search(r"\] Error 24[17]\b[^\n]*|\brc[ =]+(?:137|143)\b[^\n]*", " ".join(str(x) for x in (fr, c.get("runlog_tail"), c.get("orfs_error"), client.get("msg")) if x))
        if km:
            return "CRASH", "infra-oom", km.group(0)[:300]
        return "CRASH", "route-make-fail", fr[:300]
    # DIE-HBM-97 11-10 (COORD): a global placement that stopped at the per-pass Nesterov cap above overflow 0.1 is the
    # cause of what follows it (kv_line vC: 459k resizer buffers, DPL-0038 at 153%), not a crash or a congestion row
    gpl = KW.gpl_cap_noconverge(c.get("gpl_cap") or "")
    if gpl:
        return "STRUCTURAL", "gpl-noconverge", gpl
    if (c.get("clock_source_error") and
            "TT global-routing insertion gate failed: PASS exit 1" in c.get("FAIL_POSTCTS", "")):
        # Not in INFRA_KINDS: keep the physical checkpoint and await the fixed
        # flow/source refresh; retrying the same broken gate cannot help.
        return "CRASH", "infra-clock-source", c["clock_source_error"]
    if c.get("FAIL_POSTCTS") and c.get("gate_lost") and not c.get("clock_source_error"):
        # WF-1 11-14: the gate never produced a verdict (process killed, host out of memory): infra, resubmitted like an oom kill
        return "CRASH", "infra-oom", f"post-CTS gate lost ({c['gate_lost']}); FAIL_POSTCTS {c['FAIL_POSTCTS'][:160]}"
    if c.get("FAIL_POSTCTS"):
        return "STRUCTURAL", "post-cts-hold", "FAIL_POSTCTS " + c["FAIL_POSTCTS"]
    if c.get("hold_structural"):
        return "STRUCTURAL", "hold-structural", c["hold_structural"]
    if c.get("grt_no_progress"):
        # FAILFAST-1 11-11: class GRT_NO_PROGRESS (kit-wave class ROUTING; the line carries rounds, trend, last overflow per layer)
        return "STRUCTURAL", "grt-no-progress", c["grt_no_progress"]
    if c.get("drt_no_progress"):
        return "STRUCTURAL", "drt-no-progress", c["drt_no_progress"]
    if c.get("congestion"):
        # OWNER 11-14: GRT overflow is just a FAIL with the numbers, not a STRUCTURAL verdict
        return "FAIL", "grt-overflow", c["congestion"]
    if c.get("grt_timecap"):
        # Old pinned wrappers could stop a progressing repair on elapsed time.
        # Preserve the failure line, but do not call that a hardware verdict.
        return "FAIL", "grt-timecap", c["grt_timecap"]
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
    if c.get("oom"):
        return "CRASH", "infra-oom", c["oom"]
    # FABLE-FLOW-1000 (1): 30 stage jobs died with ENOSPC in one hour and were filed CRASH -> structural.tsv; a full disk is the HOST's failure, the job resubmits (ot-run places it on a host with room)
    _txt = " ".join(str(x) for x in (c.get("orfs_error"), c.get("runlog_tail"), client.get("msg")) if x)
    if re.search(r"No space left on device|ENOSPC|disk quota exceeded", _txt, re.I):
        return "CRASH", "infra-disk", "no space left on device: " + (re.search(r".{0,120}(?:No space left on device|ENOSPC|disk quota exceeded).{0,60}", _txt, re.I).group(0).strip())
    if client.get("exit") in (137, 143) and client.get("watchdog"):
        w = client["watchdog"]
        why = w.split(" why ", 1)[1] if " why " in w else "reason not logged (WATCHDOG.txt of that tick)"
        kind = "watchdog-superseded" if why.startswith("SUPERSEDED") else "watchdog-stopped"
        return "CRASH", kind, f"exit {client['exit']}: stopped by the hub WATCHDOG ({w[:16]}): {why}"[:600]
    if client.get("exit") in (137, 143):
        # COORD 11-05 07:01: exit 137/143 with no memory line in the logs is a signal from outside, usually a lane's
        # docker stop, not an OOM (opstore_b stopped by ruling 06:51 came back 06:58). Not in INFRA_KINDS: no retry.
        return "CRASH", "infra-stopped", f"exit {client['exit']}, no OOM line in the run logs: stopped from outside"
    # KW-RELAUNCH-2 11-05: the cap is judged after the infra outcomes (sle_ctl a7630b8a28e2 was NOT RUN on a disk floor
    # and filed as cell-cap), on the kit's own pre-floorplan native count when it has one (the post-place stdcell
    # count adds TAPCELL/endcaps: 522k placed = 316k native), the basis kit_wave.after_place and native_cell_cap.tcl use.
    if client.get("exit") == 0 and c.get("goal") == "grt" and c.get("grt_odb"):
        if c.get("grt_overflow") not in (None, 0):
            return "FAIL", "grt-overflow", f"GRT-only overflow {c['grt_overflow']}"
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


INFRA_KINDS = ("infra-oom", "infra-lost", "infra-notrun", "infra-orphan", "infra-disk")


def parse_client_log(text):
    """ot-run client log (+ our AP_RC line) -> outcome dict"""
    o = {}
    for key, prefix in (("admission_tools_fail", "ADMISSION_TOOLS FAIL:"), ("preflight_fail", "KIT_PREFLIGHT FAIL")):
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                o[key] = "\n".join(lines[index:index+6])[:600]
                break
    m = re.findall(r"ot-run: RAN on ([^\s:(]+)(?: \(unit ([^)]*)\))?:? exit (\d+)", text)
    if m:
        o["ran_on"], o["exit"] = m[-1][0], int(m[-1][2])
        if m[-1][1]:
            o["unit"] = m[-1][1].strip()
    if "ot-run: NOT RUN" in text and "ran_on" not in o:
        o["not_run"] = True
        o["msg"] = [l for l in text.splitlines() if "NOT RUN" in l][-1][:300]
    # A shell parse error in the local ot-run frontend occurs before it can emit
    # NOT RUN. Treat only that exact pre-admission signature as infrastructure;
    # HDL/flow syntax errors and errors after a payload ran remain design failures.
    shell_error = re.search(r"^(?:/[^\n:]+/)?ot-run: line \d+: syntax error[^\n]*$", text, re.M)
    if shell_error and "ran_on" not in o and "ot-heavy: admitted on" not in text:
        o["frontend_shell_fail"] = shell_error[0]
        o["not_run"] = True
        o["msg"] = "frontend shell syntax, payload not run: " + shell_error[0][:240]
    if "ot-run: NOT COMPLETED" in text:
        o["not_completed"] = True
        o["msg"] = [l for l in text.splitlines() if "NOT COMPLETED" in l][-1][:300]
    m = re.findall(r"^AP_RC=(\d+)", text, re.M)
    if m:
        o["ap_rc"] = int(m[-1])
        o.setdefault("exit", o["ap_rc"])
    if o.get("ap_rc") == o.get("exit") == 98 and o.get("ran_on"):
        root_pattern = r"(/srv/opentallas-scratch[^/\s:]*/claude/ot-jobs/[A-Za-z0-9_.-]+)"
        sealed = re.findall(r"^ot-job: SEALED " + root_pattern + r":", text, re.M)
        failed = re.findall(r"^ot-job: PUBLISH FAILED, job dir KEPT " + root_pattern + r": ([^\n]*return copy:[^\n]*)", text, re.M)
        if sealed and failed and sealed[-1] == failed[-1][0]:
            root, detail = failed[-1]
            o["publish_return"] = {"root": root, "reason": f"retained on {o['ran_on']}: {detail[:300]}"}
    m = [l for l in text.splitlines() if l.startswith("ot-run: interrupted (signal ") and "ot-run --cancel" in l]
    if m:
        o["cancelled"] = m[-1][:300]
    return o


# KW-FIX-44 11-09 (exit-143 class): the hub WATCHDOG (tools/autopilot/watchdog.py --act, watchdog.timer) stops a job's exact
# systemd scope when it is hung or SUPERSEDED (an older attempt than a live one on the current plan, a CANCELLED row, ...).
# The client then ends 137/143 with no OOM line, which classify called "stopped from outside" with no sender; 11-09 had 12
# such QC/HBM rows, every one a WATCHDOG STOP of its unit.  The STOP line names the unit, so the record now says who and why.
WATCHDOG_LOG = Path(os.environ.get("AP_WATCHDOG_LOG", str(COORD / "autopilot" / "WATCHDOG.log")))


def watchdog_stop(unit, since=0.0):
    """the WATCHDOG.log STOP line of this ot-heavy unit (oth-...) at or after `since`, or None"""
    if not unit:
        return None
    try:
        lines = WATCHDOG_LOG.read_text(errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if " STOP " not in line or (f" {unit}.scope" not in line and f" {unit} " not in line
                                     and not (unit.endswith("/") and f"/ot-jobs/{unit}" in line)):
            continue
        try:
            t = datetime.datetime.strptime(" ".join(line.split(" ")[:2]), "%Y-%m-%d %H:%M").timestamp()
        except ValueError:
            continue
        if t >= since - 120:
            return line[:400]
    return None


CANCEL_MARKS = AP_DIR / "cancel_marks.tsv"                                  # t \t dir \t who \t why: appended by kit_wave HUNG-WATCH
NOPROG_ACTIONS = COORD / "lanes" / "NOPROG-ACTIONS.tsv"                      # time(local) \t host \t type \t stage \t metric \t kit dir ...: one line per no-progress / unsignable cancel


def marked_cancel(j, now=None, marks=None, actions=None):
    """CANCELMARK-1400 (FLEET-WATCH-1400, FABLE-FLOW-1400 class 2): a job the watchdogs stopped (no-progress / unsignable cancel by ot-heavy-stop, HUNG-WATCH by docker stop) exits 143 with make
    'Error 241', and was classed infra-oom and resubmitted with more memory.  Both leave a hub-side record naming the job's dir; a record at or after this attempt started, whose dir is the
    job's path (or contains it / is inside it), makes the row CANCELLED, like an explicit ot-run --cancel.  -> the reason text or None"""
    path = str(j.get("path") or "").rstrip("/")
    if not path:
        return None
    since = float(j.get("started", 0)) - 60
    now = now or time.time()
    def hit(kit):
        kit = (kit or "").rstrip("/")
        return bool(kit) and (kit == path or kit.startswith(path + "/") or path.startswith(kit + "/"))
    for src, kind in ((marks or CANCEL_MARKS, "marks"), (actions or NOPROG_ACTIONS, "actions")):
        try:
            lines = Path(src).read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in reversed(lines[-4000:]):
            f = line.split("\t")
            try:
                if kind == "marks":
                    t, kit, who, why = float(f[0]), f[1], f[2], f[3] if len(f) > 3 else ""
                else:
                    t, kit, who, why = time.mktime(time.strptime(f[0], "%Y-%m-%d %H:%M:%S")), f[5], "no-progress watchdog", f[7] if len(f) > 7 else ""
            except (ValueError, IndexError):
                continue
            if t < since or t > now + 60 or not hit(kit):
                continue
            return f"cancelled by {who} at {time.strftime('%F %T', time.localtime(t))} (not an OOM kill): {why}"[:300]
    return None


def signals_external(j, now=None):
    """STOPPED-OUTSIDE-1630 (FABLE-FLOW-1800 item 5): the ot-run client of this job's dir was sent a SIGTERM/SIGHUP/SIGINT/SIGKILL by something else (systemd user manager, a lane's kill, a
    reboot) at or after this attempt started: signals.log has `signal N from <sender> -> ot-run pid P host H tag T WAITING|RUNNING dir <path>`.  That is an outside stop, never memory: the row is
    CANCELLED (no resubmit with --mem x1.5).  An earlyoom sender keeps its own path (EARLYOOM-RESUBMIT).  -> the log line or None"""
    path = str(j.get("path") or "").rstrip("/")
    if not path:
        return None
    try:
        lines = OT_RUN_SIGNALS.read_text(errors="replace").splitlines()
    except OSError:
        return None
    since = float(j.get("started", 0)) - 60
    now = now or time.time()
    pat = re.compile(r" signal (?:1|2|9|15) from .* -> ot-run pid \d+ .*\bdir " + re.escape(path) + r"(?::|\s|$)")
    for line in reversed(lines[-5000:]):
        if "earlyoom" in line.lower() or not pat.search(line):
            continue
        try:
            t = datetime.datetime.strptime(line.split(" ", 1)[0], "%Y-%m-%dT%H:%M:%S%z").timestamp()
        except ValueError:
            continue
        if since <= t <= now + 60:
            return line[:300]
    return None


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
UNIT_CACHE = {"t": 0.0, "set": None}
UNIT_TTL_S = 15.0


def active_unit_set(now=None):
    """WAVE-TICK-1119 (COORD 4): ONE `systemctl --user list-units` per UNIT_TTL_S names every active unit; unit_active used to start one systemctl per row
    (hundreds per tick).  None when the listing failed (callers fall back to the per-unit call)."""
    now = time.time() if now is None else now
    if UNIT_CACHE["set"] is not None and 0 <= now - UNIT_CACHE["t"] < UNIT_TTL_S:
        return UNIT_CACHE["set"]
    rc, out, _ = sh(["systemctl", "--user", "list-units", "--state=active,activating,reloading", "--no-legend", "--plain", "--no-pager"], timeout=60)
    if rc != 0:
        return None
    names = set()
    for ln in out.splitlines():
        f = ln.split()
        if f:
            names.add(f[0])
            names.add(re.sub(r"\.(service|scope)$", "", f[0]))
    UNIT_CACHE.update(t=now, set=names)
    return names


def unit_active(unit):
    """a unit in the cached active set is active (at most UNIT_TTL_S stale: a unit that just ended counts for one more tick); anything else is asked
    individually, so a unit started after the listing is never judged ended"""
    s = active_unit_set()
    if s is not None and unit in s:
        return True
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
@lru_cache(maxsize=4096)
def process_staging_roots(argv):
    """Parse each immutable live argv once across the tick's many ownership queries."""
    try:
        words = shlex.split(argv)
    except ValueError:
        return None  # malformed live client: retain data until it can be identified
    if not any(w.rsplit("/", 1)[-1] == "ot-run" for w in words):
        return ()
    roots = []
    for i, word in enumerate(words):
        candidate = None
        if word in ("--dir", "--stage") and i + 1 < len(words):
            candidate = words[i + 1]
        elif word.startswith(("--dir=", "--stage=")):
            candidate = word.split("=", 1)[1]
        if candidate and candidate.startswith("/srv/opentallas-scratch") and "/claude/" in candidate:
            roots.append(candidate.rstrip("/"))
    return tuple(roots)


def process_uses_kit(argv, path):
    """A parent staging directory owns its nested kits even when ot-run spills to another host."""
    path = path.rstrip("/")
    if path in argv and re.search(re.escape(path) + r"(?=[/\s]|$)", argv):
        return True
    roots = process_staging_roots(argv)
    return roots is None or any(path.startswith(root + "/") for root in roots)


PS_CACHE = {"t": 0.0, "out": ""}
PS_TTL_S = 20.0


def hub_ps_text(now=None):
    """WAVE-TICK-1119: one `ps` of the hub per PS_TTL_S, not one per job (hub_procs is asked for every job in poll / retry / admit: about 75 s
    of a 900 s tick on a hub at load 240).  A process that ended in the last 20 s counts as live one more tick; a failed ps is not cached."""
    now = time.time() if now is None else now
    if PS_CACHE["out"] and 0 <= now - PS_CACHE["t"] < PS_TTL_S:
        return PS_CACHE["out"]
    rc, out, _ = sh(["ps", "-eo", "pid=,etimes=,args="], timeout=60)
    if rc == 0 and out:
        PS_CACHE.update(t=now, out=out)
    return out


def hub_procs(path):
    """processes on the hub (ot-run clients, local docker run / run_kit.sh) whose command line names the kit dir
    -> [(pid, elapsed_s)]; ot-run clients always run here, also when the job itself spilled to another host"""
    out = hub_ps_text()
    me = os.getpid()
    res = []
    for line in out.splitlines():
        f = line.split(None, 2)
        if len(f) == 3 and f[0].isdigit() and int(f[0]) != me and "autopilot" not in f[2] \
                and not f[2].startswith(("ssh ", "python3 -I -")) and "/stage_odb_cap.py --watch" not in f[2] and process_uses_kit(f[2], path):
            res.append((int(f[0]), int(f[1])))
    return res


_REMOTE_ALIVE = {}
_REMOTE_ALIVE_FILE = Path.home() / ".local/state/ap_remote_alive.json"      # cross-tick cache (each tick is a new process)


def remote_job_alive(path, procs):
    """KIT-OPS-4 11-14 (COORD): a hub ot-run / ot-job client for the kit dir counts as busy only while the job is alive on the host
    it runs on: a docker container whose name holds the item, or any process naming the kit dir (checked over ssh, cached 5 min per
    host and kit).  A client with no ssh child runs local to the hub and stays busy.  Anything unknown (ssh fails, no host found)
    stays busy: the probe only releases a client whose remote host answers and shows nothing running."""
    item = os.path.basename(path.rstrip("/"))
    now = time.time()
    try:
        if not _REMOTE_ALIVE:
            try:
                _REMOTE_ALIVE.update({tuple(k.split("|", 1)): v for k, v in json.loads(_REMOTE_ALIVE_FILE.read_text()).items()
                                      if now - v[0] < 300})
            except (OSError, ValueError):
                pass
        rc, out, _ = sh(["ps", "-eo", "pid=,ppid=,args="], timeout=30)
        kids, args = {}, {}
        for line in out.splitlines():
            f = line.split(None, 2)
            if len(f) == 3 and f[0].isdigit() and f[1].isdigit():
                kids.setdefault(int(f[1]), []).append(int(f[0]))
                args[int(f[0])] = f[2]
        hosts, st = set(), [pid for pid, _ in procs]
        while st:
            x = st.pop()
            for k in kids.get(x, []):
                st.append(k)
                a = args.get(k, "")
                if a.startswith("ssh "):
                    w, i = a.split(), 1
                    while i < len(w) and w[i] == "-o":
                        i += 2
                    if i < len(w):
                        hosts.add(w[i])
        if not hosts:
            return True
        for h in sorted(hosts):
            key = (h, path)
            hit = _REMOTE_ALIVE.get(key)
            if hit and now - hit[0] < 300:
                alive = hit[1]
            else:
                cmd = (f"docker ps --format '{{{{.Names}}}}' 2>/dev/null | grep -c -- {shlex.quote(item)}; "
                       f"ps -eo args | grep -F -- {shlex.quote(path.rstrip('/'))} | grep -vc grep")
                rc, o, _ = sh(["ssh", "-n", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", h, cmd], timeout=40)
                nums = [int(t) for t in o.split() if t.isdigit()]
                alive = True if (rc != 0 and not nums) else any(n > 0 for n in nums)
                _REMOTE_ALIVE[key] = (now, alive)
                try:
                    _REMOTE_ALIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    _REMOTE_ALIVE_FILE.write_text(json.dumps({"|".join(k): v for k, v in _REMOTE_ALIVE.items() if now - v[0] < 300}))
                except OSError:
                    pass
            if alive:
                return True
        return False
    except Exception:
        return True


def proc_args(pid):
    """the command line of a hub process, '' when it is gone"""
    try:
        return Path(f"/proc/{int(pid)}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    except (OSError, ValueError):
        return ""


def place_client(pid, path):
    """KW-FIX-30: the hub process pid runs this kit's runner with goal place (the ot-run client of the kit's PLACE,
    which only waits for the pre-route proof once the place receipt is out)"""
    return bool(re.search(r"run_kit[^\s/]*\.sh\s+" + re.escape(path.rstrip("/")) + r"/?\s+place(\s|$)", proc_args(pid)))


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



def physical_receipt(j, p):
    """Fresh matching CTS/GRT result only; route/signoff always use the normal proof gate."""
    if j.get("goal") not in ("cts", "grt") or p.get("exists") is False or p.get("config") is False:
        return None
    proof = p.get("async_proof") or {}
    starts = [r for r in p.get("physical_starts") or [] if r.get("goal") == j["goal"]
              and r.get("physical_id") == p.get("physical_identity")]
    latest = max(starts, key=lambda r: r.get("started", 0), default={})
    for r in p.get("physical_completions") or []:
        if (r.get("goal") != j["goal"] or type(r.get("rc")) is not int
                or not isinstance(r.get("started"), (int, float))
                or r["started"] < float(j.get("started") or 0) - 120
                or r.get("ended", 0) < r["started"] or not r.get("run_id")
                or r["run_id"] != latest.get("run_id") or r.get("physical_id") != p.get("physical_identity")
                or (r["rc"] == 0 and not r.get("checkpoint_current"))
                or not r.get("proof_id") or r["proof_id"] != proof.get("identity")
                or r.get("proof_owner") != proof.get("owner")):
            continue
        # A live proof must remain attached to its original admitted Docker scope.
        if not proof.get("done") and proof.get("owner") not in (p.get("active_containers") or []):
            continue
        return r
    return None


def poll_physical_completion(st, j):
    if j.get("goal") not in ("cts", "grt"):
        return False
    host = j.get("probe") or j.get("ran_on") or j["host"]
    p = rpy(host, PROBE_KIT,
            {"kit": j["path"], "runner": j.get("runner", "")}, timeout=120)
    r = physical_receipt(j, p)
    if not r:
        return False
    c = probe_job(dict(j, host=host))
    if c is None or c.get("signoff") or c.get("route_odb"):
        return False  # a physical-only receipt never releases an active route/signoff scope
    # A fresh successful incremental make can honestly reuse an older unchanged checkpoint.
    # The receipt binds that exact artifact; mtime alone is not used as the completion signal.
    c = dict(c)
    if r["rc"] == 0 and r.get("checkpoint_current"):
        c[j["goal"] + "_odb"] = os.path.join(j["path"], r["checkpoint"]["path"])
    proof = p.get("async_proof") or {}
    j["physical_receipt"] = r
    j["proof_wait"] = dict(host=host, owner=r["proof_owner"],
                           identity=r["proof_id"], pid=r.get("proof_pid"), scope=r.get("proof_scope"),
                           pending=not proof.get("done"), rc=proof.get("rc"))
    finish(st, j, c, {"exit": r["rc"], "physical_only": True, "receipt": r.get("path")})
    return True


def poll_pending_proofs(st):
    """Keep early diagnostic completions linked to their still-admitted proof owner."""
    for j in st["jobs"].values():
        w = j.get("proof_wait") or {}
        if not w.get("pending"):
            continue
        p = rpy(w["host"], PROBE_KIT, {"kit": j["path"], "runner": j.get("runner", "")}, timeout=120)
        proof = p.get("async_proof") or {}
        if proof.get("identity") != w.get("identity"):
            continue
        w.update(pending=not proof.get("done"), rc=proof.get("rc"))
        if proof.get("done"):
            log(f"PROOF-COLLECT {j['id']} {w['owner']} exit {w.get('rc')}; physical result retained, EQ still gates signoff")

def poll_adopted(st, j):
    if poll_physical_completion(st, j):
        return
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
    client = {"adopted": True}
    receipt = p.get("runner_exit") or {}
    start, end = iso_epoch(receipt.get("start", "")), iso_epoch(receipt.get("end", ""))
    if (start is not None and end is not None and end >= start
            and start >= float(j.get("started") or 0) - 120 and type(receipt.get("rc")) is int):
        client.update(exit=receipt["rc"], receipt=receipt.get("path"))
    finish(st, j, c, client)


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
        # no literal /srv path in this script: ot-run SPILL refuses a command naming /srv outside its --stage paths
        if not str(dest).startswith("/"+"srv/opentallas-scratch") or "/claude/" not in str(dest):
            raise RuntimeError("admission bundle must be under an owned scratch lane")
        dest.parent.mkdir(parents=True,exist_ok=True)
        # Retry only a failed pre-payload transport, each into a fresh temporary tree.
        for attempt in range(1,4):
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
                    if attempt == 3:
                        raise RuntimeError("admission tool transfer failed after 3 attempts; physical runner not started")
                    print("ADMISSION_TOOLS transport retry "+str(attempt)+"/3; physical runner not started",flush=True)
                    continue
                manifest=json.loads((target/"BUNDLE.json").read_text())
                if manifest.get("sha256") != meta["sha256"]:
                    raise RuntimeError("admission tool version differs; physical runner not started")
                if not dest.exists():target.rename(dest)
            break
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
    # signoff.py also depends on this shared physical helper. Standalone admission
    # bundles have no repository sibling tree, so place it beside signoff.py.
    if (tools / "signoff.py").is_file() and Path("clock_family.tcl") not in payload:
        clock_family = tools.parents[1] / "physical/common_flow/clock_family.tcl"
        if not clock_family.is_file():
            raise ValueError("admission tools incomplete: missing physical/common_flow/clock_family.tcl")
        payload[Path("clock_family.tcl")] = clock_family.read_bytes()
    # FABLE-FLOW-1000 A: the per-stage flow refresh runs INSIDE the sealed stage job, where rt/current is not visible: the refresher,
    # the flow blob index of this scheduler rt and the current physical/common_flow scripts travel in the bundle (die_plan/__flow__).
    kfr = Path(__file__).with_name("kit_flow_refresh.py")
    blobs = tools.parent / ".flow_blobs.json"
    if kfr.is_file() and blobs.is_file():
        payload[Path("__flow__/kit_flow_refresh.py")] = kfr.read_bytes()
        payload[Path("__flow__/flow_blobs.json")] = blobs.read_bytes()
        kr = Path(__file__).with_name("kit_resume.py")           # FLOW-FIX-2045: the ALWAYS list creates it in a kit that lacks it (in-place restart resume)
        if kr.is_file():
            payload[Path("__flow__/kit_resume.py")] = kr.read_bytes()
        for cf in sorted((tools.parents[1] / "physical/common_flow").glob("*")):
            if cf.is_file() and cf.suffix in (".tcl", ".py", ".sh"):
                payload[Path("__flow__/common_flow") / cf.name] = cf.read_bytes()
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


def late_eco_on():
    """KW-ECO-1 late-stage ECO loop in signoff_chain.py: default ON; COORD opt-out = "late_eco": false in
    autopilot/kit_wave.json (one coord commit); per kit: a KIT/late_eco.off marker"""
    try:
        return json.loads((AP_DIR / "kit_wave.json").read_text()).get("late_eco", True) is not False
    except (OSError, ValueError, AttributeError):
        return True


NEAR_COUNT_FILE = "lanes/NEAR-COUNT.tsv"
CELL_WAIVER_FILE = "lanes/CELL-WAIVER.tsv"


def parse_near_count(text):
    """lanes/NEAR-COUNT.tsv (SIGNOFF-SPRINT-19; COORD 11-01 KIT-WAVE-16 (6)) -> {(die, name)} of cores/types one
    step from the count: their builds get ot-run --priority die --crit on admission.  A header row names the columns
    (die + item | type | core | module); without a header the first two columns are die, item.  '#' lines and blank
    lines are skipped; die '*' matches every die."""
    out = set()
    cols = None
    for ln in (text or "").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = [x.strip() for x in ln.split("\t")]
        low = [x.lower() for x in f]
        if cols is None and "die" in low and any(k in low for k in ("item", "type", "core", "module")):
            name = next(k for k in ("item", "type", "core", "module") if k in low)
            cols = (low.index("die"), low.index(name))
            continue
        di, ni = cols or (0, 1)
        if len(f) > max(di, ni) and f[di] and f[ni]:
            out.add((f[di], f[ni]))
    return out


def near_count_match(near, die, *names):
    """True when (die or '*', name) is listed for any of the names (item, parent type, core module)"""
    return any((d, n) in near for n in names if n for d in (die, "*"))


def near_count_args(near, die, *names):
    return ["--priority", "die", "--crit"] if near and near_count_match(near, die, *names) else []


def kit_lost(j):
    """'' = the job's kit is present on the hub (a resubmit can run); else why not: ot-run stages the kit from the hub, so a
    missing runner file / kit dir can only die with rc 127 (epyc4 kits whose gen dir is gone)."""
    runner, kit = j.get("runner") or "", j.get("path") or ""
    if runner and not os.path.isfile(runner):
        return f"runner {runner} missing on the hub"
    if kit and not os.path.isdir(kit):
        return f"kit dir {kit} missing on the hub"
    return ""


def wave_superseded(j):
    """why the kit-wave no longer wants this job ('' = it does, or no wave row): a resubmit would only restart it on the
    same kit (HUNG-1103: cancelled rows came back as a second container 5 min to 3 h after the cancel)"""
    v = WJ.judge(WJ.load_rows(str(AP_DIR)), WJ.wave_id([j.get("path")]), j.get("started"))
    return v[1] if v and v[0] == "STOP" else ""


def stop_cancelled(j, why):
    """FAILFAST-1 11-12 (orphan leak: containers ran 24-70 h after their rows went CANCELLED): a job that goes CANCELLED stops its
    containers by exact name on every host and records which (j['stopped_containers'] + the log).  Never raises."""
    if not DRY and j.get("path") and os.environ.get("OT_STOP_INLINE") != "1":
        # COORD 11-20: fire and forget; the detached stop appends its result to remote_stops.log tagged with the job id, check_pending_stops() reads it next tick
        if WJ.stop_bg_spawn(HUB_NAME, [j.get("path")], AP_DIR / "remote_stops.log", j["id"]):
            j["stopped_containers"] = {"at": now_s(), "names": "", "why": why[:120], "errors": "", "queued": time.time(), "retry": 0}
            log(f"CANCEL-STOP {j['id']} {j['die']}/{j['type']} ({why[:80]}): fleet stop started detached (result next tick)")
            return ""
    try:
        names, errs = WJ.stop_row_containers(sh, HUB_NAME, [j.get("path")], dry=DRY)
    except Exception as e:                           # noqa: a cancel is recorded even when the stop could not run
        names, errs = "", "; stop failed: %r" % (e,)
    j["stopped_containers"] = {"at": now_s(), "names": names, "why": why[:120], "errors": errs[:300]}
    log(f"CANCEL-STOP {j['id']} {j['die']}/{j['type']} ({why[:80]}): containers [{names or 'none running'}]{errs}")
    return names


def check_pending_stops(st):
    """the result of last tick's detached cancel-stops: a stop that finished with a host 'not checked' is started ONCE more; the outcome is logged (CANCEL-STOP-RESULT).  -> n re-started"""
    try:
        txt = (AP_DIR / "remote_stops.log").read_text(errors="replace")
    except OSError:
        txt = ""
    n = 0
    for j in (st.get("jobs") or {}).values():
        sc = j.get("stopped_containers") or {}
        if not sc.get("queued") or sc.get("checked"):
            continue
        found, ok, line = WJ.stop_result_for(txt, j["id"])
        if not found:
            if time.time() - float(sc["queued"]) > 1800:
                sc["checked"] = "no result after 30 min"
            continue
        if ok or int(sc.get("retry") or 0) >= 1:
            sc["checked"] = line[:300]
            log(f"CANCEL-STOP-RESULT {j['id']} {j.get('die')}/{j.get('type')}: {line[20:260]}")
        else:
            sc["retry"] = int(sc.get("retry") or 0) + 1
            sc["queued"] = time.time()
            WJ.stop_bg_spawn(HUB_NAME, [j.get("path")], AP_DIR / "remote_stops.log", j["id"])
            n += 1
    return n


def stop_survivors(j):
    """one flow container per kit (WATCHDOG-1 11-03): a resubmit resumes the run dir, and the previous attempt's container may
    still run, on any host, after its ot-run client was lost (ot-run leaves a started command running)"""
    res = WJ.stop_on_fleet(sh, HUB_NAME, [j.get("path")])
    names = WJ.stopped_names(res)
    if names:
        log(f"STOP-SURVIVOR {j['id']} {j['die']}/{j['type']}: stopped {' '.join(names)[:400]} before attempt {j.get('attempts', 0) + 1}")
    for h, v in res.items():
        if v.get("error"):
            log(f"STOP-SURVIVOR {j['id']}: {h} not checked: {v['error']} (watchdog duplicate check is the net)")


# KW-FIX-24 11-06 (COORD 17:5x ruling): no kit resumes on a disk-low host.  A spilled run copies everything it wrote
# back onto the kit's home host (ot-run spill copy-back); epyc6 scratch2 hit 0 bytes from those copy-backs.  A kit whose
# home host is listed in kit_wave.json "no_resume_hosts" ({host: free GB at which the entry is dropped by hand}) is
# moved, inside its own launched unit (the tick never waits on a copy), to the same path on the hub: rsync pull, file
# list + size check, source removed, marker jobs/<id>/evac.json; then ot-run runs with the hub as home (ot-run homes a
# --dir on the host that holds it).  Any failure undoes the hub copy and the job runs as before (fail-open, logged).
# The next tick (apply_evac) re-homes the job record (host/kit) from the marker.
EVAC_KEEP_GB = 100
EVAC_SH = r"""set -u
h=$1; mark=$2; keep=$3; shift 3; roots=()
while [ $# -gt 0 ] && [ "$1" != "--" ]; do roots+=("$1"); shift; done; shift
SSH=${EVAC_SSH:-ssh}; P=${EVAC_DST_PREFIX:-}
say() { printf '%s\n' "$1" > "$mark.tmp" && mv "$mark.tmp" "$mark"; echo "AP-EVAC: $1" >&2; }
made=()
undo() { for d in "${made[@]}"; do rm -rf -- "$d"; done; }
lst() { cd / && if [ -d "$1" ]; then (cd "$1" && find . -type f -printf '%P %s\n' | LC_ALL=C sort | md5sum | cut -c1-32); else stat -c %s "$1" 2>/dev/null; fi; }
run_cmd=("$@")
case "${roots[0]}" in ${EVAC_LANE:-/srv/opentallas-scratch}*/claude/*/*/*) ;; *) undo; say '{"ok": false, "why": "kit path outside a scratch lane"}'; exec "${run_cmd[@]}";; esac
need=$($SSH -n -o BatchMode=yes -o ControlPath=none "$h" "du -sb ${roots[*]} 2>/dev/null | awk '{s+=\$1} END {print s+0}'") || { undo; say '{"ok": false, "why": "size probe failed"}'; exec "${run_cmd[@]}"; }
for r in "${roots[@]}"; do
  d="$P$r"; a=$(dirname "$d"); while [ ! -d "$a" ]; do a=$(dirname "$a"); done
  free=$(df -B1 --output=avail "$a" | tail -1 | tr -dc 0-9)
  if [ $((free - need)) -lt $((keep * 1073741824)) ]; then undo; say "{\"ok\": false, \"why\": \"hub disk: $((free / 1073741824)) GB free < need + keep\"}"; exec "${run_cmd[@]}"; fi
  [ -e "$d" ] && { undo; say '{"ok": false, "why": "target exists on the hub"}'; exec "${run_cmd[@]}"; }
done
for r in "${roots[@]}"; do
  d="$P$r"; mkdir -p "$(dirname "$d")"; made+=("$d")
  if $SSH -n -o BatchMode=yes -o ControlPath=none "$h" "test -d '$r'"; then
    rsync -aH -e "$SSH -o BatchMode=yes -o ControlPath=none" "$h:$r/" "$d/" || { undo; say '{"ok": false, "why": "rsync failed"}'; exec "${run_cmd[@]}"; }
  else
    rsync -aH -e "$SSH -o BatchMode=yes -o ControlPath=none" "$h:$r" "$d" || { undo; say '{"ok": false, "why": "rsync failed"}'; exec "${run_cmd[@]}"; }
  fi
  a=$($SSH -n -o BatchMode=yes -o ControlPath=none "$h" "$(declare -f lst); lst '$r'"); b=$(lst "$d")
  [ -n "$a" ] && [ "$a" = "$b" ] || { undo; say "{\"ok\": false, \"why\": \"verify mismatch on $r\"}"; exec "${run_cmd[@]}"; }
done
$SSH -n -o BatchMode=yes -o ControlPath=none "$h" "rm -rf -- ${roots[*]}" || echo "AP-EVAC: source remove failed on $h (copy kept on the hub)" >&2
say "{\"ok\": true, \"from\": \"$h\", \"bytes\": $need}"
exec "${run_cmd[@]}"
"""


def evac_hosts():
    try:
        v = json.loads((AP_DIR / "kit_wave.json").read_text()).get("no_resume_hosts") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return dict(v) if isinstance(v, dict) else {str(h): 80 for h in v}


def evac_wrap(j, argv):
    """argv unchanged, or wrapped in the hub-side move of the kit off a no_resume host (records j['evac'])"""
    h = j.get("host")
    if not h or ssh_host(h) == "localhost" or h not in evac_hosts() or not j.get("path"):
        return argv
    roots = [j["path"]]
    r = j.get("runner") or ""
    if r and r != j["path"] and not r.startswith(j["path"] + "/"):
        roots.append(r)
    mark = AP_DIR / "jobs" / j["id"] / ("evac-a%d.json" % (j.get("attempts", 0) + 1))
    j["evac"] = {"from": h, "to": HUB_NAME, "roots": roots, "mark": str(mark), "t": time.time()}
    return ["bash", "-c", EVAC_SH, "ap-evac", h, str(mark), str(EVAC_KEEP_GB)] + roots + ["--"] + argv


def apply_evac(st):
    """re-home jobs whose launched unit moved the kit to the hub (marker ok) -> number re-homed"""
    n = 0
    for j in st["jobs"].values():
        e = j.get("evac")
        if not e or e.get("applied"):
            continue
        try:
            m = json.loads(Path(e["mark"]).read_text())
        except (OSError, ValueError):
            if time.time() - e.get("t", 0) > 6 * 3600:
                e["applied"] = "no marker"
            continue
        if m.get("ok"):
            j["host_before_evac"] = j.get("host")
            j.update(host=HUB_NAME, kit=f"{HUB_NAME}:{j['path']}")
            j.pop("probe", None)
            e["applied"] = "moved"
            n += 1
            log(f"EVAC {j['id']} {j.get('die')}/{j.get('type')}: kit moved {e['from']} -> {HUB_NAME} "
                f"({int(m.get('bytes', 0)) / 1e9:.1f} GB, source removed); no copy-back to {e['from']}")
        else:
            e["applied"] = "failed: " + str(m.get("why"))[:200]
            log(f"EVAC-FAIL {j['id']} {j.get('die')}/{j.get('type')}: {m.get('why')}; ran with home {e['from']} as before")
    return n


def stage_disk_args():
    """FABLE-FLOW-1000 (1) / WAVE-DISK-CAP: a stage SUBMIT declares its scratch need = max(measured p90 kit peak (kit_peak_gb.json, written by the wave), 3 GB) as ot-run --disk, so ot-run's disk admission
    counts it (30 jobs died ENOSPC in one hour).  No fresh measurement: no flag (ot-run's own default).  AP_STAGE_DISK=0 turns it off."""
    if os.environ.get("AP_STAGE_DISK") == "0":
        return []
    try:
        d = json.loads((AP_DIR / "kit_peak_gb.json").read_text())
        if time.time() - float(d["at"]) > 72 * 3600 or int(d["n"]) < 5:
            return []
        return ["--disk", str(max(3, int(-(-float(d["p90_gb"]) // 1))))]
    except (OSError, ValueError, KeyError, TypeError):
        return []


# COORD 11-19 (INFRA / OOM kill in GRT re-ran global placement): the kit lives on the host that was killed, which is full; the resubmit waited there or SPILLed a 40 GB lane root.  A resubmit after an
# infra kill now moves the checkpoint instead: when the killed host does not admit the job, the kit (without run/objects and the intermediate stage odbs) plus the LAST stage odb and the run
# dir's small files are rsynced (delta, hosts reach each other) to the die host with the most free admit memory, and the job is pinned there.  The same host when it still admits.
CKPT_ODB = re.compile(r"^(\d)_([a-z]+)\.odb$")                  # a final stage odb: 3_place.odb, 4_cts.odb, 5_1_grt (5_1_grt.odb is matched below)
CKPT_ODB_SUB = re.compile(r"^(\d)(?:_\d)?_([a-z_]+)\.odb$")


def pick_checkpoint_odbs(names):
    """from the file names of run/results/asap7/*/base: the odb of the LAST completed stage (highest stage number, final file of that stage, not a sub-step); [] when none"""
    best = None
    for n in names:
        m = CKPT_ODB.match(n)
        if not m:
            m2 = re.match(r"^(\d)_(\d)_([a-z]+)\.odb$", n)         # 5_1_grt.odb
            if m2 and m2.group(3) in ("grt", "route", "drt"):
                m = m2
            else:
                continue
        key = (int(m.group(1)), n)
        if best is None or key > best:
            best = key
    return [best[1]] if best else []


def resume_target(status_text, mem, ran_on, hub, die_hosts=None):
    """-> (host, why): the die host to resume on.  ran_on itself when it admits `mem` GB, else the host with the most admit GB that does (never the hub); '' when none admits"""
    adm = {}
    for h, v in (KW.parse_otrun_status(status_text) or {}).items():
        h = hub if h == "localhost" else h
        if h == hub or (die_hosts and h not in die_hosts):
            continue
        adm[h] = int(v.get("admit", 0) or 0)
    if ran_on in adm and adm[ran_on] >= mem:
        return ran_on, "the killed host still admits"
    ok = {h: a for h, a in adm.items() if a >= mem}
    if not ok:
        return "", "no die host admits %d GB now" % mem
    h = max(ok, key=lambda x: (ok[x], x))
    return h, "most free admit memory (%d GB)" % ok[h]


def delta_copy_argv(kit, src, dst, odbs):
    """the ssh+rsync command (run on the SOURCE host, hosts reach each other) that delta-copies the kit to the same path on dst: everything but run/objects and the odb files, then the last stage odb(s)"""
    q = shlex.quote
    e = "ssh -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=15"
    k = kit.rstrip("/")
    keep = "".join(f" --include={q('run/results/asap7/*/base/' + o)}" for o in odbs)
    cmd = (f"rsync -a --partial --inplace -e {q(e)} --exclude={q('run/objects')}{keep} --exclude={q('*.odb')} --exclude={q('*.odb.tmp')} {q(k + '/')} {dst}:{q(k + '/')}")
    return ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", src, cmd]


def resume_move(j, mem):
    """COORD 11-19: -> host to pin the resubmit to ('' = leave placement to ot-run).  Copies the checkpoint when it moves; any failure -> '' (the old behaviour)"""
    ro = str(j.get("ran_on") or "")
    if not j.get("infra_retry") or not re.fullmatch(r"(?:epyc|intel)\d+", ro) or ro == HUB_NAME or j.get("resume_moves", 0) >= 2:
        return ""
    rc, out, _ = sh([OT_RUN, "--status"], timeout=120)
    if rc:
        return ""
    host, why = resume_target(out, int(mem), ro, HUB_NAME)
    if not host:
        log(f"RESUME-MOVE {j['id']} {j.get('die')}/{j.get('type')}: {why}; ot-run places it")
        return ""
    if host == ro:
        return host
    kit = j["path"]
    rc, ls, _ = sh(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", ro, f"ls {shlex.quote(kit)}/run/results/asap7/*/base/ 2>/dev/null"], timeout=60)
    odbs = pick_checkpoint_odbs((ls or "").split())
    if DRY:
        log(f"would RESUME-MOVE {j['id']} {kit} {ro} -> {host} odb {odbs}")
        return ""
    rc, so, se = sh(delta_copy_argv(kit, ro, host, odbs), timeout=7200)
    if rc:
        log(f"RESUME-MOVE {j['id']} {j.get('die')}/{j.get('type')}: copy {ro} -> {host} failed rc {rc}: {(se or so)[-200:]}; ot-run places it")
        return ""
    j["resume_moves"] = int(j.get("resume_moves") or 0) + 1
    log(f"RESUME-MOVE {j['id']} {j.get('die')}/{j.get('type')}: checkpoint {','.join(odbs) or 'kit only'} copied {ro} -> {host} ({why}); resubmit pinned there")
    return host


def submit(st, j, attempt_note=""):
    n = j.get("attempts", 0) + 1
    unit = f"ap-{j['id']}-a{n}"
    logf = AP_DIR / "jobs" / j["id"] / f"a{n}.log"
    kit, runner, mem, thr = j["path"], j["runner"], j["mem_gb"], j["threads"]
    argv = [OT_RUN, "--mem", str(mem), "--threads", str(thr), "--dir", kit, "--stage", kit] + stage_disk_args()
    pin = resume_move(j, mem)
    if pin:
        argv += ["--hosts", pin]
    # NEAR-COUNT (COORD 11-01): a core/type listed in lanes/NEAR-COUNT.tsv is admitted as a die-priority crit job
    argv += near_count_args(parse_near_count(read_coord(NEAR_COUNT_FILE)), j.get("die"), j.get("type"),
                            j.get("module"), j.get("item"))
    if not runner.startswith(kit + "/"):
        argv += ["--stage", runner]
    if j["goal"] not in ("cts", "grt"):
        import base64
        bundle = stage_admission_tools()
        bundle["source_host"] = os.environ.get("AP_ADMISSION_HUB", "hub")
        encoded = base64.b64encode(json.dumps(bundle).encode()).decode()
        # --stage is spill-only. Fetch the immutable tool bundle on the
        # actual selected worker before executing any frozen kit runner.
        argv += ["--", "python3", "-c", ADMISSION_BOOTSTRAP, encoded] + ([] if late_eco_on() else ["--no-late-eco"]) + [
                 runner, kit, j["goal"], str(mem), str(thr)]
        # chain v2 (AUTOPILOT-SIGNOFF-2): main lec.py + all_shown + mtime proof, FAILED notice + data delete.
        # Jobs launched by an earlier chain keep the earlier rules (no retroactive demotion or deletion).
        j.update(chain_required=True, admission_tools_sha256=bundle["sha256"], chain_version=CHAIN_VERSION)
    else:
        argv += ["--", "bash", runner, kit, j["goal"], str(mem), str(thr)]
    argv = evac_wrap(j, argv)
    if DRY:
        log(f"would SUBMIT {j['id']} {j['die']}/{j['type']} {attempt_note}: {' '.join(argv)}")
        return
    if n > 1:
        stop_survivors(j)
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


TS_RE = re.compile(r"(20\d\d-\d\d-\d\d)[ T]+(\d\d:\d\d)")


def plan_of_record():
    """-> {die: {"ids": set, "frozen": 'YYYY-MM-DD HH:MM' or ''}}: each die's current plan of record = the kit-wave plan
    (autopilot/kit_wave.json dies[*]: 'event', the plan file stem, optional 'por_ids' list and 'por_frozen' date)"""
    try:
        cfg = json.loads((AP_DIR / "kit_wave.json").read_text())
    except Exception:
        return {}
    out = {}
    for key, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict):
            continue
        ids = {str(x) for x in [d.get("event"), Path(str(d.get("plan") or "")).stem] + list(d.get("por_ids") or [])
               if x and len(str(x)) >= 4 and str(x) not in ("die_plan", "source_plan", "plan", "plan_of_record")}
        if ids:
            por = out.setdefault(canonical_die(d.get("die") or key), {"ids": set(), "frozen": ""})
            por["ids"] |= ids
            por["frozen"] = max(por["frozen"], str(d.get("por_frozen") or ""))
    return out


PLAN_DELTA_IGNORED = []
CLOSURE_IGNORED_LOGGED = []


def parse_plan_delta(text, por=None):
    """-> {(die, type): delta id} of PENDING deltas: lines 'PENDING-DELTA <id> <die> type[,type ...]', closed by
    'CLOSED-DELTA <id>' / 'MERGED-DELTA <id>' / 'DROPPED-DELTA <id>' / 'RETIRED-DELTA <id>' (later lines win).
    Class fix DELTA-STALE (COORD 2026-11-03 17:5x): with por = plan_of_record() (or 'PLAN-OF-RECORD <die> <id>
    [YYYY-MM-DD HH:MM]' lines here), a PENDING delta of a die with a plan of record holds only if its line names one
    of that plan's ids and it is dated (timestamp on the line, else the latest one above it) after the plan's freeze;
    otherwise it is ignored and listed in PLAN_DELTA_IGNORED.  por=None keeps the legacy rule (every PENDING holds)."""
    pend = {}
    por = {k: {"ids": set(v["ids"]), "frozen": v.get("frozen", "")} for k, v in (por or {}).items()} if por is not None \
        else None
    last_ts = ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        ts = [f"{a} {b}" for a, b in TS_RE.findall(line)]
        m = re.match(r"^PLAN-OF-RECORD\s+(\S+)\s+(\S+)(.*)$", line)
        if m and por is not None:
            ent = por.setdefault(canonical_die(m.group(1)), {"ids": set(), "frozen": ""})
            ent["ids"].add(m.group(2))
            if ts:
                ent["frozen"] = max(ent["frozen"], ts[0])
            continue
        m = re.match(r"^PENDING-DELTA\s+(\S+)\s+(\S+)\s+(\S+)", line)
        if m:
            pend[m.group(1)] = (canonical_die(m.group(2)), {t for t in m.group(3).split(",") if t},
                                max(ts) if ts else last_ts, line)
        else:
            m = re.match(r"^(?:CLOSED|MERGED|DROPPED|RETIRED)-DELTA\s+(\S+)", line)
            if m:
                pend.pop(m.group(1), None)
        if ts:
            last_ts = max(ts)
    out = {}
    ignored = []
    for did, (die, types, when, line) in pend.items():
        ent = (por or {}).get(die)
        if ent and ent["ids"]:
            named = any(i in line for i in ent["ids"])
            if not named or (ent["frozen"] and not (when and when > ent["frozen"])):
                ignored.append((did, die, "names no current plan of record (" + ",".join(sorted(ent["ids"]))[:80] + ")"
                                if not named else f"dated {when or 'undated'} <= plan freeze {ent['frozen']}"))
                continue
        for t in types:
            out[(die, t)] = did
    PLAN_DELTA_IGNORED[:] = ignored
    return out


def load_closure():
    CLOSURE.clear()
    CLOSURE["gates"], CLOSURE["parts"] = parse_path_freeze(read_coord("lanes/PATH-FREEZE.md"))
    CLOSURE["delta"] = parse_plan_delta(read_coord("lanes/PLAN-DELTA.md"), plan_of_record())
    ign = sorted(PLAN_DELTA_IGNORED)
    if ign and ign != CLOSURE_IGNORED_LOGGED[:]:
        log("PLAN-DELTA stale ignored (DELTA-STALE: not on the die's plan of record / dated before its freeze): " +
            "; ".join(f"{d} {die}: {why}" for d, die, why in ign)[:3000])
    CLOSURE_IGNORED_LOGGED[:] = ign


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
    passes regardless of its path (rule 1 amendment: e.g. s81_head rows on path S81 once 'FROZEN S81-HEAD' is recorded).
    R-MINIMAL (default): the path die gate is advisory -- never a route hold, never a TRIAL-SIGNED demotion."""
    if SP.is_minimal() and canonical_die(r.get("die") or "") != "hbm":     # HBM is PARKED: its holds stay
        return ""
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


def flow_changes(tag, full, watch, exclude, own):
    """Memoize identical flow comparisons within this tick, keyed by resolved commits."""
    rc, out, _ = sh(["git", "-C", str(REPO), "rev-parse", "-q", "--verify", tag + "^{commit}"], timeout=60)
    if rc or not out.strip():
        return rc or 1, []
    tag_sha = out.strip().split()[0]
    key = (tag_sha, full, tuple(watch), tuple(exclude), None if own is None else tuple(own))
    cache = CLOSURE.setdefault("flow_changes", {})
    if key not in cache:
        rc, out, _ = sh(["git", "-C", str(REPO), "diff", "--no-renames", "--name-only", tag_sha, full], timeout=120)
        if rc:
            return rc, []                         # transport/Git failures remain retryable
        changed = tuple(p for p in out.splitlines() if any(fnmatch.fnmatch(p, w) for w in watch)
                        and not any(fnmatch.fnmatch(p, x) for x in exclude)
                        and not (own is not None and p.startswith(PLAN_ROOT) and p[len(PLAN_ROOT):].split("/", 1)[0] not in own))
        cache[key] = changed
    return 0, list(cache[key])


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
        rc, changed = flow_changes(t, full, watch, exclude, own)
        if rc:
            continue
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


def eco_provenance(j):
    """KW-ECO-1: a sign-off reached through the late-stage ECO loop names it (kind eco, base routed DB, iterations with
    their commands, flow sha); sign-off + routed LEC are the usual ones on the ECO'd routed DB.  {} otherwise."""
    eco = (j.get("chain") or {}).get("eco") or {}
    if eco.get("verdict") != "PASS":
        return {}
    return dict(kind="eco", eco=dict(tool="tools/die_plan/eco_loop.py", base_routed_db=eco.get("base_routed_db"),
                                     base_signoff=eco.get("base_signoff"), base_metrics=eco.get("base_metrics"),
                                     routed_db=(eco.get("best") or {}).get("base"), record=eco.get("record"),
                                     iterations=eco.get("iterations"), flow=eco.get("flow"), wall_s=eco.get("wall_s")))


def write_provenance(host, dest, j):
    prov = {k: j.get(k) for k in ("id", "die", "type", "src", "src_commit", "flow_tag", "lane")}
    if j.get("stage_resume"):                           # KW-RESUME-1: ORFS steps reused from the source attempt
        prov["stage_resume"] = j["stage_resume"]
    prov.update(schema="opentallas.provenance.v1", verdict="SIGNED" if j.get("flow_tag") and j.get("src_commit")
                else "SIGNED-UNVERSIONED", why=j.get("prov_error", ""), written=now_s())
    prov.update(eco_provenance(j))
    if j.get("resign_carry"):                           # KW-FIX-4 11-03: counted through the RE-SIGN of its routed DB
        prov.update(kind="resign-carry", resign_carry=j["resign_carry"],
                    why=f"build flow untagged; same routed DB re-signed at {j['resign_carry']['flow_tag']} "
                        f"({j['resign_carry']['host']}:{j['resign_carry']['record']})")
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


PROBE_ROUTED_SHA = r'''
import hashlib, json, os, sys
a = json.loads(sys.argv[1]); out = {}
try:
    x = json.load(open(a["prov"])) if a.get("prov") else {}
    if a.get("prov") and x.get("kind") != "resign":
        raise ValueError("%s is not a kind:resign record" % a["prov"])
    out["sha"] = x.get("routed_db_sha256") or None
    if not out["sha"]:
        h = hashlib.sha256()
        with open(a["db"], "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        out["sha"] = h.hexdigest()
except Exception as e:
    out["error"] = str(e)[:300]
print("AP_JSON " + json.dumps(out))
'''
RESIGN_PROBES_PER_TICK = 6                              # routed-DB hash probes per tick (each reads one routed DB once)


def _asap7_design(db):
    """.../results/asap7/<design>/base/6_final.odb -> <design> ('' when the path has no such segment)"""
    parts = str(db or "").split("/")
    return parts[parts.index("asap7") + 1] if "asap7" in parts[:-1] else ""


def resign_carry(j, cache=None, probe=None, budget=None):
    """KW-FIX-4/HBMRS 11-03 (DIE-HBM-61, COORD 17:1x): a SIGNED-UNVERSIONED job whose SAME routed DB (sha256 equal: the
    path itself or a byte copy) already has a valid RE-SIGN record (kind:resign PROVENANCE on a released flow tag
    covering its die; release_tree_plan checked tag -> src_commit, post-route LEC EQUIVALENT and the DB) is carried by
    that tag: the RE-SIGN is the 12.20 way to count a sign-off whose build flow no tag carries, and this run's sign-off
    is the same routed DB.  -> {flow_tag, tag_commit, record, host, routed_db, routed_db_sha256} or None.  Never
    guessed: no cache / no matching record / any hash unknown -> None (the job stays SIGNED-UNVERSIONED)."""
    db = (j.get("signoff") or {}).get("odb")
    jhosts = [h for h in dict.fromkeys((j.get("ran_on"), j.get("host"))) if h]   # the DB lives where the run ran
    design = _asap7_design(db)
    if not db or not jhosts or not design:
        return None
    if cache is None:
        try:
            cache = json.loads(RELEASE_CACHE.read_text())
        except (OSError, ValueError):
            return None
    probe = probe or rpy
    budget = budget if budget is not None else CLOSURE.setdefault("resign_probes", [RESIGN_PROBES_PER_TICK])
    tags = {t for t, _ in _all_flow_tags()}
    cands = [r for r in (cache or {}).get("signed_records") or []
             if isinstance(r, dict) and r.get("resign") and r.get("versioned") and not r.get("resign_error")
             and r.get("flow_tag") in tags and tag_covers(r.get("flow_tag"), j.get("die"))
             and r.get("prov_file") and r.get("host") and _asap7_design(r.get("routed_db")) == design]
    if not cands:
        return None
    memo = j.setdefault("resign_sha", {})                # host:path -> sha256 (routed DBs are immutable once signed)

    def sha(host, path, prov=None):
        k = f"{host}:{prov or path}"
        if k not in memo:
            if budget[0] <= 0:
                return None
            budget[0] -= 1
            got = probe(host, PROBE_ROUTED_SHA, {"db": path, "prov": prov}, timeout=900)
            if got.get("error") or not got.get("sha"):
                return None
            memo[k] = got["sha"]
        return memo[k]
    mine = next((x for x in (sha(h, db) for h in jhosts) if x), None)
    if not mine:
        return None
    for r in sorted(cands, key=lambda r: r["flow_tag"], reverse=True):
        if sha(r["host"], r["routed_db"], r["prov_file"]) == mine:
            return dict(flow_tag=r["flow_tag"], tag_commit=r.get("src_commit"), record=r["prov_file"], host=r["host"],
                        routed_db=r["routed_db"], routed_db_sha256=mine)
    return None


def retry_unversioned(st):
    """an archived SIGNED-UNVERSIONED run is promoted once a flow release tag carries exactly its flow, or (KW-FIX-4
    11-03) once a valid RE-SIGN of its same routed DB on a released flow tag exists (resign_carry)"""
    # WF-1 11-14 (#4): resolve_provenance (git rev-parse / fetch / flow-tag diffs) is per (src, flow, die), not per job, and its
    # git calls are independent: resolve each distinct key once, on a small thread pool, then walk the jobs
    from concurrent.futures import ThreadPoolExecutor
    keys = sorted({(j["src"], j.get("flow", ""), j.get("die")) for j in st["jobs"].values()
                   if j.get("status") == "SIGNED-UNVERSIONED" and j.get("archive")}, key=str)
    provs = {}
    if keys:
        def _one(k):
            try:
                return k, resolve_provenance(*k)
            except Exception as e:                      # a failed lookup is retried next tick
                return k, {"src_commit": "", "flow_tag": "", "error": f"{type(e).__name__}: {e}"[:200]}
        with ThreadPoolExecutor(max_workers=6) as ex:
            provs = dict(ex.map(_one, keys))
    for j in st["jobs"].values():
        if j.get("status") != "SIGNED-UNVERSIONED" or not j.get("archive"):
            continue
        prov = dict(provs[(j["src"], j.get("flow", ""), j.get("die"))])
        if prov.get("error"):
            j["prov_error"] = prov["error"]
            if apply_legacy(j):
                prov = {"src_commit": prov.get("src_commit") or j.get("src_commit", ""), "flow_tag": LEGACY_TAG}
            else:
                rc_ = resign_carry(j)
                if not rc_:
                    continue
                j["resign_carry"] = rc_
                prov = {"src_commit": prov.get("src_commit") or j.get("src_commit", ""), "flow_tag": rc_["flow_tag"]}
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
            f"flow {j['flow_tag']}" + (f" via RE-SIGN {j['resign_carry']['host']}:{j['resign_carry']['record']}"
                                       if j.get("resign_carry") else "") + ")")


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


def admit_new(st, rows, only_new=False, budget=None):
    """-> rows submitted.  only_new: the pass after the wave step, rows no earlier tick or pass has seen; budget: submits
    left this tick (default MAX_SUBMIT_PER_TICK)."""
    submitted = 0
    budget = MAX_SUBMIT_PER_TICK if budget is None else budget
    if not only_new:
        withdraw_unqueued(st, rows)
    for rid, r in sorted(rows.items(), key=lambda kv: (die_priority(kv[1].get("die")), kv[1]["line"])):
        j = st["jobs"].get(rid)
        if only_new and j is not None:
            continue
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
        if (r["mode"] != "adopt" and (r["geom"].upper() not in GEOM_OK or not r["geom_ref"]) and SP.is_minimal()
                and r["geom"].upper() != "AUTO" and canonical_die(r.get("die") or "") != "hbm"):
            # R-MINIMAL: the geometry / visual verdict never blocks launch or route; recorded as an advisory
            if not (j or {}).get("geom_advisory"):
                log(f"GEOM-ADVISORY {rid} {r['die']}/{r['type']}: GEOM '{r['geom']}' not PASS -- submitted (R-MINIMAL)")
            r = dict(r, geom_advisory=f"GEOM '{r['geom']}' {r.get('geom_auto') or ''}".strip())
        elif r["mode"] != "adopt" and (r["geom"].upper() not in GEOM_OK or not r["geom_ref"]):
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
        if submitted >= budget:
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
               + "".join(f" [{t}]" for t in (p.get("fail_text") or {}).values() if t)
               if p.get("fail_marks") else "no run_kit*.sh runner found" if not p.get("runner") else "")
        if not why and p.get("signoff_missing") and r.get("goal") not in ("cts", "grt"):
            why = (f"kit signoff.py lacks {', '.join(p['signoff_missing'])} (sign-off would crash after the route); "
                   "stage the whole bundle: tools/die_plan/signoff.py copy_signoff_bundle(kit)")
        if r["mode"] == "adopt":
            why = "kit dir missing" if not p["exists"] else "no config.mk" if not p.get("config") else ""
        beside_proof = p.get("proof_only") is True and os.environ.get("AP_ROUTE_BESIDE_PROOF", "1") != "0"
        procs = hub_procs(r["path"])
        if beside_proof:
            # KW-FIX-30 11-07 (BESIDE-PROOF never fired, 0 lines 10:59-13:2x): the PLACE client of this kit stays alive
            # on the hub inside run_kit.sh's "lec_async.sh finish" until the proof ends, and the running proof keeps
            # K/lec*.log fresh; neither is a flow job.  Any other hub process, or a fresh flow log, still holds.
            la = p.get("flow_log_age_s", la)
            procs = [x for x in procs if not place_client(x[0], r["path"])]
        # WF-1 11-14 (COORD/OWNER friction): busy = a live container, a live ot-run / ot-job process for the kit dir (procs), or a
        # log updated within 10 min (was 15).  A kit with none of them is not busy: the row is submitted, not held.
        busy = (p.get("busy") is not False and not beside_proof) or (la is not None and la < 600) \
            or (bool(procs) and remote_job_alive(r["path"], procs))
        if not why and busy and r["mode"] != "adopt":
            log(f"HOLD {rid} {r['die']}/{r['type']}: kit busy (container: {p.get('busy')}, logs "
                f"{'none' if la is None else f'{la / 60:.0f} min old'}); retry next tick")
            continue
        if why:
            log(f"REJECT {rid} {r['die']}/{r['type']} {r['kit']}: {why}")
            set_status(st, j, "REJECTED", why)
            continue
        j["runner"] = p["runner"]
        j["stage_resume"] = p.get("resume")              # KW-RESUME-1: reused steps + source attempt (PROVENANCE)
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
        if beside_proof:
            log(f"BESIDE-PROOF {rid} {r['die']}/{r['type']}: only the pre-route LEC is alive on this kit; route starts, "
                "sign-off still waits for its verdict")
        submit(st, j)
        submitted += 1
    return submitted


def admit_after_wave(st, budget):
    """FLOW-TIME-1 11-07: KW.step runs after admit_new, so a kit the wave enqueues waited a whole tick (p50 992 s over 617
    wave kits) for the next admit_new although nothing else stood in its way.  Admit such rows in the tick that enqueued
    them.  Same checks as admit_new; only rows with no job yet, so held rows are not probed twice.  AP_ADMIT_AFTER_WAVE=0
    turns it off."""
    if os.environ.get("AP_ADMIT_AFTER_WAVE", "1") == "0" or budget <= 0:
        return 0
    rows = parse_queue(read_queue_text())
    if not any(rid not in st["jobs"] for rid in rows):
        return 0
    resolve_geom(rows, GEOM_TEXT)
    AG.prepare(sys.modules[__name__], st, rows)
    resolve_geom(rows, GEOM_TEXT)
    n = admit_new(st, rows, only_new=True, budget=budget)
    save_state(st)
    return n


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


ORPHAN_DEAD_S = 600


def job_alive_remote(j, alive_probe=None):
    """WF-1 11-14: does anything of this autopilot job still live on its target host(s)?  A docker container whose name holds the item,
    or any process naming the kit dir (ssh, cached 5 min per host and kit by remote_job_alive's table).  Unknown (ssh fails) = alive."""
    path = j.get("path") or ""
    item = os.path.basename(path.rstrip("/"))
    if not path:
        return True
    now = time.time()
    hosts = [h for h in dict.fromkeys(ssh_host(x) for x in (j.get("ran_on"), j.get("host"), j.get("probe")) if x)
             if h not in ("localhost", HUB_NAME)]
    if not hosts:
        return False
    for h in hosts:
        key = (h, path)
        hit = _REMOTE_ALIVE.get(key)
        if hit and now - hit[0] < 300:
            alive = hit[1]
        else:
            cmd = (f"docker ps --format '{{{{.Names}}}}' 2>/dev/null | grep -c -- {shlex.quote(item)}; "
                   f"ps -eo args | grep -F -- {shlex.quote(path.rstrip('/'))} | grep -vc grep")
            rc, o, _ = (alive_probe or sh)(["ssh", "-n", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", h, cmd], timeout=40)
            nums = [int(x) for x in o.split() if x.isdigit()]
            alive = True if (rc != 0 and not nums) else any(n > 0 for n in nums)
            _REMOTE_ALIVE[key] = (now, alive)
        if alive:
            return True
    return False


def orphan_is_dead(j, now=None, procs=None, remote_alive=None):
    """WF-1 11-14 (COORD: 4 ENQUEUED rows whose ot-run client died, earlyoom on epyc9): a job whose client unit is gone counts as DEAD
    (-> infra-orphan, resubmitted) once it has been without a live client for ORPHAN_DEAD_S: no hub ot-run / ot-job process for its kit
    dir (procs), nothing alive on the target host (container or process, job_alive_remote).  The 3 h kit-log idle wait stays for jobs
    that still show life."""
    now = time.time() if now is None else now
    done = j.get("client_done_at")
    if not done or now - float(done) < ORPHAN_DEAD_S:
        return False
    if (procs if procs is not None else hub_procs)(j.get("path") or "") if callable(procs) or procs is None else procs:
        return False
    return not (remote_alive or job_alive_remote)(j)


def poll_running(st):
    poll_pending_proofs(st)
    for j in list(st["jobs"].values()):
        if j.get("status") not in ("RUNNING", "ORPHAN"):
            continue
        if j.get("goal") in ("cts", "grt") and j.get("client_log"):
            try:
                txt = Path(j["client_log"]).read_text(errors="replace")
                ran = parse_client_log(txt).get("ran_on")
                if ran: j["ran_on"] = ran
            except OSError: pass
        if not j.get("adopted") and poll_physical_completion(st, j):
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
            sig = signals_cancel(j) or marked_cancel(j) or signals_external(j)
            if sig:
                client["cancelled"] = sig
        if client.get("cancelled"):
            j.update(cls="CANCELLED", kind="cancelled", reasons=client["cancelled"][:600], finished=time.time())
            log(f"CLASSIFY {j['id']} {j['die']}/{j['type']} -> CANCELLED (explicit ot-run --cancel; not resubmitted): "
                f"{client['cancelled'][:240]}")
            stop_cancelled(j, "explicit cancel")
            set_status(st, j, "CANCELLED", f"cancelled: {client['cancelled'][:200]}")
            continue
        if "ap_rc" not in client and not client.get("not_completed"):
            # client gone without a result (hub reboot / unit killed): the remote job may still run
            c = probe_job(j)
            if c and c.get("signoff"):
                finish(st, j, c, client)
                continue
            idle = time.time() - max((c or {}).get("last_log_mtime", 0), j.get("started", 0))
            if idle < ORPHAN_IDLE_S and orphan_is_dead(j):
                log(f"ORPHAN-DEAD {j['id']} {j['die']}/{j['type']}: no live ot-run client, container or process for {ORPHAN_DEAD_S // 60}+ min "
                    f"(kit logs {idle / 60:.0f} min old): infra-orphan, resubmitted")
                idle = ORPHAN_IDLE_S
            if idle < ORPHAN_IDLE_S:
                if j["status"] != "ORPHAN":
                    log(f"ORPHAN {j['id']}: ot-run client ended without a result; watching the kit logs")
                    set_status(st, j, "ORPHAN", "client gone")
                continue
            client = {"orphan": True, "msg": f"client lost, kit logs idle {idle / 3600:.1f} h"}
        if client.get("not_completed"):
            c = probe_job(j)
            if c and not c.get("signoff") and time.time() - c.get("last_log_mtime", 0) < ORPHAN_IDLE_S and orphan_is_dead(j):
                log(f"ORPHAN-DEAD {j['id']} {j['die']}/{j['type']}: no live ot-run client, container or process for {ORPHAN_DEAD_S // 60}+ min: infra-orphan")
                client = dict(client, orphan=True, msg=f"client lost, nothing alive for {ORPHAN_DEAD_S // 60}+ min")
            elif c and not c.get("signoff") and time.time() - c.get("last_log_mtime", 0) < ORPHAN_IDLE_S:
                if j["status"] != "ORPHAN":
                    log(f"ORPHAN {j['id']}: {client['msg']}; remote job may still run, watching its logs")
                    set_status(st, j, "ORPHAN", client["msg"])
                continue
        else:
            c = probe_job(j)
        if c is None and not client.get("publish_return"):
            log(f"HOLD {j['id']}: classify probe failed on every host; retry next tick")
            continue
        finish(st, j, c or {}, client)


def sealed_job_dir(j):
    """the sealed ot-job dir name ('ot-job: SEALED <dir>:' in the client log) of this attempt, or ''"""
    try:
        t = Path(j.get("client_log") or "").read_text(errors="replace")
    except OSError:
        return ""
    m = re.findall(r"ot-job: SEALED (/\S+/ot-jobs/[^/\s:]+)", t)
    return m[-1] if m else ""


EARLYOOM_NEAR_S = 60
OOMKILL_MAX = 4


def is_earlyoom_kill(reasons):
    """WF-1 11-14: a job killed by the host low-memory killer (make 'Error 241' = 256-15, or an earlyoom-matched SIGTERM 143)"""
    return bool(re.search(r"Error 241\b|earlyoom|post-CTS gate lost", str(reasons or "")))


def earlyoom_kill_near(host, t, probe=None):
    """True when earlyoom on `host` sent a SIGTERM within +-EARLYOOM_NEAR_S of epoch t (journal over ssh; unknown = False)"""
    if not host or not t:
        return False
    cmd = (f"sudo -n journalctl -u earlyoom --since @{int(t) - EARLYOOM_NEAR_S} --until @{int(t) + EARLYOOM_NEAR_S} --no-pager 2>/dev/null "
           f"| grep -c 'sending SIGTERM'")
    argv = ["bash", "-c", cmd] if host in ("localhost", HUB_NAME) else ["ssh", "-n", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", host, cmd]
    rc, o, _ = (probe or sh)(argv, timeout=60)
    nums = [int(x) for x in o.split() if x.isdigit()]
    return bool(nums and nums[-1] > 0)


def retained_publish_negative(j, client, probe=None):
    """Accept only a fresh measured failure from the exact retained job."""
    entry = client["publish_return"]
    host = client["ran_on"]
    probe = probe or rpy
    c = probe(host, PROBE_CLASSIFY, {"kit": entry["root"] + "/work", "since": j.get("started", 0),
                                   "goal": j["goal"], "retained_return_to": j["path"]})
    so = (c or {}).get("signoff")
    if not so or c.get("error") or so.get("verdict") != "NOT SIGNED":
        return None
    gates = SP.judge(so, j.get("die"))["gates"]
    failed = [k for k in so.get("fails", ()) if gates.get(k) == "FAIL"]
    if not failed:
        return None
    return {"host": host, "signoff": so, "failed_gates": failed}


def finish(st, j, c, client):
    if client.get("exit") == 143 and not c.get("oom") and not client.get("watchdog") and not client.get("cancelled"):
        try:                                             # WF-1 11-14: SIGTERM 143 with an earlyoom kill on the host within +-60 s is an OOM kill
            _t = Path(j.get("client_log") or "").stat().st_mtime
        except OSError:
            _t = 0
        if _t and earlyoom_kill_near(j.get("ran_on") or j.get("host"), _t):
            c = dict(c, oom=f"earlyoom SIGTERM on {j.get('ran_on') or j.get('host')} within {EARLYOOM_NEAR_S} s of the exit (client exit 143)")
    if client.get("exit") in (137, 143) and client.get("unit") and not c.get("oom"):
        w = watchdog_stop(client["unit"], j.get("started", 0))
        sj = "" if w else sealed_job_dir(j)
        if sj:
            # KW-FIX-46 11-12 (hbm PHY_NC 2731c12447d5): the WATCHDOG stops the container inside a sealed ot-job and its
            # STOP line names that container and the job dir, not the ot-heavy unit, so the stop read 'from outside'
            w = watchdog_stop(sj.rsplit("/", 1)[-1] + "/", j.get("started", 0))
        if w:
            client = dict(client, watchdog=w)
    cls, kind, reasons = classify(c, client)
    if client.get("publish_return"):
        j["publish_return"] = client["publish_return"]
        if not c.get("signoff") and j["goal"] == "route":
            retained = retained_publish_negative(j, client)
            if retained:
                j["retained_signoff"] = retained
                cls, kind, reasons = classify({"signoff": retained["signoff"]}, {})
                reasons = f"{reasons} | return copy failed; retained {retained['host']}:{j['publish_return']['root']}"
    if j.get("chain_required") and cls in ("SIGNED", "WAIT-PARENT"):
        chain = c.get("chain") or {}
        if chain.get("verdict") == "LEC_OOM":
            cls, kind, reasons = "CRASH", "proof-oom", str(chain.get("reason"))
        elif SP.is_minimal() and cls == "SIGNED":
            # R-MINIMAL: the routed LEC is advisory/async -- a missing / failed chain LEC never blocks the count; a
            # NOT EQUIVALENT receipt is recorded as an advisory on the job
            if chain.get("lec_verdict") not in (None, "EQUIVALENT"):
                reasons = f"{reasons}; advisory: routed LEC {chain.get('lec_verdict')}"
        elif (chain.get("started", 0) < j.get("started", 0) - 120
                or chain.get("verdict") != "PASS" or chain.get("lec_verdict") != "EQUIVALENT"
                or chain.get("lec_exit") != 0 or (j.get("chain_version", 1) >= 2 and chain.get("lec_all_shown") is not True)):
            cls, kind, reasons = "STRUCTURAL", "routed-lec", "autopilot chain incomplete: " + str(chain.get("reason") or "missing current routed LEC")
    if client.get("orphan") and cls == "CRASH" and kind not in ("tool-segfault",):
        kind, reasons = "infra-orphan", client["msg"]
    eco = ((c.get("chain") or {}).get("eco") or {}) if (c.get("chain") or {}).get("started", 0) >= j.get("started", 0) - 120 else {}
    if eco.get("summary") and cls not in ("SIGNED", "WAIT-PARENT"):
        # KW-ECO-1: the FAIL evidence carries the late-stage ECO result (kit_wave class table "late-ECO exhausted")
        reasons = f"{eco['summary'][:240]} | {reasons}"
    j.update(cls=cls, kind=kind, reasons=reasons[:600], probe=c.get("probe_host"),
             signoff=c.get("signoff"), finished=time.time())
    if c.get("chain"):
        j["chain"] = {k: c["chain"].get(k) for k in ("verdict", "reason", "gates", "lec", "lec_verdict",
                                                   "lec_all_shown", "lec_tool", "signoff", "netlist", "eco")}
    if c.get("pregrt_hold_fallback"):                # R-CLOCK (COORD 11-13 07:2x): advisory, recorded, never a class
        j["pregrt_hold_fallback"] = c["pregrt_hold_fallback"]
        log(f"PREGRT_HOLD_FALLBACK {j['id']} {j['die']}/{j['type']}: {c['pregrt_hold_fallback'][:200]}")
    log(f"CLASSIFY {j['id']} {j['die']}/{j['type']} -> {cls} ({kind}): {reasons[:240]}")
    if cls == "CRASH" and kind in INFRA_KINDS and not j.get("adopted"):
        why = wave_superseded(j)
        if why:
            j.update(cls="CANCELLED", kind="cancelled")
            log(f"CLASSIFY {j['id']} {j['die']}/{j['type']} -> CANCELLED (not resubmitted): {why[:240]}")
            stop_cancelled(j, "wave no longer wants it")
            set_status(st, j, "CANCELLED", f"wave no longer wants it: {why[:200]}")
            return
        notrun = kind == "infra-notrun"
        if notrun and j.get("notrun_retries", 0) < MAX_NOTRUN:
            j["notrun_retries"] = j.get("notrun_retries", 0) + 1
            submit(st, j, f"(resubmit: never admitted, {j['notrun_retries']}/{MAX_NOTRUN})")
            return
        if kind == "infra-oom" and is_earlyoom_kill(reasons) and j.get("oomkill_retries", 0) < OOMKILL_MAX:
            # WF-1 11-14: killed by the host's earlyoom, not by the job's own cap: resubmit from the run dir checkpoint without raising --mem
            j["oomkill_retries"] = j.get("oomkill_retries", 0) + 1
            j["infra_retry"] = True
            log(f"EARLYOOM-RESUBMIT {j['id']} {j['die']}/{j['type']}: host low-memory kill ({j['oomkill_retries']}/{OOMKILL_MAX}); "
                f"resumes the run dir, --mem {j['mem_gb']} unchanged")
            submit(st, j, f"(resubmit {j['oomkill_retries']}/{OOMKILL_MAX} after an earlyoom kill; resumes the run dir; --mem {j['mem_gb']})")
            return
        if kind == "infra-oom" and j.get("oom_retries", 1 if j.get("infra_retry") else 0) < MAX_OOM_RESUBMITS:
            j["oom_retries"] = j.get("oom_retries", 1 if j.get("infra_retry") else 0) + 1
            j["infra_retry"] = True
            j["mem_gb"] = min(512, int(j["mem_gb"] * 1.5 + 0.999))
            submit(st, j, f"(resubmit {j['oom_retries']}/{MAX_OOM_RESUBMITS} after infra-oom; resumes the run dir; "
                          f"--mem {j['mem_gb']})")
            return
        lost = kit_lost(j)
        if lost:
            # KIT-OPS-5 11-14 (COORD): the gen dir / runner is gone (epyc4 kits): a resubmit can only die with rc 127 and keeps
            # the family "attempted" on the old src.  Mark the attempt dead (infra-lost) so the wave builds a new attempt.
            log(f"KIT-LOST {j['id']} {j['die']}/{j['type']}: {lost}: not resubmitted, attempt dead (the wave generates a new attempt from the current src)")
            set_status(st, j, "CRASH", f"infra-lost: kit lost, {lost}"[:200])
            after_class(st, j)
            released_cleanup()
            return
        if not notrun and kind != "infra-oom" and not j.get("infra_retry"):
            j["infra_retry"] = True
            submit(st, j, f"(resubmit once after {kind}; resumes the run dir; --mem {j['mem_gb']})")
            return
    set_status(st, j, cls, f"{kind}: {reasons[:200]}")
    after_class(st, j)
    released_cleanup()


def released_cleanup():
    """Terminal notification only: owners explicitly queue exact file releases."""
    queue = Path(os.environ.get("OT_REAPER_RELEASE_QUEUE", "~/.local/state/ot-reaper/releases")).expanduser()
    runner = Path(os.environ.get("OT_REAPER_RELEASE_RUNNER", "~/.local/lib/fleet/released-reaper-1106/ot-reaper.py")).expanduser()
    if not runner.is_file() or not queue.is_dir() or not any(queue.glob("*.json")):
        return
    try:
        with (queue.parent / "routine.log").open("a") as stream:
            subprocess.Popen([sys.executable, str(runner), "--released-manifest", str(queue)],
                             stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as error:
        log(f"released cleanup deferred to periodic pass: {error}")


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
        # OWNER 11-13 03:5x (KIT-OPS-1): visual gate at sign-off -- a kit-wave type build is archived (counted) only with its
        # visual verdict GOOD / OK / ISSUES-ACCEPT; until then it stays SIGNED, archive pending (retried each tick); a BAD /
        # ISSUES verdict withholds the archive for good (the wave row goes to WAIT-FORM).  Kit data is kept either way.
        try:
            vg, vwhy = KW.signoff_visual_gate(str(AP_DIR), j)
        except Exception as e:                       # noqa: a gate read problem holds, never counts by accident
            vg, vwhy = "hold", f"archive pending: visual gate unreadable ({type(e).__name__}: {e})"
        if vg:
            j["delete_pending"] = False
            if j.get("visual_gate") != vwhy:
                log(f"VISUAL-GATE {j['id']} {j['die']}/{j['type']}: {vwhy[:200]}")
            j["visual_gate"] = vwhy[:300]
            set_status(st, j, "SIGNED", vwhy)
            return
        j.pop("visual_gate", None)
        archive(st, j)
    elif cls == "WAIT-PARENT":
        j["delete_pending"] = False
        tsv_append("provisional.tsv", j["id"], [j["die"], j["type"], j["src"],
                   ssh_host(j.get("probe") or j["host"]), j["kit"],
                   (j.get("signoff") or {}).get("local_verdict"), j.get("reasons", ""), j.get("lane", "")])
        log(f"KEEP {j['id']} local physical PASS needs actual parent receipt; no release archive or failure cleanup")
    elif cls in ("NEAR-MISS", "STRUCTURAL", "CRASH", "FAIL"):
        if j.get("kind") == "proof-oom":
            record_failure(st, j)  # proof admission failure; no geometry reroute
        elif (j.get("signoff") or {}).get("odb"):
            start_review(st, j)
        else:
            record_failure(st, j)


ARCHIVE_PERMANENT_RE = re.compile(r"FileNotFoundError|No such file or directory|NotADirectoryError")


def archive_backoff(j, err, now=None):
    """FLOW-HEALTH-1 11-15 (FABLE-FLOW-2000 d): 'ARCHIVE FAILED 3054c87a89d6: probe rc 1: FileNotFoundError' was retried every tick, 243 times on one job
    whose kit path no longer existed.  From the 3rd consecutive failure the retry backs off (3 min x 2^n, at most 6 h); a permanent error
    (the kit / sign-off path is gone) is posted once as NEEDS-LANE.  -> True when this failure is the one to post"""
    now = time.time() if now is None else now
    n = int(j.get("archive_fail_n") or 0) + 1
    j["archive_fail_n"] = n
    j["archive_fail_err"] = str(err)[:300]
    if n >= 3:
        j["archive_retry_at"] = now + min(180 * 2 ** (n - 3), 6 * 3600)
    if ARCHIVE_PERMANENT_RE.search(str(err)) and n >= 3 and not j.get("archive_posted"):
        j["archive_posted"] = now
        return True
    return False


def archive_due(j, now=None):
    return (time.time() if now is None else now) >= float(j.get("archive_retry_at") or 0)


def archive(st, j):
    if not archive_due(j):                                           # backed off after repeated failures (archive_backoff)
        return
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
        err = r.get("error") or r.get("errors")
        post = archive_backoff(j, err)
        log(f"ARCHIVE FAILED {j['id']} (x{j.get('archive_fail_n')}): {err}; " + ("retry next tick" if int(j.get("archive_fail_n") or 0) < 3 else "backed off until %s" % time.strftime("%H:%M", time.localtime(j["archive_retry_at"]))))
        if post:
            set_status(st, j, "SIGNED-NOT-ARCHIVED", "archive path gone (permanent): " + str(err)[-160:])      # terminal: archive() only handles SIGNED
            coord_append("lanes/COORD-REVIEW-QUEUE.md", f"- {now_s()} NEEDS-LANE [AUTOPILOT -> COORD] archive of {j['die']}/{j['type']} ({j['id']}) fails permanently: {str(err)[-200:]}; "
                                                         "the kit path is gone, so the signed record cannot be archived from the host; archive from the AGIdock copy or re-sign")
        if j.get("status") != "SIGNED-NOT-ARCHIVED":
            set_status(st, j, "SIGNED", "archive pending")
        return
    # AUTO-EXPORT-1118 (FABLE-FLOW-0800 class H, OWNER r711): the fleet mirror copy is gone; the signed-store export is
    # AUTO-EXPORT alone (full record to rtx-pro, metadata + display to AGIdock, INDEX rows).  The dest above stays: it is
    # the wave's local relocation of the kit and its bind view, not an export.  The record is spooled on the host.
    q = rpy(host, PROBE_AUTO_EXPORT, {"signoff": os.path.join(dest, "kit", os.path.basename(os.path.dirname(so["path"])), "signoff.json"),
                                      "fallback": so["path"], "die": j.get("die"), "element": j.get("type")}, timeout=120)
    mirror = "AUTO-EXPORT " + (q.get("queued") or "NOT QUEUED (%s); the hub scan picks it up" % (q.get("error") or "?"))[:200]
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
    log(f"RELOCATED {j['id']} {j['die']}/{j['type']} -> {j['archive']} "
        + ("(already there)" if r.get("exists") else f"({r.get('files')} files, MD5SUMS)") + f"; export {mirror}"
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
    # KW-FIX-44 11-10 (COORD): a review render is a small read-only job (one routed ODB, 2 threads, an honest
    # render_mem_gb request) that GEOM review waits on.  Queued as a normal job it sat behind 30-50 heavy waiters
    # (epyc4 admits -84 GB, epyc7 9 GB; no PNG 04:19-07:0x).  It goes --direct: it starts at once while real
    # MemAvailable >= mem + 32 GB on its host, and still waits there when that is not true.  AP_REVIEW_DIRECT=0 opts out.
    direct = ["--direct"] if os.environ.get("AP_REVIEW_DIRECT", "1") != "0" else []
    argv = [OT_RUN, "--mem", str(mem), "--threads", "2", "--dir", rev, "--no-spill", *direct, "--",
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
        kind = j.get("kind", "")
        nonphysical = (j.get("publish_return") or kind in ("preflight", "admission-tools", "proof-oom") or
                       kind.startswith("infra-") or j.get("goal") in ("synth", "lec", "post", "proof"))
        if nonphysical:
            j.update(delete_pending=False, data_deleted=False,
                     checkpoint_preserved="preflight/infra/proof attempt does not own prior physical checkpoints")
        else:
            d = rpy(host, PROBE_DELETE, {"kit": j["path"], "dry": DRY,
                                       "preserve_before": j.get("started")}, timeout=1800)
            if d.get("preserved"):
                j.update(delete_pending=False, data_deleted=False, checkpoint_preserved=d.get("reason"))
                log(f"KEEP {j['id']}: {d.get('reason')}")
            elif d.get("error") or d.get("errors"):
                log(f"DELETE deferred {j['id']} on {host}: {d.get('error') or d.get('errors')}")
            else:
                j.update(delete_pending=False, data_deleted=not DRY)
                log(f"DELETED {j['id']} failed run data on {host} (logs kept): "
                    f"{', '.join(d.get('deleted') or ['nothing left'])}")
        failed_notice(j, cls, host)
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
    data_status = ("run data deleted (logs kept)" if j.get("data_deleted") else
                   "run data kept: " + (j.get("checkpoint_preserved") or "cleanup deferred"))
    msg = (f"{now_s()} AUTOPILOT -> {lane}: FAILED {j['id']} {j['die']}/{j['type']} ({cls}/{j.get('kind', '')}): "
           f"{(j.get('reasons') or '')[:300]} | kit {host}:{j['path']} src {j['src']} | review {rev} | "
           f"{data_status}; kit stopped, NOT retried -- fix structurally and enqueue a fresh kit")
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


MINIMAL_REJUDGE_PER_TICK = int(os.environ.get("AP_MINIMAL_REJUDGE_PER_TICK", "8"))


def minimal_rejudge_candidate(j):
    """R-MINIMAL (PROFILE-1): a finished routed NEAR-MISS / STRUCTURAL job whose recorded sign-off numbers pass the
    minimal gates (DRC 0, TT setup >= -42 ps, FF hold >= 0) and whose data is still on disk is re-probed once and
    re-finished, so it archives / counts like a new sign-off"""
    so = j.get("signoff") or {}
    return (SP.is_minimal() and j.get("status") in ("DONE-NEAR-MISS", "DONE-STRUCTURAL", "DONE-FAIL") and isinstance(so, dict)
            and so and not j.get("data_deleted") and not j.get("minimal_rejudged") and canonical_die(j.get("die")) != "hbm"
            and SP.judge(so)["verdict"] == "SIGNED")


RP_T = {}                    # WF-1 11-14: seconds / calls per retry_pending branch, logged by the tick


def _rp(name, t0):
    a = RP_T.setdefault(name, [0, 0.0])
    a[0] += 1
    a[1] += time.time() - t0


POLL_TIMED = ("poll_pending_proofs", "poll_physical_completion", "poll_adopted", "probe_job", "finish", "hub_procs", "unit_active", "stop_cancelled",
              "signals_cancel", "orphan_is_dead", "job_alive_remote", "parse_client_log")


def instrument_poll():
    """WAVE-TICK-1119: per-call wall timers of what poll_running calls, one POLL-TIMES line per tick (top consumers).  Idempotent."""
    g = globals()
    for name in POLL_TIMED:
        fn = g.get(name)
        if fn is None or getattr(fn, "_poll_timed", False):
            continue

        def mk(name, fn):
            def timed(*a, **k):
                t0 = time.time()
                try:
                    return fn(*a, **k)
                finally:
                    _rp("poll:" + name, t0)
            timed._poll_timed = True
            timed.__wrapped__ = fn
            return timed
        g[name] = mk(name, fn)


def poll_times_line():
    top = sorted(((k, v) for k, v in RP_T.items() if k.startswith("poll:")), key=lambda kv: -kv[1][1])[:8]
    return "POLL-TIMES " + " ".join(f"{k[5:]}={v[0]}x/{v[1]:.0f}s" for k, v in top)


def retry_pending(st):
    released = failure_resolutions()
    budget = MINIMAL_REJUDGE_PER_TICK
    _t = time.time()
    for j in list(st["jobs"].values()):
        if budget > 0 and not DRY and minimal_rejudge_candidate(j) and not hub_procs(j["path"]):
            budget -= 1
            j["minimal_rejudged"] = time.time()
            _t = time.time()
            c = probe_job(j)
            _rp("rejudge_probe", _t)
            so = (c or {}).get("signoff") or {}
            if so and SP.judge(so)["verdict"] == "SIGNED":
                log(f"MINIMAL-REJUDGE {j['id']} {j['die']}/{j['type']}: {j.get('status')} -> re-finish under R-MINIMAL")
                finish(st, j, c, {"minimal_rejudge": True})
            _t = time.time()
            save_state(st)
            _rp("save_state", _t)
            continue
        if j.get("status") == "SIGNED" and not DRY:
            _t = time.time()
            after_class(st, j)                         # trial check (rule 1) before an archive retry
            _rp("after_class", _t)
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
            _t = time.time()
            c = probe_job(j)
            _rp("wait_parent_probe", _t)
            so = (c or {}).get("signoff") or {}
            if so and (so.get("verdict") != "LOCAL_PASS_NEEDS_PARENT"
                       or (SP.is_minimal() and SP.judge(so)["verdict"] == "SIGNED")):
                # R-MINIMAL: io_hold_parent receipts are advisory -- a WAIT-PARENT local pass counts now
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
def tick_progress(ap_dir, t0, phase, done=False):
    """FLOW-1355 (2): .tick.progress = {start, phase, t, done}, rewritten at every phase mark; a tick killed by the service timeout leaves done=false"""
    try:
        (Path(ap_dir) / ".tick.progress").write_text(json.dumps({"start": t0, "phase": phase, "t": time.time(), "done": bool(done)}))
    except OSError:
        pass


def tick_killed_check(ap_dir, now_start):
    """at the start of a tick: the previous tick left done=false = it was killed (autopilot.service TimeoutStartSec) or crashed: one TICK-KILLED line with its last phase and age"""
    try:
        d = json.loads((Path(ap_dir) / ".tick.progress").read_text())
    except (OSError, ValueError):
        return None
    if d.get("done") or float(d.get("start") or 0) >= now_start:
        return None
    msg = "TICK-KILLED previous tick started %s was cut off in phase '%s' after %.0f s (killed by the service timeout or crashed; the launch pass may not have run)" % (
        time.strftime("%H:%M:%S", time.localtime(float(d.get("start") or 0))), d.get("phase"), float(d.get("t") or 0) - float(d.get("start") or 0))
    log(msg)
    return msg


def bad_hosts_from_status(text, hub=None):
    """hosts that are unreadable (no ot-run status row of a known fleet host) or over 2x their cores"""
    stt = KW.parse_otrun_status(text)
    if not stt:
        return set()
    hub = hub or HUB_NAME
    names = set(WJ.FLEET) | set(stt)
    return {h for h in names if h not in (hub, "localhost") and KW.host_unreadable(stt, h, hub)}      # FLOW-1949 (5): overloaded hosts still get their stops / scope teardown


def mark_bad_hosts():
    """COORD 11-19: at tick start, before any cancel-stop / survivor-stop / poll ssh, the fleet-wide stop helpers learn which hosts to skip (wave_jobs.BAD_HOSTS)"""
    rc, out, _ = sh([OT_RUN, "--status"], timeout=60)
    if rc == 0:
        WJ.BAD_HOSTS = bad_hosts_from_status(out)
        if WJ.BAD_HOSTS:
            log("BAD-HOSTS this tick (stop / reap ssh skipped): " + " ".join(sorted(WJ.BAD_HOSTS)))


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
    _t0 = time.time()
    _ph = {}                                           # WF-1 11-14: per-phase wall seconds, one TICK-TIMES line at the end
    tick_killed_check(AP_DIR, _t0)

    def _mark(name, _last=[time.time()]):
        n = time.time()
        _ph[name] = round(n - _last[0], 1)
        _last[0] = n
        tick_progress(AP_DIR, _t0, name)
    st = load_state()
    try:
        check_pending_stops(st)
    except Exception as _e:                            # a result check never stops the tick
        log(f"CANCEL-STOP-RESULT skipped: {type(_e).__name__}: {_e}")
    try:
        mark_bad_hosts()
    except Exception as _e:                            # a host-status read never stops the tick
        log(f"BAD-HOSTS skipped: {type(_e).__name__}: {_e}")
    rows = parse_queue(read_queue_text())
    geom_text = read_coord("lanes/GEOM-REVIEW.md")
    _mark("load")
    global GEOM_TEXT
    GEOM_TEXT = geom_text
    # Resolve explicit visual verdicts before promoting pending requests to measured checks.
    # Resolve again after prepare to apply a later reviewer FAIL on an AUTO-GEOM result.
    resolve_geom(rows, geom_text)
    AG.prepare(sys.modules[__name__], st, rows)
    resolve_geom(rows, geom_text)
    _mark("geom")
    load_closure()
    apply_evac(st)
    instrument_poll()
    poll_running(st)
    log(poll_times_line())
    _mark("poll_running")
    _t = time.time()
    poll_reviews(st)
    _rp("poll_reviews", _t)
    _t = time.time()
    retry_pending(st)
    _rp("retry_pending_total", _t)
    _t = time.time()
    # WF-1 11-14 (COORD/OWNER: the commit / flow-tag tie is removed from counting; COUNT-FRICTION-1 credits SIGNED-UNVERSIONED
    # directly): promoting unversioned records only to get provenance cost 476 s of a 1033 s tick, so it is OFF by default.
    # AP_RETRY_UNVERSIONED=1 (or the marker autopilot/RETRY-UNVERSIONED) turns it back on.
    if os.environ.get("AP_RETRY_UNVERSIONED") == "1" or (AP_DIR / "RETRY-UNVERSIONED").exists():
        retry_unversioned(st)
    _rp("retry_unversioned", _t)
    _mark("reviews_retry")
    log("RETRY-PENDING-TIMES " + " ".join(f"{k}={v[0]}x/{v[1]:.0f}s" for k, v in RP_T.items()))
    submitted = admit_new(st, rows)
    save_state(st)
    _mark("admit_new")
    if os.environ.get("AP_WAVE_BALANCE", "1") != "0":   # WAVE-BALANCE-1 11-11: inert unless kit_wave.json wave_balance.enabled
        try:
            WB.step(sys.modules[__name__], st)
            save_state(st)
        except Exception as e:                         # a balance pass must never stop the chain
            log(f"WAVE-BALANCE failed: {type(e).__name__}: {e}")
    _mark("wave_balance")
    if os.environ.get("AP_KIT_WAVE", "1") != "0":      # KIT-WAVE-1 (owner 10-30 (A)); inert without autopilot/kit_wave.json
        try:
            KW.step(sys.modules[__name__])
        except Exception as e:                         # the wave must never stop the chain
            log(f"KIT-WAVE failed: {type(e).__name__}: {e}")
        try:
            admit_after_wave(st, MAX_SUBMIT_PER_TICK - submitted)
        except Exception as e:                         # the next tick admits these rows anyway
            log(f"ADMIT-AFTER-WAVE failed: {type(e).__name__}: {e}")
    _mark("kit_wave_step+admit")
    # WF-1 11-14 (#4): auto-resign has its own lock and state file and no tick state; when autopilot/AUX-RESIGN exists it runs in its
    # own timer (autopilot-aux.timer: autopilot.py aux) instead of serially here (measured 164 s of a 1033 s tick).  Remove the marker to
    # put it back into the tick.
    if os.environ.get("AP_AUTO_RESIGN", "1") != "0" and not (AP_DIR / "AUX-RESIGN").exists():   # FLOW-29 owner 11-04: signed runs re-signed on the newest tag, no agent
        try:
            AR.step(sys.modules[__name__])
        except Exception as e:                         # a re-sign pass must never stop the chain
            log(f"AUTO-RESIGN failed: {type(e).__name__}: {e}")
    _mark("auto_resign")
    if not loop_gaps_off_tick():
        try:
            write_loop_gaps(st, rows, geom_text)
        except Exception as e:                         # the gap report must never stop the chain
            log(f"LOOP-GAPS failed: {type(e).__name__}: {e}")
    _mark("loop_gaps")
    UU.step(sys.modules[__name__])                     # never raises; one UNDER-USE line (idle threads per host + top hold reasons)
    _mark("under_use")
    tick_progress(AP_DIR, _t0, "done", done=True)
    log("TICK-TIMES total=%.0fs " % (time.time() - _t0) + " ".join(f"{k}={v}s" for k, v in _ph.items()))
    counts = {}
    for j in st["jobs"].values():
        counts[j.get("status")] = counts.get(j.get("status"), 0) + 1
    print(f"{now_s()} autopilot tick done: queue {len(rows)} rows; " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))))
    return 0


def loop_gaps_off_tick():
    """COORD 11-20 (loop_gaps 85-110 s of every tick): when autopilot/AUX-LOOPGAPS exists the gap report runs in the aux timer (10 min, own process), not serially in the tick.  Remove the
    marker to put it back into the tick"""
    return (AP_DIR / "AUX-LOOPGAPS").exists()


def aux_loop_gaps():
    """the LOOP-GAPS.txt / OWNERS.tsv pass outside the tick, on a READ-ONLY copy of the state (no resolve_geom / AUTO-GEOM prepare: those mutate state and stay in the tick)"""
    st = load_state()
    rows = parse_queue(read_queue_text())
    geom_text = read_coord("lanes/GEOM-REVIEW.md")
    global GEOM_TEXT
    GEOM_TEXT = geom_text
    t0 = time.time()
    write_loop_gaps(st, rows, geom_text)
    log(f"LOOP-GAPS (aux) written in {time.time() - t0:.0f}s")


def aux(args):
    """WF-1 11-14 (#4): the auto-resign pass outside the tick (own timer); auto_resign.step holds its own flock"""
    global DRY
    DRY = getattr(args, "dry_run", False)
    if loop_gaps_off_tick():
        try:
            aux_loop_gaps()
        except Exception as e:                          # a gap report never stops the aux pass
            log(f"LOOP-GAPS (aux) failed: {type(e).__name__}: {e}")
    try:
        AR.step(sys.modules[__name__])
    except Exception as e:
        log(f"AUTO-RESIGN (aux) failed: {type(e).__name__}: {e}")
        return 1
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
    submitted_kits = {(j.get("die", ""), j.get("type", "")) for j in jobs
                      if j.get("status") not in ("WAIT-GEOM", "REJECTED", None) and (j.get("attempts") or j.get("adopted"))}
    gaps = LG.gaps_geom(geom_text, now, submitted_tags, LG.parse_resolved(read_coord("autopilot/resolved.tsv")),
                        submitted_kits)
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


def read_plan_json(rel):
    """a plan json of origin/main, or its .json.gz twin (plan_of_record packages ship gzipped); None if neither"""
    j = _json(read_repo(rel))
    if j is not None:
        return j
    if REPO_FILES:
        import gzip
        try:
            return _json(gzip.decompress((Path(REPO_FILES) / (rel + ".gz")).read_bytes()).decode(errors="replace"))
        except (OSError, ValueError, EOFError):
            return None
    rc, out, _ = sh(["bash", "-c", f"set -o pipefail; git -C {shlex.quote(str(REPO))} show "
                     f"{shlex.quote('origin/main:' + rel + '.gz')} | gunzip -c"], timeout=120)
    return _json(out) if rc == 0 else None


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
        plans[die] = read_plan_json(f"physical/die_plan/{pdir}/die_plan.json")
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
    operator_args = sys.argv[1:] if argv is None else argv
    if operator_args[:1] == ["reconcile-wave"]:
        import wave_reconcile
        return wave_reconcile.main(operator_args[1:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("tick")
    t.add_argument("--dry-run", action="store_true")
    sp.add_parser("status")
    x = sp.add_parser("aux")
    x.add_argument("--dry-run", action="store_true")
    c = sp.add_parser("classify")
    c.add_argument("kit")
    c.add_argument("--since", type=float, default=0)
    c.add_argument("--goal", default="route")
    c.add_argument("--exit", type=int, default=None)
    sp.add_parser("reconcile-wave", help="read-only current-row/terminal-job report and approved recovery suggestions")
    a = ap.parse_args(argv)
    return {"tick": tick, "status": status, "classify": classify_cmd, "aux": aux}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
