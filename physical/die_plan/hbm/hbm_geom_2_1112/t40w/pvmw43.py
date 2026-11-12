# HBM-GEOM-2 11-12: pvm_W FALLBACK delta (DIE-HBM-100: prepared, NOT in the t40w event).
# q_sm0..3 pv rows (8 groups [pv, pv, accel_smh] per row): pv_merge 198.72 -> 233.28 (pins ee36b9cd6c14), the pv-pv
# channel widened to 51.84 (X = 43.2) so sum/pv_y get their own channel, accel_smh 8.64 right of pv2, groups re-pitched
# from 734.4 to 717.12 (83 x 8.64) starting at the row's first x, so the row fits (E slack stays >= 8.64).
import json, sys
src, out = sys.argv[1:3]
P = json.load(open(src)); T = P['partition_types']
PIN = 'cores/ot_hbm_sm_pv_merge__233.28x198.72__pvmW.json'
W2, CH, GAP, PITCH = 233.28, 51.84, 8.64, 717.12
rep = {}
for tn in ('q_sm0', 'q_sm1', 'q_sm2', 'q_sm3'):
    t = T[tn]; Wd = t['outline_um'][0]; hc = t['hard_cores']
    rows = sorted({h['origin_um'][1] for h in hc if h['module'] == 'ot_hbm_sm_pv_merge'})
    for y in rows:
        band = sorted([o for o in hc if o['origin_um'][1] < y + 198.72 and o['origin_um'][1] + o['outline_um'][1] > y], key=lambda o: o['origin_um'][0])
        mods = [o['module'] for o in band]
        assert len(band) % 3 == 0 and all(mods[i] == 'ot_hbm_sm_pv_merge' and mods[i + 1] == 'ot_hbm_sm_pv_merge'
                                          for i in range(0, len(band), 3)), (tn, y, mods)
        x0 = band[0]['origin_um'][0]
        for g in range(len(band) // 3):
            a, b, c = band[3 * g: 3 * g + 3]
            gx = round(x0 + g * PITCH, 4)
            a['origin_um'] = [gx, y]; b['origin_um'] = [round(gx + W2 + CH, 4), y]
            c['origin_um'] = [round(gx + 2 * W2 + CH + GAP, 4), c['origin_um'][1]]
            for o in (a, b):
                o['outline_um'] = [W2, 198.72]; o['pins_file'] = PIN
        end = band[-1]['origin_um'][0] + band[-1]['outline_um'][0]
        assert end <= Wd - GAP, (tn, y, end)
        rep[f'{tn}@{y}'] = dict(groups=len(band) // 3, e_slack=round(Wd - end, 2), inter_group_gap=round(PITCH - (2 * W2 + CH + GAP + band[2]['outline_um'][0]), 2))
json.dump(P, open(out, 'w'), indent=1)
print(json.dumps(rep))
