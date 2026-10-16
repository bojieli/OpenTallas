#!/usr/bin/env python3
"""Strap-identity VM bank masters (H-SM 2026-10-15, coordinator decision per DEDUPE results/arch/tile_dedupe_1015).

One master per quadrant (hfd_vms_bank_strap_q0..3) for all 8 banks of that quadrant.  Pins = the identity2 b0 grant
(vm_identity_grants_1417.json r2: every bit on an actual M4/M5 track, M5 centres PG-clear, explicit per-bit centres)
plus five STRAP pins bid[2:0] / sid[1:0] on the N face, on free legal M5 tracks between the clock pair and the right
N bus region (same legality rule as the r2 grant: first track 0.012, pitch 0.048, clear of the M5 PG projections,
bit pitch >= 0.096).  The die ties each instance's straps to its constants (strap_table.json); the master registers
them at the pins.  PROPOSAL for H-DIE: not adopted into the canonical die contract by this tool.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = 'results/arch/hbm_die_v15/vm_identity_grants_1417.json'
OUT = 'results/arch/hbm_die_v15/vm_strap_grants_1015.json'
g = json.loads((ROOT / SRC).read_text())
slots = []
for q in range(4):
    s = json.loads(json.dumps(next(x for x in g['slots'] if x['cell'] == f'hfd_vms_bank_identity_q{q}_b0')))
    W = s['outline']['w']; CORE = 2.16; T0, TP = .012, .048
    pg = []; k = 0
    while CORE + .3 + 5.4 * k - .06 < W:
        a = CORE + .3 + 5.4 * k - .06; pg += [(a, a + .12), (a + .192, a + .312)]; k += 1
    used = sorted(c for p in s['pins'] if p['face'] == 'N' for c in p['bit_centres_um'])
    rst = next(p for p in s['pins'] if p['name'] == 'rst_n')['bit_centres_um'][0]
    nxt = min(c for c in used if c > rst + 1e-9)
    cand = []
    i = int((rst - T0) / TP) + 1
    while T0 + i * TP < nxt - .096 + 1e-9:
        c = round(T0 + i * TP, 6); i += 1
        if c - rst < .096 - 1e-9: continue
        if any(c + .036 > a - 1e-9 and c - .036 < b + 1e-9 for a, b in pg): continue
        if cand and c - cand[-1] < .096 - 1e-9: continue
        cand.append(c)
    assert len(cand) >= 5, (q, rst, nxt, cand)
    j = 0
    for n, w in (('bid', 3), ('sid', 2)):
        cs = cand[j:j + w]; j += w
        s['pins'].append(dict(name=f'{n}[{w-1}:0]', face='N', layer='M5', offset=round((cs[0] + cs[-1]) / 2, 6),
                              span_um=[round(cs[0] - .048, 6), round(cs[-1] + .048, 6)], bit_centres_um=cs,
                              bit_pitch_um=min([round(b - a, 6) for a, b in zip(cs, cs[1:])] or [.096]),
                              bit_centres_rule='explicit bit_centres_um[bit_index] (actual track, PG-clear)',
                              strap=True))
        s['pin_ranges'][n] = [round(cs[0] - .048, 6), round(cs[-1] + .048, 6)]
    s.update(name=f'vmb_{("SW","SE","NW","NE")[q]}_strap_master', cell=f'hfd_vms_bank_strap_q{q}',
             source=f'rtl/hbm_accel/generic/vm/static/physical/hfd_vms_bank_strap_q{q}.sv',
             instances=[f'vmb_{("SW","SE","NW","NE")[q]}{b}' for b in range(8)],
             strap_values={f'vmb_{("SW","SE","NW","NE")[q]}{b}': dict(bid=b, sid=q) for b in range(8)},
             grant='strap_identity_master_proposal_1015')
    for k2 in ('compile_time_identity', 'source_sha256', 'source_dependencies_sha256', 'parent', 'parent_plan_window', 'origin', 'scope'):
        s.pop(k2, None)
    s['scope'] = ('Strap-identity quadrant master: one hardened view for the 8 banks of the quadrant; bid/sid strap pins registered '
                  'at the pins, tied to die constants per instance. Proposal for H-DIE (strap pins + per-instance tie).')
    slots.append(s)
out = dict(schema='opentallas.hier_contract.v1', die='hbm_v15', version=1, rules=g['rules'], clock_period_ps=g['clock_period_ps'],
           slots=slots, derived_from=SRC, canonical_die_contract_mutated=False, proposal_for='H-DIE')
(ROOT / OUT).write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({s['cell']: [p['bit_centres_um'] for p in s['pins'] if p.get('strap')] for s in slots}))
