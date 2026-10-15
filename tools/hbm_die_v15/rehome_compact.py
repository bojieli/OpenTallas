#!/usr/bin/env python3
"""Re-home the v15 grants (results/arch/hier_contract_1015/hbm_v15.json, every master-frame pin plan, child slot and
service window kept) onto the compact die plan (tools/hbm_die_v15/compact_plan.py; owner 2026-10-15 12:05: 660 mm2).

    rehome_compact.py --plan DIR [--contract results/arch/hier_contract_1015/hbm_v15.json]

Only the die outline, top-level origins and orientations change.  The quadrant topology of the compact plan equals the
T_band2 one the pin plans were made for (VM banks on the outer side, hub/COLL/centre column on the inner side, PHY/PC
row on the edge), so orientations are kept, except the IDX scorers which turn 90 degrees into the centre column
(keys enter from their own die half, scores toward the central glue).  SFU engine slots become REQUESTS: the compact
groups need the SFU as 4 bank-pair leaves (fixed-return LG links <= 500 um to both banks of each pair) -- one 0.4 mm2
box per group -- which the single-engine master cannot be placed as.  Every placed footprint is checked for overlap
against every other grant and every compact-plan block it does not replace.
"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SWAP = {'R90', 'R270', 'MXR90', 'MYR90'}
IDX_ORIENT = {'idx_s0': 'MYR90', 'idx_s1': 'R270', 'idx_s3': 'MXR90', 'idx_s2': 'R90'}   # SW, SE (south) / NE, NW (north)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--contract', default='results/arch/hier_contract_1015/hbm_v15.json')
    a = ap.parse_args()
    pd = Path(a.plan)
    P = json.loads((pd / 'compact.P.json').read_text())
    M = json.loads((pd / 'compact.metrics.json').read_text())
    W, H = M['die_um']
    cp = ROOT / a.contract
    C = json.loads(cp.read_text())
    slots = C['slots']
    die = slots[0]
    assert die['kind'] == 'die'
    die['outline'] = dict(w=round(W, 3), h=round(H, 3))
    die['notes'] = 'compact die (owner 2026-10-15 12:05, 660 mm2); grow only on measured GRT congestion / area misfit'
    mapping, placed, moved, requests = {}, {}, [], []
    keep = []
    for s in slots[1:]:
        if s.get('parent') != 'die':
            keep.append(s)
            continue
        n = s['name']
        blk = None
        if n.startswith('coll_') or n.startswith('idx_') or n == 'vm_status4':
            blk = n if n in P else None
        elif n.startswith('hb_dbk_'):
            blk = 'dbk_' + n[-2:]
        elif n.startswith('svc_'):
            q, k = n[4:6], int(n.split('_s')[1])
            blk = f'pc_{q}{k}' if k < 8 else None
        elif n.startswith('hb_sfu_'):
            requests.append(dict(name=n, cell=s['cell'], rtl_pending=(
                'SFU as 4 bank-pair port-group leaves sfu_%s0..3 (0.40 mm2 each, compact boxes 500 x 800 left of each bank '
                'pair; fixed-return LG_SFU <= 500 um to both banks) + engine core; the 4 LG roots exist in source on '
                'codex/hbm-die-takeover-1103 f94fb79fd/80d1f4413 -> physical leaf partition = H-ELEM-B / hbm_su_sm' % n[-2:]),
                groups=[dict(name=f'sfu_{n[-2:]}{g}', origin=dict(x=P[f'sfu_{n[-2:]}{g}']['x'], y=P[f'sfu_{n[-2:]}{g}']['y']),
                             outline=dict(w=P[f'sfu_{n[-2:]}{g}']['w'], h=P[f'sfu_{n[-2:]}{g}']['h'])) for g in range(4)],
                previous_grant=dict(outline=s['outline'], pins=len(s['pins']))))
            continue
        w, h = s['outline']['w'], s['outline']['h']
        orient = IDX_ORIENT.get(n, s['origin'].get('orient', 'R0'))
        fw, fh = (h, w) if orient in SWAP else (w, h)
        if blk:
            b = P[blk]
            x, y = b['x'], b['y']
            if (fw > b['w'] + 1e-3 or fh > b['h'] + 1e-3) and h <= b['w'] + 1e-3 and w <= b['h'] + 1e-3 and orient not in SWAP:
                orient, fw, fh = 'R90', h, w      # the plan box is the rotated outline
            if fw > b['w'] + 1e-3 or fh > b['h'] + 1e-3:
                moved.append(dict(slot=n, note=f'footprint {fw}x{fh} > plan box {b["w"]}x{b["h"]}'))
        else:
            x = y = None
        s['origin'] = dict(x=x, y=y, orient=orient)
        s['placed_footprint'] = dict(w=fw, h=fh)
        s['plan_block'] = blk
        mapping[n] = blk
        keep.append(s)
    # homes for grants without a plan block: 9th service band at the PC-row end, status4 near the hub centroid
    occ = [(k, r['x'], r['y'], r['w'], r['h']) for k, r in P.items() if k not in set(mapping.values())]
    for s in keep:
        if s.get('parent') == 'die' and s['origin'].get('x') is not None:
            occ.append((s['name'], s['origin']['x'], s['origin']['y'], s['placed_footprint']['w'], s['placed_footprint']['h']))

    def free(x, y, w, h, gap=20.0):
        if x < 20 or y < 20 or x + w > W - 20 or y + h > H - 20:
            return False
        return all(not (x < c + e + gap and c < x + w + gap and y < d + f + gap and d < y + h + gap) for _, c, d, e, f in occ)

    def near(cx, cy, w, h):
        for r in range(0, 20000, 20):
            for k in range(max(1, int(2 * math.pi * r / 20))):
                t = 2 * math.pi * k / max(1, int(2 * math.pi * r / 20))
                x, y = round(cx + r * math.cos(t) - w / 2, 2), round(cy + r * math.sin(t) - h / 2, 2)
                if free(x, y, w, h):
                    return x, y
        raise SystemExit('no home')
    for s in keep:
        if s.get('parent') != 'die' or s['origin'].get('x') is not None:
            continue
        w, h = s['placed_footprint']['w'], s['placed_footprint']['h']
        if s['name'].startswith('svc_'):
            q = s['name'][4:6]
            last = P[f'pc_{q}7']
            east = q in ('SW', 'NW')
            cx = last['x'] + (last['w'] + 20 + w / 2 if east else -20 - w / 2)
            x, y = near(cx, last['y'] + last['h'] / 2, w, h)
        else:
            hubs = [P['vmh_' + q] for q in ('SW', 'SE', 'NW', 'NE')]
            x, y = near(W / 2, H / 2, w, h)
        s['origin']['x'], s['origin']['y'] = x, y
        moved.append(dict(slot=s['name'], note=f'no plan block: nearest free home ({x}, {y})'))
        occ.append((s['name'], x, y, w, h))
    # overlap audit of every top-level footprint vs each other and vs non-replaced plan blocks
    tops = [(s['name'], s['origin']['x'], s['origin']['y'], s['placed_footprint']['w'], s['placed_footprint']['h'])
            for s in keep if s.get('parent') == 'die']
    blocks = [(k, r['x'], r['y'], r['w'], r['h']) for k, r in P.items() if k not in set(mapping.values())]
    bad = []
    allr = tops + blocks
    for i, (n, x, y, w, h) in enumerate(tops):
        for (m, c, d, e, f) in allr:
            if m == n:
                continue
            if x < c + e and c < x + w and y < d + f and d < y + h:
                bad.append((n, m))
    C['slots'] = [die] + keep
    C['version'] = int(C.get('version', 1)) + 1
    C['floorplan'] = dict(file=str(pd / 'compact.P.json'), candidate='compact660', adopted='owner 2026-10-15 12:05 (660 mm2 compact)',
                          die_um=[round(W, 3), round(H, 3)], metrics=M['metrics'], previous=C.get('floorplan'))
    C['request_slots'] = [r for r in C.get('request_slots', []) if not r['name'].startswith('hb_sfu_')] + requests
    for r in C['request_slots']:
        if r['name'].startswith('hb_su_') and r.get('port_groups'):
            q = r['name'][6:8]
            for g in r['port_groups']:
                b = P[g['name']]
                g['origin'] = dict(x=b['x'], y=b['y']); g['outline'] = dict(w=b['w'], h=b['h'])
            r['core'] = dict(name=f'sucore_{q}', origin=dict(x=P[f'sucore_{q}']['x'], y=P[f'sucore_{q}']['y']),
                             outline=dict(w=P[f'sucore_{q}']['w'], h=P[f'sucore_{q}']['h']))
    C['rehome_compact'] = dict(moved=moved, overlaps=bad, sfu_to_request=[r['name'] for r in requests])
    cp.write_text(json.dumps(C, indent=1) + '\n')
    print(json.dumps(dict(version=C['version'], die=die['outline'], top_slots=len(tops), moved=moved, overlaps=bad[:10],
                          n_overlaps=len(bad), sfu_requests=len(requests))))


if __name__ == '__main__':
    main()
