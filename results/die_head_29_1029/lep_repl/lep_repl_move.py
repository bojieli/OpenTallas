"""DIE-HEAD-29 estimate-only probe: does per-bank register replication close the LEP V5 r2r residual?
Reads Codex LEP V5 inputs read-only; same Manhattan metric as geom_rules.r2r_metrics (memories = full box, uv form)."""
import json, math, re, sys
from collections import defaultdict, deque, Counter
from pathlib import Path
V5 = Path('/srv/opentallas-scratch2/claude/codex-head-serdes-lep-0825/lep_registers_solve_v5')
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
sys.path.insert(0, str(V5 / 'code/tools/autopilot')); import geom_rules as G
R = 405.0
D = G.Design(V5 / 'input.tsv'); child = json.loads((V5 / 'child_delta.json').read_text())['child_type']; W, H = child['outline_um']
macros = {p['inst']: p for p in child['contents']}
for i, c in list(D.cells.items()):
    if c[0] == 'M':
        x, y = macros[c[6].replace('\\', '')]['origin_um']; D.cells[i] = c[:2] + (x, y, x + c[4] - c[2], y + c[5] - c[3]) + c[6:]
import os
for ov in filter(None, os.environ.get('MACRO_MOVE', '').split(';')):  # V2 what-if: inst=x,y
    inst, xy = ov.split('='); macros[inst]['origin_um'] = [float(v) for v in xy.split(',')]
    for i, c in list(D.cells.items()):
        if c[0] == 'M' and c[6].replace('\\', '') == inst:
            x, y = macros[inst]['origin_um']; D.cells[i] = c[:2] + (x, y, x + c[4] - c[2], y + c[5] - c[3]) + c[6:]
mb = [(c[6], c[2:6]) for c in D.cells.values() if c[0] == 'M']
for a_ in range(len(mb)):
    for b_ in range(a_ + 1, len(mb)):
        A, B = mb[a_][1], mb[b_][1]
        if A[0] < B[2] + 4.32 and B[0] < A[2] + 4.32 and A[1] < B[3] + 4.32 and B[1] < A[3] + 4.32: print('MACRO HALO OVERLAP', mb[a_][0], mb[b_][0], flush=True)
plan = json.loads((V5 / 'out/register_plan.json').read_text())
byname = {c[6]: i for i, c in D.cells.items()}
for s in plan['sites']:
    i = byname[s['name']]; c = D.cells[i]; x, y = s['xy']; D.cells[i] = c[:2] + (x, y, x + c[4] - c[2], y + c[5] - c[3]) + c[6:]
SEQ = {i for i, c in D.cells.items() if c[0] in 'SM'}
COMB = {i for i, c in D.cells.items() if c[0] in 'BLK'}
def bounds(i, macro_ctr=False):
    c = D.cells[i]
    if c[0] == 'M' and not macro_ctr: return (c[2] + c[3], c[4] + c[5], c[2] - c[5], c[4] - c[3])
    x, y = G.ctr(c); return (x + y, x + y, x - y, x - y)
def dist(a, b, mc=False):
    A, B = bounds(a, mc), bounds(b, mc); return max(A[1] - B[0], B[1] - A[0], A[3] - B[2], B[3] - A[2])
def ball(b):  # region (uv rect) of points within R of every point of endpoint b
    u0, u1, v0, v1 = bounds(b); return [u1 - R, u0 + R, v1 - R, v0 + R]
def inter(a, b): return [max(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), min(a[3], b[3])]
def empty(r): return r[0] > r[1] + 1e-6 or r[2] > r[3] + 1e-6
def in_die(r):  # does uv rect contain a point of the outline (sampled)
    if empty(r): return False
    for a in range(11):
        for b in range(11):
            u = r[0] + (r[1] - r[0]) * a / 10; v = r[2] + (r[3] - r[2]) * b / 10; x, y = (u + v) / 2, (u - v) / 2
            if 0 <= x <= W and 0 <= y <= H: return True
    return False
