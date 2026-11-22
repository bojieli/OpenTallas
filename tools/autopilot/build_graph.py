#!/usr/bin/env python3
"""build_graph: content-hash stamps and staleness for derived build artefacts (FABLE-PIPELINE-R1, OWNER 11-21).

About two thirds of the sign-off failures of 11-21 were procedural: a derived artefact (bind, R8 landing table, kit topology, runtime
pin, clock-tap grid) was older than the input it was made from, and nothing said so until a multi-hour stage refused it.  This module is
the one rule that replaces the hand-run refreshes:

    every derived artefact carries a STAMP = the content hash of every input it was made from;
    an artefact is FRESH only when its stamp equals the hash of the inputs as they are NOW (and every artefact it depends on is fresh);
    a build runs exactly the stale nodes, in dependency order, and each stale node says WHICH input changed.

    Node(name, inputs=[Input...], deps=[names], run=callable, out=dir, cost="fast"|"slow")
    Input.file(label, path) | Input.files(label, paths, root=) | Input.tree(label, dir, globs=) | Input.value(label, obj) | Input.env(label, keys)
    status(node, nodes) -> Status(fresh, why[])          plan(nodes, goal) -> [(node, Status)] in run order
    build(nodes, goal, dry=False) -> 0 ok | 1 a node failed | 3 dry run found stale nodes

The stamp is <out>/.ot-build/<name>.stamp.json, written tmp + rename only after run() returned 0, so a killed run leaves the node stale.
Hashes are of CONTENT (sha256); mtimes only key the per-user accelerator cache (OT_BUILD_HASH_CACHE=off disables it).  A sealed source
tree (.src-manifest.sha256 of tools/autopilot/src_manifest.py) hashes as its seal.  No network, no git; pure functions + small files."""
import fnmatch
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SCHEMA = "opentallas.build_stamp.v1"
STAMP_DIR = ".ot-build"
MISSING = "MISSING"


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_obj(obj):
    """canonical JSON hash: key order and whitespace never make an artefact stale"""
    return sha_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode())


# ---- file hashing with an mtime-keyed accelerator -------------------------------------------------------------------------------
_CACHE = None
_CACHE_DIRTY = False


def _cache_path():
    v = os.environ.get("OT_BUILD_HASH_CACHE", "")
    if v == "off":
        return None
    return Path(v) if v else Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "ot-build" / "hash_cache.json"


def _cache():
    global _CACHE
    if _CACHE is None:
        _CACHE = {}
        p = _cache_path()
        if p is not None:
            try:
                _CACHE = json.loads(p.read_text())
            except (OSError, ValueError):
                _CACHE = {}
    return _CACHE


def flush_cache():
    global _CACHE_DIRTY
    p = _cache_path()
    if p is None or not _CACHE_DIRTY or _CACHE is None:
        return
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(_CACHE))
        os.replace(tmp, p)
        _CACHE_DIRTY = False
    except OSError:
        pass


def sha_file(path):
    """sha256 of the file content; MISSING when it does not exist.  A symlink hashes as its target's content."""
    global _CACHE_DIRTY
    p = str(path)
    try:
        st = os.stat(p)
    except OSError:
        return MISSING
    if not os.path.isfile(p):
        return MISSING
    c = _cache() if _cache_path() is not None else None
    key = os.path.realpath(p)
    sig = [st.st_size, st.st_mtime_ns, st.st_ino]
    if c is not None:
        hit = c.get(key)
        if hit and hit[0] == sig:
            return hit[1]
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    d = h.hexdigest()
    if c is not None:
        c[key] = [sig, d]
        _CACHE_DIRTY = True
    return d


def sha_json_file(path, drop=()):
    """hash of a JSON file's CONTENT (canonical form), optionally without the top-level keys in `drop`; falls back to the byte hash"""
    try:
        d = json.loads(Path(path).read_text())
    except OSError:
        return MISSING
    except ValueError:
        return sha_file(path)
    if drop and isinstance(d, dict):
        d = {k: v for k, v in d.items() if k not in drop}
    return sha_obj(d)


def tree_files(root, globs=("*",), exclude=("__pycache__/*", "*.pyc", ".ot-build/*", "*/.ot-build/*", "*/__pycache__/*")):
    root = Path(root)
    out = []
    if not root.is_dir():
        return out
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            rel = os.path.relpath(os.path.join(dp, f), root)
            if any(fnmatch.fnmatch(rel, x) for x in exclude):
                continue
            if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(f, g) for g in globs):
                out.append(rel)
    return out


