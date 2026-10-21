# EPYC6-RETIRE: runs ON ot-epyc6. stdin = JSON list of root dirs. For each root writes the file list that will be copied
# to /tmp/e6r/lists/<id>.lst ("<relpath>\t<size>" per regular file, "<relpath>\tL" per symlink) and prints a JSON
# summary {root: {id, files, links, bytes}}.  Skipped (regenerable bulk): repo source snapshots (a dir named src*,
# bench_src*, bsrc_* that holds rtl/ or tools/), Verilator/C++ build dirs (obj_dir, obj*, containing *.mk), .git,
# __pycache__, *.o, *.gch, *.vvp.  The SAME list drives the rsync (--files-from) and the archive verification.
import hashlib, json, os, re, sys

LST = "/tmp/e6r/lists"
os.makedirs(LST, exist_ok=True)
SRC_NAME = re.compile(r"^(src[0-9a-z_-]*|bench_src.*|bsrc_.*)$")
OBJ_NAME = re.compile(r"^(obj_dir.*|obj[0-9a-z_]*)$")
SKIP_FILE = re.compile(r"\.(o|gch|vvp|d)$")


def skip_dir(path, name):
    if name in (".git", "__pycache__", "node_modules"):
        return True
    if SRC_NAME.match(name) and (os.path.isdir(os.path.join(path, "rtl")) or os.path.isdir(os.path.join(path, "tools"))):
        return True
    if OBJ_NAME.match(name):
        try:
            return any(f.endswith(".mk") for f in os.listdir(path))
        except OSError:
            return False
    return False


request = json.load(sys.stdin)
roots = request["roots"] if isinstance(request, dict) else request
with_hash = isinstance(request, dict) and request.get("hash", False)
res = {}
for root in roots:
    rid = hashlib.sha1(root.encode()).hexdigest()[:16]
    n = nl = b = 0
    lines = []
    tracked = set()
    if os.path.exists(os.path.join(root, ".git")):
        # EPYC6: a git worktree (e.g. qwen-kvsys/wt-kvs14r-*: 40 GB / 238k files, all repo content): copy only what git does
        # not reproduce = untracked/ignored files + tracked files modified in the worktree
        import subprocess
        try:
            g = ["git", "--work-tree=.", "-c", "core.quotepath=off"]
            t = subprocess.run(g + ["ls-files", "-z"], cwd=root, capture_output=True, timeout=600).stdout.decode("utf-8", "replace")
            mod = subprocess.run(g + ["diff", "--name-only", "-z"], cwd=root, capture_output=True, timeout=1800)
            if mod.returncode == 0:
                tracked = set(x for x in t.split("\0") if x) - set(x for x in mod.stdout.decode("utf-8", "replace").split("\0") if x)
        except Exception:
            tracked = set()
    if os.path.isdir(root):
        for dp, dns, fns in os.walk(root):
            keep = []
            for d in dns:
                p = os.path.join(dp, d)
                if os.path.islink(p):            # os.walk does not descend symlinked dirs; copy the link itself
                    lines.append((os.path.relpath(p, root), "L"))
                elif not skip_dir(p, d):
                    keep.append(d)
            dns[:] = keep
            for f in fns:
                if SKIP_FILE.search(f):
                    continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root)
                if "\n" in rel or "\t" in rel or rel in tracked:
                    continue
                try:
                    if os.path.islink(p):
                        lines.append((rel, "L"))
                        continue
                    s = os.lstat(p).st_size
                except OSError:
                    continue
                lines.append((rel, str(s)))
    for rel, s in lines:
        if s == "L":
            nl += 1
        else:
            n += 1
            b += int(s)
    hashes = {}
    if with_hash:
        for rel, size in lines:
            path = os.path.join(root, rel)
            digest = hashlib.sha256()
            if size == "L":
                digest.update(os.fsencode(os.readlink(path)))
            else:
                with open(path, "rb") as inp:
                    for block in iter(lambda: inp.read(1 << 22), b""):
                        digest.update(block)
            hashes[rel] = digest.hexdigest()
    with open(f"{LST}/{rid}.lst", "w") as fo:
        fo.write("".join(f"{r}\t{s}" + (f"\t{hashes[r]}" if with_hash else "") + "\n" for r, s in lines))
    res[root] = dict(id=rid, files=n, links=nl, bytes=b, exists=os.path.isdir(root))
print(json.dumps(res))
