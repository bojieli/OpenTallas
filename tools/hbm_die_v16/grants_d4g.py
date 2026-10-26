#!/usr/bin/env python3
"""H-D4G 10-17 (owner 0do): d4g slot grants, contract rules and clock-region map from the d4g plan.

Inputs: the d4f r8b grants (the netlist the first d4g GEN binds: the RTL lanes HBM-B-RTL1..3 have not landed), the
d4f plan (results/arch/hbm_die_v15/d4f_a2p_fullcore/compact.P.json) and the d4g plan (plan_d4g.py, idx 'phy').

Slot rule: every die-level slot keeps its position RELATIVE TO ITS PLAN BLOCK.  The host block of a slot is the
smallest d4f plan block that contains the slot centre (same quadrant first), else the nearest block; the slot moves
with that block into the d4g plan (fractional position kept, clamped inside the block).  The three d4f units the RTL
lanes replace (hc_eng -> 4 quadrant HC engines, hb_idx__scorer0/1 -> 4 scorer quarters) have no d4g block: in this
DIAGNOSTIC they get the free PHY corners (scorer of stack S/N beside its PHY, hc_eng in the SE corner), reshaped
SYNTH outlines of at least their synthesis area.  Overlaps are legalised largest-first (nearest free spot, 10.8 um
grid, 21.6 um halo); the moves are reported.  Granted face pins are dropped (pins face their peers in the d4g
geometry; top-down pin assignment re-grants after the first GEN).

Contract rules (grants['d4g']): quadrant rules R1-R3, lever 1 (channel alignment), lever 2 (fixed-pitch lanes +
fixed station rows + LANDING at every lane-fed block input), regional clocks per quadrant + neighbour-skew gate,
reset reachability gate, and the OPEN BINDINGS (units the RTL lanes change).

    grants_d4g.py --plan-dir results/arch/hbm_die_d4g/plan/d4g_phy --out-dir results/arch/hbm_die_d4g
"""
import argparse, collections, copy, json, math, re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
A_PLAN = ROOT / 'results/arch/hbm_die_v15/d4f_a2p_fullcore/compact.P.json'
GRANTS = ROOT / 'results/arch/hbm_die_v16_d4f/grants_d4f_r8b.json'
CELL = 10.8
# SYNTH area need (std / 0.60 + 1.3 x macros, run8 meta): the d4f slot (3,369.6^2) was larger than the engine needs
AREA = {'hc_eng': 10.2e6}
HALO = 21.6
QS = ('SW', 'SE', 'NW', 'NE')

# units the RTL lanes change (owner 0do): bound as their d4f RTL in the diagnostic GEN, OPEN until the lane lands
OPEN = [
    ('VM', r'^(hb_vms_|vmdel_|vmks_|vmm_|lg_|vm_status)', 'HBM-B-RTL1', 'SE/NE hub client side + 16 more delivery lanes; '
     'each hub broadcasts to its own 8 banks; VM ring stays an XQ lane; vmks fills only its quadrant'),
    ('SU', r'^(su_prog|su_pgr|pgp_|sucore_|sucx_|subr_|cij_|rfr_|leaf_|col_su)', 'HBM-B-RTL1',
     'pgp_Q drives only its 4 slices; rfr_* RF relay chains removed; 64-b scalar reduce/broadcast tree'),
    ('host', r'^(host_|smw_|pleaf_|qdq_|hb_qdq)', 'HBM-B-RTL1', '4 PHY-side config/status leaves; host_cp_ingress feeds 4 leaves'),
    ('HC', r'^(hc_eng|hcx_|hce_|hc_(SW|SE|NW|NE)$)', 'HBM-B-RTL2', 'hc_eng split into 4 quadrant engines + 1,024-b partial-sum tree'),
    ('IDX', r'^(hb_idx__|idx_|col_idx|hb_argmax|idxq_|idxs_)', 'HBM-B-RTL2',
     'scorer quarters (8 leaves each) beside the PHY + local idx_ctl/idx_query per quadrant; merge takes 4 lists'),
    ('COLL', r'^(hb_coll_|coll_|tkm|epcal_|calendar_)', 'HBM-B-RTL3',
     'engine writes only its quadrant banks; x replication = on-die all-gather on the COLL ring; compiler quadrant-local DMA'),
]

