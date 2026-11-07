#!/usr/bin/env python3
"""ot_autoclean.py (AUTOCLEAN-1, OWNER 2026-11-06 22:4x: cleanup runs automatically after a job finishes).

The hub cron drives one sweep per fleet host.  A sweep finds every kit dir (a dir holding run/results/*/*/base) whose job
has ended, for any reason (clean exit, failure or kill), and empties the files nothing resumes from.  It is outside every
job's exit path, so it cannot change a job's exit code or result.

"Ended": no process has the kit as cwd, open file, or on its command line; no running container or mount holds it; and no
file under it changed for QUIET_MIN minutes.

What goes, only inside a finished kit that is not protected:
  substep   2_[1-4]_*.odb, 3_[1-5]_*.odb once the stage ODB (2_floorplan / 3_place) exists, is non-empty and is not older
  chain     5_3_fillcell.odb, 5_route.odb, 6_1_fill.odb once a non-empty, not older 6_final.odb exists (= eco_loop.TRIM_ODBS)
  failed    *-failed.odb in a wave attempt with a newer attempt beside it
  eco_iter  every .odb/.def/.gds/.spef under run/results of an eco pass dir that eco_loop.json names as neither best nor last
  stage_old 1_synth / 2_floorplan / 3_place / 4_cts odbs once a later stage odb exists, except in the newest attempt of a wave
            item (kit_resume needs them there; that is class stage_wave, counted but not applied until kit_resume can
            resume from the newest DB alone)
  cts_copy  4_1_cts.odb once 5_1_grt.odb exists (prd_mk takes the GRT DB as stage identity when it is absent)
  old_run   in a superseded wave attempt or eco pass: every run/ file of 1 MB or more that is not a log, report or record
OWNER 11-06 23:2x: open block = newest resume DB only.  One exception, because eco_loop needs them: a routed kit keeps 5_1_grt
and 5_2_route beside 6_final (prd_mk seeds from them and refuses a kit without 5_1_grt).
Sign-off, LEC, logs, reports, renders, sources and libs stay in every kit that is not superseded.

Files are EMPTIED, not unlinked: size 0, mtime kept.  run_kit.sh calls plain make, and the ORFS Makefile has 3_place.odb
depend on 3_5_place_dp.odb and 4_cts.odb on 4_1_cts.odb, so unlinking a sub-step would make an in-place relaunch rebuild the
whole stage.  With the empty file and its old mtime, make still sees the stage as up to date.  A file with more than one
hard link is never emptied (the write would reach the other link).

Kept whole (nothing touched) when the kit, its attempt / eco root, or an ancestor holds any of these:
  PROTECTED union (PROTECTED_FILES, every row on every host), .keep, PROVENANCE.json, signoff*.json with SIGNED / LOCAL_PASS /
  NEEDS_PARENT, ARCHIVED.json, a spill marker, .git; a path on a running command line (any host) or a mount; a path named by
  a live autopilot / wave row, kit_wave.json or a resign/owner table; a path named in the review queue in QUEUE_H hours.
Roots tok-*, kv-fn-* and tool trees are not scanned.  codex-* trees are in scope (OWNER 11-06 23:0x, finished runs only); ~/.codex never.
A git-locked worktree is not entered, and a file git tracks is never emptied.

Fail closed (nothing removed on that host): a list unreadable, empty or below MIN_ROWS; docker unreadable; or no protected
kit found in the same scan (the control hit proves the list really matched this host's paths).
A manifest row is written and fsynced before each file is emptied: ~/.local/state/ot-autoclean/manifest.tsv on the host.

OFF SWITCH: touch ~/.config/ot-autoclean/OFF on the hub (or OT_AUTOCLEAN=0).  The sweep then does nothing.
    ot_autoclean.py [--dry] [--host H ...] [--only PATHPREFIX] [--max-kits N] [--json]
"""
import json
import os
import re
import stat
import subprocess
import sys
import time

QUIET_MIN = 30
QUEUE_H = 12
STALE_H = 2             # coord state older than this: state unclear, nothing removed
MIN_ROWS = 100
HOSTS = ("intel2", "intel1", "epyc2", "epyc4")      # epyc5/6 are draining (OWNER 11-06)
OFF_FILE = "~/.config/ot-autoclean/OFF"
COORD = "~/coord"
PROTECTED_FILES = ("lanes/PROTECTED-DBS.txt", "PROTECTED-DBS.txt", "lanes/prune/ARCHIVE-PROTECTED.tsv")
CITE_ALL = ("autopilot/kit_wave.json", "autopilot/kit_wave_pending.tsv", "autopilot/auto_resign.tsv",
            "autopilot/auto_resign_suggest.tsv", "autopilot/OWNERS.tsv", "autopilot/signed.tsv", "autopilot/provisional.tsv",
            "lanes/RETIRED-PROTECTION-EXTRAS.tsv", "lanes/AUTO-RESIGN.tsv", "lanes/AUTO-RESIGN-HOLD.tsv")
QUEUE = "lanes/COORD-REVIEW-QUEUE.md"
SCAN_ROOTS = ("/srv/opentallas-scratch/claude", "/srv/opentallas-scratch2/claude", "/srv/opentallas-scratch3/claude",
              "/srv/opentallas-scratch/codex", "/srv/opentallas-scratch2/codex", "/srv/opentallas-scratch3/codex")
