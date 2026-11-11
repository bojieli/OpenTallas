"""SU-L4-1 (DIE-QC-97 11-11): sle_su_l1 lane4 +25.92 um (y 34.56 -> 60.48, the slw_su_l1 position) so the rsn_i landing
band gets a 38.9-um strip at the S face instead of a 7.6/13-um one.  Moves what the lane now covers: rsn ft station 2
bank (+30.24 into the lane4/lane5 gap), rsf ft station 2 bank (+12.96), the collector tap relay at y 312.672 (+29.04),
lane4 core_resets (+25.92); rsn_i band -> one S-strip rect (rects_um / gap rect dropped), its collector_local_sources
copy and the c6d66f5b rsn reset group rect follow.  usage: move_lane4.py SRC HEAD OUT"""
import json, sys, copy
SRC, HEAD, OUT = sys.argv[1:4]
sys.path.insert(0, SRC + '/tools/die_plan')
import schema, gen_phys
raw = json.load(open(HEAD))
DY = 25.92
RECT = {'sle_su_l1__cl5ea486db': [184.68, 20.52, 350.0, 56.16], 'sle_su_l1__clc6d66f5b': [17.28, 17.28, 330.0, 56.16]}
def far(p, r): return max(abs(p[0]-x)+abs(p[1]-y) for x in (r[0], r[2]) for y in (r[1], r[3]))
P = schema.Plan(copy.deepcopy(raw), path=HEAD)
for tn, R in RECT.items():
    t = raw['partition_types'][tn]
    h = next(h for h in t['hard_cores'] if h['inst'] == 'u_lane4'); assert h['origin_um'] == [17.28, 34.56]; h['origin_um'] = [17.28, 34.56 + DY]
    fts = {s['name']: s for s in t['ft_slots']}
    for nm, k, dy in (('rsn', 2, 30.24), ('rsf', 2, 12.96)):
        s = fts[nm]; s['regs_um'][k] = [s['regs_um'][k][0], round(s['regs_um'][k][1] + dy, 4)]
        s['bit_sites_um'][k - 1] = [[x, round(y + dy, 4)] for x, y in s['bit_sites_um'][k - 1]]
    lc = t['clock']['landing_contract']
    b = lc['bands']['rsn_i']
    pins = [p for p in gen_phys.type_pins(P, tn) if p[0] == 'rsn_i']
    hop = round(max(far((p[3], p[4]), R) for p in pins), 3)
    b['rect_um'] = R; b.pop('rects_um', None)
    b['max_pin_to_band_hop_um'] = hop
    b['placement'] = 'SU-L4-1 legal macro-free S-face strip under the moved u_lane4 (single rect)'
    for s in lc['collector_local_sources']:
        if s['name'] == 'rsn_i':
            s['band'] = copy.deepcopy(b)
    ct = lc['collector_tree']
    for c in ct.get('core_resets', []):
        if c['inst'] == 'u_lane4':
            c['pin_um'] = [c['pin_um'][0], round(c['pin_um'][1] + DY, 4)]; c['xy'] = [c['xy'][0], round(c['xy'][1] + DY, 4)]
    for r in ct['relays']:
        if abs(r['xy'][1] - 312.672) < 1e-3 and abs(r['xy'][0] - 102.24) < 1e-3:
            r['xy'] = [102.24, 341.712]
    g = lc.get('group_rects_um') or {}
    if 'u_cland_rst_rsn_i' in g:
        g['u_cland_rst_rsn_i'] = [10.84, 36.0, 15.16, 40.32]
    print(tn, 'rsn_i rect', R, 'area', round((R[2]-R[0])*(R[3]-R[1]), 1), 'reserve', b.get('area_reserve_um2'), 'far hop', hop)
json.dump(raw, open(OUT, 'w'))
