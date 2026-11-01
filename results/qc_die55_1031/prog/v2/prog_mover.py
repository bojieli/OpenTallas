#!/usr/bin/env python3
"""DIE-QC-55: re-create the PROG native pin-reach FF move (Codex 10-29 native_pin_reach.odb, lost with the die-qc-34-kits
dir).  Only existing flops move; no RTL/pin/outline/cycle change.  Goals = the AUTO-GEOM rules that failed on the
archived s8b DB: pin_reg p90 <= 30 (lens LENS around the registering flop of each pin) and r2r <= 405 (target R2R).
usage: prog_mover.py GEOM_RULES_DIR DUMP.tsv OUT.tcl [LENS] [R2R] [P90_SHARE]"""
import sys, math, json
from collections import defaultdict, deque
sys.path.insert(0, sys.argv[1])
import geom_rules as G

dump, out = sys.argv[2], sys.argv[3]
LENS = float(sys.argv[4]) if len(sys.argv) > 4 else 26.0
R2R = float(sys.argv[5]) if len(sys.argv) > 5 else 392.0
D = G.Design(dump)
cells = D.cells
seq = {c for c, v in cells.items() if v[0] == 'S'}
comb = {c for c, v in cells.items() if v[0] in 'BLK'}
macros = [(v[2], v[3], v[4], v[5]) for v in cells.values() if v[0] == 'M']
core = D.extra['core']
pos = {c: G.ctr(cells[c]) for c in seq}
size = {c: (cells[c][4] - cells[c][2], cells[c][5] - cells[c][3]) for c in seq}
orig = dict(pos)
HALO = 4.6

# ---- pin -> registering flop (same walk as geom_rules.pin_reg_metrics)
anchor = {}   # flop -> (px, py) (nearest pin it registers)
pin_flop = []
for p in D.pins:
    if p['sig'] in ('POWER', 'GROUND', 'CLOCK') or G.CLOCK_PIN_RE.search(p['name']) or G.re.search(G.STRAP_RE_DEFAULT, p['name']):
        continue
    n = D.pin_net.get(p['k'])
    if n is None:
        continue
    cand = []
    if p['io'] == 'OUTPUT':
        cur, seen = n, set()
        while cur not in seen:
            seen.add(cur); dr = D.nets[cur][1]
            if not dr or dr[0] != 'i': break
            k = D.kind(dr[1])
            if k == 'S': cand = [dr[1]]; break
            if k != 'B' or not D.cell_in.get(dr[1]): break
            ins = [nn for nn, ck in D.cell_in[dr[1]] if not ck]
            if len(ins) != 1: break
            cur = ins[0]
    else:
        front, seen = [n], {n}
        while front and not cand:
            nf = []
            for nn in front:
                for s in D.nets[nn][2]:
                    if s[0] != 'i' or s[2]: continue
                    k = D.kind(s[1])
                    if k == 'S': cand.append(s[1])
                    elif k == 'B':
                        for on in D.drives.get(s[1], []):
                            if on not in seen: seen.add(on); nf.append(on)
            front = nf
    if not cand:
        continue
    f = min(cand, key=lambda c: abs(pos[c][0] - p['x']) + abs(pos[c][1] - p['y']))
    pin_flop.append((p['name'], f, p['x'], p['y']))
dist0 = sorted(abs(pos[f][0] - x) + abs(pos[f][1] - y) for _, f, x, y in pin_flop)
print('pins registered', len(pin_flop), 'p90 before', round(G.q(dist0, .9), 2))
for name, f, x, y in pin_flop:
    d = abs(pos[f][0] - x) + abs(pos[f][1] - y)
    if d > LENS:
        # a flop registering several pins keeps the first (nearest) lens; the rest stay as they are
        anchor.setdefault(f, (x, y))

# ---- combinational graph: comb cell -> fanin flops / comb cells (data pins only)
fanin = defaultdict(set)    # capture flop or comb cell -> driver cells (flop or comb)
for cid in list(seq) + list(comb):
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] == 'i' and not s[2] and (s[1] in seq or s[1] in comb):
                fanin[s[1]].add(cid)
launch_memo = {}
def launches(c):
    """flops that reach comb cell c (memoised, iterative)"""
    if c in launch_memo: return launch_memo[c]
    stack = [c]; order = []
    seen = {c}
    while stack:
        x = stack.pop(); order.append(x)
        for d in fanin.get(x, ()):
            if d in comb and d not in launch_memo and d not in seen:
                seen.add(d); stack.append(d)
    for x in reversed(order):
        s = set()
        for d in fanin.get(x, ()):
            if d in seq: s.add(d)
            elif d in comb: s |= launch_memo.get(d, set())
        launch_memo[x] = frozenset(s)
    return launch_memo[c]
