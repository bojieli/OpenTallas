#!/usr/bin/env python3
"""QC-TYPES-10/HC3: bind_hc3 vs bind_v4w (same plan v4w e5dc7eacb745, same elaboration): every rtl/ file and every
bind.f entry; only the two slw_hc3 types (and the fo32 library file) may differ."""
import hashlib, json, sys, re
from pathlib import Path
a, b = Path(sys.argv[1]), Path(sys.argv[2])          # a = bind_v4w, b = bind_hc3
def norm(o):
    if isinstance(o, dict): return {k: norm(v) for k, v in o.items() if k != "provenance"}
    if isinstance(o, list): return [norm(v) for v in o]
    return o
def h(p):   # json: provenance blocks (plan/manifest paths of the bind run) ignored; everything else byte-exact
    if p.suffix == ".json": return hashlib.sha256(json.dumps(norm(json.loads(p.read_text())), sort_keys=True).encode()).hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()
fa = {p.name: p for p in (a / "rtl").iterdir()}; fb = {p.name: p for p in (b / "rtl").iterdir()}
same = [n for n in fa if n in fb and h(fa[n]) == h(fb[n])]
diff = sorted(n for n in fa if n in fb and h(fa[n]) != h(fb[n]))
print(f"rtl files: v4w {len(fa)} hc3 {len(fb)} identical {len(same)} differ {len(diff)} only_v4w {sorted(set(fa)-set(fb))} only_hc3 {sorted(set(fb)-set(fa))}")
print("DIFFER", diff)
bad = [n for n in diff if not n.startswith("slw_hc3__")]
la = {x.replace(str(a), "BIND") for x in (a / "bind.f").read_text().split()}; lb = {x.replace(str(b), "BIND") for x in (b / "bind.f").read_text().split()}
print("bind.f only_v4w", sorted(set(la) - set(lb))); print("bind.f only_hc3", sorted(set(lb) - set(la)))
ra = json.loads((a / "bind_report.json").read_text()); rb = json.loads((b / "bind_report.json").read_text())
for k in ("partitions", "types", "crossings", "crossing_bits", "errors", "unbound", "tied", "undriven", "multiply_bound", "straps"):
    va, vb = ra.get(k), rb.get(k)
    va = len(va) if isinstance(va, list) else va; vb = len(vb) if isinstance(vb, list) else vb
    print(f"report {k}: v4w {va} hc3 {vb}")
v = rb.get("variants") or []
print("variants hc3", type(v).__name__, json.dumps(v)[:600])
for n in diff:
    if n.endswith(".sv"):
        s = fb[n].read_text(); print(n, "fo32 inst", len(re.findall(r"\bot_qfd_xs_leaf_fo32_w\s+#\([^;]*?\)\s*u_", s)),
                                     "old leaf inst", len(re.findall(r"\bot_qfd_xs_leaf\s+#", s)))
print("VERDICT", "PASS only slw_hc3 differ" if not bad else f"FAIL other types differ: {bad}")
