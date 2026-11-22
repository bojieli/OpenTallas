#!/usr/bin/env python3
"""kit_wave_edit.py: change kit_wave.json on the hub with a JSON patch and commit it in the same step (WAVE-CONFIG 11-16, FABLE-FLOW-2000 class D).

  python3 -I kit_wave_edit.py --message "KW-FIX-n: why" --patch '[{"op":"replace","path":"/dies/s81/max_inflight","value":40}]'
  python3 -I kit_wave_edit.py --message "..." --patch-file patch.json
  python3 -I kit_wave_edit.py --message "..." --set /enabled=false --set /dies/kv/owner_lane='"KV-R"'     (value = JSON; --unset /path removes)
  python3 -I kit_wave_edit.py event-pending <die> <event>     (FLEET-WATCH-R5: set when your apply gate starts; the apply clears it; expires after 60 min)
  python3 -I kit_wave_edit.py event-pending-clear <die>
  python3 -I kit_wave_edit.py --dry-run ...                                            (prints the diff, writes and commits nothing)
  python3 -I kit_wave_edit.py --expect-launch N ...      (H1, WAVE-OPS-R1 11-22: REQUIRED when the edit removes hold_items keys; N = rows that become launchable)

The patch is RFC 6902 (add, replace, remove, test; paths are JSON pointers, "-" appends to a list).  It is applied to the committed config
(`git show HEAD:autopilot/kit_wave.json`), never to a working copy somebody else is editing; a working copy that differs from HEAD is refused.  The
result is written in the file's format (indent 1, key order kept) and committed + pushed by ~/coord/bin/coord-commit.sh.  The wave
(kit_wave.py read_config_text) runs on the committed HEAD blob, so lanes must not edit the file in place: an uncommitted edit has no effect.
One editor at a time (.git/kit_wave_edit.lock in the coord checkout; the file names its holder)."""
import argparse
import copy
import fcntl
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REL = "autopilot/kit_wave.json"
HOST_ADD_PROBE = None          # tests inject probe(cfg) -> {host: {die: why}}


class PatchError(Exception):
    pass


def _tokens(ptr):
    if ptr == "":
        return []
    if not ptr.startswith("/"):
        raise PatchError(f"bad JSON pointer {ptr!r}")
    return [t.replace("~1", "/").replace("~0", "~") for t in ptr[1:].split("/")]


def _walk(doc, toks):
    cur = doc
    for t in toks:
        cur = _child(cur, t)
    return cur


def _child(cur, t):
    if isinstance(cur, dict):
        if t not in cur:
            raise PatchError(f"no key {t!r}")
        return cur[t]
    if isinstance(cur, list):
        try:
            return cur[int(t)]
        except (ValueError, IndexError):
            raise PatchError(f"no list index {t!r}")
    raise PatchError(f"cannot descend into {type(cur).__name__} at {t!r}")


def apply_patch(doc, ops):
    """a new document with the RFC 6902 ops applied (add, replace, remove, test); PatchError on any failed op, nothing partial"""
    doc = copy.deepcopy(doc)
    if not isinstance(ops, list):
        raise PatchError("a patch is a JSON list of operations")
    for n, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in ("add", "replace", "remove", "test") or "path" not in op:
            raise PatchError(f"op {n}: needs op (add|replace|remove|test) and path")
        kind, toks = op["op"], _tokens(op["path"])
        if kind != "remove" and "value" not in op:
            raise PatchError(f"op {n}: {kind} needs a value")
        try:
            if not toks:
                if kind == "test":
                    if doc != op["value"]:
                        raise PatchError("test failed at the root")
                    continue
                if kind == "remove":
                    raise PatchError("cannot remove the root")
                doc = copy.deepcopy(op["value"])
                continue
            parent, last = _walk(doc, toks[:-1]), toks[-1]
            if kind == "test":
                if _child(parent, last) != op["value"]:
                    raise PatchError(f"test failed at {op['path']}")
            elif isinstance(parent, dict):
                if kind in ("replace", "remove") and last not in parent:
                    raise PatchError(f"no key {last!r}")
                if kind == "remove":
                    del parent[last]
                else:
                    parent[last] = copy.deepcopy(op["value"])
            elif isinstance(parent, list):
                idx = len(parent) if last == "-" else int(last)
                if kind == "add":
                    if not 0 <= idx <= len(parent):
                        raise PatchError(f"list index {last!r} out of range")
                    parent.insert(idx, copy.deepcopy(op["value"]))
                else:
                    if not 0 <= idx < len(parent):
                        raise PatchError(f"list index {last!r} out of range")
                    if kind == "remove":
                        del parent[idx]
                    else:
                        parent[idx] = copy.deepcopy(op["value"])
            else:
                raise PatchError(f"cannot descend into {type(parent).__name__}")
        except PatchError as e:
            raise PatchError(f"op {n} ({kind} {op['path']}): {e}")
        except ValueError:
            raise PatchError(f"op {n} ({kind} {op['path']}): bad list index")
    return doc


