#!/usr/bin/env python3
"""auto_retire: DISK-RATE -> retirement (FLEET-OPS-R, FABLE-FLOW-2200).  Scope: SUPERSEDED die source trees (kw45/src_*) only.
  select(...)  per die keep: the current tree (dies.<die>.src), every live tree reference in kit_wave.json / kit_wave_state.json / tree_switch markers (superseded_trees is a retirement queue, not a live reference)
               (reference proof), every tree NEWER than the current one (a pending adoption such as nf15d) and ONE rollback = the newest older tree.
               Everything else of that die is a candidate, oldest first.  A tree that names no die (legacy src_*_main_*) is a candidate only when
               it is referenced nowhere.
  run(...)     for each candidate: reference proof again, ot_delete_guard.refuse (protected list + live process), SIGNED units in the signed store
               (retire3 rule), whole-tree delete; df before / after per tree in the log; stops at --target GB free.  Dry unless --apply.
usage: auto_retire.py --kit-wave kw.json --state kw_state.json --markers m.json --store-ids ids.txt --guard-module G --list L --log LOG.jsonl
                      [--root kw45] [--target 350] [--apply]"""
import argparse, glob, hashlib, importlib.util, json, os, re, shutil, sys, time

DIE_PREFIX = (("src_kv_", "qwen_kvsys"), ("src_qc_", "qwen_compute"), ("src_head_", "s81_head"), ("src_s81_", "s81"), ("src_hbm_", "hbm"))


def die_of(name):
    for p, d in DIE_PREFIX:
        if name.startswith(p):
            return d
    return None


def ref_count(name, texts):
    rx = re.compile(re.escape(name) + r"(?![A-Za-z0-9_])")
    return sum(len(rx.findall(t)) for t in texts)


# kit_wave_state.json keeps every attempt ever made (11-17: 4252 rows, 3999 CANCELLED / FAIL).  A finished attempt names the src tree it ran
# from, but nothing will start from that tree again; only a row that can still launch or resume needs it (COORD FABLE-FLOW-0300 11-17: this made every
# superseded tree "referenced", so AUTO-RETIRE deleted 0 on 4 alerts).  A state text that is not the known {"items": {...}} shape is kept whole.
LIVE_STATUS = frozenset({"ENQUEUED", "RUNNING", "ROUTE-HELD", "DEDUP", "DEDUP-WAIT", "RETRY-INFRA", "RETRY", "LAUNCHED", "QUEUED", "STARTING"})


def live_state_text(text):
    try:
        d = json.loads(text)
        items = d["items"]
        if not isinstance(items, dict):
            return text
    except (TypeError, ValueError, KeyError):
        return text
    return json.dumps({k: v for k, v in items.items() if not isinstance(v, dict) or str(v.get("status") or "") in LIVE_STATUS or not v.get("status")})


def live_reference_texts(cfg, texts):
    out = list(_cfg_live_texts(cfg, texts))
    if len(out) > 1 and out[1]:
        out[1] = live_state_text(out[1])
    return out


def _cfg_live_texts(cfg, texts):
    """Only recognized queue metadata in the matching cfg text is not a live ref.

    State, markers, malformed/nonmatching config text and every other config key
    remain unchanged. Never filter an already-built protected path list.
    """
    if not texts:
        return texts
    try:
        if json.loads(texts[0]) != cfg:
            return texts
    except (TypeError, ValueError):
        return texts
    dies = cfg.get("dies")
    if not isinstance(dies, dict):
        return texts
    clean = dict(cfg, dies=dict(dies))
    for name, die in dies.items():
        if not isinstance(die, dict):
            continue
        queue = die.get("superseded_trees")
        if isinstance(queue, list) and all(isinstance(p, str) and os.path.isabs(p) for p in queue):
            clean["dies"][name] = {k: v for k, v in die.items() if k != "superseded_trees"}
    return [json.dumps(clean), *texts[1:]]


