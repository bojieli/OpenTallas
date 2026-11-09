#!/usr/bin/env python3
"""ot-srcdedupe: hard-link byte-identical git-tracked files across source trees on one filesystem (STORE-1, 2026-11-08).

Each lane or kit-wave src_* tree holding a full checkout is about 46 GB, mostly the same blobs.  A tree stays a real
directory at the same path, so the absolute paths that kits, bind.f and PROVENANCE name keep working and no reader changes.

Dry run is the default.  --apply needs --manifest; the manifest is written before the first link.  A tree is used only when
it is the real path (no symlink component), has no process cwd in it, and no file newer than --min-idle-h.  A file joins a
group only when it is clean against its index (size and mtime); before linking the two files are compared byte for byte.
The kept inode is made read-only, so an in-place write through any link fails for a non-root writer.  Root in a container
ignores mode bits (tested 11-08), so a tree that any container mounts, or that has a kit or run under it, is refused, and
--verify re-hashes a sample of kept files against the manifest to detect a write that got through.  Files with different
exec bits never share.  Never reads or writes .git: indexes are parsed from their files, so no lane's git state is refreshed.
"""
import argparse
import collections
import filecmp
import hashlib
import json
import os
import random
import re
import stat
import struct
import subprocess
import sys
import time

MAX_NLINK = 60000            # ext4 limit is 65000
GB = 1e9
TMP = ".ot-srcdedupe-tmp"
RECORD_NAMES = {"signoff.json", "PROVENANCE.json", "ARCHIVED.json", "AUTOPILOT.json"}   # never linked, whatever the guards say
KIT_DIRS = {"kits", "kit-wave", "items"}
WAVE_SRC = re.compile(r"/claude/(?:[^/]*(?:kw\d|kw-|wave)[^/]*)/(?:.*/)?src[^/]*$")     # kit-wave and lane staged src trees
LANE_PARTS = 4               # /srv/<scratch>/claude/<lane>: a mention at or below lane level holds the trees under it


def parse_index(path):
    """{relative path bytes: (size, mtime_s, blob sha, mode)} of a git index v2/3/4, None when unreadable"""
    try:
        with open(path, "rb") as f:
            d = f.read()
    except OSError:
        return None
    if d[:4] != b"DIRC":
        return None
    ver, n = struct.unpack(">II", d[4:12])
    if ver not in (2, 3, 4):
        return None
    pos, out, prev = 12, {}, b""
    for _ in range(n):
        f = struct.unpack(">10I", d[pos:pos + 40])
        mt_s, mode, size = f[2], f[6], f[9]
        sha = d[pos + 40:pos + 60]
        flags = struct.unpack(">H", d[pos + 60:pos + 62])[0]
        q = pos + 62
        if ver >= 3 and flags & 0x4000:
            q += 2
        if ver == 4:
            c = d[q]; q += 1; k = c & 0x7f
            while c & 0x80:
                k += 1; c = d[q]; q += 1; k = (k << 7) + (c & 0x7f)
            e = d.index(b"\0", q)
            name = prev[:len(prev) - k] + d[q:e]
            prev, pos = name, e + 1
        else:
            nl = flags & 0xfff
            e = q + nl if nl < 0xfff else d.index(b"\0", q)
            name = d[q:e]
            pos += (e - pos + 1 + 7) // 8 * 8
        if not flags & 0x3000:       # skip merge-stage entries
            out[name] = (size, mt_s, sha, mode)
    return out


def index_file(tree):
    p = tree + "/.git"
    try:
        if stat.S_ISDIR(os.lstat(p).st_mode):
            return p + "/index"
        c = open(p).read().strip()
    except OSError:
        return None
    if not c.startswith("gitdir:"):
        return None
    gd = c.split(":", 1)[1].strip()
    return (gd if gd.startswith("/") else os.path.normpath(tree + "/" + gd)) + "/index"


def live_paths():
    """every path a process of ours holds: cwd, root, open fds, absolute argv words"""
    out = set()
    me = str(os.getpid())        # our own argv names the control tree through --only-tree
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or pid == me:
            continue
        for link in ("cwd", "root"):
            try:
                out.add(os.readlink(f"/proc/{pid}/{link}"))
            except OSError:
                pass
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                try:
                    out.add(os.readlink(f"/proc/{pid}/fd/{fd}"))
                except OSError:
                    pass
        except OSError:
            pass
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                out.update(w.decode("utf-8", "replace") for w in f.read().split(b"\0") if w.startswith(b"/"))
        except OSError:
            pass
    return {p for p in out if p.startswith("/")}