def seal_of(root):
    """the seal of a sealed source tree (src_manifest.py writes <tree>/.src-manifest.sha256), else None"""
    try:
        s = (Path(root) / ".src-manifest.sha256").read_text().split()
    except OSError:
        return None
    return s[0] if s and len(s[0]) == 64 else None


def sha_tree(root, globs=("*",), use_seal=False):
    if use_seal:
        s = seal_of(root)
        if s:
            return "seal:" + s
    if not Path(root).is_dir():
        return MISSING
    return sha_obj([[rel, sha_file(Path(root) / rel)] for rel in tree_files(root, globs)])


# ---- inputs ---------------------------------------------------------------------------------------------------------------------
class Input:
    """one named input of a node.  hash() is its content hash now; detail() is a short human description for the stale message."""

    def __init__(self, label, kind, ref, **kw):
        self.label, self.kind, self.ref, self.kw = label, kind, ref, kw

    @classmethod
    def file(cls, label, path):
        return cls(label, "file", str(path))

    @classmethod
    def json(cls, label, path, drop=()):
        return cls(label, "json", str(path), drop=tuple(drop))

    @classmethod
    def files(cls, label, paths, root=None):
        return cls(label, "files", sorted(str(p) for p in paths), root=str(root) if root else None)

    @classmethod
    def tree(cls, label, root, globs=("*",), use_seal=False):
        return cls(label, "tree", str(root), globs=tuple(globs), use_seal=use_seal)

    @classmethod
    def value(cls, label, obj):
        return cls(label, "value", obj)

    @classmethod
    def env(cls, label, keys, environ=None):
        e = os.environ if environ is None else environ
        return cls(label, "value", {k: e.get(k) for k in sorted(keys) if e.get(k) is not None})

    def hash(self):
        if self.kind == "file":
            return sha_file(self.ref)
        if self.kind == "json":
            return sha_json_file(self.ref, self.kw.get("drop") or ())
        if self.kind == "files":
            root = self.kw.get("root")
            return sha_obj([[p, sha_file(os.path.join(root, p) if root else p)] for p in self.ref])
        if self.kind == "tree":
            return sha_tree(self.ref, self.kw.get("globs") or ("*",), self.kw.get("use_seal", False))
        if self.kind == "value":
            return sha_obj(self.ref)
        raise ValueError(f"input kind {self.kind!r}")

    def detail(self):
        if self.kind in ("file", "json", "tree"):
            return self.ref
        if self.kind == "files":
            return f"{len(self.ref)} files" + (f" under {self.kw['root']}" if self.kw.get("root") else "")
        s = json.dumps(self.ref, sort_keys=True, default=str)
        return s if len(s) <= 120 else s[:117] + "..."


class Node:
    def __init__(self, name, inputs=(), deps=(), run=None, out=None, cost="fast", doc=""):
        self.name, self.inputs, self.deps, self.run, self.cost, self.doc = name, list(inputs), list(deps), run, cost, doc
        self.out = Path(out) if out else None
        labels = [i.label for i in self.inputs]
        dup = sorted({x for x in labels if labels.count(x) > 1})
        if dup:
            raise ValueError(f"node {name}: duplicate input labels {dup}")

    def stamp_path(self):
        if self.out is None:
            raise ValueError(f"node {self.name}: no out directory")
        return self.out / STAMP_DIR / f"{self.name}.stamp.json"


class Status:
    def __init__(self, fresh, why, parts, key):
        self.fresh, self.why, self.parts, self.key = fresh, why, parts, key

    def __repr__(self):
        return f"Status(fresh={self.fresh}, why={self.why})"


def key_of(parts):
    return sha_obj(parts)


def read_stamp(node):
    try:
        d = json.loads(node.stamp_path().read_text())
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and d.get("schema") == SCHEMA else None


def write_stamp(node, parts, key, extra=None):
    p = node.stamp_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(schema=SCHEMA, node=node.name, key=key, parts=parts, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               host=os.uname().nodename, lane=os.environ.get("OT_LANE", ""))
    if extra:
        rec["extra"] = extra
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, p)
    return rec


def drop_stamp(node):
    try:
        node.stamp_path().unlink()
    except OSError:
        pass


def parts_now(node, dep_keys):
    parts = {i.label: i.hash() for i in node.inputs}
    for d in node.deps:
        parts["dep:" + d] = dep_keys[d]
    return parts


def diff_parts(old, new, node=None):
    """-> human lines naming every input whose hash moved (the precise stale message)"""
    det = {i.label: i.detail() for i in (node.inputs if node else [])}
    why = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if a == b:
            continue
        what = f" ({det[k]})" if k in det else ""
        if a is None:
            why.append(f"input {k}{what} is new")
        elif b is None:
            why.append(f"input {k} is no longer an input")
        elif b == MISSING:
            why.append(f"input {k}{what} is MISSING now")
        else:
            why.append(f"input {k}{what} changed {str(a)[:12]} -> {str(b)[:12]}")
    return why