fc = {}
def fwd(s):
    if s in fc: return fc[s]
    out = set(); q = deque(D.drives.get(s, [])); seen = set()
    while q:
        n = q.popleft()
        if n in seen: continue
        seen.add(n)
        for r in D.nets[n][2]:
            if r[0] != 'i' or r[2]: continue
            if r[1] in SEQ: out.add(r[1])
            elif r[1] in COMB: q.extend(D.drives.get(r[1], []))
    fc[s] = out; return out
bc = {}
def bwd(t):
    if t in bc: return bc[t]
    out = set(); pins = set(); q = deque(n for n, ck in D.cell_in.get(t, []) if not ck); seen = set()
    while q:
        n = q.popleft()
        if n in seen: continue
        seen.add(n); d = D.nets[n][1]
        if d is None: continue
        if d[0] == 'p': pins.add(d[1]); continue
        if d[1] in SEQ: out.add(d[1])
        elif d[1] in COMB: q.extend(nn for nn, ck in D.cell_in.get(d[1], []) if not ck)
    bc[t] = (out, pins); return bc[t]
pins_new = {p['name']: p for p in json.loads((V5 / 'lep_pair_pins.json').read_text())['pins']}
anchored = set()
for p in D.pins:
    if p['sig'] == 'CLOCK': continue
    n = D.pin_net.get(p['k'])
    if n is None: continue
    if p['io'] == 'INPUT':
        for r in D.nets[n][2]:
            pass
        q = deque([n]); seen = set()
        while q:
            n2 = q.popleft()
            if n2 in seen: continue
            seen.add(n2)
            for r in D.nets[n2][2]:
                if r[0] != 'i' or r[2]: continue
                k = D.kind(r[1])
                if k == 'S': anchored.add(r[1])
                elif k in 'BLK': q.extend(D.drives.get(r[1], []))
    else:
        q = deque([n]); seen = set()
        while q:
            n2 = q.popleft()
            if n2 in seen: continue
            seen.add(n2); r = D.nets[n2][1]
            if not r or r[0] != 'i': continue
            k = D.kind(r[1])
            if k == 'S': anchored.add(r[1])
            elif k in 'BLK': q.extend(nn for nn, ck in D.cell_in.get(r[1], []) if not ck)
nm = lambda i: D.cells[i][6]
fam = lambda s: re.sub(r'\\\[\d+\\\]', '[]', s).replace('$_DFF_P_', '').split('$')[0].replace('\\', '')
def famgroup(i):  # replication group = registers of the same bus family (counter replicated whole)
    return fam(nm(i))

REFF = float(sys.argv[2]) if len(sys.argv) > 2 else 403.0   # placement target leaves legalization margin; census at 405
import time; t0 = time.time()
succ = {s: fwd(s) for s in SEQ}
pred = defaultdict(set)
for s, ts in succ.items():
    for t in ts: pred[t].add(s)
print('edges', sum(len(v) for v in succ.values()), 'anchored', len(anchored), round(time.time() - t0, 1), flush=True)
def ballR(b, r):
    u0, u1, v0, v1 = bounds(b); return [u1 - r, u0 + r, v1 - r, v0 + r]
def census():
    bad = set(); badedges = []
    for t in pred:
        for s in pred[t]:
            if s != t and dist(s, t) > R: bad.add(t); badedges.append((s, t))
    return bad, badedges
def pick(reg, i):  # point in uv rect inside die nearest current position
    u0, u1, v0, v1 = bounds(i); cu, cv = u0, v0
    best = None
    for a in range(21):
        for b in range(21):
            u = reg[0] + (reg[1] - reg[0]) * a / 20; v = reg[2] + (reg[3] - reg[2]) * b / 20; x, y = (u + v) / 2, (u - v) / 2
            if 4.32 <= x <= W - 4.32 and 4.32 <= y <= H - 4.32:
                d = max(abs(u - cu), abs(v - cv))
                if best is None or d < best[0]: best = (d, x, y)
    # also the clamp of current point
    u = min(max(cu, reg[0]), reg[1]); v = min(max(cv, reg[2]), reg[3]); x, y = (u + v) / 2, (u - v) / 2
    if 4.32 <= x <= W - 4.32 and 4.32 <= y <= H - 4.32:
        d = max(abs(u - cu), abs(v - cv))
        if best is None or d < best[0]: best = (d, x, y)
    return best