def container_mounts():
    """source paths of every container mount on this host; None when docker cannot be asked (the caller refuses all)"""
    try:
        ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=120, check=True).stdout.split()
        if not ids:
            return set()
        o = subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True, timeout=300, check=True).stdout
        return {m["Source"] for c in json.loads(o) for m in c.get("Mounts", []) if m.get("Source")}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def ancestors(p):
    while p and p != "/":
        yield p
        p = os.path.dirname(p)


def hits(paths, trees):
    """trees that hold one of the paths (the path at or below the tree)"""
    out = set()
    for p in paths:
        for q in ancestors(p):
            if q in trees:
                out.add(q)
    return out


def lane_held(mentions, trees):
    """trees below a mentioned path that is at or below lane level"""
    m = {p for p in mentions if len([x for x in p.split("/") if x]) >= LANE_PARTS}
    return {t for t in trees if any(q in m for q in ancestors(t))}


def git_locked(tree):
    idx = index_file(tree)
    if not idx:
        return False
    gd = os.path.dirname(idx)
    try:
        names = os.listdir(gd)
    except OSError:
        return False
    return "locked" in names or any(n.endswith(".lock") for n in names)


def kit_shaped(dn, fn, dp):
    """a directory holding kit or run output: kits/items/kit-wave dirs, a run dir with results or logs, or an .odb"""
    if KIT_DIRS & set(dn) or any(f.endswith(".odb") for f in fn):
        return True
    return "run" in dn and any(os.path.isdir(os.path.join(dp, "run", x)) for x in ("results", "logs"))


def refusal(tree, live, mounted, mentioned, min_idle_h, now):
    """why a tree is not used, None when it is fine"""
    if os.path.realpath(tree) != tree:
        return "symlink"
    if os.path.lexists(tree + "/.ot-srcdedupe-skip"):
        return "skip-marker"
    if tree in live:
        return "live-process"
    if tree in mounted:
        return "container-mount"
    if tree in mentioned:
        return "mentioned"
    if WAVE_SRC.search(tree):
        return "wave-src"
    if git_locked(tree):
        return "git-lock"
    limit = now - min_idle_h * 3600
    for dp, dn, fn in os.walk(tree):
        if ".git" in dn:
            dn.remove(".git")
        if kit_shaped(dn, fn, dp):
            return "kit-or-run"
        if min_idle_h > 0:
            for f in fn:
                try:
                    if os.lstat(os.path.join(dp, f)).st_mtime > limit:
                        return "recent"
                except OSError:
                    pass
    return None


def load_paths(files):
    """absolute paths from text files: one per line, or the second TAB column of a PROTECTED union"""
    out = set()
    for f in files or []:
        with open(f, errors="replace") as fh:
            for ln in fh:
                if ln.startswith("#") or not ln.strip():
                    continue
                c = ln.rstrip("\n").split("\t")
                p = c[1] if len(c) > 1 and c[1].startswith("/") else c[0].strip()
                if p.startswith("/"):
                    out.add(os.path.normpath(p))
    return out


class Excluded:
    """is a path at or below an excluded path; directory answers are cached"""

    def __init__(self, paths):
        self.paths, self.dirs = paths, {}

    def _dir(self, d):
        hit = self.dirs.get(d)
        if hit is None:
            hit = d in self.paths or (d not in ("/", "") and self._dir(os.path.dirname(d)))
            self.dirs[d] = hit
        return hit

    def __call__(self, p):
        return p in self.paths or self._dir(os.path.dirname(p))


