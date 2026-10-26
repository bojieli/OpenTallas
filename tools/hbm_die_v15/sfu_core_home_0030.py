#!/usr/bin/env python3
"""SFU core homes (H-DIE 0030, 2026-10-16, answer to H-SU SLOT CHANGE REQUEST 01:10): one outline for all four
ot_hgi_sfu_scheduled_engine instances (sfucore_<q>, fewer-masters rule), in the free band gap between the SU quarter core
and the COLL/DMA-back stack of each quadrant (compact660_v5; no plan block or grant slot there).  Checks every candidate
against every grant slot and plan block with a 21.6 um channel, and reports the LG path relay stages R (480 um reach,
centre-to-centre Manhattan) to the four SFU bank-pair leaves vs the v7 request (4000 x 400 mid-band strip, R_padded 11).
Writes results/arch/hbm_die_v15/sfu_core_home_0030/homes.json; does NOT edit the grants (H-SU accepts first)."""
import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
G = json.loads((ROOT / 'results/arch/hier_contract_1015/hbm_v15.json').read_text())
P = json.loads((ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json').read_text())
W, H, CH = 763.56, 1936.44, 21.6           # 707 x 1.08, 1793 x 1.08 um: fits the narrowest (NW/NE) gap
X0 = {'SW': 10861.232, 'SE': 19202.56 , 'NW': 11008.112, 'NE': 19123.0}   # gap west edge (sucore E / dbk-coll E)
Y0 = {'SW': 5102.56, 'SE': 5102.56, 'NW': 14195.133, 'NE': 14195.133}
rects = []
for s in G['slots']:
    o, w = s.get('origin'), s.get('outline')
    if o and w and s['name'] != 'die':
        rects.append((s['name'], o['x'], o['y'], o['x'] + w['w'], o['y'] + w['h']))
for n, b in P.items():
    if isinstance(b, dict) and 'x' in b:
        rects.append(('P:' + n, b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
out = {}
for q in ('SW', 'SE', 'NW', 'NE'):
    x = round(math.ceil((X0[q] + CH) / 0.216) * 0.216, 3); y = round(math.ceil((Y0[q] + CH) / 0.27) * 0.27, 3)
    if q in ('SE', 'NE'):   # east quadrants: gap runs from dbk/coll E edge to sucore W edge
        x = round(math.floor((P[f"sucore_{q}"]["x"] - CH - W) / 0.216) * 0.216, 3)
    box = (x, y, x + W, y + H)
    hits = [r[0] for r in rects if r[1] < box[2] + CH and r[3] > box[0] - CH and r[2] > box[1] - CH and r[4] < box[3] + CH]
    hits = [h for h in hits if not (r := next(z for z in rects if z[0] == h)) or
            (r[1] < box[2] + CH - 1e-6 and r[3] > box[0] - CH + 1e-6 and r[2] < box[3] + CH - 1e-6 and r[4] > box[1] - CH + 1e-6)]
    cx, cy = x + W / 2, y + H / 2
    R = {}
    for k in range(4):
        b = P[f'sfu_{q}{k}']
        d = abs(b['x'] + b['w'] / 2 - cx) + abs(b['y'] + b['h'] / 2 - cy)
        R[f'sfu_{q}{k}'] = dict(dist_um=round(d), R=max(0, math.ceil(d / 480) - 1))
    out[f'sfucore_{q}'] = dict(cell='ot_hgi_sfu_scheduled_engine', origin=dict(x=x, y=y, orient='R0'),
                               outline=dict(w=W, h=H), area_mm2=round(W * H / 1e6, 4), conflicts=hits, leaf_R=R)
rmax = max(v['R'] for h in out.values() for v in h['leaf_R'].values())
res = dict(schema='opentallas.hbm_v15.sfu_core_home.v1', status='CANDIDATE (H-SU to accept)', homes=out,
           R_padded=rmax, v7_request_R_padded=G['sfu_core_request_v7']['R_padded'],
           note='inner-end homes need no SM change but lengthen the far-leaf LG path; v7 strip needs H-SM to shrink band-side SM rows by 420 um')
p = ROOT / 'results/arch/hbm_die_v15/sfu_core_home_0030/homes.json'
p.write_text(json.dumps(res, indent=1) + '\n')
for n, h in out.items():
    print(n, h['origin'], h['area_mm2'], 'conflicts', h['conflicts'], {k: v['R'] for k, v in h['leaf_R'].items()})
print('R_padded', rmax, 'vs v7', res['v7_request_R_padded'])


def write_slots():
    """H-SU ACCEPTED 01:3x 10-16: write the four sfucore_<q> slots into the v15 grants (outline/origin/faces; exact pins are
    assigned top-down from the RTL ports by the pin tools when the kit is made)."""
    gp = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
    g = json.loads(gp.read_text())
    homes = json.loads(p.read_text())['homes']
    g['slots'] = [s for s in g['slots'] if not s['name'].startswith('sfucore_')]
    for n, h in homes.items():
        g['slots'].append(dict(
            name=n, cell=h['cell'], kind='tile', parent='die', outline=h['outline'], origin=h['origin'],
            clock_entry=dict(pin='clk', face='N', layer='M5', offset=round(W / 2, 3)), pg_layer='M5', strap_layer='M6',
            signal_max_layer='M5', layer_cap='M5', io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), version=1,
            grant='sfu_core_home_0030', rtl_owner='H-SU: ot_hgi_sfu_scheduled_engine',
            faces=dict(W='SU qcore / SFU leaf LG paths (band)', E='COLL / DMA-back stack', N='clock + reset', S='band channel'),
            notes='SFU engine core home in the band gap sucore<->COLL/DBK (H-DIE 0030, H-SU accepted); one outline for all 4; '
                  'LG path R_padded 23; every pin registered (owner rule 19:50)', pins=[], pin_status='FACES_ONLY'))
    g['sfu_core_home_0030'] = dict(source='results/arch/hbm_die_v15/sfu_core_home_0030/homes.json', status='GRANTED',
                                   supersedes='sfu_core_request_v7 (PROPOSED strip, needed SM shrink)')
    gp.write_text(json.dumps(g, indent=1) + '\n')


if __name__ == '__main__' and __import__('sys').argv[1:] == ['--write-slots']:
    write_slots()
