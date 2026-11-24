#!/usr/bin/env python3
"""ot_delete_guard: THE shared pre-delete check of every fleet cleaner (ot-autoclean delete(), wt-reaper, ot_disk_autoprune, ot_cleanup_*).
CLEAN-ALL-1115 postmortem (11-16): an urgent deleter descended into a tree it had kept as a whole and deleted every child that had no
reference of its own, hollowing live die source trees (and removed whole the src tree kit_wave.json names).  This module makes both
impossible.  refuse(target) -> None (may delete) or the reason string.  A target is refused when
  1. it is a symlink or its realpath differs (no aliases: the epyc4 loss),
  2. it IS, CONTAINS or lies INSIDE a protected path: kit_wave.json dies[*].src / item_inputs[*].src / plan dirs, any tree_switch_*.json
     marker tree, a bind of record (kit_rtl bind_out/asbuilt/script + dirs), prov_view_sources dirs,
  3. a live process has its cwd, an open file or its command line under it (or its cwd is a parent of it),
  4. it is a STRICT DESCENDANT of a source tree root (<lane>/kw45/<tree>/x, <lane>/src_*/x): trees are deleted WHOLE or not at all.
The protected list is built on the hub (build_protected) and pushed to every host as protected.txt (header '# built <epoch>'); a missing
or older-than-MAX_AGE_H list fails CLOSED for any tree root.  usage: ot_delete_guard.py build COORD_DIR OUT | check PATH [LIST]"""
import re
import glob, json, os, re, sys, time

DEFAULT_LIST = os.path.expanduser("~/.local/state/ot-delete-guard/protected.txt")
ALLOW_EXACT = os.path.expanduser("~/.local/state/ot-delete-guard/allow_exact.txt")   # COORD-ruled narrow exceptions: "<path>\t<expiry epoch>\t<reason>" per line
CURRENT_TREES = os.path.expanduser("~/.local/state/ot-delete-guard/current_trees.json")   # hub-built: {src_<die prefix>_: {"tree": name, "adopted_at": epoch}}
MAX_AGE_H = float(os.environ.get("OT_GUARD_MAX_AGE_H", "6"))
TREE_ROOT = re.compile(r"^(?P<root>/srv/opentallas-scratch[0-9]*/claude/(?:kw45/snap_[^/]+/[^/]+|kw45/[^/]+|[^/]+/src_[^/]+))(?:/(?P<rest>.+))?$")   # kw45/snap_<die>/<tree>: each snapshot is its own tree (CLEAN-AGGR-1121)
ROUTED_GRACE_H = float(os.environ.get("OT_GUARD_ROUTED_GRACE_H", "2"))
# CLEAN-AGGR-R2 (COORD / FABLE-FLOW-2000 item 5, 11-21): a signed result is kept until EXPORTED.  The hub signed store holds only the sign-off json, so it is
# not an export.  exported_records.txt is written by auto_export drain on the hub (sha256 of each exported sign-off record = AGIdock/rtx INDEX 'record' column,
# plus each INDEX ODB sha) and pushed to every host; hold_ids.txt lists autopilot ids / unit names / paths that must not be retired (COUNT-REVOKED, open re-LEC).
EXPORTED_LIST = os.path.expanduser("~/.local/state/ot-delete-guard/exported_records.txt")
HOLD_LIST = os.path.expanduser("~/.local/state/ot-delete-guard/hold_ids.txt")
EXPORTED_MAX_AGE_H = float(os.environ.get("OT_GUARD_EXPORTED_MAX_AGE_H", "48"))
SIGNED_VERDICT = re.compile(r"^(SIGNED|LOCAL_PASS|NEEDS_PARENT)")
SRV = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/[A-Za-z0-9._+/@=-]+")


def canon(p):
    return re.sub(r"opentallas-scratch[0-9]+", "opentallas-scratch2", p).replace("opentallas-scratch/", "opentallas-scratch2/").rstrip("/")