def collect(trees, min_size, min_idle_h, now, log, exclude=frozenset(), mentions=frozenset()):
    """{(dev, sha, xbit, size): [(path, ino, nlink, mtime)]}, {tree: refusal}"""
    tset, groups, refused = set(trees), collections.defaultdict(list), {}
    mounts = container_mounts()
    if mounts is None:
        return groups, {t: "docker-unreadable" for t in trees}
    mounted = hits(mounts, tset) | {t for t in tset if any(q in mounts for q in ancestors(t))}
    live, mentioned = hits(live_paths(), tset), hits(mentions, tset) | lane_held(mentions, tset)
    excl = Excluded(exclude)
    dropped = 0
    for t in trees:
        why = refusal(t, live, mounted, mentioned, min_idle_h, now)
        idx = None if why else (parse_index(index_file(t) or "") if index_file(t) else None)
        if why or idx is None:
            refused[t] = why or "no-index"
            continue
        n = 0
        for rel, (size, mt, sha, mode) in idx.items():
            if size < min_size or mode >> 12 != 0o10:
                continue
            base = rel.rsplit(b"/", 1)[-1].decode("utf-8", "surrogateescape")
            if base in RECORD_NAMES or base.endswith(".signoff.json"):
                continue
            p = os.path.join(t.encode(), rel)
            if excl(os.fsdecode(p)):
                dropped += 1
                continue
            try:
                s = os.lstat(p)
            except OSError:
                continue
            if not stat.S_ISREG(s.st_mode) or s.st_size != size or int(s.st_mtime) != mt:
                continue                 # dirty or stat-mismatched against the index
            groups[(s.st_dev, sha, bool(mode & 0o111), size)].append((p, s.st_ino, s.st_nlink, s.st_mtime))
            n += 1
        log(f"{t}: {n} clean candidates")
    log(f"excluded files: {dropped}")
    return groups, refused


def plan(groups, max_nlink):
    """rows [(dev, sha, size, canon path, path, old ino)] and bytes freed per device; the most-linked oldest inode is kept.
    An old inode frees its bytes only when every one of its links is replaced; links outside the given trees keep it."""
    rows, per_fs, kept_out = [], collections.Counter(), collections.Counter()
    for (dev, sha, xbit, size), ents in groups.items():
        inos = {e[1] for e in ents}
        if len(inos) < 2:
            continue
        canon = min(ents, key=lambda e: (-e[2], e[3], e[0]))
        canon_links = canon[2]
        replaced, nlink = collections.Counter(), {}
        for p, ino, nl, mt in ents:
            if ino == canon[1]:
                continue
            canon_links += 1
            if canon_links >= max_nlink:
                break
            rows.append((dev, sha.hex(), size, canon[0], p, ino))
            replaced[ino] += 1
            nlink[ino] = nl
        for ino, n in replaced.items():
            (per_fs if n == nlink[ino] else kept_out)[dev] += size
    return rows, per_fs, kept_out


def blob_sha(path):
    """git blob sha1 of a file, hashed from its bytes"""
    h = hashlib.sha1(b"blob %d\0" % os.lstat(path).st_size)
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def apply_rows(rows, chmod_dirs, log):
    done, skipped = 0, collections.Counter()
    tmp = f"{TMP}.{os.getpid()}"
    kept_ok = {}
    for dev, sha, size, canon, path, ino in rows:
        try:
            if canon not in kept_ok:
                kept_ok[canon] = blob_sha(canon) == sha
            if not kept_ok[canon]:
                skipped["kept-sha-mismatch"] += 1
                continue
            c = os.lstat(canon)
            s = os.lstat(path)
            if s.st_ino != ino or s.st_size != size or c.st_size != size or s.st_dev != c.st_dev:
                skipped["changed"] += 1
                continue
            if c.st_nlink >= MAX_NLINK:
                skipped["nlink"] += 1
                continue
            if not filecmp.cmp(canon, path, shallow=False):
                skipped["bytes-differ"] += 1
                continue
            d = os.path.dirname(path)
            mode = None
            if not os.access(d, os.W_OK):
                if not chmod_dirs:
                    skipped["dir-readonly"] += 1
                    continue
                mode = stat.S_IMODE(os.lstat(d).st_mode)
                os.chmod(d, mode | 0o200)
            try:
                if c.st_mode & 0o222:
                    os.chmod(canon, stat.S_IMODE(c.st_mode) & ~0o222)
                t = os.path.join(d, tmp.encode())
                os.link(canon, t)
                os.rename(t, path)
            finally:
                if mode is not None:
                    os.chmod(d, mode)
            done += 1
        except OSError as e:
            skipped[type(e).__name__] += 1
            log(f"ERROR {path!r}: {e}")
    return done, skipped


def load_trees(p):
    txt = open(p).read()
    if txt.lstrip().startswith("{"):
        d = json.loads(txt)
        return [r["tree"] for r in d.get("trees", []) if not r.get("unscanned")]
    return [l.strip() for l in txt.splitlines() if l.strip() and not l.startswith("#")]


