#!/usr/bin/env python3
"""ot-autoclean: standing automatic disk cleanup for the fleet scratch disks (AUTOCLEAN-7, OWNER 2026-11-07 18:1x:
"all hosts should automatically apply the cleanup rule: copy signed results to the AGIdock archive, then delete
finished and superseded runs").

Two halves, one file (the localhost driver copies this file to every host):

  HOST  `run` (hourly timer per host; DRY RUN unless --apply).  Deletes ONLY these classes:
    a  kit-wave attempt dirs  .../items/<item>/attempt_N  older than 6 h whose kit-wave state (snapshot) says
       finished (FAIL / CANCELLED / SUPERSEDED / WITHDRAWN, ENQUEUED with a terminal queue status) or superseded
       (a later attempt_M of the same item exists in the state); never one a running/queued/held row, a resume
       source or a spec src/plan/queue_src points at, never one holding a signed record, a .git, a hard link.
    b  ODB trim: results dirs holding 6_final.odb AND 6_final.spef (> 1 KB, 6_final.odb > 6 h old): only
       5_3_fillcell.odb, 5_route.odb, 6_1_fill.odb.
    c  intermediates: results dirs holding 3_place.odb (> 1 KB, > 6 h): only 2_1..2_4 floorplan stage odbs and
       3_1..3_5 place stage odbs, plus 4_1_cts.odb where 4_cts.odb > 1 KB.  NEVER 2_floorplan.odb (kit_resume
       STEP_OUT), 3_place / 4_cts / 5_1_grt / 5_2_route / 6_final.*, signoff / LEC / spef / PROVENANCE / logs / reports.
       Class c also never trims inside a kit-wave attempt < 24 h old whose row is FAIL (or unknown) and not
       superseded: the kit wave resumes it from its last valid stage (COORD 11-08).
    Every candidate is refused when: protected (union of lanes/PROTECTED-DBS.txt + PROTECTED-DBS.txt +
    RETIRED-PROTECTION-EXTRAS.tsv + lanes/prune/ARCHIVE-PROTECTED.tsv; the 3 lists are REQUIRED, any missing/unreadable = no deletes, parent or child, under every bind-mount alias), counted (a path a SIGNED
    signoff.json / PROVENANCE.json on this host names, parent or child below lane level), kit-wave keep set,
    git alternates target, ot-run spill_pending record, wt-reaper protect.d line, named by a queue post of the
    last 25 h (path, or a row-specific dir name; with --queuename-skip-trim-c a bare name no longer blocks class c), live (/proc cmdline / cwd / open fd, docker mounts incl. stopped
    containers), hard link, git-locked worktree, .keep in the tree or an ancestor, tok-* / kv-fn-* lanes, *tool*
    trees, newer than 6 h.  Every check is repeated right before each rm; a protected / counted / kit-wave-keep
    hit at that recheck is an ALERT: ALERT file, exit 3, no further deletes (the ALERT file is sticky: later runs
    refuse until a human removes it).  A positive control (fake row deleted) and a negative control (fake
    protected row refused) run first; either failing aborts (exit 4).  Then tools/fleet/wt-reaper.py runs with the
    generated protection union (--protected-dbs <union> --protected-dbs-repo '': no git fetch on the host).
    Manifest: <state>/manifests/AUTOCLEAN-auto-<host>-<stamp>.tsv (printed as "MANIFEST <path>").

  LOCALHOST  `drive` (the only place with ~/.ssh/agidock_ot and ~/coord):
    1. snapshot: protection union + queue paths/names (last 25 h) from ~/coord, kit-wave state reduced on the
       kit-wave hub (read only) -> pushed to every host's <state>/snapshot (hosts refuse a snapshot older than 3 h);
    2. archive: per host `list-signed` (units = dirs of SIGNED / LOCAL_PASS* / resign signoff.json and
       PROVENANCE.json with signoff/, lec, PROVENANCE and the 6_final.odb/spef/abstracts they cite), streamed
       `tar | zstd -3` host -> localhost -> `unzstd | tar` on AGIdock under /archive/opentallas-signed-1106/<host>/<abs
       path> (nothing lands on localhost), verified by file count + bytes + sha256 of EVERY file on both ends, then
       ARCHIVED.json (sha list + archive path) written into the unit on the host.  Copy only: signed content is
       never deleted by this tool.  Dry unless --apply;
    3. runs `run` on each host (dry unless --apply) and collects each manifest into
       <coord>/lanes/prune/AUTOCLEAN-auto-<host>-<stamp>.tsv; --commit commits them with coord-commit.sh.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
SELF = globals().get("__file__", "ot-autoclean.py")
STATE = os.path.join(HOME, ".local/state/ot-autoclean-auto")      # not ~/.local/state/ot-autoclean (AUTOCLEAN-1 ot_autoclean.py)
TOOLS_DIR = os.path.join(HOME, ".local/share/ot-autoclean-auto")
OFF_FILES = tuple(os.environ.get("OT_AUTOCLEAN_OFF_FILES", f"{HOME}/.config/ot-autoclean/OFF:{HOME}/.config/ot-autoclean-auto/OFF").split(":"))
DEFAULT_ROOTS = ["/srv/opentallas-scratch/claude", "/srv/opentallas-scratch2/claude", "/srv/opentallas-scratch3/claude",
                 os.path.join(HOME, "scratch-root/claude")]
HOSTS = ["intel1", "intel2", "epyc2", "epyc4", "epyc7", "epyc8", "epyc9", "localhost"]   # LOCALHOST_1111 (COORD 11-11): + localhost (root md0 at 100 %, no cleaner ran there)   # AUTOCLEAN-12 11-10: + epyc7/epyc8 (COORD). KW-FIX-44 2026-11-10: epyc5/epyc6 terminated 11-09 (was + "epyc5", "epyc6")
HOSTNAME_ALIAS = {"ubuntu": "localhost", "key-cardinal": "intel1", "tolerant-swine": "intel2", "dear-crayfish": "epyc2",
                  "aware-parakeet": "epyc4", "devoted-wren": "epyc5", "eager-sunfish": "epyc6"}
AGIDOCK_SSH = "ssh -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=10 -i ~/.ssh/agidock_ot ubuntu@155.103.253.53"
ARCHIVE_ROOT = "/archive/opentallas-signed-1106"
AGE_S = 6 * 3600
# COORD 11-12 emergency hold (autoclean emptied die-hbm-92-su/ab on 3 hosts; live HBM binds named it): never deleted, any class
EMERGENCY_HOLD_RE = re.compile(r"/claude/die-hbm-[^/]+/ab(?:/|$)")      # src_* trees are held by reference (kit-wave keep + bind refs + live lane), not by name (COORD 11-12 epyc2)
CTIME_GRACE = True          # a src_* copy keeps the source's old mtimes: its inode change time says when it landed
EMERGENCY_ANC_RE = re.compile(r"/claude/die-hbm-[^/]+/ab/|/claude/[^/]+/src_[^/]+/")
GRACE_S = 2 * 3600          # --aggressive (OWNER 11-12): the only age wait, after a job ends
D_SKIP_LANES = {"autopilot", "ot-jobs", "explorer-2-work", "explorer-2", "restore-head", "signed-keep", "_ot_autoclean_ctl", "hub-coord"}
# LOCALHOST_1111: localhost holds lane and Codex trees outside the scratch roots (~/wt, ~/codex-*, ~/wt-codex-*,
# ~/scratch-codex-*); `run --host localhost` scans them too (OWNER 11-06: finished runs in Codex trees are pruned on
# localhost and fleet; 10-29: idle Codex worktrees > 12 h).  NEVER_TOUCH is refused on every host, by path and realpath.
LOCAL_EXTRA_GLOBS = [os.path.join(HOME, "wt"), os.path.join(HOME, "codex-*"), os.path.join(HOME, "wt-codex-*"),
                     os.path.join(HOME, "scratch-codex-*")]
NEVER_TOUCH_SUBSTR = ("coro-train", "OpenRealtime", "Xilinx", "closed_archive")
NEVER_TOUCH_PATHS = (os.path.join(HOME, ".codex"), os.path.join(HOME, "OpenTallas"), os.path.join(HOME, "coord"),
                     os.path.join(HOME, ".claude"))
LOCAL_WT_IDLE_H = 12.0
LOCAL_RESCUE_DIR = "/srv/opentallas-scratch/claude/rescue"   # wt-reaper default (scratch2/claude/rescue) is not writable on localhost
# DESIGN_EXPORT_1112 (EXPLORER-2; OWNER 11-12 "export before cleanup ... export to web views is the most important
# deliverable"): DEFAULT ON.  A host run HOLDS every class a attempt (finished or superseded), class b trim and class s
# stub-trim whose unit holds a routed / CTS ODB (6_final .. 4_cts) not yet in the design explorer's ledger of published
# cuts (<snapshot>/design_export.json, fleet_viz/design_export_hook.py snapshot), and prints one DXREQ line per ODB for
# the drive to enqueue.  The file names the current designs; one that names none ("all": true, or the file missing)
# holds every such ODB.  Holds only add refusals.  --design-export off (explicit) is the only way to open the gate.
DX_FILE = "design_export.json"
DX_STAGES = ["6_final", "5_3_fillcell", "5_2_route", "5_1_grt", "5_route", "6_1_fill", "4_1_cts", "4_cts"]
DX_ODB_RE = re.compile(r"/results/[^/]+/([^/]+)/(?:base/)?([0-9]_[0-9a-z_]+)\.odb$")


def dx_norm(name):
    """= design_export_hook.norm: results design dir -> plan name"""
    n = re.sub(r"^(kl|dp|hbc|hd|ds)_", "", name or "")
    n = re.sub(r"(__cl[0-9a-f]{8})+$", "", n)
    return re.sub(r"_(rt\w+|cv\w+|r\d\w*)$", "", n)


STORE_INDEX = "store.json"   # snapshot: signed-store index {sha256(signoff.json): {"archive", "locs"}} (SRCCOPY_1111)


def never_touch(p):
    """a path (or its realpath) under a never-touch tree: refused on every host, every class"""
    for q in {p, os.path.realpath(p)}:
        if any(x in q for x in NEVER_TOUCH_SUBSTR):
            return "never-touch " + q
        for t in NEVER_TOUCH_PATHS:
            if q == t or q.startswith(t + "/"):
                return "never-touch " + t
    return None


def local_extra_roots():
    import glob
    out = []
    for g in LOCAL_EXTRA_GLOBS:
        for r in sorted(glob.glob(g)):
            if os.path.isdir(r) and not os.path.islink(r) and not never_touch(r):
                out.append(r)
    return out
MIN_BYTES = 1024
WAVE_ROOT_RE = re.compile(r"/runs/[^/]+/kit-wave$")   # a kit-wave work root (protect.d/kit_wave.txt source line)
GENERATED_UNION = "protected-dbs.txt"   # protect.d copy of write_union output (wt-reaper --protected-dbs)
LANE_DEPTH = 4                     # /srv/<scratch>/claude/<lane>
TRIM_B = ("5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb")
TRIM_C = ("2_1_floorplan.odb", "2_2_floorplan_macro.odb", "2_3_floorplan_tapcell.odb", "2_4_floorplan_pdn.odb",
          "3_1_place_gp_skip_io.odb", "3_2_place_iop.odb", "3_3_place_gp.odb", "3_4_place_resized.odb",
          "3_5_place_dp.odb")                                   # + 4_1_cts.odb when 4_cts.odb > 1 KB
NEVER = {"2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "6_final.odb",
         "6_final.spef", "6_final.v", "6_final.def", "6_final.sdc", "signoff.json", "PROVENANCE.json", "ARCHIVED.json"}
RECORD_NAMES = ("signoff.json", "PROVENANCE.json")
STUB_AGE_S = 12 * 3600            # class s: every file it would delete is older than this (COORD 11-11)
STUB_MARKER = "STUBBED.json"      # class s: written at the unit root; like ARCHIVED.json it is not part of the unit's archive set
ARCHIVE_PREFIX = "/archive/opentallas-signed-1106/"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GENERIC_NAMES = {"kit", "run", "base", "results", "asap7", "src", "items", "work", "kits", "children", "child",
                 "s81_head", "kit-wave", "relocated-1106", "relocated-1106b", "signoff", "objects", "logs", "reports"}
HEAVY_DIRS = {"run", "objects", "results", "logs", "reports", "gen", "items", ".git"}
ABS_RE = re.compile(r"(?<![\w.~/])/(?:srv|home|tmp)/[^\s'\"<>|;,()\[\]{}`*?$\\]+")
REL_RE = re.compile(r"(?<![\w./-])(scratch\d*/claude/[^\s'\"<>|;,()\[\]{}`*?$\\]+)")
WORD_RE = re.compile(r"[A-Za-z0-9_.+-]{8,}")
ATTEMPT_RE = re.compile(r"^(.*/items/[^/]+)/attempt_(\d+)(?=/|$)")
ITEM_RE = re.compile(r"^(.*/items/[^/]+)(?=/|$)")
VISUAL_DIRS = ("layout_review", "geom")      # FLEET-2 11-12: judged by GEOM-REVIEW before an attempt may go
VISUAL_HOLD_S = 24 * 3600
VISUAL_EXT = (".png", ".svg", ".html", ".jpg", ".jpeg", ".gif", ".webp")
RESUME_S = 24 * 3600   # COORD 11-08: FAIL rows resume from their last valid stage
XPATH_RE = re.compile(r"/kit-wave/([^/]+)/[^/]+/items/([^/]+)/attempt_(\d+)$")   # die, item, N (plan dir ignored)
STAMP_RE = re.compile(r"(20\d\d-\d\d-\d\d) (\d\d:\d\d)(?::(\d\d))?")
ACTIVE_STATUS = {"RUN", "RUNNING", "ROUTE-HELD", "RETRY-INFRA", "PENDING-DEP", "QUEUED", "WAIT-PARENT", "PASS"}
STALE_Q_H = 12.0          # DISK-1111: terminal status + stale queue status older than this, with a later attempt, no longer holds
TERMINAL_STATUS = {"FAIL", "CANCELLED", "SUPERSEDED", "WITHDRAWN"}
ACTIVE_Q = {"RUNNING", "QUEUED", "WAIT-PARENT"}
TERMINAL_Q = {"FAIL", "CANCELLED", "WITHDRAWN"}
ALERT_HITS = ("protected", "counted", "kitwave-keep", "signed")


def say(*a):
    print(*a, flush=True)


def now_s():
    return time.time()


def stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def rd(p, errors="replace"):
    with open(p, errors=errors) as fh:
        return fh.read()


def jl(p):
    with open(p) as fh:
        return json.load(fh)


def depth(p):
    return len([c for c in p.split("/") if c])


def ancestors(p):
    out = []
    while True:
        q = os.path.dirname(p)
        if q == p or not q:
            return out
        out.append(q)
        p = q


def clean_path(p):
    p = p.rstrip(".:,;'\")]}")
    return os.path.normpath(p) if p.startswith("/") else None


def text_paths(s):
    """absolute /srv|/home paths and 'scratchN/claude/...' relative forms named in a text"""
    out = set()
    for m in ABS_RE.findall(s):
        p = clean_path(m)
        if p:
            out.add(p)
    for m in REL_RE.findall(s):
        p = clean_path("/srv/opentallas-" + m)
        if p:
            out.add(p)
    return out


# ------------------------------------------------------------------ aliases (bind mounts with a [subpath])
def parse_findmnt(text):
    """[(alias_prefix, canonical_prefix)] for bind mounts: TARGET is canonical, <mountpoint of SOURCE dev> +
    subpath is the alias (epyc5/6: /srv/opentallas-scratch3 = /dev/md0[/home/ubuntu/scratch-root], md0 on /)"""
    rows = []
    for ln in text.splitlines():
        parts = ln.split(" ", 1)
        if len(parts) != 2:
            continue
        t, src = parts[0].replace("\\x20", " "), parts[1].strip()
        rows.append((t, src))
    plain = {}
    for t, src in rows:
        if "[" not in src:
            plain.setdefault(src, []).append(t)
    out = []
    for t, src in rows:
        m = re.fullmatch(r"(/dev/[^\[]+)\[(/[^\]]*)\]", src)
        if not m:
            continue
        dev, sub = m.groups()
        for mp in plain.get(dev, []):
            alias = os.path.normpath(mp.rstrip("/") + sub)
            if alias != t:
                out.append((alias, os.path.normpath(t)))
    return out


def host_aliases():
    try:
        r = subprocess.run(["findmnt", "-rn", "-o", "TARGET,SOURCE"], capture_output=True, text=True, timeout=60)
        out = parse_findmnt(r.stdout) if r.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        out = []
    for root in DEFAULT_ROOTS:   # symlinked roots are aliases of their target too
        if os.path.islink(root):
            out.append((os.path.normpath(root), os.path.realpath(root)))
    return out


class Paths:
    """canonical form + all alias forms of paths"""

    def __init__(self, aliases, resolve=True):
        self.aliases = list(aliases)
        self.resolve = resolve
        self._real = {}

    def _alias(self, p):
        for a, c in self.aliases:
            if p == a or p.startswith(a + "/"):
                return c + p[len(a):]
        return p

    def _realprefix(self, p):
        """symlinks resolved on the longest existing prefix (lane dirs are symlinked between scratch disks:
        11-07 INCIDENT, kit-wave keep paths named one side, the scan found the other)"""
        head, tail = p, ""
        while head not in self._real:
            if os.path.lexists(head) or head == "/":
                self._real[head] = os.path.realpath(head)
                break
            head, t = os.path.split(head)
            tail = "/" + t + tail
            if not head:
                return p
        return self._real[head] + tail

    def canon(self, p):
        p = self._alias(os.path.normpath(p))
        if self.resolve and p.startswith("/"):
            p = self._alias(os.path.normpath(self._realprefix(p)))
        return p

    def forms(self, p):
        c = self.canon(p)
        out = {c, os.path.normpath(p)}
        for a, t in self.aliases:
            if c == t or c.startswith(t + "/"):
                out.add(a + c[len(t):])
        return out


class PathSet:
    """members; hit(p): p equals a member, is an ancestor of one, or lies under a member for which deep(member)
    holds (default: any member; citations / queue paths: only members below lane level)"""

    def __init__(self, paths=(), deep=None, canon=lambda p: p):
        self.canon = canon
        self.deep = deep or (lambda p: True)
        self.m = {}
        self.anc = {}
        for p, why in paths:
            self.add(p, why)

    def add(self, p, why=""):
        c = self.canon(os.path.normpath(p))
        if c in self.m:
            return
        self.m[c] = why
        for a in ancestors(c):
            self.anc.setdefault(a, c)

    def hit(self, p):
        c = self.canon(os.path.normpath(p))
        if c in self.m:
            return f"{c} ({self.m[c]})"
        if c in self.anc:
            q = self.anc[c]
            return f"holds {q} ({self.m[q]})"
        for a in ancestors(c):
            if a in self.m and self.deep(a):
                return f"inside {a} ({self.m[a]})"
        return None

    def __len__(self):
        return len(self.m)


# ------------------------------------------------------------------ protection union
def parse_protected(text, source):
    """rows of a PROTECTED-DBS style file: host<TAB|SPACE>path<...>; every path-like token is kept"""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        for tok in re.split(r"[\t ]+", s):
            tok = re.sub(r"^[\w.-]+:(?=/)", "", tok)        # host:/path
            if tok.startswith("/"):
                p = clean_path(tok)
            elif re.match(r"scratch\d*/claude/", tok):
                p = clean_path("/srv/opentallas-" + tok)
            else:
                continue
            if p and depth(p) >= 2:
                out.append((p, source))
    return out


REQUIRED_PROTECTED = ("lanes/PROTECTED-DBS.txt", "PROTECTED-DBS.txt", "lanes/prune/ARCHIVE-PROTECTED.tsv")
OPTIONAL_PROTECTED = ("lanes/RETIRED-PROTECTION-EXTRAS.tsv",)
REFUSE_LOG = os.path.join(HOME, ".local/state/ot-autoclean-auto/PROTECTED-LISTS-REFUSED.log")


def refuse_lists(msg):
    """a required protected list is missing / unreadable / empty: delete nothing, log loudly (COORD 2026-11-10, AUTOCLEAN-12)"""
    line = f"{time.strftime('%F %T %Z')} {socket.gethostname()} ot-autoclean REFUSING, NOTHING DELETED: {msg}"
    print("!!! " + line, file=sys.stderr, flush=True)
    try:
        os.makedirs(os.path.dirname(REFUSE_LOG), exist_ok=True)
        with open(REFUSE_LOG, "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    raise RuntimeError(line)


def protected_sources(coord):
    """the three protected lists are REQUIRED (COORD 2026-11-10: any missing or unreadable -> delete nothing, log loudly):
    lanes/PROTECTED-DBS.txt, PROTECTED-DBS.txt, lanes/prune/ARCHIVE-PROTECTED.tsv (AUTOCLEAN-1 11-06: asbuilt/bind inputs
    named by signed records, kit_wave live inputs; AUTOCLEAN-13: 8 rows under it were deleted on 11-10 because the union
    did not read it).  RETIRED-PROTECTION-EXTRAS.tsv stays optional."""
    return [os.path.join(coord, f) for f in REQUIRED_PROTECTED + OPTIONAL_PROTECTED]


def build_protected_union(coord):
    rows = []
    for f in protected_sources(coord):
        rel = os.path.relpath(f, coord)
        req = rel in REQUIRED_PROTECTED
        try:
            with open(f, errors="strict") as fh:
                got = parse_protected(fh.read(), rel)
        except FileNotFoundError:
            if req:
                refuse_lists(f"required protected list missing: {f}")
            continue
        except (OSError, UnicodeDecodeError) as e:
            if req:
                refuse_lists(f"required protected list unreadable: {f}: {e}")
            continue
        if req and not got:
            refuse_lists(f"required protected list has no path rows: {f}")
        rows += got
    return rows


def check_required_sources(rows, what):
    """every required list must have contributed rows (the snapshot names each row's source list)"""
    srcs = {w for _, w in rows}
    miss = [r for r in REQUIRED_PROTECTED if r not in srcs]
    if miss:
        refuse_lists(f"{what} has no rows from required protected list(s) {', '.join(miss)}")


# ------------------------------------------------------------------ queue posts
def parse_queue(text, now, hours=25.0, tz="America/Los_Angeles"):
    """(paths, words) named by posts whose header time is within the last `hours` (continuation lines included)"""
    try:
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(tz)
    except Exception:
        zone = None
    import datetime
    lo = now - hours * 3600
    paths, words = set(), set()
    cur = False
    for ln in text.splitlines():
        if ln[:1] and not ln[:1].isspace():
            m = STAMP_RE.search(ln[:80])
            if m:
                try:
                    dt = datetime.datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3) or '00'}", "%Y-%m-%d %H:%M:%S")
                    t = dt.replace(tzinfo=zone).timestamp() if zone else time.mktime(dt.timetuple())
                    cur = t >= lo
                except ValueError:
                    cur = True
        if not cur:
            continue
        paths |= text_paths(ln)
        words |= {w.rstrip(".") for w in WORD_RE.findall(ln)}
    return paths, words


