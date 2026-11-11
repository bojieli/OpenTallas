#!/usr/bin/env python3
"""kit_store: self-contained kit inputs backed by a per-host content-addressed dedupe store (KIT-INPUT-STORE-1, 2026-11-10).

Problem: kit-wave kits read their inputs (plan json, strict-bind output, the RTL files the bind lists, kit_rtl recipe
script, asbuilt, sidecars) from lane worktrees on scratch.  Cleanup and lane churn delete those paths, so a relaunch fails
at kit_rtl / FileNotFoundError (KV kv3_pv x6, S81 leaf t42, HEAD hd_ctl, 100 S81 types on a stale bind8, 11-10).

Design (COORD amendment 11-10):
  1. The KIT is self-contained.  At kit generation `snapshot` hardlinks every input file the kit reads into
     <W>/kit_inputs/<original absolute path> and the wave passes those kit-local paths to bind / kit-rtl / gen; after
     kit-rtl, `localize-filelist` pulls every source kit_rtl.f names from outside the kit into kit_inputs as well.
     Text recipes that name other inputs by absolute path (bind.f, *.sh) are rewritten in the kit copy to the kit-local
     paths; identity-bearing json (plan, asbuilt, sidecars) is never rewritten (byte-identical, same sha).
  2. The STORE is only the dedupe source of those hardlinks: <scratch root>/kit-store/blobs/<sha[:2]>/<sha256>, one
     read-only (0444) inode per content sha per host and filesystem.  Kits never name a store path.  A path index
     (kit-store/paths/) remembers which sha each original path had, so a relaunch whose original was pruned is rebuilt
     from the store ("restored"), never from a guess.
  3. Sparse: only files kits read (plan, bind output dir, bind.f RTL files, kit_rtl script and the files it names,
     asbuilt and the files it names, sidecars).  Never a full repo worktree: the wave src checkout is rebuildable from
     its git sha, which the manifest records together with the bind recipe (amendment 4: hosts are volatile).
  4. Retention is a referenced-set rule (`gc`, called by ot-autoclean): a blob is kept while any kit hardlinks it
     (st_nlink > 1: live kits, counted records, archived units) or a launch manifest of the last 14 days names its
     sha, or an extra referenced-sha list names it; otherwise it is deleted.  No heuristics, dry run unless --apply.

Stdlib only; the wave runs it on a gen host as `python3 - <args> <<EOF <this file> EOF` (no repo checkout needed).
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import stat
import sys
import time

SCHEMA = "opentallas.kit_inputs.v1"
STORE_DIR = "kit-store"
KEEP_DAYS = 14
SCAN_PREFIX = "/srv/opentallas-scratch"            # deep references are scratch paths only (tests point it elsewhere)


def abs_re():
    return re.compile(r"(?:^|(?<=[\s=,:'\"+]))(" + re.escape(SCAN_PREFIX) + r"[^\s\"',;:=()$`<>|&]*)")
RECIPE_SUFFIX = (".sh", ".f")                       # rewritten in the kit copy (path lists / recipes, no identity sha)
SCAN_SUFFIX = (".sh", ".f", ".json", ".tcl", ".mk")  # scanned for further inputs (deep references)
SCAN_MAX_BYTES = 64 << 20
DEEP_FILE_MAX_BYTES = 4 << 30
DATA_FILE_MAX_BYTES = 512 << 20                     # a file a data json names (views, sidecars): larger = not a kit input
SCRATCH_FLOOR_GB = 50                               # never copy into a store fs below this (gen_disk_min_gb is 70)
DIR_MAX_FILES = 20000                               # a referenced directory bigger than this is a tree, not a kit input
MIN_LANE_DEPTH = 5                                  # /srv/<scratch>/claude/<lane>/<x>: never a lane root or claude/
ROOT_FLOOR_GB = 150


class StoreError(Exception):
    pass


def jload(p):
    with open(p) as f:
        return json.load(f)


def now_s():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def store_root_for(path):
    """the store of the filesystem a kit dir lives on: /srv/opentallas-scratchN/kit-store (hardlinks need one fs)"""
    p = os.path.realpath(path).split("/")
    if len(p) > 2 and p[1] == "srv" and p[2].startswith("opentallas-scratch"):
        return f"/srv/{p[2]}/{STORE_DIR}"
    return os.path.join(os.path.expanduser("~"), "scratch-root", STORE_DIR)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


class Store:
    def __init__(self, root):
        self.root = root
        for d in ("blobs", "paths", "manifests", "index", "tmp"):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        self.db = sqlite3.connect(os.path.join(root, "index", "ino.sqlite"), timeout=600)
        self.db.execute("create table if not exists ino (dev int, ino int, size int, mtime int, sha text, "
                        "primary key (dev, ino, size, mtime))")
        self.dev = os.stat(os.path.join(root, "blobs")).st_dev
        self.bytes_copied = 0
        self.files_new = 0

    def blob(self, sha):
        return os.path.join(self.root, "blobs", sha[:2], sha)

    def file_sha(self, path, st):
        k = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
        r = self.db.execute("select sha from ino where dev=? and ino=? and size=? and mtime=?", k).fetchone()
        if r:
            return r[0]
        sha = sha256_file(path)
        self.db.execute("insert or replace into ino values (?,?,?,?,?)", k + (sha,))
        return sha

    def ingest(self, path):
        """content of path -> blob (hardlink when same fs and already read-only, else copy) -> sha"""
        st = os.stat(path)
        sha = self.file_sha(path, st)
        b = self.blob(sha)
        if os.path.exists(b):
            return sha, st.st_size
        os.makedirs(os.path.dirname(b), exist_ok=True)
        tmp = os.path.join(self.root, "tmp", f"{sha}.{os.getpid()}")
        linked = False
        if st.st_dev == self.dev and not (st.st_mode & 0o222):
            try:
                os.link(path, tmp)
                linked = True
            except OSError:
                linked = False
        if not linked:
            shutil.copyfile(path, tmp)
            if sha256_file(tmp) != sha:
                os.unlink(tmp)
                raise StoreError(f"content changed while copying {path}")
            os.chmod(tmp, 0o444)
            self.bytes_copied += st.st_size
            ts = os.stat(tmp)
            self.db.execute("insert or replace into ino values (?,?,?,?,?)",
                            (ts.st_dev, ts.st_ino, ts.st_size, ts.st_mtime_ns, sha))
        try:
            os.rename(tmp, b) if not os.path.exists(b) else os.unlink(tmp)
        except OSError:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self.files_new += 1
        return sha, st.st_size

    def linkable(self, path):
        """a source the store can hardlink (no bytes): same fs, already read-only"""
        st = os.stat(path)
        return st.st_dev == self.dev and not (st.st_mode & 0o222)

    def put_bytes(self, data):
        sha = hashlib.sha256(data).hexdigest()
        b = self.blob(sha)
        if not os.path.exists(b):
            os.makedirs(os.path.dirname(b), exist_ok=True)
            tmp = os.path.join(self.root, "tmp", f"{sha}.{os.getpid()}")
            with open(tmp, "wb") as f:
                f.write(data)
            os.chmod(tmp, 0o444)
            os.rename(tmp, b)
            self.bytes_copied += len(data)
        return sha

    # path index: the sha every original path had when a kit last read it (restore source after a prune)
    def _pidx(self, path):
        h = hashlib.sha1(path.encode()).hexdigest()
        return os.path.join(self.root, "paths", h[:2], h + ".json")

    def remember(self, path, kind, files):
        p = self._pidx(path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        old = {}
        try:
            old = jload(p)
        except (OSError, ValueError):
            pass
        hist = [h for h in old.get("history", []) if h.get("files") != files][-9:]
        doc = {"path": path, "kind": kind, "files": files, "t": now_s(), "history": hist + [{"files": files, "t": now_s()}]}
        tmp = p + f".{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump(doc, f)
        os.replace(tmp, p)

    def recall(self, path):
        """-> (kind, {rel: sha}) of a path the store saw, only when every blob is still present"""
        try:
            doc = jload(self._pidx(path))
        except (OSError, ValueError):
            return None
        if all(os.path.exists(self.blob(s)) for s in doc["files"].values()):
            return doc["kind"], doc["files"]
        return None

    def commit(self):
        self.db.commit()
        self.db.close()


def link_into(store, sha, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.lexists(dest):
        os.unlink(dest)
    try:
        os.link(store.blob(sha), dest)
    except OSError:                                   # another fs: a copy (kit stays self-contained)
        shutil.copyfile(store.blob(sha), dest)
        os.chmod(dest, 0o444)


def dir_files(d, cap=DIR_MAX_FILES, recursive=True, subdirs=()):
    """{rel: path} of the regular files below d (links followed); recursive False = d's own files + the named subdirs"""
    out = {}
    for dp, dns, fns in os.walk(d, followlinks=True):
        dns.sort()
        if not recursive:
            rel = os.path.relpath(dp, d)
            if rel != "." and rel.split("/")[0] not in subdirs:
                dns[:] = []
                continue
            if rel == ".":
                dns[:] = [x for x in dns if x in subdirs]
        for n in sorted(fns):
            p = os.path.join(dp, n)
            if os.path.isfile(p):
                out[os.path.relpath(p, d)] = p
            if cap and len(out) > cap:
                raise StoreError(f"{d}: more than {DIR_MAX_FILES} files (a tree, not a kit input)")
    return out


