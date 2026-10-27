"""CLOCK-KV-R11 probe: kv_rcx rcx.tcl drops every M9 split from a shared VIA89 *via* junction ($jdK); RCX attaches the
2nd branch at the far end of the 1st (resistor path retraces the 1st leg).  Here the via is followed by a 1-dbu M9
point and THAT point is the junction (the same point-junction form the M8 trunk already uses for jlo/jhi).  Same
metal (+1 nm), no connectivity change intended; checked by spef_connectivity after extraction."""
import re, sys
src, dst = sys.argv[1:3]
L = open(src).read().split("\n")
out, xy, n, last = [], {}, 0, None
for i, l in enumerate(L):
    m = re.match(r"(?:set (\w+) \[)?\$e addPoint (-?\d+) (-?\d+)\]?$", l)
    if m:
        last = (int(m.group(2)), int(m.group(3)))
        if m.group(1):
            xy[m.group(1)] = last
    m0 = re.match(r"\$e newPath \$(j\w+) FIXED", l)
    if m0 and m0.group(1) in xy:
        last = xy[m0.group(1)]
    m1 = re.match(r"set (jd\d+) \[\$e addTechVia \[V VIA89\]\]$", l)
    if m1 and last is not None:
        k = m1.group(1)
        x, y = last
        out += ["$e addTechVia [V VIA89]", f"set {k} [$e addPoint {x} {y + 1}]"]
        xy[k] = (x, y + 1); n += 1
        continue
    out.append(l)
open(dst, "w").write("\n".join(out))
print("M9 point junctions", n)
