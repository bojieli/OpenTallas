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
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', help='write an explicitly unqualified proposal here, preserving the active contract')
    a = ap.parse_args()
    pd, od = ROOT / a.plan, ROOT / a.old
    P6 = json.loads((pd / 'compact.P.json').read_text()); P5 = json.loads((od / 'compact.P.json').read_text())
    M6 = json.loads((pd / 'compact.metrics.json').read_text()); W, H = M6['die_um']
    pins6 = json.loads(next((pd / 'pins').glob('*.pins.json')).read_text())
    cp = ROOT / a.contract
    C = json.loads(cp.read_text())
    slots = C['slots']
    die = slots[0]; assert die['kind'] == 'die'
    die['outline'] = dict(w=round(W, 3), h=round(H, 3))
    die['notes'] = 'v6b die (H-DIE 0300 10-16, OWNER 02:15: grow where area fixes a measured fit/congestion problem)'
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
        if s['name'].startswith(('sm_', 'su_', 'sucore_', 'vmh_')) and \
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
        s['origin'] = dict(x=round(o['x'] + dx, 3), y=round(o['y'] + dy, 3), orient=o.get('orient', 'R0'))
        log['translated'].append(dict(slot=s['name'], anchor=k, dx=round(dx, 3), dy=round(dy, 3)))
    for h in C['pc_homes']['homes'].values():
        h['x'], h['y'], _ = tr(h['x'], h['y'])
    for r in C['su_rf_relays_v7']['routes']:
        r['homes'] = [list(tr(x, y)[:2]) for x, y in r['homes']]
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
    for q in R.QID:
        for g in range(4):
            sl, co = P6[f'su_{q}{g}'], P6[f'sucore_{q}']
            corex = 'E' if co['x'] > sl['x'] else 'W'        # v6b: the quarter core may sit between slices
            R.grant_su(S[f'su_{q}{g}'], R.ports('pgslice', dict(QID=R.QID[q], G=g)), q, g, ref, sha['pgslice'], corex=corex); regrant.append(f'su_{q}{g}')
        R.grant_core(S[f'sucore_{q}'], R.ports('qcore', {}), q, rf, ref, sha['qcore']); regrant.append(f'sucore_{q}')
        # H-SM 10-16 03:2x: SM slot 7,200 x 1,800 with NO in-slot 40-um feedthrough (relays use die channels)
        ff, fr = R.ft_forbid, R.ft_record
        R.ft_forbid, R.ft_record = (lambda o: {}), (lambda o: [])
        try:
            for i in range(8):
                R.grant_sm(S[f'sm_{q}{i}'], R.ports('sm', {}), ref, sha['sm']); regrant.append(f'sm_{q}{i}')
                S[f'sm_{q}{i}']['notes'] = S[f'sm_{q}{i}']['notes'].replace('die feedthrough column+row reserved',
                                                                              'no in-slot feedthrough (H-SM 10-16; relays in die channels)')
        finally:
            R.ft_forbid, R.ft_record = ff, fr
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
    C['version'] = int(C.get('version', 1)) + 1
    C['floorplan'] = dict(file=str(a.plan) + '/compact.P.json', candidate=Path(a.plan).name, adopted=a.adopted,
                          die_um=[round(W, 3), round(H, 3)], metrics=M6.get('metrics'), previous=C.get('floorplan'))
    C['rehome_v6'] = dict(plan=a.plan, old=a.old, mapped=len(log['mapped']), resized=log['resized'], new=log['new'],
                          translated=log['translated'], regranted_pins=regrant, outside=outside, overlaps=ov,
                          points_in_hard_blocks=bad_pts)
    C['updated'] = subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip()
    summary = dict(die=die['outline'], mapped=len(log['mapped']), resized=len(log['resized']), new=log['new'],
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