pairs = []
for cap in seq:
    ls = set()
    for d in fanin.get(cap, ()):
        if d in seq: ls.add(d)
        elif d in comb: ls |= launches(d)
    for l in ls:
        if l != cap: pairs.append((l, cap))
print('r2r pairs', len(pairs))
md = lambda a, b: abs(pos[a][0] - pos[b][0]) + abs(pos[a][1] - pos[b][1])
print('r2r max before', round(max(md(a, b) for a, b in pairs), 2), 'over405', len({b for a, b in pairs if md(a, b) > 405}))

def legal(x, y, w, h):
    x = min(max(x, core[0] + w / 2 + 0.5), core[2] - w / 2 - 0.5)
    y = min(max(y, core[1] + h / 2 + 0.5), core[3] - h / 2 - 0.5)
    for (x0, y0, x1, y1) in macros:
        if x0 - HALO - w / 2 < x < x1 + HALO + w / 2 and y0 - HALO - h / 2 < y < y1 + HALO + h / 2:
            opts = [(x0 - HALO - w / 2 - 0.3, y), (x1 + HALO + w / 2 + 0.3, y), (x, y0 - HALO - h / 2 - 0.3), (x, y1 + HALO + h / 2 + 0.3)]
            x, y = min(opts, key=lambda o: abs(o[0] - x) + abs(o[1] - y))
    return x, y

def to_lens(f):
    px, py = anchor[f]; x, y = pos[f]
    d = abs(x - px) + abs(y - py)
    if d <= LENS: return
    t = LENS / d
    pos[f] = legal(px + (x - px) * t, py + (y - py) * t, *size[f])

def pull(a, b, amt):
    """move a toward b by amt (Manhattan, split over dx/dy proportionally)"""
    x, y = pos[a]; bx, by = pos[b]
    d = abs(bx - x) + abs(by - y)
    if d <= 0: return
    t = min(1.0, amt / d)
    pos[a] = legal(x + (bx - x) * t, y + (by - y) * t, *size[a])

for f in anchor: to_lens(f)
for it in range(60):
    viol = [(a, b, md(a, b)) for a, b in pairs if md(a, b) > R2R]
    if not viol: break
    for a, b, d in viol:
        d = md(a, b); ex = d - R2R + 0.5
        if ex <= 0: continue
        if a in anchor and b in anchor:
            pull(a, b, ex / 2); pull(b, a, ex / 2)
        elif a in anchor: pull(b, a, ex)
        elif b in anchor: pull(a, b, ex)
        else: pull(a, b, ex / 2); pull(b, a, ex / 2)
    for f in anchor: to_lens(f)
viol = [(a, b, md(a, b)) for a, b in pairs if md(a, b) > R2R]
moved = {f for f in seq if abs(pos[f][0] - orig[f][0]) + abs(pos[f][1] - orig[f][1]) > 0.05}
dist1 = sorted(abs(pos[f][0] - x) + abs(pos[f][1] - y) for _, f, x, y in pin_flop)
mv = [abs(pos[f][0] - orig[f][0]) + abs(pos[f][1] - orig[f][1]) for f in moved]
print('iterations', it + 1, 'remaining r2r >', R2R, len(viol), 'r2r max after', round(max(md(a, b) for a, b in pairs), 2))
print('pin p90 after (pre-DPL)', round(G.q(dist1, .9), 2), 'anchored', len(anchor), 'moved', len(moved), 'max move', round(max(mv or [0]), 2))
with open(out, 'w') as fh:
    fh.write('# prog_mover.py: %d flops moved (pre-DPL centres)\nset b [ord::get_db_block]\nset u [$b getDbUnitsPerMicron]\n' % len(moved))
    for f in sorted(moved):
        w, h = size[f]; x, y = pos[f]
        fh.write('set i [$b findInst {%s}]; $i setPlacementStatus PLACED; $i setLocation [expr {round(%.4f*$u)}] [expr {round(%.4f*$u)}]\n'
                 % (cells[f][6], x - w / 2, y - h / 2))
json.dump(dict(moved=len(moved), max_move=round(max(mv or [0]), 2), lens=LENS, r2r_target=R2R, anchored=len(anchor)),
          open(out + '.json', 'w'))
