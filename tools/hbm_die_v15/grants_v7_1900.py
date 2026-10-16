#!/usr/bin/env python3
"""H-DIE grants v7 step 1 (2026-10-15 ~19:00, coordinator relay of H-COLL+IDX requests):
 (1) COLL writer v4 (ot_hgi_coll_static_vmwrite, 103.68 x 388.8): tkw_d[482] native capture 192.8 > 190 ps from the
     crowded S face (569 pins on 103.68 um).  tkw_d[567:284] moves to the W face, lowest part (next to the S corner,
     below rgx_*): W M4 [24.576, 51.84]; tkw_v + tkw_d[283:0] stay S M5 [24.528, 51.888].  Same bits, same order.
 (2) COLL state: the captured-state lane ot_hgi_coll_pring_static_state_capture_lane (closed TT +203.25 / FF +26.87,
     native PASS; identical port list, same 64.8 x 64.8 outline) replaces ot_hgi_coll_pring_static_state_lane in all 32
     state slots.  Cost accepted by the coordinator (+10 % per ring pass, <= 1.3 % tok/s, inside the ledger).
 (3) IDX scorers idx_s0..s3: rst_n, rank, first_ord, nkeys, keep_en, keep_bitmap (374 b, driven from idx_sel/idx_op/idx_q)
     move from local E to local W after ql_*/score/fault (the face toward the glue row), W M4 [1561.608, 1597.512];
     clocks stay local E (die clock entry).
Idempotent; writes the grants file and a 'grants_v7_1900' record.
"""
import hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
GF = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
CAP_SRC = 'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static_state_capture.sv'
G = json.loads(GF.read_text())
S = {s['name']: s for s in G['slots']}
rec = dict(date='2026-10-15', owner='H-DIE', requests='H-COLL+IDX via coordinator', changes=[])
# (1) writer
for q in ('SW', 'SE', 'NW', 'NE'):
    s = S[f'coll_{q}_writer0']
    pins = [p for p in s['pins'] if not p['name'].startswith('tkw_d')]
    pins.insert(next(i for i, p in enumerate(pins) if p['name'] == 'tkw_v') + 1,
                dict(name='tkw_d[283:0]', face='S', layer='M5', span_um=[24.624, 24.624 + 284 * 0.096]))
    pins.append(dict(name='tkw_d[567:284]', face='W', layer='M4', span_um=[24.576, 24.576 + 284 * 0.096]))
    for p in pins:
        p['span_um'] = [round(x, 3) for x in p['span_um']]
    s['pins'] = pins; s['version'] = 7
rec['changes'].append('writer x4: tkw_d[567:284] -> W M4 [24.576, 51.84]; tkw_d[283:0] S M5 [24.624, 51.888]')
# (2) state
sha = hashlib.sha256((ROOT / CAP_SRC).read_bytes()).hexdigest()
n = 0
for s in G['slots']:
    if s['cell'] in ('ot_hgi_coll_pring_static_state_lane', 'ot_hgi_coll_pring_static_state_capture_lane'):
        s['cell'] = 'ot_hgi_coll_pring_static_state_capture_lane'; s['source'] = CAP_SRC; s['source_sha256'] = sha
        s['view'] = 'physical/ref_tile/hcoll_ring_state_capture_1417/views/ot_hgi_coll_pring_static_state_capture_lane'
        s['version'] = 7; n += 1
rec['changes'].append(f'state x{n}: cell ot_hgi_coll_pring_static_state_capture_lane (same ports/outline), cost accepted')
# (3) idx
CTL = ('rst_n', 'rank', 'first_ord', 'nkeys', 'keep_en', 'keep_bitmap')
for q in range(4):
    s = S[f'idx_s{q}']
    keep = [p for p in s['pins'] if re.sub(r'\[.*', '', p['name']) not in CTL]
    moved = [p for p in s['pins'] if re.sub(r'\[.*', '', p['name']) in CTL]
    x = 1561.608
    for p in moved:
        m = re.search(r'\[(\d+):(\d+)\]', p['name']); nb = int(m.group(1)) - int(m.group(2)) + 1 if m else 1
        p.update(face='W', layer='M4', span_um=[round(x, 3), round(x + nb * 0.096, 3)]); x += nb * 0.096
    s['pins'] = keep + moved; s['version'] = 7
rec['changes'].append('idx_s0..s3: 374 control bits local E -> local W [1561.608, 1597.512] next to ql_*/score; clocks stay E')
for s in G['slots']:
    if s.get('version') == 7:
        for p in s.get('pins', []):
            p['offset'] = round((p['span_um'][0] + p['span_um'][1]) / 2, 3)
G['grants_v7_1900'] = rec
GF.write_text(json.dumps(G, indent=1) + '\n')
print(json.dumps(rec, indent=1))
