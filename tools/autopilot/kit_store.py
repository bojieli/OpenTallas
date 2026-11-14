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

  5. SNAPSHOT (KIT-FIX-F 11-13, wave option kit_snap): `snap` builds the same closure once per content under
     <scratch root>/kit-store/snaps/<id>/root/<original absolute path>, where <id> is the sha256 of the sorted
     (original path, content sha) list, so every item and attempt with the same inputs shares one immutable snapshot.
     A required input that is absent stops the item there, before any queue wait (KIT-STORE MISSING).  The snapshot
     moves to another host as a plain directory copy at the same absolute path; `verify` re-hashes every file against
     MANIFEST.json and only then writes .verified, the marker every reader requires.

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
TREE_MAX_BYTES = 2 << 30                            # an input's own directory is taken whole up to this size ('tree')
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


def _scan_refs_as(path, name):
    """scan_refs of the content at path, read as a file called name (the .f rule goes by the name)"""
    if path == name:
        return scan_refs(path)
    try:
        if os.path.getsize(path) > SCAN_MAX_BYTES:
            return []
        with open(path, errors="replace") as f:
            txt = f.read()
    except OSError:
        return []
    if name.endswith(".f"):
        return [ln.strip() for ln in txt.splitlines() if ln.strip().startswith(SCAN_PREFIX)]
    return [m.rstrip(".") for m in abs_re().findall(txt)]


def _small_tree(d):
    """a directory of at most DIR_MAX_FILES files and TREE_MAX_BYTES bytes"""
    n = b = 0
    for dp, _, fns in os.walk(d, followlinks=True):
        for f in fns:
            n += 1
            try:
                b += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
            if n > DIR_MAX_FILES or b > TREE_MAX_BYTES:
                return False
    return True


def lane_depth_ok(p):
    return len([x for x in p.split("/") if x]) >= MIN_LANE_DEPTH


def free_gb(path):
    s = os.statvfs(path)
    return s.f_bavail * s.f_frsize / 1e9


def snapshot(spec, kit_inputs, store_root=None, depth=2, log=print, dry=False, manifest_dir=None):
    """spec: {inputs: [{role, path, kind: file|dir, required: bool, deep: bool}], rebuild: {...}, meta: {...}}
    -> manifest {map: {orig: local}, files: {orig_file: sha}, restored, absent, ...}; writes <kit_inputs>/MANIFEST.json"""
    # dry: walk the same closure and hash it, link nothing and write nothing into kit_inputs (snap id computation)
    store = Store(store_root or store_root_for(kit_inputs))
    if not dry:
        os.makedirs(kit_inputs, exist_ok=True)
    files, mp, restored, absent, roles = {}, {}, [], [], {}
    seen = set()
    # KIT-STAGE-1 11-13 (KV kv3_pv x15 'preferred HDL source missing' 18:25): an input inside the wave's own source tree
    # (spec 'in_place' = the src root) is NOT moved into the kit.  Moved, the bind resolved the as-built's tree-relative
    # files (rtl/...) against kit_inputs/<src>, where only the plan dir was.  The src tree is the wave's pinned,
    # sha-named checkout (src_<die>_main_<sha>, kept by the kit-wave keep set); its files are recorded by content sha.
    in_place = [os.path.normpath(x).rstrip("/") for x in (spec.get("in_place") or []) if x]
    kept_in_place = {}

    def under_src(p):
        return any(p == r or p.startswith(r + "/") for r in in_place)
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
        if under_src(p):
            try:
                kept_in_place[p] = store.file_sha(p, os.stat(p)) if os.path.isfile(p) else "dir"
            except OSError:
                kept_in_place[p] = "absent"
            if inp.get("deep", True) and lvl < depth and os.path.isfile(p) and p.endswith(SCAN_SUFFIX):
                fo = p.endswith((".json", ".tcl", ".mk"))
                for r in scan_refs(p):              # a file in the tree may still name inputs outside it
                    r = os.path.normpath(r)
                    if r not in seen and not under_src(r):
                        queue.append(({"role": "deep", "path": r, "required": False, "deep": True, "files_only": fo}, lvl + 1))
            continue
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
            if dry:
                for rel, f in lst.items():
                    got[rel] = store.file_sha(f, os.stat(f))
            else:
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
            if not dry:
                link_into(store, sha, dest)
            files[os.path.join(p, rel) if rel else p] = sha
        if not inp.get("flat"):
            mp[p] = local                             # a flat (partial) neighbour dir is not a path prefix to rewrite
        if kind == "file" and inp.get("siblings") is not None and lane_depth_ok(os.path.dirname(p)):
            # plan / asbuilt neighbours read by relative path (gen die_io.json, bind r8/ landings, die_plan.json, views)
            pd = os.path.dirname(p)
            # KIT-FIX-F 11-13 ('tree', set by the wave's kit_snap): a plan / as-built outside the pinned src is read
            # together with files below its own directory by relative path (HEAD prep/native_domains, assets, published;
            # hd_spn canary: FileNotFoundError .../prep/native_domains/parent_clock_contract.json).  A bounded directory
            # moves whole; a large one (it also holds a bind output or run trees) keeps the flat rule.
            if inp.get("tree") and _small_tree(pd):
                queue.insert(0, ({"role": (inp.get("role") or "") + "_tree", "path": pd, "kind": "dir", "required": False,
                                  "deep": False}, lvl))
            else:
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
                src_s = s
                if dry:                               # nothing was linked: read the content from its blob or original
                    o = p + s[len(local):]
                    src_s = o if os.path.exists(o) else store.blob(files.get(o, ""))
                for r in _scan_refs_as(src_s, s):
                    r = os.path.normpath(r)
                    if r not in seen and not any(r.startswith(m + "/") for m in mp):
                        queue.append(({"role": "deep", "path": r, "required": False, "deep": True,
                                       "files_only": files_only}, lvl + 1))
    # rewrite recipes (file lists, scripts) in the kit copy to kit-local paths; json keeps its bytes
    keys = sorted(mp, key=len, reverse=True)
    rewritten = {}
    for orig, sha in sorted(files.items()):
        if dry or not orig.endswith(RECIPE_SUFFIX) or not keys:
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
           "in_place": kept_in_place,
           "bytes_copied": store.bytes_copied, "blobs_new": store.files_new,
           "rebuild": spec.get("rebuild") or {}, "meta": spec.get("meta") or {}}
    if not dry:
        write_manifest(store, kit_inputs, man, manifest_dir)
    return man


