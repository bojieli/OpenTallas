# S81-DIE10 10-20: mu5 GRT overflow CLASS TABLE from the dumped post-GRT guides (dump_guides.py) -- read-only analysis.
# usage: python3 grt_class.py <dumpdir> <case.json> <out.json>
# Model: per gcell & layer, demand = #guides covering the gcell on that layer (GRT guides are gcell-aligned);
# capacity = tracks across the gcell (perpendicular extent / pitch) x (1 - GRT layer adjustment) x (1 - OBS/pin cover).
# Totals are calibrated against GRT's own per-layer overflow (reported side by side); classes are by gcell location.
import json, sys, collections
import numpy as np
from scipy import ndimage

D, CASE, OUT = sys.argv[1:4]
meta = json.load(open(f'{D}/meta.json')); dbu = meta['dbu']
gx = np.array(meta['gx'], dtype=np.int64); gy = np.array(meta['gy'], dtype=np.int64)
X0, Y0, X1, Y1 = meta['die']
if gx[-1] < X1: gx = np.append(gx, X1)
if gy[-1] < Y1: gy = np.append(gy, Y1)
NX, NY = len(gx) - 1, len(gy) - 1
LAY = {v['level']: (k, v) for k, v in meta['layers'].items()}
TP = {'M2': .64, 'M3': .64, 'M4': .048, 'M5': .048, 'M6': .064, 'M7': .064, 'M8': .08, 'M9': .08}
ADJ = {2: .5, 3: .5, 4: .3, 5: .3, 6: .2, 7: .2, 8: 0., 9: 0.}
gdt = np.dtype([('l', 'u1'), ('c', 'u1'), ('sp', 'u1'), ('x0', '<i4'), ('y0', '<i4'), ('x1', '<i4'), ('y1', '<i4')])
odt = np.dtype([('l', 'u1'), ('x0', '<i4'), ('y0', '<i4'), ('x1', '<i4'), ('y1', '<i4')])
G = np.fromfile(f'{D}/guides.bin', dtype=gdt)
O = np.fromfile(f'{D}/obs.bin', dtype=odt)
cls_name = {v: k for k, v in meta['classes'].items()}


def idx(lo, hi, grid, n):
    a = np.clip(np.searchsorted(grid, lo, 'right') - 1, 0, n - 1)
    b = np.clip(np.searchsorted(grid, np.maximum(hi - 1, lo), 'right') - 1, 0, n - 1)
    return a, b


def rect_add(shape, a0, a1, b0, b1, w=None):
    d = np.zeros((shape[0] + 1, shape[1] + 1), dtype=np.float64)
    w = np.ones(len(a0)) if w is None else w
    np.add.at(d, (a0, b0), w); np.add.at(d, (a1 + 1, b0), -w); np.add.at(d, (a0, b1 + 1), -w); np.add.at(d, (a1 + 1, b1 + 1), w)
    return d.cumsum(0).cumsum(1)[:shape[0], :shape[1]]


# --- demand per layer (x index first)
dem = {}; dem_c = {}
for lv in range(2, 10):
    g = G[G['l'] == lv]
    if not len(g): continue
    ix0, ix1 = idx(g['x0'], g['x1'], gx, NX); iy0, iy1 = idx(g['y0'], g['y1'], gy, NY)
    dem[lv] = rect_add((NX, NY), ix0, ix1, iy0, iy1)
    dem_c[lv] = (g['c'], ix0, ix1, iy0, iy1)