def move(i, x, y):
    c = D.cells[i]; w, h = c[4] - c[2], c[5] - c[3]; D.cells[i] = c[:2] + (x - w / 2, y - h / 2, x + w / 2, y + h / 2) + c[6:]
bad0, be0 = census(); print('baseline census', len(bad0), 'violating edges', len(be0), flush=True)
moved = {}; stuck = set(); pushed = set()
for it in range(12):
    bad, be = census()
    ends = Counter()
    for s, t in be: ends[s] += 1; ends[t] += 1
    nmv = 0
    for i, _ in ends.most_common():
        if D.cells[i][0] != 'S' or i in anchored: continue
        reg = [-1e9, 1e9, -1e9, 1e9]
        for n in (succ[i] | pred[i]) - {i}: reg = inter(reg, ballR(n, REFF))
        if empty(reg) or pick(reg, i) is None:
            reg = [-1e9, 1e9, -1e9, 1e9]   # push: satisfy fixed neighbours only; movable neighbours ripple next pass
            for n in (succ[i] | pred[i]) - {i}:
                if D.cells[n][0] == 'M' or n in anchored: reg = inter(reg, ballR(n, REFF))
            pushed.add(i)
        p = pick(reg, i) if not empty(reg) else None
        if p is None: stuck.add(i); continue
        if i not in moved: moved[i] = bounds(i)
        move(i, p[1], p[2]); nmv += 1; stuck.discard(i)
    bad, be = census(); print('pass', it, 'moved', nmv, 'violating captures', len(bad), 'edges', len(be), flush=True)
    if nmv == 0 or not bad: break

# --- legalization with the V5 model's own row-site packer (same grid, macro halos, centre clock box) ---
X0, Y0, X1, Y1 = 4.32, 4.32, W - 4.32, H - 4.32; SX, SY = .054, .27
NX = int(round((X1 - X0) / SX)); NY = int(round((Y1 - Y0) / SY)); base = [bytearray(NX) for _ in range(NY)]
boxes = [(c[2] - 4.32, c[3] - 4.32, c[4] + 4.32, c[5] + 4.32) for c in D.cells.values() if c[0] == 'M']; boxes.append((W / 2 - 3, H / 2 - 3, W / 2 + 3, H / 2 + 3))
for x0, y0, x1, y1 in boxes:
    lo = max(0, int(math.floor((x0 - X0) / SX))); hi = min(NX, int(math.ceil((x1 - X0) / SX)))
    for j in range(max(0, int(math.floor((y0 - Y0) / SY))), min(NY, int(math.ceil((y1 - Y0) / SY)))): base[j][lo:hi] = b'\1' * (hi - lo)
def pack(order):
    occ = [bytearray(x) for x in base]; dmax = []
    for i in order:
        c = D.cells[i]; w = int(math.ceil((c[4] - c[2] + .54 - .00001) / SX)); tx, ty = G.ctr(c)
        ix = max(0, min(NX - w, int(round((tx - (c[4] - c[2]) / 2 - X0) / SX)))); iy = max(0, min(NY - 1, int(round((ty - .135 - Y0) / SY)))); z = b'\0' * w; best = None
        for radius in (0, 8, 40, 160, NY):
            for j in range(max(0, iy - radius), min(NY, iy + radius + 1)):
                if best is not None and abs((j - iy) * SY) > best[0]: continue
                for k in (occ[j].rfind(z, 0, min(NX, ix + w)), occ[j].find(z, ix, NX)):
                    if k < 0: continue
                    v = (abs((j - iy) * SY) + abs((k - ix) * SX), j, k)
                    if best is None or v < best: best = v
            if best is not None and radius * SY >= best[0]: break
        _, j, k = best; occ[j][k:k + w] = b'\1' * w; x = X0 + k * SX; y = Y0 + j * SY; dmax.append(best[0])
        D.cells[i] = c[:2] + (x, y, x + c[4] - c[2], y + c[5] - c[3]) + c[6:]
    return max(dmax)
