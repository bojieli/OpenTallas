"""HBM-PLAN-1 helpers: read/write a plan dir (die_plan.json + .gz mtime 0 + SHA256SUMS of uncompressed bytes)."""
import gzip, hashlib, json, shutil, sys
from pathlib import Path

def sha(b): return hashlib.sha256(b).hexdigest()

def load(d):
    return json.loads((Path(d) / "die_plan.json").read_bytes())

def copy_dir(src, dst):
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    shutil.copytree(src, dst, symlinks=False)

def dump_plan(P):
    return (json.dumps(P, indent=1) + "\n").encode()

def write_file(d, rel, data, gz=True):
    """write rel (uncompressed) and rel.gz (mtime 0) into plan dir d, update SHA256SUMS."""
    d = Path(d); p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists(): p.unlink()
    p.write_bytes(data)
    if gz:
        g = Path(str(p) + ".gz")
        if g.exists(): g.unlink()
        with open(g, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as z:
            z.write(data)
    sums_p = d / "SHA256SUMS"
    lines = [l for l in sums_p.read_text().split("\n") if l.strip()] if sums_p.exists() else []
    m = {}
    for l in lines:
        h, n = l.split("  ", 1); m[n] = h
    m[rel] = sha(data)
    if gz:
        m[rel + ".gz"] = sha(Path(str(p) + ".gz").read_bytes())
    sums_p.unlink()
    sums_p.write_text("".join(f"{m[n]}  {n}\n" for n in sorted(m)))
    return m[rel]

def write_plan(d, P):
    return write_file(d, "die_plan.json", dump_plan(P))

def write_event(d, name, ev):
    return write_file(d, name, (json.dumps(ev, indent=1) + "\n").encode(), gz=False)
