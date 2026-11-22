"""bind_emit_par: the per-type emit of a die bind in parallel forked workers (FABLE-PIPELINE-R1, OWNER 11-21 "why does bind take hours").

Binder.emit runs emit_type + the per-type RTL passes for every bound type, one after the other, on one core: the long pole of a strict
bind (QC N4 1056 s of ~40 min, BIND-SPEED-1118).  The types do not read each other's emit results, but they share the Binder object, so
threads cannot split them.  Here each type runs in a FORKED child (a private copy-on-write Binder), and the child sends back only what
it changed:

    child:   snapshot Binder.__dict__  ->  Binder._emit_one(tn, ps, out, files)  ->  delta ops + new files + captured stdout/stderr
    parent:  applies the deltas in SORTED TYPE ORDER (the serial order), replays the output in that order, and goes on with emit_top.

The delta is generic (no list of attributes to keep in step with bind.py): attributes whose pickle is small (< DEEP_MAX) are compared
deeply; objects that are big or do not pickle are followed into their own attributes; big containers (the elaborated netlist) one level
deep (new / replaced keys, list tails).  Ops: set (dict key / attribute /
whole value), extend (list tail), union (set).  Anything else (a removed key, a list edited in place, two types setting one path to
values that do not merge) is UNSAFE: the parent raises ParUnsafe before touching its state and the caller reruns the plain serial loop, so a
form this module does not understand costs time, never a wrong bind.

    OT_BIND_EMIT_J=N     workers (default `auto` = min(8, cpus/4, what the memory limit holds); 1 = the plain serial loop)
    OT_BIND_EMIT_PAR_REC=FILE   per-type wall / worker private memory record (default OUT/bind_emit_par.json)

Proof duty of a caller that turns it on for a new die: one serial and one parallel bind of the same inputs, `diff -r` of the two out
directories (tools/die_plan/test_bind_emit_par.py does it on a synthetic Binder; ot-build records the real-die comparisons)."""
import copy
import io
import json
import os
import pickle
import re
import sys
import tempfile
import time
import traceback

DEEP_MAX = int(os.environ.get("OT_BIND_EMIT_DEEP_MAX", str(16 << 20)))
_ABSENT = object()


class ParUnsafe(Exception):
    """a state change the delta cannot express, or a cross-type conflict: the caller falls back to the serial loop"""


DEFAULT_J = "auto"         # proven byte-identical to the serial loop on KV D27d3 (OPUS-PIPELINE-R2 11-21); OT_BIND_EMIT_J=1 = serial
WORKER_FRAC = 0.8          # a worker's private (dirtied) memory per byte of the parent's RSS: KV D27d3 ~6 GB per 8 GB parent


def _mem_limit_bytes():
    """-> the tightest memory limit over this process's cgroup (v2 memory.max up the tree) and MemAvailable + own RSS"""
    lims = []
    try:
        for ln in open("/proc/meminfo"):
            if ln.startswith("MemAvailable:"):
                lims.append(int(ln.split()[1]) * 1024 + _rss_bytes())
    except OSError:
        pass
    try:
        rel = [ln.split(":", 2)[2].strip() for ln in open("/proc/self/cgroup") if ln.startswith("0::")]
        p = "/sys/fs/cgroup" + (rel[0] if rel else "")
        while p.startswith("/sys/fs/cgroup"):
            try:
                v = open(os.path.join(p, "memory.max")).read().strip()
                if v != "max":
                    used = int(open(os.path.join(p, "memory.current")).read().strip())
                    lims.append(int(v) - used + _rss_bytes())
            except (OSError, ValueError):
                pass
            if p == "/sys/fs/cgroup":
                break
            p = os.path.dirname(p)
    except OSError:
        pass
    return min(lims) if lims else None


def _rss_bytes():
    try:
        for ln in open("/proc/self/status"):
            if ln.startswith("VmRSS:"):
                return int(ln.split()[1]) * 1024
    except OSError:
        pass
    return 0