# --- capacity per layer
gw = np.diff(gx).astype(float); gh = np.diff(gy).astype(float)
cap = {}
for lv, (nm, L) in LAY.items():
    if lv < 2 or lv not in ADJ: continue
    pitch = TP[nm] * dbu      # GRT track pitch (GRT-0088 / make_tracks), not the LEF pitch
    horiz = str(L['dir']).upper().startswith('HOR')
    tr = np.floor((gh if horiz else gw) / pitch)
    base = (np.broadcast_to(tr[None, :], (NX, NY)) if horiz else np.broadcast_to(tr[:, None], (NX, NY))) * (1 - ADJ[lv])
    cov = np.zeros((NX, NY))
    for code in (lv, 100 + lv):
        o = O[O['l'] == code]
        if not len(o): continue
        # fractional OBS cover: area of each box clipped to its gcell span, spread uniformly (good for big OBS)
        ix0, ix1 = idx(o['x0'], o['x1'], gx, NX); iy0, iy1 = idx(o['y0'], o['y1'], gy, NY)
        area = (o['x1'] - o['x0']).astype(float) * (o['y1'] - o['y0'])
        cells = (gx[ix1 + 1] - gx[ix0]).astype(float) * (gy[iy1 + 1] - gy[iy0])
        cov += rect_add((NX, NY), ix0, ix1, iy0, iy1, area / np.maximum(cells, 1))
    if lv == 7:
        cov = cov6      # GRT blocks M7 over every macro footprint like M6 (GRT-0053 M7 resources == M6), OBS dump has no M7
    if lv == 6:
        cov6 = cov.copy()
    cap[lv] = base * (1 - np.clip(cov, 0, 1))
# --- region labels from instances
insts = json.load(open(f'{D}/insts.json'))
q = json.load(open(CASE))
standin = {k.split(':', 1)[1] for k in q['census'] if k.startswith('standin:')}


def mclass(m):
    for pre, c in (('ot_hbm3e_phy', 'PHY'), ('rv_phy_hbm', 'PHY'), ('dsfd_ctrl_rg2', 'CTRL'), ('rv_ctrl', 'CTRL'),
                   ('rv_f_', 'frame'), ('rv_rsv', 'svc_rs'), ('rv_s_', 'slice_col'), ('rv_lk', 'serdes_lk'), ('rv_bk_sel', 'bk_topk'),
                   ('rv_gunit', 'gunit'), ('rv_seqhost', 'seq_host'), ('dsfd_dvrlyh_', 'relay_h'), ('dsfd_rly_', 'relay_1b'),
                   ('dsfd_dvland_', 'frame_landing'), ('col_h', 'frame'), ('dsdv_svc_rs', 'svc_rs'), ('ot_s81sl_', 'slice_col'),
                   ('ot_pdie_serdes', 'serdes'), ('dsdv_bk_', 'bk_topk'), ('dsdv_gunit', 'gunit'), ('dsdv_seq_host', 'seq_host'),
                   ('ot_sram', 'sram')):
        if m.startswith(pre): return c
    return 'other_macro'


CL = ['channel']; cid = {'channel': 0}
lab = np.zeros((NX, NY), dtype=np.int16); stat = np.zeros((NX, NY), dtype=np.int8)   # 1 closed, 2 stand-in
order = sorted([i for i in insts if i[6]], key=lambda i: -(i[4] - i[2]) * (i[5] - i[3]))   # big first, small overwrite
for nm, m, x0, y0, x1, y1, blk in order:
    c = mclass(m); cid.setdefault(c, len(CL)) == len(CL) and CL.append(c)
    a0, a1 = idx(np.array([x0]), np.array([x1]), gx, NX); b0, b1 = idx(np.array([y0]), np.array([y1]), gy, NY)
    lab[a0[0]:a1[0] + 1, b0[0]:b1[0] + 1] = cid[c]
    stat[a0[0]:a1[0] + 1, b0[0]:b1[0] + 1] = 2 if (m in standin or m.startswith('rv_')) else 1
# channel gcells -> nearest macro class (distance transform), and distance in gcells
SMALL = {cid.get(k) for k in ('relay_h', 'relay_1b', 'frame_landing') if k in cid}
big = np.where(np.isin(lab, list(SMALL)), 0, lab)
dist, (ni, nj) = ndimage.distance_transform_edt(big == 0, return_indices=True)
near = big[ni, nj]
res_region = {}
# PHY face / ctrl seam zones: within 400 um of the PHY macro bbox
phy = [i for i in insts if i[6] and mclass(i[1]) == 'PHY']
label_status = {mclass(i[1]): ('standin' if i[1].startswith('rv_') else 'closed') for i in insts if i[6]}
ctrl = [i for i in insts if i[6] and mclass(i[1]) == 'CTRL']
cxm = (gx[:-1] + gx[1:]) / 2.; cym = (gy[:-1] + gy[1:]) / 2.
def near_mask(boxes, um):
    m_ = np.zeros((NX, NY), dtype=bool)
    for nm, m, x0, y0, x1, y1, blk in boxes:
        dx = np.maximum(0, np.maximum(x0 - cxm, cxm - x1)) / dbu; dy = np.maximum(0, np.maximum(y0 - cym, cym - y1)) / dbu
        m_ |= (dx[:, None] ** 2 + dy[None, :] ** 2) <= um ** 2
    return m_
