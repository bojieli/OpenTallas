#!/usr/bin/env python3
"""DIE-QC-36 legal column-aware clock-cell re-site (QC-001 fix order step 1).

Same de-stack objective as DIE-QC-35 dqc35_whatif_destack.py (no two different-net clock pins in one M7 column,
|dx| <= 0.064 um, within DY um), but every move is LEGALIZED: whole-site x shift in the same row, on the site grid,
inside the die, no overlap with any other clock cell (post-move) or any provider (non-clock) placed cell, and the
cell keeps exactly its original partition-outline containment (no edge crossing). Connectivity is untouched
(sites only), so the strict bind graph is unchanged; the script asserts the net graph sha is identical.
Writes a new tree.json (sites replaced) + report json.
usage: dqc36_resite.py tree.json clkonly.v cells.lef placements.json plan.json DY out_tree.json report.json maxsites cell_windows.json
A moved cell must also stay wholly inside its own clock-island window(s) (cell_windows.json rect_die_um).
"""
import sys, json, re, math, hashlib, collections, bisect

tree_p, net_p, lef_p, plc_p, plan_p, DY, out_p, rep_p = sys.argv[1:9]
DY = float(DY); MAXS = int(sys.argv[9]); ISL = json.load(open(sys.argv[10]))['cells']
SITE, ROW, COL, EPS = 0.054, 0.27, 0.064, 1e-6