def rollback_snapshot(die, row, current, trees, mtimes, root=None):
    """An existing local, same-die, older source entry can be the one rollback."""
    path = row.get("rollback_tree")
    if not isinstance(path, str) or not os.path.isabs(path):
        return None
    name = os.path.basename(path.rstrip("/"))
    if name not in trees or die_of(name) != die or name == current:
        return None
    if name not in mtimes or current not in mtimes or mtimes[name] >= mtimes[current]:
        return None
    if os.path.islink(path) or not os.path.isdir(path):
        return None
    if root is not None:
        try:
            if not os.path.samefile(path, os.path.join(root, name)):
                return None
        except OSError:
            return None
    return name


def select(trees, cfg, texts, mtimes, root=None):
    """trees = [name]; cfg = parsed kit_wave.json; texts = [kit_wave.json, state, markers text]; mtimes = {name: mtime}.  -> [name] candidates, oldest first"""
    texts = live_reference_texts(cfg, texts)
    dies = cfg.get("dies") or {}
    cur = {d: os.path.basename(str((v or {}).get("src") or "").rstrip("/")) for d, v in dies.items()}
    rollbacks = {}
    for die, row in dies.items():
        name = rollback_snapshot(die, row or {}, cur.get(die), trees, mtimes, root)
        if name is not None:
            rollbacks[die] = name
    out = []
    for name in sorted(trees, key=lambda n: mtimes.get(n, 0)):
        if name in rollbacks.values() or ref_count(name, texts):
            continue                                                  # referenced anywhere = kept, whole tree
        d = die_of(name)
        if d and cur.get(d):
            cm = mtimes.get(cur[d], 0)
            if mtimes.get(name, 0) >= cm:
                continue                                              # newer than (or) current: pending adoption
        out.append(name)
    # An explicit qualified rollback is already kept. Use the old conservative
    # fallback only when that designated snapshot is absent or invalid.
    keep = set()
    for d in {die_of(n) for n in out} - {None}:
        if d in rollbacks:
            continue
        olds = [n for n in out if die_of(n) == d]
        if olds:
            keep.add(max(olds, key=lambda n: mtimes.get(n, 0)))
    return [n for n in out if n not in keep]


def signed_not_in_store(tree, ids):
    miss = n = 0
    for r, ds, fs in os.walk(tree):
        for f in fs:
            if f != "signoff.json" and not f.endswith(".signoff.json"):
                continue
            p = os.path.join(r, f)
            try:
                if os.path.getsize(p) > 8e6:
                    continue
                t = open(p, errors="replace").read()
                if json.loads(t).get("verdict") != "SIGNED":
                    continue
            except (OSError, ValueError, AttributeError):
                continue
            n += 1
            if hashlib.sha256(t.encode(errors="replace")).hexdigest() not in ids:
                miss += 1
    return n, miss


def git_unsafe(path, timeout=15):
    """clean3 lesson (CLEAN-3 11-13 deleted .git of idle clones with unpushed work + bare repos): a tree that holds a git work tree with uncommitted changes or commits on no remote, or a
    bare repo, is never an idle-lane candidate.  -> reason or ''.  Looks for .git / bare repos to depth 3."""
    import subprocess
    cands = []
    for r, ds, fs in os.walk(path):
        if r[len(path):].count(os.sep) >= 3:
            ds[:] = []
        if ".git" in ds or ".git" in fs:
            cands.append(r); ds[:] = [d for d in ds if d != ".git"]
        elif {"HEAD", "objects", "refs"} <= set(fs + ds):
            return "bare git repo at " + r
    for r in cands:
        try:
            dirty = subprocess.run(["git", "-C", r, "status", "--porcelain", "-uno", "--ignore-submodules"], capture_output=True, text=True, timeout=timeout).stdout.strip()
            ahead = subprocess.run(["git", "-C", r, "log", "--branches", "--not", "--remotes", "--oneline", "-n", "1"], capture_output=True, text=True, timeout=timeout).stdout.strip()
        except Exception as e:
            return "git state unreadable at %s (%s)" % (r, type(e).__name__)
        if dirty:
            return "git work tree with uncommitted changes at " + r
        if ahead:
            return "git commit on no remote at " + r
    return ""


