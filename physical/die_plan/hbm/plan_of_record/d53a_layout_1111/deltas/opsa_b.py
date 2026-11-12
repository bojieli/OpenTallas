"""DIE-LAYOUT-HBM d51-opsa form (B): ot_hgi_sfu_opsa_group0 in q_b113 and q_b113__physical_v1.
(A) +74.52 up was refused: it closes the band above g0 to 3.24 um and the NE pv1 crossing L5076x3 (653 b, N face ->
W face) would need a detour around g0 with +2 stations (+2 cycles).
(B) g0 760.32x233.28 @ (1080, 1261.44) -> 895.32x270.00 @ (945.0, 1261.44): +135 left, +36.72 up (+36.3% area),
MX kept, bottom (toward g1) fixed; the band above g0 stays 41.04 um (1531.44-1572.48) and every station that sat in
1495-1531 moves up into it (y 1551.96); L5096x8 S5 (1071,1344, now inside) -> (1050.0, 1250.0) under g0, S6 into the
band.  Station counts unchanged (0 cycles), all hops <= 405 um (asserted).
pins file (provisional, HBM-CORES-B owns the real view): x + DX for every pin (physical x kept), core-frame N-face
pins (y >= 233.0, toward g1) y + 36.72.
LATTICE (HBM-CORES-C 11-12, DIE-HBM-101): DX is snapped OUTWARD to a multiple of the M4/M5 pin pitch 0.048 (135.0 -> 135.024), so the
origin x (1080 - DX = 944.976) and every core-frame M5 pin stay on the kit lattice (0.024 + 0.048 n); with DX = 135.0 (= 2812.5 pitches)
the origin and all 2051 M5 pins were half a pitch off and gen_core_kit_hbm.py refused the kit. Absolute pin positions are unchanged.
The widened outline is 760.32 + DX = 895.344 and the right edge stays at 1840.32.
usage: opsa_b.py PLAN_IN PLAN_OUT CORES_DIR"""
import json, sys, os, math
PITCH = 0.048
src, dst, cores = sys.argv[1:4]
D = json.load(open(src)); T = D['partition_types']
OLD = 'cores/ot_hgi_sfu_opsa_group0__760.32x233.28__d44v_split.json'
DX0 = 135.0
DX = round(math.ceil(DX0 / PITCH - 1e-9) * PITCH, 6)            # outward to the pin-pitch lattice
DY = 270.0 - 233.28
OX, OW = round(1080.0 - DX, 6), round(760.32 + DX, 6)
NEW = 'cores/ot_hgi_sfu_opsa_group0__%gx270__d51opsaB.json' % OW
G0 = (OX, 1261.44, OX + OW, 1261.44 + 270.0)
BAND_Y = 1551.96
pins = json.load(open(os.path.join(cores, os.path.basename(OLD))))
out = []
for p in pins:
    q = dict(p); q['x'] = round(p['x'] + DX, 4)
    if p['y'] >= 233.0: q['y'] = round(p['y'] + DY, 4)
    out.append(q)
newp = os.path.join(os.path.dirname(os.path.abspath(dst)), 'cores_d51', os.path.basename(NEW))
os.makedirs(os.path.dirname(newp), exist_ok=True); json.dump(out, open(newp, 'w'))
def inside(r): return G0[0] <= r[0] <= G0[2] and G0[1] <= r[1] <= G0[3]
def dist(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
def face_pt(t, face, win):
    W, H = t['outline_um']; m = (win[0] + win[1]) / 2
    return {'N': [m, H], 'S': [m, 0.0], 'E': [W, m], 'W': [0.0, m]}[face]
SPECIAL = {('q_b113__physical_v1', 'L5096x8'): {5: [1050.0, 1250.0], 6: [1000.08, BAND_Y], 7: [1380.24, BAND_Y],
                                               8: [1767.0, BAND_Y]},
           # the wide N-face exit (1615 b) passed x 972 at y 1343 (now inside g0): around the W end of g0 instead
           ('q_b113', 'L8350x3'): {3: [1000.08, 1240.2], 4: [900.18, 1490.4], 5: [560.16, 1500.12], 6: [300.24, 1564.2]},
           ('q_b113__physical_v1', 'L8350mx3'): {3: [1000.08, 1240.2], 4: [900.18, 1490.4], 5: [560.16, 1500.12],
                                                 6: [300.24, 1564.2]}}
for tn in ('q_b113', 'q_b113__physical_v1'):
    t = T[tn]
    for h in t['hard_cores']:
        if h['module'] == 'ot_hgi_sfu_opsa_group0':
            assert h['outline_um'] == [760.32, 233.28] and h['origin_um'] == [1080.0, 1261.44], h
            h['origin_um'] = [OX, 1261.44]; h['outline_um'] = [OW, 270.0]; h['pins_file'] = NEW
    # other cores must not overlap the new g0
    for h in t['hard_cores']:
        if h['module'] == 'ot_hgi_sfu_opsa_group0': continue
        r = (h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1])
        assert not (min(r[2], G0[2]) - max(r[0], G0[0]) > 1e-6 and min(r[3], G0[3]) - max(r[1], G0[1]) > 1e-6), (tn, h['inst'])
    for s in t['ft_slots']:
        regs = s.get('regs_um', []); changed = False
        sp = SPECIAL.get((tn, s['name']), {})
        for i, r in enumerate(regs):
            if i in sp: regs[i] = sp[i]; changed = True
            elif inside(r):
                if r[1] < 1440: print('  NEEDS SPECIAL', tn, s['name'], s['width'], i, r, [[round(a), round(b)] for a, b in regs]); continue
                regs[i] = [r[0], BAND_Y]; changed = True
        if changed:
            s.pop('bit_sites_um', None); s.pop('bit_site_cell_um', None)
            pts = []
            if s.get('in_window_um'): pts.append(face_pt(t, s['in_face'], s['in_window_um']))
            pts += regs
            if s.get('out_window_um'): pts.append(face_pt(t, s['out_face'], s['out_window_um']))
            hops = [dist(a, b) for a, b in zip(pts, pts[1:])]
            # the in-face -> S0 leg is the kit's face register (S0 sits at the pin); judge station legs only
            leg = hops[1:] if s.get('in_window_um') else hops
            print(tn, s['name'], s['width'], 'b, stations', s['stations'], 'legs', [round(h) for h in leg])
            assert max(leg) <= 405, (tn, s['name'])
            assert not any(inside(r) for r in regs)
            for r in regs:
                for h in t['hard_cores']:
                    o, e = h['origin_um'], h['outline_um']
                    assert not (o[0] <= r[0] <= o[0] + e[0] and o[1] <= r[1] <= o[1] + e[1]), (tn, s['name'], r, h['inst'])
    for s in t.get('internal_stations', []):
        for r in s.get('regs_um', []):
            assert not inside(r), (tn, s['conn'], r)
open(dst, 'w').write(json.dumps(D, indent=1) + '\n')
print('pins file ->', newp, len(out))
