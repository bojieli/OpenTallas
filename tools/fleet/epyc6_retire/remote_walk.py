# EPYC6-RETIRE: runs ON ot-epyc6. stdin = JSON list of root dirs. For each root writes the file list that will be copied
# to /tmp/e6r/lists/<id>.lst ("<relpath>\t<size>" per regular file, "<relpath>\tL" per symlink) and prints a JSON
# summary {root: {id, files, links, bytes}}.  Skipped (regenerable bulk): repo source snapshots (a dir named src*,
# bench_src*, bsrc_* that holds rtl/ or tools/), Verilator/C++ build dirs (obj_dir, obj*, containing *.mk), .git,
# __pycache__, *.o, *.gch, *.vvp.  The SAME list drives the rsync (--files-from) and the archive verification.
import hashlib, json, os, pathlib, re, sys

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


def pristine_files(root, proofs, require_proof=False):
    """Only exclude reconstructible tracked content; errors preserve the complete copy."""
    import subprocess
    try:
        git = ["git", "-c", "diff.autoRefreshIndex=false", "--git-dir=" + str(git_dir(root)), "--work-tree=" + root, "-c", "core.quotepath=off"]
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        def call(*args):
            return subprocess.run(git + list(args), capture_output=True, timeout=600, env=env, check=True).stdout
        if require_proof:
            proof = proofs.get(root, {})
            if not (proof.get("archive_verified") is True and len(proof.get("bundle_sha256", "")) == 64):
                return set()
            index = call("rev-parse", "--git-path", "index").decode().strip()
            head = call("rev-parse", "HEAD").decode().strip()
            diff = call("diff", "--binary", "HEAD", "--")
            if not (proof.get("archive_verified") is True and len(proof.get("bundle_sha256", "")) == 64
                    and proof.get("head") == head
                    and proof.get("refs_sha256") == hashlib.sha256(call("for-each-ref", "--format=%(objectname) %(refname)")).hexdigest()
                    and proof.get("index_sha256") == hashlib.sha256(pathlib.Path(index).read_bytes()).hexdigest()
                    and proof.get("diff_sha256") == hashlib.sha256(diff).hexdigest()):
                return set()
        tracked = call("ls-files", "-z").decode("utf-8", "surrogateescape").split("\0")
        modified = call("diff", "HEAD", "--name-only", "-z").decode("utf-8", "surrogateescape").split("\0")
        return set(tracked) - set(modified) - {""}
    except Exception:
        return set()


def git_dir(root):
    p = os.path.join(root, ".git")
    if os.path.isfile(p):
        text = open(p).read().strip()
        if not text.startswith("gitdir: "):
            raise ValueError("invalid worktree gitdir")
        return os.path.abspath(os.path.join(root, text[8:]))
    if os.path.isdir(p):
        return p
    raise ValueError("no git boundary")


def main():
    request = json.load(sys.stdin)
    roots = request["roots"] if isinstance(request, dict) else request
    with_hash = isinstance(request, dict) and request.get("hash", False)
    proof_path = request.get("git_proofs", "/tmp/e6r/git_reconstruction_verified.json") if isinstance(request, dict) else "/tmp/e6r/git_reconstruction_verified.json"
    try:
        proofs = json.load(open(proof_path))["worktrees"]
    except (OSError, ValueError, KeyError):
        proofs = {}
    res = {}
    for root in roots:
        rid = hashlib.sha1(root.encode()).hexdigest()[:16]
        n = nl = b = 0
        lines = []
        boundaries = {}
        if os.path.exists(os.path.join(root, ".git")):
            boundaries[root] = pristine_files(root, proofs)
        if os.path.isdir(root):
            for dp, dns, fns in os.walk(root):
                if dp != root and os.path.exists(os.path.join(dp, ".git")):
                    boundaries[dp] = pristine_files(dp, proofs, require_proof=True)
                boundary = next((a for a in sorted(boundaries, key=len, reverse=True) if dp == a or dp.startswith(a + "/")), None)
                tracked = boundaries.get(boundary, set())
                keep = []
                for d in dns:
                    p = os.path.join(dp, d)
                    if os.path.islink(p):
                        lines.append((os.path.relpath(p, root), "L"))
                    elif not skip_dir(p, d):
                        keep.append(d)
                dns[:] = keep
                for f in fns:
                    if SKIP_FILE.search(f):
                        continue
                    p = os.path.join(dp, f)
                    rel = os.path.relpath(p, root)
                    if "\n" in rel or "\t" in rel:
                        continue
                    try:
                        if os.path.islink(p):
                            lines.append((rel, "L"))
                            continue
                        if boundary and os.path.relpath(p, boundary) in tracked:
                            continue
                        size = os.lstat(p).st_size
                    except OSError:
                        continue
                    lines.append((rel, str(size)))
        for rel, size in lines:
            if size == "L":
                nl += 1
            else:
                n += 1
                b += int(size)
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


if __name__ == "__main__":
    main()
