#!/usr/bin/env python3
"""ot_store.py: the per-host content-addressed artifact store for sealed jobs (ISOLATE-1, OWNER 2026-11-09 03:4x:
"yes, isolate the jobs. simply delete the finished job folder").

One store per scratch filesystem, outside every lane root (so no lane cleanup ever walks it):
  <fs>/ot-store/objects/<sha[:2]>/<sha>      immutable file objects, mode 0444, named by the sha256 of their bytes
  <fs>/ot-store/records/<id[:2]>/<id>.json.gz artifact records (signed_store.write_entry format, schema ARTIFACT_SCHEMA):
                                              name, producer (job, host, cmd, rc, times), tree sha, files [[rel, size, sha]]
  <fs>/ot-store/refs/<name>.json             reference lists: job-<tag> (a live job's inputs, dropped at job end),
                                              pin-<name> (an input of a live form, a counted view; dropped by its owner)
A directory is stored as a TREE object: a JSON file object {"schema": TREE_SCHEMA, "files": {rel: [sha, size, exec]},
"links": {rel: target}, "dirs": [rel]} whose sha is the tree id.  Relative symlinks that stay inside the tree are kept;
an absolute or escaping symlink is refused: it is exactly the cross-job reference the store exists to remove.

Same-filesystem staging hardlinks objects (no disk cost); everything else copies.  GC is by reference only:
an object survives if a ref (expanded through trees), a counted signed-store record (files sha256), or its own age
(< 24 h) keeps it.  Nothing else is consulted; gc is dry unless --apply.

  ot_store.py put PATH [--store S] [--link]           -> prints kind sha
  ot_store.py stage SHA DEST [--store S] [--copy]     hardlink (default) or copy a file/tree out
  ot_store.py verify SHA [--store S]                  re-hash the object (and a tree's files)
  ot_store.py publish PATH --name N [--producer JSON] [--link]   put + write the artifact record; prints the record
  ot_store.py fetch SHA --from HOST [--store S]        copy missing objects from HOST's store (ssh, sha checked)
  ot_store.py push SHA --to HOST [--store S]           copy missing objects to HOST's store (second copy of a live input)
  ot_store.py ref NAME SHA... | unref NAME
  ot_store.py gc [--store S] [--counted DIR] [--apply]
  ot_store.py gc-all [--counted DIR] [--apply]        every scratch store on this host (the daily ot-store-gc.timer)

GC-LOCK (KW-FIX-44 11-10, COORD): <store>/.gc.lock.  Staging (ot-job from the first put until its job-<tag> ref is
written) and publish (put until the record is written) hold it SHARED; gc --apply holds it EXCLUSIVE from building the
keep set to the last unlink.  So an object a job is about to name (a dedup put onto an old object) cannot be deleted
between the put and the ref.  The keep set (the rule applied once on epyc2/epyc7 11-10): every ref (through trees),
every artifact record of this store, counted signed-store files, objects younger than 24 h, and any object with a
second hardlink (still staged in a job dir).  gc --apply writes the deleted list to <store>/gc-log/<UTC time>.tsv.
"""
import argparse
import contextlib
import fcntl
import gzip
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import signed_store as SS  # noqa: E402  (records use the signed-store entry format and its atomic writer)

TREE_SCHEMA = "opentallas.ot_store.tree.v1"
ARTIFACT_SCHEMA = "opentallas.ot_store.artifact.v1"
REF_SCHEMA = "opentallas.ot_store.ref.v1"
KEEP_YOUNG_S = 24 * 3600            # OWNER 11-08: hosts volatile, every hold/lifetime is 24 h
LOCK_NAME = ".gc.lock"
SCRATCH_STORES = ("/srv/opentallas-scratch2/ot-store", "/srv/opentallas-scratch3/ot-store")
BUF = 1 << 20


class StoreError(Exception):
    pass


def default_store(near=None):
    """the store on the filesystem of `near` (a job dir), else OT_STORE, else scratch2's"""
    if os.environ.get("OT_STORE"):
        return os.environ["OT_STORE"]
    if near:
        p = os.path.realpath(near)
        for s in SCRATCH_STORES:
            root = os.path.dirname(s)
            if p == root or p.startswith(root + "/"):
                return s
    return SCRATCH_STORES[0]