def scan_refs(path):
    """absolute scratch paths a recipe / json names"""
    try:
        if os.path.getsize(path) > SCAN_MAX_BYTES:
            return []
        with open(path, errors="replace") as f:
            txt = f.read()
    except OSError:
        return []
    if path.endswith(".f"):
        return [ln.strip() for ln in txt.splitlines() if ln.strip().startswith(SCAN_PREFIX)]
    return [m.rstrip(".") for m in abs_re().findall(txt)]


def lane_depth_ok(p):
    return len([x for x in p.split("/") if x]) >= MIN_LANE_DEPTH


def free_gb(path):
    s = os.statvfs(path)
    return s.f_bavail * s.f_frsize / 1e9


def snapshot(spec, kit_inputs, store_root=None, depth=2, log=print):
    """spec: {inputs: [{role, path, kind: file|dir, required: bool, deep: bool}], rebuild: {...}, meta: {...}}
    -> manifest {map: {orig: local}, files: {orig_file: sha}, restored, absent, ...}; writes <kit_inputs>/MANIFEST.json"""
    store = Store(store_root or store_root_for(kit_inputs))
    os.makedirs(kit_inputs, exist_ok=True)
    files, mp, restored, absent, roles = {}, {}, [], [], {}
    seen = set()
    queue = [(dict(x), 0) for x in spec.get("inputs") or []]
    # floor guard: copies (writable or foreign-fs sources) count against the host root floor when the store is on '/'
    root_dev = os.stat("/").st_dev
    on_root = os.stat(store.root).st_dev == root_dev
    while queue:
        inp, lvl = queue.pop(0)
        p = os.path.normpath(inp["path"])
        if p in seen:
            continue
        seen.add(p)
        local = kit_inputs.rstrip("/") + p
        kind = inp.get("kind") or ("dir" if os.path.isdir(p) else "file")
        got = {}
        if os.path.exists(p):
            if os.path.isdir(p):
                kind = "dir"
                if inp.get("files_only"):
                    absent.append({"path": p, "role": inp.get("role"), "why": "directory named by data json: not copied"})
                    continue
                if not inp.get("required") and (not lane_depth_ok(p)):
                    absent.append({"path": p, "role": inp.get("role"), "why": "directory above lane sub-dir level: not a kit input"})
                    continue
                try:
                    lst = dir_files(p, cap=0 if inp.get("required") else DIR_MAX_FILES,
                                    recursive=not inp.get("flat"), subdirs=tuple(inp.get("subdirs") or ()))
                except StoreError as e:
                    if inp.get("required"):
                        raise
                    absent.append({"path": p, "role": inp.get("role"), "why": str(e)})
                    continue
            else:
                kind = "file"
                cap = DATA_FILE_MAX_BYTES if inp.get("files_only") else DEEP_FILE_MAX_BYTES
                if not inp.get("required") and os.path.getsize(p) > cap:
                    absent.append({"path": p, "role": inp.get("role"), "why": "file over the deep-input size cap"})
                    continue
                lst = {"": p}
            floor = ROOT_FLOOR_GB if on_root else SCRATCH_FLOOR_GB
            need = sum(os.path.getsize(f) for f in lst.values() if not store.linkable(f)) / 1e9
            if need and free_gb(store.root) - need < floor:
                raise StoreError(f"store floor {floor} GB on {store.root}: copying {need:.1f} GB for {p} would cross it")
            for rel, f in lst.items():
                got[rel] = store.ingest(f)[0]
            store.remember(p, kind, got)
        else:
            rec = store.recall(p)
            if rec is None:
                if inp.get("required"):
                    raise StoreError(f"KIT-STORE MISSING {inp.get('role')} {p}: absent on {socket.gethostname()} and "
                                     "never stored here (rebuild from the manifest's git sha + bind recipe)")
                absent.append({"path": p, "role": inp.get("role"), "why": "absent, not in store"})
                continue
            kind, got = rec
            restored.append(p)
            log(f"KIT-STORE RESTORED {p} ({len(got)} files) from {store.root}")
        for rel, sha in got.items():
            dest = os.path.join(local, rel) if rel else local
            link_into(store, sha, dest)
            files[os.path.join(p, rel) if rel else p] = sha
        if not inp.get("flat"):
            mp[p] = local                             # a flat (partial) neighbour dir is not a path prefix to rewrite
        if kind == "file" and inp.get("siblings") is not None and lane_depth_ok(os.path.dirname(p)):
            # plan / asbuilt neighbours read by relative path (gen die_io.json, bind r8/ landings, die_plan.json, views)
            pd = os.path.dirname(p)
            queue.insert(0, ({"role": (inp.get("role") or "") + "_dir", "path": pd, "kind": "dir", "required": False,
                              "deep": False, "flat": True, "subdirs": list(inp.get("siblings") or [])}, lvl))
        roles.setdefault(inp.get("role") or "deep", []).append(p)
        if inp.get("deep", True) and lvl < depth:
            scan = [local + ("/" + r if r else "") for r in got if (r or local).endswith(SCAN_SUFFIX)] \
                if kind == "dir" else ([local] if local.endswith(SCAN_SUFFIX) else [])
            for s in scan:
                if kind == "dir" and not s.endswith(("bind.f",)) and not s.endswith(".sh"):
                    continue                          # inside a bind dir: only its file list names further inputs
                files_only = s.endswith((".json", ".tcl", ".mk"))   # data names files; recipes may name dirs
                for r in scan_refs(s):
                    r = os.path.normpath(r)
                    if r not in seen and not any(r.startswith(m + "/") for m in mp):
                        queue.append(({"role": "deep", "path": r, "required": False, "deep": True,
                                       "files_only": files_only}, lvl + 1))
    # rewrite recipes (file lists, scripts) in the kit copy to kit-local paths; json keeps its bytes
    keys = sorted(mp, key=len, reverse=True)
    rewritten = {}
    for orig, sha in sorted(files.items()):
        if not orig.endswith(RECIPE_SUFFIX) or not keys:
            continue
        local = kit_inputs.rstrip("/") + orig
        with open(store.blob(sha), "rb") as f:
            data = f.read()
        if len(data) > SCAN_MAX_BYTES:
            continue
        txt = data.decode("utf-8", errors="surrogateescape")
        # only whole path prefixes: the match must end at a path boundary
        new = re.sub("(" + "|".join(re.escape(k) for k in keys) + r")(?=[/\s\"',;:=()$`<>|&]|$)",
                     lambda m: mp[m.group(1)], txt)
        if new != txt:
            nsha = store.put_bytes(new.encode("utf-8", errors="surrogateescape"))
            link_into(store, nsha, local)
            rewritten[orig] = {"sha": sha, "kit_sha": nsha}
    store.commit()
    man = {"schema": SCHEMA, "t": now_s(), "host": socket.gethostname(), "store": store.root, "kit_inputs": kit_inputs,
           "map": mp, "roles": roles, "files": files, "rewritten": rewritten, "restored": restored, "absent": absent,
           "bytes_copied": store.bytes_copied, "blobs_new": store.files_new,
           "rebuild": spec.get("rebuild") or {}, "meta": spec.get("meta") or {}}
    write_manifest(store, kit_inputs, man)
    return man


