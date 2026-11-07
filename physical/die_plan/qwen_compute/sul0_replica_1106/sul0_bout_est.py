"""DQ85-SUL0 vE estimate: bout bits sited at their source lane mouth; check no D/Q straight segment crosses a lane."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import sul0_apply as A
K = Path(sys.argv[2]); T = K.name
mp = (K / "macro_place.tcl").read_text()
org = {m.group(1): (float(m.group(2)), float(m.group(3)))
       for m in re.finditer(r"u_bound\.(\w+)\} -location \{([\d.]+) ([\d.]+)\} -orientation R0", mp)}
t = (K / "sul0_bound_pre.sv.txt").read_text()
masters = {i: re.search(r"^\s*(\w+) %s \(" % i, t, re.M).group(1) for i in org}
sizes = {i: A.lef_pins(K / "macros" / f"{masters[i]}.lef") for i in org}
ports = {f"{p['bus']}[{p['bit']}]": (p["x"], p["y"]) for p in json.loads((K / "pins.json").read_text())}
site = {m.group(1): tuple(map(float, m.group(2).split())) for m in
        re.finditer(r"dict set sul0_sites \{(\S+)\} \{([\d. ]+)\}", (K / "sul0_sites.tcl").read_text())}
widths = {m.group(2): int(m.group(1)) + 1 for m in re.finditer(r"^\s*wire\s+\[(\d+):0\]\s+(\w+);", t, re.M)}
src = {}
for i, (ox, oy) in org.items():
    line = next(l for l in t.split("\n") if re.match(r"^\s*\w+ %s \(" % i, l))
    pins = sizes[i][0]
    for port, body in re.findall(r"\.(\w+)\((\{.*?\}|[^(){}]*)\)", line):
        items = A._expand(body, widths); n = len(items)
        for p, it in enumerate(items):
            pin = f"{port}[{n-1-p}]" if n > 1 or f"{port}[0]" in pins else port
            if pin in pins: src[it] = (i, ox + pins[pin][0], oy + pins[pin][1], pins[pin][0] < 1.0)
out = {"bits": [], "summary": {}}
for B, qb, w, pb in A.bout_bits(t, set(org)):
    i, x, y, west = src[w]; key = f"u_bound.u_bout_{B}/q[{qb}]"
    s = site.get(key); P = ports[pb]
    before = A.straddles((x, y), P, org, sizes)
    after = (A.straddles((x, y), s, org, sizes) + A.straddles(s, P, org, sizes)) if s else before
    out["bits"].append([B, qb, i, round(x, 2), round(y, 2), s, P, len(before), len(after)])
    S = out["summary"].setdefault(B, {"bits": 0, "west_src": 0, "cross_before": 0, "sited": 0, "cross_after": 0})
    S["bits"] += 1; S["west_src"] += west; S["cross_before"] += bool(before); S["sited"] += bool(s); S["cross_after"] += bool(after)
print(json.dumps(out["summary"], indent=0))
json.dump(out, open(sys.argv[3], "w"))