def write_manifest(store, kit_inputs, man, manifest_dir=None):
    body = json.dumps(man, indent=1, sort_keys=True)
    with open(os.path.join(manifest_dir or kit_inputs, "MANIFEST.json"), "w") as f:
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


SNAP_DIR = "snaps"
SNAP_SCHEMA = "opentallas.kit_snap.v1"
SNAP_KEEP_DAYS = 14


def snap_root_for(path):
    """the snapshot root of the filesystem a kit dir lives on: <scratch root>/kit-store/snaps"""
    return os.path.join(store_root_for(path), SNAP_DIR)


def snap_id(man):
    """content address of a closure: sha256 over the sorted (original path, content sha) of every file the kit reads,
    the files kept in place in the pinned source tree included.  Host, time and the snapshot's own location are not in it."""
    h = hashlib.sha256()
    for k, v in sorted((man.get("files") or {}).items()):
        h.update(f"F\t{k}\t{v}\n".encode())
    for k, v in sorted((man.get("in_place") or {}).items()):
        h.update(f"P\t{k}\t{v}\n".encode())
    return h.hexdigest()[:40]


def _touch(p):
    with open(p, "a"):
        os.utime(p, None)


VIEW_REF_MAX_BYTES = 600 << 20


def view_refs(plan_path, typ, roots, store=None):
    """KIT-FIX-F follow-up (QC slw_su_l1 canary): gen reads, for each child view the plan type names (<view dir>/x.lef),
    <view dir>/provenance.json and follows its absolute paths to the ORIGINAL signed kit (provenance.src/face_guard.json,
    the netlist that names, the sign-off receipt).  Those paths sit in json inside the pinned src tree, are read at
    their original place and so cannot be remapped; they must exist on the gen host.
    -> {present: {path: sha | 'dir'}, missing: [{path, by}]} for the views of ONE type (other types' views never block)."""
    out = {"present": {}, "missing": []}
    try:
        t = (jload(plan_path).get("partition_types") or {}).get(typ)
    except (OSError, ValueError):
        return out
    lefs, todo = set(), [t]
    while todo:
        v = todo.pop()
        if isinstance(v, dict):
            todo += list(v.values())
        elif isinstance(v, list):
            todo += v
        elif isinstance(v, str) and v.endswith(".lef"):
            lefs.add(v)
    seen = set()

    def take(p, by):
        p = os.path.normpath(p)
        if p in seen or not p.startswith("/"):
            return
        seen.add(p)
        if os.path.isdir(p):
            out["present"][p] = "dir"
        elif os.path.isfile(p):
            st = os.stat(p)
            out["present"][p] = store.file_sha(p, st) if store else sha256_file(p)
        else:
            out["missing"].append({"path": p, "by": by})

    for lef in sorted(lefs):
        cands = [lef] if os.path.isabs(lef) else [os.path.join(r, lef) for r in list(roots) + [os.path.dirname(plan_path)]]
        vd = next((os.path.dirname(c) for c in cands if os.path.isfile(c)), None)
        pv = os.path.join(vd, "provenance.json") if vd else ""
        if not pv or not os.path.isfile(pv):
            continue
        try:
            j = jload(pv)
        except (OSError, ValueError):
            continue
        refs = [r for r in scan_refs(pv) if os.path.normpath(r) != os.path.normpath(str(j.get("src") or "/"))]
        if isinstance(j.get("src"), str) and j["src"].startswith("/"):
            fg = os.path.join(j["src"], "face_guard.json")
            refs.append(fg)
            try:
                n = jload(fg).get("netlist")
                if isinstance(n, str) and n.startswith("/"):
                    refs.append(n)
            except (OSError, ValueError, AttributeError):
                pass
        for r in refs:
            if os.path.isfile(os.path.join(vd, "signoff.json")) and r == str((j.get("export") or {}).get("signoff")):
                continue                              # the view carries its own receipt: the original is not read
            take(r, pv)
    return out


