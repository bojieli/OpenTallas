#!/usr/bin/env python3
"""delete_manifest.py -- a per-file record of every tree ot-delete / ot-auto-retire removes (FLOW-OPS-0900, COORD 11-21, FLEET-WATCH-R7 4524dcc726).

Why: on 11-18 ot-auto-retire on epyc2 removed fable-pd-head-clk (it held ca2/ring_declared.json, later a HEAD bind input) and 126 other idle trees
under the owner-approved aggressive cleanup, and no file list was kept, so the lost input could not be named or restored from a sister copy.

Before a tree is removed, write(tree, tool) stores one gzip JSON-lines file
    ~/.local/state/delete-manifests/<YYYY-MM-DD>/<HHMMSS>-<tool>-<tree as name>.jsonl.gz
line 1: {"schema", "tree", "tool", "host", "lane", "time", "realpath"}; then one line per entry, paths relative to the tree:
    {"p": rel, "size": bytes, "sha256": hex}          a regular file under 50 MB (OT_DELETE_MANIFEST_SHA_MAX_MB)
    {"p": rel, "size": bytes, "sha256": null, "why": "large" | "budget" | "unreadable"}
    {"p": rel, "link": target}                        a symlink (never followed)
last line: {"end": true, "files": n, "bytes": total, "hashed": n, "truncated": bool}
Hashing stops after OT_DELETE_MANIFEST_HASH_S seconds (default 900) per tree; the rest is still listed with size.
This is a record only: it never refuses, never raises, and a failure to write it never changes what is deleted (owner: no new restrictive rule).
OT_DELETE_MANIFEST_DIR overrides the directory; without it, trees outside /srv are not recorded (test temp dirs).
INPUT TARBALL (FLOW-OPS-1000, FABLE-FLOW-1000 h): the BYTES of the small generated inputs go with the record, so a lane file a later plan step reads
(ring_declared.json) can be restored: every regular file of an input kind (INPUT_EXT: json tsv tcl sdc py sv v vh md sh mk txt yaml cfg csv) under
OT_DELETE_INPUT_MAX_MB (default 5) is packed into <manifest stem>.inputs.tar.gz beside the manifest, up to OT_DELETE_INPUT_TOTAL_MB (200) per tree and
inside the hash budget; the end line names it ("inputs_tar", "inputs_n").  Tool outputs (odb def spef gds log) are never packed.  Restore:
tar -xzf <tarball> -C <tree>.  A record only, like the manifest: a failure to pack never changes what is deleted.
CLI: delete_manifest.py find PATH_SUBSTRING [DAYS]   -> manifest lines naming it (to find which deleted tree held a file)
     delete_manifest.py rotate [HOURS]                -> FLEET-OPS 11-25 (COORD: the dir grew 3.5 GB a day on the hub root): every day dir whose files are all older
     than HOURS (24) is packed into <root>/<day>.pack.tar.zst (zstd -19 --long, the .gz members stored decompressed so the near-identical input tarballs of
     a day dedupe: 4x on a measured day).  Nothing is dropped: the archive is read back and every member's sha256 checked before a source file is unlinked,
     one file at a time (never a tree delete).  find() reads the packs.  Restore: zstd -dc <day>.pack.tar.zst | tar -x   (members are the originals without .gz).
"""
import gzip
import hashlib
import json
import os
import re
import socket
import sys
import time

SCHEMA = "opentallas.delete_manifest/1"
INPUT_EXT = {".json", ".tsv", ".tcl", ".sdc", ".py", ".sv", ".v", ".vh", ".md", ".sh", ".mk", ".txt", ".yaml", ".yml", ".cfg", ".csv"}


def root_dir():
    return os.environ.get("OT_DELETE_MANIFEST_DIR") or os.path.expanduser("~/.local/state/delete-manifests")