def home_link_targets(home=None, depth=2):
    """COORD 11-18: realpaths that a symlink under ~ (depth <= 2, not entering skyhum-work / .claude / .codex) points to; a lane dir that is, contains or lies inside one of them is never retired"""
    home = home or os.path.expanduser("~")
    out = set()
    for r, ds, fs in os.walk(home):
        rel = r[len(home):].count(os.sep)
        ds[:] = [d for d in ds if d not in ("skyhum-work", ".claude", ".codex", ".git") and rel < depth and not os.path.islink(os.path.join(r, d))]
        for n in fs + [d for d in os.listdir(r) if os.path.islink(os.path.join(r, d))]:
            q = os.path.join(r, n)
            if os.path.islink(q):
                try:
                    out.add(os.path.realpath(q)); out.add(os.path.normpath(os.path.join(os.path.dirname(q), os.readlink(q))))
                except OSError:
                    pass
    return out


def link_hit(path, targets):
    p = path.rstrip("/")
    for t in targets:
        if t == p or t.startswith(p + "/") or p.startswith(t + "/"):
            return t
    return ""


def post_text_hit(path, posts):
    """a lane tree named in a hub post of the last 24 h (the posts file is built by the hub driver) is in use by somebody"""
    return bool(posts) and re.search(re.escape(path.rstrip("/")) + r"(?![A-Za-z0-9_.-])", posts) is not None


def free_gb(path):
    s = os.statvfs(path)
    return s.f_bavail * s.f_frsize / 1e9


def run(root, cfg, texts, ids, refuse, log, target_gb, apply=False, delete=None, free=None):
    texts = live_reference_texts(cfg, texts)
    free = free or (lambda: free_gb(root))
    if not os.path.isdir(root):                           # a host with no kw45 (the hub): nothing to retire, not an error
        return []
    names = [n for n in os.listdir(root) if n.startswith("src_") and os.path.isdir(os.path.join(root, n)) and not os.path.islink(os.path.join(root, n))]
    cand = select(names, cfg, texts, {n: os.lstat(os.path.join(root, n)).st_mtime for n in names}, root=root)
    res = []
    for n in cand:
        if free() >= target_gb:
            res.append(dict(stop="target", free=round(free(), 1))); break
        t = os.path.join(root, n)
        rec = dict(tree=t, t=time.strftime("%F %T"), die=die_of(n))
        why = refuse(t)
        if not why and ref_count(n, texts):
            why = "referenced"
        if not why:
            sn, miss = signed_not_in_store(t, ids)
            rec.update(signed_units=sn, signed_not_in_store=miss)
            if miss:
                why = "%d SIGNED unit(s) not in the signed store" % miss
        if why:
            rec["result"] = "REFUSED: " + str(why)[:120]
        elif not apply:
            rec["result"] = "WOULD-DELETE"
        else:
            b = free()
            (delete or (lambda p: (os.system("find " + p + " -type d -exec chmod u+w {} +"), shutil.rmtree(p, ignore_errors=True))))(t)
            rec.update(result="DELETED" if not os.path.exists(t) else "FAILED", free_before=round(b, 1), free_after=round(free(), 1))
        log(rec); res.append(rec)
    return res


LANE_SKIP = frozenset({"kw45", "rt", "hub-coord", "mq1", "mq-gate", "git", "clean-all-1115", "tools-converge", "fleet-ops-r", "signed-store", "autopilot", "moved"})   # moved: ~/.cache and ~/OpenTallas link into it (COORD 11-18)