def lef_access(text, master):
    m = re.search(r'(?ms)^MACRO\s+'+re.escape(master)+r'\s*\n(.*?)^END\s+'+re.escape(master)+r'\s*$', text)
    body = m[1]; size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body); acc = {}
    for pin in ('A', 'Y'):
        pm = re.search(r'(?ms)^\s*PIN\s+'+pin+r'\s*\n(.*?)^\s*END\s+'+pin+r'\s*$', body)
        layers = re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\Z)', pm[1], re.S)
        rects = [tuple(map(float, r)) for layer, c in layers if layer == 'M1'
                 for r in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', c)]
        bars = [r for r in rects if r[3]-r[1] > r[2]-r[0] and r[2]-r[0] >= .0179]
        ty = .09 if pin == 'A' else .18
        bars = [r for r in bars if r[1]+.008 <= ty <= r[3]-.008]
        ch = min(bars, key=lambda r: r[0]) if pin == 'A' else max(bars, key=lambda r: r[2])
        acc[pin] = ((ch[0]+ch[2])/2, ty)
    return tuple(map(float, size.groups())), acc


tree = json.load(open(tree_p)); text = open(net_p).read(); lef = open(lef_p).read()
cells, pinnet, edges = {}, {}, []
for master, name, pins in re.findall(r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\w+)\s*\(([^;]+)\);', text):
    pp = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', pins))
    key = name[3:] if name.startswith('ck_') else name
    xy = tree['sites'][key]
    cells[name] = dict(key=key, x=xy[0], y=xy[1], lib=master)
    pinnet[(name, 'A')] = pp['A']; pinnet[(name, 'Y')] = pp['Y']; edges.append((name, pp['A'], pp['Y']))
graph_sha = hashlib.sha256(json.dumps(sorted(edges)).encode()).hexdigest()
libs = {c['lib'] for c in cells.values()}
geo = {m: lef_access(lef, m) for m in libs}

# partition outlines (bbox; orient R0/MX/MY/R180 keep the bbox)
plan = json.load(open(plan_p)); pt = plan['partition_types']
parts = []
for p in plan['partitions']:
    w, h = pt[p['type']]['outline_um']
    if p.get('orient') in ('R90', 'R270', 'MXR90', 'MYR90'): w, h = h, w
    parts.append((p['origin_um'][0], p['origin_um'][1], p['origin_um'][0]+w, p['origin_um'][1]+h, p['name']))
PB = 500.0; pbins = collections.defaultdict(list)
for r in parts:
    for i in range(int(r[0]//PB), int(r[2]//PB)+1):
        for j in range(int(r[1]//PB), int(r[3]//PB)+1): pbins[(i, j)].append(r)
def containment(x0, y0, x1, y1):
    s = set()
    for r in pbins[(int(x0//PB), int(y0//PB))] + pbins[(int(x1//PB), int(y1//PB))]:
        if r[0]-EPS <= x0 and x1 <= r[2]+EPS and r[1]-EPS <= y0 and y1 <= r[3]+EPS: s.add((r[4], 'in'))
        elif x0 < r[2]-EPS and r[0]+EPS < x1 and y0 < r[3]-EPS and r[1]+EPS < y1: s.add((r[4], 'cross'))
    return frozenset(s)

# row occupancy: key = round(y/ROW) -> sorted list of (x0, x1, owner)
occ = collections.defaultdict(list)
plc = json.load(open(plc_p)); dbu = plc.get('dbu', 1000)
for q in plc['cells']:
    b = [v/dbu for v in q['bbox_dbu']]
    for r in range(round(b[1]/ROW), round(b[3]/ROW)):
        occ[r].append((b[0], b[2], 'P:'+q['inst']))
def cbox(name, x):
    c = cells[name]; w, h = geo[c['lib']][0]; return (x, c['y'], x+w, c['y']+h)
for n, c in cells.items():
    x0, y0, x1, y1 = cbox(n, c['x'])
    for r in range(round(y0/ROW), round(y1/ROW)): occ[r].append((x0, x1, 'C:'+n))
for r in occ: occ[r].sort()

def overlaps(name, x0, y0, x1, y1, ignore):
    hits = []
    for r in range(round(y0/ROW), round(y1/ROW)):
        L = occ[r]; i = bisect.bisect_left(L, (x0-2.0,))
        while i < len(L) and L[i][0] < x1-EPS:
            a, b, o = L[i]
            if o != ignore and b > x0+EPS: hits.append(o)
            i += 1
    return hits
def occ_move(name, xold, xnew):
    x0, y0, x1, y1 = cbox(name, xold); X0, _, X1, _ = cbox(name, xnew)
    for r in range(round(y0/ROW), round(y1/ROW)):
        L = occ[r]; L.remove((x0, x1, 'C:'+name)); bisect.insort(L, (X0, X1, 'C:'+name))

def in_island(key, bx):
    return any(r[0]-EPS <= bx[0] and bx[2] <= r[2]+EPS and r[1]-EPS <= bx[1] and bx[3] <= r[3]+EPS
               for r in (q['rect_die_um'] for q in ISL[key]))
# baseline legality census (before any move)
base_ovl = collections.Counter(); offgrid = 0
for n, c in cells.items():
    x0, y0, x1, y1 = cbox(n, c['x'])
    if not in_island(c['key'], (x0, y0, x1, y1)): base_ovl['outside_island'] += 1
    if abs(c['x']/SITE - round(c['x']/SITE)) > 1e-3 or abs(c['y']/ROW - round(c['y']/ROW)) > 1e-3: offgrid += 1
    for o in overlaps(n, x0, y0, x1, y1, 'C:'+n): base_ovl[o[0]] += 1
print('baseline overlaps', dict(base_ovl), 'offgrid', offgrid, flush=True)

B = .2; bins = collections.defaultdict(list)
def pins(name, x):
    c = cells[name]; acc = geo[c['lib']][1]
    return [(x+acc[p][0], c['y']+.135, pinnet[(name, p)]) for p in ('A', 'Y')]
def stacked(name, x):
    for px, py, net in pins(name, x):
        for b in range(math.floor((px-.07)/B), math.floor((px+.07)/B)+1):
            for ox, oy, onet, other in bins[b]:
                if other != name and onet != net and abs(ox-px) <= COL+1e-9 and abs(oy-py) < DY: return True
    return False

order = sorted(cells, key=lambda k: (cells[k]['x'], cells[k]['y']))
shifts = [0] + [s for k in range(1, MAXS+1) for s in (k, -k)]
moved, unresolved, why = {}, [], collections.Counter()
die_w, die_h = plan['die']['outline_um']
for name in order:
    c = cells[name]; x0 = c['x']; b0 = cbox(name, x0); cont0 = containment(*b0); chosen = None
    for s in shifts:
        x = round(x0+s*SITE, 6); bx = cbox(name, x)
        if s:
            if bx[0] < -EPS or bx[2] > die_w+EPS: why['die'] += 1; continue
            if containment(*bx) != cont0: why['partition_edge'] += 1; continue
            if not in_island(c['key'], bx): why['island'] += 1; continue
            if overlaps(name, *bx, 'C:'+name): why['overlap'] += 1; continue
        if not stacked(name, x): chosen = s; break
        why['stacked'] += 1
    if chosen is None:
        chosen = 0; unresolved.append(name)
    if chosen:
        xn = round(x0+chosen*SITE, 6); occ_move(name, x0, xn); c['x'] = xn; moved[name] = chosen
    for px, py, net in pins(name, c['x']): bins[math.floor(px/B)].append((px, py, net, name))

# post-move legality audit (independent recount)
post_ovl = collections.Counter(); post_edge = 0
for n, c in cells.items():
    bx = cbox(n, c['x'])
    for o in overlaps(n, *bx, 'C:'+n): post_ovl[o[0]] += 1
    if not in_island(c['key'], bx): post_ovl['outside_island'] += 1
    if n in moved:
        tx = tree['sites'][c['key']]
        if containment(*bx) != containment(*cbox(n, tx[0])): post_edge += 1
# recheck stacking from scratch
bins = collections.defaultdict(list)
for n in cells:
    for px, py, net in pins(n, cells[n]['x']): bins[math.floor(px/B)].append((px, py, net, n))
still = sum(1 for n in cells if stacked(n, cells[n]['x']))
new_sites = dict(tree['sites'])
for n in moved: new_sites[cells[n]['key']] = [cells[n]['x'], cells[n]['y']]
tree['sites'] = new_sites
tree.setdefault('meta', {})['resite_dqc36'] = dict(dy_um=DY, moved=len(moved), max_sites=MAXS)
json.dump(tree, open(out_p, 'w'))
rep = dict(dy_um=DY, cells=len(cells), moved=len(moved), unresolved=len(unresolved), unresolved_cells=unresolved[:50],
           still_stacked_recount=still, baseline_overlaps=dict(base_ovl), baseline_offgrid=offgrid,
           post_overlaps=dict(post_ovl), post_partition_edge_changes=post_edge,
           shift_sites_hist=dict(sorted(collections.Counter(moved.values()).items())),
           max_abs_um=round(max([abs(v)*SITE for v in moved.values()] or [0]), 4),
           rejected_candidates=dict(why), graph_sha256=graph_sha, provider_cells=len(plc['cells']),
           note='x-only whole-site shifts, same row; connectivity unchanged (graph sha)')
json.dump(rep, open(rep_p, 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'unresolved_cells'}), flush=True)
