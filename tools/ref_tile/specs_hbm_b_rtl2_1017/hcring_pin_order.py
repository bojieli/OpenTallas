"""HCRING 10-19: bit order across the HC ring bank joints (follow-up of HH-9's flag).  Run in the worktree root; edits
the five bank specs in place (idempotent), then re-run `ref_tile.py gen` on each.

Ring (mk_ring_kits.py): b0 W, b1 NW, b2 N, b3 NE, b4 E, b5 SE, b6 S, b7 SW on 734.4 um cells; masters e2 = b2 / b6,
e0 = b4, b0 = b0, ca = b1 / b5, cb = b3 / b7; the S row (b5, b6, b7) is placed R180.  Two defects:

1. NO BIT ORDER AT ALL on any face: the route runs with OT_PIN_GROUP_MAX 32 (ref_tile default), i.e. each 2,048-b
   chain bus is 64 ordered groups of 32 in one region, and PPL places the groups independently (measured on the
   closed hbfd_rly_1136_WE view: 13 descents in its 1,136-b i bus, chunks scattered over the face).  Two abutted
   tiles therefore meet chunk-scrambled even when both are R0.  FIX: route.pin_balance (run_abi3_physical place_pin,
   uniform over each port's range, sorted bit order, layer alternating per pin): bit k of a port at
   lo + (hi - lo) (k + 0.5) / n -- deterministic and identical in every kit with the same range.
2. R0 -> R180 joints (HH-9 flag): e0 (b4, R0) S -> ca (b5, R180) S-as-N and cb (b7, R180) S-as-N -> b0 (R0) S.
   ca / cb are shared with the R0 slots b1 / b3, so their pins cannot change; the unique masters e0 and b0 take the
   mirror image of the shared face: range x -> 734.4 - x (130..731.4 -> 3..604.4, NOT the same range) AND high bit
   first (pin_order_desc -> OT_PIN_ORDER_DESC).  With pin_balance the mirror is exact:
   734.4 - (lo + (hi-lo)(k+.5)/n) == (734.4-hi) + (hi-lo)(n-1-k+.5)/n.
Verified by tools/ref_tile/specs_hbm_b_rtl2_1017/hc_ring_joints.py (all 8 joints identity, 0 crossings) and the
geometry-wired ring lockstep (run_hbm_hc_eng4_ring.sh with HC_JOINT_MAP).
"""
import json
from pathlib import Path
RT = Path('physical/ref_tile')
S = 734.4
BAL = {"group_max": 1, "h": "M4 M6", "v": "M5"}       # same layers as the kits' PIN_H / PIN_V
MIRROR = {'hbm_hcq_bank_e0_1017': ['o_v', 'o_ss', 'o_nv', 'o_wa', 'o_xa', 'sum_out', 'f_out'],   # S face -> b5 (R180)
          'hbm_hcq_bank_b0_1017': ['s_i']}                                                     # S face <- b7 (R180)
NOTE = (' HCRING 10-19 (HH-9 flag, R0->R180 joints): route.pin_balance gives every face a defined bit order (PPL '
        'chunks of 32 scattered the buses); faces that abut an R180 neighbour are the mirror image of that '
        'neighbour\'s shared face (range 734.4 - x, high bit first: pin_order_desc).')
for k in ['e0', 'ca', 'cb', 'b0', 'e2']:
    name = f'hbm_hcq_bank_{k}_1017'
    p = RT / name / 'spec.json'
    s = json.loads(p.read_text())
    s['route']['pin_balance'] = dict(BAL)
    if name in MIRROR:
        for port in MIRROR[name]:
            lo, hi = s['pin_ranges'][port]
            if lo >= 100:                      # still the R0 plan (130..731.4) -> mirror once
                s['pin_ranges'][port] = [round(S - hi, 3), round(S - lo, 3)]
        s['pin_order_desc'] = MIRROR[name]
    if 'HCRING' not in s.get('structural_change', ''):
        s['structural_change'] = s.get('structural_change', '') + NOTE
    j = s['job']
    j.update(owner='Claude:HBM-HCRING', branch='claude/hcring-1019', tag='pord1')
    if 'results/rtl/hbm_hc_ring_1019_joint' not in j['extra_paths']:
        j['extra_paths'] = j['extra_paths'] + ['results/rtl/hbm_hc_ring_1019_joint']
    p.write_text(json.dumps(s, indent=1) + '\n')
    print(p, {q: s['pin_ranges'][q] for q in MIRROR.get(name, [])})
