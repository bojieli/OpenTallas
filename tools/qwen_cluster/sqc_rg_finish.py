#!/usr/bin/env python3
"""SQC-CB16 10-22: finish a real-A0-face CB16 ring parent kit (output of qc_ring_parent_kit.py) with the rgxh lineage
deltas, re-derived on the new geometry:
  * A0 children / blackbox = a0_rc14face (live A0 820.8 x 907.2, FINAL rc2 pin plan; still a stand-in body: diagnostic)
  * N/S data buses re-pinned directly over their pin-register station at 4 pins/um (rgxd rule; IO leg = face gap only)
  * interior-row clock ports (r1 / r2 on W / E) centred in the row-gap channel next to their region (rgxc rule)
  * clock = cb16_ckring3.tcl stage-matched regional rings (one root per region, A0-bbox ring), K / step / buffer per variant
RTL, ports, children, reset trees, SDC and calendar unchanged (0 cycles).
    sqc_rg_finish.py NAME K STEP_UM BUF TAG_PURPOSE
"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
name, K, step, buf, purpose = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
p = ROOT / 'physical/ref_tile' / name / 'spec.json'
s = json.loads(p.read_text())
s['sources'] = [x.replace('/a0_standin/', '/a0_rc14face/') for x in s['sources']]
assert all('a0_rc14face' in c['view'] for c in s['children'] if c['inst'].startswith('u_t_'))
kids = {c['inst']: c for c in s['children']}
W, H = s['outline']['w'], s['outline']['h']
STN = {'bc0': 'u_fab.u_dn0_entry', 'bc1': 'u_fab.u_dn1_entry', 'bc2': 'u_fab.u_dn2_entry', 'bc3': 'u_fab.u_dn3_entry',
       'bco0': 'u_fab.u_dn0_exit', 'bco1': 'u_fab.u_dn1_exit', 'bco2': 'u_fab.u_dn2_exit', 'bco3': 'u_fab.u_dn3_exit',
       'rs': 'u_fab.u_rs_1', 'rs_o': 'u_fab.u_ft_16', 'rs_i': 'u_fab.u_ft_0'}
SW = 51.84
face = {q: f for f, l in s['pins'].items() for q in l}
want = {}
for port, inst in STN.items():
    lo, hi = s['pin_ranges'][port]; w = hi - lo            # keep the bus span (4 pins/um), centre it over the station
    cx = kids[inst]['at'][0] + SW / 2
    want[port] = [cx - w / 2, w, face[port]]
for f in ('N', 'S'):                                       # resolve overlaps on each face: sweep, keep >= 4.32 um gaps
    ps = sorted((q for q in want if want[q][2] == f), key=lambda q: want[q][0])
    x = 21.6
    for q in ps:
        want[q][0] = max(want[q][0], x); x = want[q][0] + want[q][1] + 4.32
    over = x - 4.32 - (W - 21.6)
    if over > 0:                                           # push back from the far corner
        for q in reversed(ps):
            want[q][0] -= over; over = 0
    for q in ps:
        s['pin_ranges'][q] = [round(want[q][0], 2), round(want[q][0] + want[q][1], 2)]
# scalar / reset ports keep their place unless they now overlap a bus range
bus = {q: s['pin_ranges'][q] for q in STN}
for q, (lo, hi) in list(s['pin_ranges'].items()):
    if q in STN or face.get(q) not in ('N', 'S'): continue
    for b, (blo, bhi) in bus.items():
        if face[b] == face[q] and lo < bhi + 2 and hi > blo - 2:
            shift = bhi + 4.32 - lo
            s['pin_ranges'][q] = [round(lo + shift, 3), round(hi + shift, 3)]
            lo, hi = s['pin_ranges'][q]
# interior clock ports into the row-gap channel next to their region
a0 = {c['inst']: c for c in s['children'] if c['inst'].startswith('u_t_')}
A0H = 907.2
for q in [x for x in s['pin_ranges'] if x.startswith('ck_c') and face.get(x) in ('W', 'E')]:
    c, r = int(q[4]), int(q[6])
    y0 = a0[f'u_t_{c}_{r}']['at'][1]
    gap = y0 - 86.4 if r in (1, 2) else None              # centre of the gap row below the region's A0 (172.8 um gap)
    if gap is None: continue
    s['pin_ranges'][q] = [round(gap, 3), round(gap + 0.3, 3)]
s['pre_cts_extra'] = ['tools/qwen_cluster/cb16_km/cb16_ckring3.tcl']
s['orfs_vars'].update({'OT_CKR_STEP_UM': step, 'OT_CKR_SEG_UM': '120', 'OT_CKR_DMAX_UM': '150', 'OT_CKR_BUF': buf,
                       'OT_CKR_ENTRIES': K, 'OT_CKR_POST_ROUNDS': '2', 'OT_CKR_FFMIX': '0.5'})
s['job'].update({'owner': 'Claude:SQC-CB16', 'branch': 'claude/sqc-cb16-1022', 'tag': name.rsplit('_', 1)[-1], 'submit': False,
                 'purpose': purpose})
s['structural_change'] = (
    f"SQC-CB16 10-22 {name}: CB16 parent re-floorplanned on the LIVE A0 faces (a0_rc14face 820.8 x 907.2, rc14 FINAL rc2 pin "
    f"plan; every earlier rgx* used the obsolete 457.92 x 1166.4 c1 stand-in) -> outline {W} x {H} (regions ~1.1 x 1.1 mm, one "
    f"regional clock root per region); ring tiles + free stations by ring_tile_place_b.py; N/S buses over their pin-register "
    f"stations at 4 pins/um; interior clock ports in the row-gap channels; clock = cb16_ckring3 stage-matched regional rings "
    f"(K {K}, {buf} every {step} um; the rgxh form whose 16 roots measured TT 27-68 / FF 14-31 ps); crossings stay the 69 hard "
    f"landing-ring tiles. RTL / ports / children / SDC / calendar unchanged, 0 cycles. Prior: " + s['structural_change'][:400])
p.write_text(json.dumps(s, indent=1) + '\n')
print('SQC_RG_FINISH', name, {q: s['pin_ranges'][q] for q in STN})
