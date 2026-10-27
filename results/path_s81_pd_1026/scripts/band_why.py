"""PATH-S81-PD: why do the 60 landing bands fail?  For each still-failing (type,bus) on the composed plan:
need area, free macro-free area within reach (excluding the type's already-placed bands), largest single legal
rectangle (any aspect, same legality as _grid_scan), and a greedy multi-bank split (<=4 disjoint banks, each within reach).
usage: band_why.py PLAN SIDE OUT.json"""
import json, sys, math, collections
sys.path.insert(0, 'tools/die_plan')
import numpy as np
import clock_landing_plan as CLP, reset_tree as RT
P = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
T = P['partition_types']; F = S['collector']['placement_failures']
g = 2.16; margin = 17.28; reach = 405 - 2.16


def obstacles(t):
    obs = [list(o) for o in RT.blockages(t)]
    kinds = ['core'] * len(obs)
    for slot in t.get('ft_slots', []):
        cell = slot.get('bit_site_cell_um', [1.404, .27])
        for st in slot.get('bit_sites_um', []):
            if st:
                obs.append([min(p[0] for p in st)-cell[0]/2, min(p[1] for p in st)-cell[1]/2, max(p[0] for p in st)+cell[0]/2, max(p[1] for p in st)+cell[1]/2]); kinds.append('ft')
        if not slot.get('bit_sites_um'):
            for x, y in slot.get('regs_um', []):
                obs.append([x-2.16, y-2.16, x+2.16, y+2.16]); kinds.append('ft')
    lc = t.get('clock', {}).get('landing_contract', {})
    for b in (lc.get('bands') or {}).values():
        if b.get('rect_um'):
            obs.append(b['rect_um']); kinds.append('band')
    return obs, kinds


def occ_grid(w, h, obs):
    nx, ny = int(w // g), int(h // g)
    occ = np.zeros((nx, ny), bool)
    for o in obs:
        i0, i1 = max(0, int(math.floor(o[0]/g))), min(nx, int(math.ceil(o[2]/g)))
        j0, j1 = max(0, int(math.floor(o[1]/g))), min(ny, int(math.ceil(o[3]/g)))
        if i1 > i0 and j1 > j0: occ[i0:i1, j0:j1] = True
    m = int(math.ceil(margin/g)); occ[:m, :] = occ[-m:, :] = occ[:, :m] = occ[:, -m:] = True
    return occ


def best_rect(occ, px, py, need_cells, min_side=4):
    """largest-area legal rectangle with all corners within reach; brute over heights with histogram method restricted to reach."""
    nx, ny = occ.shape
    X = (np.arange(nx)) * g; Y = (np.arange(ny)) * g
    best = (0, None)
    Sm = np.zeros((nx+1, ny+1), np.int64); Sm[1:, 1:] = occ.cumsum(0).cumsum(1)
    for bw in sorted({min_side, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96, 128, 192, 256}):
        if bw > nx: continue
        for bh in sorted({min_side, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96, 128, 192, 256, 384}):
            if bh > ny or bw*bh <= best[0]: continue
            blk = Sm[bw:, bh:] - Sm[:-bw, bh:] - Sm[bw:, :-bh] + Sm[:-bw, :-bh]
            ii, jj = np.nonzero(blk == 0)
            if not len(ii): continue
            x0 = ii*g; y0 = jj*g; x1 = x0+bw*g; y1 = y0+bh*g
            far = np.maximum(abs(x0-px), abs(x1-px)) + np.maximum(abs(y0-py), abs(y1-py))
            ok = np.nonzero(far <= reach)[0]
            if len(ok):
                k = ok[0]; best = (bw*bh, [float(x0[k]), float(y0[k]), float(x1[k]), float(y1[k])])
    return best


out = []
used_by_type = collections.defaultdict(list)
for f in F:
    tn = f['type']; t = T[tn]; w, h = t['outline_um']
    b = CLP._bus_geom(t, f['bus']); width = int(b.get('width') or 2)
    rw = 64*math.ceil((width+1)/64); area = (5*rw*.2916 + 4*rw*.0729 + 160*.2916)/.40
    px, py = CLP._bus_xy(t, f['bus'])
    obs, kinds = obstacles(t)
    obs = obs + used_by_type[tn]
    occ = occ_grid(w, h, obs)
    nx, ny = occ.shape
    XX, YY = np.meshgrid((np.arange(nx)+.5)*g, (np.arange(ny)+.5)*g, indexing='ij')
    near = (np.abs(XX-px)+np.abs(YY-py)) <= reach
    free_near = float(((~occ) & near).sum()*g*g)
    # what blocks the face strip directly behind the window: fraction of near cells by kind
    kind_area = collections.Counter()
    for o, k in zip(obs, kinds + ['newband']*(len(obs)-len(kinds))):
        i0, i1 = max(0, int(o[0]//g)), min(nx, int(math.ceil(o[2]/g)))
        j0, j1 = max(0, int(o[1]//g)), min(ny, int(math.ceil(o[3]/g)))
        if i1 > i0 and j1 > j0: kind_area[k] += float(near[i0:i1, j0:j1].sum()*g*g)
    need_cells = area/(g*g)
    a1, r1 = best_rect(occ, px, py, need_cells)
    # greedy split: take best rects repeatedly until area covered (<=4 banks)
    occ2 = occ.copy(); got = 0.0; banks = []
    for _ in range(4):
        a, r = best_rect(occ2, px, py, need_cells)
        if not r: break
        banks.append(r); got += a*g*g
        i0, j0 = int(round(r[0]/g)), int(round(r[1]/g)); i1, j1 = int(round(r[2]/g)), int(round(r[3]/g))
        occ2[max(0, i0-1):i1+1, max(0, j0-1):j1+1] = True
        if got >= area: break
    rec = dict(type=tn, bus=f['bus'], face=b['face'], width=width, window=b['window_um'], pin=[round(px, 2), round(py, 2)],
               need_um2=round(area), free_near_um2=round(free_near), near_blocked_by={k: round(v) for k, v in kind_area.items()},
               best_single_um2=round(a1*g*g), best_single=r1, split_banks=len(banks), split_um2=round(got), split_ok=got >= area,
               cores=[(c.get('name'), c.get('origin_um'), c.get('outline_um'), c.get('orient')) for c in t.get('hard_cores', []) or []],
               outline=t['outline_um'])
    out.append(rec)
    if got >= area: used_by_type[tn] += banks
json.dump(out, open(sys.argv[3], 'w'), indent=1)
print('fails', len(out), 'free_near>=need', sum(r['free_near_um2'] >= r['need_um2'] for r in out),
      'split<=4 ok', sum(r['split_ok'] for r in out))
for r in out:
    print(r['type'][:40], r['bus'], r['face'], 'w', r['width'], 'need', r['need_um2'], 'free', r['free_near_um2'], 'single', r['best_single_um2'],
          'split', r['split_banks'], r['split_ok'], r['near_blocked_by'])