HOME_GLOBS = ("/home/ubuntu/wt-codex-*", "/home/ubuntu/scratch-codex-*")   # localhost Codex trees
SKIP_TOP = re.compile(r"^(tok-.*|tok_.*|kv-fn-.*|tools|seed|repos|data|git-mirror|flowhold|ttbatch|ttviews|"
                      r"closure-loop.*|closed-archive-gds|lost\+found|layout-viewer-store|viz-elem-store|ref_gate|moved|wt|"
                      r"hub-coord|\..*)$")
SKIP_DESCEND = {".git", "__pycache__", "src", "bind", "rtl", "obj_dir", "lec", "signoff", "views", "so"}
PATH_RE = re.compile(r"(?:/srv/opentallas-scratch[0-9]*|/home/ubuntu/scratch-root|/home/ubuntu/scratch)/[^\s\"'`\]\[,;()<>|*{}=:]+")
TOKEN_RE = re.compile(r"[A-Za-z0-9_.+-]+(?:/[A-Za-z0-9_.+-]+)*")
STATE_LIVE_DONE = re.compile(r"^(DONE-.*|CANCELLED|WITHDRAWN|REJECTED)$")
WAVE_DONE = {"FAIL", "CANCELLED"}
SIGNED_RE = re.compile(r'"\w*(?:status|verdict|result)"\s*:\s*"(SIGNED|LOCAL_PASS\w*|NEEDS_PARENT)"')
PROTECT_MARKS = {".keep", "PROVENANCE.json", "ARCHIVED.json", ".ot-run-spill-copy", ".ot-run-proof-away"}
SUB = {"substep2": (re.compile(r"^2_[1-4]_.*\.odb$"), "2_floorplan.odb"),
       "substep3": (re.compile(r"^3_[1-5]_.*\.odb$"), "3_place.odb"),
       "chain": (re.compile(r"^(5_3_fillcell|5_route|6_1_fill)\.odb$"), "6_final.odb")}
STAGE_OLD = ("1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb")
LATER = ("2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb", "5_2_route.odb", "5_route.odb", "6_final.odb")
OLD_KEEP_EXT = (".log", ".rpt", ".json", ".txt", ".png", ".md", ".tsv", ".csv", ".sdc", ".sh", ".mk", ".tcl", ".py")
UNLINK = {"old_run", "cts_copy"}      # never relaunched in place, or the reader already accepts the file being absent
ECO_EXT = (".odb", ".def", ".gds", ".gds.gz", ".spef")
GENERIC = {"kit", "gen", "run", "base", "src", "eco", "kits", "final"}
MARKER = ".ot_autoclean.json"
GATED = ("stage_wave",)     # counted in the dry run, not applied: kit_resume reads these from the newest attempt


# ---------------------------------------------------------------------------------------------- path sets
def norm(p):
    """the alias forms a path has on the fleet: scratch-root = scratch3"""
    p = os.path.normpath(p)
    if p == "/home/ubuntu/scratch-root" or p.startswith("/home/ubuntu/scratch-root/"):
        p = "/srv/opentallas-scratch3" + p[len("/home/ubuntu/scratch-root"):]
    return p


def ancestors(p):
    out = []
    while True:
        q = os.path.dirname(p)
        if q == p or len(q) < 2:
            return out
        out.append(q)
        p = q


class PathSet:
    """related(p): p equals a member, lies under one, or is an ancestor of one.  Members shallower than a lane root
    (/srv/x/claude) are ignored: they say nothing about any one kit."""

    def __init__(self, paths, realpath=True):
        self.s, self.a = set(), set()
        for raw in paths:
            forms = {norm(raw)}
            if realpath:
                try:
                    forms.add(os.path.realpath(norm(raw)))
                except OSError:
                    pass
            for x in forms:
                if x.count("/") < 4:
                    continue
                self.s.add(x)
                self.a.update(ancestors(x))

    def related(self, p):
        return p in self.s or p in self.a or any(q in self.s for q in ancestors(p))

    def near(self, p, levels=2):
        """as related, but a member above p counts only within `levels` dirs: a queue post or table that names a whole lane or
        wave root (.../claude/kit-wave) says nothing about one finished kit far below it"""
        return p in self.s or p in self.a or any(q in self.s for q in ancestors(p)[:levels])


def parse_rows(text):
    """every absolute path of a protected list, in any of its row forms (host<TAB>path, any<TAB>path, host:/path)"""
    out = []
    for ln in (text or "").splitlines():
        if ln.lstrip().startswith("#"):
            continue
        for f in ln.split("\t") if "\t" in ln else ln.split():
            f = f.strip()
            if ":/" in f and not f.startswith("/"):
                f = f.split(":", 1)[1]
            if f.startswith("/") and " " not in f:
                out.append(f.rstrip("/"))
                break
    return out