def newest_mtime(path, stop_after=None):
    """newest file mtime under path (0 = empty); stops at the first file newer than stop_after (idle test needs only that)"""
    best = 0.0
    for r, ds, fs in os.walk(path):
        for f in fs + ds:
            try:
                t = os.lstat(os.path.join(r, f)).st_mtime
            except OSError:
                continue
            best = max(best, t)
            if stop_after is not None and best > stop_after:
                return best
    try:
        return max(best, os.lstat(path).st_mtime)
    except OSError:
        return best


def lane_candidates(claude, now=None, idle_h=24.0, skip=LANE_SKIP, mtime=newest_mtime, depth=2):
    """FABLE-FLOW-0700 (1): idle lane dirs.  -> [(path, idle seconds)] oldest first.  Level 1 = claude/<lane>, plus (when the lane is claude/wt, or a lane the guard
    refuses as a whole) level 2 = claude/<lane>/<child>.  Idle = nothing under it modified in idle_h hours (24 h rule)."""
    now = now or time.time(); cut = now - idle_h * 3600; out = []
    for n in sorted(os.listdir(claude)):
        p = os.path.join(claude, n)
        if n in LANE_SKIP or n in skip or not os.path.isdir(p) or os.path.islink(p) or n.startswith("."):
            continue
        out.append(p)
        if depth >= 2:
            try:
                out += [os.path.join(p, c) for c in sorted(os.listdir(p)) if os.path.isdir(os.path.join(p, c)) and not os.path.islink(os.path.join(p, c))]
            except OSError:
                pass
    res = []
    for p in out:
        m = mtime(p, cut)
        if m <= cut:
            res.append((p, now - m))
    res.sort(key=lambda x: -x[1])
    return res


def run_lanes(claude, ids, refuse, log, target_gb, apply=False, delete=None, free=None, now=None, idle_h=24.0, mtime=newest_mtime, posts="", git_check=git_unsafe, links=None, deadline=None):
    """retire idle lane dirs (and claude/wt children) through the guard, ingest-first, oldest first, stop at target_gb free.  A parent already removed or
    refused as a whole is retried through its children (level 2 is in the candidate list)."""
    free = free or (lambda: free_gb(claude)); res = []; gone = []
    links = home_link_targets() if links is None else links
    for p, idle in lane_candidates(claude, now, idle_h, mtime=mtime):
        if deadline and time.time() > deadline:            # 11-18: a pass must END (epyc2 sat 15+ min in git status of 50 GB trees, no host.log line for 100 min): the rest is next pass
            res.append(dict(stop="deadline")); log(dict(stop="deadline", t=time.strftime("%F %T"))); break
        if free() >= target_gb:
            res.append(dict(stop="target", free=round(free(), 1))); break
        if any(p == g or p.startswith(g + "/") for g in gone) or not os.path.isdir(p):
            continue
        rec = dict(tree=p, t=time.strftime("%F %T"), idle_h=round(idle / 3600, 1), kind="lane")
        why = refuse(p)
        if not why and link_hit(p, links):
            why = "a symlink under ~ points into it (%s)" % link_hit(p, links)
        if not why and post_text_hit(p, posts):
            why = "named in a hub post of the last 24 h"
        if not why:
            why = git_check(p) if git_check else ""
        if not why:
            sn, miss = signed_not_in_store(p, ids)
            rec.update(signed_units=sn, signed_not_in_store=miss)
            if miss:
                why = "%d SIGNED unit(s) not in the signed store" % miss
        if why:
            rec["result"] = "REFUSED: " + str(why)[:120]
        elif not apply:
            rec["result"] = "WOULD-DELETE"; gone.append(p)
        else:
            b = free()
            (delete or (lambda q: (os.system("find " + q + " -type d -exec chmod u+w {} +"), shutil.rmtree(q, ignore_errors=True))))(p)
            rec.update(result="DELETED" if not os.path.exists(p) else "FAILED", free_before=round(b, 1), free_after=round(free(), 1))
            if rec["result"] == "DELETED": gone.append(p)
        log(rec); res.append(rec)
    return res