ffs = [i for i, c in D.cells.items() if c[0] == 'S']
order = sorted(ffs, key=lambda i: (i not in anchored, i not in moved, i))
lmax = pack(order); badL, beL = census(); print('after legalization: captures', len(badL), 'edges', len(beL), 'max legal disp', round(lmax, 2), flush=True)
legal_hist = [dict(round=0, captures=len(badL), edges=len(beL), max_legal_disp=round(lmax, 2))]
for rnd in range(1, int(sys.argv[3]) if len(sys.argv) > 3 else 7):
    if not badL: break
    for it in range(8):
        bad, be = census(); ends = Counter()
        for s_, t_ in be: ends[s_] += 1; ends[t_] += 1
        nmv = 0
        for i, _ in ends.most_common():
            if D.cells[i][0] != 'S' or i in anchored: continue
            reg = [-1e9, 1e9, -1e9, 1e9]
            for n in (succ[i] | pred[i]) - {i}: reg = inter(reg, ballR(n, REFF))
            if empty(reg) or pick(reg, i) is None:
                reg = [-1e9, 1e9, -1e9, 1e9]
                for n in (succ[i] | pred[i]) - {i}:
                    if D.cells[n][0] == 'M' or n in anchored: reg = inter(reg, ballR(n, REFF))
                pushed.add(i)
            p = pick(reg, i) if not empty(reg) else None
            if p is None: continue
            if i not in moved: moved[i] = bounds(i)
            move(i, p[1], p[2]); nmv += 1
        if nmv == 0: break
    order = sorted(ffs, key=lambda i: (i not in anchored, i not in moved, i))
    lmax = pack(order); badL, beL = census(); print('legal round', rnd, 'captures', len(badL), 'edges', len(beL), flush=True)
    legal_hist.append(dict(round=rnd, captures=len(badL), edges=len(beL), max_legal_disp=round(lmax, 2)))
disp = []
for i, b0 in moved.items():
    b1 = bounds(i); disp.append(max(abs(b1[0] - b0[0]), abs(b1[2] - b0[2])))
disp.sort()
badM, beM = census()
# --- replication pass on remaining edges (source movable, all incident regions not jointly feasible) ---
rep_rows = []; added = 0; fixed_caps = set(); still = Counter()
srcs = Counter(s for s, t in beM)
for s, nb in srcs.most_common():
    fam_s = fam(nm(s))
    if D.cells[s][0] == 'M' or s in anchored: still['fixed source: ' + fam_s] += nb; continue
    U = [-1e9, 1e9, -1e9, 1e9]
    for u in pred[s] - {s}:
        if D.cells[u][0] == 'S' and fam(nm(u)) == fam_s and u not in anchored: continue  # replicated together (counter whole)
        U = inter(U, ballR(u, REFF))
    regs = sorted([(t, inter(U, ballR(t, REFF))) for t in succ[s] - {s}], key=lambda x: x[1][1])
    if any(not in_die(r) for t, r in regs): still['upstream of replica cannot reach sink: ' + fam_s] += nb; continue
    copies = []
    for t, r in regs:
        for cp in copies:
            nr = inter(cp[0], r)
            if in_die(nr): cp[0] = nr; cp[1].append(t); break
        else: copies.append([r, [t]])
    if len(copies) == 1: still['movable alone (legalization residue): ' + fam_s] += nb; continue
    added += len(copies) - 1
    rep_rows.append((fam_s, len(succ[s]), len(copies)))
    for t in succ[s]: fixed_caps.add((s, t))