ZONES = {'PHY_face_400um': near_mask(phy, 400), 'ctrl_seam_200um_channel': near_mask(ctrl, 200) & (lab == 0)}
ZONES['rest_of_die'] = ~(ZONES['PHY_face_400um'] | ZONES['ctrl_seam_200um_channel'])
# --- overflow and tables
res = dict(schema='opentallas.s81_die10.grt_class.v1', dump=D, gcells=[NX, NY],
           gcell_um=[float(np.median(gw)) / dbu, float(np.median(gh)) / dbu], layers={}, by_class={}, by_zone={}, by_status={},
           hot_tiles=[], phy_face={}, by_region={}, net_class_in_overflow={})
ov = {}
for lv in sorted(dem):
    if lv not in cap: continue
    o = np.maximum(0, dem[lv] - cap[lv]); ov[lv] = o
    nm = LAY[lv][0]
    res['layers'][nm] = dict(model_overflow=int(o.sum()), model_capacity=int(cap[lv].sum()), model_demand=int(dem[lv].sum()),
                             overflowed_gcells=int((o > 0).sum()))
tot = sum(ov.values())
for k in range(len(CL)):
    m_on = lab == k; m_ch = (lab == 0) & (near == k)
    row = {}
    for lv, o in ov.items():
        row[LAY[lv][0]] = dict(on=int(o[m_on].sum()) if k else 0, channel_near=int(o[m_ch].sum()))
    res['by_class'][CL[k]] = dict(total_on=int(tot[m_on].sum()) if k else 0, total_channel_near=int(tot[m_ch].sum()), layers=row,
                                  gcells_on=int(m_on.sum()) if k else 0)
for k in range(1, len(CL)):
    if k in SMALL: continue
    mk = (near == k) | (big == k)
    row = dict(total=int(tot[mk].sum()), over_block=int(tot[big == k].sum()))
    for sk in SMALL:
        row['over_' + CL[sk]] = int(tot[mk & (lab == sk)].sum())
    row['open_channel'] = int(tot[mk & (lab == 0)].sum())
    row['layers'] = {LAY[lv][0]: int(o[mk].sum()) for lv, o in ov.items()}
    res['by_region'][CL[k]] = row
# (2) net classes of guides crossing overflowed gcells (count of overflowed gcells each guide covers)
P = np.zeros((NX + 1, NY + 1)); 
for lv, (c, ix0, ix1, iy0, iy1) in dem_c.items():
    if lv not in ov: continue
    P[1:, 1:] = (ov[lv] > 0).cumsum(0).cumsum(1)
    hit = P[ix1 + 1, iy1 + 1] - P[ix0, iy1 + 1] - P[ix1 + 1, iy0] + P[ix0, iy0]
    for cc_, n in zip(*np.unique(c[hit > 0], return_counts=True)):
        res['net_class_in_overflow'].setdefault(cls_name.get(int(cc_), str(cc_)), {})[LAY[lv][0]] = int(n)
for zn, mz in ZONES.items():
    res['by_zone'][zn] = dict(total=int(tot[mz].sum()), layers={LAY[lv][0]: int(o[mz].sum()) for lv, o in ov.items()})
for s, sn in ((0, 'channel'), (1, 'over_closed_view'), (2, 'over_standin')):
    res['by_status'][sn] = int(tot[stat == s].sum())
