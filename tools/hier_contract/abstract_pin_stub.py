#!/usr/bin/env python3
"""Move OBS rects that overlap a signal pin's rect on the same layer into that pin's PORT (they are the pin net's
own stub: in a DRC-clean routed child, any metal touching a pin on its layer is that pin's net)."""
import os, re, sys, tempfile
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
mac_end = t.rfind("END ")
obs_i = t.find("\n  OBS")
assert obs_i > 0
head, obs = t[:obs_i], t[obs_i:]
pins = {}
for m in re.finditer(r"  PIN (\S+)\n(.*?)\n  END \1", head, re.S):
    b = m.group(2)
    if re.search(r"USE (POWER|GROUND)", b): continue
    for lay, rs in re.findall(r"LAYER (\S+) ;\s*((?:RECT[^;]*;\s*)+)", b):
        for r in re.findall(r"RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", rs):
            pins.setdefault(m.group(1), []).append((lay, *map(float, r)))
def ov(a, b):  # overlap with positive area
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
moved = {}
out, cur = [], None
for line in obs.split("\n"):
    m = re.match(r"\s*LAYER (\S+)", line)
    if m: cur = m.group(1); out.append(line); continue
    m = re.match(r"\s*RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", line)
    if m:
        r = tuple(map(float, m.groups()))
        hit = [p for p, rs in pins.items() if any(l == cur and ov(r, x[1:]) for x in rs for l in [x[0]])]
        if len(hit) == 1:
            moved.setdefault(hit[0], []).append((cur, m.groups())); continue
    out.append(line)
obs = "\n".join(out)
for p, rs in moved.items():
    add = "".join(f"\n    PORT\n      LAYER {l} ;\n        RECT  {a} {b} {c} {d} ;\n    END" for l, (a, b, c, d) in rs)
    head = re.sub(rf"(  PIN {re.escape(p)}\n.*?)(\n  END {re.escape(p)})", lambda m: m.group(1) + add + m.group(2), head, count=1, flags=re.S)
# atomic replace, not an in-place write: ref_tile export rewrites the view LEF in place (dst == src) and the exporter's
# container leaves it root-owned (open(dst, "w") -> PermissionError, hgi_topk_heap_rt_m5-h3m5-6d8d554ba collect 10-12);
# the view directory itself is the job user's
fd, tmp = tempfile.mkstemp(prefix=".pinstub.", dir=os.path.dirname(os.path.abspath(dst)))
with os.fdopen(fd, "w") as f:
    f.write(head + obs)
os.chmod(tmp, 0o664)
os.replace(tmp, dst)
print(f"pinstub: {sum(map(len, moved.values()))} OBS rects moved into {len(moved)} pins: " + ", ".join(sorted(moved)[:12]))
