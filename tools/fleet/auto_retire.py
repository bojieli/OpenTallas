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
            (delete or (lambda p: (os.system("chmod -R u+w " + p), shutil.rmtree(p, ignore_errors=True))))(t)
            rec.update(result="DELETED" if not os.path.exists(t) else "FAILED", free_before=round(b, 1), free_after=round(free(), 1))
        log(rec); res.append(rec)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--kit-wave", "--state", "--markers", "--store-ids", "--guard-module", "--list", "--log"):
        ap.add_argument(k, required=True)
    ap.add_argument("--root", default="/srv/opentallas-scratch2/claude/kw45"); ap.add_argument("--target", type=float, default=350.0)
    ap.add_argument("--apply", action="store_true")
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
    for r in res:
        print(r.get("result") or r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
