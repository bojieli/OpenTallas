"""DIE-HBM-61/PLAN d44v RE-FORM slot planner (plan-time; OWNER 11-03 shape rules).
python3 reform.py PLANDIR GEOMCOLL.json BATCH.txt OUT.json"""
import json, sys, math, collections
pd, gj, bt, out = sys.argv[1:5]
P = json.load(open(pd + '/die_plan.json')); CM = json.load(open(pd + '/core_macros.json'))['cores']
G = json.load(open(gj)); B = [l.strip() for l in open(bt) if l.strip()]
STEP, HALO, PPL = 8.64, 4.32, 5.0          # outline step, core halo, pins/um per layer (remap 0.192 spacing)
FILL_T, FILL_LO, FILL_HI, ASP, CELLS_MAX, SINKS_PER_ENTRY = 0.40, 0.35, 0.45, 2.0, 150000, 5000
inst = collections.defaultdict(list)
for tn, t in P['partition_types'].items():
    for h in t.get('hard_cores') or []:
        inst[h['module']].append((tn, h))
def faces(pins, W, H):
    f = collections.defaultdict(collections.Counter)
    for q in pins:
        x, y = q['x'], q['y']
        k = 'S' if y <= .5 else 'N' if y >= H - .5 else 'W' if x <= .5 else 'E' if x >= W - .5 else 'in'
        f[k][q.get('layer')] += 1
    return f
def room(tn, h):
    """max centred growth (um each side, x and y) of this instance before hitting a neighbour core (+halo) or the type outline"""
    t = P['partition_types'][tn]; TW, TH = t['outline_um']; x0, y0 = h['origin_um']; w, hh = h['outline_um']
    x1, y1 = x0 + w, y0 + hh
    gx, gy = min(x0, TW - x1), min(y0, TH - y1)
    for o in t['hard_cores']:
        if o is h: continue
        a0, b0 = o['origin_um']; a1, b1 = a0 + o['outline_um'][0], b0 + o['outline_um'][1]
        if b1 > y0 - 1 and b0 < y1 + 1:   # overlaps in y band -> limits x growth
            if a1 <= x0: gx = min(gx, x0 - a1 - HALO)
            elif a0 >= x1: gx = min(gx, a0 - x1 - HALO)
        if a1 > x0 - 1 and a0 < x1 + 1:
            if b1 <= y0: gy = min(gy, y0 - b1 - HALO)
            elif b0 >= y1: gy = min(gy, b0 - y1 - HALO)
    return round(gx, 2), round(gy, 2)
def up(v): return round(math.ceil(v / STEP - 1e-9) * STEP, 3)
rows = []
for m in B:
    L = inst.get(m)
    if not L: rows.append(dict(module=m, decision='NOT_IN_PLAN')); continue
    tn, h = L[0]; W, H = h['outline_um']
    pins = json.load(open(pd + '/' + h['pins_file'])) if h.get('pins_file') else []
    f = faces(pins, W, H)
    g = (G.get(m) or {}).get('metrics') or {}
    mac = (CM.get(m) or {}).get('macros') or []
    mac_area = sum((r['rect_um'][2] - r['rect_um'][0]) * (r['rect_um'][3] - r['rect_um'][1]) for r in mac)
    fill = g.get('fill_of_free'); cells = g.get('std_cells'); sinks = g.get('clock_sinks')
    free = W * H - mac_area
    A = fill * free if fill is not None else None
    lay = lambda k: max(1, len(f[k]))
    need_w = max(sum(f['N'].values()) / (PPL * lay('N')), sum(f['S'].values()) / (PPL * lay('S')))
    need_h = max(sum(f['W'].values()) / (PPL * lay('W')), sum(f['E'].values()) / (PPL * lay('E')))
    if mac:  # macros keep their bounding box + 10.8 channels on all sides (macros on the edge: inset only)
        mw = max(r['rect_um'][2] for r in mac) - min(r['rect_um'][0] for r in mac)
        mh = max(r['rect_um'][3] for r in mac) - min(r['rect_um'][1] for r in mac)
    else: mw = mh = 0
    rmx = [room(t2, h2) for t2, h2 in L]
    gx = min(r[0] for r in rmx); gy = min(r[1] for r in rmx)
    rec = dict(module=m, n_inst=len(L), types=sorted({t for t, _ in L}), old=[W, H], old_aspect=round(max(W, H) / min(W, H), 2),
               old_fill=fill, cells=cells, sinks=sinks, macros=len(mac), macro_area=round(mac_area), cell_area=A and round(A),
               pins={k: dict(v) for k, v in f.items()}, pin_need_wh=[round(need_w, 1), round(need_h, 1)],
               macro_bbox=[round(mw, 1), round(mh, 1)], room_xy=[gx, gy],
               clock_regions=math.ceil(sinks / SINKS_PER_ENTRY) if sinks else None, flags=[])
    if cells and cells > CELLS_MAX: rec['flags'].append('CELLS>150k: SPLIT (source event) n=%d' % math.ceil(cells / CELLS_MAX))
    if A is None: rec['decision'] = 'NO_GEOM_DATA'; rows.append(rec); continue
    S = A / FILL_T + mac_area * (1.15 if mac else 1)
    best = None
    w = max(up(need_w), up(mw + 2 * 4.32) if mac else 0, STEP)
    while w <= 2000:
        hh = max(up(need_h), up(mh + 2 * 4.32) if mac else 0, up(S / w), up(w / ASP))
        if max(w, hh) / min(w, hh) <= ASP + 1e-6:
            sc = (abs(w * hh - S) / S, abs(w - W) + abs(hh - H))
            if best is None or sc < best[0]: best = (sc, w, hh)
        w = round(w + STEP, 3)
    _, W2, H2 = best
    nf = A / (W2 * H2 - mac_area)
    rec.update(new=[W2, H2], new_aspect=round(max(W2, H2) / min(W2, H2), 2), new_fill=round(nf, 3),
               grow_xy=[round((W2 - W) / 2, 2), round((H2 - H) / 2, 2)])
    bound = 'pins' if (W2 * H2 > S * 1.1) else 'fill'
    rec['bound'] = bound
    fits = rec['grow_xy'][0] <= gx + 1e-6 and rec['grow_xy'][1] <= gy + 1e-6
    rec['fits_parent'] = fits
    in_band = FILL_LO <= fill <= FILL_HI and rec['old_aspect'] <= ASP
    if in_band: rec['decision'] = 'KEEP (in band)'
    else: rec['decision'] = 'RESHAPE' if fits else 'RESHAPE-NOFIT'
    rows.append(rec)
json.dump(rows, open(out, 'w'), indent=1)
for r in rows:
    if 'new' not in r: print(r['module'], r['decision']); continue
    print(f"{r['module'][:44]:44s} {r['decision']:13s} {r['old'][0]:.0f}x{r['old'][1]:.0f} f{r['old_fill']:.3f} a{r['old_aspect']} -> {r['new'][0]:.0f}x{r['new'][1]:.0f} f{r['new_fill']} a{r['new_aspect']} {r['bound']} grow{r['grow_xy']} room{r['room_xy']} pinneed{r['pin_need_wh']} mac{r['macros']} cr{r['clock_regions']} {';'.join(r['flags'])}")