def queue_cites(text, now, hours=QUEUE_H):
    """-> (absolute paths, relative tokens) named in queue posts of the last `hours` h.  Continuation lines belong to the post above."""
    keep, on = [], False
    for ln in text.split("\n"):
        m = re.match(r"- (20\d\d-\d\d-\d\d \d\d:\d\d)", ln)
        if m:
            try:
                on = now - time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M")) < hours * 3600
            except ValueError:
                on = True
        if on:
            keep.append(ln)
    txt = "\n".join(keep)
    return sorted({os.path.normpath(m.rstrip(".:")) for m in PATH_RE.findall(txt)}), sorted(set(TOKEN_RE.findall(txt)))


def live_rows(state, wave):
    """paths named by autopilot rows that are not finished.  A finished row names a kit that may be cleaned."""
    out = set()
    for r in ((state or {}).get("jobs") or {}).values():
        if not STATE_LIVE_DONE.match(str(r.get("status") or "")):
            out.update(PATH_RE.findall(json.dumps(r)))
    for k, r in ((wave or {}).get("items") or {}).items():
        if r.get("status") not in WAVE_DONE:
            out.update(PATH_RE.findall(json.dumps(r)))
    for k, v in (wave or {}).items():
        if k != "items":
            out.update(PATH_RE.findall(json.dumps(v)))
    return {os.path.normpath(p.rstrip(".:")) for p in out}


