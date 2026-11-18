#!/usr/bin/env python3
"""src_manifest: a die source tree = one main sha + an explicit overlay manifest (SRC-TREE-1115, FABLE-FLOW-1000 classes 4 and 5).

Class 4 (hardlinked, writable trees: one in-place write changed 233 paths, 58 STALE-CORE-VIEW fails) and class 5 (a die tree
drifts from main; 26 files hand-patched live) are closed by three rules this tool enforces:

  build     tree = `git archive <main sha>` of the scope + the overlay files (each listed with its sha256, checked before the
            copy).  Every file is a fresh copy (never a hardlink).  The tree carries .src-manifest.json: main sha, scope,
            overlay {path: sha256}, files {path: sha256}, manifest_hash = sha256 of that content.  `.src-manifest.sha256`
            holds the hash alone (the value adoption pins as dies.<die>.src_manifest_hash).
  publish   verify, chmod a-w every file and directory, then switch a pointer (symlink) to the tree with an atomic rename.
            A change is a NEW tree dir + a pointer switch; nothing is ever edited in place.
  verify    manifest hash self-consistent, equals --expect when given, every listed file present with its sha256, no file the
            manifest does not list, none writable (--ro).  Names each drifted file.  Exit 1 on any drift.
  hosts     run verify on every gen host over ssh (adoption: the event is switched only when this passes on all of them).
  replicate rsync a published tree to other hosts (no hard links), verify it there before the final rename, keep it read-only.
  derive    list the files of a LIVE tree that differ from main at a sha (candidate overlay.json: explicit, with sha256).

overlay.json: {"files": {"<tree relpath>": {"from": "<source path, relative to overlay.json or absolute>", "sha256": "<hex>"}}}
A live patch is a new overlay entry in a new tree, never an edit.  Stdlib only (kit_wave ships this file to the gen host).
"""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

MANIFEST = ".src-manifest.json"
HASHFILE = ".src-manifest.sha256"
SNAPGROUP = ".snap-group"        # TOOLS-DECOUPLE phase 2 (live_tree.py): a snapshot of the die's live tree; its files share inodes with the live tree and the
                                 # die's other snapshots by design (read-only files, rename-only writes), so the shared-inode check does not apply
LINKBASE = ".link-base"          # STAGE A (COORD 11-17, QC D-steps wrote 57 GB each): text file naming the published base tree whose inodes this tree shares
DEFAULT_SCOPE = ["tools", "rtl", "physical", "plans"]
SKIP_DIRS = ("__pycache__", ".git", ".pytest_cache")
SKIP_FILES = ("*.pyc", "*.bak*", "*.orig", "*.rej")
CACHE_DIR = os.path.expanduser("~/.cache/src-manifest")
MAX_SHOW = 20


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def skipped(rel):
    parts = rel.split("/")
    return any(d in SKIP_DIRS for d in parts[:-1]) or any(fnmatch.fnmatch(parts[-1], g) for g in SKIP_FILES)


def manifest_hash(m):
    core = {k: m[k] for k in ("main_sha", "scope", "overlay", "files")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def walk_tree(root):
    """{relpath: abs} of every regular file under root (symlinks recorded too, hashed by target text), skipping caches"""
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            if rel in (MANIFEST, HASHFILE, LINKBASE, SNAPGROUP) or skipped(rel):
                continue
            out[rel] = p
    return out


def tree_hash(p):
    if os.path.islink(p):
        return "link:" + hashlib.sha256(os.readlink(p).encode()).hexdigest()
    return sha256_file(p)


def signature(root):
    n = z = m = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            try:
                st = os.lstat(os.path.join(dp, f))
            except OSError:
                continue
            n += 1
            z += st.st_size
            m = max(m, st.st_mtime_ns)
    return f"{n}:{m}:{z}"


def link_base(root):
    """the declared base tree of a link-published tree ('' = none).  Only a path that is itself a manifest tree counts."""
    try:
        b = open(os.path.join(root, LINKBASE)).read().strip()
    except OSError:
        return ""
    return b if b and os.path.isfile(os.path.join(b, MANIFEST)) else ""


def write_link_base(root, base):
    """(re)write ROOT/.link-base = realpath(base), copy+mv: a .link-base copied or hardlinked from an earlier tree (a chained link,
    e.g. D4 -> M5 -> M5T) is read-only and may share its inode with that tree's own .link-base, so it is replaced, never written through.
    The caller makes ROOT writable first."""
    dst = os.path.join(root, LINKBASE)
    tmp = dst + f".tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        f.write(os.path.realpath(base) + "\n")
    os.chmod(tmp, 0o444)
    os.replace(tmp, dst)


def linked_children(root):
    """COORD 11-18: published sibling trees whose .link-base is this tree (a tools refresh child linked from it): their files are intended extra names of this tree's inodes"""
    parent, me, out = os.path.dirname(os.path.realpath(root)), os.path.realpath(root), []
    try:
        names = os.listdir(parent)
    except OSError:
        return out
    for n in names:
        c = os.path.join(parent, n)
        if c != me and os.path.isfile(os.path.join(c, LINKBASE)) and link_base(c) == me:
            out.append(c)
    return out


def links_accounted(path, rel, st, base, children):
    """every extra name of a read-only file is the same inode at rel in the declared base or in a tree linked from this one: nlink <= 1 + those"""
    names = 1
    for t in ([base] if base else []) + list(children):
        try:
            if os.lstat(os.path.join(t, rel)).st_ino == st.st_ino:
                names += 1
        except OSError:
            pass
    return st.st_nlink <= names


def shares_with_base(path, rel, base):
    """True when the file is the same inode as the file at rel in the declared base (an intended link, not a cp -al copy elsewhere)"""
    if not base:
        return False
    try:
        return os.lstat(path).st_ino == os.lstat(os.path.join(base, rel)).st_ino
    except OSError:
        return False


def snap_group(root):
    """the live tree a live_tree.py snapshot was taken from ('' = not a snapshot)"""
    try:
        return open(os.path.join(root, SNAPGROUP)).read().strip()
    except OSError:
        return ""


def load_manifest(root):
    try:
        with open(os.path.join(root, MANIFEST)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def writable(p):
    return bool(os.lstat(p).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)) and not os.path.islink(p)


def verify(root, expect="", ro=False, full=False):
    """-> (errors, info).  errors = ['SRC_MANIFEST DRIFT <path> (why)', ...]; [] = tree is exactly what the manifest says."""
    root = os.path.realpath(root)
    m = load_manifest(root)
    if m is None:
        return [f"SRC_MANIFEST MISSING {root}/{MANIFEST} (tree not built by src_manifest.py build)"], {}
    errs = []
    h = manifest_hash(m)
    if h != m.get("manifest_hash"):
        errs.append(f"SRC_MANIFEST DRIFT {MANIFEST} (manifest content does not match its own hash)")
    if expect and h != expect:
        errs.append(f"SRC_MANIFEST DRIFT {MANIFEST} (hash {h[:12]} is not the adopted {expect[:12]})")
    info = {"manifest_hash": h, "main_sha": m.get("main_sha"), "files": len(m.get("files") or {})}
    cf = os.path.join(CACHE_DIR, hashlib.md5(root.encode()).hexdigest() + ".json")
    sig = signature(root)
    if not errs and not full and not ro:
        try:
            with open(cf) as f:
                c = json.load(f)
            if c.get("sig") == sig and c.get("hash") == h:
                info["cached"] = True
                return [], info
        except (OSError, ValueError):
            pass
    want = m.get("files") or {}
    have = walk_tree(root)
    lbase = link_base(root)
    kids = linked_children(root)
    snap = bool(snap_group(root))
    for rel in sorted(want):
        p = have.get(rel)
        if p is None:
            errs.append(f"SRC_MANIFEST DRIFT {rel} (missing)")
        elif tree_hash(p) != want[rel]:
            errs.append(f"SRC_MANIFEST DRIFT {rel} (modified: not the manifest content)")
        elif ro and writable(p):
            errs.append(f"SRC_MANIFEST DRIFT {rel} (writable: published trees are read-only)")
        elif ro and not snap and not os.path.islink(p) and os.lstat(p).st_nlink > 1 and not shares_with_base(p, rel, lbase) \
                and not links_accounted(p, rel, os.lstat(p), lbase, kids):
            errs.append(f"SRC_MANIFEST DRIFT {rel} (hardlinked, nlink {os.lstat(p).st_nlink}: a write or chmod elsewhere reaches this file)")
    nshared = sum(1 for e in errs if "hardlinked, nlink" in e)
    if nshared:
        errs.insert(0, f"SRC_MANIFEST NOT-READY {nshared} file(s) share an inode with another path (cp -al copy elsewhere): "
                       f"a published tree must be unshared; run `src_manifest.py links TREE --find-in DIR...` to name the other paths")
    for rel in sorted(set(have) - set(want)):
        errs.append(f"SRC_MANIFEST DRIFT {rel} (extra: not in the manifest)")
    if ro and writable(root):
        errs.append("SRC_MANIFEST DRIFT . (tree dir writable)")
    info["drift"] = len(errs)
    if not errs:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cf + ".tmp", "w") as f:
                json.dump({"sig": sig, "hash": h}, f)
            os.replace(cf + ".tmp", cf)
        except OSError:
            pass
    return errs, info