LIVE_ROW = frozenset({"RUNNING", "ENQUEUED", "ROUTE-HELD", "DEDUP", "DEDUP-WAIT", "LAUNCHING", "RETRY-INFRA", "RETRY", "QUEUED", "STARTING"})
ATTEMPT_GLOB = "*/runs/*/kit-wave/*/*/items/*/attempt_*"
ATTEMPT_QUIET_S = 1800            # FAIL / CANCELLED attempts go once nothing in them changed for 30 min ("at once")
OLD_EVENT_IDLE_H = 12.0
KEEP_FAILED_H = 24.0              # the newest failed attempt of a type keeps its final DB this long


def attempt_candidates(claude, cfg, state, refs, now=None, quiet_s=ATTEMPT_QUIET_S, old_idle_h=OLD_EVENT_IDLE_H, mtime=newest_mtime, globber=None):
    """COORD 11-18 (owner aggressive rules): kit-wave attempt dirs of a finished work.  -> [(path, why)]
      * state row FAIL / CANCELLED / class SUPERSEDED (same die, event, item, attempt) and the item has a newer attempt or its event is not the die's current one: quiet >= quiet_s.
      * no state row, event != the die's current event, a higher attempt dir of the item exists: idle >= old_idle_h.
      * event != the die's current event (latest attempt too): idle >= old_idle_h, not named in refs (auto-resign state, COUNT-DIRECT ...), no q_signoff / carry-over row.
    Never: a live row of the item, the latest attempt of a current-event item, a hold-ECO marker < 7 d, anything named in refs, anything modified within the quiet / idle window."""
    now = now or time.time()
    items = (state or {}).get("items") or {}
    cur = {d: str(v.get("event")) for d, v in ((cfg or {}).get("dies") or {}).items() if isinstance(v, dict)}
    by = {}
    for v in items.values():
        if isinstance(v, dict):
            by.setdefault((v.get("die"), str(v.get("event")), v.get("item")), []).append(v)
    out, allf = [], {}
    for p in sorted((globber or (lambda: glob.glob(os.path.join(claude, ATTEMPT_GLOB))))()):
        if not os.path.isdir(p) or os.path.islink(p):
            continue
        parts = p.split("/runs/", 1)[1].split("/")           # <die>/kit-wave/<die>/<event>/items/<item>/attempt_N
        if len(parts) < 7:
            continue
        die, event, item = parts[0], parts[3], parts[5]
        tail = parts[6].split("_", 1)
        n = int(tail[1]) if len(tail) == 2 and tail[1].isdigit() else -1
        cand = by.get((die, event, item), [])
        if any(str(v.get("status")) in LIVE_ROW for v in cand):
            continue
        mine = [v for v in cand if v.get("attempt") == n]
        sib = [int(x.split("_", 1)[1]) for x in os.listdir(os.path.dirname(p)) if x.startswith("attempt_") and x.split("_", 1)[1].isdigit()]
        newer = any((v.get("attempt") or 0) > n for v in cand) or (sib and max(sib) > n)
        incur = cur.get(die) == event
        if mine:
            row = mine[0]
            if "q_signoff" in json.dumps(row) or "carry" in json.dumps(row).lower():
                continue
            failed = str(row.get("status")) in ("FAIL", "CANCELLED") or row.get("class") == "SUPERSEDED"
            if failed:
                try:
                    allf.setdefault((die, event, row.get("parent_item") or item), []).append((os.lstat(p).st_mtime, n, p))
                except OSError:
                    pass
            if failed and (newer or not incur):
                why, win = "failed/cancelled/superseded attempt, %s" % ("newer attempt exists" if newer else "event not current"), quiet_s
            elif not incur:
                why, win = "old-event attempt", old_idle_h * 3600
            else:
                continue
        else:
            if incur:
                continue
            if newer:
                why, win = "no state row, old event, newer attempt dir", old_idle_h * 3600
            else:
                why, win = "no state row, old event", old_idle_h * 3600
        if re.search(re.escape(p.split("/runs/", 1)[1].rsplit("/attempt_", 1)[0]) + r"/attempt_%d(?![0-9])" % n, refs or ""):
            continue
        if mtime(p, now - win) > now - win:
            continue
        out.append((p, why))
    # COORD 11-18 (the Fable lane could diagnose 1 of 11 setup-stopped strip DBs): the NEWEST failed attempt of each TYPE (over ALL its failed attempts, retired or not) keeps its final DB
    # (the whole attempt dir) for KEEP_FAILED_H after it last changed; older attempts of the type go as before.  Type = state parent_item, else the item.
    keep_cut = now - KEEP_FAILED_H * 3600
    keep = set()
    for grp in allf.values():
        m, n, p = max(grp)
        if m > keep_cut:
            keep.add(p)
    return [(p, why) for p, why in out if p not in keep]


