# EPYC6-RETIRE: runs ON AGIdock. argv[1] = mode.
#  list  : stdin JSON {dest_root: [[relpath, size|"L", sha256], ...]} -> JSON {dest_root: {ok, missing, size_mismatch, examples}}
#  closed: stdin JSON [[alt_root_1, alt_root_2, relpath, size], ...] -> JSON {relpath: "ok"|"missing"|"size <n>"}
#  sha   : stdin JSON [path, ...] -> JSON {path: sha256|null}   (4 parallel sha256sum)
import concurrent.futures as cf, hashlib, json, os, sys

mode = sys.argv[1]
data = json.load(sys.stdin)


def st(p):
    try:
        return os.lstat(p)
    except OSError:
        return None


if mode == "list":
    out = {}
    for root, items in data.items():
        miss, bad, hash_bad = [], [], []
        for rel, s, expected in items:
            x = st(os.path.join(root, rel))
            if x is None:
                miss.append(rel)
            elif s == "L" and not os.path.islink(os.path.join(root, rel)):
                bad.append(rel)
            elif s != "L" and (not os.path.isfile(os.path.join(root, rel)) or x.st_size != int(s)):
                bad.append(rel)
            else:
                digest = hashlib.sha256()
                try:
                    if s == "L":
                        digest.update(os.fsencode(os.readlink(os.path.join(root, rel))))
                    else:
                        with open(os.path.join(root, rel), "rb") as inp:
                            for block in iter(lambda: inp.read(1 << 22), b""):
                                digest.update(block)
                    if digest.hexdigest() != expected:
                        hash_bad.append(rel)
                except OSError:
                    hash_bad.append(rel)
        out[root] = dict(n=len(items), missing=len(miss), size_mismatch=len(bad), hash_mismatch=len(hash_bad),
                         ok=not miss and not bad and not hash_bad, examples=(miss + bad + hash_bad)[:5])
    print(json.dumps(out))
elif mode == "closed":
    out = {}
    for a, b, rel, size in data:
        r = "missing"
        for root in (a, b):
            x = st(os.path.join(root, rel))
            if x is not None:
                if os.path.islink(os.path.join(root, rel)) or x.st_size == size:
                    r = "ok"
                    break
                r = f"size {x.st_size}"
        out[rel] = r
    print(json.dumps(out))
elif mode == "sha":
    def h(p):
        try:
            d = hashlib.sha256()
            with open(p, "rb") as f:
                for blk in iter(lambda: f.read(1 << 22), b""):
                    d.update(blk)
            return p, d.hexdigest()
        except OSError:
            return p, None
    with cf.ThreadPoolExecutor(4) as ex:
        print(json.dumps(dict(ex.map(h, data))))