def obj_path(store, sha):
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise StoreError(f"not a sha256: {sha!r}")
    return os.path.join(store, "objects", sha[:2], sha)


def have(store, sha):
    return os.path.isfile(obj_path(store, sha))


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(BUF), b""):
            h.update(b)
    return h.hexdigest()


def _tmp(store):
    d = os.path.join(store, "tmp")
    os.makedirs(d, exist_ok=True)
    m = os.path.join(store, ".ot-isolated.json")          # AUTOCLEAN-13: legacy cleanup never touches the store
    if not os.path.exists(m):
        with open(m, "w") as fh:
            json.dump({"schema": "opentallas.ot_isolated.v1", "kind": "ot-store", "written": time.time()}, fh)
    return d


def _install(store, tmp, sha):
    """move a finished temp file into objects/ (first writer wins; the object is immutable)"""
    dst = obj_path(store, sha)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.chmod(tmp, 0o444)
    if os.path.exists(dst):
        os.unlink(tmp)
    else:
        os.replace(tmp, dst)
    return sha


def put_bytes(store, data):
    sha = hashlib.sha256(data).hexdigest()
    if have(store, sha):
        return sha
    fd, tmp = tempfile.mkstemp(dir=_tmp(store), prefix=".o.")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return _install(store, tmp, sha)


def put_file(store, p, link=False):
    """-> sha.  link=True hardlinks the file itself into the store when it is on the same filesystem (for job outputs
    whose job dir is deleted next; the inode becomes read-only).  Otherwise the bytes are copied, hashed while copying."""
    if link:
        sha = sha_file(p)
        if have(store, sha):
            return sha
        fd, tmp = tempfile.mkstemp(dir=_tmp(store), prefix=".l.")
        os.close(fd)
        os.unlink(tmp)
        try:
            os.link(p, tmp)
        except OSError:
            return put_file(store, p, link=False)
        if sha_file(tmp) != sha:                       # changed between the hash and the link: refuse, never store a lie
            os.unlink(tmp)
            raise StoreError(f"{p} changed while it was published")
        return _install(store, tmp, sha)
    h = hashlib.sha256()
    fd, tmp = tempfile.mkstemp(dir=_tmp(store), prefix=".c.")
    with os.fdopen(fd, "wb") as out, open(p, "rb") as fh:
        for b in iter(lambda: fh.read(BUF), b""):
            h.update(b)
            out.write(b)
    return _install(store, tmp, h.hexdigest())


def _inside(rel_dir, target):
    """a relative symlink target that stays inside the tree"""
    if os.path.isabs(target):
        return False
    n = os.path.normpath(os.path.join(rel_dir, target))
    return not (n == ".." or n.startswith("../"))


def put_tree(store, root, link=False):
    """-> tree sha.  Keeps relative links that stay inside and absolute links that resolve inside (stored relative);
    refuses links that leave the tree, and special files."""
    files, links, dirs = {}, {}, []
    root = os.path.abspath(root)
    for dp, dns, fns in os.walk(root, followlinks=False):
        rd = os.path.relpath(dp, root)
        for dn in list(dns):
            p = os.path.join(dp, dn)
            if os.path.islink(p):
                dns.remove(dn)
                fns.append(dn)
            else:
                dirs.append(os.path.normpath(os.path.join(rd, dn)))
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.normpath(os.path.join(rd, fn))
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                t = os.readlink(p)
                if os.path.isabs(t):
                    # KW-FIX-44 COORD 19:3x: an ABSOLUTE link that resolves inside the tree (W/plandir/README.md ->
                    # W/prov/plan/README) is kept, stored as the equivalent relative link so it stays inside wherever
                    # the tree is materialized; one that resolves outside is refused as before
                    a = os.path.normpath(t)
                    if a == root or a.startswith(root + "/"):
                        t = os.path.relpath(a, os.path.dirname(p))
                if not _inside(os.path.dirname(rel), t):
                    raise StoreError(f"symlink {p} -> {t} leaves the tree: declare its target as an input instead")
                links[rel] = t
            elif stat.S_ISREG(st.st_mode):
                files[rel] = [put_file(store, p, link=link), st.st_size, bool(st.st_mode & 0o111)]
            else:
                raise StoreError(f"special file {p} cannot be stored")
    tree = {"schema": TREE_SCHEMA, "files": files, "links": links, "dirs": sorted(dirs)}
    return put_bytes(store, json.dumps(tree, sort_keys=True, separators=(",", ":")).encode())