def _sha(path, cap):
    h = hashlib.sha256()
    with open(path, "rb", buffering=0) as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write(tree, tool, sha_max_mb=None, budget_s=None, exclude=()):
    """-> manifest path, or None (not recorded / failed).  Never raises."""
    try:
        tree = os.path.abspath(tree)
        if not os.environ.get("OT_DELETE_MANIFEST_DIR") and not tree.startswith("/srv/"):
            return None
        sha_max = int(float(sha_max_mb if sha_max_mb is not None else os.environ.get("OT_DELETE_MANIFEST_SHA_MAX_MB", "50")) * 2**20)
        budget = float(budget_s if budget_s is not None else os.environ.get("OT_DELETE_MANIFEST_HASH_S", "900"))
        day, hms = time.strftime("%Y-%m-%d"), time.strftime("%H%M%S")
        d = os.path.join(root_dir(), day)
        os.makedirs(d, exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", tree.strip("/"))[-150:]
        out = os.path.join(d, f"{hms}-{re.sub(r'[^A-Za-z0-9_-]+', '_', tool)}-{name}.jsonl.gz")
        tmp = out + f".tmp{os.getpid()}"
        t0 = time.time()
        n = total = hashed = 0
        truncated = False
        in_max = int(float(os.environ.get("OT_DELETE_INPUT_MAX_MB", "5")) * 2**20)
        in_total = int(float(os.environ.get("OT_DELETE_INPUT_TOTAL_MB", "200")) * 2**20)
        small, small_b = [], 0
        with gzip.open(tmp, "wt") as fh:
            fh.write(json.dumps({"schema": SCHEMA, "tree": tree, "tool": tool, "host": socket.gethostname().split(".")[0],
                                 "lane": os.environ.get("OT_LANE", ""), "time": time.strftime("%F %T %Z"),
                                 "realpath": os.path.realpath(tree)}) + "\n")
            if os.path.islink(tree) or not os.path.isdir(tree):
                walk = [(os.path.dirname(tree), [], [os.path.basename(tree)])]
                base = os.path.dirname(tree)
            else:
                walk = os.walk(tree, followlinks=False)
                base = tree
            for dp, dns, fns in walk:
                rel_dp = os.path.relpath(dp, base)
                if rel_dp == "." and exclude:
                    dns[:] = [x for x in dns if x not in exclude]
                    fns = [x for x in fns if x not in exclude]
                for x in [x for x in dns if os.path.islink(os.path.join(dp, x))] + list(fns):
                    p = os.path.join(dp, x)
                    rel = os.path.normpath(os.path.join(rel_dp, x))
                    try:
                        if os.path.islink(p):
                            fh.write(json.dumps({"p": rel, "link": os.readlink(p)}) + "\n")
                            continue
                        st = os.lstat(p)
                    except OSError:
                        fh.write(json.dumps({"p": rel, "size": None, "sha256": None, "why": "unreadable"}) + "\n")
                        continue
                    n += 1
                    total += st.st_size
                    rec = {"p": rel, "size": st.st_size}
                    if (os.path.splitext(x)[1].lower() in INPUT_EXT and st.st_size <= in_max and small_b + st.st_size <= in_total
                            and __import__("stat").S_ISREG(st.st_mode)):
                        small.append((p, rel))
                        small_b += st.st_size
                    if st.st_size >= sha_max:
                        rec.update(sha256=None, why="large")
                    elif time.time() - t0 > budget:
                        rec.update(sha256=None, why="budget")
                        truncated = True
                    else:
                        try:
                            rec["sha256"] = _sha(p, sha_max)
                            hashed += 1
                        except OSError:
                            rec.update(sha256=None, why="unreadable")
                    fh.write(json.dumps(rec) + "\n")
            tar_path, tar_n = _pack_inputs(out, small, t0, budget)
            fh.write(json.dumps({"end": True, "files": n, "bytes": total, "hashed": hashed, "truncated": truncated,
                                 "inputs_tar": tar_path, "inputs_n": tar_n}) + "\n")
        os.replace(tmp, out)
        return out
    except Exception as e:                       # noqa: BLE001 - a record, never a stop
        print(f"delete_manifest: not written for {tree}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def _pack_inputs(out, small, t0, budget):
    """-> (tarball path or None, files packed): the small input files of the tree, inside what is left of the hash budget (+120 s)"""
    if not small:
        return None, 0
    import tarfile
    dst = out[:-len(".jsonl.gz")] + ".inputs.tar.gz"
    tmp = dst + f".tmp{os.getpid()}"
    k = 0
    try:
        with tarfile.open(tmp, "w:gz") as tf:
            for p, rel in small:
                if time.time() - t0 > budget + 120:
                    break
                try:
                    tf.add(p, arcname=rel, recursive=False)
                    k += 1
                except OSError:
                    continue
        os.replace(tmp, dst)
        return dst, k
    except Exception as e:                       # noqa: BLE001 - a record, never a stop
        print(f"delete_manifest: inputs not packed: {type(e).__name__}: {e}", file=sys.stderr)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None, 0


def _members(dd):
    """-> [(arcname, original file name, path)] of one day dir (.gz members are stored decompressed under the original name without .gz)"""
    out = []
    for f in sorted(os.listdir(dd)):
        q = os.path.join(dd, f)
        if os.path.isfile(q):
            out.append((os.path.basename(dd) + "/" + (f[:-3] if f.endswith(".gz") else f), f, q))
    return out


def _data(path):
    with (gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")) as fh:
        return fh.read()


def rotate(hours=24.0, root=None, now=None, level=12):
    """pack every day dir whose files are all older than HOURS into <day>.pack.tar.zst, streamed one member at a time (a day is GBs once decompressed),
    verified by a sha256 read-back, then unlink the originals one by one.  -> [(day, files, bytes_before, bytes_after)].  One bad day is left as it was."""
    import subprocess
    import tarfile
    import io
    r = root or root_dir()
    now = time.time() if now is None else now
    done = []
    try:
        days = sorted(d for d in os.listdir(r) if re.fullmatch(r"\d{4}-\d\d-\d\d", d) and os.path.isdir(os.path.join(r, d)))
    except OSError:
        return done
    for day in days:
        dd = os.path.join(r, day)
        pack = os.path.join(r, day + ".pack.tar.zst")
        tmp = pack + ".tmp"
        try:
            names = os.listdir(dd)
            if not names or os.path.exists(pack) or any(now - os.path.getmtime(os.path.join(dd, n)) < hours * 3600 for n in names):
                continue
            before = sum(os.path.getsize(os.path.join(dd, n)) for n in names)
            mem = _members(dd)
            want = {}
            with open(tmp, "wb") as out:
                z = subprocess.Popen(["zstd", "-q", f"-{level}", "--long=27", "-T2", "-c"], stdin=subprocess.PIPE, stdout=out)
                with tarfile.open(fileobj=z.stdin, mode="w|") as tf:
                    for arc, orig, q in mem:
                        data = _data(q)
                        ti = tarfile.TarInfo(arc)
                        ti.size, ti.mtime = len(data), int(os.path.getmtime(q))
                        tf.addfile(ti, io.BytesIO(data))
                        want[arc] = hashlib.sha256(data).hexdigest()
                z.stdin.close()
                if z.wait() != 0:
                    raise OSError("zstd failed")
            back = {}
            z = subprocess.Popen(["zstd", "-dc", "--long=27", tmp], stdout=subprocess.PIPE)
            with tarfile.open(fileobj=z.stdout, mode="r|") as tf:
                for ti in tf:
                    back[ti.name] = hashlib.sha256(tf.extractfile(ti).read()).hexdigest()
            if z.wait() != 0 or back != want:
                os.unlink(tmp)
                continue
            os.replace(tmp, pack)
            for _arc, orig, q in mem:
                os.unlink(q)
            if not os.listdir(dd):
                os.rmdir(dd)
            done.append((day, len(mem), before, os.path.getsize(pack)))
        except (OSError, ValueError, EOFError, subprocess.SubprocessError, tarfile.TarError):
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return done


def _find_packs(sub, r, cut):
    import subprocess
    import tarfile
    out = []
    for f in sorted(os.listdir(r), reverse=True):
        m = os.path.join(r, f)
        if not f.endswith(".pack.tar.zst") or os.path.getmtime(m) < cut:
            continue
        try:
            z = subprocess.Popen(["zstd", "-dc", "--long=27", m], stdout=subprocess.PIPE)
            with tarfile.open(fileobj=z.stdout, mode="r|") as tf:
                for ti in tf:
                    if not ti.name.endswith(".jsonl"):
                        continue
                    lines = tf.extractfile(ti).read().decode("utf8", "replace").splitlines()
                    head = json.loads(lines[0])
                    for ln in lines[1:]:
                        rec = json.loads(ln)
                        if "p" in rec and sub in os.path.join(head.get("tree", ""), rec["p"]):
                            out.append((m + ":" + ti.name, head.get("tree"), rec))
            z.wait()
        except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError):
            continue
    return out


def find(sub, days=30):
    """-> [(manifest, tree, line)] entries whose tree/relative path contains SUB, newest first"""
    out = []
    r = root_dir()
    cut = time.time() - days * 86400
    try:
        dirs = sorted(d for d in os.listdir(r) if os.path.isdir(os.path.join(r, d)))[::-1]
    except OSError:
        return out
    out.extend(_find_packs(sub, r, cut))
    for dd in dirs:
        for f in sorted(os.listdir(os.path.join(r, dd)), reverse=True):
            m = os.path.join(r, dd, f)
            if not f.endswith(".jsonl.gz") or os.path.getmtime(m) < cut:
                continue
            try:
                with gzip.open(m, "rt") as fh:
                    head = json.loads(fh.readline())
                    for ln in fh:
                        rec = json.loads(ln)
                        if "p" in rec and sub in os.path.join(head.get("tree", ""), rec["p"]):
                            out.append((m, head.get("tree"), rec))
            except (OSError, ValueError, EOFError):
                continue
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "find":
        for m, t, rec in find(a[1], float(a[2]) if len(a) > 2 else 30):
            print(f"{m}\t{t}\t{json.dumps(rec)}")
        sys.exit(0)
    if a and a[0] == "rotate":
        for day, n, b, af in rotate(float(a[1]) if len(a) > 1 else 24.0):
            print(f"ROTATED {day}: {n} files {b} -> {af} bytes")
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