RULES = dict(
    R1='a quadrant service (VM hub/banks, SU slices + core + programme slice, SFU groups + core/store, HC client + engine, '
       'IDX scorer quarter + local ctl/query, COLL engine) serves ONLY its own 4 SMs; an SM-side sink is never served from '
       'another quadrant',
    R2='die-wide drivers (host, ckgen/status, su programme root, col_*, argmax, idx merge) reach a quadrant through ONE fat tree '
       'lane root -> quadrant leaf (pleaf_Q PHY side / leaf_Q core side), then local fan-out',
    R3='only collectives (COLL ring, VM ring), the IDX top-k merge, argmax, HC partial sums and host cross quadrants, as XQ '
       'lanes through the centre lane channel / centre strip; any other cross-quadrant bus FAILS the contract check',
    L1='lever 1: SM k of a stack sits behind PC k; quadrant W = PCs 0-3, E = PCs 4-7; the PC3|PC4 line is the die centre '
       'line and carries the CENTRE LANE CHANNEL (400 um) for the vertical HBM->core lanes; IDX scorer quarters beside the '
       'PHY next to the PC row (they read the same SM packet as the SMs)',
    L2='lever 2: buses sharing (driver block, sink blocks, domain) are bundled into wide fixed-pitch forwarded-clock lanes '
       '(624-b point-to-point, 136-b forks; 48-b only for a lone narrow bus), one lane row of T tiles per station at a FIXED '
       'site every 380 um (plan; every hop <= 405 um), placed as a unit (die_case_v16 rule 3a, slide <= 150 um)',
    LAND='every block input fed by a lane with >= 1 station has a LANDING (lanes/LANDING-CONTRACT.md: dsfd_dvland ring D=4, '
         'fixed K strap, write epoch = first forwarded edge, read epoch = block regional reset); the compiler charges '
         'N + 1 + E + 1 per lane; die STA checks the L5 window at TT and FF with one E per link',
    CLK='regional clocks: one region set per quadrant (SM regions, PC half, core band <= 4 mm boxes, IDX corner) + strip '
        'regions; communicating pairs <= 405 um merge; neighbour-skew gate (TT AND FF skew <= 80 ps on pairs <= 405 um; landed pairs judged by the landing window, LANDING-CONTRACT L5) in run.sh',
    RST='regional synchronous reset forest per quadrant (reset_forest_layer --zones quadrant); die_case reset reachability '
        'gate FAILS on any unreachable reset sink/driver (OT_RESET_GATE=diag continues, recorded FAIL_DIAG)',
)


def inside(r, x, y):
    return r['x'] <= x <= r['x'] + r['w'] and r['y'] <= y <= r['y'] + r['h']


def quad(n):
    m = re.search(r'_(SW|SE|NW|NE)(\d*|_.*)$', n)
    return m.group(1) if m else None


