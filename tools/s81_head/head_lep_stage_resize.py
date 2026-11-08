#!/usr/bin/env python3
# DIE-HEAD-86 11-08 head_lep_stage_resize.py -- run with: openroad -python -exit head_lep_stage_resize.py <3_2_place_iop.odb> <landing_placement.tcl> <out.tcl>
# Measures each cland stage window (stage:<tag>) against the reserve row length its cells need (landing_placement:
# ceil(w/0.4) sites per cell), widens it about its centre to >= MARGIN x demand on the real rows, lifts it off macros
# (<= 3 um), pushes same-channel neighbours apart and writes the cland list back.  Prints need/rowlen/ratio per window.
# DIE-HEAD-86: size each declared stage window from its own cell demand (reserve row length, landing_placement rule
# ceil(w/0.4/site)*site) so usable row length >= MARGIN x demand; keep the leg centre, push neighbours in the same
# channel apart, keep clear of macros. Writes the new cland stage list.
import odb, re, sys, math, collections
MARGIN = 1.25
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
rows = [(r.getBBox().xMin()/u, r.getBBox().yMin()/u, r.getBBox().xMax()/u, r.getBBox().yMax()/u) for r in b.getRows()]
macs = [(i.getBBox().xMin()/u, i.getBBox().yMin()/u, i.getBBox().xMax()/u, i.getBBox().yMax()/u) for i in b.getInsts() if i.getMaster().isBlock()]
lines = open(sys.argv[2]).read().splitlines()
ent = []
for k, ln in enumerate(lines):
    m = re.search(r"\{\{(.*?)\} \{([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)\} (stage:\S+)\}", ln)
    if m: ent.append(dict(k=k, pat=m.group(1), r=list(map(float, m.groups()[1:5])), tag=m.group(6)))
insts = [(i.getName(), i.getMaster().getWidth()/u) for i in b.getInsts()]
need = collections.Counter()
for e in ent:
    g = re.compile('^' + e['pat'])
    need[e['tag']] += sum(math.ceil(w/0.4/0.054)*0.054 for n, w in insts if g.match(n))
def rowlen(r):
    x0, y0, x1, y1 = r; s = 0.0
    for a0, b0, a1, b1 in rows:
        if b0 >= y0-1e-6 and b1 <= y1+1e-6:
            w = min(x1, a1)-max(x0, a0)
            if w > 0: s += w
    return s
def hits_macro(r):
    x0, y0, x1, y1 = r
    return any(min(x1, a1)-max(x0, a0) > 0 and min(y1, b1)-max(y0, b0) > 0 for a0, b0, a1, b1 in macs)
tags = {}
for e in ent: tags.setdefault(e['tag'], e['r'])
new = {}
for t, r in tags.items():
    x0, y0, x1, y1 = r; cx = (x0+x1)/2
    # clear a macro overlap by moving the window up/down inside its channel (<= 3 um)
    for dy in (0, 0.5, 1, 1.5, 2, 2.5, 3, -0.5, -1, -1.5, -2, -2.5, -3):
        if not hits_macro((x0, y0+dy, x1, y1+dy)): y0, y1 = y0+dy, y1+dy; break
    w = x1-x0
    vertical = (y1-y0) > (x1-x0)
    while rowlen((cx-w/2, y0, cx+w/2, y1) if not vertical else (x0, y0, x1, y1)) < MARGIN*need[t]:
        if vertical: y1 += 1.0
        else: w += 2.0
        if w > 400 or y1-y0 > 600: break
    new[t] = [cx-w/2, y0, cx+w/2, y1] if not vertical else [x0, y0, x1, y1]
# resolve overlaps in each channel (same y0): push the east window east
for _ in range(20):
    moved = False
    items = sorted(new.items(), key=lambda kv: (round(kv[1][1], 1), kv[1][0]))
    for (ta, ra), (tb, rb) in zip(items, items[1:]):
        if abs(ra[1]-rb[1]) < 0.5 and rb[0] < ra[2] + 1.0:
            d = ra[2] + 1.0 - rb[0]; rb[0] += d; rb[2] += d; moved = True
    if not moved: break
bad = []
for t, r in sorted(new.items()):
    rl = rowlen(r); ok = rl >= MARGIN*need[t] and not hits_macro(r)
    for t2, r2 in new.items():
        if t2 != t and min(r[2], r2[2])-max(r[0], r2[0]) > 0 and min(r[3], r2[3])-max(r[1], r2[1]) > 0: ok = False
    if not ok: bad.append(t)
    print("%-10s old %s new %s need %.0f rowlen %.0f ratio %.2f %s" % (t, ["%.1f" % v for v in tags[t]], ["%.1f" % v for v in r], need[t], rl, rl/max(need[t], 1), "OK" if ok else "BAD"))
out = list(lines)
for e in ent:
    r = new[e['tag']]
    out[e['k']] = re.sub(r"\} \{[\d.]+ [\d.]+ [\d.]+ [\d.]+\} (stage:\S+)\}", "} {%.5f %.5f %.5f %.5f} \\1}" % tuple(r), lines[e['k']])
open(sys.argv[3], 'w').write("\n".join(out) + "\n")
print("BAD", bad)