def write_manifest(store, kit_inputs, man):
    body = json.dumps(man, indent=1, sort_keys=True)
    with open(os.path.join(kit_inputs, "MANIFEST.json"), "w") as f:
        f.write(body)
    tag = re.sub(r"[^A-Za-z0-9_.-]", "_", "-".join(str(man.get("meta", {}).get(k, "")) for k in ("die", "item", "attempt")))
    name = f"{time.strftime('%Y%m%dT%H%M%S')}-{tag}-{hashlib.sha1(kit_inputs.encode()).hexdigest()[:8]}.json"
    with open(os.path.join(store.root, "manifests", name), "w") as f:
        f.write(json.dumps({"kit_inputs": kit_inputs, "t": man["t"], "meta": man.get("meta"),
                            "shas": sorted(set(man["files"].values()) | {r["kit_sha"] for r in man["rewritten"].values()})}))


def localize_filelist(flist, kit_root, kit_inputs, store_root=None):
    """every absolute source a kit filelist (kit_rtl.f) names outside kit_root -> kit_inputs (same store rules); the
    list is rewritten in place to the kit-local paths.  -> {n_local, n_moved, missing}"""
    store = Store(store_root or store_root_for(kit_inputs))
    kr = os.path.realpath(kit_root).rstrip("/") + "/"
    out, moved, missing = [], 0, []
    with open(flist) as f:
        lines = f.read().splitlines()
    for ln in lines:
        s = ln.strip()
        pre = ""
        for p in ("+incdir+", "-v ", "-y "):
            if s.startswith(p):
                pre, s = p, s[len(p):].strip()
        if not s.startswith("/") or os.path.realpath(s).startswith(kr) or s.startswith(kit_inputs.rstrip("/") + "/"):
            out.append(ln)
            continue
        if not os.path.exists(s):
            rec = store.recall(s)
            if rec is None:
                missing.append(s)
                out.append(ln)
                continue
            kind, got = rec
        elif os.path.isdir(s):
            kind, got = "dir", {r: store.ingest(f)[0] for r, f in dir_files(s).items()}
            store.remember(s, kind, got)
        else:
            kind, got = "file", {"": store.ingest(s)[0]}
            store.remember(s, kind, got)
        local = kit_inputs.rstrip("/") + s
        for rel, sha in got.items():
            link_into(store, sha, os.path.join(local, rel) if rel else local)
        out.append(pre + local)
        moved += 1
    store.commit()
    if moved:
        tmp = flist + ".kit_store.tmp"
        with open(tmp, "w") as f:
            f.write("\n".join(out) + "\n")
        os.replace(tmp, flist)
        with open(flist + ".orig_paths", "w") as f:
            f.write("\n".join(lines) + "\n")
    return {"n_lines": len(lines), "n_moved": moved, "missing": missing}


