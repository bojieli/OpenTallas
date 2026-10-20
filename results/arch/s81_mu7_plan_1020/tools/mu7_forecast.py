# S81-MU7PLAN 10-20: calibrated GRT congestion forecast for the mu7 variants (M7-cap / M8-open) from the mu5k guide dump.
# usage: python3 mu7_forecast.py <grt_class.py> <dumpdir> <case.json> <out.json>
# Reuses grt_class.py (S81-DIE10 04a5c1233) demand/capacity/region model (lines before '# --- overflow and tables').
# Pooled-direction model: per gcell, H demand/capacity = sum over H layers (M2,M4,M6[,M8]), V = (M3,M5,M7[,M9]);
# both smoothed over a w x w gcell window (GRT detour radius); overflow_dir = sum max(0, Ds - Cs);
# calibrated per direction to GRT's own mu5k per-layer overflow (k_H, k_V). Variants change capacity only (same demand).
import sys, json
import numpy as np
from scipy import ndimage
SRC, D, CASE, OUT = sys.argv[1:5]
src = open(SRC).read().split('# --- overflow and tables')[0]
sys.argv = ['grt_class.py', D, CASE, OUT]
exec(compile(src, SRC, 'exec'))
GRT = dict(M2=31574, M3=81322, M4=332457, M5=227272, M6=155182, M7=26561)
H, V = [2, 4, 6], [3, 5, 7]
GRT_H = sum(GRT['M%d' % l] for l in H); GRT_V = sum(GRT['M%d' % l] for l in V)
# M8/M9 capacity: no OBS on M8/M9 in the dump (macros block M2-M7 only); adj 0.20 like M6/M7
def free_cap(lv, adj=0.20):
    nm, L = LAY[lv]; pitch = TP[nm] * dbu; horiz = str(L['dir']).upper().startswith('HOR')
    tr = np.floor((gh if horiz else gw) / pitch)
    return (np.broadcast_to(tr[None, :], (NX, NY)) if horiz else np.broadcast_to(tr[:, None], (NX, NY))) * (1 - adj)
cap8, cap9 = free_cap(8), free_cap(9)
DH = sum(dem.get(l, 0) for l in H) + dem.get(8, 0); DV = sum(dem.get(l, 0) for l in V) + dem.get(9, 0)
CH = sum(cap[l] for l in H); CV = sum(cap[l] for l in V)
# open-channel tracks per um per direction (no macro cover), for channel-width sizing
tH = sum((1 - ADJ[l]) / TP[LAY[l][0]] for l in H); tV = sum((1 - ADJ[l]) / TP[LAY[l][0]] for l in V)
t8 = 0.8 / TP['M8']
gum = float(np.median(gw)) / dbu
big_k = {CL[k]: k for k in range(len(CL))}
reg = {}
for name in ('frame', 'slice_col', 'svc_rs', 'CTRL', 'PHY', 'seq_host', 'gunit', 'bk_topk', 'serdes_lk'):
    k = big_k.get(name)
    if k is not None: reg[name] = (near == k) | (big == k)
res = dict(schema='opentallas.s81_mu7plan.forecast.v1', dump=D, grt_mu5k=GRT, grt_H=GRT_H, grt_V=GRT_V,
           tracks_per_um=dict(H_M2M4M6=tH, V_M3M5M7=tV, M8=t8), gcell_um=gum, windows={})
for w in (3, 5, 9):
    sm = lambda a: ndimage.uniform_filter(np.asarray(a, dtype=np.float64), size=w, mode='nearest')
    DHs, DVs, CHs, CVs, C8s = sm(DH), sm(DV), sm(CH), sm(CV), sm(cap8)
    oH0 = np.maximum(0, DHs - CHs); oV0 = np.maximum(0, DVs - CVs)
    kH = GRT_H / oH0.sum(); kV = GRT_V / oV0.sum()
    oH8 = np.maximum(0, DHs - CHs - C8s)
    out = dict(k_H=kH, k_V=kV)
    def rows(oH, oV):
        r = dict(total=kH * oH.sum() + kV * oV.sum(), H=kH * oH.sum(), V=kV * oV.sum())
        r['by_region'] = {n: int(kH * oH[m].sum() + kV * oV[m].sum()) for n, m in reg.items()}
        # channel sizing: added die height for H excess (strip across the die per gcell row), width for V excess
        eH = kH * oH; eV = kV * oV
        r['add_height_um_M2M7'] = float(eH.max(0).sum() / tH)        # sum over y of max over x
        r['add_width_um_M2M7'] = float(eV.max(1).sum() / tV)
        r['add_height_um_55pct'] = float((kH * np.maximum(0, DHs - 0.55 * CHs)).max(0).sum() / tH)
        r['add_width_um_55pct'] = float((kV * np.maximum(0, DVs - 0.55 * CVs)).max(1).sum() / tV)
        r['overflow_rows_H'] = int((eH.max(0) > 0).sum()); r['overflow_cols_V'] = int((eV.max(1) > 0).sum())
        r['by_zone'] = {z: dict(H=int(eH[m].sum()), V=int(eV[m].sum())) for z, m in ZONES.items()}
        rest = ZONES['rest_of_die']
        r['add_height_um_rest'] = float(np.where(rest, eH, 0).max(0).sum() / tH)
        r['add_width_um_rest'] = float(np.where(rest, eV, 0).max(1).sum() / tV)
        return r
    out['base'] = rows(oH0, oV0)
    out['m8_open'] = rows(oH8, oV0)
    out['m8_m9_open_ref'] = rows(oH8, np.maximum(0, DVs - CVs - sm(cap9)))
    # M8-open with H lanes rerouted: fraction of the H excess absorbed by M8 in the hot PHY/CTRL zone
    out['m8_open']['phy_zone_H_base'] = int(kH * oH0[ZONES['PHY_face_400um']].sum())
    out['m8_open']['phy_zone_H_m8'] = int(kH * oH8[ZONES['PHY_face_400um']].sum())
    res['windows'][w] = out
json.dump(res, open(OUT, 'w'), indent=1, default=float)
print('MU7_FORECAST_DONE', OUT, json.dumps({w: dict(base=round(o['base']['total']), m8=round(o['m8_open']['total']),
      m8V=round(o['m8_open']['V']), addH=round(o['base']['add_height_um_M2M7']), addW=round(o['base']['add_width_um_M2M7']),
      addH8=round(o['m8_open']['add_height_um_M2M7'])) for w, o in res['windows'].items()}))