KEEP_NAMES = ("reports", "logs", "REPORTS-KEPT.txt")      # COORD 11-18: reports/ (and bind inputs, via the guard's protected list) survive a cleanup


def strip_keep_reports(p, rm=None):
    """delete an attempt dir's contents except reports/, logs/ and REPORTS-KEPT.txt (the dir itself stays when one of them exists); a dir with none of them goes whole.
    The guard check happened on the dir before; every entry removed here is below it.  No rm: shutil only, symlinks unlinked, never followed."""
    # 11-18: a PermissionError (a root-owned file inside) used to escape and end the whole pass with rc 1 on all six hosts (0 deleted, every 30 min): errors are skipped here and the
    # attempt is reported FAILED by the caller when something is left.
    rm = rm or (lambda q: shutil.rmtree(q, ignore_errors=True))
    names = os.listdir(p)
    keep = [n for n in names if n in KEEP_NAMES]
    if not keep:
        os.system("find " + shlex_quote(p) + " -type d -exec chmod u+w {} +")
        rm(p)
        return
    for n in names:
        if n in KEEP_NAMES:
            continue
        q = os.path.join(p, n)
        try:
            if os.path.islink(q) or not os.path.isdir(q):
                os.unlink(q)
            else:
                os.system("find " + shlex_quote(q) + " -type d -exec chmod u+w {} +")
                rm(q)
        except OSError:
            pass


def shlex_quote(x):
    import shlex
    return shlex.quote(x)


def eco_marker(p):
    import subprocess
    r = subprocess.run(["find", p, "-maxdepth", "3", "(", "-iname", "*hold*eco*", "-o", "-iname", "eco_hold*", ")", "-mtime", "-7", "-print", "-quit"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def run_attempts(claude, cfg, state, refs, ids, g, prot, log, apply=False, delete=None, free=None, now=None, deadline=None, **kw):
    """delete attempt_candidates through the guard.  The kit_wave work root (runs/<die>/kit-wave) is a protected ANCESTOR of every attempt, so each listed attempt gets an exact
    allow entry (1 h, written here, reason cites COORD 11-18): it skips protected ancestors only, never a protected path inside, a live process or the signed-store check."""
    free = free or (lambda: free_gb(claude)); res = []
    cands = attempt_candidates(claude, cfg, state, refs, now, **kw)
    exp = int((now or time.time()) + 3600)
    allow = getattr(g, "ALLOW_EXACT", None)
    if apply and allow and cands:
        os.makedirs(os.path.dirname(allow), exist_ok=True)
        with open(allow, "a") as f:
            for p, _ in cands:
                f.write("%s\t%d\tauto_retire attempts (COORD 11-18 aggressive cleanup)\n" % (p, exp))
    for p, why0 in cands:
        if deadline and time.time() > deadline:
            res.append(dict(stop="deadline")); break
        rec = dict(tree=p, t=time.strftime("%F %T"), kind="attempt", why=why0)
        why = refuse_attempt(g, p, prot)
        if not why and eco_marker(p):
            why = "hold ECO marker < 7 d"
        if not why:
            sn, miss = signed_not_in_store(p, ids)
            rec.update(signed_units=sn, signed_not_in_store=miss)
            if miss:
                why = "%d SIGNED unit(s) not in the signed store" % miss
        if why:
            rec["result"] = "REFUSED: " + str(why)[:120]
        elif not apply:
            rec["result"] = "WOULD-DELETE"
        else:
            b = free()
            try:
                (delete or strip_keep_reports)(p)
            except Exception as e:                      # one attempt never ends the pass
                rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:100])
            left = os.listdir(p) if os.path.isdir(p) else []
            rec.update(result="DELETED" if not left or all(n in KEEP_NAMES for n in left) else "FAILED", free_before=round(b, 1), free_after=round(free(), 1))
        log(rec); res.append(rec)
    return res