def referenced(store_root, extra=(), keep_days=KEEP_DAYS, now=None):
    """shas a launch manifest of the last keep_days names, plus extra (counted-record / live-row lists)"""
    now = now or time.time()
    keep = set(extra)
    md = os.path.join(store_root, "manifests")
    for n in os.listdir(md) if os.path.isdir(md) else []:
        p = os.path.join(md, n)
        try:
            if now - os.path.getmtime(p) > keep_days * 86400:
                continue
            keep.update(jload(p).get("shas") or [])
        except (OSError, ValueError):
            # an unreadable manifest of the window could name anything: refuse to collect
            raise StoreError(f"unreadable manifest {p}: gc refuses (referenced set unknown)")
    return keep


def gc(store_root, extra=(), keep_days=KEEP_DAYS, apply=False, now=None, log=print):
    """referenced-set rule only: delete a blob iff no kit hardlinks it (st_nlink == 1) AND no manifest of the window /
    extra list names its sha.  Expired manifests (older than the window) are deleted with --apply.  -> summary"""
    keep = referenced(store_root, extra, keep_days, now)
    now = now or time.time()
    out = {"store": store_root, "keep_shas": len(keep), "delete": 0, "delete_bytes": 0, "kept_linked": 0,
           "kept_manifest": 0, "apply": apply, "manifests_expired": 0}
    bd = os.path.join(store_root, "blobs")
    for sub in sorted(os.listdir(bd)) if os.path.isdir(bd) else []:
        for n in sorted(os.listdir(os.path.join(bd, sub))):
            p = os.path.join(bd, sub, n)
            st = os.lstat(p)
            if st.st_nlink > 1:
                out["kept_linked"] += 1
                continue
            if n in keep:
                out["kept_manifest"] += 1
                continue
            out["delete"] += 1
            out["delete_bytes"] += st.st_size
            if apply:
                os.unlink(p)
                log(f"KIT-STORE GC deleted {p} ({st.st_size} B): no kit link, no manifest within {keep_days} d")
    md = os.path.join(store_root, "manifests")
    for n in os.listdir(md) if os.path.isdir(md) else []:
        p = os.path.join(md, n)
        if now - os.path.getmtime(p) > keep_days * 86400:
            out["manifests_expired"] += 1
            if apply:
                os.unlink(p)
    return out