# hot 1 mm tiles
T = max(1, int(round(1000 * dbu / np.median(gw))))
tx, ty = NX // T + 1, NY // T + 1
tt = np.zeros((tx, ty)); np.add.at(tt, (np.arange(NX)[:, None] // T * np.ones((1, NY), int), np.ones((NX, 1), int) * (np.arange(NY)[None, :] // T)), tot)
hot = np.argsort(tt.ravel())[::-1][:25]
for h in hot:
    i, j = divmod(int(h), ty)
    sl = (slice(i * T, (i + 1) * T), slice(j * T, (j + 1) * T))
    cc = collections.Counter()
    for k in range(len(CL)):
        v = tot[sl][(lab[sl] == k) | ((lab[sl] == 0) & (near[sl] == k))].sum()
        if v: cc[CL[k]] += float(v)
    # net classes of guides in the overflowed gcells of this tile
    nc = collections.Counter()
    hotmask = tot[sl] > 0
    for lv, (c, ix0, ix1, iy0, iy1) in dem_c.items():
        sel = (ix1 >= i * T) & (ix0 < (i + 1) * T) & (iy1 >= j * T) & (iy0 < (j + 1) * T)
        for cc_, n in zip(*np.unique(c[sel], return_counts=True)):
            nc[cls_name.get(int(cc_), str(cc_))] += int(n)
    res['hot_tiles'].append(dict(x_mm=[i * T * float(np.median(gw)) / dbu / 1000, (i + 1) * T * float(np.median(gw)) / dbu / 1000],
                                 y_mm=[j * T * float(np.median(gh)) / dbu / 1000, (j + 1) * T * float(np.median(gh)) / dbu / 1000],
                                 overflow=int(tt[i, j]), layers={LAY[lv][0]: int(o[sl].sum()) for lv, o in ov.items() if o[sl].sum()},
                                 classes={k: int(v) for k, v in cc.most_common(5)}, guide_net_classes=dict(nc.most_common(6)),
                                 overflowed_gcells=int(hotmask.sum())))
# PHY face cut-vs-track: for each PHY face, the gcell ring just outside it: demand / capacity per layer (crossing direction)
for nm, m, x0, y0, x1, y1, blk in phy:
    a0, a1 = idx(np.array([x0]), np.array([x1]), gx, NX); b0, b1 = idx(np.array([y0]), np.array([y1]), gy, NY)
    a0, a1, b0, b1 = int(a0[0]), int(a1[0]), int(b0[0]), int(b1[0])
    faces = dict(N=(slice(a0, a1 + 1), slice(min(b1 + 1, NY - 1), min(b1 + 2, NY))), S=(slice(a0, a1 + 1), slice(max(b0 - 1, 0), b0)),
                 E=(slice(min(a1 + 1, NX - 1), min(a1 + 2, NX)), slice(b0, b1 + 1)), W=(slice(max(a0 - 1, 0), a0), slice(b0, b1 + 1)))
    fr = {}
    for f, sl in faces.items():
        vert_cross = f in 'NS'      # crossing a N/S face = vertical wires
        row = {}
        for lv in sorted(dem):
            if lv not in cap: continue
            nmL, L = LAY[lv]; horiz = str(L['dir']).upper().startswith('HOR')
            if horiz == vert_cross: continue
            d_ = float(dem[lv][sl].sum()); c_ = float(cap[lv][sl].sum())
            row[nmL] = dict(demand=int(d_), capacity=int(c_), ratio=round(d_ / c_, 3) if c_ else None, overflow=int(ov[lv][sl].sum()))
        fr[f] = row
    rows = []
    for k in range(1, 13):
        jj = b1 + k
        if jj >= NY: break
        r_ = dict(row=k, y_um=float(gy[jj]) / dbu)
        for lv in (3, 5, 7):
            if lv in cap:
                d_ = float(dem[lv][a0:a1 + 1, jj].sum()); c_ = float(cap[lv][a0:a1 + 1, jj].sum())
                r_[LAY[lv][0]] = dict(demand=int(d_), capacity=int(c_), ratio=round(d_ / c_, 3) if c_ else None)
        r_['blocked_frac'] = round(float((lab[a0:a1 + 1, jj] != 0).mean()), 3)
        r_['ctrl_frac'] = round(float((lab[a0:a1 + 1, jj] == cid.get('CTRL', -1)).mean()), 3)
        rows.append(r_)
    res.setdefault('phy_north_cut_rows', {})[nm] = rows
    res['phy_face'][nm] = dict(master=m, bbox_um=[x0 / dbu, y0 / dbu, x1 / dbu, y1 / dbu], faces=fr)
res['classes_present'] = CL
res['class_view_status'] = label_status
res['total_model_overflow'] = int(tot.sum())
json.dump(res, open(OUT, 'w'), indent=1)
print('GRT_CLASS_DONE', OUT, res['total_model_overflow'], json.dumps({k: v['model_overflow'] for k, v in res['layers'].items()}))