def read_tree(store, sha):
    try:
        with open(obj_path(store, sha), "rb") as fh:
            head = fh.read(64)
            if not head.startswith(b"{"):
                return None
            t = json.loads(head + fh.read())
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return t if isinstance(t, dict) and t.get("schema") == TREE_SCHEMA else None


def put(store, path, link=False):
    """-> (kind, sha)"""
    if os.path.isdir(path) and not os.path.islink(path):
        return "tree", put_tree(store, path, link=link)
    if os.path.isfile(path) and not os.path.islink(path):
        return "file", put_file(store, path, link=link)
    raise StoreError(f"{path}: not a regular file or directory (a symlink is a reference, name its target)")


def closure(store, sha, missing_ok=False):
    """every object id reachable from sha (itself, and a tree's files)"""
    out = {sha}
    t = read_tree(store, sha) if have(store, sha) else None
    if t is None and not have(store, sha) and not missing_ok:
        raise StoreError(f"object {sha} not in {store}")
    if t:
        out.update(v[0] for v in t["files"].values())
    return out


def _place(store, sha, dst, copy, exe=False):
    src = obj_path(store, sha)
    if not copy:
        try:
            os.link(src, dst)
            return
        except OSError:
            pass                                       # other filesystem: fall back to a read-only copy
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o555 if exe else 0o444)
        return
    shutil.copyfile(src, dst)
    os.chmod(dst, 0o755 if exe else 0o644)


def stage(store, sha, dest, copy=False):
    """materialize sha at dest (must not exist).  copy=False: hardlinks, read-only files and dirs (an input);
    copy=True: private writable copies (a work dir seed)."""
    if os.path.lexists(dest):
        raise StoreError(f"{dest} exists")
    t = read_tree(store, sha)
    if t is None:
        if not have(store, sha):
            raise StoreError(f"object {sha} not in {store}")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        _place(store, sha, dest, copy)
        return
    os.makedirs(dest)
    for d in t["dirs"]:
        os.makedirs(os.path.join(dest, d), exist_ok=True)
    for rel, (fsha, _size, exe) in sorted(t["files"].items()):
        _place(store, fsha, os.path.join(dest, rel), copy, exe)
    for rel, tgt in sorted(t["links"].items()):
        os.symlink(tgt, os.path.join(dest, rel))
    if not copy:
        for dp, _dns, _fns in os.walk(dest, topdown=False):
            os.chmod(dp, 0o555)


def verify(store, sha):
    """-> list of problems (empty = every object present and its bytes hash to its name)"""
    bad = []
    for o in sorted(closure(store, sha, missing_ok=True)):
        if not have(store, o):
            bad.append(f"missing {o}")
        elif sha_file(obj_path(store, o)) != o:
            bad.append(f"corrupt {o}")
    return bad


# ---- records (signed_store entry format) -------------------------------------------------------------------------------

def tree_files(store, kind, sha):
    """[[rel, size, sha]] in signed_store.entry_files order"""
    if kind == "file":
        return [[".", os.path.getsize(obj_path(store, sha)), sha]]
    t = read_tree(store, sha)
    return [[rel, v[1], v[0]] for rel, v in sorted(t["files"].items())]