def generic_name(n):
    return (len(n) < 8 or n in GENERIC_NAMES or n.startswith("attempt") or re.fullmatch(r"[0-9a-f]{10,}", n) is not None
            or n.startswith("qwen_") or "wave-" in n or n == "flow-canary" or n.startswith("_ot_autoclean")
            or n.startswith("opentallas-scratch") or n == "scratch-root")   # mount names inside nested paths


# ------------------------------------------------------------------ kit-wave state reduction (runs on the hub)
def _host_path(s, default_host=""):
    if not isinstance(s, str):
        return None
    m = re.match(r"^([\w.-]+):(/.*)$", s)
    if m:
        return m.group(1), os.path.normpath(m.group(2))
    if s.startswith("/"):
        return default_host, os.path.normpath(s)
    return None


def _json_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _json_strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _json_strings(x)


def rec_active(r):
    st, q = r.get("status"), r.get("q_status")
    if q in ACTIVE_Q:
        return True
    if st in ACTIVE_STATUS or (st == "PASS" and r.get("enqueue_pending")):
        return True
    if st == "ENQUEUED":
        return q not in TERMINAL_Q and q != "SIGNED"
    return st not in TERMINAL_STATUS          # unknown status: keep (fail safe)


def rec_signed(r):
    return r.get("q_status") == "SIGNED" or r.get("status") == "SIGNED"


def reduce_kitwave(state, stage_rows, read_spec=None):
    """compact snapshot: attempts {"host:dir": {"active","signed","terminal":[..]}}, latest {"host:items/x": N},
    keep ["host:path"] (every path of an active record + its spec.json src/plan/queue_src)."""
    attempts, latest, keep, current_di = {}, {}, set(), {}
    newest_att = {}                           # DISK-1111: newest attempt number per die|item|event path, for the stale-queue rule
    now_s = time.time()
    for rec in (state.get("items") or {}).values():
        if isinstance(rec, dict):
            hp0 = _host_path(rec.get("kit") or rec.get("evidence") or rec.get("geom_dir"))
            m0 = ATTEMPT_RE.match(hp0[1]) if hp0 else None
            if m0:
                kk = f"{hp0[0]}:{m0.group(1)}"
                newest_att[kk] = max(newest_att.get(kk, -1), int(m0.group(2)))

    def stale_queue(rec, hp):
        """status is already terminal (FAIL / CANCELLED / SUPERSEDED / WITHDRAWN) but q_status still says RUNNING / QUEUED /
        WAIT-PARENT (a queue row nobody updated), the record is older than STALE_Q_H and a LATER attempt of the item exists:
        it does not hold the attempt (203 CANCELLED/RUNNING rows kept old waves for ever).  The newest attempt, a young
        record and any non-terminal status keep the old behaviour."""
        if rec.get("status") not in TERMINAL_STATUS or rec.get("q_status") not in ACTIVE_Q or not hp:
            return False
        m1 = ATTEMPT_RE.match(hp[1])
        try:
            upd = float(rec.get("updated") or 0)
        except (TypeError, ValueError):
            return False
        return bool(m1) and now_s - upd >= STALE_Q_H * 3600 and int(m1.group(2)) < newest_att.get(f"{hp[0]}:{m1.group(1)}", -1)

    def att(hp):
        m = ATTEMPT_RE.match(hp[1])
        if not m:
            return None
        key = f"{hp[0]}:{m.group(1)}"
        latest[key] = max(latest.get(key, -1), int(m.group(2)))
        return f"{hp[0]}:{m.group(1)}/attempt_{m.group(2)}"

    def slot(a):
        return attempts.setdefault(a, {"active": False, "signed": False, "terminal": []})

    for rec in (state.get("items") or {}).values():
        if not isinstance(rec, dict):
            continue
        own = None
        for k in ("kit", "evidence", "geom_dir"):
            hp = _host_path(rec.get(k))
            if hp and hp[0]:
                own = hp
                break
        host = own[0] if own else ""
        for s in _json_strings(rec):              # register every attempt the record names (latest numbers)
            hp = _host_path(s, host)
            if hp and hp[0]:
                att(hp)
        a = att(own) if own else None
        active, signed = rec_active(rec), rec_signed(rec)
        if active and stale_queue(rec, own):
            active = False
        xm = XPATH_RE.search(a.partition(":")[2]) if a else None
        if xm:                                    # the state's current attempt of die|item, whatever plan dir
            k = f"{xm.group(1)}|{xm.group(2)}"
            current_di[k] = max(current_di.get(k, -1), int(xm.group(3)))
        if a:
            sl = slot(a)
            sl["active"] |= active
            sl["signed"] |= signed
            if not active and not signed:
                sl["terminal"].append(f"{rec.get('status')}/{rec.get('q_status')}")
        if active or signed:
            own_att = ATTEMPT_RE.match(own[1]).group(0) if own and ATTEMPT_RE.match(own[1]) else None
            queued = rec.get("status") in ("QUEUED", "PENDING-DEP", "WAIT-PARENT", "RETRY-INFRA", "ENQUEUED") or rec.get("q_status") in ("QUEUED", "WAIT-PARENT")
            for s in _json_strings(rec):
                hp = _host_path(s, host)
                if hp and hp[0]:
                    ma = ATTEMPT_RE.match(hp[1])
                    if ma and own_att and ma.group(0) != own_att and not queued:   # OWNER 11-12: a RUNNING row's job is self contained; only a QUEUED row still copies from other trees
                        continue
                    keep.add(f"{hp[0]}:{hp[1]}")
            spec = read_spec(rec.get("dir")) if read_spec and rec.get("dir") else {}
            for f in ("src", "plan", "queue_src"):
                hp = _host_path(spec.get(f), spec.get("host") or host) if isinstance(spec, dict) else None
                if hp and hp[0]:
                    keep.add(f"{hp[0]}:{hp[1]}")
    for row in stage_rows:
        hp = _host_path(row.get("kit"))
        if not hp or not hp[0]:
            continue
        a = att(hp)
        st, cl = row.get("status", ""), row.get("class", "")
        signed = st == "SIGNED" or cl == "COUNTED"
        active = not signed and st not in TERMINAL_STATUS
        if a:
            sl = slot(a)
            sl["signed"] |= signed
            sl["active"] |= active
            if not signed and not active:
                sl["terminal"].append(f"stage:{st}")
        if signed or active:
            keep.add(f"{hp[0]}:{hp[1]}")
    return {"attempts": attempts, "latest": latest, "keep": sorted(keep), "current_di": current_di}