def status(node, dep_status=None):
    """Status of one node given the Status of its deps ({name: Status}).  A node with a stale dep is stale; its key is then
    'pending' (the dep's new key is not known before the dep runs)."""
    dep_status = dep_status or {}
    stale_deps = [d for d in node.deps if not dep_status[d].fresh]
    if stale_deps:
        return Status(False, [f"dependency {d} is stale" for d in stale_deps], None, None)
    parts = parts_now(node, {d: dep_status[d].key for d in node.deps})
    key = key_of(parts)
    missing = [i for i in node.inputs if parts[i.label] == MISSING and not i.kw.get("optional")]
    st = read_stamp(node)
    if st is None:
        return Status(False, ["no stamp (never built here, or the last run did not finish)"], parts, key)
    if st.get("key") == key:
        return Status(True, [], parts, key)
    why = diff_parts(st.get("parts") or {}, parts, node) or ["stamp key differs"]
    if missing:
        why += [f"input {i.label} ({i.detail()}) is MISSING" for i in missing if f"input {i.label}" not in " ".join(why)]
    return Status(False, why, parts, key)


def order(nodes, goal=None):
    """topological order of the nodes `goal` needs (all nodes when goal is None); raises on a cycle or an unknown dep"""
    by = {n.name: n for n in nodes}
    if len(by) != len(nodes):
        raise ValueError("duplicate node names")
    want = [goal] if isinstance(goal, str) else list(goal or by)
    seen, out, path = set(), [], []

    def visit(name):
        if name not in by:
            raise ValueError(f"unknown node {name!r}" + (f" (dep of {path[-1]})" if path else ""))
        if name in path:
            raise ValueError("dependency cycle: " + " -> ".join(path[path.index(name):] + [name]))
        if name in seen:
            return
        path.append(name)
        for d in by[name].deps:
            visit(d)
        path.pop()
        seen.add(name)
        out.append(by[name])
    for g in want:
        visit(g)
    return out


def plan(nodes, goal=None):
    """-> [(node, Status)] in run order, statuses as of now (nothing is run)"""
    res, st = [], {}
    for n in order(nodes, goal):
        st[n.name] = status(n, st)
        res.append((n, st[n.name]))
    return res


def build(nodes, goal=None, dry=False, log=None, force=()):
    """Run exactly the stale nodes of `goal` in dependency order.  Each run(node) returns 0 / None on success (the stamp is then
    written from the inputs as hashed BEFORE the run: an input edited during the run leaves the node stale for the next build).
    -> 0 all fresh or built, 1 a node failed (later nodes not run), 3 dry run with stale nodes."""
    log = log or (lambda s: print(s, flush=True))
    st, stale_seen = {}, False
    for n in order(nodes, goal):
        s = status(n, st)
        if n.name in force and s.fresh:
            s = Status(False, ["forced"], s.parts, s.key)
        if s.fresh:
            log(f"ot-build: {n.name:10s} FRESH   {s.key[:12]}")
            st[n.name] = s
            continue
        stale_seen = True
        log(f"ot-build: {n.name:10s} STALE   " + "; ".join(s.why[:6]) + (f" (+{len(s.why) - 6} more)" if len(s.why) > 6 else ""))
        if dry:
            st[n.name] = s
            continue
        if s.parts is None:                      # a dep was stale and has now been rebuilt: hash again
            s = status(n, st)
        if n.run is None:
            log(f"ot-build: {n.name:10s} FAILED  stale and no rule to make it")
            flush_cache()
            return 1
        drop_stamp(n)
        t0 = time.time()
        try:
            rc = n.run(n) or 0
        except BuildError as e:
            log(f"ot-build: {n.name:10s} FAILED  {e}")
            flush_cache()
            return 1
        if rc != 0:
            log(f"ot-build: {n.name:10s} FAILED  rc={rc} after {time.time() - t0:.0f} s")
            flush_cache()
            return 1
        write_stamp(n, s.parts, s.key, extra=dict(wall_s=round(time.time() - t0, 1)))
        log(f"ot-build: {n.name:10s} BUILT   {s.key[:12]} in {time.time() - t0:.0f} s")
        st[n.name] = Status(True, [], s.parts, s.key)
    flush_cache()
    return 3 if (dry and stale_seen) else 0


class BuildError(Exception):
    """a node's run() refuses with a precise message (an inconsistent input); build() prints it and stops"""


if __name__ == "__main__":
    sys.exit("build_graph is a library: use tools/autopilot/ot-build")