@contextlib.contextmanager
def lock(store, exclusive=False):
    """GC-LOCK: shared for writers that name objects (staging, publish), exclusive for gc --apply"""
    _tmp(store)
    fd = os.open(os.path.join(store, LOCK_NAME), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        os.close(fd)


def publish(store, path, name, producer=None, link=False):
    """put PATH, write an immutable artifact record naming its producer; -> the record"""
    with lock(store):
        return _publish(store, path, name, producer, link)


def _publish(store, path, name, producer, link):
    kind, sha = put(store, path, link=link)
    bad = verify(store, sha)
    if bad:
        raise StoreError(f"publish {path}: store verify failed: {bad[:3]}")
    body = {"schema": ARTIFACT_SCHEMA, "name": name, "kind": kind, "sha": sha, "source_path": os.path.abspath(path),
            "producer": producer or {}, "files": tree_files(store, kind, sha)}
    rid = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    rec = dict(body, id=rid, published=time.time())
    SS.write_entry(rec, store=store)
    return rec


def records(store):
    return SS.read_manifest(store=store)


# ---- refs and gc ----------------------------------------------------------------------------------------------------------

def _ref_path(store, name):
    if not name or "/" in name or name.startswith("."):
        raise StoreError(f"bad ref name {name!r}")
    return os.path.join(store, "refs", name + ".json")


def ref(store, name, shas, note=""):
    _tmp(store)                                            # store dirs + its isolation marker
    p = _ref_path(store, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".r.")
    with os.fdopen(fd, "w") as fh:
        json.dump({"schema": REF_SCHEMA, "name": name, "shas": sorted(set(shas)), "note": note, "written": time.time()}, fh)
    os.replace(tmp, p)


def unref(store, name):
    try:
        os.unlink(_ref_path(store, name))
    except FileNotFoundError:
        pass


def refs(store):
    d = os.path.join(store, "refs")
    out = {}
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if fn.endswith(".json") and not fn.startswith("."):
            with open(os.path.join(d, fn)) as fh:
                out[fn[:-5]] = json.load(fh)
    return out


def counted_shas(counted_store):
    """sha256 of every file a counted signed-store record lists (those views must stay wherever they are)"""
    out = set()
    if counted_store and os.path.isdir(os.path.join(counted_store, SS.RECORDS)):
        for e in SS.read_manifest(store=counted_store):
            for f in SS.entry_files(e):
                if len(f) > 2 and isinstance(f[2], str) and len(f[2]) == 64:
                    out.add(f[2])
    return out


def gc(store, counted_store=None, apply=False, now=None, young_s=KEEP_YOUNG_S, log=None):
    """-> {"objects", "keep", "delete": [sha...], "freed": bytes}.  See GC-LOCK in the module doc for the keep set;
    with apply the whole pass runs under the exclusive lock and the deleted list goes to log (or gc-log/<time>.tsv)."""
    if not apply:
        return _gc(store, counted_store, False, now, young_s, None)
    with lock(store, exclusive=True):
        if log is None:
            os.makedirs(os.path.join(store, "gc-log"), exist_ok=True)
            log = os.path.join(store, "gc-log", time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + ".tsv")
        return _gc(store, counted_store, True, now, young_s, log)


def _gc(store, counted_store, apply, now, young_s, log):
    now = now or time.time()
    keep = set(counted_shas(counted_store))
    for r in refs(store).values():
        for s in r.get("shas", []):
            keep |= closure(store, s, missing_ok=True)
    for e in records(store):                       # every artifact record of this store keeps its whole tree
        keep |= closure(store, e["sha"], missing_ok=True)
    dele, freed, n = [], 0, 0
    od = os.path.join(store, "objects")
    fh = open(log, "w") if log else None
    try:
        for dp, _dns, fns in os.walk(od):
            for fn in fns:
                p = os.path.join(dp, fn)
                n += 1
                try:
                    st = os.lstat(p)
                except FileNotFoundError:
                    continue
                if fn in keep or now - st.st_mtime < young_s or st.st_nlink > 1:
                    continue
                dele.append(fn)
                freed += st.st_size
                if apply:
                    os.unlink(p)
                    fh.write(f"{fn}\t{st.st_size}\t{int(now - st.st_mtime)}\n")
    finally:
        if fh:
            fh.close()
    return {"objects": n, "keep": n - len(dele), "delete": sorted(dele), "freed": freed, "log": log}


# ---- between hosts --------------------------------------------------------------------------------------------------------

def _ssh(host):
    return ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host]