def cached_receipt(root, expect=""):
    """Reuse a completed content verification only while its immutable metadata still matches.

    This never hashes source payload again. The existing verify cache is written
    only after error-free content verification; a missing/stale cache is a miss,
    and the caller must run the normal verifier. Read-only and inode checks are
    current, not assumed from that earlier verification.
    """
    root = os.path.realpath(root)
    m = load_manifest(root)
    if m is None:
        return [f"SRC_MANIFEST CACHE MISS {root}: no manifest"], {}
    try:
        h = manifest_hash(m)
    except (KeyError, TypeError, ValueError) as e:
        return [f"SRC_MANIFEST CACHE MISS {root}: malformed manifest ({e})"], {}
    errs = []
    if h != m.get("manifest_hash"):
        errs.append("SRC_MANIFEST CACHE MISS manifest content does not match its hash")
    if expect and h != expect:
        errs.append(f"SRC_MANIFEST CACHE MISS hash {h} is not expected {expect}")
    try:
        if Path(root, HASHFILE).read_text().strip() != h:
            errs.append("SRC_MANIFEST CACHE MISS published hash file differs from manifest")
    except OSError as e:
        errs.append(f"SRC_MANIFEST CACHE MISS hash file: {e}")
    cf = os.path.join(CACHE_DIR, hashlib.md5(root.encode()).hexdigest() + ".json")
    try:
        cb = Path(cf).read_bytes()
        cached = json.loads(cb)
        cache_mtime = os.stat(cf).st_mtime_ns
    except (OSError, ValueError) as e:
        return errs + [f"SRC_MANIFEST CACHE MISS {cf}: {e}"], {}
    sig = signature(root)
    if cached.get("hash") != h or cached.get("sig") != sig:
        errs.append("SRC_MANIFEST CACHE MISS completed verification hash/signature is stale")
    have = walk_tree(root)
    want = m.get("files") or {}
    if set(have) != set(want):
        errs.append("SRC_MANIFEST CACHE MISS current inventory differs from verified manifest")
    paths = [root, os.path.join(root, MANIFEST), os.path.join(root, HASHFILE)] + list(have.values())
    snap = bool(snap_group(root))
    lbase = link_base(root)                                     # a link-published tree: inodes shared with exactly its declared base are intended (as verify)
    for dp, dn, _fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        paths.extend(os.path.join(dp, d) for d in dn)
    for q in paths:
        try:
            st = os.lstat(q)
            if not stat.S_ISLNK(st.st_mode) and st.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                errs.append(f"SRC_MANIFEST CACHE MISS writable {os.path.relpath(q, root)}")
            if stat.S_ISREG(st.st_mode) and st.st_nlink > 1 and not snap and not shares_with_base(q, os.path.relpath(q, root), lbase):
                errs.append(f"SRC_MANIFEST CACHE MISS shared inode {os.path.relpath(q, root)} nlink={st.st_nlink}")
        except OSError as e:
            errs.append(f"SRC_MANIFEST CACHE MISS stat {q}: {e}")
    info = dict(schema="opentallas.src_manifest.cached_receipt.v1", verdict="PASS" if not errs else "MISS",
                source=root, manifest_hash=h, main_sha=m.get("main_sha"), files=len(want),
                signature=sig, cache_path=cf, cache_mtime_ns=cache_mtime,
                cache_sha256=hashlib.sha256(cb).hexdigest(),
                basis="completed content verification cache plus current read-only unshared inventory" + (f" (inodes shared only with link base {lbase})" if lbase else ""))
    return errs, info