# ---------------------------------------------------------------------------------------------- host side
def live_snapshot():
    """-> (paths, command-line text).  Raises when docker cannot be read: then the state is unclear."""
    paths, blob = set(), []
    me = os.getpid()
    for p in os.listdir("/proc"):
        if not p.isdigit() or int(p) == me:
            continue
        try:
            txt = open(f"/proc/{p}/cmdline", "rb").read().replace(b"\0", b" ").decode("utf-8", "replace")
            if "ot_autoclean" in txt:
                continue
            blob.append(txt)
            paths.update(PATH_RE.findall(txt))
            paths.add(os.readlink(f"/proc/{p}/cwd"))
        except OSError:
            continue
        try:
            for fd in os.listdir(f"/proc/{p}/fd"):
                try:
                    t = os.readlink(f"/proc/{p}/fd/{fd}")
                    if t.startswith("/"):
                        paths.add(t)
                except OSError:
                    pass
        except OSError:
            pass
    ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60)
    if ids.returncode:
        raise RuntimeError("docker ps failed")
    if ids.stdout.split():
        r = subprocess.run(["docker", "inspect", "--format", "{{range .Mounts}}{{.Source}}\n{{end}}"] + ids.stdout.split(),
                           capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise RuntimeError("docker inspect failed")
        paths.update(x.strip() for x in r.stdout.splitlines() if x.strip())
    with open("/proc/mounts") as f:
        for ln in f:
            c = ln.split()
            if len(c) > 1 and "/opentallas-scratch" in c[1] and c[1].count("/") >= 4:
                paths.add(c[1])
    return {norm(p) for p in paths if p.startswith("/")}, "\n".join(blob)


def is_live(k, base_re, live_set, blob):
    if live_set.related(k):
        return "live-path"
    if base_re and base_re.search(blob):
        return "live-cmdline"
    return ""


def git_locked(d):
    """a worktree with a lock file, or a .git file we cannot read"""
    p = os.path.join(d, ".git")
    if not os.path.isfile(p):
        return False
    try:
        with open(p) as f:
            g = f.read().split("gitdir:")[-1].strip()
    except OSError:
        return True
    return os.path.exists(os.path.join(g if os.path.isabs(g) else os.path.join(d, g), "locked"))


def find_kits(roots, only="", globs=HOME_GLOBS):
    seen, out, tops = set(), [], []
    for r in roots:
        if not os.path.isdir(r):
            continue
        rr = os.path.realpath(r)
        if rr in seen:
            continue
        seen.add(rr)
        for e in sorted(os.scandir(rr), key=lambda e: e.name):
            if not SKIP_TOP.match(e.name) and not e.is_symlink() and e.is_dir(follow_symlinks=False):
                tops.append(e.path)
    import glob
    tops += [p for g in globs for p in sorted(glob.glob(g)) if os.path.isdir(p) and not os.path.islink(p)]
    for top in tops:
        if only and not (top.startswith(only) or only.startswith(top + "/")):
            continue
        for d, ds, fs in os.walk(top):
            if ".git" in fs and git_locked(d):
                ds[:] = []
                continue
            if "run" in ds and os.path.isdir(os.path.join(d, "run", "results")):
                if not only or d.startswith(only):
                    out.append(d)
            ds[:] = [x for x in ds if x not in SKIP_DESCEND and x != "run" and not os.path.islink(os.path.join(d, x))]
    return out


def tracked(paths, cwd):
    """the subset of paths git tracks; None when cwd is in a repo and git cannot answer (then nothing goes)"""
    a = cwd
    while a not in ("/", "") and not os.path.lexists(os.path.join(a, ".git")):
        a = os.path.dirname(a)
    if a in ("/", ""):
        return set()
    try:
        r = subprocess.run(["git", "-C", a, "ls-files", "-z", "--"] + [os.path.relpath(p, a) for p in paths],
                           capture_output=True, timeout=120, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode:
        return None
    return {os.path.join(a, x.decode()) for x in r.stdout.split(b"\0") if x}


def group_root(k):
    """the set a kit is judged with: its wave attempt, or its eco loop root, else itself"""
    m = re.match(r"^(.*/attempt_\d+)(?:/|$)", k)
    if m:
        return m.group(1)
    p = os.path.dirname(k)
    if os.path.isfile(os.path.join(p, "eco_loop.json")) or re.fullmatch(r"i\d+[a-z]*", os.path.basename(k)):
        return p
    return k


def protect_scan(g):
    """-> (why or "", newest mtime of any file under g).  Any sign-off record, marker or unreadable record protects."""
    newest = 0.0
    for d, ds, fs in os.walk(g):
        ds[:] = [x for x in ds if x != "objects" and not os.path.islink(os.path.join(d, x))]
        for f in fs:
            if f in PROTECT_MARKS:
                return "mark:" + f, newest
            p = os.path.join(d, f)
            if f == MARKER:
                continue
            try:
                newest = max(newest, os.lstat(p).st_mtime)
            except OSError:
                continue
            if f.startswith("signoff") and f.endswith(".json"):
                try:
                    with open(p, errors="replace") as fh:
                        if SIGNED_RE.search(fh.read(1 << 22)):
                            return "signed", newest
                except OSError:
                    return "signed-unreadable", newest
    return "", newest


def ancestor_mark(k):
    for a in ancestors(k):
        if a.count("/") < 4:
            break
        for m in (".keep", "ARCHIVED.json", ".ot-run-spill-copy", ".ot-run-proof-away", "PROVENANCE.json"):
            if os.path.exists(os.path.join(a, m)):
                return m
    return ""


def newest_attempt(k):
    return bool(re.search(r"/attempt_\d+(?:/|$)", k)) and not superseded_attempt(k)


def superseded_attempt(k):
    m = re.match(r"^(.*)/attempt_(\d+)(?:/|$)", k)
    if not m:
        return False
    try:
        return any(re.fullmatch(r"attempt_\d+", x) and int(x[8:]) > int(m.group(2)) for x in os.listdir(m.group(1)))
    except OSError:
        return False


def eco_superseded(k):
    """True when k is a pass dir of a finished eco loop that eco_loop.json names as neither best nor the last iteration."""
    root = os.path.dirname(k)
    try:
        with open(os.path.join(root, "eco_loop.json")) as f:
            j = json.load(f)
    except (OSError, ValueError):
        return False
    its = j.get("iterations") or []
    if not j.get("verdict") or not its:
        return False
    keep = set()
    best = j.get("best")
    for it in ([best] if isinstance(best, dict) else []) + [its[-1]]:
        for x in [it.get("dir")] + list(it.get("pass_dirs") or []):
            if x:
                keep.add(os.path.basename(x.rstrip("/")))
    if isinstance(best, (str, int)):
        for it in its:
            if str(it.get("n")) == str(best) or it.get("dir") == best:
                keep.update(os.path.basename(x.rstrip("/")) for x in [it.get("dir")] + list(it.get("pass_dirs") or []) if x)
    return bool(keep) and os.path.basename(k) not in keep


def plan_kit(k):
    """-> [(class, path, blocks bytes, size, mtime)] the files this kit may empty.  Non-regular, linked, empty files never."""
    out = []
    def add(cls, p, st):
        out.append((cls, p, st.st_blocks * 512, st.st_size, st.st_mtime))
    if superseded_attempt(k) or eco_superseded(k):
        for d, ds, fs in os.walk(os.path.join(k, "run")):
            ds[:] = [x for x in ds if not os.path.islink(os.path.join(d, x))]
            for f in fs:
                p = os.path.join(d, f)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size >= 1 << 20 and not f.endswith(OLD_KEEP_EXT):
                    add("old_run", p, st)
        return out
    wave_newest = newest_attempt(k)
    for d, ds, fs in os.walk(os.path.join(k, "run", "results")):
        ds[:] = [x for x in ds if not os.path.islink(os.path.join(d, x))]
        for f in fs:
            p = os.path.join(d, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size == 0:
                continue
            if f == "4_1_cts.odb":
                try:
                    if os.stat(os.path.join(d, "5_1_grt.odb")).st_size > 0 and not wave_newest:
                        add("cts_copy", p, st)
                except OSError:
                    pass
                continue
            if f in STAGE_OLD:
                for n in LATER[LATER.index(f) + 1:] if f in LATER else LATER:
                    try:
                        b = os.stat(os.path.join(d, n))
                    except OSError:
                        continue
                    if b.st_size > 0 and b.st_mtime >= st.st_mtime:
                        add("stage_wave" if wave_newest else "stage_old", p, st)
                        break
                continue
            for cls, (rx, bnd) in SUB.items():
                if rx.match(f):
                    try:
                        b = os.stat(os.path.join(d, bnd))
                    except OSError:
                        break
                    if b.st_size > 0 and b.st_mtime >= st.st_mtime:
                        add(cls, p, st)
                    break
    return out


def empty_file(p, mtime):
    """size 0, mtime kept.  A kit a killed container left root-owned goes through sudo -n."""
    try:
        with open(p, "r+b") as f:
            f.truncate(0)
        os.utime(p, (mtime, mtime))
    except PermissionError:
        r = subprocess.run(["sudo", "-n", "sh", "-c", 'truncate -s0 -- "$1" && touch -m -d "@$2" -- "$1"', "x", p, repr(mtime)],
                           capture_output=True, timeout=60)
        if r.returncode:
            raise


def manifest_path(req):
    d = os.path.expanduser(req.get("state_dir") or "~/.local/state/ot-autoclean")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "manifest.tsv")


def sweep(req):
    """host side.  -> summary dict; one JSON line on stdout."""
    now = req.get("now") or time.time()
    dry = bool(req.get("dry"))
    res = dict(dry=dry, kits=0, verdicts={}, classes={}, class_files={}, held_gb={}, freed=0, files=0, errors=0, control_hits=0,
               planned_on_protected=[], sample={}, kit_rows=[])
    def tally(v, k=None):
        res["verdicts"][v] = res["verdicts"].get(v, 0) + 1
        if k and req.get("held_detail"):
            res["held_gb"][v] = res["held_gb"].get(v, 0) + sum(x[2] for x in plan_kit(k)) / 1e9
    prot = PathSet(req["protected"])
    if len(prot.s) < int(req.get("min_rows", MIN_ROWS)):
        res["fail_closed"] = f"protected list has {len(prot.s)} usable rows"
        return res
    cited = PathSet(req.get("cited") or [])
    tokens = set(req.get("tokens") or [])
    if "live" in req:
        live_paths, blob = set(req["live"]), req.get("blob", "")
    else:
        try:
            live_paths, blob = live_snapshot()
        except Exception as ex:
            res["fail_closed"] = f"live snapshot: {ex!r}"
            return res
    live = PathSet(list(live_paths) + list(req.get("other_host_live") or []), realpath=False)
    plans = []
    kits = find_kits(req["roots"], req.get("only") or "", ()) if req.get("roots") else find_kits(SCAN_ROOTS, req.get("only") or "")
    group_cache = {}
    max_kits = int(req.get("max_kits") or 0)
    for k in kits:
        res["kits"] += 1
        g = group_root(k)
        if prot.related(k) or prot.related(g):
            res["control_hits"] += 1
            tally("protected", k)
            continue
        if req.get("skip_codex") and re.search(r"/(codex[^/]*|wt-codex[^/]*|scratch-codex[^/]*)(/|$)", k):
            tally("codex-later", k)
            continue
        comps = k.split("/")
        tail2 = "/".join(comps[-2:])
        name = comps[-1]
        if cited.near(k) or tail2 in tokens or (name not in GENERIC and len(name) >= 8 and name in tokens):
            tally("cited", k)
            continue
        rx = None if name in GENERIC or len(name) < 4 else re.compile(r"(?<![\w.+-])" + re.escape(name) + r"(?![\w.+-])")
        lv = is_live(k, rx, live, blob) or (is_live(g, None, live, blob) if g != k else "")
        if lv:
            tally(lv, k)
            continue
        m = ancestor_mark(k)
        if m:
            tally("mark:" + m, k)
            continue
        if g not in group_cache:
            group_cache[g] = protect_scan(g)
        why, newest = group_cache[g]
        if why:
            tally(why, k)
            continue
        if now - newest < float(req.get("quiet_min", QUIET_MIN)) * 60:
            tally("quiet", k)
            continue
        try:
            with open(os.path.join(k, "run", MARKER)) as f:
                if float(json.load(f).get("newest", 0)) >= newest:
                    tally("already-clean")
                    continue
        except (OSError, ValueError, AttributeError):
            pass
        p = plan_kit(k)
        if p:
            t = tracked([x[1] for x in p], k)
            if t is None:
                tally("git-unclear")
                continue
            p = [x for x in p if x[1] not in t]
        if not p:
            tally("nothing-to-do")
            continue
        tally("planned")
        plans.append((k, p, newest))
        for cls, path, blk, _, _ in p:
            if prot.related(path):                     # independent of the kit-level check above
                res["planned_on_protected"].append(path)
            res["classes"][cls] = res["classes"].get(cls, 0) + blk
            res["class_files"][cls] = res["class_files"].get(cls, 0) + 1
        res["kit_rows"].append([k, sum(x[2] for x in p)])
        if max_kits and len(plans) >= max_kits:
            break
    res["kit_rows"] = sorted(res["kit_rows"], key=lambda r: -r[1])[:int(req.get("kit_rows", 15))]
    if res["planned_on_protected"]:
        res["fail_closed"] = "a planned file is on a protected path"
        return res
    if not res["control_hits"] and not req.get("no_control"):
        res["fail_closed"] = "no protected kit seen in this scan (no control hit)"
        return res
    if dry:
        return res
    man = manifest_path(req)
    with open(man, "a") as mf:
        for k, p, newest in plans:
            try:
                fresh, fresh_blob = (set(req["live"]), req.get("blob", "")) if "live" in req else live_snapshot()
            except Exception as ex:
                res["fail_closed"] = f"live re-check: {ex!r}"
                return res
            lv = PathSet(list(fresh) + list(req.get("other_host_live") or []), realpath=False)
            name = os.path.basename(k)
            rx = None if name in GENERIC or len(name) < 4 else re.compile(r"(?<![\w.+-])" + re.escape(name) + r"(?![\w.+-])")
            if is_live(k, rx, lv, fresh_blob) or protect_scan(group_root(k))[1] != newest:
                res["verdicts"]["changed-at-apply"] = res["verdicts"].get("changed-at-apply", 0) + 1
                continue
            done = 0
            for cls, path, blk, size, mtime in p:
                if cls in req.get("gated", GATED):
                    continue
                try:
                    st = os.lstat(path)
                    if st.st_size != size or st.st_mtime != mtime or st.st_nlink != 1:
                        continue
                    mf.write("\t".join((time.strftime("%Y-%m-%d %H:%M:%S"), cls, path, str(size), str(mtime))) + "\n")
                    mf.flush()
                    os.fsync(mf.fileno())
                    if cls in UNLINK:
                        os.unlink(path)
                    else:
                        empty_file(path, mtime)
                    res["freed"] += blk
                    res["files"] += 1
                    done += 1
                except Exception:
                    res["errors"] += 1
            try:
                with open(os.path.join(k, "run", MARKER), "w") as f:
                    json.dump(dict(tool="ot_autoclean", when=time.time(), newest=newest, files=done,
                                   note="run/results files of size 0 were emptied by ot_autoclean, see the host manifest"), f)
            except OSError:
                pass
    return res


# ---------------------------------------------------------------------------------------------- closed units (archive flow)
ARCH_ODB = re.compile(r"^([1-5]_[^/]*|6_1_fill)\.odb$")
CLOSED_QUIET_H = 6


def signed_record(k):
    """the kit's own sign-off record reads SIGNED / LOCAL_PASS / NEEDS_PARENT"""
    p = os.path.join(k, "signoff", "signoff.json")
    try:
        with open(p, errors="replace") as f:
            j = json.load(f)
    except (OSError, ValueError):
        return None
    txt = json.dumps({x: j.get(x) for x in ("verdict", "status", "result")})
    return j if SIGNED_RE.search(txt) else None


def must_keep(k, rec, prot_exact):
    """files of a closed kit a reader needs, whatever their name: the DB its sign-off read, its PROVENANCE routed DB, any
    exact protected path"""
    keep = {p for p in prot_exact if p.startswith(k + "/")}
    inp = (rec or {}).get("inputs") or {}
    if isinstance(inp, dict) and isinstance(inp.get("odb"), str):
        keep.add(norm(inp["odb"]))
        keep.add(os.path.join(k, os.path.relpath(inp["odb"], "/work")) if inp["odb"].startswith("/work/") else norm(inp["odb"]))
    try:
        with open(os.path.join(k, "PROVENANCE.json")) as f:
            v = json.load(f).get("routed_db")
        if isinstance(v, str):
            keep.add(norm(v))
    except (OSError, ValueError, AttributeError):
        pass
    return keep


def closed_plan(k, prot_exact, rec):
    """-> [(path, size)] stage ODBs that leave the host once archived.  Needs a non-empty 6_final.odb or the DB the record read."""
    keep = must_keep(k, rec, prot_exact)
    out = []
    for b, ds, fs in os.walk(os.path.join(k, "run", "results")):
        ds[:] = [x for x in ds if not os.path.islink(os.path.join(b, x))]
        if not any(os.path.exists(os.path.join(b, n)) and os.path.getsize(os.path.join(b, n)) > 0 for n in ("6_final.odb",)):
            if "6_final.odb" not in fs and any(ARCH_ODB.match(f) for f in fs):
                return []                  # no final DB in this base: a route-goal kit, its routed DB is a 5_* file
            continue
        for f in fs:
            p = os.path.join(b, f)
            if not ARCH_ODB.match(f) or p in keep or os.path.realpath(p) in keep:
                continue
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size > 0:
                out.append((p, st.st_blocks * 512))
    return out


def closed_units(req):
    """host side.  -> {units: [...eligible], held: {why: [count, GB of stage ODBs]}}"""
    now = req.get("now") or time.time()
    prot = PathSet(req["protected"])
    res = dict(units=[], held={}, control_hits=0)
    if len(prot.s) < int(req.get("min_rows", MIN_ROWS)):
        res["fail_closed"] = "short protected list"
        return res
    cited = PathSet(req.get("cited") or [])
    tokens = set(req.get("tokens") or [])
    if "live" in req:
        live_paths, blob = set(req["live"]), req.get("blob", "")
    else:
        try:
            live_paths, blob = live_snapshot()
        except Exception as ex:
            res["fail_closed"] = repr(ex)
            return res
    live = PathSet(list(live_paths) + list(req.get("other_host_live") or []), realpath=False)
    def hold(why, gb):
        c = res["held"].setdefault(why, [0, 0.0])
        c[0] += 1
        c[1] += gb
    roots = req.get("roots")
    for k in (find_kits(roots, "", ()) if roots else find_kits(SCAN_ROOTS)):
        rec = signed_record(k)
        if not rec:
            continue
        plan = closed_plan(k, prot.s, rec)
        gb = sum(x[1] for x in plan) / 1e9
        if os.path.exists(os.path.join(k, "ARCHIVED.json")):
            hold("archived", gb)
        elif prot.related(k):
            res["control_hits"] += 1
            hold("protected", gb)
        elif ancestor_mark(k) or os.path.exists(os.path.join(k, ".keep")) or os.path.exists(os.path.join(k, ".ot-run-spill-copy")):
            hold("keep", gb)
        elif cited.near(k) or "/".join(k.split("/")[-2:]) in tokens:
            hold("cited", gb)
        elif live.related(k) or re.search(r"(?<![\w.+-])" + re.escape(os.path.basename(k)) + r"(?![\w.+-])", blob):
            hold("live", gb)
        else:
            newest = protect_scan_mtime(k)
            if now - newest < CLOSED_QUIET_H * 3600:
                hold("quiet", gb)
            elif not plan:
                hold("no-stage-odb", 0)
            else:
                res["units"].append(dict(path=k, gb=round(gb, 3), files=len(plan)))
                hold("eligible", gb)
    return res


def protect_scan_mtime(g):
    newest = 0.0
    for d, ds, fs in os.walk(g):
        ds[:] = [x for x in ds if x != "objects" and not os.path.islink(os.path.join(d, x))]
        for f in fs:
            try:
                newest = max(newest, os.lstat(os.path.join(d, f)).st_mtime)
            except OSError:
                pass
    return newest


def tree_measure(k):
    """-> (files, bytes, {name: sha256}) of regular files; hashes the records the archive check compares"""
    import hashlib
    n, b, sha = 0, 0, {}
    for d, ds, fs in os.walk(k):
        ds[:] = [x for x in ds if not os.path.islink(os.path.join(d, x))]
        for f in fs:
            p = os.path.join(d, f)
            st = os.lstat(p)
            if not stat.S_ISREG(st.st_mode):
                continue
            n += 1
            b += st.st_size
            if f in ("signoff.json", "PROVENANCE.json", "6_final.odb"):
                h = hashlib.sha256()
                with open(p, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 22), b""):
                        h.update(chunk)
                sha[os.path.relpath(p, k)] = h.hexdigest()
    return n, b, sha


def stub_unit(req):
    """host side, after the archive verified: re-check, write the manifest, drop the stage ODBs, write ARCHIVED.json."""
    k = req["path"]
    prot = PathSet(req["protected"])
    if len(prot.s) < int(req.get("min_rows", MIN_ROWS)) or prot.related(k):
        return dict(path=k, error="protected")
    rec = signed_record(k)
    if not rec or ancestor_mark(k) or os.path.exists(os.path.join(k, ".keep")) or os.path.exists(os.path.join(k, "ARCHIVED.json")):
        return dict(path=k, error="state changed")
    live_paths, blob = live_snapshot()
    if PathSet(list(live_paths) + list(req.get("other_host_live") or []), realpath=False).related(k) or \
            re.search(r"(?<![\w.+-])" + re.escape(os.path.basename(k)) + r"(?![\w.+-])", blob):
        return dict(path=k, error="live")
    if tree_measure(k)[:2] != tuple(req["measured"][:2]):
        return dict(path=k, error="kit changed since it was archived")
    plan = closed_plan(k, prot.s, rec)
    man = manifest_path(req)
    gone = []
    with open(man, "a") as mf:
        for p, blk in plan:
            mf.write("\t".join((time.strftime("%Y-%m-%d %H:%M:%S"), "archived", p, str(blk), req["archive"])) + "\n")
            mf.flush()
            os.fsync(mf.fileno())
        for p, blk in plan:
            st = os.lstat(p)
            empty_file(p, st.st_mtime)
            gone.append(os.path.relpath(p, k))
    tmp = os.path.join(k, "ARCHIVED.json.tmp")
    with open(tmp, "w") as f:
        json.dump(dict(schema="opentallas.archived_stub.v1", lane="ot_autoclean", rule="OWNER 2026-11-06 23:1x stage ODBs archived on agidock",
                       archive=req["archive"], date=time.strftime("%Y-%m-%d %H:%M:%S %Z"), files=req["measured"][0], bytes=req["measured"][1],
                       sha256=req["measured"][2], emptied=gone, freed=sum(x[1] for x in plan)), f, indent=1)
    os.replace(tmp, os.path.join(k, "ARCHIVED.json"))
    return dict(path=k, ok=True, files=len(gone), freed=sum(x[1] for x in plan))


# ---------------------------------------------------------------------------------------------- hub side
def read_required(coord):
    rows = []
    for rel in PROTECTED_FILES:
        with open(os.path.join(coord, rel), errors="replace") as f:
            got = parse_rows(f.read())
        if not got:
            raise RuntimeError(f"{rel}: no rows")
        rows += got
    return sorted(set(rows))


def read_cites(coord, now):
    cited, tokens = set(), []
    for rel in CITE_ALL:
        try:
            with open(os.path.join(coord, rel), errors="replace") as f:
                cited.update(os.path.normpath(m.rstrip(".:")) for m in PATH_RE.findall(f.read()))
        except FileNotFoundError:
            pass                                      # optional tables; the protected lists above are the required ones
    try:                                              # Codex names its runs in its log, as lanes do in the queue
        with open(os.path.join(coord, "CODEX-LOG.md"), errors="replace") as f:
            f.seek(max(0, os.fstat(f.fileno()).st_size - (1 << 20)))
            cited.update(os.path.normpath(m.rstrip(".:")) for m in PATH_RE.findall(f.read()))
    except OSError:
        pass
    for rel in ("autopilot/state.json", "autopilot/kit_wave_state.json", QUEUE):
        age = now - os.path.getmtime(os.path.join(coord, rel))
        if age > STALE_H * 3600:
            raise RuntimeError(f"{rel} is {age / 3600:.1f} h old")
    with open(os.path.join(coord, "autopilot/state.json")) as f:
        state = json.load(f)
    with open(os.path.join(coord, "autopilot/kit_wave_state.json")) as f:
        wave = json.load(f)
    cited |= live_rows(state, wave)
    with open(os.path.join(coord, QUEUE), errors="replace") as f:
        abs_, tokens = queue_cites(f.read(), now)
    cited.update(abs_)
    return sorted(cited), tokens


def is_self(host):
    import socket
    return host == "self" or (host == "intel2" and socket.gethostname() == "tolerant-swine")


def ssh(host):
    if is_self(host):
        return ["sh", "-c"]
    return ["ssh", "-n", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", host]


def remote_live(host):
    prog = ("for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null; echo; done | grep -v ot_autoclean; "
            "docker ps -q | xargs -r docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}'")
    r = subprocess.run(ssh(host) + [prog], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(f"{host}: rc {r.returncode}")
    return {os.path.normpath(m.rstrip(".:")) for m in PATH_RE.findall(r.stdout)}


def run_on_host(host, req, fn="sweep"):
    with open(os.path.abspath(__file__)) as f:
        code = f.read()
    tail = '\nif __name__ == "__main__":\n    sys.exit(main())\n'
    assert code.endswith(tail)
    prog = code[:-len(tail)] + f"\nprint(json.dumps({fn}(json.loads({json.dumps(req)!r}))))\n"
    cmd = "cd / && nice -n 19 ionice -c 3 python3 -I -"
    argv = ["sh", "-c", cmd] if is_self(host) else ["ssh", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", host, cmd]
    r = subprocess.run(argv, input=prog, capture_output=True, text=True, timeout=3000)
    if r.returncode:
        return dict(host=host, fail_closed=f"rc {r.returncode}: {r.stderr.strip()[-300:]}")
    return dict(json.loads(r.stdout.strip().splitlines()[-1]), host=host)


def off():
    return os.environ.get("OT_AUTOCLEAN") == "0" or os.path.exists(os.path.expanduser(OFF_FILE))


FLAGS = {"--apply", "--dry", "--json", "--closed", "--no-codex"}   # no --apply = dry run: a mistyped command never deletes
VALUE_FLAGS = {"--host", "--only", "--max-kits"}


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    unknown = [x for i, x in enumerate(a) if x.startswith("-") and x not in FLAGS | VALUE_FLAGS | {"-h", "--help"}]
    if unknown or "-h" in a or "--help" in a:
        print(f"usage: ot_autoclean.py [--apply] {' '.join(sorted(FLAGS - {'--apply'}))} {' '.join(x + ' V' for x in sorted(VALUE_FLAGS))}\n"
              "Without --apply nothing changes on disk (dry run).")
        return 2 if unknown else 0
    if off():
        print("ot_autoclean: OFF")
        return 0
    def opt(name):
        return [a[i + 1] for i, x in enumerate(a) if x == name]
    now = time.time()
    coord = os.path.expanduser(COORD)
    hosts = opt("--host") or list(HOSTS)
    try:
        protected = read_required(coord)
        cited, tokens = read_cites(coord, now)
    except Exception as ex:
        print(f"ot_autoclean: FAIL CLOSED, nothing removed: {ex!r}")
        return 0
    all_live, fail = set(), {}
    for h in list(HOSTS) + ["epyc5", "epyc6"]:
        try:
            if h in hosts or "self" not in hosts:
                all_live |= remote_live(h)
        except Exception as ex:
            if h in hosts:
                fail[h] = repr(ex)
    req = dict(protected=protected, cited=cited, tokens=tokens, other_host_live=sorted(all_live), dry="--apply" not in a,
               held_detail="--apply" not in a, skip_codex="--no-codex" in a, only=(opt("--only") or [""])[0], max_kits=int((opt("--max-kits") or [0])[0]), now=now)
    import concurrent.futures as cf
    todo = [h for h in hosts if h not in fail]
    fn = "closed_units" if "--closed" in a else "sweep"
    with cf.ThreadPoolExecutor(max(1, len(todo))) as ex:
        results = list(ex.map(lambda h: run_on_host(h, req, fn), todo))
    for h, why in fail.items():
        results.append(dict(host=h, fail_closed=why))
    for r in results:
        print(json.dumps(r) if "--json" in a else
              f"{time.strftime('%F %T')} {r['host']} dry={r.get('dry')} kits={r.get('kits')} control={r.get('control_hits')} "
              f"freed={r.get('freed', 0) / 1e9:.1f}GB files={r.get('files')} errors={r.get('errors')} "
              f"plan_GB={ {k: round(v / 1e9, 1) for k, v in (r.get('classes') or {}).items()} } "
              f"verdicts={r.get('verdicts')} fail_closed={r.get('fail_closed')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
