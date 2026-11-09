#!/usr/bin/env python3
"""ot-srcdedupe: hard-link byte-identical git-tracked files across source trees on one filesystem (STORE-1, 2026-11-08).

Each lane or kit-wave src_* tree holding a full checkout is about 46 GB, mostly the same blobs.  A tree stays a real
directory at the same path, so the absolute paths that kits, bind.f and PROVENANCE name keep working and no reader changes.

Dry run is the default.  --apply needs --manifest; the manifest is written before the first link.  A tree is used only when
it is the real path (no symlink component), has no process cwd in it, and no file newer than --min-idle-h.  A file joins a
group only when it is clean against its index (size and mtime); before linking the two files are compared byte for byte.
The kept inode is made read-only, so an in-place write through any link fails.  Files with different exec bits never share.
Never reads or writes .git: indexes are parsed from their files, so no lane's git state is refreshed.
"""
import argparse
import collections
import filecmp
import json
import os
import stat
import struct
import sys
import time

MAX_NLINK = 60000            # ext4 limit is 65000
GB = 1e9
TMP = ".ot-srcdedupe-tmp"


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


def live_cwds():
    out = set()
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                out.add(os.readlink(f"/proc/{pid}/cwd"))
            except OSError:
                pass
    return out


def refusal(tree, cwds, min_idle_h, now):
    """why a tree is not used, None when it is fine"""
    if os.path.realpath(tree) != tree:
        return "symlink"
    if os.path.lexists(tree + "/.ot-srcdedupe-skip"):
        return "skip-marker"
    if any(c == tree or c.startswith(tree + "/") for c in cwds):
        return "live-cwd"
    if min_idle_h > 0:
        limit = now - min_idle_h * 3600
        for dp, dn, fn in os.walk(tree):
            if ".git" in dn:
                dn.remove(".git")
            for f in fn:
                try:
                    if os.lstat(os.path.join(dp, f)).st_mtime > limit:
                        return "recent"
                except OSError:
                    pass
    return None


def collect(trees, min_size, min_idle_h, now, log):
    """{(dev, sha, xbit, size): [(path, ino, nlink, mtime)]}, {tree: refusal}"""
    cwds, groups, refused = live_cwds(), collections.defaultdict(list), {}
    for t in trees:
        why = refusal(t, cwds, min_idle_h, now)
        idx = None if why else (parse_index(index_file(t) or "") if index_file(t) else None)
        if why or idx is None:
            refused[t] = why or "no-index"
            continue
        n = 0
        for rel, (size, mt, sha, mode) in idx.items():
            if size < min_size or mode >> 12 != 0o10:
                continue
            p = os.path.join(t.encode(), rel)
            try:
                s = os.lstat(p)
            except OSError:
                continue
            if not stat.S_ISREG(s.st_mode) or s.st_size != size or int(s.st_mtime) != mt:
                continue                 # dirty or stat-mismatched against the index
            groups[(s.st_dev, sha, bool(mode & 0o111), size)].append((p, s.st_ino, s.st_nlink, s.st_mtime))
            n += 1
        log(f"{t}: {n} clean candidates")
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


def apply_rows(rows, chmod_dirs, log):
    done, skipped = 0, collections.Counter()
    tmp = f"{TMP}.{os.getpid()}"
    for dev, sha, size, canon, path, ino in rows:
        try:
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trees", required=True, help="file: one tree per line, or a STORE-1 scan JSON")
    ap.add_argument("--apply", action="store_true", help="make the links; without it nothing changes")
    ap.add_argument("--manifest", help="TSV written before any link (required with --apply)")
    ap.add_argument("--min-idle-h", type=float, default=6.0)
    ap.add_argument("--min-size", type=int, default=4096)
    ap.add_argument("--chmod-dirs", action="store_true", help="briefly add u+w to a read-only directory to link in it")
    a = ap.parse_args(argv)
    if a.apply and not a.manifest:
        ap.error("--apply needs --manifest")

    def log(*x):
        print(time.strftime("%H:%M:%S"), *x, flush=True)

    trees = load_trees(a.trees)
    groups, refused = collect(trees, a.min_size, a.min_idle_h, time.time(), log)
    rows, per_fs, kept_out = plan(groups, MAX_NLINK)
    for t, why in sorted(refused.items()):
        log("REFUSED", why, t)
    if a.manifest:
        with open(a.manifest + ".tmp", "w") as m:
            m.write("#dev\tblob\tsize\tkept\treplaced\told_ino\n")
            for dev, sha, size, canon, p, ino in rows:
                m.write(f"{dev}\t{sha}\t{size}\t{os.fsdecode(canon)}\t{os.fsdecode(p)}\t{ino}\n")
        os.replace(a.manifest + ".tmp", a.manifest)
    res = dict(trees=len(trees), refused=len(refused), rows=len(rows),
               gb_by_dev={str(d): round(v / GB, 2) for d, v in per_fs.items()},
               gb_linked_elsewhere={str(d): round(v / GB, 2) for d, v in kept_out.items()}, applied=0)
    if a.apply:
        res["applied"], sk = apply_rows(rows, a.chmod_dirs, log)
        res["skipped"] = dict(sk)
    print(json.dumps(res), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