def shared_inodes(root, limit=0):
    """stat-only scan (no hashing: cheap enough for every tick): [(relpath, nlink)] of every regular file with nlink > 1, i.e. a file
    another path (a `cp -al` copy in some lane's tree) can change.  A published tree must have none (TOOLS-CONVERGE-1116, 2nd
    occurrence: S81 cmp_B6gF2s, HEAD fable-fix-head-serdes/tree5)."""
    out = []
    lbase = link_base(root)
    kids = linked_children(root)      # COORD 11-18: extra names that are the same inode in the base or in a tree linked FROM this one are intended (a tools refresh child)
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and st.st_nlink > 1 and not shares_with_base(p, os.path.relpath(p, root), lbase):
                rel = os.path.relpath(p, root)
                if not st.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) and links_accounted(p, rel, st, lbase, kids):
                    continue
                out.append((rel, st.st_nlink))
                if limit and len(out) >= limit:
                    return out
    return out


def links_report(root, find_in=(), show=20):
    """-> (errors, n): 'SRC_MANIFEST SHARED-INODE <path> (nlink n[, also <path>])'; find_in = dirs searched for the other names"""
    bad = shared_inodes(root)
    errs = []
    inos = {}
    for rel, n in bad[:show]:
        inos[os.lstat(os.path.join(root, rel)).st_ino] = rel
    partners = {}
    if find_in and inos:
        for top in find_in:
            for dp, dn, fn in os.walk(top):
                if os.path.realpath(dp).startswith(os.path.realpath(root)):
                    dn[:] = []
                    continue
                for f in fn:
                    pp = os.path.join(dp, f)
                    try:
                        i = os.lstat(pp).st_ino
                    except OSError:
                        continue
                    if i in inos and i not in partners:
                        partners[i] = pp
                if len(partners) == len(inos):
                    break
    for rel, n in bad[:show]:
        ino = os.lstat(os.path.join(root, rel)).st_ino
        errs.append(f"SRC_MANIFEST SHARED-INODE {rel} (nlink {n}" + (f", also {partners[ino]}" if ino in partners else "") + ")")
    if len(bad) > show:
        errs.append(f"SRC_MANIFEST SHARED-INODE ... and {len(bad) - show} more of {len(bad)}")
    return errs, len(bad)


def report(errs):
    for e in errs[:MAX_SHOW]:
        print(e)
    if len(errs) > MAX_SHOW:
        print(f"SRC_MANIFEST DRIFT ... and {len(errs) - MAX_SHOW} more")


# ---- build ----------------------------------------------------------------------------------------------------------