def _add(s, p):
    if isinstance(p, str) and p.startswith("/srv/"):
        s.add(canon(p))
        s.add(canon(os.path.dirname(p)) if os.path.basename(p) in ("bind_report.json", "asbuilt.json", "asbuilt_sources.json") else canon(p))


# COORD 11-18 (intel1 scratch2 at 5 GB, cleanup refused everything): a path in a die's work_root (a container of every attempt dir) or in free-text / history keys (note_*, *_prev*, evidence, gate,
# hold reasons: provenance prose and revert notes) is NOT a live owner of a tree.  Those keys are skipped, except for dies named in HISTORY_KEEP_DIES (HBM stays parked: its src_prev_* trees are wanted).
HISTORY_KEY = re.compile(r"^(work_root|job|dir_prev.*|note.*|.*_note|.*_notes|evidence|reason|enable_note|plan_note|tools_note|gate|retry_fix|hold_items.*|src_prev.*|queue_src_prev.*|plan_prev.*|gen_host_prev.*|.*_prev_.*|.*_prev|prev_.*)$")
HISTORY_KEEP_DIES = ("hbm",)


def _walk_paths(s, o, skip_history=False):
    if isinstance(o, dict):
        for k, v in o.items():
            if skip_history and HISTORY_KEY.match(str(k)):
                continue
            _walk_paths(s, v, skip_history)
    elif isinstance(o, list):
        for v in o:
            _walk_paths(s, v, skip_history)
    elif isinstance(o, str):
        for m in SRV.finditer(o):
            t = m.group().rstrip("/.-")
            if t.count("/") >= 5:                     # /srv/<scratch>/claude/<lane>/...: never the lane root itself, never a shorter prefix
                s.add(canon(t))


def build_protected(coord, marker_dir=None):
    """coord may be one dir or a list (hub clone + hub-coord copy): the union is protected"""
    if isinstance(coord, (list, tuple)):
        s = set()
        for c in coord:
            try:
                s |= build_protected(c, marker_dir)
            except (OSError, ValueError, KeyError):
                pass
        return s
    s = set(); cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))["dies"]
    for d in cfg.values():
        for it in [d] + [i for i in (d.get("item_inputs") or {}).values() if isinstance(i, dict)]:
            _add(s, it.get("src")); _add(s, os.path.dirname(str(it.get("plan") or "")))
            kr = it.get("kit_rtl") or {}
            for k in ("bind_out", "asbuilt", "script"):
                _add(s, kr.get(k))
        for lst in (d.get("prov_view_sources") or {}).values():
            for c in lst if isinstance(lst, list) else [lst]:
                if isinstance(c, dict):
                    _add(s, c.get("dir")); _add(s, c.get("base"))
    # FLEET-OPS-R (COORD 11-16, E8 wave-src 364 GB): every absolute scratch path in a die block of kit_wave.json is a protected root, whatever its key
    # (src_prev_*, item_inputs, kit_rtl, plan dirs, prov_view_sources ...).  The named keys above are only the common ones; a path under any other key
    # (dies.hbm.src_prev_kw43fsp = .../wave-src/20261110hbm2/hbm) must protect its tree too.
    # superseded_trees is the recognized retirement queue, not a live owner.
    # Drop only a well-formed direct die queue; other/nested keys stay protected.
    # Manual protected paths are never subtracted from an existing list.
    for name, d in cfg.items():
        paths = d
        if isinstance(d, dict):
            queue = d.get("superseded_trees")
            if isinstance(queue, list) and all(isinstance(p, str) and os.path.isabs(p) for p in queue):
                paths = {k: v for k, v in d.items() if k != "superseded_trees"}
        _walk_paths(s, paths, skip_history=(name not in HISTORY_KEEP_DIES))
    for f in glob.glob(os.path.join(marker_dir or os.path.join(coord, "lanes/handoff"), "tree_switch_*.json")):
        try:
            _add(s, json.load(open(f)).get("tree"))
        except (OSError, ValueError):
            pass
    s.discard("")
    return s


