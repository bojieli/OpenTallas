#!/usr/bin/env python3
"""Re-home the v15 grants (results/arch/hier_contract_1015/hbm_v15.json) from compact660_v5 onto a v6 plan
(H-DIE 0300 10-16: compact_v6b adopted, OWNER 02:15 die may grow).  rehome_compact.py (v5) stays untouched, so v5 is
reproducible from it; this tool only moves an existing v5-homed contract to the new plan.

    rehome_v6.py --plan results/arch/hbm_die_v15/compact_v6b [--old results/arch/hbm_die_v15/compact660_v5] [--dry-run]

Rules:
 1. every die-level slot that IS a plan block (same name, hb_<name>, svc_<q>_s<k> -> pc_<q><k>, sfucore/cij) takes the
    new block origin; slots whose plan block changed size (SM, SU slices, SU core, VM hub) take the new outline;
 2. every other absolute coordinate (die-level slots without a block, pc_homes, SU RF relay homes, request-slot groups,
    9th service bands, host/ckgen/status/calendars/quant transport) moves by TRANSLATION with its anchor: the v5 block
    containing it, else the nearest v5 block; the delta is that block's nearest-corner delta (keeps the item's offset
    from the block edge it sits against, also on resized blocks and in mirrored quadrants);
 3. resized slots re-derive their exact pins top-down with tools/hbm_die_v15/rtl_pin_grants_1405.py (grant_su /
    grant_sm / grant_core: same faces and order, new pin windows from the plan's pin file);
 4. audit: every die-level footprint inside the die (20 um edge), no overlap between die-level footprints or with plan
    blocks they do not represent, every relay/PC home point outside foreign hard footprints.
H-DIE-V790 10-16 (core4_sfu2_su2825; the tall 480-um hub covers the v5 translation targets).  Structural homes:
 5. a plan-block slot without exact pins (pin windows only or none: hc_eng, sfucore_<q>) takes the plan outline as well
    as its origin; plan blocks without a slot (sfus_<q> SU SFU store, hc_eng_tgt / hc_tbl_tgt programme collars) get a
    FACES_ONLY slot; a plan hc_eng that is the v16 ot_hbm_hc_eng_static (graph node provenance) takes that cell;
 6. a translated slot that sat on the 20-um die edge in the old plan keeps that edge exactly (v5 host_N overhung it by
    0.024 um through rounding; translation alone cannot repair that);
 7. calendar_<q> (hfd_hgi_vm_calendar; E face = 187-bit hub schedule, W = cfg, S = status) is homed AGAINST the band-side
    face of vmh_<q> across a 21.6-um channel, at the first y (from the quadrant's die-edge end of the hub) whose span
    clears every plan block, the hub's face pin windows and the RF footprints; orient mirrors per quadrant (SW R0,
    SE MY, NW MX, NE R180) so the E face always faces the hub;
 8. with <plan>/rf_centre_allocation.json (tools/hbm_die_v15/rf_centre_routes.py + rf_centre_allocate.py on the plan)
    the SU RF relay homes are the allocated standard-48 footprint centres (production 36 stages); every footprint is
    audited as a rectangle against hard footprints and against the other footprints.  Without that file (v6b) the v5
    homes are translated as before.
"""
import argparse, copy, json, math, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
LAYER = dict(N='M5', S='M5', E='M4', W='M4')
SWAP = {'R90', 'R270', 'MXR90', 'MYR90'}


def rect(b):
    return (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])


def block_of(n, P):
    if n in P:
        return n
    if n.startswith('hb_') and n[3:] in P:
        return n[3:]
    if n.startswith('svc_'):
        q, k = n[4:6], int(n.split('_s')[1])
        return f'pc_{q}{k}' if k < 8 else None
    return None


