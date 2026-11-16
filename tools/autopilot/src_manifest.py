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
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

MANIFEST = ".src-manifest.json"
HASHFILE = ".src-manifest.sha256"
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
            if rel in (MANIFEST, HASHFILE) or skipped(rel):
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
    for rel in sorted(want):
        p = have.get(rel)
        if p is None:
            errs.append(f"SRC_MANIFEST DRIFT {rel} (missing)")
        elif tree_hash(p) != want[rel]:
            errs.append(f"SRC_MANIFEST DRIFT {rel} (modified: not the manifest content)")
        elif ro and writable(p):
            errs.append(f"SRC_MANIFEST DRIFT {rel} (writable: published trees are read-only)")
        elif ro and not os.path.islink(p) and os.lstat(p).st_nlink > 1:
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


def shared_inodes(root, limit=0):
    """stat-only scan (no hashing: cheap enough for every tick): [(relpath, nlink)] of every regular file with nlink > 1, i.e. a file
    another path (a `cp -al` copy in some lane's tree) can change.  A published tree must have none (TOOLS-CONVERGE-1116, 2nd
    occurrence: S81 cmp_B6gF2s, HEAD fable-fix-head-serdes/tree5)."""
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and st.st_nlink > 1:
                out.append((os.path.relpath(p, root), st.st_nlink))
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
            if not os.path.islink(p):
                os.chmod(p, os.lstat(p).st_mode & ~0o222)
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


# ---- hosts ----------------------------------------------------------------------------------------------------------

SSH = ["timeout", "900", "ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20"]


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
    v = sp.add_parser("verify")
    v.add_argument("tree")
    v.add_argument("--expect", default="")
    v.add_argument("--ro", action="store_true")
    v.add_argument("--full", action="store_true")
    lk = sp.add_parser("links", help="stat-only: fail when any file of TREE has another hardlink (a published tree must be unshared)")
    lk.add_argument("tree")
    lk.add_argument("--find-in", nargs="*", default=[], help="dirs to search for the other names (slow)")
    h = sp.add_parser("hosts")
    h.add_argument("tree")
    h.add_argument("--hosts", required=True)
    h.add_argument("--expect", default="")
    h.add_argument("--links-only", action="store_true", help="per host: stat-only shared-inode check instead of the full hash verify")
    r = sp.add_parser("replicate")
    r.add_argument("tree")
    r.add_argument("--hosts", required=True)
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
        print(f"SRC_MANIFEST PUBLISHED {a.tree} read-only hash {info['manifest_hash']}" + (f" pointer {a.pointer}" if a.pointer else ""))
    elif a.cmd == "verify":
        errs, info = verify(a.tree, a.expect, a.ro, a.full)
        if errs:
            report(errs)
            return 1
        print(f"SRC_MANIFEST OK {info['manifest_hash']} main {str(info.get('main_sha'))[:12]} files {info.get('files')}")
    elif a.cmd == "links":
        errs, n = links_report(os.path.abspath(a.tree), a.find_in)
        if errs:
            report(errs)
            return 1
        print(f"SRC_MANIFEST LINKS OK {a.tree}: no file shared with another path")
    elif a.cmd == "hosts":
        bad = 0
        for host in a.hosts.split(","):
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
        for host in a.hosts.split(","):
            part = f"{tree}.part"
            if subprocess.run(SSH + [host, f"test ! -e {shlex.quote(tree)} && rm -rf {shlex.quote(part)} && mkdir -p {shlex.quote(os.path.dirname(tree))}"]).returncode:
                print(f"{host}: refuse (target exists or not writable)")
                bad = 1
                continue
            rs = subprocess.run(["rsync", "-a", "-e",
                                 "ssh -o BatchMode=yes -o ControlPath=none", tree + "/", f"{host}:{part}/"])
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