def mem_jobs(rss=None, limit=None):
    """-> how many workers fit next to the parent in the memory this process may use (at least 1)"""
    rss = _rss_bytes() if rss is None else rss
    limit = _mem_limit_bytes() if limit is None else limit
    if not rss or not limit:
        return 8
    return max(1, int((limit - 1.1 * rss) // (WORKER_FRAC * rss)))


def jobs():
    """OT_BIND_EMIT_J: N workers, 1 = the serial loop, `auto` (the default) = min(8, cpus/4, what the memory limit holds)"""
    v = os.environ.get("OT_BIND_EMIT_J", DEFAULT_J).strip() or DEFAULT_J
    if v == "auto":
        return max(1, min(8, (os.cpu_count() or 4) // 4, mem_jobs()))
    try:
        return max(1, int(v))
    except ValueError:
        return 1


# ---- snapshots ------------------------------------------------------------------------------------------------------------------
def _try_pickle(v, cap):
    """-> pickle bytes when the value pickles and is at most cap bytes, else None (big or not picklable)"""
    class _Cap(io.BytesIO):
        def write(self, b):
            if self.tell() + len(b) > cap:
                raise OverflowError
            return super().write(b)
    buf = _Cap()
    try:
        pickle.Pickler(buf, protocol=pickle.HIGHEST_PROTOCOL).dump(v)
    except (OverflowError, RecursionError, pickle.PicklingError, TypeError, AttributeError, ValueError):
        return None
    return buf.getvalue()


def _shallow(v):
    """one-level fingerprint of a big / unpicklable value"""
    if isinstance(v, dict):
        return ("dict", {k: id(x) for k, x in v.items()})
    if isinstance(v, list):
        return ("list", len(v), [id(x) for x in v])
    if isinstance(v, (set, frozenset)):
        return ("set", set(v))
    if hasattr(v, "__dict__") and not isinstance(v, type):
        return ("obj", id(v), {k: id(x) for k, x in vars(v).items()})
    return ("id", id(v))


def snapshot(state, deep_max=None, depth=0, seen=None):
    """child, before its type: per entry of the state dict (Binder.__dict__, or vars() of an object it holds)
         ("deep", pickle)            small and picklable: compared exactly afterwards
         ("obj", ref, {..})          an object that is big or does not pickle: its own attributes, the same way (4 levels)
         ("shallow", fp, ref)        a big container: one level (keys / length / item identities)"""
    deep_max = DEEP_MAX if deep_max is None else deep_max
    seen = set() if seen is None else seen
    snap = {}
    for k, v in state.items():
        b = _try_pickle(v, deep_max)
        if b is not None:
            snap[k] = ("deep", b)
        elif id(v) in seen:
            snap[k] = ("alias", v)                   # the Binder itself (self.pc.B) or an object already followed: reported at its first path
        elif hasattr(v, "__dict__") and not isinstance(v, type) and depth < 4 \
                and not callable(v) and type(v).__module__ != "builtins":
            seen.add(id(v))
            snap[k] = ("obj", v, snapshot(vars(v), deep_max, depth + 1, seen))
        else:
            snap[k] = ("shallow", _shallow(v), v)
    return snap


def kinds(snap, pre=""):
    out = {}
    for k, s in snap.items():
        if s[0] == "obj":
            out[pre + str(k)] = "obj"
            out.update(kinds(s[2], pre + str(k) + "."))
        else:
            out[pre + str(k)] = s[0]
    return out


# ---- delta ----------------------------------------------------------------------------------------------------------------------
def _diff(old, new, path, ops):
    """structural diff of two plain values -> ops; raises ParUnsafe on a change no op expresses"""
    if type(old) is not type(new):
        ops.append(("set", path, new))           # includes None -> value (a lazily computed memo)
        return
    if isinstance(new, dict):
        gone = [k for k in old if k not in new]
        if gone:
            raise ParUnsafe(f"{_p(path)}: key(s) removed {gone[:3]}")
        for k, v in new.items():
            if k not in old:
                _new(path + (("k", k),), v, ops)
            elif old[k] != v or _retyped(old[k], v):
                _diff(old[k], v, path + (("k", k),), ops)
        return
    if isinstance(new, list):
        if len(new) >= len(old) and new[:len(old)] == old:
            if len(new) > len(old):
                ops.append(("extend", path, new[len(old):]))
            return
        if len(new) == len(old):                 # same length, items edited in place: item-wise
            for i, (a, b) in enumerate(zip(old, new)):
                if a != b:
                    _diff(a, b, path + (("i", i),), ops)
            return
        raise ParUnsafe(f"{_p(path)}: list changed other than by append ({len(old)} -> {len(new)} items)")
    if isinstance(new, set):
        if old - new:
            raise ParUnsafe(f"{_p(path)}: set items removed")
        if new - old:
            ops.append(("union", path, new - old))
        return
    if hasattr(new, "__dict__") and not isinstance(new, type) and type(new).__eq__ is object.__eq__:
        _diff(vars(old), vars(new), path + (("o",),), ops)
        return
    if old != new:
        if _num(old) and _num(new):
            ops.append(("add", path, new - old))     # a number that moved: its increment (a statistics counter sums over the types)
        else:
            ops.append(("set", path, new))


COUNTER_RE = re.compile(r"(^|_)(stats?|counts?|counters?|emitted|total|n)(_|$)")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_counter(path):
    """a number changed by MORE than one type is summed only where the name says it is a count (self.pc.stats['cells_emitted']);
    any other shared number (a maximum, a last-writer value) stays ParUnsafe"""
    return any(step[0] == "k" and isinstance(step[1], str) and COUNTER_RE.search(step[1]) for step in path)


def _new(path, v, ops):
    """a value that did not exist before (or replaces None): sent whole; the parent merges what several types created at one path"""
    ops.append(("set", path, v))


def merge_set(a, b, path):
    """two types set one path.  Equal non-numeric values are one memo / flag (computed by whichever type came first: once); two dicts
    are merged key by key (`self.__dict__.setdefault("_receipts", {})[tn] = r`); two sets are united.  Everything else -- equal
    numbers (a counter: 0 -> 1 in every worker), different lists or scalars (last writer) -- is a cross-type value: ParUnsafe."""
    if _num(a) and _num(b) and _is_counter(path):
        return a + b                                 # a count first created by the workers themselves (stats.get(k, 0) + n): absent = 0
    if type(a) is type(b):
        if isinstance(a, dict):
            out = copy.copy(a)                       # keeps a defaultdict / Counter what it is
            for k, v in b.items():
                if k not in a:
                    out[k] = v
                elif not _num(v) and _same_pickle(a[k], v):
                    out[k] = a[k]                    # one cache entry / record both types computed the same (Plan._reset_tree_cache)
                else:
                    out[k] = merge_set(a[k], v, path + (("k", k),))
            return out
        if isinstance(a, (set, frozenset)):
            return a | b
        try:
            same = a == b
        except Exception:
            same = False
        if same is not True and not isinstance(a, (int, float, list, tuple, str, bytes)):
            try:                                     # an object without __eq__ (a lazily built plan record): equal when it pickles the same
                same = pickle.dumps(a, protocol=4) == pickle.dumps(b, protocol=4)
            except Exception:
                same = False
        if same is True and (isinstance(a, bool) or not isinstance(a, (int, float))):
            return a
        if hasattr(a, "__dict__") and not isinstance(a, type) and type(a).__eq__ is object.__eq__:
            # a lazily built record object that every type created and then filled with its OWN cache entries
            # (clock_landings._physical_clock_plan = schema.Plan: _reset_tree_cache[(kind, type)]): merged attribute by
            # attribute -- an attribute that pickles the same everywhere is one value, dicts merge key by key, anything else
            # follows the rules above (a clash stays ParUnsafe).  The serial loop ends with the same union of entries.
            va, vb = vars(a), vars(b)
            merged = dict(va)
            for k, y in vb.items():                  # a cache attribute only some types created (a lazy memo of the record): taken whole
                if k not in va:
                    merged[k] = y
                    continue
                x = va[k]
                if not (_num(x) and _is_counter(path + (("o",), ("k", k)))) and _same_pickle(x, y):
                    merged[k] = x
                else:
                    merged[k] = merge_set(x, y, path + (("o",), ("k", k)))
            out = copy.copy(a)
            out.__dict__.clear()
            out.__dict__.update(merged)
            return out
    raise ParUnsafe(f"{_p(path)}: set by more than one type to values that do not merge (a counter / last-writer value)")


def _same_pickle(x, y):
    if x is y:
        return True
    try:
        return pickle.dumps(x, protocol=4) == pickle.dumps(y, protocol=4)
    except Exception:
        return False


def _retyped(a, b):
    return type(a) is not type(b)


def _p(path):
    out = "self"
    for n, step in enumerate(path):
        if step[0] == "k":
            prev_obj = n == 0 or path[n - 1][0] == "o"
            out += ("." + str(step[1])) if prev_obj else "[%r]" % (step[1],)
        elif step[0] == "i":
            out += "[%d]" % step[1]
    return out


def delta(snap, state, pre=()):
    """child, after its type: ops that turn the snapshot state into the state now"""
    ops = []
    for k in snap:
        if k not in state:
            raise ParUnsafe(f"{_p(pre + (('k', k),))}: attribute deleted")
    for k, v in state.items():
        path = pre + (("k", k),)
        if k not in snap:
            _new(path, v, ops)
            continue
        s = snap[k]
        if s[0] == "deep":
            nb = _try_pickle(v, len(s[1]) * 8 + (64 << 20))
            if nb == s[1]:
                continue
            old = pickle.loads(s[1])
            if nb is None:
                ops.append(("set", path, v))
                continue
            _diff(old, pickle.loads(nb), path, ops)          # diff on plain copies: identical object graphs on both sides
            continue
        if s[0] == "alias":
            if v is not s[1]:
                ops.append(("set", path, v))
            continue
        if s[0] == "obj":
            if v is not s[1]:
                ops.append(("set", path, v))
            else:
                ops.extend(delta(s[2], vars(v), path + (("o",),)))
            continue
        _, fp, ref = s
        if v is not ref:
            ops.append(("set", path, v))
            continue
        now = _shallow(v)
        if now == fp:
            continue
        if fp[0] == "dict":
            if any(q not in now[1] for q in fp[1]):
                raise ParUnsafe(f"{_p(path)}: key(s) removed from a large dict")
            for q, i in now[1].items():
                if q not in fp[1]:
                    _new(path + (("k", q),), v[q], ops)
                elif fp[1][q] != i:
                    ops.append(("set", path + (("k", q),), v[q]))
        elif fp[0] == "list":
            if now[1] < fp[1] or now[2][:fp[1]] != fp[2]:
                raise ParUnsafe(f"{_p(path)}: large list changed other than by append")
            ops.append(("extend", path, v[fp[1]:]))
        elif fp[0] == "set":
            if fp[1] - now[1]:
                raise ParUnsafe(f"{_p(path)}: items removed from a large set")
            ops.append(("union", path, now[1] - fp[1]))
        elif fp[0] == "obj":
            if any(q not in now[2] for q in fp[2]):
                raise ParUnsafe(f"{_p(path)}: attribute removed from an object")
            for q, i in now[2].items():
                if q not in fp[2]:
                    _new(path + (("o",), ("k", q)), vars(v)[q], ops)
                elif fp[2][q] != i:
                    ops.append(("set", path + (("o",), ("k", q)), vars(v)[q]))
        else:
            ops.append(("set", path, v))
    return ops


def _resolve(state, path):
    """-> (container, last step) so the op applies to container at last step"""
    cur = state
    for step in path[:-1]:
        cur = _get(cur, step)
    return cur, path[-1]


def _get(cur, step):
    if step[0] in ("k", "i"):
        return cur[step[1]]
    if step[0] == "o":
        return vars(cur)
    raise ParUnsafe(f"path step {step!r}")


def apply(state, per_type_ops):
    """parent: apply [(type, ops)] in the given (sorted type) order; every conflict is found by plan_merge BEFORE anything is applied"""
    _apply_planned(state, per_type_ops, plan_merge(per_type_ops))


def plan_merge(per_type_ops):
    """the checks of apply(), without a state (also run offline on kept worker results: OT_BIND_EMIT_PAR_KEEP):
    one path set by several types must merge (merge_set); an op of one type under / over a path another type set is a
    cross-type dependency.  -> ParUnsafe, state untouched."""
    sets, owners, under = {}, {}, {}
    for tn, ops in per_type_ops:
        for op, path, val in ops:
            if op != "set":
                continue
            if path in sets:
                sets[path] = merge_set(sets[path], val, path)
            else:
                sets[path] = val
            owners.setdefault(path, set()).add(tn)
            for n in range(1, len(path)):
                under.setdefault(path[:n], set()).add(tn)
    adders = {}
    for tn, ops in per_type_ops:
        for op, path, val in ops:
            if op == "add":
                adders.setdefault(path, set()).add(tn)
    for path, who in adders.items():
        if len(who) > 1 and not _is_counter(path):
            raise ParUnsafe(f"{_p(path)}: a number changed by {len(who)} types ({sorted(who)[0]}, ..) and not named as a counter")
    for tn, ops in per_type_ops:
        for op, path, val in ops:
            for n in range(1, len(path) + (0 if op == "set" else 1)):
                o = owners.get(path[:n])
                if o and o != {tn}:
                    raise ParUnsafe(f"{_p(path)}: changed by {tn} under {_p(path[:n])}, which {sorted(o - {tn})[0]} set")
            if op == "set" and (under.get(path) or {tn}) != {tn}:
                raise ParUnsafe(f"{_p(path)}: set by {tn}, changed inside by {sorted(under[path] - {tn})[0]}")
    return sets


def _apply_planned(state, per_type_ops, sets):
    did, done_sets = set(), set()                # one list / set reached by two attribute paths (an alias) is extended once per type
    for tn, ops in per_type_ops:
        for op, path, val in ops:
            try:
                cont, last = _resolve(state, path)
                if op == "set":
                    if path in done_sets:
                        continue
                    done_sets.add(path)
                    if last[0] == "o":
                        raise ParUnsafe(f"{_p(path)}: object replaced")
                    cont[last[1]] = sets[path]
                    continue
                if op == "add":
                    if (tn, id(cont), last, op) in did:
                        continue
                    did.add((tn, id(cont), last, op))
                    if last[0] == "o":
                        raise ParUnsafe(f"{_p(path)}: object replaced")
                    cont[last[1]] = cont[last[1]] + val
                    continue
                tgt = _get(cont, last)
                if (tn, id(tgt), op) in did:
                    continue
                did.add((tn, id(tgt), op))
                if op == "extend":
                    tgt.extend(val)
                elif op == "union":
                    tgt |= val
                else:
                    raise ParUnsafe(f"op {op!r}")
            except (KeyError, IndexError, TypeError) as e:
                raise ParUnsafe(f"{_p(path)}: cannot apply {op} from {tn}: {e!r}") from e


# ---- workers --------------------------------------------------------------------------------------------------------------------
def _private_mb():
    try:
        for ln in open("/proc/self/smaps_rollup"):
            if ln.startswith("Private_Dirty:"):
                return int(ln.split()[1]) // 1024
    except OSError:
        pass
    return None


def _child(B, tn, ps, out, res_path, log_path):
    rc = 0
    try:
        fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        sys.stdout = os.fdopen(1, "w", closefd=False)    # whatever the parent had installed (a capture, a tee): the worker logs to its file
        sys.stderr = os.fdopen(2, "w", closefd=False)
        t0 = time.time()
        snap = snapshot(B.__dict__, seen={id(B)})
        t_snap = time.time() - t0
        files, exc = [], None
        try:
            B._emit_one(tn, ps, out, files)
        except Exception as e:                   # a BindError stops the serial loop too: the parent re-raises it in type order
            exc = e
            tb = traceback.format_exc()
        t1 = time.time()
        rec = dict(type=tn, wall_s=round(t1 - t0, 2), snap_s=round(t_snap, 2))
        kd = kinds(snap)
        try:
            ops = delta(snap, B.__dict__)
            res = dict(ops=ops, files=[str(f) for f in files])
        except ParUnsafe as e:
            res = dict(unsafe=str(e))
        if exc is not None:
            try:
                pickle.dumps(exc)
                res["exc"] = exc
            except Exception:
                res["exc_text"] = tb
        rec["delta_s"] = round(time.time() - t1, 2)
        rec["private_mb"] = _private_mb()
        rec["shallow"] = sorted(k for k, v in kd.items() if v == "shallow")
        res["rec"] = rec
        sys.stdout.flush()
        sys.stderr.flush()
        try:
            blob = pickle.dumps(res, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            blob = pickle.dumps(dict(unsafe=f"{tn}: the state delta does not pickle ({e!r})", rec=rec))
        tmp = res_path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, res_path)
    except BaseException:
        rc = 1
        try:
            traceback.print_exc()
            sys.stderr.flush()
        except Exception:
            pass
    finally:
        os._exit(rc)


def weight(B, tn, ps):
    """a rough per-type cost for largest-first scheduling (only order, never results, depends on it)"""
    try:
        m = getattr(B, "members", {}).get(ps[0])
        return len(m) if m is not None else 0
    except Exception:
        return 0


def run(B, out, files, j, rec_path=None):
    t0 = time.time()
    try:
        return _run(B, out, files, j, rec_path)
    except ParUnsafe as e:
        raise ParUnsafe(f"{e} (parallel attempt cost {time.time() - t0:.0f} s)") from e


def _run(B, out, files, j, rec_path=None):
    """Emit every type of B.by_type with j forked workers; on return B and `files` are as after the serial loop.
    Raises ParUnsafe (B untouched, files untouched; type files on disk are rewritten by the serial rerun) or the first type's
    own exception in sorted type order, like the serial loop."""
    import gc
    from pathlib import Path
    order = sorted(B.by_type.items())
    if j <= 1 or len(order) <= 1 or not hasattr(os, "fork"):
        raise ParUnsafe("nothing to parallelise")
    t0 = time.time()
    keep = os.environ.get("OT_BIND_EMIT_PAR_KEEP")       # diagnosis: keep every worker's result (<i>.res pickles) in this directory
    if keep:
        os.makedirs(keep, exist_ok=True)
    work = keep or tempfile.mkdtemp(prefix="bind_emit_par_", dir=os.environ.get("TMPDIR") or None)
    todo = sorted(order, key=lambda kv: -weight(B, kv[0], kv[1]))
    live, done = {}, {}
    sys.stdout.flush()
    sys.stderr.flush()
    gc.collect()
    if hasattr(gc, "freeze"):
        gc.freeze()                              # keep the children's GC from dirtying (copying) the parent's pages
    try:
        while todo or live:
            while todo and len(live) < j:
                tn, ps = todo.pop(0)
                i = [k for k, _ in order].index(tn)
                rp, lp = os.path.join(work, f"{i}.res"), os.path.join(work, f"{i}.log")
                pid = os.fork()
                if pid == 0:
                    _child(B, tn, ps, out, rp, lp)
                live[pid] = (tn, rp, lp)
            # The bind also owns a concurrent plan-gate child. Collect only
            # workers so the gate's caller can still join its own status.
            for pid in live:
                ready, st = os.waitpid(pid, os.WNOHANG)
                if ready:
                    break
            else:
                time.sleep(0.02)
                continue
            tn, rp, lp = live.pop(pid)
            done[tn] = (st, rp, lp)
    finally:
        if hasattr(gc, "unfreeze"):
            gc.unfreeze()
        for pid in list(live):                   # an exception in the parent: do not leave workers behind
            try:
                os.kill(pid, 15)
                os.waitpid(pid, 0)
            except OSError:
                pass
    results, recs = [], []
    for tn, _ in order:
        st, rp, lp = done[tn]
        try:
            log = open(lp, errors="replace").read()
        except OSError:
            log = ""
        if st != 0 or not os.path.isfile(rp):
            _cleanup(work)
            raise ParUnsafe(f"worker of type {tn} died (wait status {st}): {log[-400:]}")
        with open(rp, "rb") as f:
            res = pickle.load(f)
        if "unsafe" in res:
            _cleanup(work)
            raise ParUnsafe(f"{tn}: {res['unsafe']}")
        results.append((tn, res, log))
        recs.append(res["rec"])
    _cleanup(work)
    # everything read: apply in sorted type order up to (and including the state of) the first failing type, like the serial loop
    upto, err = [], None
    for tn, res, log in results:
        upto.append((tn, res["ops"]))
        if "exc" in res or "exc_text" in res:
            err = (tn, res)
            break
    apply(B.__dict__, upto)
    for tn, res, log in results[:len(upto)]:
        if log:
            sys.stdout.write(log if log.endswith("\n") else log + "\n")
        files.extend(Path(f) for f in res["files"])
    sys.stdout.flush()
    rec = dict(schema="opentallas.bind_emit_par.v1", jobs=j, types=len(order), wall_s=round(time.time() - t0, 1),
               serial_sum_s=round(sum(r["wall_s"] for r in recs), 1), max_private_mb=max([r.get("private_mb") or 0 for r in recs] or [0]),
               shallow_attrs=sorted({k for r in recs for k in r.pop("shallow", [])}),
               per_type=sorted(recs, key=lambda r: -r["wall_s"]))
    print(f"bind: emit parallel j={j}: {len(order)} types in {rec['wall_s']} s (sum of type walls {rec['serial_sum_s']} s, "
          f"max worker private {rec['max_private_mb']} MB)", flush=True)
    try:
        p = rec_path or os.environ.get("OT_BIND_EMIT_PAR_REC") or str(Path(out).parent / "bind_emit_par.json")
        Path(p).write_text(json.dumps(rec, indent=1) + "\n")
    except OSError:
        pass
    if err is not None:
        tn, res = err
        if "exc" in res:
            raise res["exc"]
        raise RuntimeError(f"emit of type {tn} failed in its worker:\n{res['exc_text']}")
    return rec


def _cleanup(work):
    if os.environ.get("OT_BIND_EMIT_PAR_KEEP"):
        return
    try:
        for f in os.listdir(work):
            os.unlink(os.path.join(work, f))
        os.rmdir(work)
    except OSError:
        pass