def region_map(P, slots, W, pd, od, prev=None):
    """d4g clock region map from the plan + the die slots (also --regions-only: SMFRAME 10-18 re-runs it on the
    transformed grants, tools/hbm_die_v16/d4g_sm_frame.py)"""
    # ---- clock region map (regional, per quadrant)
    regions, inst = {}, {}
    prev = prev or {}

    def reg_of(b, r):
        q = quad(b)
        cx, cy = r['x'] + r['w'] / 2, r['y'] + r['h'] / 2
        if b.startswith('sm_'):
            return b
        if b.startswith('phy_'):
            return f'phy_{b[4:]}'
        if b.startswith('pc_'):
            st, k = b[3:5], int(b[5:])
            return f'pc_{ {"SW": ("SW", "SE"), "NW": ("NW", "NE")}[st][k >= 4] }'
        if b.startswith('idxs_'):
            return f'idx_{q}'
        if b.startswith('xq_'):
            st, p = b[3:5], int(b[7])
            return f'xq_{ {"SW": ("SW", "SE"), "NW": ("NW", "NE")}[st][p >= 2] }'
        if b.startswith(('lk_', 'ep_', 'tkm', 'idx_', 'host_')) or q is None:
            return 'strip_' + ('W' if cx < W / 3 else ('E' if cx > 2 * W / 3 else 'C'))
        # core band of quadrant q: <= 4 mm boxes along x (3 boxes of ~3 mm)
        k = int(min(2, (cx if q in ('SW', 'NW') else W - cx) // (W / 2 / 3)))
        return f'band_{q}{k}'
    members = collections.defaultdict(list)
    for b, r in P.items():
        members[reg_of(b, r)].append(b)
    for rg, bs in members.items():
        xs = [P[b]['x'] + P[b]['w'] / 2 for b in bs]; ys = [P[b]['y'] + P[b]['h'] / 2 for b in bs]
        regions[rg] = dict(site=[round(sum(xs) / len(xs), 1), round(sum(ys) / len(ys), 1)], members=sorted(bs))
        for b in bs:
            inst[b] = dict(region=rg, site=regions[rg]['site'])
    for s in slots:                          # slot name -> region of the d4g block under its centre
        if s['name'] in inst:
            continue
        cx, cy = s['origin']['x'] + s['outline']['w'] / 2, s['origin']['y'] + s['outline']['h'] / 2
        hs = [b for b, r in P.items() if inside(r, cx, cy)]
        if not hs and s['name'] in prev and prev[s['name']]['region'] in regions:
            # SMFRAME 10-18: a slot in a gap (the H-D4G2 sfup_SE/NE re-plan) keeps its previous map region
            rg = prev[s['name']]['region']; inst[s['name']] = dict(region=rg, site=regions[rg]['site']); continue
        if hs:
            b = min(hs, key=lambda b: P[b]['w'] * P[b]['h']); inst[s['name']] = dict(region=inst[b]['region'], site=inst[b]['site'])
    for n in ('idx_s0', 'idx_s1', 'hc_eng'):
        q = {'idx_s0': 'SW', 'idx_s1': 'NW', 'hc_eng': 'SE'}[n]
        inst[n] = dict(region=f'idx_{q}', site=regions[f'idx_{q}']['site'])
    near = 600.0
    nb = set()
    rl = sorted(regions)
    for i, x in enumerate(rl):
        for y in rl[i + 1:]:
            for bx in regions[x]['members']:
                A = P[bx]
                if any(max(A['x'] - P[by_]['x'] - P[by_]['w'], P[by_]['x'] - A['x'] - A['w'], A['y'] - P[by_]['y'] - P[by_]['h'],
                           P[by_]['y'] - A['y'] - A['h']) <= near for by_ in regions[y]['members']):
                    nb.add((x, y)); break
    rm = dict(schema='opentallas.die_clock.region_map.v1', plan=str((pd / 'compact.P.json').relative_to(ROOT)),
              rule='d4g (H-D4G): per-quadrant regions -- each SM its own region, the quadrant PC half, the quadrant core band in '
                   '3 boxes (<= 4 mm), the IDX corner, the XQL stores of the quadrant; strip W/C/E; PHY its own region; '
                   f'neighbours = outlines within {near} um', instances=inst, regions=regions, neighbours=sorted(map(list, nb)))
    (od / 'd4g_region_map.json').write_text(json.dumps(rm, indent=1) + '\n')
    return regions, nb


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan-dir', required=True); ap.add_argument('--out-dir', required=True)
    ap.add_argument('--grants', default=str(GRANTS))
    ap.add_argument('--regions-only', action='store_true', help='rebuild only d4g_region_map.json from OUT_DIR/grants_d4g.json')
    a = ap.parse_args()
    pd, od = ROOT / a.plan_dir, ROOT / a.out_dir
    od.mkdir(parents=True, exist_ok=True)
    PA = json.loads(A_PLAN.read_text()); P = json.loads((pd / 'compact.P.json').read_text())
    W, H = json.loads((pd / 'compact.metrics.json').read_text())['die_um']
    if a.regions_only:
        G2 = json.loads((od / 'grants_d4g.json').read_text())
        rmp = od / 'd4g_region_map.json'
        prev = json.loads(rmp.read_text())['instances'] if rmp.is_file() else {}
        regions, nb = region_map(P, [s for s in G2['slots'] if s.get('parent') == 'die'], W, pd, od, prev)
        print(json.dumps(dict(regions=len(regions), neighbour_pairs=len(nb))))
        return
    G = json.loads(Path(a.grants).read_text())
    G2 = copy.deepcopy(G)
    slots = [s for s in G2['slots'] if s.get('parent') == 'die']
    # ---- special homes (diagnostic) for the d4f units with no d4g block
    phyS, phyN = P['phy_SW'], P['phy_NW']
    smS, smN = P['sm_SW0'], P['sm_NW0']
    cyS0, cyS1 = 21.6, smS['y'] - 60.0
    pcrS = max(P[f'pc_SW{i}']['x'] + P[f'pc_SW{i}']['w'] for i in range(8))     # the PC row overhangs the PHY on E
    cyN0, cyN1 = smN['y'] + smN['h'] + 60.0, H - 21.6
    special = {
        'idx_s0': (42.4 + 40, cyS0, phyS['x'] - 60.0 - 82.4, cyS1 - cyS0, 'S stack PHY W corner (scorer quarters SW+SE region)'),
        'idx_s1': (42.4 + 40, cyN0, phyN['x'] - 60.0 - 82.4, cyN1 - cyN0, 'N stack PHY W corner (scorer quarters NW+NE region)'),
        'hc_eng': (pcrS + 60.0, cyS0, W - 42.4 - 40 - (pcrS + 60.0), cyS1 - cyS0,
                   'S stack PHY E corner (replaced by 4 quadrant engines hce_Q)'),
    }
    by_ = {s['name']: s for s in slots}
    rep = dict(moved={}, special={}, legalised={}, unhosted=[])
    targets = {}
    for s in slots:
        n = s['name']
        o, wh = s['origin'], s['outline']
        if n in special:
            x, y, w, h, why = special[n]
            area = AREA.get(n, wh['w'] * wh['h'])
            # reshape to the corner: full corner height, width = area / height (at least the old area)
            hh = round(h - 2 * 10.8, 3); ww = round(min(w, max(area / hh, 1000.0)), 3)
            if ww * hh < 0.98 * area:
                ww = round(w, 3)
            s['outline'] = dict(w=ww, h=hh)
            targets[n] = (x + (w - ww) / 2, y + 10.8)
            rep['special'][n] = dict(outline=[ww, hh], area_mm2=round(ww * hh / 1e6, 3), old=[wh['w'], wh['h']], why=why)
            continue
        if n.startswith('phy_'):
            targets[n] = (P[n]['x'], P[n]['y']); continue
        alias = {'host_cp': 'host_cp', 'host_N': 'host_cp', 'hb_ckgen': 'idx_op'}
        if n in alias:                    # d4g strip homes (plan (b) host / ckgen in the centre strip)
            r = P[alias[n]]; targets[n] = (r['x'] + r['w'] / 2 - wh['w'] / 2, r['y'] + r['h'] / 2 - wh['h'] / 2)
            rep['moved'][n] = dict(host=alias[n], d4f=[o['x'], o['y']], target=[round(v, 1) for v in targets[n]]); continue
        if n in P and n in PA:
            hb = n
        else:
            cx, cy = o['x'] + wh['w'] / 2, o['y'] + wh['h'] / 2
            q = quad(n)
            cand = [b for b, r in PA.items() if inside(r, cx, cy) and b in P and (q is None or quad(b) in (q, None))]
            if not cand:
                cand = [b for b, r in PA.items() if inside(r, cx, cy) and b in P]
            if cand:
                hb = min(cand, key=lambda b: PA[b]['w'] * PA[b]['h'])
            else:
                pool = [b for b in PA if b in P and (q is None or quad(b) in (q, None))] or [b for b in PA if b in P]
                dd = lambda r: max(r['x'] - cx, 0, cx - r['x'] - r['w']) + max(r['y'] - cy, 0, cy - r['y'] - r['h'])
                hb = min(pool, key=lambda b: dd(PA[b]))
                rep['unhosted'].append([n, hb, round(dd(PA[hb]))])
        ra, rb = PA[hb], P[hb]
        cx, cy = o['x'] + wh['w'] / 2, o['y'] + wh['h'] / 2
        fx = min(max((cx - ra['x']) / ra['w'], 0.0), 1.0); fy = min(max((cy - ra['y']) / ra['h'], 0.0), 1.0)
        nx_ = rb['x'] + fx * rb['w'] - wh['w'] / 2; ny_ = rb['y'] + fy * rb['h'] - wh['h'] / 2
        targets[n] = (nx_, ny_)
        rep['moved'][n] = dict(host=hb, d4f=[o['x'], o['y']], target=[round(nx_, 1), round(ny_, 1)])
    for n in ('hc_eng_tgt', 'hc_tbl_tgt'):     # HC programme targets beside their engine (diagnostic corner)
        if n in targets and 'hc_eng' in targets:
            hx, hy = targets['hc_eng']; targets[n] = (hx, hy + by_['hc_eng']['outline']['h'] + 40.0)
    # ---- legalise largest first (PHY + PC row pre-marked: die_case 1a owns them)
    nx, ny = int(math.ceil(W / CELL)), int(math.ceil(H / CELL))
    occ = np.zeros((ny, nx), bool)

    def ij(x, y, w, h, halo=0.0):
        return (max(0, int((x - halo) // CELL)), max(0, int((y - halo) // CELL)),
                min(nx, int(math.ceil((x + w + halo) / CELL))), min(ny, int(math.ceil((y + h + halo) / CELL))))

    def free(x, y, w, h):
        if x < 21.6 or y < 21.6 or x + w > W - 21.6 or y + h > H - 21.6:
            return False
        i0, j0, i1, j1 = ij(x, y, w, h)
        return not occ[j0:j1, i0:i1].any()

    def mark(x, y, w, h):
        i0, j0, i1, j1 = ij(x, y, w, h, HALO / 2)
        occ[j0:j1, i0:i1] = True
    for k in ('phy_SW', 'phy_NW'):
        r = P[k]; mark(r['x'], r['y'], r['w'], r['h'])
    for st in ('SW', 'NW'):
        for i in range(8):
            r = P[f'pc_{st}{i}']; mark(r['x'], r['y'], r['w'], r['h'])
    by = {s['name']: s for s in slots}
    order = sorted((n for n in targets if not n.startswith('phy_') and not n.startswith('svc_')),
                   key=lambda n: -by[n]['outline']['w'] * by[n]['outline']['h'])
    for n in order:
        s = by[n]; w, h = s['outline']['w'], s['outline']['h']
        if s['origin'].get('orient', 'R0') in ('R90', 'R270'):
            w, h = h, w
        x0, y0 = targets[n]
        got = None
        if free(x0, y0, w, h):
            got = (x0, y0)
        else:
            for rad in range(1, 400):
                best = None
                for dx in range(-rad, rad + 1):
                    for dy in (-rad, rad) if abs(dx) != rad else range(-rad, rad + 1):
                        x, y = x0 + dx * CELL, y0 + dy * CELL
                        if free(x, y, w, h):
                            d = abs(dx) + abs(dy)
                            if best is None or d < best[0]:
                                best = (d, x, y)
                if best:
                    got = best[1:]; break
        if got is None:
            raise SystemExit(f'no free spot for slot {n} ({w}x{h})')
        if got != (x0, y0):
            rep['legalised'][n] = dict(target=[round(x0, 1), round(y0, 1)], at=[round(got[0], 1), round(got[1], 1)],
                                       moved_um=round(abs(got[0] - x0) + abs(got[1] - y0), 1))
        mark(got[0], got[1], w, h)
        s['origin']['x'] = round(round(got[0] / 0.216) * 0.216, 3); s['origin']['y'] = round(round(got[1] / 0.216) * 0.216, 3)
    for n, (x, y) in targets.items():
        if n.startswith(('phy_', 'svc_')):     # PHY at the plan; service bands follow their PC block (die_case 1a owns them)
            by[n]['origin']['x'] = round(x, 3); by[n]['origin']['y'] = round(y, 3)
    for s in slots:
        if s.get('pins'):
            s['pins_d4f_dropped'] = len(s['pins']); s['pins'] = []
            s.pop('pin_status', None)
    die = next(s for s in G2['slots'] if s['kind'] == 'die')
    die['outline'] = dict(w=W, h=H)
    die['notes'] = 'HBM die d4g (owner 0do 10-17): plan (b) per-quadrant services + lever 1 (channel-aligned quadrants) + lever 2 (fixed-pitch lanes)'
    G2['version'] = 'd4g.1'; G2['owner'] = 'H-D4G'; G2['updated'] = '2026-10-17'
    G2['floorplan'] = dict(file=str((pd / 'compact.P.json').relative_to(ROOT)), candidate='d4g_phy',
                           adopted='owner 0do 10-17 (plan (b) + levers); DIAGNOSTIC until HBM-B-RTL1..3 land', die_um=[W, H],
                           previous=G['floorplan']['file'])
    # ---- open bindings
    import gzip
    opens = []
    for unit, rx, lane, what in OPEN:
        opens.append(dict(unit=unit, regex=rx, lane=lane, change=what,
                          slots=sorted(s['name'] for s in slots if re.match(rx, s['name']))))
    G2['d4g'] = dict(rules=RULES, open_bindings=opens, report=dict(special=rep['special'], legalised=len(rep['legalised']),
                                                                   unhosted=rep['unhosted']))
    (od / 'grants_d4g.json').write_text(json.dumps(G2, indent=1) + '\n')
    (od / 'grants_d4g_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    regions, nb = region_map(P, slots, W, pd, od)
    print(json.dumps(dict(slots=len(slots), moved=len(rep['moved']), legalised=len(rep['legalised']),
                          legalised_max_um=max([v['moved_um'] for v in rep['legalised'].values()] or [0]),
                          unhosted=len(rep['unhosted']), special=rep['special'], regions=len(regions), neighbour_pairs=len(nb))))


if __name__ == '__main__':
    main()
