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
import json, pathlib, sys, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import qc_cluster_cfg as CF   # SQC-CB8: OT_QC_CLUSTER
ROOT = pathlib.Path(__file__).resolve().parents[2]
name, K, step, buf, purpose = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
p = ROOT / 'physical/ref_tile' / name / 'spec.json'
s = json.loads(p.read_text())
s['sources'] = [x.replace('/a0_standin/', '/a0_rc14face/') for x in s['sources']]
assert all('a0_rc14face' in c['view'] for c in s['children'] if c['inst'].startswith('u_t_'))
kids = {c['inst']: c for c in s['children']}
W, H = s['outline']['w'], s['outline']['h']
# column buses over their entry / exit station; rs over its pin-register station (u_rs_1); rs_i / rs_o over the first / last
# feedthrough station (u_ft_16 for the 4 x 4)
_ft = max(int(i.rsplit('_', 1)[1]) for i in kids if re.fullmatch(r'u_fab\.u_ft_\d+', i))
STN = {**{f'bc{c}': f'u_fab.u_dn{c}_entry' for c in range(CF.NC)}, **{f'bco{c}': f'u_fab.u_dn{c}_exit' for c in range(CF.NC)},
       'rs': 'u_fab.u_rs_1', 'rs_o': f'u_fab.u_ft_{_ft}', 'rs_i': 'u_fab.u_ft_0'}
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
    moved = False
    for b, (blo, bhi) in bus.items():
        if face[b] == face[q] and lo < bhi + 2 and hi > blo - 2:
            shift = bhi + 4.32 - lo
            s['pin_ranges'][q] = [round(lo + shift, 3), round(hi + shift, 3)]
            lo, hi = s['pin_ranges'][q]; moved = True
    # SQC-CB8: a shifted scalar port must not land on another port of its face (CB8 rgm: ck_c1r0 / rst_c1r0 both shifted
    # past rs_o to the same x); step it along the face, past every bus / port of that face, until it is clear
    while moved:
        hit = [r for x, r in s['pin_ranges'].items() if x != q and face.get(x) == face[q]
               and lo < r[1] + 0.7 and hi > r[0] - 0.7]
        if not hit: break
        shift = max(r[1] for r in hit) + 1.0 - lo
        s['pin_ranges'][q] = [round(lo + shift, 3), round(hi + shift, 3)]; lo, hi = s['pin_ranges'][q]
# interior clock ports into the row-gap channel next to their region
a0 = {c['inst']: c for c in s['children'] if c['inst'].startswith('u_t_')}
A0H = 907.2
for q in [x for x in s['pin_ranges'] if x.startswith('ck_c') and face.get(x) in ('W', 'E')]:
    c, r = int(q[4]), int(q[6])
    y0 = a0[f'u_t_{c}_{r}']['at'][1]
    gap = y0 - 86.4 if 0 < r < CF.NR - 1 else None        # 86.4 below the region's A0 (= centre of a 172.8 um gap row)
    if gap is None: continue
    s['pin_ranges'][q] = [round(gap, 3), round(gap + 0.3, 3)]
if not CF.IS16:
    s['orfs_vars']['OT_CKR_PORTS'] = f'^ck_c[0-{CF.NC - 1}]r[0-{CF.NR - 1}]$'
s['pre_cts_extra'] = ['tools/qwen_cluster/cb16_km/cb16_ckring3.tcl']
s['orfs_vars'].update({'OT_CKR_STEP_UM': step, 'OT_CKR_SEG_UM': '120', 'OT_CKR_DMAX_UM': '150', 'OT_CKR_BUF': buf,
                       'OT_CKR_ENTRIES': K, 'OT_CKR_POST_ROUNDS': '2', 'OT_CKR_FFMIX': '0.5'})
s['job'].update({'owner': CF.T['owner'], 'branch': CF.T['branch'], 'tag': name.rsplit('_', 1)[-1], 'submit': False,
                 'purpose': purpose})
s['structural_change'] = ((
    f"SQC-CB8 10-22 {name} (PENDING-COORD, die contract not ruled): CB8 = {CF.NT} live A0 (a0_rc14face 820.8 x 907.2) as "
    f"{CF.NC} cols x {CF.NR} rows (MY | R0 pair sharing corridor A) -> outline {W} x {H} in the die slot 2445.12 x 5227.2; "
    f"T trunk (rs_i -> rs_o far-band feedthrough + station spine) = a horizontal band ({CF.CLUSTER}); {CF.NT} regional clock "
    f"roots ck_c<c>r<r> / resets rst_c<c>r<r>; ring tiles + free stations by ring_tile_place_b.py; buses over their pin-register "
    f"stations at 4 pins/um; clock = cb16_ckring3 regional rings (K {K}, {buf} every {step} um, as rgk); every region crossing "
    f"a hard landing-ring tile.  Prior: " + s['structural_change'][:400]) if not CF.IS16 else
    f"SQC-CB16 10-22 {name}: CB16 parent re-floorplanned on the LIVE A0 faces (a0_rc14face 820.8 x 907.2, rc14 FINAL rc2 pin "
    f"plan; every earlier rgx* used the obsolete 457.92 x 1166.4 c1 stand-in) -> outline {W} x {H} (regions ~1.1 x 1.1 mm, one "
    f"regional clock root per region); ring tiles + free stations by ring_tile_place_b.py; N/S buses over their pin-register "
    f"stations at 4 pins/um; interior clock ports in the row-gap channels; clock = cb16_ckring3 stage-matched regional rings "
    f"(K {K}, {buf} every {step} um; the rgxh form whose 16 roots measured TT 27-68 / FF 14-31 ps); crossings stay the 69 hard "
    f"landing-ring tiles. RTL / ports / children / SDC / calendar unchanged, 0 cycles. Prior: " + s['structural_change'][:400])
p.write_text(json.dumps(s, indent=1) + '\n')
print('SQC_RG_FINISH', name, {q: s['pin_ranges'][q] for q in STN})