def anchor(x, y, P5, P6, skip=()):
    best = None
    for k, b in P5.items():
        if k not in P6 or k in skip:
            continue
        x0, y0, x1, y1 = rect(b)
        dx = max(x0 - x, 0, x - x1); dy = max(y0 - y, 0, y - y1)
        d = dx + dy
        if best is None or d < best[0]:
            best = (d, k)
    k = best[1]
    o, n = P5[k], P6[k]
    cx = 'r' if x > o['x'] + o['w'] / 2 else 'l'
    cy = 't' if y > o['y'] + o['h'] / 2 else 'b'
    ox = o['x'] + (o['w'] if cx == 'r' else 0); oy = o['y'] + (o['h'] if cy == 't' else 0)
    nx = n['x'] + (n['w'] if cx == 'r' else 0); ny = n['y'] + (n['h'] if cy == 't' else 0)
    return nx - ox, ny - oy, k


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True); ap.add_argument('--old', default='results/arch/hbm_die_v15/compact660_v5')
    ap.add_argument('--contract', default='results/arch/hier_contract_1015/hbm_v15.json')
    ap.add_argument('--adopted', default='H-DIE 0300 10-16, owner 02:15 growth (v6b: SU 77 mm2 at 60 % util, SM 7,050 x 1,780)')
    ap.add_argument('--sm-carve', type=float, help='SM frame edge feedthrough carve width (W column + N row, OWNER/H-SM rp4c 40.32)')
    ap.add_argument('--quadrants', default='SW,SE,NW,NE', help='OWNER 10-16 A2P half die: keep only these quadrants (e.g. SW,NW); '
                    'slots, PC homes and RF routes of the other quadrants are DROPPED (the half-die netlist has no such instances)')
    ap.add_argument('--drop-ghosts', action='store_true', help='drop the v15 IDX scorer/glue slots (idx_*; not in the v16 contract)')
    ap.add_argument('--sm-column', action='store_true', help='A2P: SM slots take the plan column outline with FACES_ONLY pins '
                    '(H-SM portrait column kit pending; exact pins re-granted from that kit)')
    ap.add_argument('--homes', help='JSON {slot: {x, y, orient}}: explicit homes for translated (non-plan) slots, applied before the audit')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', help='write an explicitly unqualified proposal here, preserving the active contract')
    a = ap.parse_args()
    pd, od = ROOT / a.plan, ROOT / a.old
    P6 = json.loads((pd / 'compact.P.json').read_text()); P5 = json.loads((od / 'compact.P.json').read_text())
    M6 = json.loads((pd / 'compact.metrics.json').read_text()); W, H = M6['die_um']
    M5 = json.loads((od / 'compact.metrics.json').read_text())
    pins6 = json.loads(next((pd / 'pins').glob('*.pins.json')).read_text())
    cp = ROOT / a.contract
    C = json.loads(cp.read_text())
    slots = C['slots']
    die = slots[0]; assert die['kind'] == 'die'
    die['outline'] = dict(w=round(W, 3), h=round(H, 3))
    import reticle; reticle.require_die(W, H, 'rehome_v6.py')   # OWNER 10-16: >= 0.5 mm in W AND H
    die['notes'] = 'v6b die (H-DIE 0300 10-16, OWNER 02:15: grow where area fixes a measured fit/congestion problem)'
    import re as _re
    KQ = a.quadrants.split(',')
    DQ = [q for q in ('SW', 'SE', 'NW', 'NE') if q not in KQ]
    dropped = []
    if DQ or a.drop_ghosts:
        rxq = _re.compile(r'(^|_)(' + '|'.join(DQ) + r')(\d|_|$)') if DQ else None
        def gone(n):
            return bool((rxq and rxq.search(n)) or (a.drop_ghosts and n.startswith('idx_')))
        keep = [slots[0]]
        for s_ in slots[1:]:
            if gone(s_['name']) or (s_.get('parent') not in (None, 'die') and gone(s_.get('parent', ''))):
                dropped.append(s_['name'])
            else:
                keep.append(s_)
        slots[:] = keep
        C['pc_homes']['homes'] = {k: v for k, v in C['pc_homes']['homes'].items() if not gone(k) and not gone(v.get('band', ''))}
        C['su_rf_relays_v7']['routes'] = [r for r in C['su_rf_relays_v7']['routes'] if r['src'] in KQ and r['dst'] in KQ]
        die['notes'] = f'A2P half die (OWNER 10-16: 16 SMs + 2 HBM stacks; quadrants {a.quadrants})'
    log = dict(mapped=[], resized=[], translated=[], new=[])
    S = {s['name']: s for s in slots}
    # 1. plan-block slots
    for s in slots[1:]:
        if s.get('parent') != 'die':
            continue
        blk = block_of(s['name'], P6)
        if not blk:
            continue
        b = P6[blk]
        o = s['origin']
        s['origin'] = dict(x=round(b['x'], 3), y=round(b['y'], 3), orient=o.get('orient', 'R0'))
        if s.get('placed_footprint'):
            s['placed_footprint'] = dict(s['placed_footprint'])
        if (s['name'].startswith(('sm_', 'su_', 'sucore_', 'vmh_')) or not s.get('pins')) and \
                (abs(s['outline']['w'] - b['w']) > 1e-3 or abs(s['outline']['h'] - b['h']) > 1e-3):
            log['resized'].append(dict(slot=s['name'], old=s['outline'], new=dict(w=b['w'], h=b['h'])))
            s['outline'] = dict(w=b['w'], h=b['h'])
            if s.get('placed_footprint'):
                s['placed_footprint'] = dict(w=b['w'], h=b['h'])
        s['plan_block'] = blk
        log['mapped'].append(s['name'])
    # new plan blocks without a slot (cij_<q>)
    for k, b in P6.items():
        if k.startswith('cij_') and k not in S:
            q = k[4:]
            ns = dict(name=k, cell='ot_hgi_coll_inj_idx_join', kind='tile', parent='die', outline=dict(w=b['w'], h=b['h']),
                      origin=dict(x=b['x'], y=b['y'], orient='R0'), clock_entry=dict(pin='clk', face='N', layer='M5', offset=round(b['w'] / 2, 3)),
                      pg_layer='M5', strap_layer='M6', signal_max_layer='M5', layer_cap='M5',
                      io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), version=1, grant='v6b_cij_0300',
                      rtl_owner='H-NETLIST/H-COLL: ot_hgi_coll_inj_idx_join', plan_block=k,
                      faces=dict(E=f'coll_{q} inject / RED_CARRY / delivery', W=f'sucore_{q} (sucx_{q}) inject inj_d 1,024 b, COLL->SU 194 b'),
                      notes='COLL inject/IDX join leaf in the 21.6 + 43.2 + 21.6 um channel between sucore and COLL: COLL<->SU 0 relay stages',
                      pins=[], pin_status='FACES_ONLY')
            slots.append(ns); S[k] = ns; log['new'].append(k)
    G6 = json.loads((pd / 'compact.graph.json').read_text())
    NEWCELL = {'sfus_': (None, 'H-SU: store partition of ot_hgi_sfu_scheduled_engine (sfucore_sizing_0600, side-upper bay)'),
               'hc_eng_tgt': ('ot_static_program_target', 'HC owner (H-NETLIST hceng) TARGET 164'),
               'hc_tbl_tgt': ('ot_static_program_target', 'HC owner (H-NETLIST hceng) TARGET 165'),
               'hc_': ('ot_hbm_hc_q_static', 'HC owner (H-NETLIST hc): quadrant HC client at the band inner end')}
    for k, b in P6.items():
        pre = next((x for x in NEWCELL if k.startswith(x)), None)
        if pre and k not in S:
            cell, owner = NEWCELL[pre]
            ns = dict(name=k, cell=cell, kind='tile', parent='die', outline=dict(w=b['w'], h=b['h']),
                      origin=dict(x=b['x'], y=b['y'], orient='R0'), clock_entry=dict(pin='clk', face='W', layer='M4'),
                      pg_layer='M5', strap_layer='M6', signal_max_layer='M5', layer_cap='M5',
                      io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), version=1, grant='v790_plan_block_1016',
                      rtl_owner=owner, plan_block=k, qualified=False,
                      notes=G6['nodes'].get(k, {}).get('provenance', 'plan block') + '; candidate outline, pins FACES_ONLY',
                      pins=[], pin_status='FACES_ONLY')
            slots.append(ns); S[k] = ns; log['new'].append(k)
    he = G6['nodes'].get('hc_eng', {})
    if 'ot_hbm_hc_eng_static' in he.get('provenance', '') and 'hc_eng' in S:
        S['hc_eng'].update(cell='ot_hbm_hc_eng_static', source='rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_eng_static.sv',
                           notes=he['provenance'] + '; H-DIE-V790 centre-column home, pins from the plan pin windows (v16 widths)')
    # 2. translations
    def tr(x, y, skip=()):
        dx, dy, k = anchor(x, y, P5, P6, skip)
        return round(x + dx, 3), round(y + dy, 3), k
    for s in slots[1:]:
        if s.get('parent') != 'die' or s.get('plan_block') or s['name'] in log['new']:
            continue
        o = s['origin']
        fp = s.get('placed_footprint') or s['outline']
        cx, cy = o['x'] + fp['w'] / 2, o['y'] + fp['h'] / 2
        dx, dy, k = anchor(cx, cy, P5, P6)
        nx, ny = round(o['x'] + dx, 3), round(o['y'] + dy, 3)
        W5, H5 = M5['die_um']
        edge = []                                            # rule 6
        if abs(o['y'] + fp['h'] - (H5 - 20)) < 1.0:
            ny = round(H - 20 - fp['h'], 3); edge.append('N')
        if abs(o['y'] - 20) < 1.0:
            ny = 20.0; edge.append('S')
        if abs(o['x'] + fp['w'] - (W5 - 20)) < 1.0:
            nx = round(W - 20 - fp['w'], 3); edge.append('E')
        if abs(o['x'] - 20) < 1.0:
            nx = 20.0; edge.append('W')
        s['origin'] = dict(x=nx, y=ny, orient=o.get('orient', 'R0'))
        log['translated'].append(dict(slot=s['name'], anchor=k, dx=round(nx - o['x'], 3), dy=round(ny - o['y'], 3),
                                      **(dict(edge_kept=edge) if edge else {})))
    # 8. RF relay footprints from the plan's RF route allocation
    rfa_path = pd / 'rf_centre_allocation.json'
    rf_fp = []
    if rfa_path.exists():
        rfa = json.loads(rfa_path.read_text())
        assert rfa['all_36_stage_routes_allocated'] and not rfa['failures'], 'RF allocation incomplete'
        rf_fp = [(c['name'], c['rect']) for c in rfa['cells']]
    # 7. calendar homes against the hub's band-side face
    MIRROR = dict(SW='R0', SE='MY', NW='MX', NE='R180')
    for q in KQ:
        s = S.get(f'calendar_{q}')
        if not s or f'vmh_{q}' not in P6:
            continue
        hb, cw, chh, ch = P6[f'vmh_{q}'], s['outline']['w'], s['outline']['h'], 21.6
        east = q.endswith('E')                               # SE/NE: band lies east of the hub
        hubface = 'E' if east else 'W'
        x = hb['x'] + hb['w'] + ch if east else hb['x'] - ch - cw
        wins = [(p['offset_um'], p['offset_um'] + p['span_um']) for p in pins6['blocks'][f'vmh_{q}']['faces'].get(hubface, {}).get('pins', [])]
        north = q.startswith('N')
        obst = [b for k, b in P6.items() if k != f'vmh_{q}'] + [r for _, r in rf_fp]
        found = None
        for step in range(int(hb['h'] / 2.16)):
            off = step * 2.16                                 # from the die-edge end of the hub
            y = hb['y'] + hb['h'] - off - chh if north else hb['y'] + off
            lo = y - hb['y']
            if lo < 0 or lo + chh > hb['h']:
                continue
            if any(a < lo + chh and lo < b for a, b in wins):
                continue
            if any(x - ch < b['x'] + b['w'] and b['x'] < x + cw + ch and y - ch < b['y'] + b['h'] and b['y'] < y + chh + ch for b in obst):
                continue
            found = (round(x, 3), round(y, 3)); break
        assert found, ('no calendar home beside', q)
        o = s['origin']
        oc = (o['x'] + cw / 2, o['y'] + chh / 2); nc = (found[0] + cw / 2, found[1] + chh / 2)
        s['origin'] = dict(x=found[0], y=found[1], orient=MIRROR[q])
        s['home_rule'] = (f'H-DIE-V790 10-16: against vmh_{q} {hubface} face across a 21.6-um channel, clear of plan blocks, '
                          f'hub face pin windows and RF footprints; E (hub) face toward the hub')
        for t in log['translated']:
            if t['slot'] == s['name']:
                t.update(rehomed=dict(rule='calendar beside hub', origin=s['origin'],
                                      move_um=round(abs(nc[0] - oc[0]) + abs(nc[1] - oc[1]), 3), hub_gap_um=ch))
    for h in C['pc_homes']['homes'].values():
        h['x'], h['y'], _ = tr(h['x'], h['y'])
    if rf_fp:
        rr = {x['route']: x for x in rfa['routes']}
        for r in C['su_rf_relays_v7']['routes']:
            key = f"{r['src']}>{r['dst']}"
            cells = sorted((c for c in rfa['cells'] if c['route'] == key), key=lambda c: c['index'])
            assert len(cells) == r['stages'] == 36, (key, len(cells))
            r['homes'] = [[round(c['rect']['x'] + c['rect']['w'] / 2, 3), round(c['rect']['y'] + c['rect']['h'] / 2, 3)] for c in cells]
            r['footprints'] = [dict(name=c['name'], cell=c['cell'], **c['rect']) for c in cells]
            r['path'] = rr[key]['path']; r['length_um'] = rr[key]['length_um']
            hops = rr[key]['allocated_hop_um']
            r['max_hop_um'] = max(hops) if hops else r.get('max_hop_um')
        C['su_rf_relays_v7']['rule'] = (f'H-DIE-V790 10-16: allocated standard-48 footprints on the centre-route witness '
                                       f'({a.plan}/rf_centre_routes.json + rf_centre_allocation.json; geometry only)')
    else:
        for r in C['su_rf_relays_v7']['routes']:
            r['homes'] = [list(tr(x, y)[:2]) for x, y in r['homes']]
            if DQ and r['src'] != r['dst']:
                # A2P half die: the cross-quadrant RF route is a short straight run between the two quarter cores (the
                # bands abut at the die centre); the contract's stage count is kept (equal-age pad, compiler-fixed) and its
                # homes spread evenly along the src-core -> dst-core centre line (Manhattan: vertical, then horizontal)
                a_, b_ = P6[f"sucore_{r['src']}"], P6[f"sucore_{r['dst']}"]
                up = b_['y'] > a_['y']
                p0 = (a_['x'] + a_['w'] / 2, a_['y'] + (a_['h'] if up else 0.0))
                p1 = (b_['x'] + b_['w'] / 2, b_['y'] + (0.0 if up else b_['h']))
                L = abs(p1[1] - p0[1]) + abs(p1[0] - p0[0]); n_ = len(r['homes'])
                hs = []
                for i in range(n_):
                    t = (i + 1) * L / (n_ + 1); dy = abs(p1[1] - p0[1])
                    hs.append([round(p0[0], 3), round(p0[1] + (t if up else -t), 3)] if t <= dy else
                              [round(p0[0] + (t - dy) * (1 if p1[0] > p0[0] else -1), 3), round(p1[1], 3)])
                r.update(homes=hs, length_um=round(L, 3), max_hop_um=round(L / (n_ + 1), 3), footprints=[],
                         path=[list(p0), [p0[0], p1[1]], list(p1)],
                         note=f'A2P half die: {n_} equal-age stages kept on a {L:.0f} um core-to-core run (H-NETLIST may '
                              'reduce the count; the compiler table must follow)')
    for r in C.get('request_slots', []):
        for key in ('groups', 'port_groups'):
            for g in r.get(key, []) or []:
                if g['name'] in P6:
                    b = P6[g['name']]
                    g['origin'] = dict(x=b['x'], y=b['y']); g['outline'] = dict(w=b['w'], h=b['h'])
        if r.get('core') and r['core']['name'] in P6:
            b = P6[r['core']['name']]
            r['core']['origin'] = dict(x=b['x'], y=b['y']); r['core']['outline'] = dict(w=b['w'], h=b['h'])
    if 'sfu_core_request_v7' in C:
        C['sfu_core_request_v7']['status'] = 'SUPERSEDED by sfu_core_home_0030 (granted); boxes are v5 coordinates'
    # 3. pin windows + exact pins for re-planned slots
    import rtl_pin_grants_1405 as R
    for b, v in pins6['blocks'].items():
        s = S.get(b) or S.get('hb_' + b)
        if not s or s.get('parent') != 'die' or 'pin_windows' not in s:
            continue
        s['pin_windows'] = [dict(face=f, layer=LAYER[f], offset=p['offset_um'], span_um=p['span_um'], bits=p['bits'],
                                 peer=p['peer'], cls=p['cls'], link=p['link'])
                            for f, fx in v['faces'].items() for p in fx['pins']]
    ref = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short=9', 'HEAD'], capture_output=True, text=True).stdout.strip()
    sha = {k: __import__('hashlib').sha256(R.git('HEAD', p)).hexdigest() for k, p in R.SRC.items()}
    rfp = json.loads((ROOT / R.RFP).read_text())
    rf = copy.deepcopy(rfp)
    for rr in rf['routes']:
        for e in ('src_pin', 'dst_pin'):
            blk = rr[e]['block']
            if blk in P5 and blk in P6:
                rr[e]['xy'] = [rr[e]['xy'][0] - P5[blk]['x'] + P6[blk]['x'], rr[e]['xy'][1] - P5[blk]['y'] + P6[blk]['y']]
    regrant = []
    for q in [q_ for q_ in R.QID if q_ in KQ]:
        for g in range(4):
            sl, co = P6[f'su_{q}{g}'], P6[f'sucore_{q}']
            corex = 'E' if co['x'] > sl['x'] else 'W'        # v6b: the quarter core may sit between slices
            R.grant_su(S[f'su_{q}{g}'], R.ports('pgslice', dict(QID=R.QID[q], G=g)), q, g, ref, sha['pgslice'], corex=corex); regrant.append(f'su_{q}{g}')
        R.grant_core(S[f'sucore_{q}'], R.ports('qcore', {}), q, rf, ref, sha['qcore']); regrant.append(f'sucore_{q}')
        # H-SM 10-16 03:2x: SM slot 7,200 x 1,800 with NO in-slot 40-um feedthrough (relays use die channels)
        ff, fr = R.ft_forbid, R.ft_record
        R.ft_forbid, R.ft_record = (lambda o: {}), (lambda o: [])
        R.SM_CARVE = a.sm_carve
        if a.sm_carve is None:      # v6b..v5: no SM feedthrough; with --sm-carve grant_sm uses the edge carve
            R.ft_forbid_sm, R.ft_record_sm = R.ft_forbid, R.ft_record
        try:
            for i in range(8):
                if a.sm_column:
                    sm_ = S[f'sm_{q}{i}']
                    sm_.update(pins=[], pin_status='FACES_ONLY', reserved_channels=[],
                               notes=f'A2P SM column {sm_["outline"]["w"]} x {sm_["outline"]["h"]}: SM_HBM window on the PC-row '
                                     'short face, xw (>= 360 um) on the band short face; H-SM native portrait column kit pending '
                                     '(coordinator 10-16 19:30); exact pins from that kit')
                    regrant.append(f'sm_{q}{i}:FACES_ONLY'); continue
                R.grant_sm(S[f'sm_{q}{i}'], R.ports('sm', {}), ref, sha['sm']); regrant.append(f'sm_{q}{i}')
                S[f'sm_{q}{i}']['notes'] = S[f'sm_{q}{i}']['notes'].replace('die feedthrough column+row reserved',
                                                                              'no in-slot feedthrough (H-SM 10-16; relays in die channels)'
                                                                              if a.sm_carve is None else
                                                                              f'OWNER feedthrough carve: W-edge column + N-edge row {a.sm_carve} um (H-SM rp4c)')
        finally:
            R.ft_forbid, R.ft_record = ff, fr
    if a.homes:
        for k, h in json.loads(Path(a.homes).read_text()).items():
            if k in S:
                S[k]['origin'] = dict(x=h['x'], y=h['y'], orient=h.get('orient', S[k]['origin'].get('orient', 'R0')))
                S[k]['home_rule'] = h.get('rule', 'explicit home (--homes)')
                log.setdefault('explicit_homes', []).append(k)
    # 4. audit
    tops = []
    for s in slots[1:]:
        if s.get('parent') != 'die' or s['origin'].get('x') is None:
            continue
        fp = s.get('placed_footprint') or s['outline']
        orient = s['origin'].get('orient', 'R0')
        w, h = (fp['h'], fp['w']) if (orient in SWAP and not s.get('placed_footprint')) else (fp['w'], fp['h'])
        tops.append((s['name'], s['origin']['x'], s['origin']['y'], w, h, s.get('plan_block')))
    rep_blocks = {t[5] for t in tops if t[5]}
    others = [(k, b['x'], b['y'], b['w'], b['h'], None) for k, b in P6.items() if k not in rep_blocks]
    outside = [t[0] for t in tops if t[1] < 20 - 1e-6 or t[2] < 20 - 1e-6 or t[1] + t[3] > W - 20 + 1e-6 or t[2] + t[4] > H - 20 + 1e-6]
    ov = []
    allr = tops + others
    for i, (n, x, y, w, h, _) in enumerate(tops):
        for (m, c, d, e, f, _) in allr:
            if m == n:
                continue
            if x < c + e - 1e-6 and c < x + w - 1e-6 and y < d + f - 1e-6 and d < y + h - 1e-6:
                if (m, n) not in ov:
                    ov.append((n, m))
    hard = [t for t in tops if not t[0].startswith(('svc_', 'host_cp'))]

    def inside(x, y, own=()):
        return [t[0] for t in hard if t[0] not in own and t[1] < x < t[1] + t[3] and t[2] < y < t[2] + t[4]]
    bad_pts = []
    for k, h in C['pc_homes']['homes'].items():
        hit = inside(h['x'], h['y'], own=(h.get('band'),))
        if hit:
            bad_pts.append((k, hit))
    for r in C['su_rf_relays_v7']['routes']:
        for x, y in r['homes']:
            hit = inside(x, y)
            if hit:
                bad_pts.append((f"rf {r['src']}>{r['dst']}", hit)); break
    tops_rects = tops + others                           # RF footprints may not overlap ANY die-level footprint
    for n, b in rf_fp:
        x, y, w, h = b['x'], b['y'], b['w'], b['h']
        hit = [t[0] for t in tops_rects if x < t[1] + t[3] - 1e-6 and t[1] < x + w - 1e-6 and y < t[2] + t[4] - 1e-6 and t[2] < y + h - 1e-6]
        if x < 20 - 1e-6 or y < 20 - 1e-6 or x + w > W - 20 + 1e-6 or y + h > H - 20 + 1e-6:
            outside.append(n)
        if hit:
            bad_pts.append((n, hit))
    for i in range(len(rf_fp)):
        for j in range(i + 1, len(rf_fp)):
            p_, q_ = rf_fp[i][1], rf_fp[j][1]
            if p_['x'] < q_['x'] + q_['w'] - 1e-6 and q_['x'] < p_['x'] + p_['w'] - 1e-6 and p_['y'] < q_['y'] + q_['h'] - 1e-6 and q_['y'] < p_['y'] + p_['h'] - 1e-6:
                ov.append((rf_fp[i][0], rf_fp[j][0]))
    C['version'] = int(C.get('version', 1)) + 1
    C['floorplan'] = dict(file=str(a.plan) + '/compact.P.json', candidate=Path(a.plan).name, adopted=a.adopted,
                          die_um=[round(W, 3), round(H, 3)], metrics=M6.get('metrics'), previous=C.get('floorplan'))
    C['rehome_v6'] = dict(plan=a.plan, old=a.old, quadrants=a.quadrants, dropped_slots=dropped, explicit_homes=log.get('explicit_homes', []), mapped=len(log['mapped']), resized=log['resized'], new=log['new'],
                          translated=log['translated'], regranted_pins=regrant, outside=outside, overlaps=ov,
                          points_in_hard_blocks=bad_pts)
    C['updated'] = subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip()
    summary = dict(dropped=len(dropped), die=die['outline'], mapped=len(log['mapped']), resized=len(log['resized']), new=log['new'],
                   translated=len(log['translated']), regranted=len(regrant), outside=outside, n_overlaps=len(ov),
                   overlaps=ov[:12], points_in_hard_blocks=bad_pts[:12], n_bad_points=len(bad_pts))
    print(json.dumps(summary))
    C['rehome_v6']['qualification'] = 'UNQUALIFIED_GEOMETRY_PROPOSAL'
    C['rehome_v6']['blockers'] = summary
    if not a.dry_run:
        if not a.out and (outside or ov or bad_pts):
            raise SystemExit('Refusing active-contract adoption: geometry audit failed; use --out for a diagnostic proposal')
        (ROOT / a.out if a.out else cp).write_text(json.dumps(C, indent=1) + '\n')


if __name__ == '__main__':
    main()
