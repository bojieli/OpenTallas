#!/usr/bin/env python3
"""DIE-HBM-90-PEV: package the expx328_1107 replay (RR/new) into d44v.   pack_expx.py RR D44V"""
import gzip, hashlib, json, shutil, sys
from pathlib import Path
rr, d = Path(sys.argv[1]), Path(sys.argv[2])
new, base = rr / "new", rr / "base"
def gzw(src, dst):
    raw = src.read_bytes()
    with open(dst, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g: g.write(raw)
    return hashlib.sha256(raw).hexdigest()
ch = {}
for n in ("die_plan.json", "clock_entries.json"):
    assert (d / (n + ".gz")).exists(); ch[n] = gzw(new / n, d / (n + ".gz"))
for n in ("core_macros.json", "cores/ot_hbm_su_pg_lane_exp_x_core__328.32x207.36__d44v_expx328.json", "expx328_1107_event.json"):
    shutil.copyfile(new / n, d / n); ch[n] = hashlib.sha256((d / n).read_bytes()).hexdigest()
shutil.copyfile(rr / "ft_nudge_ledger.json", d / "expx328_1107_ft_nudge_ledger.json")
ch["expx328_1107_ft_nudge_ledger.json"] = hashlib.sha256((d / "expx328_1107_ft_nudge_ledger.json").read_bytes()).hexdigest()
# nothing else may differ between base and new
for f in sorted(new.rglob("*")):
    if f.is_file():
        r = str(f.relative_to(new)); b = base / r
        if r not in ch: assert b.exists() and b.read_bytes() == f.read_bytes(), ("unpackaged change", r)
L = [l.split(None, 1) for l in (d / "SHA256SUMS").read_text().splitlines() if l.strip()]
seen = set()
for x in L:
    x[1] = x[1].strip()
    if x[1] in ch: x[0] = ch[x[1]]; seen.add(x[1])
L += [[ch[n], n] for n in ch if n not in seen]
(d / "SHA256SUMS").write_text("".join(f"{a}  {n}\n" for a, n in L))
print("packed", {n: h[:12] for n, h in ch.items()}, "replaced", sorted(seen))