def git_archive(repo, sha, scope, out, lazy=False):
    """write the scope of commit `sha` into out: ls-tree + cat-file (no .gitattributes / export filters, exact blobs).
    A missing blob (partial clone without it) is an error naming the path, never a silent skip."""
    lt = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "-z", sha, "--"] + list(scope), capture_output=True)
    if lt.returncode:
        raise SystemExit(f"git ls-tree {sha} failed: {lt.stderr.decode()[-300:]}")
    ents = []
    for rec in lt.stdout.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, typ, oid = meta.decode().split()
        if typ == "blob":
            ents.append((mode, oid, path.decode()))
    if not ents:
        raise SystemExit(f"scope {scope} is empty at {sha}")
    cf = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          env=dict(os.environ) if lazy else dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    try:
        for mode, oid, path in ents:
            cf.stdin.write(oid.encode() + b"\n")
            cf.stdin.flush()
            hdr = cf.stdout.readline().split()
            if len(hdr) != 3 or hdr[1] != b"blob":
                raise SystemExit(f"blob {oid[:12]} of {path} not available in {repo} (partial clone: check out the scope first, or lazy=True)")
            data = cf.stdout.read(int(hdr[2]))
            cf.stdout.read(1)
            dest = os.path.join(out, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if mode == "120000":
                os.symlink(data.decode(), dest)
            else:
                with open(dest, "wb") as f:
                    f.write(data)
                os.chmod(dest, 0o755 if mode == "100755" else 0o644)
    finally:
        cf.stdin.close()
        cf.wait()


TOOLS_SCOPE = ("tools/", "physical/common_flow/", "rtl/lib/", "rtl/common/")


def check_pin(repo, sha, main_ref, rt_root):
    """TOOLS-CONVERGE-1115 (FABLE-FLOWCLASS-TOOLSKEW-2030 2.2): the pinned tools_sha must be an ancestor of main_ref and, when
    rt_root is given, have rt/<sha12>.manifest.json there.  Errors -> SystemExit."""
    if main_ref:
        r = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", sha, main_ref], capture_output=True)
        if r.returncode:
            raise SystemExit(f"refuse: tools_sha {sha[:12]} is not an ancestor of {main_ref} (a die tree is built from merged main only)")
    if rt_root and not os.path.isfile(os.path.join(rt_root, f"{sha[:12]}.manifest.json")):
        raise SystemExit(f"refuse: no {rt_root}/{sha[:12]}.manifest.json (tools_sha is not published as an rt tree on this host)")


def tool_overlay_errors(ov, die, allow_file, now=None):
    """overlay entries under the TOOLS scope are refused unless tool_skew_allow.json lists them for the die with a branch_sha
    and an expiry (ISO date-time) at most 12 h away.  -> [error text]"""
    import datetime
    tools = sorted(r for r in ov if r.startswith(TOOLS_SCOPE))
    if not tools:
        return []
    now = now or datetime.datetime.now()
    try:
        allow = (json.load(open(allow_file)) if allow_file else {}).get(die or "", {})
    except (OSError, ValueError):
        allow = {}
    errs = []
    for rel in tools:
        ent = next((e for pat, e in allow.items() if pat == rel or fnmatch.fnmatchcase(rel, pat)), None)
        try:
            exp = datetime.datetime.fromisoformat(str((ent or {}).get("expires", "")))
        except ValueError:
            exp = None
        if ent is None or not ent.get("branch_sha") or exp is None:
            errs.append(f"overlay {rel} is a TOOL (only DATA may be overlaid); allow it per die with branch_sha + expires in tool_skew_allow.json")
        elif exp < now or exp > now + datetime.timedelta(hours=12):
            errs.append(f"overlay {rel}: allowlist expiry {exp} must be in the future and within 12 h")
    return errs


# ---- frozen views by content hash (KV-R 11-16, FABLE-FLOW-2000) ------------------------------------------------------

def view_hash_errors(root):
    """[error] for every <view>/landing_evidence (provenance.json + manifest.json) under root whose frozen files do not have the
    sha256 the view's own provenance records (signoff.json, <m>.lef, <m>_tt.lib, face_guard_source.py), or whose manifest.json lists a
    stale hash.  A tree with such a view must not be built or published (w652/w653/w672: face tool 5083985a != frozen 7ecd3a0d failed
    hard_landing.prove at gen).  Same rule as tools/autopilot/view_by_hash.py check; stdlib only, because this file ships alone."""
    errs = []
    for dp, dn, fn in os.walk(root):
        if os.path.basename(dp) != "landing_evidence" or "provenance.json" not in fn or "manifest.json" not in fn:
            continue
        rel = os.path.relpath(dp, root)
        try:
            prov = json.load(open(os.path.join(dp, "provenance.json")))
            man = json.load(open(os.path.join(dp, "manifest.json")))
            master = man["master"]
            exp = prov.get("export") or {}
            want = {"signoff.json": exp.get("signoff_sha256"), "face_guard_source.py": (prov.get("kit") or {}).get("face_guard_sha256")}
            for name, sha in (exp.get("files_sha256") or {}).items():
                if name in (master + ".lef", master + "_tt.lib"):
                    want[name] = sha
            for name, sha in want.items():
                if not sha:
                    continue
                f = os.path.join(dp, name)
                if not os.path.isfile(f):
                    errs.append(f"VIEW-HASH {rel}: {name} missing")
                elif sha256_file(f) != sha:
                    errs.append(f"VIEW-HASH {rel}: {name} {sha256_file(f)[:8]} != provenance {sha[:8]}")
            for name, sha in (man.get("sha256") or {}).items():
                f = os.path.join(dp, name)
                if os.path.isfile(f) and sha256_file(f) != sha:
                    errs.append(f"VIEW-HASH {rel}: manifest.json stale hash for {name}")
        except (OSError, ValueError, KeyError) as e:
            errs.append(f"VIEW-HASH {rel}: unreadable evidence ({type(e).__name__}: {e})")
    return errs


def build(repo, sha, overlay_json, scope, out, die="", allow_file="", main_ref="origin/main", rt_root=""):
    if os.path.exists(out):
        raise SystemExit(f"refuse: {out} exists (a tree is built once into a new dir, never rebuilt in place)")
    sha = subprocess.run(["git", "-C", repo, "rev-parse", sha + "^{commit}"], capture_output=True, text=True,
                         check=True).stdout.strip()
    check_pin(repo, sha, main_ref, rt_root)
    ov = {}
    if overlay_json:
        base = os.path.dirname(os.path.abspath(overlay_json))
        ov = json.load(open(overlay_json)).get("files") or {}
        for rel, e in ov.items():
            src = e["from"] if os.path.isabs(e["from"]) else os.path.join(base, e["from"])
            if not os.path.isfile(src) or sha256_file(src) != e["sha256"]:
                raise SystemExit(f"overlay {rel}: source {src} missing or sha256 != declared {e['sha256'][:12]}")
            if rel.startswith("/") or ".." in rel.split("/"):
                raise SystemExit(f"overlay path {rel} escapes the tree")
    bad = tool_overlay_errors(ov, die, allow_file)
    if bad:
        raise SystemExit("refuse:\n  " + "\n  ".join(bad))
    tmp = out + ".building"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    git_archive(repo, sha, scope, tmp)
    for rel, e in sorted(ov.items()):
        src = e["from"] if os.path.isabs(e["from"]) else os.path.join(os.path.dirname(os.path.abspath(overlay_json)), e["from"])
        dest = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.lexists(dest):
            os.unlink(dest)
        shutil.copyfile(src, dest)                      # a fresh inode, never a link
        os.chmod(dest, os.stat(src).st_mode & 0o755 | 0o644)
    vh = view_hash_errors(tmp)
    if vh:                                              # fail closed: a view whose bytes differ from its provenance never ships
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit("refuse: frozen view hash mismatch:\n  " + "\n  ".join(vh[:20]))
    files = {rel: tree_hash(p) for rel, p in walk_tree(tmp).items()}
    m = {"version": 1, "main_sha": sha, "scope": list(scope), "overlay": {r: e["sha256"] for r, e in sorted(ov.items())},
         "files": files}
    m["manifest_hash"] = manifest_hash(m)
    with open(os.path.join(tmp, MANIFEST), "w") as f:
        json.dump(m, f, indent=0, sort_keys=True)
    with open(os.path.join(tmp, HASHFILE), "w") as f:
        f.write(m["manifest_hash"] + "\n")
    os.rename(tmp, out)
    return m


def make_ro(root):
    for dp, dn, fn in os.walk(root, topdown=False):
        for f in fn:
            p = os.path.join(dp, f)
            if not os.path.islink(p) and os.lstat(p).st_mode & 0o222:
                os.chmod(p, os.lstat(p).st_mode & ~0o222)           # a file already a-w (e.g. one linked from the base) is left alone: no chmod of a shared inode
        if os.lstat(dp).st_mode & 0o222:
            os.chmod(dp, os.lstat(dp).st_mode & ~0o222)


def switch_pointer(pointer, tree):
    """atomic: pointer -> tree (a symlink); never writes inside either tree"""
    tmp = f"{pointer}.new.{os.getpid()}"
    if os.path.lexists(tmp):
        os.unlink(tmp)
    os.symlink(os.path.abspath(tree), tmp)
    os.replace(tmp, pointer)


def publish(tree, pointer=""):
    errs, info = verify(tree, full=True)
    if errs:
        report(errs)
        raise SystemExit("publish refused: tree does not match its manifest")
    vh = view_hash_errors(tree)
    if vh:
        for e in vh[:MAX_SHOW]:
            print(e)
        raise SystemExit("publish refused: frozen view hash mismatch (view_by_hash.py stage repairs it by the recorded sha)")
    make_ro(tree)
    errs, info = verify(tree, ro=True, full=True)
    if errs:
        report(errs)
        raise SystemExit("publish refused: tree not read-only after chmod")
    if pointer:
        if os.path.lexists(pointer) and not os.path.islink(pointer):
            raise SystemExit(f"refuse: pointer {pointer} exists and is not a symlink")
        switch_pointer(pointer, tree)
    return info


def derive(live, repo, sha, scope):
    """candidate overlay: live-tree files whose content differs from (or is absent in) main at sha"""
    out = {}
    tmp = tempfile.mkdtemp(prefix="srcm-derive-")
    try:
        git_archive(repo, sha, scope, tmp)
        base = {rel: tree_hash(p) for rel, p in walk_tree(tmp).items()}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for rel, p in walk_tree(live).items():
        if not any(rel == s.rstrip("/") or rel.startswith(s.rstrip("/") + "/") for s in scope):
            continue
        if os.path.islink(p):
            continue
        h = sha256_file(p)
        if base.get(rel) != h:
            out[rel] = {"from": os.path.abspath(p), "sha256": h, "main": "absent" if rel not in base else "differs"}
    return {"main_sha": sha, "files": out}


# ---- delta (v2 trees without a rebuild or a 48 GB network copy) --------------------------------------------------------------

def delta_make(repo, old_tree, new_sha, out, drop_overlay=(), paths=None):
    """pack = the paths whose content differs between the tree's main sha and new_sha inside the tree's scope (typically 40-80 files):
    out/delta.json + out/files/<path>.  A changed path that the tree's overlay carries is refused (the overlay wins; re-derive it)."""
    m = load_manifest(old_tree)
    if not m:
        raise SystemExit(f"{old_tree} has no manifest")
    new_sha = subprocess.run(["git", "-C", repo, "rev-parse", new_sha + "^{commit}"], capture_output=True, text=True,
                             check=True).stdout.strip()
    spec = list(paths) if paths else list(m["scope"])          # WAVE-FLOW-R2: --paths restricts the pack (tools-only refresh: plan and RTL stay byte-identical)
    if paths and not all(any(x == sc or x.startswith(sc + "/") for sc in m["scope"]) for x in spec):
        raise SystemExit("refuse: --paths outside the tree scope " + ",".join(m["scope"]))
    nm = subprocess.run(["git", "-C", repo, "diff", "--name-status", "-z", "--no-renames", m["main_sha"], new_sha, "--"] + spec,
                        capture_output=True, text=True, check=True).stdout.split("\0")
    recs = [(nm[i], nm[i + 1]) for i in range(0, len(nm) - 1, 2)]
    drop = set(drop_overlay)
    clash = [p for _st, p in recs if p in m["overlay"] and p not in drop]
    if clash:
        raise SystemExit("refuse: paths changed on main are overlaid by the tree: " + ", ".join(clash[:10]))
    if os.path.exists(out):
        raise SystemExit(f"refuse: {out} exists")
    os.makedirs(os.path.join(out, "files"))
    add, delete = {}, []
    for st, path in recs:
        if st == "D":
            delete.append(path)
            continue
        blob = subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{new_sha}:{path}"], capture_output=True, check=True).stdout
        mode = subprocess.run(["git", "-C", repo, "ls-tree", new_sha, "--", path], capture_output=True, text=True).stdout.split()[0]
        dest = os.path.join(out, "files", path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(blob)
        add[path] = {"sha256": hashlib.sha256(blob).hexdigest(), "exec": mode == "100755", "link": mode == "120000"}
    json.dump({"old_manifest_hash": m["manifest_hash"], "old_main": m["main_sha"], "new_main": new_sha, "scope": m["scope"],
               "add": add, "delete": delete, "overlay_drop": sorted(drop & set(m["overlay"]))},
              open(os.path.join(out, "delta.json"), "w"), indent=0, sort_keys=True)
    return len(add), len(delete)


def link_tree(src, dst):
    """STAGE A: dst = the directory structure of src with every regular file HARDLINKED from src (unchanged files cost nothing), symlinks recreated.  src must be a
    read-only published tree: the links are made once, into the new tree, which is then made read-only; nothing ever writes through them (delta-apply unlinks a path
    before it writes a new copy, retire tools chmod directories only)."""
    for dp, dn, fn in os.walk(src):
        rel = os.path.relpath(dp, src)
        d = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(d, exist_ok=True)
        for f in fn:
            sp_, dp_ = os.path.join(dp, f), os.path.join(d, f)
            if os.path.islink(sp_):
                os.symlink(os.readlink(sp_), dp_)
            else:
                os.link(sp_, dp_)
        for x in dn:                                              # keep the source's directory modes (made writable by the caller)
            os.makedirs(os.path.join(d, x), exist_ok=True)


def delta_apply(pack, old_tree, out, link=False, expect=""):
    """out = a real copy (cp -a, fresh inodes, never links) of old_tree + the pack; new manifest = old manifest with the changed paths;
    nothing is trusted: the caller runs publish (full verify) afterwards."""
    d = json.load(open(os.path.join(pack, "delta.json")))
    m = load_manifest(old_tree)
    if not m or m["manifest_hash"] != d["old_manifest_hash"]:
        raise SystemExit("refuse: pack was made for another tree (old manifest hash differs)")
    if os.path.exists(out):
        raise SystemExit(f"refuse: {out} exists")
    tmp = out + ".building"
    shutil.rmtree(tmp, ignore_errors=True)
    if link:
        link_tree(old_tree, tmp)
    else:
        subprocess.run(["cp", "-a", "--reflink=never", old_tree, tmp], check=True)
    for dp, dn, fn in os.walk(tmp):
        os.chmod(dp, os.lstat(dp).st_mode | stat.S_IWUSR)
    files = dict(m["files"])
    for path in d["delete"]:
        try:
            os.unlink(os.path.join(tmp, path))
        except FileNotFoundError:
            pass
        files.pop(path, None)
    for path, e in d["add"].items():
        dest = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.lexists(dest):
            os.chmod(os.path.dirname(dest), os.lstat(os.path.dirname(dest)).st_mode | stat.S_IWUSR)
            os.unlink(dest)
        shutil.copyfile(os.path.join(pack, "files", path), dest)
        os.chmod(dest, 0o755 if e["exec"] else 0o644)
        files[path] = e["sha256"]
    ov = dict(m["overlay"])
    for k in d.get("overlay_drop") or []:                       # a stale overlay copy of a file main changed: main's version wins
        ov.pop(k, None)
    ov.update(d.get("overlay_add") or {})                       # data files a data pack adds (data_pack.py): they are overlay, not main
    nm = {"version": 1, "main_sha": d["new_main"], "scope": m["scope"], "overlay": ov, "files": files}
    nm["manifest_hash"] = manifest_hash(nm)
    for fn in (MANIFEST, HASHFILE):
        try:
            os.unlink(os.path.join(tmp, fn))
        except FileNotFoundError:
            pass
    with open(os.path.join(tmp, MANIFEST), "w") as f:
        json.dump(nm, f, indent=0, sort_keys=True)
    with open(os.path.join(tmp, HASHFILE), "w") as f:
        f.write(nm["manifest_hash"] + "\n")
    if link:
        write_link_base(tmp, old_tree)                          # old_tree's own .link-base (chained link) was hardlinked in: replace it
    if expect or link:                                           # (4) hash equality BEFORE the tree can be published or applied
        errs, _info = verify(tmp, expect=expect, full=True)
        if errs:
            for dp, dn, fn in os.walk(tmp):                      # directories only: a file chmod would reach the shared inode in the base
                os.chmod(dp, os.lstat(dp).st_mode | stat.S_IWUSR)
            shutil.rmtree(tmp, ignore_errors=True)
            report(errs)
            raise SystemExit("delta-apply refused: composed tree does not match the manifest" + (f" / expected {expect[:12]}" if expect else ""))
    os.rename(tmp, out)
    return nm


# ---- retire (FLOW-1113 / r343: one base tree per tools sha + small data packs; superseded _dN versions are deleted at publish) ----

import re as _re

_DN = _re.compile(r"^(?P<base>.+?)_d(?P<n>\d+)$")


def _in_use(path):
    """True when any process cmdline or cwd names `path` (a running kit/bind keeps its tree)"""
    needle = path.rstrip("/").encode()
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if needle in open(f"/proc/{pid}/cmdline", "rb").read():
                return True
            if os.readlink(f"/proc/{pid}/cwd").startswith(path.rstrip("/")):
                return True
        except OSError:
            continue
    return False


def retire_candidates(new_tree, refs=(), keep=0):
    """-> [(path, why)] superseded siblings of new_tree: same base name with a LOWER _dN (the base tree itself is kept: it is the
    shared base the packs were made from), not named in any refs file, not in use.  keep = how many of the newest older _dN to keep."""
    new_tree = os.path.abspath(new_tree).rstrip("/")
    d, name = os.path.dirname(new_tree), os.path.basename(new_tree)
    m = _DN.match(name)
    if not m:
        return []
    base, n = m.group("base"), int(m.group("n"))
    text = ""
    for r in refs:
        try:
            text += open(r, errors="ignore").read()
        except OSError:
            pass
    older = []
    for e in sorted(os.listdir(d)):
        mm = _DN.match(e)
        if mm and mm.group("base") == base and int(mm.group("n")) < n and os.path.isdir(os.path.join(d, e)):
            older.append((int(mm.group("n")), e))
    older.sort(reverse=True)
    out = []
    for i, (k, e) in enumerate(older):
        path = os.path.join(d, e)
        if i < keep:
            continue
        if _re.search(_re.escape(e) + r"(?![\w])", text):
            out.append((path, "REFERENCED"))
        elif _in_use(path):
            out.append((path, "IN-USE"))
        else:
            out.append((path, "DELETE"))
    return out


def _guard():
    """the ONE shared delete rule (tools/fleet/ot_delete_guard.py, CLEAN-ALL-1115 postmortem): -> module, or None when it cannot be loaded.
    A missing guard fails CLOSED: nothing is deleted."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fleet"))
        import ot_delete_guard as G
        return G if hasattr(G, "refuse") else None
    except Exception:
        return None


def retire(new_tree, refs=(), keep=0, dry=False, guard=None):
    done = []
    G = guard if guard is not None else _guard()
    for path, why in retire_candidates(new_tree, refs, keep):
        if why != "DELETE":
            print(f"SRC_MANIFEST RETIRE-KEEP {path} ({why})")
            continue
        if G is None:
            print(f"SRC_MANIFEST RETIRE-REFUSED {path} (ot_delete_guard missing: fail closed)")
            continue
        try:
            reason = G.refuse(path)
        except Exception as e:                           # a guard that errors is a guard that refuses
            reason = f"guard error {type(e).__name__}: {e}"
        if reason:
            print(f"SRC_MANIFEST RETIRE-REFUSED {path} (ot_delete_guard: {reason})")
            continue
        if not dry:
            for dp, dn, fn in os.walk(path):
                os.chmod(dp, os.lstat(dp).st_mode | stat.S_IWUSR)
            shutil.rmtree(path)
        print(f"SRC_MANIFEST RETIRED {path}" + (" (dry run)" if dry else ""))
        done.append(path)
    return done


# ---- hosts ----------------------------------------------------------------------------------------------------------

RSYNC_SSH = "ssh -o BatchMode=yes -o ControlPath=none"   # rsync -e (tests swap in a local stand-in)
SSH = ["timeout", "900", "ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20"]


REPL_FLOOR_GB = 50          # ot-run's scratch floor (never lower)
REPL_MARGIN_GB = 20         # COORD FABLE-FLOW-1100: a copy must leave floor + 20 GB free on the target


def room_after_copy(free_gb, tree_gb, part_gb=0.0, floor_gb=REPL_FLOOR_GB, margin_gb=REPL_MARGIN_GB):
    """-> (ok, free_after_gb).  part_gb = bytes already written into the target's .part (they are not charged twice)."""
    after = free_gb + part_gb - tree_gb
    return after >= floor_gb + margin_gb, after


def tree_gb(path):
    out = subprocess.run(["du", "-sb", path], capture_output=True, text=True).stdout.split()
    return int(out[0]) / 2**30 if out else 0.0


def remote_free_gb(host, directory, part):
    """(free GB of the target's disk, GB already in <part>) over ssh; (None, 0) when the host does not answer"""
    cmd = f"df -BM --output=avail {shlex.quote(directory)} | tail -n1 | tr -dc 0-9; echo; du -sb {shlex.quote(part)} 2>/dev/null | cut -f1"
    p = subprocess.run(SSH + [host, cmd], capture_output=True, text=True)
    ls = [x.strip() for x in p.stdout.splitlines()]
    try:
        return int(ls[0]) / 1024, (int(ls[1]) / 2**30 if len(ls) > 1 and ls[1] else 0.0)
    except (ValueError, IndexError):
        return None, 0.0


def remote_verify(host, path, expect, ro=True):
    script = open(os.path.abspath(__file__)).read()
    cmd = f"python3 -I -c {shlex.quote(script)} verify {shlex.quote(path)}" + (f" --expect {expect}" if expect else "") + \
          (" --ro" if ro else "")
    p = subprocess.run(SSH + [host, cmd], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build")
    b.add_argument("--repo", required=True)
    b.add_argument("--sha", required=True)
    b.add_argument("--overlay")
    b.add_argument("--scope", nargs="+", default=DEFAULT_SCOPE)
    b.add_argument("--out", required=True)
    b.add_argument("--die", default="")
    b.add_argument("--allow", default="", help="tool_skew_allow.json (a TOOLS-scope overlay entry needs a live entry there)")
    b.add_argument("--main-ref", default="origin/main", help="tools sha must be an ancestor of this ref ('' = no check)")
    b.add_argument("--rt-root", default="", help="require rt-root/<sha12>.manifest.json (the published rt tree of the pin)")
    pu = sp.add_parser("publish")
    pu.add_argument("tree")
    pu.add_argument("--pointer", default="")
    pu.add_argument("--retire-refs", nargs="*", default=None, help="after a clean publish, retire superseded _dN siblings (refs = files naming live trees)")
    v = sp.add_parser("verify")
    v.add_argument("tree")
    v.add_argument("--expect", default="")
    v.add_argument("--ro", action="store_true")
    v.add_argument("--full", action="store_true")
    cr = sp.add_parser("cached-receipt", help="reuse an exact completed verification plus current immutable metadata, no payload rehash")
    cr.add_argument("tree")
    cr.add_argument("--expect", default="")
    dm = sp.add_parser("delta-make", help="pack of the paths that differ between the tree's main sha and --sha (small)")
    dm.add_argument("tree")
    dm.add_argument("--repo", required=True)
    dm.add_argument("--sha", required=True)
    dm.add_argument("--out", required=True)
    dm.add_argument("--drop-overlay", nargs="*", default=[], help="overlay paths whose copy is an OLDER main version: main wins")
    dm.add_argument("--paths", nargs="*", default=None, help="restrict the pack to these paths inside the tree scope (e.g. tools physical/common_flow)")
    da = sp.add_parser("delta-apply", help="OUT = cp -a of TREE + the pack (run on each host, then publish)")
    da.add_argument("pack")
    da.add_argument("--old", required=True)
    da.add_argument("--out", required=True)
    da.add_argument("--link", action="store_true", help="STAGE A: hardlink unchanged files from --old (a D-step costs the delta); the new tree is verified before it is kept")
    da.add_argument("--expect", default="", help="manifest hash the composed tree must have (checked before the rename)")
    rt = sp.add_parser("retire", help="delete superseded <base>_dN siblings of TREE (older N), unless referenced or in use")
    rt.add_argument("tree")
    rt.add_argument("--refs", nargs="*", default=[], help="files that may name a tree (kit_wave.json, handoff markers): a named tree is kept")
    rt.add_argument("--keep", type=int, default=0)
    rt.add_argument("--dry", action="store_true")
    lk = sp.add_parser("links", help="stat-only: fail when any file of TREE has another hardlink (a published tree must be unshared)")
    lk.add_argument("tree")
    lk.add_argument("--find-in", nargs="*", default=[], help="dirs to search for the other names (slow)")
    h = sp.add_parser("hosts")
    h.add_argument("tree")
    h.add_argument("--hosts", required=True)
    h.add_argument("--expect", default="")
    h.add_argument("--links-only", action="store_true", help="per host: stat-only shared-inode check instead of the full hash verify")
    h.add_argument("--cached-receipts", action="store_true", help="per host: exact completed verification receipt, fail on cache miss")
    r = sp.add_parser("replicate")
    r.add_argument("tree")
    r.add_argument("--hosts", required=True)
    r.add_argument("--link-from", default="", help="basename of an earlier published tree of the same die: on each target that holds it, unchanged files are hardlinked from it (--link-dest), "
                                                   "so the copy costs the delta; the target's .link-base names it (verify accepts exactly those shared inodes)")
    d = sp.add_parser("derive")
    d.add_argument("live")
    d.add_argument("--repo", required=True)
    d.add_argument("--sha", required=True)
    d.add_argument("--scope", nargs="+", default=DEFAULT_SCOPE)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        m = build(a.repo, a.sha, a.overlay, a.scope, a.out, a.die, a.allow, a.main_ref, a.rt_root)
        print(f"SRC_MANIFEST BUILT {a.out} main {m['main_sha'][:12]} overlay {len(m['overlay'])} files {len(m['files'])} hash {m['manifest_hash']}")
    elif a.cmd == "publish":
        info = publish(a.tree, a.pointer)
        if a.retire_refs is not None:
            retire(a.tree, a.retire_refs)
        print(f"SRC_MANIFEST PUBLISHED {a.tree} read-only hash {info['manifest_hash']}" + (f" pointer {a.pointer}" if a.pointer else ""))
    elif a.cmd == "verify":
        errs, info = verify(a.tree, a.expect, a.ro, a.full)
        if errs:
            report(errs)
            return 1
        print(f"SRC_MANIFEST OK {info['manifest_hash']} main {str(info.get('main_sha'))[:12]} files {info.get('files')}")
    elif a.cmd == "cached-receipt":
        errs, info = cached_receipt(a.tree, a.expect)
        if errs:
            report(errs)
            return 1
        print(json.dumps(info, sort_keys=True))
    elif a.cmd == "delta-make":
        n, dl = delta_make(a.repo, os.path.abspath(a.tree), a.sha, a.out, a.drop_overlay, a.paths)
        print(f"SRC_MANIFEST DELTA {a.out}: {n} changed/added, {dl} deleted")
    elif a.cmd == "delta-apply":
        nm = delta_apply(a.pack, os.path.abspath(a.old), a.out, a.link, a.expect)
        print(f"SRC_MANIFEST DELTA-APPLIED {a.out} main {nm['main_sha'][:12]} hash {nm['manifest_hash']} (run publish next)")
    elif a.cmd == "retire":
        retire(os.path.abspath(a.tree), a.refs, a.keep, a.dry)
    elif a.cmd == "links":
        errs, n = links_report(os.path.abspath(a.tree), a.find_in)
        if errs:
            report(errs)
            return 1
        print(f"SRC_MANIFEST LINKS OK {a.tree}: no file shared with another path")
    elif a.cmd == "hosts":
        bad = 0
        for host in a.hosts.split(","):
            if a.cached_receipts:
                script = open(os.path.abspath(__file__)).read()
                cmd = f"python3 -I -c {shlex.quote(script)} cached-receipt {shlex.quote(os.path.abspath(a.tree))}"
                if a.expect:
                    cmd += " --expect " + shlex.quote(a.expect)
                p = subprocess.run(SSH + [host, cmd], capture_output=True, text=True)
                txt = (p.stdout + p.stderr).strip()
                print(f"{host}: " + (txt.splitlines()[-1] if p.returncode == 0 and txt else txt[:2000]))
                bad |= bool(p.returncode)
                continue
            if a.links_only:
                script = open(os.path.abspath(__file__)).read()
                p = subprocess.run(SSH + [host, f"python3 -I -c {shlex.quote(script)} links {shlex.quote(os.path.abspath(a.tree))}"],
                                   capture_output=True, text=True)
                txt = (p.stdout + p.stderr).strip()
                print(f"{host}: " + (txt.splitlines()[-1] if p.returncode == 0 and txt else txt[:1500]))
                bad |= bool(p.returncode)
                continue
            rc, txt = remote_verify(host, os.path.abspath(a.tree), a.expect)
            print(f"{host}: " + (txt.splitlines()[-1] if rc == 0 and txt else txt[:2000]))
            bad |= bool(rc)
        return 1 if bad else 0
    elif a.cmd == "replicate":
        tree = os.path.abspath(a.tree).rstrip("/")
        m = load_manifest(tree)
        if not m:
            raise SystemExit("not a manifest tree")
        bad = 0
        size = tree_gb(tree)
        for host in a.hosts.split(","):
            part = f"{tree}.part"
            free, have = remote_free_gb(host, os.path.dirname(tree), part)
            if free is None:
                print(f"{host}: refuse (cannot read the target's free space)"); bad = 1; continue
            lk = bool(a.link_from) and subprocess.run(SSH + [host, f"test -d {shlex.quote(os.path.join(os.path.dirname(tree), a.link_from))}"]).returncode == 0
            ok, after = room_after_copy(free, min(size, 8.0) if lk else size, have, max(REPL_FLOOR_GB, int(os.environ.get("OT_REPL_FLOOR_GB", REPL_FLOOR_GB))))   # a linked copy is budgeted at <= 8 GB
            if not ok:
                print(f"{host}: refuse (free {free:.0f} GB + part {have:.0f} - tree {size:.0f} = {after:.0f} GB after the copy < floor {REPL_FLOOR_GB} + {REPL_MARGIN_GB} GB)")
                bad = 1
                continue
            # a stale .part of an earlier copy is read-only: directories get u+w first (never the files), then it goes
            if subprocess.run(SSH + [host, f"test ! -e {shlex.quote(tree)} && {{ [ ! -d {shlex.quote(part)} ] || find {shlex.quote(part)} -type d -exec chmod u+w {{}} + ; }} && rm -rf {shlex.quote(part)} && mkdir -p {shlex.quote(os.path.dirname(tree))}"]).returncode:
                print(f"{host}: refuse (target exists or not writable)")
                bad = 1
                continue
            linkdir = ""
            if a.link_from:
                cand = os.path.join(os.path.dirname(tree), a.link_from)
                if subprocess.run(SSH + [host, f"test -f {shlex.quote(cand)}/{MANIFEST} && test -d {shlex.quote(cand)}"]).returncode == 0:
                    linkdir = cand
            # the source's own .link-base (it may itself be a link replica, D4 -> M5 -> M5T) names a base on the SOURCE host and is read-only:
            # never copy it; the target gets a fresh one naming its own base, written by copy+mv (11-17: the copied file made the write fail)
            rs = subprocess.run(["rsync", "-a", "--exclude=/" + LINKBASE, *([f"--link-dest={linkdir}/"] if linkdir else []), "-e",
                                 RSYNC_SSH, tree + "/", f"{host}:{part}/"])
            if rs.returncode == 0 and linkdir:
                lw = subprocess.run(SSH + [host, f"cd {shlex.quote(part)} && chmod u+w . && readlink -f {shlex.quote(linkdir)} > {LINKBASE}.tmp && "
                                                 f"chmod a-w {LINKBASE}.tmp && mv -f {LINKBASE}.tmp {LINKBASE} && chmod a-w ."])
                print(f"{host}: linked from {os.path.basename(linkdir)}" + ("" if lw.returncode == 0 else " (.link-base write FAILED)"))
            rc, txt = remote_verify(host, part, m["manifest_hash"], ro=True) if rs.returncode == 0 else (1, "rsync failed")
            if rc == 0:
                rc = subprocess.run(SSH + [host, f"mv -T {shlex.quote(part)} {shlex.quote(tree)}"]).returncode
            print(f"{host}: " + ("OK" if rc == 0 else txt[:1500]))
            bad |= bool(rc)
        return 1 if bad else 0
    elif a.cmd == "derive":
        print(json.dumps(derive(a.live, a.repo, a.sha, a.scope), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