remaining_caps = {t for s, t in beM if (s, t) not in fixed_caps}
fr = defaultdict(lambda: [0, 0, 0, 0])
for f, fo, k in rep_rows: e = fr[f]; e[0] += 1; e[1] = max(e[1], fo); e[2] = max(e[2], k); e[3] += k - 1
# residual families
resfam = Counter()
for s, t in beM:
    if (s, t) not in fixed_caps: resfam[(fam(nm(s)), fam(nm(t)), D.cells[s][0] == 'M', s in anchored, D.cells[t][0] == 'M', t in anchored)] += 1
res = dict(kind='ESTIMATE_ONLY_MOVE_THEN_REPLICATE', R=R, REFF=REFF, baseline_captures=len(bad0), baseline_edges=len(be0),
           legalization=legal_hist, after_move_captures=len(badM), after_move_edges=len(beM), moved_regs=len(moved), pushed_regs=len(pushed),
           move_disp_um=dict(p50=disp[len(disp) // 2] if disp else 0, p90=disp[int(.9 * len(disp))] if disp else 0, max=disp[-1] if disp else 0),
           replication_added_flops=added, replicated_families={k: dict(regs=v[0], fanout_max=v[1], k_max=v[2], added=v[3]) for k, v in fr.items()},
           after_replication_captures=len(remaining_caps), not_fixable=dict(still),
           residual_edge_families=[dict(n=n, src=k[0], cap=k[1], src_macro=k[2], src_anch=k[3], cap_macro=k[4], cap_anch=k[5]) for k, n in resfam.most_common(25)])
diag = {}
for s_, t_ in beM:
    if (s_, t_) in fixed_caps: continue
    if D.cells[s_][0] == 'M' or D.cells[t_][0] == 'M':
        m = s_ if D.cells[s_][0] == 'M' else t_; o = t_ if m == s_ else s_
        reg = [-1e9, 1e9, -1e9, 1e9]
        for n in (succ[o] | pred[o]) - {o}: reg = inter(reg, ballR(n, R))
        drv = sorted(pred[o] | succ[o], key=lambda n: -dist(n, o))[:3]
        diag.setdefault(fam(nm(s_)) + ' -> ' + fam(nm(t_)), []).append(dict(other=nm(o), d=round(dist(s_, t_), 1), joint_region_gap_um=round(max(reg[0] - reg[1], reg[2] - reg[3]) / 2, 1),
             far=[(nm(n), [round(v, 1) for v in D.cells[n][2:4]], round(dist(n, o), 1)) for n in drv]))
res['residual_diag'] = {k: v[:4] for k, v in diag.items()}; res['residual_diag_counts'] = {k: len(v) for k, v in diag.items()}
(OUT / ('move_replicate_%g%s.json' % (REFF, os.environ.get('TAG', '')))).write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps(res, indent=1))
# --- cross-check with the V5 model's own patched census (geom_rules.r2r_metrics + full memory box) on the legalized positions ---
import inspect
src = inspect.getsource(G.r2r_metrics)
src = src.replace('memories=set(); unknown=[]', 'memories={i for i,c in D.cells.items() if c[0]=="M"}; unknown=[]')
ns = dict(G.__dict__); exec(src, ns); rc = ns['r2r_metrics'](D)
print('MODEL CENSUS on legalized positions:', {k: rc[k] for k in ('r2r_captures_gt405', 'r2r_max', 'r2r_captures', 'r2r_worst')}, flush=True)
res['model_census_legalized'] = {k: rc[k] for k in ('r2r_captures_gt405', 'r2r_max', 'r2r_captures', 'r2r_worst')}
(OUT / ('move_replicate_%g%s.json' % (REFF, os.environ.get('TAG', '')))).write_text(json.dumps(res, indent=1) + '\n')
(OUT / ('sites_legal_%g%s.json' % (REFF, os.environ.get('TAG', '')))).write_text(json.dumps([dict(name=D.cells[i][6], master=D.cells[i][1], xy=[round(D.cells[i][2], 3), round(D.cells[i][3], 3)]) for i in ffs]) + '\n')