def dump(doc):
    return json.dumps(doc, indent=1) + "\n"          # the format of the file in the hub checkout: indent 1, key order kept


def git(coord, *args, check=True):
    p = subprocess.run(["git", "-C", str(coord), *args], capture_output=True, text=True, timeout=120)
    if check and p.returncode:
        raise SystemExit(f"kit_wave_edit: git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p


def _event_terms(rel):
    return sorted(t for t in (rel or []) if str(t).startswith("event_adopt:"))


def release_repoint_errors(old_doc, new_doc, ops):
    """WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-1900 D): a hold's release term changes only when its CAUSE changes.  A patch that changes the event_adopt
    term of a hold record must also set that record's release_changed_because (the named cause change) in the same patch; a bulk re-point of
    many records to one event is refused (QC st_a was released by a bulk re-point to event_adopt:N1B while its fix is in N2B)."""
    errs, changed = [], []
    for die, d in (new_doc.get("dies") or {}).items():
        old = {r.get("id"): r for r in ((old_doc.get("dies") or {}).get(die) or {}).get("hold_records") or []}
        for r in d.get("hold_records") or []:
            o = old.get(r.get("id"))
            if o is None or _event_terms(o.get("release")) == _event_terms(r.get("release")):
                continue
            changed.append((die, r.get("id"), tuple(_event_terms(r.get("release")))))
            if not str(r.get("release_changed_because") or "").strip() or r.get("release_changed_because") == o.get("release_changed_because"):
                errs.append(f"{die}/{r.get('id')}: event term {_event_terms(o.get('release'))} -> {_event_terms(r.get('release'))} without a new release_changed_because (the cause that changed)")
    targets = {c[2] for c in changed}
    if len(changed) > 3 and len(targets) == 1:
        errs.append(f"bulk re-point refused: {len(changed)} hold records moved to the same event term; keep each hold's cause-specific term")
    return errs


LAUNCH_PROBE = None            # tests inject probe(coord, old_doc, new_doc, die) -> set of items newly eligible for launch


def noop_hold_record_problems(old_doc, new_doc):
    """H1 (WAVE-OPS-R1 11-22, FABLE-FLOW-0600 class H1): hold_records compile to nothing on a die where stops_off applies (every die but hbm, r703): only the
    hold_items list blocks there.  S81-J6-ASSEMBLY-R5 moved 342 holds into records on S81; 194 rows launched against them.  An edit that ADDS or CHANGES a hold
    record on such a die is refused (a no-op hold).  Records already in the file and untouched are not judged.  -> [problem text]"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from flow_guard import stops_off_die
    except Exception:
        return []
    od = (old_doc or {}).get("dies") or {}
    out = []
    for die, d in sorted(((new_doc or {}).get("dies") or {}).items()):
        if not isinstance(d, dict) or not isinstance(d.get("hold_records"), list) or not stops_off_die(new_doc, die):
            continue
        old = {r.get("id"): r for r in ((od.get(die) or {}).get("hold_records") or []) if isinstance(r, dict)} if isinstance(od.get(die), dict) else {}
        for r in d["hold_records"]:
            if isinstance(r, dict) and old.get(r.get("id")) != r:
                out.append(f"NO-OP-HOLD refused for {die}/{r.get('id')}: hold records do not block on {die} (stops_off, r703: only hbm keeps them); "
                           f"use the hold list instead: add the keys to dies.{die}.hold_items with 'owner=<lane> eta=<YYYY-mm-dd HH:MM>'")
    return out


def removed_hold_keys(old_doc, new_doc):
    """{die: [hold_items key, ...]} keys the edit REMOVES (a key gone, its map gone, or its die gone) -- a hold release.  Pure."""
    out = {}
    for die, d in ((old_doc or {}).get("dies") or {}).items():
        oh = d.get("hold_items") if isinstance(d, dict) else None
        if not isinstance(oh, dict) or not oh:
            continue
        nd = ((new_doc or {}).get("dies") or {}).get(die)
        nh = nd.get("hold_items") if isinstance(nd, dict) else None
        gone = [k for k in oh if not (isinstance(nh, dict) and k in nh)]
        if gone:
            out[die] = sorted(gone)
    return out


def _default_launch_probe(coord, old_doc, new_doc, die):
    """the wave's own select() on the OWNERS rows + state of the hub, with the old and the new config (hold_items are its first filter)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kit_wave as _KW
    ap = Path(coord) / "autopilot"
    owners = _KW.parse_owners((ap / "OWNERS.tsv").read_text())
    st = _KW.load_state(str(ap))
    st.setdefault("items", {})
    picks = []
    for doc in (old_doc, new_doc):
        cfg = _KW.load_config(dump(doc))
        p, _skip = _KW.select(owners, cfg, die, copy.deepcopy(st), None)
        picks.append({r["item"] for r in p})
    return picks[1] - picks[0]


def newly_launchable(coord, old_doc, new_doc, removed, probe=None):
    """{die: sorted items} rows that are held now and eligible to launch once the removed hold_items keys are gone (a dry select, no launch)"""
    probe = probe or LAUNCH_PROBE or _default_launch_probe
    return {die: sorted(probe(coord, old_doc, new_doc, die)) for die in sorted(removed)}


def launch_count_problems(coord, old_doc, new_doc, expect_launch, dry):
    """H1: removing hold_items keys needs --expect-launch N and N must equal the rows that become launchable.  -> [problem text] (prints the count)"""
    removed = removed_hold_keys(old_doc, new_doc)
    if not removed:
        if expect_launch is not None:
            print("kit_wave_edit: --expect-launch ignored: the edit removes no hold_items key")
        return []
    try:
        per = newly_launchable(coord, old_doc, new_doc, removed)
    except Exception as e:
        return [f"LAUNCH-COUNT refused: cannot count the rows that become launchable ({type(e).__name__}: {str(e)[:200]})"]
    n = sum(len(v) for v in per.values())
    detail = ", ".join(f"{die} {len(v)}" for die, v in per.items())
    print(f"kit_wave_edit: LAUNCHABLE {n} ({detail}) after removing {sum(len(v) for v in removed.values())} hold_items key(s)")
    if expect_launch is None:
        return [] if dry else [f"HOLD-RELEASE refused: removing hold keys needs --expect-launch N; {n} row(s) become launchable now ({detail}); "
                               f"rerun with --expect-launch {n} if that is meant"]
    if n != expect_launch:
        return [f"HOLD-RELEASE refused: --expect-launch {expect_launch} but {n} row(s) become launchable ({detail}); "
                f"{sorted(x for v in per.values() for x in v)[:12]}"]
    return []


def edit(coord, ops, message, dry=False, commit_cmd=None, expect_launch=None):
    """patch the committed config and commit it; returns the new text.  commit_cmd(message, rel) overrides coord-commit.sh (tests)"""
    coord = Path(coord)
    gd = git(coord, "rev-parse", "--absolute-git-dir").stdout.strip()      # ~/coord is a linked worktree: .git is a file there
    lock = open(Path(gd) / "kit_wave_edit.lock", "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.seek(0)
        raise SystemExit(f"kit_wave_edit: another edit holds kit_wave_edit.lock: {lock.read().strip() or 'unknown'}")
    lock.seek(0); lock.truncate(); lock.write(f"pid={os.getpid()} cmd={' '.join(sys.argv)[:200]}\n"); lock.flush()
    try:
        for _try in range(5):
            res = _edit_once(coord, ops, message, dry, commit_cmd, expect_launch)
            if res != "retry":
                return res
        raise SystemExit("kit_wave_edit: the file kept moving under the edit (5 compare-and-swap retries); nothing left half-written")
    finally:
        lock.close()


def hold_term_problems(old_doc, new_doc):
    """F5 (FLOW-OPS-R2 11-22, FABLE-FLOW-0000): a hold_items key ADDED (or re-worded) by an edit must carry owner=<lane> and eta=<YYYY-mm-dd[ HH:MM]> in
    its text, so the wave can report HOLD-OVERDUE.  Removing a hold is always allowed; untouched old keys are not judged.  -> [problem text]"""
    import re as _re
    od, nd = (old_doc or {}).get("dies") or {}, (new_doc or {}).get("dies") or {}
    out = []
    for die, d in sorted(nd.items()):
        if not isinstance(d, dict) or not isinstance(d.get("hold_items"), dict):
            continue
        oh = ((od.get(die) or {}).get("hold_items") or {}) if isinstance(od.get(die), dict) else {}
        for k, v in d["hold_items"].items():
            if oh.get(k) == v:
                continue
            s = str(v)
            if not (_re.search(r"\bowner\s*[=:]\s*[A-Za-z0-9_.-]+", s, _re.I) and _re.search(r"\beta\s*[=:]\s*\d{4}-\d\d-\d\d", s, _re.I)):
                out.append(f"HOLD-TERM refused for {die}/{k}: a new hold needs 'owner=<lane> eta=<YYYY-mm-dd HH:MM>' in its text (F5: holds with no term idle the fleet)")
    return out


def required_review_problems(old_doc, new_doc):
    """VISUAL-NOBLOCK (FLOW-OPS-R2 11-22, FABLE-FLOW-2200 item 1; owner rule "visual review never blocks"): a die's
    review_before_route.required = true held 50 rows WAIT-VISUAL 24-39 h after it was put back 11-21 03:07-04:12 and 14:16-14:21.
    An edit that sets it (where the die did not already carry it) is refused; removing it is always allowed.  -> [problem text]"""
    od, nd = (old_doc or {}).get("dies") or {}, (new_doc or {}).get("dies") or {}
    out = []
    for die, d in sorted(nd.items()):
        if not isinstance(d, dict):
            continue
        new_req = ((d.get("review_before_route") or {}) if isinstance(d.get("review_before_route"), dict) else {}).get("required") is True
        o = (od.get(die) or {}).get("review_before_route") if isinstance(od.get(die), dict) else None
        old_req = isinstance(o, dict) and o.get("required") is True
        if new_req and not old_req:
            out.append(f"REQUIRED-REVIEW refused for {die}: review_before_route.required makes visual review a route hold; owner rule: visual "
                       "review never blocks (advisory review: leave out 'required', the GEOM queue lists the rows)")
    return out


def event_problems(old_doc, new_doc):
    """FLOW-1949 (1): a die whose event CHANGED must carry an event the wave's die gate can resolve: a label of the die's accepted list (GATE_EVENTS exact + gate_events_extra) or, for a commit-typed
    die, a hex commit id.  A synthetic key (spaces, empty, an unlisted label) would turn the die off at the next tick.  -> [problem text].  Needs kit_wave (same dir); absent -> no check"""
    try:
        import re
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import kit_wave as _KW
    except Exception:
        return []
    out = []
    od, nd = (old_doc or {}).get("dies") or {}, (new_doc or {}).get("dies") or {}
    for die, d in nd.items():
        if not isinstance(d, dict) or not d.get("enabled") or str(d.get("event") or "") == str((od.get(die) or {}).get("event") or ""):
            continue
        ev, rule = str(d.get("event") or ""), _KW.GATE_EVENTS.get(die)
        if not ev.strip() or re.search(r"\s", ev):
            out.append(f"{die}: event {ev!r} is empty or has whitespace (not a resolvable event)")
        elif rule and "exact" in rule and ev not in rule["exact"] and ev not in (d.get("gate_events_extra") or ()):
            out.append(f"{die}: event {ev!r} is not in the die's accepted events (GATE_EVENTS exact / gate_events_extra); add it to gate_events_extra in the same edit")
        elif rule and "descends" in rule and not re.fullmatch(r"[0-9a-f]{7,40}", ev):
            out.append(f"{die}: event {ev!r} is not a commit id (the die gate needs one descending from {rule['descends']})")
    return out


def cas_write(coord, new_obj, base_text, wait_s=120):
    """COORD 11-18 (a writer holding a stale snapshot overwrote kit_wave.json 70 s after a commit and blocked every kit_wave_edit): the whole-file writers
    (apply_reviewed_tree_marker) write through this: take kit_wave_edit.lock (blocking up to wait_s, so no edit is in flight), compare the file with the text this writer READ at its start
    (compare-and-swap) and write atomically only when equal.  A moved file raises SystemExit, nothing written: rerun the apply on the new content.  The caller commits."""
    import time
    coord = Path(coord)
    gd = git(coord, "rev-parse", "--absolute-git-dir", check=False).stdout.strip() or str(coord)      # a non-git coord dir (tests): the lock file sits beside the config
    lock = open(Path(gd) / "kit_wave_edit.lock", "a+")
    t0 = time.time()
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() - t0 > wait_s:
                lock.seek(0)
                raise SystemExit(f"kit_wave_edit: lock held {wait_s}s by: {lock.read().strip() or 'unknown'}; nothing written")
            time.sleep(1)
    try:
        lock.seek(0); lock.truncate(); lock.write(f"pid={os.getpid()} cmd=cas_write {' '.join(sys.argv)[:160]}\n"); lock.flush()
        p = coord / REL
        if p.read_text() != base_text:
            raise SystemExit(f"kit_wave_edit: {REL} changed while this writer worked (compare-and-swap failed); nothing written, rerun on the new content")
        _ep = event_problems(json.loads(base_text), new_obj)
        if _ep:
            raise SystemExit("kit_wave_edit: die event refused at write time, nothing written: " + "; ".join(_ep[:4]))
        tmp = p.with_name(p.name + f".tmp.cas.{os.getpid()}")
        tmp.write_text(dump(new_obj))
        os.replace(tmp, p)
    finally:
        lock.close()


def blob_sha(coord):
    return git(coord, "rev-parse", f"HEAD:{REL}").stdout.strip()


def commit_config(coord, message, commit_cmd):
    """Return the config commit itself, even when other journal commits move HEAD."""
    if commit_cmd:
        pushed = commit_cmd(message, REL)
        if isinstance(pushed, str) and pushed:
            return pushed
        return git(coord, "log", "-1", "--first-parent", "--format=%H", "HEAD", "--", REL).stdout.strip()
    result = subprocess.run(
        ["bash", os.path.expanduser("~/coord/bin/coord-commit.sh"), message, REL],
        timeout=600, stdout=subprocess.PIPE, text=True,
    )
    sys.stdout.write(result.stdout)
    result.check_returncode()
    receipts = re.findall(r"(?m)^PUSHED ([0-9a-f]{40,64})$", result.stdout)
    if not receipts:
        raise SystemExit("kit_wave_edit: push command returned no exact commit receipt")
    return receipts[-1]


def added_gen_hosts(old_doc, new_doc):
    """{die: [host, ...]} hosts a patch adds to dies.<die>.gen_hosts / gen_host (pure)"""
    out = {}
    for die, d in ((new_doc or {}).get("dies") or {}).items():
        if not isinstance(d, dict):
            continue
        o = ((old_doc or {}).get("dies") or {}).get(die) or {}
        was = set(o.get("gen_hosts") or []) | ({o.get("gen_host")} if o.get("gen_host") else set())
        now = list(d.get("gen_hosts") or []) + ([d.get("gen_host")] if d.get("gen_host") else [])
        add = [h for h in dict.fromkeys(now) if h and h not in was]
        if add:
            out[die] = add
    return out


class _ProbeAP:
    """the AP surface kit_wave.src_incomplete needs (sh with stdin), run locally / over ssh"""
    HUB_NAME = os.environ.get("OT_HUB_NAME", "intel2")

    @staticmethod
    def sh(argv, timeout=180, input=None):
        try:
            r = subprocess.run(argv, input=input, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout, r.stderr
        except (OSError, subprocess.SubprocessError) as e:
            return 255, "", str(e)


def host_add_problems(new_doc, added, probe=None):
    """FLOW-OPS-1300 / FABLE-FLOW-1900 (intel2 joined QC/KV/S81 gen_hosts without the bind / postbind / macro trees: SRC-INCOMPLETE 4 ticks running): a host is
    added to a die's gen hosts only when the wave's own input-closure probe (kit_wave.src_incomplete) finds nothing missing there.  -> ["die host: why", ...].
    probe(cfg) -> {host: {die: why}} (tests); default = kit_wave.src_incomplete with a local/ssh AP.  OT_HOST_ADD_FORCE=1 skips (logged in the commit)."""
    if not added or os.environ.get("OT_HOST_ADD_FORCE") == "1":
        return []
    cfg = copy.deepcopy(new_doc)
    for die, d in list((cfg.get("dies") or {}).items()):
        if die not in added:
            d["src_probe"] = False                       # probe only the dies that gain a host ...
        else:
            d["gen_hosts"] = list(added[die])            # ... and only on the hosts they gain
            d["gen_host"] = added[die][0]
    cfg["_hub"] = _ProbeAP.HUB_NAME
    if probe is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import kit_wave as _KW
        probe = lambda c: _KW.src_incomplete(_ProbeAP, c)
    res = probe(cfg) or {}
    return [f"{die} {h}: {str(why)[:400]}" for h, ds in sorted(res.items()) for die, why in sorted(ds.items()) if h in added.get(die, [])]


def _edit_once(coord, ops, message, dry, commit_cmd, expect_launch=None):
    """one read-modify-write.  WAVE-PILOT-FIX 11-17 (COORD, 17:5x: a patch applied to a copy of HEAD read minutes earlier reverted another lane's
    commit): the base is the blob sha of HEAD:file read just now; before the commit it is compared again (compare-and-swap) and the patch is
    re-applied to the new HEAD when it moved; the pushed commit receipt's PARENT blob must equal the base, else the commit overwrote a commit
    that slipped in while coord-commit waited for its lock, and the patch is re-applied on top of that parent immediately (repair)."""
    base_ref = git(coord, "rev-parse", "HEAD").stdout.strip()
    base = git(coord, "rev-parse", f"{base_ref}:{REL}").stdout.strip()
    head = git(coord, "show", f"{base_ref}:{REL}").stdout
    work_p = coord / REL
    work = work_p.read_text() if work_p.exists() else head
    if work != head:
        raise SystemExit(f"kit_wave_edit: {REL} in {coord} differs from HEAD (an uncommitted edit by someone else); "
                         f"commit or discard it first: git -C {coord} diff {REL}")
    try:
        _old = json.loads(head)
        _newdoc = apply_patch(_old, ops)
        _errs = release_repoint_errors(_old, _newdoc, ops) + event_problems(_old, _newdoc) + required_review_problems(_old, _newdoc) + hold_term_problems(_old, _newdoc) + noop_hold_record_problems(_old, _newdoc)
        _errs += launch_count_problems(coord, _old, _newdoc, expect_launch, dry)
        _hp = host_add_problems(_newdoc, added_gen_hosts(_old, _newdoc), HOST_ADD_PROBE)
        if _hp:
            _errs += ["HOST-ADD refused, input closure incomplete (copy the trees, re-run; OT_HOST_ADD_FORCE=1 overrides): " + " | ".join(_hp[:6])]
        if _errs:
            raise PatchError("; ".join(_errs[:6]))
        new = dump(_newdoc)
    except (PatchError, ValueError) as e:
        raise SystemExit(f"kit_wave_edit: patch refused, nothing written: {e}")
    if new == head:
        print("kit_wave_edit: no change")
        return new
    if dry:
        import difflib
        sys.stdout.writelines(difflib.unified_diff(head.splitlines(True), new.splitlines(True), "HEAD:" + REL, "patched", n=1))
        return new
    if blob_sha(coord) != base:                          # compare-and-swap: HEAD moved while the patch was computed
        return "retry"
    tmp = work_p.with_name(work_p.name + f".edit{os.getpid()}")
    tmp.write_text(new)
    os.replace(tmp, work_p)                            # atomic: a reader never sees half a file
    try:
        pushed = commit_config(coord, message, commit_cmd)
    except Exception:
        work_p.write_text(head)                        # failed commit: put the committed text back, never leave an unpushed edit
        raise
    tip = git(coord, "show", f"HEAD:{REL}").stdout
    if tip != new or git(coord, "show", f"{pushed}:{REL}").stdout != new:
        work_p.write_text(tip)
        raise SystemExit("kit_wave_edit: coord-commit did not leave the patched config at HEAD; working file restored")
    parent = git(coord, "rev-parse", f"{pushed}~1:{REL}", check=False).stdout.strip()
    if parent and parent != base:                        # a commit slipped in between our read and our commit and was overwritten: put it back
        print(f"kit_wave_edit: CAS repair: parent blob {parent[:12]} != base {base[:12]}, re-applying the patch on the parent")
        old_parent = git(coord, "show", f"{pushed}~1:{REL}").stdout
        try:
            fixed = dump(apply_patch(json.loads(old_parent), ops))
        except (PatchError, ValueError) as e:
            raise SystemExit(f"kit_wave_edit: CAS repair failed, the committed file lost another commit's change; fix by hand: {e}")
        if fixed != new:
            tmp2 = work_p.with_name(work_p.name + f".repair{os.getpid()}")
            tmp2.write_text(fixed)
            os.replace(tmp2, work_p)
            pushed = commit_config(coord, message + " (CAS repair: keeps the commit that landed in between)", commit_cmd)
            new = fixed
    print(f"kit_wave_edit: committed {REL} at {pushed}")
    return new




def event_pending_ops(cmd, die, event, doc):
    """FLEET-WATCH-R5 11-21 (FABLE-FLOW-0800 class d): `event-pending <die> <event>` sets dies.<die>.event_pending = {event, since} (new launches for the die wait until the apply lands, max 60 min);
    `event-pending-clear <die>` removes it (a no-op when absent).  -> ops"""
    import time
    if die not in (doc.get("dies") or {}):
        raise SystemExit(f"kit_wave_edit: unknown die {die!r}")
    if cmd == "event-pending":
        return [{"op": "add", "path": f"/dies/{die}/event_pending", "value": {"event": event, "since": time.time()}}]
    return [{"op": "remove", "path": f"/dies/{die}/event_pending"}] if "event_pending" in doc["dies"][die] else []


def main_event_pending(argv):
    ap = argparse.ArgumentParser(prog="kit_wave_edit event-pending")
    ap.add_argument("cmd", choices=["event-pending", "event-pending-clear"])
    ap.add_argument("die")
    ap.add_argument("event", nargs="?", default="")
    ap.add_argument("--coord", default=os.environ.get("AP_COORD", os.path.expanduser("~/coord")))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "event-pending" and not a.event:
        raise SystemExit("kit_wave_edit: event-pending <die> <event>")
    doc = json.loads((Path(a.coord) / REL).read_text())
    ops = event_pending_ops(a.cmd, a.die, a.event, doc)
    if not ops:
        print(f"kit_wave_edit: {a.die} has no event_pending; nothing to clear")
        return 0
    who = os.environ.get("OT_LANE", "lane")
    msg = (f"{who}: event_pending {a.die} {a.event}: apply gate started, new launches for the die wait (max 60 min)" if a.cmd == "event-pending"
           else f"{who}: event_pending cleared for {a.die}")
    edit(a.coord, ops, msg, dry=a.dry_run)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("event-pending", "event-pending-clear"):
        return main_event_pending(argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--coord", default=os.environ.get("AP_COORD", os.path.expanduser("~/coord")))
    ap.add_argument("--message", "-m", required=True, help="commit message (name the lane and why)")
    ap.add_argument("--patch", help="JSON patch (a list of ops) inline")
    ap.add_argument("--patch-file", help="JSON patch file")
    ap.add_argument("--set", action="append", default=[], metavar="/PTR=JSON", help="replace-or-add the value at the pointer")
    ap.add_argument("--unset", action="append", default=[], metavar="/PTR")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--expect-launch", type=int, default=None, metavar="N",
                    help="required when the edit removes hold_items keys: the number of rows that become launchable (the edit prints it; refused when it differs)")
    a = ap.parse_args(argv)
    ops = []
    try:
        if a.patch:
            ops += json.loads(a.patch)
        if a.patch_file:
            ops += json.loads(Path(a.patch_file).read_text())
        for s in a.set:
            ptr, _, val = s.partition("=")
            ops.append({"op": "add", "path": ptr, "value": json.loads(val)})     # RFC 6902 add replaces an existing member
        for u in a.unset:
            ops.append({"op": "remove", "path": u})
    except ValueError as e:
        raise SystemExit(f"kit_wave_edit: bad JSON: {e}")
    if not ops:
        raise SystemExit("kit_wave_edit: no patch (--patch, --patch-file, --set or --unset)")
    edit(a.coord, ops, a.message, dry=a.dry_run, expect_launch=a.expect_launch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