def write_list(s, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True); tmp = out + ".tmp"
    with open(tmp, "w") as fh:
        fh.write("# built %d\n" % time.time()); fh.write("\n".join(sorted(s)) + "\n")
    os.replace(tmp, out)


def load_list(path=None, now=None):
    path = path or os.environ.get("OT_GUARD_LIST") or DEFAULT_LIST
    try:
        lines = open(path).read().splitlines()
        built = float(lines[0].split()[2]) if lines and lines[0].startswith("# built") else os.path.getmtime(path)
    except (OSError, ValueError, IndexError):
        return None, "protected list missing/unreadable"
    if (now or time.time()) - built > MAX_AGE_H * 3600:
        return None, "protected list older than %gh" % MAX_AGE_H
    me = self_alias()
    out = set()
    for l in lines:
        if l.startswith("/srv/"):
            out.add(canon(l))
        elif l.startswith("@") and " /srv/" in l:   # CLEAN-AGGR-R3: host-scoped (hub ot-run --hosts): applies on those hosts; unknown host = applies
            hs, p = l[1:].split(" ", 1)
            if me is None or me in hs.split(","):
                out.add(canon(p.strip()))
    return out, None


HOST_ALIAS = {"key-cardinal": "intel1", "tolerant-swine": "intel2", "dear-crayfish": "epyc2", "loved-redfish": "epyc7",
              "outgoing-giraffe": "epyc8", "renewed-glider": "epyc9", "civil-redfish": "epyc10", "viable-ram": "epyc11"}


def self_alias():
    """fleet alias of this host (ot-run --hosts names), or None when unknown (then every host-scoped line applies: fail closed)"""
    import socket
    h = os.environ.get("OT_HOST_ALIAS") or socket.gethostname()
    return HOST_ALIAS.get(h, h if h in HOST_ALIAS.values() else None)


_CACHE = {"t": 0, "v": ""}


def live_text(skip=(), ttl=20):
    if time.time() - _CACHE["t"] < ttl and not skip:
        return _CACHE["v"]
    v = _live_text(skip); _CACHE.update(t=time.time(), v=v)
    return v


