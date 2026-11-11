#!/usr/bin/env python3
"""S81-ARCH-RTL-2 11-11 (COORD slice-4 ruling): derive the slice-4 event plan from the base die plan.
  (a) col_h9_r1 frame_int_i1 broadcast: every col_h9 fi_*_r0r1 lane fixed_cycles +1 (one depth per crossing, C4)
  (c) t73 leafdn_i0 -> vs: lane dn_s_7N_L3 fixed_cycles +1
  (c) t73 vs <-> vq: one 'u'-class internal station on ot_s81sl_leaf__t73 (kit_istations --apply -> CS_U_D 1)
Usage: apply_slice4.py BASE_PLAN EVENT_JSON OUT_PLAN ; then tools/die_plan/gen.py latency OUT_PLAN --inplace --out DIR"""
import json, sys
base, ev, out = sys.argv[1:4]
p = json.load(open(base)); d = json.load(open(ev))['pin_cycle_deltas']
lanes = p['lanes']; it = lanes.items() if isinstance(lanes, dict) else [(l['id'], l) for l in lanes]
hit = 0
for n, l in it:
    if n in d:
        l['fixed_cycles'] += d[n]; hit += 1
assert hit == len(d), (hit, len(d))
t = p['partition_types']['ot_s81sl_leaf__t73']['internal_stations']
assert not any(s['launch'].startswith('core:u_lf.u_vs.u') for s in t)
a, b = [579.03, 470.0], [924.546, 150.0]
t.append(dict(conn='core:u_lf.u_vs.u|core:u_lf.u_vq', from_um=a, to_um=b, bits=3 + 256 + 2 + 8 + 2,
              regs_um=[[round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)]], launch='core:u_lf.u_vs.u',
              capture='u_lf.u_vq.u',
              note='S81-ARCH-RTL-2 11-11 COORD slice-4 (c) t73 vs<->vq pin cycle: u/um stream (u_v/u_i/u, um_v/um_q/um_b/um_i) 1 station = CS_U_D 1, +1 cycle on the vs->vq interface (leaf bench t73u1 PASS, MUT_UV FAIL)'))
json.dump(p, open(out, 'w'), indent=1)
print('slice4', hit, 'lanes +1, t73 u station 1 ->', out)