def verify(manifests, sample, max_gb, alert_file, log):
    """re-hash a random sample of kept files against the manifests' blob shas; a mismatch is a write through a link"""
    pick, seen = [], 0
    for m in manifests:
        with open(m, errors="surrogateescape") as fh:
            for ln in fh:
                if ln.startswith("#"):
                    continue
                seen += 1
                if len(pick) < sample:
                    pick.append(ln)
                else:
                    j = random.randrange(seen)
                    if j < sample:
                        pick[j] = ln
    done, gone, bad, got, limit = 0, 0, [], set(), max_gb * GB
    for ln in pick:
        _, sha, size, kept, _p, _ino = ln.rstrip("\n").split("\t")
        if kept in got or limit < int(size):
            continue
        got.add(kept)
        try:
            real = blob_sha(os.fsencode(kept))
        except OSError:
            gone += 1                    # the tree went away by a legal delete; nothing to compare
            continue
        limit -= int(size)
        done += 1
        if real != sha:
            bad.append(f"{kept}\tmanifest {sha}\tnow {real}")
    res = dict(rows=seen, sampled=done, gone=gone, mismatches=len(bad))
    if bad:
        msg = (f"{time.strftime('%F %T %Z')} ot-srcdedupe ALERT on {os.uname().nodename}: {len(bad)} kept file(s) changed "
               "after linking; a write reached every tree sharing the inode.\n" + "\n".join(bad) + "\n")
        sys.stderr.write(msg)
        if alert_file:
            with open(alert_file, "a") as f:
                f.write(msg)
    log(json.dumps(res))
    return 3 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trees", help="file: one tree per line, or a STORE-1 scan JSON")
    ap.add_argument("--apply", action="store_true", help="make the links; without it nothing changes")
    ap.add_argument("--manifest", help="TSV written before any link (required with --apply)")
    ap.add_argument("--min-idle-h", type=float, default=6.0)
    ap.add_argument("--min-size", type=int, default=4096)
    ap.add_argument("--chmod-dirs", action="store_true", help="briefly add u+w to a read-only directory to link in it")
    ap.add_argument("--exclude", action="append", help="file of paths (or a PROTECTED union): files at or below one are never touched")
    ap.add_argument("--mentions", action="append", help="file of paths named by the queue or kit-wave: the trees they fall in are refused")
    ap.add_argument("--only-tree", help="link only rows that replace a file in this tree (control tree)")
    ap.add_argument("--verify", nargs="+", metavar="MANIFEST", help="re-hash a sample of kept files; exit 3 on any mismatch")
    ap.add_argument("--sample", type=int, default=500)
    ap.add_argument("--max-gb", type=float, default=5.0, help="bytes hashed by one --verify")
    ap.add_argument("--alert-file", help="--verify appends mismatches here")
    a = ap.parse_args(argv)

    def log(*x):
        print(time.strftime("%H:%M:%S"), *x, flush=True)

    if a.verify:
        return verify(a.verify, a.sample, a.max_gb, a.alert_file, log)
    if not a.trees:
        ap.error("--trees is required")
    if a.apply and not a.manifest:
        ap.error("--apply needs --manifest")
    trees = load_trees(a.trees)
    groups, refused = collect(trees, a.min_size, a.min_idle_h, time.time(), log, load_paths(a.exclude), load_paths(a.mentions))
    rows, per_fs, kept_out = plan(groups, MAX_NLINK)
    if a.only_tree:
        prefix = a.only_tree.rstrip("/").encode() + b"/"
        rows = [r for r in rows if r[4].startswith(prefix)]
    for t, why in sorted(refused.items()):
        log("REFUSED", why, t)
    if a.manifest:
        with open(a.manifest + ".tmp", "w", errors="surrogateescape") as m:
            m.write("#dev\tblob\tsize\tkept\treplaced\told_ino\n")
            for dev, sha, size, canon, p, ino in rows:
                m.write(f"{dev}\t{sha}\t{size}\t{os.fsdecode(canon)}\t{os.fsdecode(p)}\t{ino}\n")
        os.replace(a.manifest + ".tmp", a.manifest)
    res = dict(trees=len(trees), refused=len(refused), refused_by=dict(collections.Counter(refused.values())), rows=len(rows),
               gb_by_dev={str(d): round(v / GB, 2) for d, v in per_fs.items()},
               gb_linked_elsewhere={str(d): round(v / GB, 2) for d, v in kept_out.items()}, applied=0)
    if a.apply:
        res["applied"], sk = apply_rows(rows, a.chmod_dirs, log)
        res["skipped"] = dict(sk)
    print(json.dumps(res), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
