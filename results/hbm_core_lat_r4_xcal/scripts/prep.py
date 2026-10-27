#!/usr/bin/env python3
"""HBM-CORE-LAT-R4 xcal_rel_t re-pack prep (TRIAL): new outline pin tables (stretched B2o, M4/M5 lattice),
views, master slice with in-core islands, explicit macro placement, slot clearance check vs plan of record."""
import json, hashlib, shutil, sys, os, copy
R3 = '/srv/opentallas-scratch2/claude/hbm-core-lat-r3-xcal'
D = sys.argv[1]
W0 = H0 = 207.36
W, H = 241.92, 224.64
os.makedirs(D, exist_ok=True)
plan = D + '/planR4'
if not os.path.isdir(plan):
    shutil.copytree(R3 + '/planS2snap', plan, symlinks=True)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
snap = lambda v: round(0.024 + round((v - 0.024) / 0.048) * 0.048, 3)
V = json.load(open(R3 + '/views_snap.json'))
xv = [v for v in V['view_list'] if v['module'] == 'ot_hbm_svc_sm_xcal_rel_t']
out = []
for v in xv:
    pins = json.load(open(plan + '/' + v['pins_file']))
    inst = v['instances'][0].replace('.', '_')
    new = []
    for p in pins:
        x, y = p['x'], p['y']
        q = dict(p)
        if x < 0.1:   q['x'] = x; q['y'] = snap(y * H / H0)            # W
        elif x > W0 - 0.1: q['x'] = round(W - (W0 - x), 3); q['y'] = snap(y * H / H0)   # E
        elif y < 0.1: q['y'] = y; q['x'] = snap(x * W / W0)            # S
        else:         q['y'] = round(H - (H0 - y), 3); q['x'] = snap(x * W / W0)        # N
        new.append(q)
    assert len({(q['layer'], round(q['x'], 3), round(q['y'], 3)) for q in new}) == len(new), 'pin collision'
    fn = 'cores/ot_hbm_svc_sm_xcal_rel_t__%gx%g__%s.json' % (W, H, inst)
    json.dump(new, open(plan + '/' + fn, 'w'))
    s = sha(plan + '/' + fn)
    nv = dict(v, view='ot_hbm_svc_sm_xcal_rel_t@' + s[:12], outline_um=[W, H], pins_file=fn, pins_sha256=s)
    nv['note'] = 'TRIAL R4 re-pack outline %gx%g: B2o table stretched (N/S x*%.4f, E/W y*%.4f), snapped to the 0.048 M4/M5 lattice; plan owner re-derives' % (W, H, W / W0, H / H0)
    out.append(nv)
V2 = dict(V, plan='planR4/die_plan.json', view_list=out, views=len(out))
json.dump(V2, open(D + '/views_r4.json', 'w'), indent=1)
# macro placement (explicit, one per type)
mp = {'macro_placement': [
    dict(k='u_xcal.u_cal.g_m2.u_program_hi', macro='ot_sram_1r1w_1024x256_m2_r2c2', origin_um=[33.588, 10.8], orient='R0'),
    dict(k='u_xcal.u_cal.g_m2.u_program_lo', macro='ot_sram_1r1w_1024x256_m2_r2c2', origin_um=[33.588, 143.1], orient='MX'),
    dict(k='u_xcal.g_t2.u_tab_lo', macro='ot_sram_1r1w_128x256_m1_r2c2', origin_um=[15.12, 91.8], orient='R0'),
    dict(k='u_xcal.g_t2.u_tab_hi', macro='ot_sram_1r1w_128x256_m1_r2c2', origin_um=[131.976, 91.8], orient='MY')]}
json.dump(mp, open(D + '/macro_place_r4.json', 'w'), indent=1)
# slice with islands
sl = json.load(open(R3 + '/sliceA/ot_hbm_svc_sm_xcal_rel_t.json'))
sl['outline_um'] = [W, H]
cx, cy = 120.96, 112.32
def isl(name, r, use='clock_driver'):
    return dict(name=name, rect_um=r, centre_um=[round((r[0] + r[2]) / 2, 3), round((r[1] + r[3]) / 2, 3)], use=use)