def du(store_root):
    """bytes of the store: total, and store-only (no kit or source links the inode: the bytes the store alone holds,
    which count against the host floor)"""
    tot = only = n = n_only = 0
    bd = os.path.join(store_root, "blobs")
    for dp, _, fns in os.walk(bd):
        for f in fns:
            st = os.lstat(os.path.join(dp, f))
            n += 1
            tot += st.st_size
            if st.st_nlink == 1:
                n_only += 1
                only += st.st_blocks * 512
    return {"store": store_root, "host": socket.gethostname(), "blobs": n, "bytes": tot, "store_only_blobs": n_only,
            "store_only_bytes": only}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("snapshot")
    s.add_argument("--spec-b64", required=True)
    s.add_argument("--kit-inputs", required=True)
    s.add_argument("--store-root")
    s = sp.add_parser("localize-filelist")
    s.add_argument("flist")
    s.add_argument("--kit-root", required=True)
    s.add_argument("--kit-inputs", required=True)
    s.add_argument("--store-root")
    s = sp.add_parser("ingest", help="migration: store paths now (one manifest), so a later prune can be restored")
    s.add_argument("paths", nargs="+")
    s.add_argument("--kit-inputs", required=True, help="a self-contained copy dir (hardlinks) holding the snapshot")
    s.add_argument("--tag", default="migrate")
    s.add_argument("--store-root")
    s = sp.add_parser("gc")
    s.add_argument("--store-root", required=True)
    s.add_argument("--referenced", action="append", default=[], help="file of extra referenced shas (one per line)")
    s.add_argument("--keep-days", type=float, default=KEEP_DAYS)
    s.add_argument("--apply", action="store_true")
    s = sp.add_parser("du")
    s.add_argument("--store-root", nargs="+", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "snapshot":
            spec = json.loads(base64.b64decode(a.spec_b64))
            man = snapshot(spec, a.kit_inputs, a.store_root)
            print("KW_KIT_STORE " + json.dumps({k: man[k] for k in ("map", "restored", "absent", "bytes_copied",
                                                                     "blobs_new", "store")}
                                               | {"n_files": len(man["files"]), "rewritten": sorted(man["rewritten"])}))
        elif a.cmd == "localize-filelist":
            print("KW_KIT_STORE_FL " + json.dumps(localize_filelist(a.flist, a.kit_root, a.kit_inputs, a.store_root)))
        elif a.cmd == "ingest":
            spec = {"inputs": [{"role": "migrate", "path": p, "required": True, "deep": True} for p in a.paths],
                    "meta": {"die": a.tag, "item": "migrate", "attempt": 0}}
            man = snapshot(spec, a.kit_inputs, a.store_root)
            print("KW_KIT_STORE " + json.dumps({"n_files": len(man["files"]), "bytes_copied": man["bytes_copied"],
                                                "blobs_new": man["blobs_new"], "absent": man["absent"][:20],
                                                "n_absent": len(man["absent"]), "restored": man["restored"],
                                                "store": man["store"]}))
        elif a.cmd == "gc":
            extra = set()
            for f in a.referenced:
                extra.update(x.strip() for x in open(f) if re.fullmatch(r"[0-9a-f]{64}", x.strip()))
            print("KW_KIT_STORE_GC " + json.dumps(gc(a.store_root, extra, a.keep_days, a.apply)))
        elif a.cmd == "du":
            for r in a.store_root:
                if os.path.isdir(r):
                    print("KW_KIT_STORE_DU " + json.dumps(du(r)))
    except StoreError as e:
        print(f"KIT-STORE FAIL {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