def ancestor_pids(pid=None, proc="/proc"):
    """CLEAN-AGGR-R3 11-21: the caller's own process chain (pid -> init).  `timeout N ot-delete <path>` or an ssh `bash -c '... <path>'`
    named the target in an ANCESTOR cmdline, so the live check refused every delete run that way (s81-die-r3-e8 on epyc2/intel1)."""
    out, pid = set(), os.getpid() if pid is None else pid
    while pid > 1 and pid not in out:
        out.add(pid)
        try:
            pid = int(open(f"{proc}/{pid}/stat").read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return out


def _live_text(skip=()):
    t, me = [], {os.getpid(), os.getppid(), *skip}
    anc = ancestor_pids()
    for p in glob.glob("/proc/[0-9]*"):
        if int(p[6:]) in me:
            continue
        try:
            if int(p[6:]) not in anc:      # an ancestor's cmdline is the delete request itself; its cwd / open files still count
                t.append(open(p + "/cmdline", "rb").read().decode("latin1"))
            t.append(os.readlink(p + "/cwd"))
        except OSError:
            continue
        try:
            for f in os.listdir(p + "/fd"):
                try:
                    t.append(os.readlink(p + "/fd/" + f))
                except OSError:
                    pass
        except OSError:
            pass
    return "\n".join(t).replace("opentallas-scratch3", "opentallas-scratch2")


def load_allow_exact(path=None, now=None):
    """{canon path} of the unexpired exact exceptions.  An exception lets ONE directory be deleted although a protected ancestor (a rows dir) contains it; it never lifts the protection of
    the directory itself, of anything protected INSIDE it, the live-process check or the newer-than-current rule."""
    now = time.time() if now is None else now
    out = set()
    try:
        for ln in open(path or ALLOW_EXACT):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 2 and f[0].startswith("/srv/") and float(f[1]) > now:
                out.add(canon(f[0]))
    except (OSError, ValueError):
        pass
    return out


def newer_than_current(target, current=None):
    """COORD 11-17 (QC M5T was retired while its apply was pending): a source tree whose manifest is NEWER than the moment its die adopted the current tree is an adoption in progress,
    never a superseded tree.  current = {prefix: {"tree": name, "adopted_at": epoch}} (default: the hub-built current_trees.json).  -> reason or ''"""
    if current is None:
        try:
            current = json.load(open(CURRENT_TREES))
        except (OSError, ValueError):
            return ""
    name = os.path.basename(os.path.abspath(target).rstrip("/"))
    # COORD RULING 11-22 03:05 (hub 6d564bb7): a lane's own superseded private work tree (name contains "_work") named EXACTLY in
    # OT_DELETE_SUPERSEDED_PRIVATE (colon list of tree roots) is retired by ruling, not an adoption in progress.  Every other check still applies.
    ok = [q.rstrip("/") for q in os.environ.get("OT_DELETE_SUPERSEDED_PRIVATE", "").split(":") if q]
    if "_work" in name and os.path.abspath(target).rstrip("/") in ok:
        return ""
    for prefix, row in (current or {}).items():
        if name.startswith(prefix) and name != row.get("tree") and not name.endswith((".part", ".building")):
            for f in (os.path.join(target, ".src-manifest.json"), target):
                try:
                    mt = os.stat(f).st_mtime
                    break
                except OSError:
                    continue
            else:
                return ""
            if mt > float(row.get("adopted_at") or 0) + 60:
                return "newer than the die's current tree %s (published after its adoption: apply pending / in progress)" % row.get("tree")
    return ""


ATTEMPT_DIR = re.compile(r"^(?P<item>.*/items/[^/]+)/attempt_(?P<n>\d+)(?:/|$)")
ROUTED_FILES = ("5_2_route.odb", "6_final.odb")


def _routed(attempt_dir):
    return any(glob.glob(os.path.join(attempt_dir, "**", "run", "results", "asap7", "*", "base", f), recursive=True) for f in ROUTED_FILES)


def routed_unsigned_refusal(t):
    """FABLE-FLOW-1555 (B): slice_station__t47 (14:06) and hd_ctl (14:58) lost their routed results to grt_arm_reclaim / auto_retire.attempt_candidates.  The one choke point refuses any target at or inside a
    kit-wave attempt dir that holds 5_2_route.odb or 6_final.odb, unless that attempt is SIGNED (a signoff.json with verdict SIGNED under it) or a NEWER attempt of the same item also holds routed results.
    -> reason or None"""
    m = ATTEMPT_DIR.match(t)
    if not m:
        return None
    ad = t[:m.end()].rstrip("/")
    if not os.path.isdir(ad) or not _routed(ad):
        return None
    # CLEAN-AGGR-1121 (OWNER 11-12: unsigned / failed results are deleted directly, 2 h grace after the job ends): a routed unsigned result older than the grace is
    # protected only by what protects any attempt -- a live / queued row listing it (build_protected_live.live_attempt_paths), PROTECTED-DBS, a live process.
    newest = max((os.path.getmtime(f) for x in ROUTED_FILES for f in glob.glob(os.path.join(ad, "**", "run", "results", "asap7", "*", "base", x), recursive=True)), default=0)
    if time.time() - newest > ROUTED_GRACE_H * 3600:
        return None
    for so in glob.glob(os.path.join(ad, "**", "signoff*.json"), recursive=True):
        try:
            if SIGNED_VERDICT.match(str(json.load(open(so)).get("verdict") or "")):
                return None
        except (OSError, ValueError, AttributeError):
            continue
    n = int(m.group("n"))
    for other in glob.glob(m.group("item") + "/attempt_*"):
        k = re.search(r"attempt_(\d+)$", other)
        if k and int(k.group(1)) > n and _routed(other):
            return None
    return "routed result not signed and not superseded by a newer routed attempt (5_2_route.odb / 6_final.odb): " + os.path.basename(ad)


def attempt_dir_of(t):
    """the kit-wave attempt dir (.../items/<item>/attempt_N) t is or lies inside, else None"""
    m = ATTEMPT_DIR.match(t)
    return t[:m.end()].rstrip("/") if m else None


# CLEAN-AGGR-R3 (COORD 11-21: QC-RELAUNCH-R1 failed private slw_su_c kits refused because the die work_root kit-wave is protected whole):
# a private-spec kit dir .../kit-wave/<die>/<plan>/private/<LANE>/<kit> is a unit like attempt_N: an ANCESTOR entry does not protect it.
PRIVATE_KIT_DIR = re.compile(r"^.*/kit-wave/[^/]+/[^/]+/private/[^/]+/[^/]+(?=/|$)")


def unit_dir_of(t):
    """the attempt_N dir or private-spec kit dir t is or lies inside, else None"""
    ad = attempt_dir_of(t)
    if ad:
        return ad
    m = PRIVATE_KIT_DIR.match(t)
    return m.group(0).rstrip("/") if m else None


# CLEAN-AGGR-R3 (COORD 11-21): a kit carries COPIES of its child views' sign-offs as inputs (gen/<item>/ft_physical/<child>/signoff.json, the view
# cache, rtl/, plandir/); a copied record is not this unit's result and must not make a failed kit "signed".
COPIED_INPUT_DIRS = {"ft_physical", ".cache", "rtl", "plandir"}


def attempt_signed(ad):
    """a signoff*.json with verdict SIGNED / LOCAL_PASS* / NEEDS_PARENT under the attempt dir (LOCAL_PASS counts as signed, CLEAN-AGGR-R2),
    not counting copies inside the unit's input dirs (COPIED_INPUT_DIRS)"""
    for so in glob.glob(os.path.join(ad, "**", "signoff*.json"), recursive=True):
        if COPIED_INPUT_DIRS & set(os.path.relpath(so, ad).split(os.sep)[:-1]):
            continue
        try:
            if SIGNED_VERDICT.match(str(json.load(open(so)).get("verdict") or "")):
                return True
        except (OSError, ValueError, AttributeError):
            continue
    return False


def load_exported(path=None, now=None):
    """-> set of exported sha256 (records and ODBs), or None when the list is missing, unreadable or older than EXPORTED_MAX_AGE_H (callers fail closed)"""
    now = time.time() if now is None else now
    try:
        with open(path or EXPORTED_LIST) as f:
            head = f.readline()
            m = re.match(r"# built (\d+)", head)
            if not m or now - int(m.group(1)) > EXPORTED_MAX_AGE_H * 3600:
                return None
            return {ln.split("\t")[0].strip() for ln in f if re.match(r"[0-9a-f]{64}", ln)}
    except OSError:
        return None


def load_hold(path=None):
    """-> set of hold tokens (autopilot ids, unit dir names, /srv paths); missing file = empty"""
    try:
        return {ln.split("\t")[0].strip() for ln in open(path or HOLD_LIST) if ln.strip() and not ln.startswith("#")}
    except OSError:
        return set()


def signed_records(t):
    """-> [(sha256 of the sign-off bytes, relpath)] of every SIGNED / LOCAL_PASS* / NEEDS_PARENT signoff json at or under t (symlinks not followed)"""
    import hashlib
    out = []
    for d, ds, fs in os.walk(t):
        ds[:] = [x for x in ds if not os.path.islink(os.path.join(d, x))]
        for f in fs:
            if f != "signoff.json" and not f.endswith(".signoff.json"):
                continue
            p = os.path.join(d, f)
            try:
                if os.path.islink(p) or os.path.getsize(p) > 8e6:
                    continue
                raw = open(p, "rb").read()
                if SIGNED_VERDICT.match(str(json.loads(raw).get("verdict") or "")):
                    out.append((hashlib.sha256(raw).hexdigest(), os.path.relpath(p, t)))
            except (OSError, ValueError, AttributeError):
                continue
    return out


CLOSED_PART = re.compile(r"/autopilot/closed(/|$)")


def closed_unit_refusal(t, exported=None, hold=None):
    """CLEAN-AGGR-R2: a target at, inside or above an autopilot/closed unit is refused while (1) it holds a signed / LOCAL_PASS record that is not
    exported (record sha not in exported_records.txt; a missing or stale list exports nothing), or (2) the unit is on hold (COUNT-REVOKED, open re-LEC).
    -> reason or None.  Only autopilot/closed targets are walked (the unit dirs are small apart from their DBs)."""
    if not CLOSED_PART.search(t) and not os.path.isdir(os.path.join(t, "autopilot", "closed")) and not t.endswith("/autopilot"):
        return None
    if not os.path.isdir(t):
        return None
    hold = load_hold() if hold is None else hold
    if hold:
        for d, ds, fs in os.walk(t):
            ds[:] = [x for x in ds if not os.path.islink(os.path.join(d, x)) and x not in ("run", "results", "base", "objects")]
            if os.path.basename(d) in hold or d in hold or canon(d) in hold:
                return "unit on hold (hold_ids.txt: COUNT-REVOKED / open re-LEC): " + os.path.basename(d)
            if "AUTOPILOT.json" in fs:
                try:
                    if str(json.load(open(os.path.join(d, "AUTOPILOT.json"))).get("id")) in hold:
                        return "unit on hold (hold_ids.txt autopilot id): " + os.path.basename(d)
                except (OSError, ValueError, AttributeError):
                    pass
    recs = signed_records(t)
    if not recs:
        return None
    exported = load_exported() if exported is None else exported
    if exported is None:
        return "signed record(s) present and exported_records.txt missing or stale (signed results are kept until exported): " + recs[0][1]
    miss = [r for s_, r in recs if s_ not in exported]
    if miss:
        return "signed record not exported (%d of %d, e.g. %s)" % (len(miss), len(recs), miss[0])
    return None


def own_signed_records(t, host=None):
    """Signed result records under t, including a returned result whose exact final ODB is local.

    Imported child views and repo content remain outside the result inventory.
    """
    import hashlib, socket
    host = host or socket.gethostname()
    root = os.path.realpath(t)
    out = []
    for d, ds, fs in os.walk(t):
        ds[:] = [x for x in ds if not os.path.islink(os.path.join(d, x)) and x not in COPIED_INPUT_DIRS
                 and not (x in ("die_plan", "ref_tile") and os.path.basename(d) == "physical" and os.path.isdir(os.path.join(d, "die_plan")))]
        # physical/die_plan + physical/ref_tile of a source tree (has physical/die_plan) = git-tracked plan / signed view content (in main), not a result
        # (CLEAN-AGGR-R3 11-22: 13 main ref_tile views refused every tree copy on intel2 at 96 %)
        for f in fs:
            if f != "signoff.json" and not f.endswith(".signoff.json"):
                continue
            q = os.path.join(d, f)
            try:
                if os.path.islink(q) or os.path.getsize(q) > 8e6:
                    continue
                raw = open(q, "rb").read()
                rec = json.loads(raw)
                if not SIGNED_VERDICT.match(str(rec.get("verdict") or "")):
                    continue
                if rec.get("host") and str(rec.get("host")) != host:
                    # A sealed return keeps the producer hostname but can leave the last final DB here.
                    inputs = rec.get("inputs")
                    odb = inputs.get("odb") if isinstance(inputs, dict) else None
                    if (not isinstance(odb, str) or not os.path.isabs(odb)
                            or os.path.basename(odb) != "6_final.odb"
                            or os.path.commonpath((root, os.path.realpath(odb))) != root
                            or os.path.islink(odb) or not os.path.isfile(odb)):
                        continue
                out.append((hashlib.sha256(raw).hexdigest(), os.path.relpath(q, t)))
            except (OSError, ValueError, AttributeError):
                continue
    return out


def signed_unexported_refusal(t, exported=None, host=None):
    """CLEAN-AGGR-R3 (COORD 11-22 class bug: sle_st_b_v2__cl14c98df5__pv41c959f3 attempt_2 went to ot-auto-retire 11-21 17:01 and its closed unit to ot-delete at
    19:24 while its SIGNED record 8f88a85b... was never exported): ANY target -- attempt, lane dir, kit, tree -- holding this host's signed record whose sha256 is
    not in exported_records.txt (the auto_export ledger / rtx-pro INDEX record column) is refused; a missing or stale list exports nothing (fail closed)."""
    if not os.path.isdir(t) or os.path.islink(t):
        return None
    recs = own_signed_records(t, host)
    if not recs:
        return None
    exported = load_exported() if exported is None else exported
    if exported is None:
        return "signed record(s) present and exported_records.txt missing or stale (signed results are kept until exported): " + recs[0][1]
    miss = [r for s_, r in recs if s_ not in exported]
    if miss:
        return "signed record not exported (%d of %d, e.g. %s)" % (len(miss), len(recs), miss[0])
    return None


def keep_refusal(target):
    """ROMW-LOSS-1124 (COORD 11-24): a .keep file at or above the target keeps it.  Until now only ot-autoclean honoured .keep, so ot-delete of
    romw-1119/ckpt, head, logs, venv, wt ... (lane dir held a .keep) removed 323 GB of checkpoints on 11-23.  No list, allow_exact entry or flag
    bypasses this; only removing the .keep file does."""
    t = os.path.abspath(target)
    d = t
    while True:
        k = os.path.join(d, ".keep")
        try:
            os.lstat(k)
            return ".keep file keeps it (%s; remove the .keep file to delete)" % k
        except OSError:
            pass
        nd = os.path.dirname(d)
        if nd == d:
            return None
        d = nd


# JOBROOT-KEEP-1124 (COORD: CLEAN-DISK ot-delete removed epyc9 ot-jobs/.return and ot-jobs/.ot-isolated.json): the ot-run job root's own
# entries are infrastructure, never cleanup targets.  .ot-isolated.json marks the root as ot-run-owned (ot-lifecycle / autoclean skip it);
# .return holds HUB-FETCH return stages that a pending copy-back still reads.  Both are re-made on demand, but deleting them races live jobs.
# Per-job dirs and single .return/<pid>-<t> stages keep their ordinary rules.
JOBROOT_KEEP = (".ot-isolated.json", ".return")


def jobroot_refusal(t):
    parent, base = os.path.split(t.rstrip("/"))
    if base in JOBROOT_KEEP and os.path.basename(parent) == "ot-jobs":
        return f"ot-run job root entry {base} (never deleted: JOBROOT-KEEP-1124)"
    return ""


def refuse(target, protected=None, ptext=None, why_list=None, current=None, allow=None):
    """None = allowed.  protected/ptext may be passed in (tests, batch callers); otherwise loaded."""
    t = canon(os.path.abspath(target))
    jr = jobroot_refusal(os.path.abspath(target))
    if jr:
        return jr
    if os.path.islink(target) or os.path.realpath(target) != os.path.abspath(target):
        if canon(os.path.realpath(target)) != t:
            return "symlink or realpath differs"
    kr = keep_refusal(target)
    if kr:
        return kr
    rr = routed_unsigned_refusal(t)
    if rr:
        return rr
    cr = closed_unit_refusal(os.path.abspath(target))
    if cr:
        return cr
    m = TREE_ROOT.match(t)
    if m and m.group("rest"):
        return "partial delete inside source tree %s (whole trees only)" % os.path.basename(m.group("root"))
    if m and not m.group("rest"):
        nt = newer_than_current(t if os.path.isdir(t) else target, current)
        if nt:
            return nt
    if protected is None:
        protected, err = load_list()
        if protected is None:
            return err if m else None            # fail closed for tree roots; other targets keep the other guards
    allow = load_allow_exact() if allow is None else allow
    # FLOW-OPS-1300 item 13 (FLEET-WATCH-R7: ~97 % of 4,400 idle failed / superseded attempt dirs per host refused): a die's work_root (the rows container
    # .../runs/<die>/kit-wave) is protected as a whole, so every old attempt_N inside it was refused.  Owner rule 11-12 (keep only live jobs, live / queued refs, signed until
    # archived): an attempt_N dir is NOT protected by an ANCESTOR entry.  It stays refused when it is listed itself (the latest attempts of live / queued rows,
    # build_protected_live.live_attempt_paths), holds something listed (PROTECTED-DBS, binds of record), holds a signed result, holds an unsigned routed result
    # (routed_unsigned_refusal above), or a live process / ot-run command line names it (below).
    ad = unit_dir_of(t)
    ad_free = bool(ad) and not attempt_signed(ad)
    for p in protected:
        if t.startswith(p + "/") and t in allow:
            continue                                  # exact exception: only a protected ANCESTOR is skipped
        if ad_free and ad.startswith(p + "/"):
            continue                                  # an ancestor of the attempt dir (the rows container): not a protection of the attempt
        if p == t or p.startswith(t + "/") or t.startswith(p + "/"):
            if p.endswith("/."):                      # OPS-SUPPORT-R1: "<lane dir>/." = a lane dir a handoff / post of the last 24 h names (build_protected_live.lane_root_paths)
                return "live lane dir (named by a handoff or lane post updated in the last 24 h; delete its idle trees, not the lane dir): " + p[:-2]
            return "protected (kit_wave.json src/bind of record/marker/prov): " + p
    su = signed_unexported_refusal(os.path.abspath(target))      # after the list: a protected tree keeps its own reason
    if su:
        return su
    lr = lease_refusal(t)
    if lr:
        return lr
    pt = live_text() if ptext is None else ptext
    if names_path(pt, t):
        return "live process cwd/open file/cmdline under it"
    if ad and ad != t and names_path(pt, ad):
        return "live process cwd/open file/cmdline under its attempt dir"
    return None


def names_path(text, p):
    """CLEAN-AGGR-R3 (FABLE-FLOW-2200: a live specA7 run-item kept specA): p occurs in text as a whole path -- followed by '/', the end, or a
    character that cannot continue a path component -- not as the prefix of a longer name"""
    if p not in text:
        return False
    return re.search(re.escape(p) + r"(?=$|[/\s'\";:,)=|&<>\]}*?`])", text) is not None


def lease_refusal(t):
    """CLEAN-AGGR-R3 leases (tools/fleet/ot_lease.py): a live lease on t, inside t or containing t keeps it"""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import ot_lease
    except ImportError:
        return None
    r = ot_lease.covering(t, ot_lease.leases())
    if r:
        return "leased by %s until %s: %s" % (r.get("owner"), time.strftime("%F %T", time.localtime(float(r.get("expires") or 0))), r.get("path"))
    return None


if __name__ == "__main__":
    if sys.argv[1] == "build":
        s = build_protected(sys.argv[2].split(",")); write_list(s, sys.argv[3]); print(len(s), "protected paths ->", sys.argv[3])
    else:
        r = refuse(sys.argv[2], *(([load_list(sys.argv[3])[0]] if len(sys.argv) > 3 else [])))
        print("REFUSE: " + r if r else "ok"); sys.exit(1 if r else 0)