def kitwave_reduce_main(a):
    import csv
    state = jl(a.state_json)
    rows = []
    try:
        with open(a.stages_tsv, newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
    except FileNotFoundError:
        pass

    def read_spec(d):
        try:
            return jl(os.path.join(d, "spec.json"))
        except (OSError, ValueError):
            return {}
    out = reduce_kitwave(state, rows, read_spec)
    out["created"] = now_s()
    out["source"] = f"{socket.gethostname()}:{a.state_json} mtime {int(os.path.getmtime(a.state_json))}"
    json.dump(out, sys.stdout)
    return 0


# ------------------------------------------------------------------ live use
class Live:
    def __init__(self, docker="docker", deep=lambda p: depth(p) > LANE_DEPTH):
        self.docker = docker
        self.deep = deep
        self.refresh()

    def refresh(self):
        me = os.getpid()
        self.cmds, self.cwds, self.fds, self.mounts = [], [], [], []
        for d in os.listdir("/proc"):
            if not d.isdigit() or int(d) == me:
                continue
            try:
                with open(f"/proc/{d}/cmdline", "rb") as fh:
                    self.cmds.append(fh.read().replace(b"\0", b" ").decode(errors="replace"))
            except OSError:
                pass
            try:
                self.cwds.append(os.readlink(f"/proc/{d}/cwd"))
            except OSError:
                pass
            try:
                for f in os.listdir(f"/proc/{d}/fd"):
                    try:
                        self.fds.append(os.readlink(f"/proc/{d}/fd/{f}"))
                    except OSError:
                        pass
            except OSError:
                pass
        if self.docker:
            dk = shlex.split(self.docker)
            try:
                q = subprocess.run(dk + ["ps", "-aq"], capture_output=True, text=True, timeout=120)
            except (OSError, subprocess.TimeoutExpired) as e:
                raise RuntimeError(f"docker ps failed: {e}")
            if q.returncode:
                raise RuntimeError(f"docker ps failed: {q.stderr.strip()[:200]}")
            ids = q.stdout.split()
            if ids:
                m = subprocess.run(dk + ["inspect", "-f", "{{range .Mounts}}{{.Source}} {{end}}"] + ids,
                                   capture_output=True, text=True, timeout=300)
                if m.returncode:
                    # a container removed between ps and inspect has no mounts: only that error is tolerated
                    errs = [ln for ln in m.stderr.splitlines() if ln.strip()]
                    if not errs or any("no such object" not in ln.lower() for ln in errs):
                        raise RuntimeError(f"docker inspect failed: {m.stderr.strip()[:200]}")
                self.mounts = [os.path.normpath(x) for x in m.stdout.split()]
        return self

    def why(self, forms):
        for k in forms:
            pre = k + "/"
            pat = re.compile(re.escape(k) + r"(?=$|[/\s'\";:,)=])")
            for c in self.cmds:
                if k in c and pat.search(c):
                    return "live cmdline: " + c[:120]
            for c in self.cwds:
                c = c.split(" (deleted)")[0]
                if c == k or c.startswith(pre) or (k.startswith(c + "/") and self.deep(c)):
                    return "live cwd " + c
            for f in self.fds:
                if f == k or f.startswith(pre):
                    return "live fd " + f
            for m in self.mounts:
                if m == k or m.startswith(pre) or (k.startswith(m + "/") and self.deep(m)):
                    return "docker mount " + m
        return None


# ------------------------------------------------------------------ scan
def scan_roots(roots, timeout=3600):
    """one find per root: attempt dirs, results-dir anchors, records, .keep, .git entries.  None on failure."""
    found = {"attempt": [], "spef": [], "place": [], "record": [], "keep": [], "git": [], "archived": []}
    for r in roots:
        cmd = ["nice", "-n", "15", "find", r, "-xdev",
               "(", "-name", ".git", "-prune", "-printf", "g\t%p\n", ")", "-o",
               "(", "-type", "d", "-name", "attempt_[0-9]*", "-printf", "a\t%p\n", ")", "-o",
               "(", "-type", "f", "(", "-name", "6_final.spef", "-o", "-name", "3_place.odb", "-o", "-name", "signoff.json",
               "-o", "-name", "*.signoff.json", "-o", "-name", "PROVENANCE.json", "-o", "-name", ".keep", "-o",
               "-name", "ARCHIVED.json", ")", "-printf", "f\t%p\n", ")"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        except subprocess.TimeoutExpired:
            return None
        if p.returncode not in (0, 1):
            return None
        for ln in p.stdout.splitlines():
            k, _, path = ln.partition("\t")
            b = os.path.basename(path)
            if k == "g":
                found["git"].append(path)
            elif k == "a":
                found["attempt"].append(path)
            elif b == "6_final.spef":
                found["spef"].append(path)
            elif b == "3_place.odb":
                found["place"].append(path)
            elif b == ".keep":
                found["keep"].append(path)
            elif b == "ARCHIVED.json":
                found["archived"].append(path)
            else:
                found["record"].append(path)
    return found


def write_store_index(coord, out):
    """SRCCOPY_1111: {id: {"archive": dir, "locs": [host:path, ...]}} of every signed-store entry (id = sha256 of signoff.json).
    Missing / unreadable store -> no file (hosts then exempt nothing)."""
    import glob
    import gzip
    rec = os.path.join(coord, "signed-store", "records")
    idx = {}
    try:
        for f in glob.glob(os.path.join(rec, "*", "*.json.gz")):
            with gzip.open(f, "rt") as fh:
                e = json.load(fh)
            v = str(e.get("verdict") or "")
            if e.get("id") and (v == "SIGNED" or v.startswith("LOCAL_PASS")):
                idx[e["id"]] = {"archive": e.get("archive") or "", "locs": [x for x in [e.get("origin")] + list(e.get("aliases") or []) if x]}
    except (OSError, ValueError):
        return 0
    if not idx:
        return 0
    tmp = out + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(idx, fh)
    os.replace(tmp, out)
    return len(idx)


def _git(top, *args, timeout=120):
    return subprocess.run(["git", "-C", top] + list(args), capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0"))


class SourceCopy:
    """SRCCOPY_1111 (COORD 11-11): a signed record is a SOURCE COPY (restorable from git, not a counted unit) only when ALL hold:
      1. it is signoff.json inside a git checkout, tracked, and its record dir matches HEAD exactly (no modified, staged,
         untracked or ignored file in the dir: git status --porcelain --ignored empty, git diff-index HEAD clean);
      2. HEAD is an ancestor of a branch head origin has now (git ls-remote), after a fresh `git fetch origin` in THIS run;
      3. its canonical copy is in the signed store (snapshot store.json, id = sha256 of the file) with an AGIdock archive dir,
         and no store location of it lies inside this checkout;
      4. every path the record names that lies inside the checkout is tracked and matches HEAD (named paths outside stay counted).
    Any error, timeout or doubt = not a source copy (the record stays counted)."""

    def __init__(self, store_file, host, fetch_timeout=600):
        self.host = host
        self.fetch_timeout = fetch_timeout
        self.fetched = {}
        self.onorigin = {}
        try:
            self.store = jl(store_file) if store_file and os.path.exists(store_file) else None
        except (OSError, ValueError):
            self.store = None

    def _top(self, d):
        r = _git(d, "rev-parse", "--show-toplevel", "--git-common-dir")
        if r.returncode:
            return None, None
        top, common = r.stdout.splitlines()[:2]
        return os.path.realpath(top), os.path.realpath(os.path.join(top, common))

    def _fetched(self, top, common):
        if common not in self.fetched:
            try:
                r = _git(top, "fetch", "--quiet", "--no-write-fetch-head", "origin", timeout=self.fetch_timeout)
                self.fetched[common] = r.returncode == 0
            except subprocess.TimeoutExpired:
                self.fetched[common] = False
        return self.fetched[common]

    def _on_origin(self, top, common, head):
        """HEAD is an ancestor of a branch head origin has NOW (git ls-remote, not the cached remote-tracking refs)"""
        key = (common, head)
        if key not in self.onorigin:
            ok = False
            try:
                r = _git(top, "ls-remote", "--heads", "origin", timeout=self.fetch_timeout)
                if r.returncode == 0:
                    live = {ln.split()[0] for ln in r.stdout.splitlines() if ln.strip()}
                    # one walk (the fetch above refreshed refs/remotes/origin): the remote-tracking heads that contain HEAD,
                    # kept only where origin still has that exact sha now (ls-remote); a pruned or moved branch never counts
                    c = _git(top, "for-each-ref", "--contains", head, "--format=%(objectname)", "refs/remotes/origin",
                             timeout=self.fetch_timeout)
                    ok = head in live or (c.returncode == 0 and bool(live & set(c.stdout.split())))
            except subprocess.TimeoutExpired:
                ok = False
            self.onorigin[key] = ok
        return self.onorigin[key]

    def check(self, rec, text):
        """None if rec is a source copy, else the reason it stays counted"""
        try:
            return self._check(rec, text)
        except Exception as e:      # any doubt keeps it counted
            return f"error {type(e).__name__}"

    def _check(self, rec, text):
        if self.store is None:
            return "no signed-store index"
        if os.path.basename(rec) != "signoff.json":
            return "not signoff.json"
        d = os.path.dirname(rec)
        top, common = self._top(d)
        if not top:
            return "not in a git checkout"
        rr = os.path.realpath(rec)
        if not rr.startswith(top + "/"):
            return "outside its checkout"
        rel_dir = os.path.relpath(os.path.realpath(d), top)
        rel = os.path.relpath(rr, top)
        with open(rr, "rb") as fh:                   # the cheap store test first: most records end here
            sha = hashlib.sha256(fh.read()).hexdigest()
        e = self.store.get(sha)
        if not e:
            return "not in signed store"
        if not str(e.get("archive", "")).startswith("/archive/"):
            return "store entry has no AGIdock archive"
        if _git(top, "ls-files", "--error-unmatch", "--", rel).returncode:
            return "untracked"
        st = _git(top, "status", "--porcelain", "--ignored", "--untracked-files=all", "--", rel_dir)
        if st.returncode or st.stdout.strip():
            return "record dir differs from HEAD"
        if _git(top, "diff-index", "--quiet", "HEAD", "--", rel_dir).returncode:
            return "diff-index not clean"
        if not self._fetched(top, common):
            return "fetch origin failed"
        head = _git(top, "rev-parse", "HEAD").stdout.strip()
        if not self._on_origin(top, common, head):
            return "HEAD not on origin"
        for loc in e.get("locs", []):
            pth = loc.partition(":")[2] if ":" in loc and not loc.startswith("/") else loc
            for q in {pth, os.path.realpath(pth)}:
                if q == top or q.startswith(top + "/"):
                    return "store location inside this checkout"
        named_in = sorted({os.path.relpath(os.path.realpath(x), top) for x in text_paths(text)
                           if os.path.realpath(x).startswith(top + "/")})
        for i in range(0, len(named_in), 200):
            chunk = named_in[i:i + 200]
            tracked = set(_git(top, "ls-files", "--", *chunk).stdout.splitlines())
            for x in chunk:
                if os.path.isdir(os.path.join(top, x)):
                    continue
                if os.path.lexists(os.path.join(top, x)) and x not in tracked:
                    return "names an untracked path in the checkout: " + x
            st = _git(top, "status", "--porcelain", "--ignored", "--untracked-files=all", "--", *chunk)
            if st.returncode or st.stdout.strip():
                return "a named path differs from HEAD"
        self.top_of = getattr(self, "top_of", {})
        self.top_of[rec] = top
        return None


def read_record(p):
    """(signed?, text) of a signoff.json / PROVENANCE.json; unreadable or unparsable counts as signed (fail safe)"""
    try:
        if os.path.getsize(p) > (8 << 20):
            return True, ""
        s = rd(p)
        d = json.loads(s)
    except (OSError, ValueError):
        return True, ""
    if not isinstance(d, dict):
        return False, s
    v = d.get("verdict")
    signed = (isinstance(v, str) and (v == "SIGNED" or v.startswith("LOCAL_PASS"))) or d.get("kind") == "resign"
    return signed, s


NEVER_TOUCH_SUBSTR = ("coro-train", "OpenRealtime", "Xilinx", "closed_archive")
NEVER_TOUCH_PATHS = (os.path.join(HOME, ".codex"), os.path.join(HOME, "OpenTallas"), os.path.join(HOME, "coord"),
                     os.path.join(HOME, ".claude"))


def never_touch(p):
    """a path (or its realpath) under a never-touch tree: refused by class s on every host"""
    for q in {p, os.path.realpath(p)}:
        if any(x in q for x in NEVER_TOUCH_SUBSTR):
            return "never-touch " + q
        for t_ in NEVER_TOUCH_PATHS:
            if q == t_ or q.startswith(t_ + "/"):
                return "never-touch " + t_
    return None


def dedupe_roots(roots):
    seen, out = set(), []
    for r in roots:
        try:
            st = os.stat(r)
        except OSError:
            continue
        if (st.st_dev, st.st_ino) in seen:
            continue
        seen.add((st.st_dev, st.st_ino))
        out.append(os.path.realpath(r))   # a symlinked root (epyc6 /srv/opentallas-scratch/claude -> scratch2) is scanned by its target
    return out


def alternates_targets(git_entries):
    out = set()
    for g in git_entries + [os.path.join(HOME, "OpenTallas/.git")]:
        gd = g
        if os.path.isfile(g):
            try:
                gd = rd(g).split("gitdir:", 1)[1].strip()
                cd = os.path.join(gd, "commondir")
                if os.path.isfile(cd):
                    gd = os.path.normpath(os.path.join(gd, rd(cd).strip()))
            except (OSError, IndexError):
                continue
        f = os.path.join(gd, "objects/info/alternates")
        try:
            for ln in rd(f).splitlines():
                ln = ln.strip()
                if ln.startswith("/"):
                    t = os.path.normpath(ln)
                    out.add(os.path.dirname(t) if t.endswith("/objects") else t)
        except OSError:
            pass
    return out


def git_locked(path, stop_depth=3):
    a = path
    while depth(a) > stop_depth:
        g = os.path.join(a, ".git")
        if os.path.isfile(g):
            try:
                gd = rd(g).split("gitdir:", 1)[1].strip()
                if os.path.exists(os.path.join(gd, "locked")):
                    return g
            except (OSError, IndexError):
                return g
        a = os.path.dirname(a)
    return None


def tree_info(d):
    """(newest mtime, bytes, nlink>1 file or None)"""
    newest, size, hl = os.lstat(d).st_mtime, 0, None
    for dp, dns, fns in os.walk(d):
        for n in dns + fns:
            try:
                st = os.lstat(os.path.join(dp, n))
            except OSError:
                continue
            newest = max(newest, st.st_mtime)
            if stat.S_ISREG(st.st_mode):
                size += st.st_blocks * 512
                if st.st_nlink > 1 and hl is None:
                    hl = os.path.join(dp, n)
    return newest, size, hl


_TI = {}


def tree_info_c(d):
    """tree_info cached for this run: the same tree was walked three times (eval, size, delete)"""
    if d not in _TI:
        _TI[d] = tree_info(d)
    return _TI[d]


# ------------------------------------------------------------------ the host job
class Job:
    def __init__(self, a):
        self.a = a
        self.host = a.host or HOSTNAME_ALIAS.get(socket.gethostname(), socket.gethostname())
        self.paths = Paths(host_aliases() if a.aliases is None else parse_findmnt(rd(a.aliases)))
        self.now = now_s()
        self.rows = []
        self.alerts = []
        self.recheck_hits = 0

    # ---- inputs
    def load_snapshot(self):
        a, snap = self.a, self.a.snapshot
        meta = jl(os.path.join(snap, "meta.json"))
        age = self.now - float(meta["created"])
        if age > a.max_snapshot_age_h * 3600:
            raise RuntimeError(f"snapshot {snap} is {age / 3600:.1f} h old (> {a.max_snapshot_age_h} h)")
        self.snapshot_meta = meta
        self.prot_file = os.path.join(snap, "protected.tsv")
        self.load_protected()
        q = jl(os.path.join(snap, "queue.json"))
        self.queue = PathSet([(p, "queue post") for p in q["paths"]], deep=self.deep, canon=self.paths.canon)
        self.qwords = set(q["words"])
        vh = os.path.join(snap, "visual_hold.txt")
        self.visual_names = None
        if os.path.exists(vh):
            with open(vh) as fh:
                self.visual_names = {self.paths.canon(x.strip()) if x.strip().startswith("/") else x.strip()
                                     for x in fh if x.strip() and not x.startswith("#")}
        kw = os.path.join(snap, "kitwave.json")
        self.kitwave = None
        if os.path.exists(kw):
            k = jl(kw)
            self.kitwave = k
            # match on PATH, any host: a row's kit host may be "localhost" (= the hub) and ran_on copies share
            # the path on another host; active / signed / keep from any host therefore protect it here too
            self.kw_attempts = {}
            for key, v in k["attempts"].items():
                c = self.paths.canon(key.partition(":")[2])
                o = self.kw_attempts.setdefault(c, {"active": False, "signed": False, "terminal": []})
                o["active"] |= bool(v.get("active"))
                o["signed"] |= bool(v.get("signed"))
                o["terminal"] = o["terminal"] + list(v.get("terminal") or [])
            self.kw_latest = {}
            for key, n in k["latest"].items():
                c = self.paths.canon(key.partition(":")[2])
                self.kw_latest[c] = max(self.kw_latest.get(c, -1), n)
            self.kw_current_di = dict(k.get("current_di") or {})
            self.kwkeep = PathSet([(key.partition(":")[2], "kit-wave active/resume/spec") for key in k["keep"]],
                                  canon=self.paths.canon)
        else:
            self.kwkeep = PathSet()
        self.add_bind_refs()
        self.dx, self.dx_sent = None, set()
        if getattr(a, "design_export", "on") != "off":
            dxf = os.path.join(snap, DX_FILE)
            d = jl(dxf) if os.path.exists(dxf) else {"all": True, "ledger": []}   # no gate file: hold every routed DB
            names = None if d.get("all") or d.get("names") is None else set(d["names"])
            self.dx = dict(ledger=set(d.get("ledger") or []), paths=set(d.get("ledger_paths") or []), names=names,
                           stages=list(DX_STAGES))

    BIND_NAME_RE = re.compile(r"(^bind.*\.f$|\.f$|^manifest.*\.json$|^plan.*\.json$|^filelist.*|^spec\.json$|^config\.mk$|\.mk$|^cmd\.sh$|^run_kit\.sh$)")

    def add_bind_refs(self):
        """COORD 11-12 (autoclean emptied die-hbm-92-su/ab, named only by bind.f): parse every bind.f / filelist / manifest / plan /
        spec of each kit-wave keep path (live or queued rows) and keep every path they name plus its parent dir"""
        if not len(self.kwkeep):
            return
        files, seen = [], set()
        for p in list(self.kwkeep.m):
            if os.path.isfile(p):
                files.append(p)
            elif os.path.isdir(p):
                stack, n = [(p, 0)], 0
                while stack and n < 400:
                    d, dep = stack.pop()
                    try:
                        ents = list(os.scandir(d))
                    except OSError:
                        continue
                    for e in ents:
                        try:
                            if e.is_symlink():
                                continue
                            if e.is_dir(follow_symlinks=False):
                                if dep < 3 and e.name not in HEAVY_DIRS and e.name not in ("results", "run", "logs", "objects", "reports"):
                                    stack.append((e.path, dep + 1))
                            elif self.BIND_NAME_RE.search(e.name):
                                files.append(e.path)
                                n += 1
                        except OSError:
                            pass
        added = 0
        for f in files:
            if f in seen:
                continue
            seen.add(f)
            try:
                if os.path.getsize(f) > (8 << 20):
                    continue
                txt = rd(f)
            except OSError:
                continue
            for q in text_paths(txt):
                if os.path.exists(q):
                    for r_ in {q, os.path.dirname(q)}:
                        if r_.count("/") >= 4:
                            self.kwkeep.add(r_, "bind/filelist ref from " + f)
                            added += 1
        say(f"kit-wave keep: {len(files)} bind/filelist/manifest files parsed, {added} referenced paths added")

    def signed_near(self, unit):
        """DISK-1111 (OWNER 11-12 "routing results should be exported only if it is signed"): the unit, something below it or
        its enclosing kit holds a signed record (signoff.json / PROVENANCE.json read as SIGNED or LOCAL_PASS)."""
        recs = [r for r in self.found.get("record", []) if r.startswith(unit + "/")]
        a = unit
        for _ in range(6):
            for n in ("signoff/signoff.json", "signoff.json", "PROVENANCE.json"):
                q = os.path.join(a, n)
                if os.path.exists(q):
                    recs.append(q)
            a = os.path.dirname(a)
            if a.count("/") < LANE_DEPTH:
                break
        return any(read_record(r)[0] for r in recs)

    def dx_hold(self, unit, kind="newest"):
        """DESIGN_EXPORT_1112: None, or why the unit is held until the design explorer has cut its routed ODB(s)"""
        if not self.dx or "/_ot_autoclean_ctl/" in unit + "/":   # the run's own control fixture is never a design
            return None
        if not self.signed_near(unit):                            # OWNER 11-12: only SIGNED routed DBs are exported; unsigned / failed need no cut
            return None
        best = {}
        for dp, dn, fn in os.walk(unit):
            for f in fn:
                m = DX_ODB_RE.search(os.path.join(dp, f))
                if not m or m.group(2) not in self.dx["stages"]:
                    continue
                if self.dx["names"] is not None and dx_norm(m.group(1)) not in self.dx["names"]:
                    continue
                k, rank = os.path.dirname(os.path.join(dp, f)), self.dx["stages"].index(m.group(2))
                if k not in best or rank < best[k][0]:
                    best[k] = (rank, os.path.join(dp, f), m.group(1), m.group(2))
        pend = []
        for _r, f, design, stage in best.values():
            label = f"{self.host}:{f}"
            if label in self.dx["ledger"] or f in self.dx["paths"] or os.path.realpath(f) in self.dx["paths"]:
                continue
            pend.append(f)
            if label not in self.dx_sent:
                self.dx_sent.add(label)
                say(f"DXREQ\t{label}\t{dx_norm(design)}\t{stage}\t{kind}")
        return f"design-export pending ({len(pend)} ODB): {pend[0]}" if pend else None

    def load_protected(self):
        rows = []
        try:
            txt = rd(self.prot_file)
        except OSError as e:
            refuse_lists(f"protection union {self.prot_file} unreadable: {e}")
        for ln in txt.splitlines():
            p, _, src = ln.rstrip("\n").partition("\t")
            if p.startswith("/"):
                rows.append((p, src))
        if len(rows) < self.a.min_protected:
            refuse_lists(f"protection union {self.prot_file} has {len(rows)} rows (< {self.a.min_protected})")
        check_required_sources(rows, f"protection union {self.prot_file}")
        self.protected = PathSet(rows, canon=self.paths.canon)

    def load_local_keeps(self):
        rows = []
        for d in (os.path.join(HOME, ".local/state/wt-reaper/protect.d"),):
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    # protect.d/protected-dbs.txt is this job's own union, copied back by wt-reaper's sync.  Read as a keep
                    # source it keeps every path that ever entered the union, for good (DISK-URGENT-2 audit, COORD 11-08).
                    if f == GENERATED_UNION and getattr(self.a, "union_real_sources_only", False):
                        continue
                    if f.endswith(".txt"):
                        try:
                            for p, _ in parse_protected(rd(os.path.join(d, f)), f):
                                rows.append((p, "wt-reaper protect.d/" + f))
                        except OSError:
                            pass
        sp = os.path.join(HOME, ".local/state/ot-run/spill_pending")
        if os.path.isdir(sp):
            for f in os.listdir(sp):
                # <tag>.done = back-copy finished; ot-run --spill-sweep reads only *.json, so a .done record holds nothing live.
                if f.endswith(".done") and getattr(self.a, "union_real_sources_only", False):
                    continue
                try:
                    for p in text_paths(rd(os.path.join(sp, f))):
                        rows.append((p, "ot-run spill_pending/" + f))
                except OSError:
                    pass
        for t in alternates_targets(self.found["git"]):
            rows.append((t, "git alternates target"))
        self.localkeep = PathSet(rows, deep=self.deep, canon=self.paths.canon)
        # COORD 11-10 20:3x (AUTOCLEAN-12): protect.d/kit_wave.txt publishes whole wave roots (.../runs/<die>/kit-wave) as
        # wt-reaper SOURCE paths ("worktrees holding these paths are kit-wave sources").  For the class b/c file trims of
        # intermediate stage ODBs such a root holds only itself and its ancestors, not every run below it; the 3 protected
        # lists, counted, kit-wave keep (active/resume/spec), resume_hold, queue, live and age checks still apply.
        self.localkeep_trim = PathSet(rows, deep=lambda q: self.deep(q) and not WAVE_ROOT_RE.search(self.paths.canon(q)),
                                      canon=self.paths.canon)

    def load_counted(self):
        rows, self.signed_records = [], []
        sc = SourceCopy(os.path.join(self.a.snapshot, STORE_INDEX), self.host) if getattr(self.a, "srccopy", False) else None
        self.srccopy_rows = []
        for r in self.found["record"]:
            signed, text = read_record(r)
            if not signed:
                continue
            why = sc.check(r, text) if sc else "srccopy off"
            if why is None:
                # source copy: the record dir and the paths it names INSIDE the checkout are git content; named paths
                # outside the checkout stay counted
                top = sc.top_of[r]
                self.srccopy_rows.append(r)
                for p in text_paths(text):
                    if not os.path.realpath(p).startswith(top + "/"):
                        rows.append((p, "named by signed " + r))
                continue
            self.signed_records.append(self.paths.canon(r))
            rows.append((os.path.dirname(r), "signed record dir " + r))
            for p in text_paths(text):
                rows.append((p, "named by signed " + r))
        if sc:
            say(f"SRCCOPY source-copy records {len(self.srccopy_rows)} (not counted); "
                f"repos fetched {sum(sc.fetched.values())}/{len(sc.fetched)}")
            with open(os.path.join(self.a.state, "srccopy.tsv"), "w") as fh:
                fh.write("".join(r + "\n" for r in self.srccopy_rows))
        # lane-root (or shallower) citations never block whole trees: child match only below lane level
        self.counted = PathSet(rows, deep=self.deep, canon=self.paths.canon)
        self.signed_set = PathSet([(p, "signed record") for p in self.signed_records], canon=self.paths.canon)

    # ---- checks
    def deep(self, p):
        """p lies below lane level (<root>/<lane>/...): lane-root or shallower paths never block whole trees"""
        c = self.paths.canon(p)
        lvl = LANE_DEPTH
        for r in sorted(getattr(self, "roots", []), key=len, reverse=True):
            r = self.paths.canon(r)
            if c == r or c.startswith(r + "/"):
                lvl = depth(r) + 1
                break
        return depth(c) > lvl

    def lane(self, k):
        return k.split("/claude/", 1)[1].split("/")[0] if "/claude/" in k else ""

    def _indep_real(self, p):
        p = self.paths._alias(os.path.normpath(p))
        head, tail = p, ""
        while head and head != "/" and not os.path.lexists(head):
            head, t = os.path.split(head)
            tail = "/" + t + tail
        return self.paths._alias(os.path.realpath(head or "/") + tail)

    def indep_hit(self, path, files):
        """INCIDENT 11-07 belt-and-braces: independent of Paths.canon/PathSet, realpath every raw kit-wave keep /
        active / signed path and every PROTECTED row; a candidate equal to, above or below one is an ALERT"""
        import bisect
        if getattr(self, "_indep", None) is None:
            raw = [ln.split("\t", 1)[0] for ln in rd(self.prot_file).splitlines() if ln.startswith("/")]
            if self.kitwave is not None:
                raw += [x.partition(":")[2] for x in self.kitwave.get("keep", [])]
                raw += [x.partition(":")[2] for x, v in self.kitwave.get("attempts", {}).items()
                        if v.get("active") or v.get("signed")]
            self._indep = sorted({self._indep_real(r) for r in raw if r.startswith("/")})
            self._indep_set = set(self._indep)
        for c in [path] + list(files):
            d = self._indep_real(c)
            i = bisect.bisect_left(self._indep, d)
            if i < len(self._indep) and (self._indep[i] == d or self._indep[i].startswith(d + "/")):
                return f"independent realpath: {self._indep[i]}"
            a = d
            while a not in ("", "/"):
                if a in self._indep_set and a.count("/") > 4:
                    return f"independent realpath ancestor: {a}"
                a = os.path.dirname(a)
        return None

    def guard_hits(self, k):
        """protected / counted / kit-wave keep: hits here at recheck time are ALERTs"""
        for name, ps in (("protected", self.protected), ("counted", self.counted), ("kitwave-keep", self.kwkeep)):
            for f in self.paths.forms(k):
                h = ps.hit(f)
                if h:
                    return f"{name}: {h}"
        return None

    def common_why(self, k, files, qn_ok=False):
        nt = never_touch(k)
        if nt:
            return nt
        for q in (k, os.path.realpath(k)):
            if EMERGENCY_HOLD_RE.search(q + "/"):
                return "emergency hold (bind/src tree): " + q
        lane = self.lane(k)
        if lane.startswith(("tok-", "kv-fn-")) or "/tok-" in k or "/kv-fn-" in k:
            return "lane " + lane
        if any("tool" in c for c in k.split("/")):
            return "tool tree"
        g = self.guard_hits(k)
        if g:
            return g
        h = getattr(self, "localkeep_trim", self.localkeep).hit(k)   # DISK-1111: a wave-root row (protect.d/kit_wave.txt) holds the root, not every finished attempt below it (class a per-attempt kit-wave state decides)
        if h:
            return "local keep: " + h
        h = self.queue.hit(k)
        if h and not getattr(self, "_attempt_mode", False):          # OWNER 11-12: a queue post does not hold a terminal / superseded attempt
            return "queuepath: " + h
        rest = k.split("/claude/", 1)[1].split("/")[1:] if "/claude/" in k else []
        for i, n in enumerate(rest):
            if i >= 2 and rest[i - 2] == "kit-wave":   # kit-wave/<die>/<plan event>: the plan dir names a whole wave
                continue
            if not generic_name(n) and n in self.qwords and not getattr(self, "_qn_skip", False) and not qn_ok:
                return "queuename: " + n
        w = self.live.why(self.paths.forms(k))
        if w:
            return w
        for f in ([] if getattr(self, "_attempt_mode", False) else files):
            try:
                if os.stat(f).st_nlink > 1:
                    return "hardlink " + f
            except OSError:
                return "gone " + f
        g = git_locked(k)
        if g:
            return "gitlocked " + g
        for a in [k] + ancestors(k):
            if os.path.exists(os.path.join(a, ".keep")):
                if self.keep_expired(os.path.join(a, ".keep")):
                    continue
                if getattr(self, "_trim_cls", "") == "c" and a != k and self.old_keep_finished(k, a):
                    continue
                return "keep " + a
        for kp in self.found["keep"]:
            if kp.startswith(k + "/") and not self.keep_expired(kp):
                return "keep " + kp
        return None

    def keep_expired(self, keep_file):
        """DISK-1111 (OWNER 11-12 "old plans removed directly", COORD): --keep-expire-h H: a .keep file not touched for
        H hours (default off, timers use 168 = 7 days) no longer holds; the protected lists, kit-wave state, live-job,
        queue and realpath guards still apply to the same path."""
        h = float(getattr(self.a, "keep_expire_h", 0) or 0)
        if h <= 0:
            return False
        try:
            return self.now - os.lstat(keep_file).st_mtime >= h * 3600
        except OSError:
            return False

    def _reg(self, p, min_bytes=0):
        try:
            st = os.lstat(p)
        except OSError:
            return None
        if not stat.S_ISREG(st.st_mode) or st.st_size < min_bytes:
            return None
        return st

    def eval_trim(self, cls, d):
        """class b / c on results dir d -> (why or None, kit, files)"""
        kit = d.split("/results/")[0] if "/results/" in d else d
        if kit.endswith("/run"):
            kit = kit[:-4]
        if cls == "b":
            anchors = ["6_final.odb", "6_final.spef"]
            names = list(TRIM_B)
        else:
            anchors = ["3_place.odb"]
            names = list(TRIM_C)
            if self._reg(os.path.join(d, "4_cts.odb"), MIN_BYTES + 1):
                names.append("4_1_cts.odb")
        for n in anchors:
            if not self._reg(os.path.join(d, n), MIN_BYTES + 1):
                return f"no {n} > 1 KB", kit, []
        files = [os.path.join(d, n) for n in names if n not in NEVER and self._reg(os.path.join(d, n))]
        if not files:
            return "nothing", kit, []
        for p in [os.path.join(d, anchors[0])] + files:
            if self.now - os.lstat(p).st_mtime < AGE_S:
                return "lt6h " + os.path.basename(p), kit, files
        # --queuename-skip-trim-c (AUTOCLEAN-9 11-08): a bare queue NAME (mostly a design type name, posted daily)
        # does not stop the class c trim of 2_x / 3_x stage intermediates; an exact queue PATH and every other check
        # still do.  Class b and class a are unchanged.
        if cls == "c":
            r = self.resume_hold(d)
            if r:
                return r, kit, files
        if cls == "b":   # the trims sit beside 6_final: held until that results dir's 6_final is cut
            h = self.dx_hold(d)
            if h:
                return h, kit, files
        qn_ok = cls == "c" and bool(getattr(self.a, "queuename_skip_trim_c", False))
        self._trim_cls = cls
        try:
            return self.common_why(kit, files, qn_ok=qn_ok), kit, files
        finally:
            self._trim_cls = ""

    def old_keep_finished(self, k, a):
        """--c-old-keep-h H (COORD 11-08 08:0x / 09:2x, DISK-URGENT-1): an ANCESTOR .keep older than H hours does not
        stop the class c trim of kit k when k is finished or superseded: k holds a 6_final.odb (> 1 KB) or a
        signoff.json, or k lies in attempt_N of an item that has a later attempt_M.  A .keep younger than H, a .keep
        inside k (or the results dir) and every other guard still protect."""
        h = float(getattr(self.a, "c_old_keep_h", 0) or 0)
        if h <= 0:
            return False
        try:
            if self.now - os.lstat(os.path.join(a, ".keep")).st_mtime < h * 3600:
                return False
        except OSError:
            return False
        for dp, dn, fn in os.walk(k):
            if "6_final.odb" in fn and self._reg(os.path.join(dp, "6_final.odb"), MIN_BYTES + 1):
                return True
            if "signoff.json" in fn:
                return True
        m = ATTEMPT_RE.match(k)
        if m:
            try:
                for n in os.listdir(m.group(1)):
                    mm = re.fullmatch(r"attempt_(\d+)", n)
                    if mm and int(mm.group(1)) > int(m.group(2)):
                        return True
            except OSError:
                pass
        return False

    def resume_hold(self, d):
        """COORD 11-08 04:4x: the kit wave resumes a FAIL row from its last valid stage, so class c never trims inside a
        kit-wave attempt (.../items/<item>/attempt_N, or an item dir without attempt_N: its latest attempt) whose
        newest file is < RESUME_S old and whose row is FAIL (or unknown to the state) and not superseded."""
        c = self.paths.canon(d)
        m = ATTEMPT_RE.match(c)
        if m:
            item, n, adir = m.group(1), int(m.group(2)), m.group(0)
        else:
            mi = ITEM_RE.match(c)
            if not mi:
                return None
            item = adir = mi.group(1)
            n = self.kw_latest.get(item, -1) if self.kitwave is not None else -1
        if self.now - tree_info(adir)[0] >= RESUME_S:
            return None
        if self.kitwave is None:
            return "resume-pending: kit-wave attempt < 24 h, no kit-wave snapshot"
        st = self.kw_attempts.get(f"{item}/attempt_{n}") if n >= 0 else None
        xm = XPATH_RE.search(f"{item}/attempt_{max(n, 0)}")
        cur = self.kw_current_di.get(f"{xm.group(1)}|{xm.group(2)}", -1) if xm else -1
        if n >= 0 and (self.kw_latest.get(item, -1) > n or cur > n):
            return None                                  # superseded: a later attempt exists
        term = ",".join(sorted(set(st["terminal"]))) if st else ""
        if st and term and "FAIL" not in term:
            return None                                  # finished without FAIL (CANCELLED / WITHDRAWN ...)
        return f"resume-pending: attempt_{n} {term or 'unknown'} not superseded, < 24 h"

    def eval_attempt(self, d):
        if self.kitwave is None:
            return "no kit-wave snapshot", []
        c = self.paths.canon(d)
        m = ATTEMPT_RE.match(c)
        if not m or m.group(0) != c:
            return "not an attempt dir", []
        st = self.kw_attempts.get(c)
        h = self.kwkeep.hit(c)
        if h:
            return "kitwave-keep: " + h, []
        aggr = bool(getattr(self.a, "aggressive", False))
        if st and st["signed"]:
            return "kit-wave signed", []
        if st and st["active"]:
            return "kit-wave active", []
        xm = XPATH_RE.search(c)
        cur = self.kw_current_di.get(f"{xm.group(1)}|{xm.group(2)}", -1) if xm else -1
        if st and st["terminal"]:
            verdict = "finished " + ",".join(sorted(set(st["terminal"])))[:80]
        elif self.kw_latest.get(m.group(1), -1) > int(m.group(2)):
            verdict = f"superseded by attempt_{self.kw_latest[m.group(1)]}"
        elif cur > int(m.group(2)):               # older attempt of a die|item now run from another plan dir
            verdict = f"superseded-xpath by attempt_{cur}"
        else:
            # FLEET-2 11-12 RUN-DIR LOSS: a row the kit-wave state does not know (lane run roots such as vislayout2-*,
            # a state snapshot taken before the row was launched) is NEVER deleted, aggressive or not: only a terminal
            # record or a later attempt of the same item may release an attempt
            return "kit-wave unknown", []
        vh = self.visual_hold(d, c)
        if vh:
            return vh, []
        h = self.signed_set.hit(c)
        if h and not (aggr and self.stub_verified(c) is None):       # aggressive: a verified AGIdock copy lets the signed attempt go
            return "signed: " + h, []
        for g in self.found["git"]:
            if g.startswith(d + "/"):
                return "git inside " + g, []
        newest, size, hl = tree_info_c(d)
        if self.now - newest < (GRACE_S if aggr else AGE_S):
            return "lt6h" if not aggr else "lt2h", []
        if hl and not aggr:                                          # aggressive: unlinking one name of a shared inode is safe
            return "hardlink " + hl, []
        h = self.dx_hold(d, "newest" if verdict.startswith("finished") else "superseded")
        if h:
            return h, []
        self._attempt_note = verdict
        # --queuename-skip-superseded: a bare item NAME in a queue post protects the item's current attempt, not
        # older attempts the state has superseded (an exact queue PATH still protects them)
        self._qn_skip = (bool(getattr(self.a, "queuename_skip_superseded", False)) and verdict.startswith("superseded")) or aggr
        self._attempt_mode = aggr
        try:
            return self.common_why(d, []), [d]
        finally:
            self._qn_skip = False
            self._attempt_mode = False

    def visual_hold(self, d, c):
        """FLEET-2 11-12: an attempt whose layout_review/ or geom/ is not yet judged keeps EVERYTHING (gen/, geom/,
        layout_review/, renders): held while it is named in <snapshot>/visual_hold.txt (one path or item name per line,
        written by the driver from lanes/GEOM-REVIEW.md WAIT-VISUAL attempts), and, with no such list, while its
        layout_review/ or geom/ is younger than VISUAL_HOLD_S."""
        try:
            has = any(os.path.isdir(os.path.join(d, n)) for n in VISUAL_DIRS)
        except OSError:
            return "visual-hold: unreadable"
        names = getattr(self, "visual_names", None)
        if names is not None:
            m = ATTEMPT_RE.match(c)
            if c in names or d in names or (m and (m.group(1) in names or os.path.basename(m.group(1)) in names)):
                return "visual-hold: WAIT-VISUAL attempt (visual_hold.txt)"
        if not has:
            return None
        if names is None:
            # no driver list: the renders a reviewer looks at (layout_review/ anything; geom/ images, svg, html) younger than 24 h;
            # geom/auto_geom.json alone is a machine check, not a render, and does not hold
            for n in VISUAL_DIRS:
                p = os.path.join(d, n)
                if not os.path.isdir(p):
                    continue
                newest = 0.0
                for dp, _dn, fns in os.walk(p):
                    for fn in fns:
                        if n == "layout_review" or fn.lower().endswith(VISUAL_EXT):
                            try:
                                newest = max(newest, os.lstat(os.path.join(dp, fn)).st_mtime)
                            except OSError:
                                pass
                if newest and self.now - newest < VISUAL_HOLD_S:
                    return f"visual-hold: {n}/ render < 24 h and no visual_hold.txt"
        return None

    # ---- recheck + delete
    def recheck(self, cls, path, files):
        self.load_protected()                      # re-read the union file: a row added meanwhile must stop us
        k = path
        g = self.guard_hits(k)
        if not g and cls == "a":
            g = self.signed_set.hit(self.paths.canon(k))
            g = "signed: " + g if g else None
        if not g:
            for f in files:
                g = self.guard_hits(f)
                if g:
                    break
        if not g:
            g = self.indep_hit(path, files)
        if g:
            return "ALERT", g
        if self.a.apply:
            self.live.refresh()
            if cls == "a":
                w, _ = self.eval_attempt(path)
            else:
                w, _, _ = self.eval_trim(cls, os.path.dirname(files[0]))
            if w:
                return "SKIP", "recheck: " + w
        return None, None

    def rm_tree(self, f):
        """rm -rf --one-file-system of f; with --aggressive the grandchildren go in parallel (--rm-jobs, default 16): a
        deep attempt tree is millions of small files and one rm walks them serially (the slow part of every run)"""
        jobs = int(getattr(self.a, "rm_jobs", 1) or 1)
        if jobs > 1 and os.path.isdir(f) and not os.path.islink(f):
            try:
                tg = []
                for n in os.listdir(f):
                    q = os.path.join(f, n)
                    if os.path.isdir(q) and not os.path.islink(q):
                        try:
                            tg += [os.path.join(q, m) for m in os.listdir(q)] or [q]
                        except OSError:
                            tg.append(q)
                    else:
                        tg.append(q)
                if len(tg) > 1:
                    def one(q):
                        return subprocess.run(["rm", "-rf", "--one-file-system", "--", q], capture_output=True, text=True, timeout=7200)
                    errs = [x for x in run_pool(one, tg, jobs) if x.returncode]
                    if errs:
                        return errs[0]
            except OSError:
                pass
        return subprocess.run(["rm", "-rf", "--one-file-system", "--", f], capture_output=True, text=True, timeout=7200)

    def delete(self, cls, files):
        freed = 0
        for f in files:
            if EMERGENCY_HOLD_RE.search(os.path.realpath(f) + "/") or EMERGENCY_HOLD_RE.search(f + "/"):
                raise OSError("emergency hold " + f)
            try:                                              # per-delete journal: the manifest is written only when a run ends
                with open(os.path.join(self.a.state, "deleted.log"), "a") as jf:  # noqa
                    jf.write(f"{time.strftime('%F %T')}\t{cls}\t{f}\n")
            except (OSError, AttributeError):
                pass
            if cls == "a":
                _, size, _ = tree_info_c(f)
                r = self.rm_tree(f)
                if r.returncode and "ermission denied" in r.stderr and getattr(self.a, "aggressive", False) \
                        and os.path.realpath(f) == f and not os.path.islink(f):
                    # root-owned files from docker jobs: the same path, already approved by every guard, removed as root
                    r = subprocess.run(["sudo", "-n", "rm", "-rf", "--one-file-system", "--", f], capture_output=True, text=True,
                                       timeout=7200)
                if r.returncode:
                    raise OSError(r.stderr.strip()[:200])
                freed += size
            else:
                if os.path.basename(f) in NEVER:
                    raise OSError("refusing never-delete name " + f)
                st = os.lstat(f)
                os.unlink(f)
                freed += st.st_blocks * 512
        return freed

    def handle(self, cls, path, files, why, mtime):
        size = 0
        for f in files:
            try:
                size += (tree_info_c(f)[1] if cls == "a" else os.lstat(f).st_blocks * 512)
            except OSError:
                pass
        verdict = "SKIP" if why else ("WOULD" if not self.a.apply else "DELETE")
        reason = why or getattr(self, "_attempt_note", "") if cls == "a" else why or ""
        if not why:
            v, r = self.recheck(cls, path, files)
            if v == "ALERT":
                self.recheck_hits += 1
                self.alerts.append(f"{cls}\t{path}\t{r}")
                verdict, reason = "ALERT", r
            elif v == "SKIP":
                verdict, reason = "SKIP", r
            elif self.a.apply:
                try:
                    size = self.delete(cls, files)
                    verdict = "DELETED"
                except OSError as e:
                    verdict, reason = "ERROR", str(e)[:200]
        self.rows.append([time.strftime("%F %T"), self.host, cls, verdict, " ".join(reason.split())[:300], path,
                          ",".join(os.path.basename(f) for f in files) if cls != "a" else "<tree>", size, int(mtime)])
        return verdict


    # ---- class d (OWNER 11-12 "aggressive cleanup ... the jobs are self contained"): lane trees that nothing keeps
    def d_keepset(self):
        """paths kept whole (live / referenced / signed-unarchived / git / never-touch) and their ancestors (never deleted whole)"""
        keep = set()
        for t in NEVER_TOUCH_PATHS:
            keep.add(os.path.realpath(t))
            keep.add(t)
        for g in self.found["git"]:
            keep.add(os.path.dirname(g))                 # a checkout / worktree (the worktree reaper owns it)
        for r in self.found["record"]:
            if read_record(r)[0]:
                keep.add(unit_of(r))
        for a in self.found["attempt"]:                  # attempts still on disk after class a (it decides them)
            if os.path.isdir(a):
                keep.add(a)
        for kp in self.found["keep"]:
            if not self.keep_expired(kp):
                keep.add(os.path.dirname(kp))
        anc = set()
        for k in keep:
            anc.update(ancestors(k))
        return keep, anc

    def d_why(self, p, keep, anc):
        """None = deletable whole; 'recurse' = holds something kept, look inside; else the reason it stays"""
        c = self.paths.canon(p)
        for q in (p, c, os.path.realpath(p)):
            if EMERGENCY_HOLD_RE.search(q + "/"):
                return "kept: emergency hold (bind/src tree)"
        if c in keep or p in keep:
            return "kept: referenced / signed / git / keep"
        if os.path.basename(c) in VISUAL_DIRS + ("gen",) and re.search(r"/items/[^/]+/attempt_\d+/", c + "/"):
            return "kept: layout_review/geom/gen of an attempt (FLEET-2 11-12)"
        if re.search(r"/(vislayout2?[^/]*|[^/]*-wave-[^/]*)/", c + "/") and os.path.isfile(os.path.join(p, ".keep")):
            return "kept: lane run root .keep"
        for name, ps in (("protected", self.protected), ("counted", self.counted), ("kitwave-keep", self.kwkeep),
                         ("local keep", self.localkeep_trim)):
            for f in self.paths.forms(p):
                h = ps.hit(f)
                if h:
                    return "recurse" if h.startswith("holds") else f"{name}: {h}"
        w = self.live.why(self.paths.forms(p))
        if w:
            return w
        g = git_locked(p)
        if g:
            return "gitlocked " + g
        if c in anc or p in anc:
            return "recurse"
        if os.path.isdir(p) and self.holds_emergency_below(p):
            return "recurse"
        return None

    def holds_emergency_below(self, p):
        """a bind / src tree (die-hbm-*/ab, src_*) lies within 6 levels below p: p is never deleted whole"""
        r = subprocess.run(["find", "-P", p, "-maxdepth", "6", "-path", "*/claude/die-hbm-*/ab", "-print", "-quit"],
                           capture_output=True, text=True, timeout=600)
        return bool(r.stdout.strip())

    def live_lane_roots(self):
        """OWNER/COORD 11-12 (class d deleted die-proto-3/{proto_die.sh,scripts,s81} under DIE-PROTO-1's running chains): every
        */claude/<lane> root that holds the cwd, an open file, a docker bind-mount source or an absolute path in the argv of a
        running process / container on this host.  Class d never touches such a lane."""
        self.live.refresh()
        paths = set(self.live.cwds) | set(self.live.fds) | set(self.live.mounts)
        for c in self.live.cmds:
            for m in re.findall(r"(/[^\s'\";:,)=]+/claude/[^\s'\";:,)=]+)", c):
                paths.add(m)
        lanes = set()
        for q in paths:
            q = q.split(" (deleted)")[0]
            for cand in {q, os.path.realpath(q)}:
                m = re.match(r"(.*?/srv/[^/]+/claude/[^/]+)", cand)
                if m:
                    lanes.add(m.group(1))
                    lanes.add(os.path.realpath(m.group(1)))
        for t in getattr(self.a, "d_live_extra", []) or []:
            lanes.add(t)
        return lanes

    def prune_lane_trees(self, gone):
        a = self.a
        keep, anc = self.d_keepset()
        n_del = 0

        def visit(p, depth):
            nonlocal n_del
            try:
                st = os.lstat(p)
            except OSError:
                return
            if stat.S_ISLNK(st.st_mode) or never_touch(p):
                return
            if stat.S_ISDIR(st.st_mode):
                if os.path.exists(os.path.join(p, ".ot-hold")):
                    return
                why = self.d_why(p, keep, anc)
            else:
                why = None
            if why == "recurse":
                try:
                    kids = sorted(os.listdir(p))
                except OSError:
                    return
                for n in kids:
                    visit(os.path.join(p, n), depth + 1)
                return
            if depth < 2 and why is None and stat.S_ISDIR(st.st_mode):
                pass
            size = 0
            if why is None:
                newest, size, _hl = tree_info_c(p) if stat.S_ISDIR(st.st_mode) else (st.st_mtime, st.st_blocks * 512, None)
                if CTIME_GRACE and stat.S_ISDIR(st.st_mode) and os.path.basename(p).startswith("src_"):
                    newest = max(newest, st.st_ctime)
                if self.now - newest < GRACE_S:
                    why = "lt2h"
            verdict = "SKIP" if why else ("WOULD" if not a.apply else "DELETE")
            if not why:
                g = self.guard_hits(p) or self.indep_hit(p, [])
                if g:
                    self.recheck_hits += 1
                    self.alerts.append(f"d\t{p}\t{g}")
                    verdict, why = "ALERT", g
                elif a.apply:
                    self.load_protected()
                    self.live.refresh()
                    w2 = self.d_why(p, keep, anc)
                    if w2:
                        verdict, why = "SKIP", "recheck: " + w2
                    else:
                        try:
                            self.delete("a", [p]) if stat.S_ISDIR(st.st_mode) else os.unlink(p)
                            verdict = "DELETED"
                            gone.append(p)
                        except OSError as e:
                            verdict, why = "ERROR", str(e)[:200]
            if verdict in ("DELETED", "WOULD", "ERROR", "ALERT") or why not in (None,) and verdict == "SKIP" and size > (1 << 30):
                self.rows.append([time.strftime("%F %T"), self.host, "d", verdict, " ".join((why or "aggressive lane tree").split())[:300],
                                  p, "<tree>", size, int(st.st_mtime)])
            return

        live_lanes = self.live_lane_roots()
        for r in self.roots:
            if not re.fullmatch(r"/srv/[^/]+/claude", r) and not getattr(a, "d_any_root", False):
                continue                                  # class d only prunes the fleet scratch roots, never a home / checkout root
            try:
                lanes = sorted(os.listdir(r))
            except OSError:
                continue
            for lane in lanes:
                lp = os.path.join(r, lane)
                if lane in D_SKIP_LANES or lane.startswith(("tok-", "kv-fn-")) or "tool" in lane or os.path.islink(lp) \
                        or not os.path.isdir(lp):
                    continue
                if os.path.realpath(lp) in live_lanes or lp in live_lanes:        # COORD 11-12: a running process / container works in this lane
                    self.rows.append([time.strftime("%F %T"), self.host, "d", "SKIP", "live lane (cwd / argv / fd / docker mount)", lp,
                                      "<tree>", 0, int(os.lstat(lp).st_mtime)])
                    continue
                visit(lp, 1)

    # ---- class s: stub-trim of a signed unit whose archive copy is verified (COORD 11-11, KW-FIX-46)
    def stub_verified(self, unit):
        """None, or why the unit's ARCHIVED.json is not a verified archive of exactly the unit's current archive set"""
        p = os.path.join(unit, "ARCHIVED.json")
        try:
            if os.path.islink(p) or not os.path.isfile(p):
                return "no ARCHIVED.json"
            rec = jl(p)
            files = rec["files"]
            if rec.get("schema") != "opentallas.archived.v2":
                return "ARCHIVED.json schema"
            if not str(rec.get("verify", "")).startswith("OK"):
                return "ARCHIVED.json not verified"
            if not str(rec.get("archive", "")).startswith(ARCHIVE_PREFIX):
                return "ARCHIVED.json archive path"
            if not files or rec.get("nfiles") != len(files) or not all(SHA_RE.match(str(f.get("sha256", ""))) for f in files):
                return "ARCHIVED.json sha256 list"
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return "ARCHIVED.json unreadable"
        if not archived_ok(unit, unit_files(unit, self.roots)):
            return "unit changed since the archive copy"
        return None

    def stub_units(self):
        units = {}
        for r in self.found["record"]:
            signed, _ = read_record(r)
            if signed:
                units.setdefault(unit_of(r), []).append(r)
        return {u: rs for u, rs in units.items() if not any(u.startswith(v + "/") for v in units)}

    def stub_own(self, unit, why):
        """a counted row that this unit's own records created (their dir, the paths they cite): the stub keeps all of it"""
        for r in (os.path.join(unit, "signoff.json"), os.path.join(unit, "PROVENANCE.json"),
                  os.path.join(unit, "signoff", "signoff.json"), os.path.join(unit, "signoff", "PROVENANCE.json")):
            if why.endswith(" " + r) or why.endswith(" " + self.paths.canon(r)):
                return True
        return False

    def stub_unit_hold(self, unit):
        """protection that holds the WHOLE unit: a protected / kit-wave / local-keep row equal to it or above it
        (--stub-protected-units relaxes it for protected rows only: the stub then keeps every protected path inside)"""
        c = self.paths.canon(os.path.normpath(unit))
        for name, ps in (("protected", self.protected), ("kitwave-keep", self.kwkeep), ("local keep", getattr(self, "localkeep_trim", self.localkeep))):
            for a in [c] + ancestors(c):
                if a in ps.m and (a == c or ps.deep(a)):
                    if name == "protected" and getattr(self.a, "stub_protected_units", False):
                        break
                    return f"{name}: {a} ({ps.m[a]})"
        return None

    def stub_file_hold(self, unit, f):
        for form in self.paths.forms(f):
            h = self.protected.hit(form)
            if h:
                return "protected"
            h = self.kwkeep.hit(form)
            if h:
                return "kitwave-keep"
            h = getattr(self, "localkeep_trim", self.localkeep).hit(form)
            if h:
                return "local keep"
            h = self.queue.hit(form)
            if h:
                return "queuepath"
            c = self.paths.canon(os.path.normpath(form))
            for a in [c] + ancestors(c):
                why = self.counted.m.get(a)
                if why is not None and (a == c or self.counted.deep(a)) and not self.stub_own(unit, why):
                    return "counted"
        return None

    def eval_stub(self, unit):
        """-> (why or None, [(path, size, disk_bytes, mtime)], {held reason: n})"""
        nt = never_touch(unit)
        if nt:
            return nt, [], {}
        if os.path.realpath(unit) != os.path.normpath(unit) or any(
                os.path.islink(a) for a in [unit] + ancestors(unit) if depth(a) > LANE_DEPTH - 1):
            return "symlinked path " + unit, [], {}
        lane = self.lane(unit)
        if lane.startswith(("tok-", "kv-fn-")) or any("tool" in c for c in unit.split("/")):
            return "lane/tool tree " + lane, [], {}
        if in_git_checkout(unit):
            return "git checkout", [], {}
        why = self.stub_verified(unit)
        if why:
            return why, [], {}
        why = self.stub_unit_hold(unit) or self.dx_hold(unit)
        if why:
            return why, [], {}
        w = self.live.why(self.paths.forms(unit))
        if w:
            return w, [], {}
        g = git_locked(unit)
        if g:
            return "gitlocked " + g, [], {}
        for a in [unit] + ancestors(unit):
            if os.path.exists(os.path.join(a, ".keep")):
                return "keep " + a, [], {}
        try:
            keep = {f["path"] for f in jl(os.path.join(unit, "ARCHIVED.json"))["files"]}
        except (OSError, ValueError, KeyError, TypeError):
            return "ARCHIVED.json unreadable", [], {}
        keep.add(os.path.join(unit, "ARCHIVED.json"))
        keep.add(os.path.join(unit, STUB_MARKER))
        dev = os.lstat(unit).st_dev
        cands, held = [], {}
        for dp, dns, fns in os.walk(unit, followlinks=False):
            sub = []
            for d in dns:
                full = os.path.join(dp, d)
                if os.path.islink(full):
                    held["symlink"] = held.get("symlink", 0) + 1
                elif d == ".git":
                    held["git"] = held.get("git", 0) + 1
                elif any(os.path.exists(os.path.join(full, *x)) for x in
                         (("signoff.json",), ("PROVENANCE.json",), ("ARCHIVED.json",), ("signoff", "signoff.json"))):
                    held["nested record"] = held.get("nested record", 0) + 1
                elif os.lstat(full).st_dev != dev:
                    held["other filesystem"] = held.get("other filesystem", 0) + 1
                else:
                    sub.append(d)
            dns[:] = sub
            for f in fns:
                pth = os.path.join(dp, f)
                if pth in keep:
                    continue
                try:
                    st = os.lstat(pth)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    held["not a regular file"] = held.get("not a regular file", 0) + 1
                    continue
                if st.st_nlink > 1:
                    held["hardlink"] = held.get("hardlink", 0) + 1
                    continue
                if f in NEVER:
                    held["never-delete name"] = held.get("never-delete name", 0) + 1
                    continue
                h = self.stub_file_hold(unit, pth)
                if h:
                    held[h] = held.get(h, 0) + 1
                    continue
                if self.now - st.st_mtime < STUB_AGE_S:
                    return f"lt12h {pth}", [], held
                cands.append((pth, st.st_size, st.st_blocks * 512, int(st.st_mtime)))
        return (None if cands else "nothing to trim"), cands, held

    def stub_apply(self, unit, cands, held):
        """receipt first, then marker, then unlink; every file is re-checked right before its unlink"""
        import gzip
        rdir = os.path.join(self.a.state, "stub-receipts")
        os.makedirs(rdir, exist_ok=True)
        arch = jl(os.path.join(unit, "ARCHIVED.json"))
        rid = hashlib.sha256(unit.encode()).hexdigest()[:12]
        rpath = os.path.join(rdir, f"STUB-{self.host}-{stamp()}-{rid}.json.gz")
        rec = {"schema": "opentallas.stub-receipt.v1", "host": self.host, "unit": unit, "date": time.strftime("%F %T %Z"),
               "archive": arch.get("archive"), "archive_verify": arch.get("verify"),
               "archived_json_sha256": sha256(os.path.join(unit, "ARCHIVED.json")),
               "files": [{"path": p_, "size": s, "mtime": m} for p_, s, _, m in cands], "held": held}
        with gzip.open(rpath + ".tmp", "wt") as fh:
            json.dump(rec, fh)
        os.replace(rpath + ".tmp", rpath)
        mk = os.path.join(unit, STUB_MARKER)
        with open(mk + ".tmp", "w") as fh:
            json.dump({"schema": "opentallas.stubbed.v1", "date": rec["date"], "archive": rec["archive"], "nfiles": len(cands),
                       "bytes": sum(s for _, s, _, _ in cands), "receipt": rpath, "held": held}, fh, indent=1)
        os.replace(mk + ".tmp", mk)
        freed, dirs = 0, set()
        for p_, size, disk, _ in cands:
            self.load_protected() if False else None
            g = self.guard_hits(p_) if not self.stub_own_ok(unit, p_) else None
            if g:
                return freed, f"ALERT {g}"
            st = os.lstat(p_)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink > 1 or os.path.basename(p_) in NEVER:
                continue
            os.unlink(p_)
            freed += st.st_blocks * 512
            dirs.add(os.path.dirname(p_))
        for d in sorted(dirs, key=len, reverse=True):
            while d != unit and d.startswith(unit + "/"):
                try:
                    os.rmdir(d)
                except OSError:
                    break
                d = os.path.dirname(d)
        return freed, ""

    def stub_own_ok(self, unit, p_):
        """True when guard_hits would only name this unit's own counted rows (the stub keeps those files)"""
        return self.stub_file_hold(unit, p_) is None

    # ---- controls
    def controls(self):
        base = os.path.join(self.roots[0], "_ot_autoclean_ctl", f"{os.getpid()}-{stamp()}")
        d = os.path.join(base, "run/results/asap7/x/base")
        try:
            os.makedirs(d)
            old = self.now - 10 * 3600
            for n, sz in (("6_final.odb", 4096), ("6_final.spef", 4096), ("5_route.odb", 2048), ("2_floorplan.odb", 2048)):
                with open(os.path.join(d, n), "wb") as fh:
                    fh.write(os.urandom(sz))
                os.utime(os.path.join(d, n), (old, old))
            why, kit, files = self.eval_trim("b", d)
            pos = (why is None and [os.path.basename(f) for f in files] == ["5_route.odb"]
                   and self.recheck("b", kit, files) == (None, None))
            if pos:
                self.delete("b", files)
                pos = not os.path.exists(os.path.join(d, "5_route.odb")) and all(
                    os.path.exists(os.path.join(d, n)) for n in ("6_final.odb", "6_final.spef", "2_floorplan.odb"))
            # negative: the same row again, now named by a fake protected row (under an alias form when one exists)
            with open(os.path.join(d, "5_route.odb"), "wb") as fh:
                fh.write(os.urandom(2048))
            os.utime(os.path.join(d, "5_route.odb"), (old, old))
            saved = self.protected
            fake = sorted(self.paths.forms(base))[-1]
            self.protected = PathSet(list((p, w) for p, w in saved.m.items()) + [(fake, "negative control")],
                                     canon=self.paths.canon)
            nwhy, _, nfiles = self.eval_trim("b", d)
            g = self.guard_hits(kit)
            self.protected = saved
            neg = (nwhy or "").startswith("protected") and g is not None and os.path.exists(os.path.join(d, "5_route.odb"))
            return pos, neg
        finally:
            shutil.rmtree(os.path.join(self.roots[0], "_ot_autoclean_ctl", os.path.basename(base)), ignore_errors=True)
            try:
                os.rmdir(os.path.join(self.roots[0], "_ot_autoclean_ctl"))
            except OSError:
                pass

    # ---- main
    def write_union(self, path):
        """protection union for wt-reaper (host<TAB>path<TAB>source rows, every alias form)"""
        rows = []
        for name, ps in (("protected", self.protected), ("counted", self.counted), ("kitwave", self.kwkeep),
                         ("localkeep", self.localkeep)):
            for p, w in ps.m.items():
                for f in sorted(self.paths.forms(p)):
                    rows.append(f"{self.host}\t{f}\t{name}: {' '.join(str(w).split())[:120]}")
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            fh.write("# ot-autoclean generated protection union (do not edit)\n" + "\n".join(rows) + "\n")
        os.replace(tmp, path)

    def run(self):
        a = self.a
        os.makedirs(a.state, exist_ok=True)
        with open(os.path.join(a.state, "lock"), "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                say("ot-autoclean: another run holds the lock; exiting")
                return 0
            return self._run()

    def _run(self):
        a = self.a
        _TI.clear()
        off = [f for f in OFF_FILES if os.path.exists(f)]
        if off or os.environ.get("OT_AUTOCLEAN") == "0":
            say(f"ot-autoclean: OFF switch {off or 'OT_AUTOCLEAN=0'}; nothing done")
            return 0
        alert_f = os.path.join(a.state, "ALERT")
        if os.path.exists(alert_f):
            say(f"ot-autoclean: {alert_f} exists (sticky); no deletes until a human removes it")
            return 3
        self.roots = dedupe_roots(list(a.roots) + (local_extra_roots() if self.host == "localhost" else []))
        self.roots = [r for r in self.roots if not never_touch(r)]
        if not self.roots:
            say("ot-autoclean: no roots")
            return 0
        self.load_snapshot()
        self.live = Live(a.docker, self.deep)
        self.found = scan_roots(self.roots, a.find_timeout)
        if self.found is None:
            raise RuntimeError("find scan failed or timed out")
        self.load_counted()
        self.load_local_keeps()
        pos, neg = self.controls()
        say(f"controls: positive {'PASS' if pos else 'FAIL'} negative {'PASS' if neg else 'FAIL'}")
        if not (pos and neg):
            say("ot-autoclean: control failed; abort, nothing deleted")
            return 4
        mode = "apply" if a.apply else "dry"
        say(f"ot-autoclean {mode} host {self.host} roots {' '.join(self.roots)}; protected {len(self.protected)} "
            f"counted {len(self.counted)} kit-wave keep {len(self.kwkeep)} local keep {len(self.localkeep)} "
            f"signed records {len(self.signed_records)}; snapshot {self.snapshot_meta.get('created_h', '')}")
        seen, gone = set(), []
        classes = a.classes
        stop = False

        def once(p, cls):
            try:
                st = os.stat(p)
            except OSError:
                return False
            if (cls, st.st_dev, st.st_ino) in seen:
                return False
            seen.add((cls, st.st_dev, st.st_ino))
            return True
        if "a" in classes:
            for d in sorted(self.found["attempt"]):
                if stop:
                    break
                if any(d.startswith(g + "/") for g in gone) or not once(d, "a"):
                    continue
                self._attempt_note = ""
                why, files = self.eval_attempt(d)
                if why in ("not an attempt dir",):
                    continue
                v = self.handle("a", d, files or [d], why, os.lstat(d).st_mtime)
                if v in ("DELETED", "WOULD"):
                    gone.append(d)
                stop = v == "ALERT"
        for cls, key in (("b", "spef"), ("c", "place")):
            if cls not in classes or stop:
                continue
            for p in sorted(self.found[key]):
                if stop:
                    break
                d = os.path.dirname(p)
                if "/results/" not in d or any(d.startswith(g + "/") for g in gone) or not once(d, cls):
                    continue
                why, kit, files = self.eval_trim(cls, d)
                if why in ("nothing",) or (why or "").startswith("no "):
                    continue
                try:
                    mt = os.lstat(p).st_mtime
                except OSError:
                    continue
                v = self.handle(cls, d, files, why, mt)
                stop = v == "ALERT"
        if "d" in classes and not stop and getattr(a, "aggressive", False):
            self.prune_lane_trees(gone)
        if "s" in classes and not stop:
            for unit in sorted(self.stub_units()):
                if stop:
                    break
                if not once(unit, "s"):
                    continue
                why, cands, held = self.eval_stub(unit)
                if why in ("nothing to trim", "no ARCHIVED.json"):
                    continue
                size = sum(d_ for _, _, d_, _ in cands)
                note = ",".join(f"{k}={n}" for k, n in sorted(held.items()))
                verdict = "SKIP" if why else ("WOULD" if not a.apply else "STUB")
                if not why and a.apply:
                    self.load_protected()                    # a row added meanwhile must stop us
                    self.live.refresh()
                    w2, c2, h2 = self.eval_stub(unit)
                    if w2:
                        verdict, why = "SKIP", "recheck: " + w2
                    else:
                        try:
                            size, err = self.stub_apply(unit, c2, h2)
                            if err:
                                verdict, why = "ALERT", err
                                self.recheck_hits += 1
                                self.alerts.append(f"s\t{unit}\t{err}")
                            else:
                                verdict = "STUBBED"
                        except OSError as e:
                            verdict, why = "ERROR", str(e)[:200]
                self.rows.append([time.strftime("%F %T"), self.host, "s", verdict, " ".join((why or note).split())[:300], unit,
                                  f"{len(cands)} files", size, int(os.lstat(unit).st_mtime)])
                stop = verdict == "ALERT"
        mdir = os.path.join(a.state, "manifests")
        os.makedirs(mdir, exist_ok=True)
        mf = os.path.join(mdir, f"AUTOCLEAN-auto-{self.host}-{stamp()}.tsv")
        with open(mf, "w") as fh:
            fh.write("time\thost\tclass\tverdict\treason\tpath\tfiles\tbytes\tmtime\n")
            for r in self.rows:
                fh.write("\t".join(str(x) for x in r) + "\n")
        tot = {}
        for r in self.rows:
            k = (r[2], r[3])
            n, b = tot.get(k, (0, 0))
            tot[k] = (n + 1, b + int(r[7]))
        for (cls, v), (n, b) in sorted(tot.items()):
            say(f"TOTAL class {cls} {v}: {n} rows {b / 1e9:.2f} GB")
        skips = {}
        for r in self.rows:
            if r[3] == "SKIP":
                k = r[2] + " " + r[4].split(":")[0].split(" ")[0]
                skips[k] = skips.get(k, 0) + 1
        say("SKIPS " + " ".join(f"{k}={n}" for k, n in sorted(skips.items())))
        say(f"PROTECTED/COUNTED HITS AT RECHECK: {self.recheck_hits} (must be 0)")
        say(f"MANIFEST {mf}")
        if self.alerts:
            with open(alert_f, "w") as fh:
                fh.write(f"{time.strftime('%F %T %Z')} ot-autoclean ALERT on {self.host}: a protected/counted path matched "
                         f"a delete candidate at recheck; deletes stopped.\n" + "\n".join(self.alerts) + "\n")
            say(f"ALERT written {alert_f}")
            return 3
        if a.wt_reaper:
            union = os.path.join(a.state, "protected-union.txt")
            self.write_union(union)
            cmd = [sys.executable, "-I", a.wt_reaper, "--protected-dbs", union, "--protected-dbs-repo", "",
                   "--idle-h", str(max(a.wt_reaper_idle_h, LOCAL_WT_IDLE_H) if self.host == "localhost" else a.wt_reaper_idle_h)] + (
                   ["--rescue-dir", LOCAL_RESCUE_DIR] if self.host == "localhost" else []) + [
                   "--roots"] + dedupe_roots(self.roots + [os.path.join(HOME, "wt")]) + (["--apply"] if a.apply else [])
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.wt_reaper_timeout)
                with open(os.path.join(a.state, "wt-reaper.log"), "a") as fh:
                    fh.write(f"=== {time.strftime('%F %T')} {' '.join(cmd)}\n{r.stdout}{r.stderr}")
                last = (r.stdout.strip().splitlines() or [""])[-1]
                say(f"wt-reaper rc {r.returncode}: {last[:300]}")
            except subprocess.TimeoutExpired:
                say("wt-reaper timed out")
        return 0


# ------------------------------------------------------------------ signed units (archive, host side)
def unit_of(record):
    d = os.path.dirname(record)
    return os.path.dirname(d) if os.path.basename(d) == "signoff" else d


def unit_files(unit, roots=None):
    """[(path, size, mtime)] the archive copies for a signed unit: the unit tree minus heavy run trees, plus every
    regular file its signed records cite, plus 6_final.* and *.lef/*.lib abstracts next to a cited 6_final.odb"""
    out, cites = {}, set()
    for dp, dns, fns in os.walk(unit):
        dns[:] = [d for d in dns if d not in HEAVY_DIRS and not d.startswith("attempt_")
                  and not os.path.islink(os.path.join(dp, d))]
        for f in fns:
            p = os.path.join(dp, f)
            if f in ("ARCHIVED.json", STUB_MARKER) and dp == unit:
                continue
            out[p] = None
            if f in RECORD_NAMES or f.endswith(".signoff.json"):
                signed, text = read_record(p)
                if signed:
                    cites |= text_paths(text)
    roots = [os.path.realpath(r) for r in (roots or DEFAULT_ROOTS)]
    for c in sorted(cites):
        if not any(os.path.realpath(c).startswith(r + "/") for r in roots):
            continue                                  # only scratch-root files (not platform libs, not other trees)
        if os.path.isfile(c) and not os.path.islink(c):
            out[c] = None
            if os.path.basename(c) == "6_final.odb":
                d = os.path.dirname(c)
                for f in os.listdir(d):
                    if f.startswith("6_final.") or f.endswith((".lef", ".lib", ".lib.gz")):
                        out[os.path.join(d, f)] = None
    res = []
    for p in sorted(out):
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if stat.S_ISREG(st.st_mode):
            res.append((p, st.st_size, int(st.st_mtime)))
    return res


def archived_ok(unit, files):
    try:
        d = jl(os.path.join(unit, "ARCHIVED.json"))
        rec = {f["path"]: (f["size"], f["mtime"]) for f in d["files"]}
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return len(rec) == len(files) and all(rec.get(p) == (s, m) for p, s, m in files)


def in_git_checkout(u):
    """class s: a signed unit inside a git checkout is a tracked view copy in a source tree (views live on origin/main)"""
    a = u
    while depth(a) > LANE_DEPTH:
        if os.path.lexists(os.path.join(a, ".git")):
            return True
        a = os.path.dirname(a)
    return False


def list_signed_main(a):
    roots = dedupe_roots(a.roots)
    found = scan_roots(roots, a.find_timeout)
    if found is None:
        say(json.dumps({"error": "scan failed"}))
        return 2
    units = {}
    for r in found["record"]:
        signed, _ = read_record(r)
        if signed:
            units.setdefault(unit_of(r), []).append(r)
    for u in sorted(units):
        if any(u.startswith(v + "/") for v in units):          # nested unit: the outer one covers it
            continue
        files = unit_files(u, roots)
        print(json.dumps({"unit": u, "archived": archived_ok(u, files), "files": files,
                          "bytes": sum(s for _, s, _ in files)}), flush=True)
    return 0


def run_pool(fn, items, workers):
    """DISK-1111: fn(item) for every item, up to `workers` at a time -> [(item-result...)] in input order"""
    if workers <= 1:
        return [fn(i) for i in items]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def hash_main(a):
    """stdin: one path per line (paths relative to --base when given) -> JSON {path: [size, sha256]}"""
    out = {}
    for ln in sys.stdin.read().splitlines():
        if not ln:
            continue
        p = os.path.join(a.base, ln.lstrip("/")) if a.base else ln
        try:
            st = os.lstat(p)
            out[ln] = [st.st_size, sha256(p)] if stat.S_ISREG(st.st_mode) else None
        except OSError:
            out[ln] = None
    json.dump(out, sys.stdout, sort_keys=True)
    return 0


def mark_archived_main(a):
    """stdin: {"archive": path, "sha": {path: [size, sha]}, "verify": str}; writes <unit>/ARCHIVED.json when the
    unit's current files still match the hashed list"""
    d = json.load(sys.stdin)
    files = unit_files(a.unit, dedupe_roots(a.roots))
    sha = d["sha"]
    if sorted(p for p, _, _ in files) != sorted(sha) or any(sha[p][0] != s for p, s, _ in files):
        say(json.dumps({"ok": False, "error": "unit changed since hashing"}))
        return 2
    rec = {"schema": "opentallas.archived.v2", "writer": "tools/fleet/ot-autoclean.py", "lane": "AUTOCLEAN-7",
           "rule": "OWNER 2026-11-07 18:1x: copy signed results to the AGIdock archive (copy only; never deleted here)",
           "archive": d["archive"], "date": time.strftime("%F %T %Z"), "verify": d.get("verify", ""),
           "nfiles": len(files), "bytes": sum(s for _, s, _ in files),
           "files": [{"path": p, "size": s, "mtime": m, "sha256": sha[p][1]} for p, s, m in files]}
    t = os.path.join(a.unit, ".ARCHIVED.json.tmp")
    with open(t, "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(t, os.path.join(a.unit, "ARCHIVED.json"))
    say(json.dumps({"ok": True, "nfiles": len(files)}))
    return 0


# ------------------------------------------------------------------ localhost driver
class Remote:
    def __init__(self, ssh, agidock_ssh, timeout):
        self.ssh = shlex.split(os.path.expanduser(ssh))
        self.agi = shlex.split(os.path.expanduser(agidock_ssh))
        self.timeout = timeout

    def argv(self, h):
        """LOCALHOST_1111: the driver's own host runs its commands locally (no ssh to itself)"""
        return ["bash", "-c"] if h == "localhost" else self.ssh + ([h] if h else [])

    def host(self, h, cmd, inp=None, timeout=None, binary=False):
        argv = self.argv(h) + ["cd / && " + cmd]
        return subprocess.run(argv, input=inp, capture_output=True, text=not binary,
                              timeout=timeout or self.timeout)

    def agidock(self, cmd, inp=None, timeout=None):
        return subprocess.run(self.agi + ["cd / && " + cmd], input=inp, capture_output=True, text=True,
                              timeout=timeout or self.timeout)


def tar_stream(src_argv, src_cmd, dst_argv, dst_cmd, file_list, timeout):
    """src: tar the listed files (stdin, NUL separated) -> stdout; dst: unpack stdin.  Both rc must be 0."""
    p1 = subprocess.Popen(src_argv + ["cd / && " + src_cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    p2 = subprocess.Popen(dst_argv + ["cd / && " + dst_cmd], stdin=p1.stdout, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    p1.stdout.close()
    p1.stdin.write(b"".join(p.lstrip("/").encode() + b"\0" for p in file_list))
    p1.stdin.close()
    try:
        o2, e2 = p2.communicate(timeout=timeout)
        p1.wait(timeout=60)
    except subprocess.TimeoutExpired:
        p1.kill()
        p2.kill()
        return False, "timeout"
    e1 = p1.stderr.read().decode(errors="replace")
    ok = p1.returncode == 0 and p2.returncode == 0
    return ok, f"src rc {p1.returncode} {e1.strip()[:150]} dst rc {p2.returncode} {e2.decode(errors='replace').strip()[:150]}"


class Driver:
    store_new = []                 # record-store files added in this drive (COUNT-ARCHIVE-1)
    def __init__(self, a):
        self.a = a
        self.r = Remote(a.ssh, a.agidock_ssh, a.timeout)
        self.script = os.path.abspath(SELF)
        self.tools = os.path.expanduser(a.tools_dir)
        self.rstate = a.remote_state
        self.py = f"python3 -I {shlex.quote(self.tools + '/ot-autoclean.py')}"

    def dx_snapshot(self, out):
        """DESIGN_EXPORT_1112 gate file for the hosts; any failure -> HOLD ALL (default on, never blocks the drive)"""
        a = self.a
        dxf = os.path.join(out, DX_FILE)
        if a.design_export_hook and os.path.exists(a.design_export_hook):
            try:
                r = subprocess.run([sys.executable, "-I", a.design_export_hook, "snapshot", "--out", dxf]
                                   + shlex.split(a.design_export_args), capture_output=True, text=True, timeout=600)
                say(f"snapshot: design export gate rc {r.returncode} {(r.stdout or r.stderr).strip()[-200:]}")
            except (OSError, subprocess.SubprocessError) as e:
                say(f"snapshot: design export gate failed {e!r}")
        if not os.path.exists(dxf):   # DESIGN_EXPORT_1112 default ON: no ledger -> hosts hold every routed DB
            with open(dxf, "w") as fh:
                json.dump({"all": True, "ledger": [], "why": "design export snapshot unavailable"}, fh)
            say("snapshot: design export gate HOLD ALL (no ledger)")

    def dx_drain(self):
        """DESIGN_EXPORT_1112: start the hook's drain (cut + publish the held DBs under ot-run) detached, so the holds
        this run placed are released by a later run; one drain at a time (its own lock), never blocks the drive"""
        a = self.a
        if not (a.design_export_hook and os.path.exists(a.design_export_hook) and a.design_export_drain > 0):
            return
        log = os.path.join(STATE, "design_export_drain.log")
        os.makedirs(STATE, exist_ok=True)
        with open(log, "a") as fh:
            subprocess.Popen([sys.executable, "-I", a.design_export_hook, "drain", "--max", str(a.design_export_drain)],
                             stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        say(f"design export drain started (max {a.design_export_drain}; log {log})")

    def build_snapshot(self, out):
        a = self.a
        os.makedirs(out, exist_ok=True)
        rows = build_protected_union(a.coord)
        check_required_sources(rows, "snapshot union")
        with open(os.path.join(out, "protected.tsv"), "w") as fh:
            fh.write("".join(f"{p}\t{w}\n" for p, w in rows))
        qf = os.path.join(a.coord, "lanes/COORD-REVIEW-QUEUE.md")
        paths, words = parse_queue(rd(qf), now_s(), a.queue_hours)
        with open(os.path.join(out, "queue.json"), "w") as fh:
            json.dump({"paths": sorted(paths), "words": sorted(words)}, fh)
        kw = None
        if a.kitwave_state:                          # local files (tests / a host with the state)
            r = subprocess.run([sys.executable, "-I", self.script, "kitwave-reduce", "--state-json", a.kitwave_state,
                                "--stages-tsv", a.kitwave_stages], capture_output=True, text=True, timeout=600)
            kw = r.stdout if r.returncode == 0 else None
        elif a.kitwave_host:
            r = self.r.host(a.kitwave_host, "timeout 600 python3 -I - kitwave-reduce", inp=rd(self.script),
                            timeout=900)
            kw = r.stdout if r.returncode == 0 else None
        if kw:
            json.loads(kw)
            with open(os.path.join(out, "kitwave.json"), "w") as fh:
                fh.write(kw)
        else:
            say("snapshot: kit-wave state unavailable; hosts skip class a")
        self.dx_snapshot(out)
        n_store = write_store_index(a.coord, os.path.join(out, STORE_INDEX))
        say(f"snapshot: signed-store index {n_store} entries")
        with open(os.path.join(out, "meta.json"), "w") as fh:
            json.dump({"created": now_s(), "created_h": time.strftime("%F %T %Z"), "by": socket.gethostname(),
                       "protected_rows": len(rows), "queue_paths": len(paths)}, fh)
        say(f"snapshot {out}: protected {len(rows)} rows, queue paths {len(paths)} words {len(words)}, "
            f"kit-wave {'yes' if kw else 'NO'}")
        return out

    def push(self, h, snap):
        """tools + snapshot to the host (atomic dir swap)"""
        here = os.path.dirname(self.script)
        tb = tempfile.mkdtemp(prefix="ac7push")
        try:
            os.makedirs(os.path.join(tb, "tools"))
            shutil.copy(self.script, os.path.join(tb, "tools/ot-autoclean.py"))
            wr = os.path.join(here, "wt-reaper.py")
            if os.path.exists(wr):
                shutil.copy(wr, os.path.join(tb, "tools/wt-reaper.py"))
            shutil.copytree(snap, os.path.join(tb, "snapshot"))
            data = subprocess.run(["tar", "-C", tb, "-cf", "-", "tools", "snapshot"], capture_output=True).stdout
        finally:
            shutil.rmtree(tb, ignore_errors=True)
        st, td = shlex.quote(self.rstate), shlex.quote(self.tools)
        cmd = (f"set -e; mkdir -p {st} {td}; T=$(mktemp -d {st}/.push.XXXXXX); tar -C $T -xf -; "
               f"cp $T/tools/* {td}/; rm -rf {st}/snapshot.old; if [ -d {st}/snapshot ]; then mv {st}/snapshot "
               f"{st}/snapshot.old; fi; mv $T/snapshot {st}/snapshot; rm -rf $T {st}/snapshot.old")
        r = self.r.host(h, cmd, inp=data, binary=True)
        return r.returncode == 0, (r.stderr or b"").decode(errors="replace")[:200]

    def archive(self, h, rows):
        a = self.a
        r = self.r.host(h, f"timeout {a.find_timeout + 600} {self.py} list-signed --roots {' '.join(map(shlex.quote, a.roots))}",
                        timeout=a.find_timeout + 900)
        if r.returncode:
            say(f"{h}: list-signed failed rc {r.returncode} {r.stderr.strip()[:200]}")
            return False
        base = f"{a.archive_root.rstrip('/')}/{h}"
        todo = [json.loads(ln) for ln in r.stdout.splitlines() if ln.startswith("{")]
        new = [u for u in todo if not u.get("archived")]
        say(f"{h}: signed units {len(todo)}, already archived {len(todo) - len(new)}, to archive {len(new)} "
            f"({sum(u['bytes'] for u in new) / 1e9:.2f} GB)")
        def one(u):
            files = [p for p, _, _ in u["files"]]
            dest = base + u["unit"]
            if not a.apply:
                say(f"WOULD-ARCHIVE {h}:{u['unit']} files {len(files)} bytes {u['bytes']} -> {dest}")
                rows.append([h, u["unit"], len(files), u["bytes"], dest, "-", "WOULD-ARCHIVE"])
                return True
            lst = "\n".join(files) + "\n"
            hs = self.r.host(h, f"nice -n 10 {self.py} hash", inp=lst, timeout=a.timeout)
            try:
                src = json.loads(hs.stdout)
            except ValueError:
                src = None
            comp, decomp = ("zstd -q -T8 -3 -c", "zstd -q -d -c") if a.compress == "zstd" else ("cat", "cat")
            ok, msg = (False, "hash failed") if not src or None in src.values() else tar_stream(
                self.r.argv(h), f"set -o pipefail; nice -n 10 tar -C / --null -T - -cf - | {comp}",
                self.r.agi, f"set -o pipefail; mkdir -p {shlex.quote(base)} && {decomp} | tar -C {shlex.quote(base)} -xf -",
                files, a.timeout)
            verify = "-"
            if ok:
                ds = self.r.agidock(f"nice -n 10 {a.agidock_python} hash --base {shlex.quote(base)}", inp=lst)
                try:
                    dst = json.loads(ds.stdout)
                except ValueError:
                    dst = None
                nb = sum(v[0] for v in src.values())
                if dst == src:
                    verify = f"OK files {len(src)} bytes {nb} sha256 all match"
                else:
                    ok, msg = False, "verify mismatch"
            if ok:
                m = self.r.host(h, f"{self.py} mark-archived --unit {shlex.quote(u['unit'])} --roots "
                                   f"{' '.join(map(shlex.quote, a.roots))}",
                                inp=json.dumps({"archive": dest, "sha": src, "verify": verify}))
                ok = m.returncode == 0
                msg = m.stdout.strip()[:200]
            if verify.startswith("OK"):            # a verified copy, even when the marker cannot be written (read-only src tree)
                self.store_ingest(h, src, base)
            act = "ARCHIVED" if ok else f"FAIL {msg}"
            say(f"{act} {h}:{u['unit']} {verify}")
            rows.append([h, u["unit"], len(files), u["bytes"], dest, verify, act])
            return ok
        ok_all = all(run_pool(one, new, max(1, int(getattr(a, "archive_jobs", 1) or 1))))
        return ok_all

    def store_ingest(self, h, src, base):
        """COUNT-ARCHIVE-1: a newly archived signed unit enters the durable record store (~/coord/signed-store), which the counter reads.
        A failure never fails the archive: it is logged and the next archive of the unit (or a backfill) adds the row."""
        try:
            sys.path.insert(0, os.path.join(self.a.coord, "tools"))
            import signed_store
            for eid in signed_store.ingest(h, src, base):
                self.store_new.append(os.path.relpath(signed_store.entry_path(eid), self.a.coord))
                say(f"STORE {h} {eid[:12]}")
        except Exception as e:                                # the archive itself succeeded
            say(f"STORE INGEST FAILED {h}: {type(e).__name__} {str(e)[:300]}")

    def collect(self, h, prune):
        """copy the host's manifests (its timer runs and this drive's run) not yet in <coord>/lanes/prune"""
        md = shlex.quote(self.rstate + "/manifests")
        r = self.r.host(h, f"ls -1 {md} 2>/dev/null | tail -n 48")
        out = []
        for name in r.stdout.split():
            if not re.fullmatch(r"AUTOCLEAN-auto-[\w.-]+-\d{8}-\d{6}\.tsv", name):
                continue
            f = os.path.join(prune, name)
            if os.path.exists(f):
                continue
            c = self.r.host(h, f"cat {md}/{name}")
            if c.returncode == 0:
                os.makedirs(prune, exist_ok=True)
                with open(f + ".tmp", "w") as fh:
                    fh.write(c.stdout)
                os.replace(f + ".tmp", f)
                out.append(f)
        return out

    def install_agidock(self):
        r = self.r.agidock(f"mkdir -p {shlex.quote(self.tools)} && cat > {shlex.quote(self.tools)}/ot-autoclean.py.tmp && "
                           f"mv {shlex.quote(self.tools)}/ot-autoclean.py.tmp {shlex.quote(self.tools)}/ot-autoclean.py",
                           inp=rd(self.script))
        return r.returncode == 0

    def main(self):
        a = self.a
        st = stamp()
        snapdir = tempfile.mkdtemp(prefix="ot-autoclean-snap-")
        prune = os.path.join(a.coord, "lanes/prune")
        written = []
        try:
            self.build_snapshot(snapdir)
            if a.archive and a.apply and not self.install_agidock():
                say("agidock: cannot install the verify helper; archive skipped")
                a.archive = False
            for h in a.hosts:
                ok, msg = self.push(h, snapdir)
                if not ok:
                    say(f"{h}: push failed {msg}")
                    continue
                rows = []
                if a.archive:
                    self.archive(h, rows)
                    if rows and a.collect:
                        f = os.path.join(prune, f"AUTOCLEAN-archive-{h}-{st}.tsv")
                        os.makedirs(prune, exist_ok=True)
                        with open(f, "w") as fh:
                            fh.write("host\tunit\tfiles\tbytes\tarchive_path\tverify\taction\n")
                            fh.write("".join("\t".join(map(str, x)) + "\n" for x in rows))
                        written.append(f)
                if a.run:
                    extra = " ".join(shlex.quote(x) for x in shlex.split(a.run_args))
                    r = self.r.host(h, f"timeout {a.run_timeout} {self.py} run --host {h} --state {shlex.quote(self.rstate)} "
                                       f"--snapshot {shlex.quote(self.rstate + '/snapshot')} "
                                       f"--wt-reaper {shlex.quote(self.tools + '/wt-reaper.py')}"
                                       f"{' --apply' if a.apply else ''} {extra}", timeout=a.run_timeout + 120)
                    out = r.stdout
                    dxreq = "".join(ln + "\n" for ln in out.splitlines() if ln.startswith("DXREQ\t"))
                    if dxreq and a.design_export_hook:
                        q = subprocess.run([sys.executable, "-I", a.design_export_hook, "enqueue"], input=dxreq,
                                           capture_output=True, text=True, timeout=120)
                        say(f"{h}: {(q.stdout or q.stderr).strip()[-200:]}")
                    for ln in out.splitlines():
                        if ln.startswith(("TOTAL", "SKIPS", "PROTECTED", "controls", "ALERT", "wt-reaper")):
                            say(f"{h}: {ln}")
                    say(f"{h}: run rc {r.returncode}{' ' + r.stderr.strip()[-200:] if r.returncode else ''}")
                if a.collect:
                    written += self.collect(h, prune)
            self.dx_drain()
            if written:
                say("collected " + " ".join(written))
            written += [os.path.join(a.coord, x) for x in self.store_new]
            if a.commit and written:
                rel = [os.path.relpath(f, a.coord) for f in written]
                r = subprocess.run(["timeout", "280", os.path.join(a.coord, "bin/coord-commit.sh"),
                                    f"AUTOCLEAN auto manifests {st}"] + rel, cwd=a.coord, capture_output=True, text=True)
                say(f"coord-commit rc {r.returncode} {r.stdout.strip()[-200:]} {r.stderr.strip()[-200:]}")
        finally:
            shutil.rmtree(snapdir, ignore_errors=True)
        return 0


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="host job (dry unless --apply)")
    r.add_argument("--apply", action="store_true")
    r.add_argument("--design-export", choices=("on", "off"), default="on",
                   help="DESIGN_EXPORT_1112 export-before-delete gate (default on; off only by explicit owner/COORD call)")
    r.add_argument("--host", default="")
    r.add_argument("--state", default=STATE)
    r.add_argument("--snapshot", default=os.path.join(STATE, "snapshot"))
    r.add_argument("--max-snapshot-age-h", type=float, default=3.0)
    r.add_argument("--min-protected", type=int, default=100, help="refuse a union smaller than this")
    r.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    r.add_argument("--classes", default="abc", help="a b c = deletes of unsigned attempts / ODB trims; s = stub-trim of signed units "
                   "whose ARCHIVED.json is verified (never in the default set)")
    r.add_argument("--stub-protected-units", action="store_true",
                   help="class s: a protected-list row that EQUALS or CONTAINS the unit does not hold the unit (the stub keeps every "
                        "protected path inside it and the unit's own records and cited files); default off = such a unit is skipped")
    r.add_argument("--docker", default="docker", help="docker command ('' = no docker on this host)")
    r.add_argument("--aliases", default=None, help="findmnt -rn -o TARGET,SOURCE text file (tests)")
    r.add_argument("--find-timeout", type=int, default=3600)
    r.add_argument("--wt-reaper", default=os.path.join(os.path.dirname(os.path.abspath(SELF)), "wt-reaper.py"),
                   help="'' = skip the worktree reaper")
    r.add_argument("--wt-reaper-timeout", type=int, default=5400)
    r.add_argument("--queuename-skip-superseded", action="store_true",
                   help="class a: a queue-named item name does not protect superseded (older) attempts; COORD ruling")
    r.add_argument("--queuename-skip-trim-c", action="store_true",
                   help="class c only: a bare queue-post name does not block the 2_x/3_x intermediate trim (a queue PATH "
                        "still does); COORD ruling")
    r.add_argument("--srccopy", action="store_true",
                   help="SRCCOPY_1111: git-tracked unmodified signed records whose HEAD is on origin and whose canonical copy is in "
                        "the signed store are source copies, not counted (COORD 11-11)")
    r.add_argument("--union-real-sources-only", action="store_true",
                   help="do not read protect.d/protected-dbs.txt (this job's own union) back as a keep source; a path stays "
                        "only while a real source names it; finished ot-run spill records (spill_pending/*.done) stop holding "
                        "paths, pending *.json records still hold (COORD 11-08)")
    r.add_argument("--aggressive", action="store_true",
                   help="OWNER 11-12 aggressive mode: keep only live jobs, kit-wave-referenced trees, unarchived signed units and the protected lists; "
                        "2 h grace, no queue-name/path holds on terminal attempts, attempts without a state row go, class d prunes lane trees")
    r.add_argument("--rm-jobs", type=int, default=16, help="parallel rm workers per deleted tree (1 = serial)")
    r.add_argument("--d-any-root", action="store_true", help=argparse.SUPPRESS)
    r.add_argument("--keep-expire-h", type=float, default=0.0,
                   help="DISK-1111: a .keep file untouched for this many hours (168 = 7 days) no longer holds a unit; 0 = off")
    r.add_argument("--c-old-keep-h", type=float, default=0.0,
                   help="class c only: an ancestor .keep older than this many hours does not block the trim of a finished "
                        "or superseded kit (6_final.odb, signoff.json or a later attempt); 0 = off (COORD 11-08)")
    r.add_argument("--wt-reaper-idle-h", type=float, default=6.0, help="worktree idle hours before the reaper may remove it (fleet 6 h rule)")
    ls = sub.add_parser("list-signed")
    ls.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    ls.add_argument("--find-timeout", type=int, default=3600)
    hs = sub.add_parser("hash")
    hs.add_argument("--base", default="")
    ma = sub.add_parser("mark-archived")
    ma.add_argument("--unit", required=True)
    ma.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    kr = sub.add_parser("kitwave-reduce")
    kr.add_argument("--state-json", default=os.path.join(HOME, "coord/autopilot/kit_wave_state.json"))
    kr.add_argument("--stages-tsv", default=os.path.join(HOME, "coord/autopilot/kit_wave_stages.tsv"))
    dr = sub.add_parser("drive", help="localhost driver: snapshot -> push -> archive -> host runs -> collect")
    dr.add_argument("--archive-jobs", type=int, default=8, help="DISK-1111: signed units archived in parallel per host (1 = old serial pace)")
    dr.add_argument("--hosts", default=",".join(HOSTS))
    dr.add_argument("--apply", action="store_true", help="really archive and pass --apply to the host runs")
    dr.add_argument("--no-archive", dest="archive", action="store_false")
    dr.add_argument("--no-run", dest="run", action="store_false")
    dr.add_argument("--no-collect", dest="collect", action="store_false")
    dr.add_argument("--commit", action="store_true", help="commit collected manifests with coord-commit.sh")
    dr.add_argument("--coord", default=os.path.join(HOME, "coord"))
    dr.add_argument("--queue-hours", type=float, default=25.0)
    dr.add_argument("--kitwave-host", default="intel2")
    dr.add_argument("--kitwave-state", default="", help="local kit_wave_state.json instead of the hub (tests)")
    dr.add_argument("--kitwave-stages", default="")
    dr.add_argument("--ssh", default="ssh -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=10")
    dr.add_argument("--agidock-ssh", default=AGIDOCK_SSH)
    dr.add_argument("--agidock-python", default=f"python3 -I {TOOLS_DIR}/ot-autoclean.py")
    dr.add_argument("--archive-root", default=ARCHIVE_ROOT)
    dr.add_argument("--compress", default="zstd", choices=("zstd", "none"))
    dr.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    dr.add_argument("--find-timeout", type=int, default=3600)
    dr.add_argument("--tools-dir", default=TOOLS_DIR)
    dr.add_argument("--remote-state", default=STATE)
    dr.add_argument("--timeout", type=int, default=21600)
    dr.add_argument("--run-timeout", type=int, default=10800)
    dr.add_argument("--design-export-hook", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(SELF))),
                    "fleet_viz", "design_export_hook.py"), help="fleet_viz/design_export_hook.py (DESIGN_EXPORT_1112, default ON: "
                    "hosts hold units until the design explorer has cut their routed ODBs; missing or failing = hold all)")
    dr.add_argument("--design-export-drain", type=int, default=20, help="DBs the detached drain cuts per drive (0 = no drain)")
    dr.add_argument("--design-export-args", default="", help="extra args for its snapshot, one string (--index/--store)")
    dr.add_argument("--run-args", default="", help="extra args for the host run, one string (--run-args='--classes b')")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        a.classes = set(a.classes)
        try:
            return Job(a).run()
        except (RuntimeError, OSError, ValueError, KeyError) as e:
            say(f"ot-autoclean: ABORT {e!r}; nothing deleted")
            return 2
    if a.cmd == "list-signed":
        return list_signed_main(a)
    if a.cmd == "hash":
        return hash_main(a)
    if a.cmd == "mark-archived":
        return mark_archived_main(a)
    if a.cmd == "kitwave-reduce":
        return kitwave_reduce_main(a)
    if a.cmd == "drive":
        a.hosts = [h for h in a.hosts.split(",") if h]
        return Driver(a).main()
    return 1


if __name__ == "__main__":
    sys.exit(main())