def snap(spec, snap_root, store_root=None, log=print):
    """content-addressed snapshot of one kit's input closure -> {id, dir, kit_inputs, map, reused, n_files, ...}.
    A required input that is absent raises StoreError (KIT-STORE MISSING): the caller stops the item before any queue wait."""
    import fcntl
    store_root = store_root or os.path.dirname(snap_root.rstrip("/"))
    os.makedirs(snap_root, exist_ok=True)
    dry = snapshot(spec, os.path.join(snap_root, ".dry"), store_root, log=lambda *a: None, dry=True)
    vr = {"present": {}, "missing": []}
    vt = spec.get("view_refs_type")
    plan_in = next((x["path"] for x in spec.get("inputs") or [] if x.get("role") == "plan"), "")
    if vt and plan_in:
        vr = view_refs(plan_in, vt, [r for r in spec.get("in_place") or [] if r])
    dry["in_place"] = dict(dry.get("in_place") or {}, **{"viewref:" + k: v for k, v in vr["present"].items()})
    sid = snap_id(dry)
    d = os.path.join(snap_root, sid)
    root = os.path.join(d, "root")
    with open(d + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)                # one builder per content; later items reuse the finished dir
        reused = os.path.exists(os.path.join(d, ".verified"))
        if reused:
            man = jload(os.path.join(d, "MANIFEST.json"))
        else:
            os.makedirs(d, exist_ok=True)
            man = snapshot(spec, root, store_root, log=log, manifest_dir=d)
            man["in_place"] = dict(man.get("in_place") or {}, **{"viewref:" + k: v for k, v in vr["present"].items()})
            if snap_id(man) != sid:
                raise StoreError(f"KIT-SNAP inputs changed while the snapshot {sid} was built (a lane is still writing "
                                 "them): relaunch when the inputs are final")
            man.update(snap_schema=SNAP_SCHEMA, snap_id=sid)
            with open(os.path.join(d, "MANIFEST.json"), "w") as f:
                f.write(json.dumps(man, indent=1, sort_keys=True))
            verify(d, mark=True)
        _touch(os.path.join(d, ".used"))
    return {"id": sid, "dir": d, "kit_inputs": root, "map": man["map"], "reused": reused, "n_files": len(man["files"]),
            "absent": man.get("absent") or [], "restored": man.get("restored") or [], "host": socket.gethostname(),
            "view_refs": len(vr["present"]), "view_refs_missing": vr["missing"],
            "bytes_copied": 0 if reused else man.get("bytes_copied", 0), "store": store_root}


