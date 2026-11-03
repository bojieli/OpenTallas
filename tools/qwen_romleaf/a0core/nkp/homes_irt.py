#!/usr/bin/env python3
"""ICG_IDLE_RT graph homes: g_icg.dr[i] homes move to g_icg.g_root.g_erx.dr_x[i] (same coordinates, same yosys type
suffix as in the netlist); the new idle_r takes the home of the tile-root enable flop g_icg.g_root.en_g (next to the
ICG); then every home must name a cell of the netlist (fail closed, as graph_homes.tcl).
usage: homes_irt.py HOMES_IN NETLIST OUT"""
import re, sys
hin, net, out = sys.argv[1:4]
names = set(n.lstrip('\\') for _, n in re.findall(r"^\s*(\w+)\s+(\S+)\s+\(", open(net).read(), re.M))
esc = lambda n: n.replace('[', '\\[').replace(']', '\\]')
raw = lambda n: n.replace('\\[', '[').replace('\\]', ']')
rows, moved, eng = [], 0, None
for ln in open(hin):
    nm, x, y = ln.rstrip('\n').split('\t')[:3]
    r = raw(nm)
    m = re.match(r"^g_icg\.dr\[(\d+)\](\$.*)$", r)
    if m:
        r = f"g_icg.g_root.g_erx.dr_x[{m.group(1)}]{m.group(2)}"; moved += 1
    if r == "g_icg.g_root.en_g$_DFF_PN1_": eng = (x, y)
    rows.append((r, x, y))
assert moved == 8, moved
assert eng, "no en_g home"
rows.append(("g_icg.g_root.g_erx.idle_r$_DFF_PN1_", eng[0], eng[1]))
miss = [r for r, _, _ in rows if r not in names]
assert not miss, ("homes without a netlist cell", len(miss), miss[:5])
open(out, 'w').write(''.join(f"{esc(r)}\t{x}\t{y}\n" for r, x, y in rows))
print(f"HOMES_IRT rows={len(rows)} moved_dr={moved} idle_r_at={eng}")