def fetch(store, sha, host, remote_store=None, runner=subprocess.run):
    """copy sha (and a tree's files) from host's store; every object is re-hashed here before it is installed"""
    rs = remote_store or store

    def get(o):
        if have(store, o):
            return
        fd, tmp = tempfile.mkstemp(dir=_tmp(store), prefix=".f.")
        with os.fdopen(fd, "wb") as fh:
            r = runner(_ssh(host) + ["cat " + shlex.quote(obj_path(rs, o))], stdout=fh, stderr=subprocess.PIPE)
        if r.returncode != 0 or sha_file(tmp) != o:
            os.unlink(tmp)
            raise StoreError(f"fetch {o} from {host}:{rs} failed (rc {r.returncode})")
        _install(store, tmp, o)
    get(sha)
    t = read_tree(store, sha)
    for v in (t or {}).get("files", {}).values():
        get(v[0])


def push(store, sha, host, remote_store=None, runner=subprocess.run):
    """copy missing objects of sha to host's store (sha256sum checked on the far side before the rename)"""
    rs = remote_store or store
    for o in sorted(closure(store, sha)):
        dst = obj_path(rs, o)
        sh = (f"test -f {shlex.quote(dst)} && exit 0; mkdir -p {shlex.quote(os.path.dirname(dst))} {shlex.quote(rs)}/tmp && "
              f"t=$(mktemp -p {shlex.quote(rs)}/tmp .p.XXXXXX) && cat > \"$t\" && "
              f"[ \"$(sha256sum < \"$t\" | cut -c1-64)\" = {o} ] && chmod 444 \"$t\" && mv -n \"$t\" {shlex.quote(dst)}; "
              f"rc=$?; rm -f \"$t\"; exit $rc")
        with open(obj_path(store, o), "rb") as fh:
            r = runner(_ssh(host)[:1] + _ssh(host)[2:] + [sh], stdin=fh, stderr=subprocess.PIPE)
        if r.returncode != 0:
            raise StoreError(f"push {o} to {host}:{rs} failed (rc {r.returncode})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--store")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--copy", action="store_true")
    ap.add_argument("--name")
    ap.add_argument("--producer")
    ap.add_argument("--from", dest="src_host")
    ap.add_argument("--to", dest="dst_host")
    ap.add_argument("--counted")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    st = a.store or (None if a.op == "gc-all" else default_store(a.args[0] if a.op in ("put", "publish") and a.args else None))
    if a.op == "put":
        print(*put(st, a.args[0], link=a.link))
    elif a.op == "stage":
        stage(st, a.args[0], a.args[1], copy=a.copy)
    elif a.op == "verify":
        bad = verify(st, a.args[0])
        print("\n".join(bad) or "OK")
        return 1 if bad else 0
    elif a.op == "publish":
        print(json.dumps(publish(st, a.args[0], a.name or os.path.basename(a.args[0]),
                                 json.loads(a.producer) if a.producer else None, link=a.link), sort_keys=True))
    elif a.op == "fetch":
        fetch(st, a.args[0], a.src_host)
    elif a.op == "push":
        push(st, a.args[0], a.dst_host)
    elif a.op == "ref":
        ref(st, a.args[0], a.args[1:])
    elif a.op == "unref":
        unref(st, a.args[0])
    elif a.op == "gc":
        r = gc(st, counted_store=a.counted, apply=a.apply)
        print(json.dumps(dict(r, delete=len(r["delete"]), applied=a.apply)))
    elif a.op == "gc-all":
        for st in SCRATCH_STORES:
            if os.path.isdir(os.path.join(st, "objects")):
                r = gc(st, counted_store=a.counted, apply=a.apply)
                print(json.dumps(dict(r, store=st, delete=len(r["delete"]), applied=a.apply, at=time.time())), flush=True)
    else:
        ap.error(f"unknown op {a.op}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