def refuse_attempt(g, p, prot):
    try:
        return g.refuse(p, prot)
    except TypeError:
        return g.refuse(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--kit-wave", "--state", "--markers", "--store-ids", "--guard-module", "--list", "--log"):
        ap.add_argument(k, required=True)
    ap.add_argument("--root", default="/srv/opentallas-scratch2/claude/kw45"); ap.add_argument("--target", type=float, default=350.0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--lanes", action="store_true", help="also retire idle lane dirs and claude/wt children, after the source trees (idle window --idle-h, default 12)")
    ap.add_argument("--idle-h", type=float, default=12.0)
    ap.add_argument("--max-s", type=float, default=float(os.environ.get("AC_MAX_S", "600")), help="wall seconds per claude root; the pass stops starting new candidates after this and finishes (0 = no limit)")
    ap.add_argument("--attempts", action="store_true", help="retire finished kit-wave attempt dirs (failed/cancelled/superseded at once, old-event attempts after --idle-h)")
    ap.add_argument("--refs", default="", help="file: AUTO-RESIGN state + COUNT-DIRECT + ... text; an attempt named there is kept")
    ap.add_argument("--posts", default="", help="file: hub post text of the last 24 h; a lane tree named there is kept")
    a = ap.parse_args(argv)
    sp = importlib.util.spec_from_file_location("g", a.guard_module); g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
    prot, err = g.load_list(a.list)
    if prot is None:
        print("protected list unusable (fail closed): %s" % err); return 3
    cfgt = open(a.kit_wave).read()
    texts = [cfgt, open(a.state).read(), open(a.markers).read()]
    ids = {l.strip() for l in open(a.store_ids) if l.strip()}
    with open(a.log, "a") as lf:
        res = run(a.root, json.loads(cfgt), texts, ids, lambda t: g.refuse(t, prot), lambda r: lf.write(json.dumps(r) + "\n"), a.target, a.apply)
        claude = os.path.dirname(a.root.rstrip("/"))
        deadline = time.time() + a.max_s if a.max_s else None
        posts = open(a.posts, errors="replace").read() if a.posts else ""
        if a.attempts:                                  # attempts first (the biggest, most certain dead weight), then idle lanes
            res += run_attempts(claude, json.loads(cfgt), json.loads(texts[1]), open(a.refs, errors="replace").read() if a.refs else "", ids, g, prot,
                                lambda r: lf.write(json.dumps(r) + "\n"), a.apply, old_idle_h=a.idle_h, deadline=deadline)
        if a.lanes:
            res += run_lanes(claude, ids, lambda t: g.refuse(t, prot), lambda r: lf.write(json.dumps(r) + "\n"), a.target, a.apply, idle_h=a.idle_h, posts=posts, deadline=deadline)
    for r in res:
        print(r.get("result") or r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
