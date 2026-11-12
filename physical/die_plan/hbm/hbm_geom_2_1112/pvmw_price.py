# HBM-GEOM-2 11-12 pvm_W pricing (paper, NOT for compose): ot_hbm_sm_pv_merge 198.72 -> 233.28 wide in q_sm0..3.
# Per pv row (y band of the pv cores) every core is re-packed left->right: a widened pv pushes its row east, each gap
# shrinks to max(8.64, original gap - pending push) (slack absorbs the push).  Cores outside the pv rows stay.
import json, sys, copy
src, out = sys.argv[1:3]
R = json.load(open(src)); T = R['partition_types']; G = 34.56; MINC = 8.64
rep = {}
for tn in ('q_sm0', 'q_sm1', 'q_sm2', 'q_sm3'):
    t = T[tn]; W, H = t['outline_um']; hc = t['hard_cores']
    pv = [h for h in hc if h['module'] == 'ot_hbm_sm_pv_merge']
    rows = sorted({h['origin_um'][1] for h in pv})
    moved = 0; maxshift = 0; overflow = []
    for y in rows:
        band = sorted([o for o in hc if o['origin_um'][1] < y + 198.72 and o['origin_um'][1] + o['outline_um'][1] > y],
                      key=lambda o: o['origin_um'][0])
        prev_new_r, prev_old_r = None, None
        for o in band:
            x0 = o['origin_um'][0]; w = o['outline_um'][0]
            if prev_new_r is None:
                nx = x0
            else:
                gap = x0 - prev_old_r
                nx = max(x0, prev_new_r + min(gap, max(MINC, gap)) if gap <= MINC else max(x0, prev_new_r + MINC))
            nw = w + G if o['module'] == 'ot_hbm_sm_pv_merge' and o['origin_um'][1] == y else w
            prev_old_r = max(prev_old_r or 0, x0 + w)
            nx = round(round(nx / 0.864) * 0.864, 4) if nx != x0 else x0
            if nx + nw > W - MINC: overflow.append(o['inst'])
            if nx != x0: moved += 1; maxshift = max(maxshift, nx - x0)
            o['origin_um'] = [nx, o['origin_um'][1]]
            if nw != w:
                o['outline_um'] = [round(nw, 4), o['outline_um'][1]]
                o['pins_file'] = 'cores_pvmw/ot_hbm_sm_pv_merge__233.28x198.72__pvmW.json'
            prev_new_r = max(prev_new_r or 0, nx + nw)
    rep[tn] = dict(pv=len(pv), rows=rows, moved_cores=moved, max_shift_um=round(maxshift, 2), overflow=overflow,
                   added_core_area_um2=round(len(pv) * G * 198.72, 1), instances=[p['name'] for p in R['partitions'] if p['type'] == tn])
json.dump(R, open(out, 'w'), indent=1)
print(json.dumps(rep, indent=1))