e = isl('ck_entry', [116.64, 108.0, 125.28, 116.64]); e['via_stack'] = ['M9', 'M5']; e['clock_pin'] = dict(layer='M5', xy_um=[120.984, 112.32])
sl['islands'] = [e,
    isl('ck_l1_s', [116.64, 84.24, 125.28, 88.56]), isl('ck_l1_n', [116.64, 136.08, 125.28, 140.4]),
    isl('ck_l2_sw', [12.96, 84.24, 21.6, 88.56]), isl('ck_l2_se', [220.32, 84.24, 228.96, 88.56]),
    isl('ck_l2_nw', [12.96, 136.08, 21.6, 140.4]), isl('ck_l2_ne', [220.32, 136.08, 228.96, 140.4])]
sl['note'] = 'TRIAL R4 re-pack: centre std pocket (tab row) + full-width bands y83.45-89.64 / 135.02-140.94 + W/E strips; 7 in-core islands, identical for all 4 pin variants'
os.makedirs(D + '/sliceR4', exist_ok=True)
json.dump(sl, open(D + '/sliceR4/ot_hbm_svc_sm_xcal_rel_t.json', 'w'), indent=1)
# slot check: grow each instance into free space (origin shift), clearance to every other object in the partition
dp = json.load(open(plan + '/die_plan.json'))
grow = {'u_xc_Q0': (-(W - W0), 0), 'u_xc_Q1': (-(W - W0), 0), 'u_xc_Q2': (-(W - W0), -(H - H0)), 'u_xc_Q3': (-(W - W0), -(H - H0))}
rep = []
for t in ('q_spb2', 'q_spt0'):
    tt = dp['partition_types'][t]; PW, PH = tt['outline_um']
    objs = []
    for c in tt['contents']:
        if c.get('origin_um') and c.get('outline_um'):
            objs.append((c['inst'], [c['origin_um'][0], c['origin_um'][1], c['origin_um'][0] + c['outline_um'][0], c['origin_um'][1] + c['outline_um'][1]]))
    pts = []
    for f in tt.get('ft_slots', []): pts += [(f['name'], r) for r in f['regs_um']]
    for s in tt.get('internal_stations', []): pts += [(s['conn'], r) for r in s.get('regs_um', [])]
    for hc in tt['hard_cores']:
        if hc['module'] != 'ot_hbm_svc_sm_xcal_rel_t': continue
        dx, dy = grow[hc['inst']]
        o = [hc['origin_um'][0] + dx, hc['origin_um'][1] + dy]
        r = [o[0], o[1], o[0] + W, o[1] + H]
        def gap(a, b):
            gx = max(b[0] - a[2], a[0] - b[2], 0); gy = max(b[1] - a[3], a[1] - b[3], 0)
            return round(max(gx, gy) if (gx == 0 or gy == 0) else (gx * gx + gy * gy) ** .5, 2)
        cl = sorted((gap(r, b), n) for n, b in objs if n != hc['inst'])
        cp = sorted((gap(r, [p[0], p[1], p[0], p[1]]), n) for n, p in pts)
        inside = [n for n, p in pts if r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]]
        rep.append(dict(partition=t, inst=hc['inst'], old_origin=hc['origin_um'], new_origin=[round(v, 3) for v in o], new_rect=[round(v, 3) for v in r],
                        in_partition=r[0] >= 0 and r[1] >= 0 and r[2] <= PW and r[3] <= PH, edge_margin=round(min(r[0], r[1], PW - r[2], PH - r[3]), 2),
                        nearest_core=cl[:2], nearest_station_reg=cp[:3], station_regs_inside=inside, die_ft_band_overlap=[b for b in tt.get("die_ft_bands", []) if (b["dir"] == "NS" and r[0] < b["span_um"][1] and r[2] > b["span_um"][0]) or (b["dir"] == "EW" and r[1] < b["span_um"][1] and r[3] > b["span_um"][0])]))
json.dump(rep, open(D + '/slot_check_r4.json', 'w'), indent=1)
for x in rep: print(json.dumps(x))
for v in out: print(v['view'], v['instances'])