def verify(snap_dir, mark=True):
    """re-hash every file of a snapshot against its MANIFEST.json; write .verified only when all match.
    Run after the snapshot is built and again on every host it is copied to.  -> {id, n_files}"""
    d = snap_dir.rstrip("/")
    try:
        man = jload(os.path.join(d, "MANIFEST.json"))
    except (OSError, ValueError) as e:
        raise StoreError(f"KIT-SNAP VERIFY {d}: MANIFEST.json unreadable ({e})")
    sid = snap_id(man)
    if sid != os.path.basename(d) or man.get("snap_id") != sid:
        raise StoreError(f"KIT-SNAP VERIFY {d}: manifest content id {sid} is not the directory name")
    root = os.path.join(d, "root")
    if man.get("kit_inputs") != root:
        raise StoreError(f"KIT-SNAP VERIFY {d}: built for {man.get('kit_inputs')}; a snapshot must sit at the same "
                         "absolute path on every host (its recipes name that path)")
    bad = []
    rew = man.get("rewritten") or {}
    for orig, sha in sorted(man["files"].items()):
        want = rew[orig]["kit_sha"] if orig in rew else sha
        f = root + orig
        try:
            got = sha256_file(f)
        except OSError:
            got = "missing"
        if got != want:
            bad.append(f"{orig} ({got[:12]} != {want[:12]})")
            if len(bad) >= 20:
                break
    if bad:
        try:
            os.unlink(os.path.join(d, ".verified"))
        except OSError:
            pass
        raise StoreError(f"KIT-SNAP VERIFY {d}: {len(bad)} file(s) differ from the manifest: " + "; ".join(bad[:5]))
    if mark:
        with open(os.path.join(d, ".verified"), "w") as f:
            f.write(json.dumps({"id": sid, "host": socket.gethostname(), "t": now_s(), "n_files": len(man["files"])}))
        _touch(os.path.join(d, ".used"))
    return {"id": sid, "dir": d, "n_files": len(man["files"]), "host": socket.gethostname()}


def snap_gc(snap_root, keep_days=SNAP_KEEP_DAYS, apply=False, now=None, log=print):
    """delete snapshots no item used for keep_days (.used mtime); dry run unless apply.  Blobs follow the store gc."""
    now = now or time.time()
    out = {"snap_root": snap_root, "kept": 0, "delete": 0, "apply": apply}
    for n in sorted(os.listdir(snap_root)) if os.path.isdir(snap_root) else []:
        d = os.path.join(snap_root, n)
        if not os.path.isdir(d) or not re.fullmatch(r"[0-9a-f]{40}", n):
            continue
        try:
            used = max(os.path.getmtime(os.path.join(d, x)) for x in (".used", ".verified", "MANIFEST.json")
                       if os.path.exists(os.path.join(d, x)))
        except ValueError:
            used = os.path.getmtime(d)
        if now - used <= keep_days * 86400:
            out["kept"] += 1
            continue
        out["delete"] += 1
        if apply:
            shutil.rmtree(d)
            for x in (d + ".lock",):
                if os.path.exists(x):
                    os.unlink(x)
            log(f"KIT-SNAP GC deleted {d}: unused for more than {keep_days} d")
    return out


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
    s = sp.add_parser("snap", help="content-addressed snapshot of a kit's input closure (wave option kit_snap)")
    s.add_argument("--spec-b64", required=True)
    s.add_argument("--snap-root", required=True)
    s.add_argument("--store-root")
    s = sp.add_parser("verify", help="re-hash a snapshot against its manifest; writes .verified when it matches")
    s.add_argument("snap_dir")
    s = sp.add_parser("snap-gc")
    s.add_argument("--snap-root", required=True)
    s.add_argument("--keep-days", type=float, default=SNAP_KEEP_DAYS)
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
        elif a.cmd == "snap":
            print("KW_KIT_SNAP " + json.dumps(snap(json.loads(base64.b64decode(a.spec_b64)), a.snap_root, a.store_root)))
        elif a.cmd == "verify":
            print("KW_KIT_SNAP_VERIFY " + json.dumps(verify(a.snap_dir)))
        elif a.cmd == "snap-gc":
            print("KW_KIT_SNAP_GC " + json.dumps(snap_gc(a.snap_root, a.keep_days, a.apply)))
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
