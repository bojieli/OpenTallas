#!/usr/bin/env python3
"""KV-BIND 10-24: plan rewires for the kv44 re-bind = bind/plan_rewires_v34.json (KV-P4 classes, unchanged) + two classes
the TOK-QK boot findings require, applied by tools/die_plan/bind.py asbuilt.rewires (no post-bind edit):

  kvpc_hbm_reset (TOK-QK KV-R1 = COORD ruling A, was the post-bind tool kv_kvpc_hbm_reset.py): every kvpc_<Q>_<k>.rst_n
      (128 instances: the PC controller / HBM calendar / embedding endpoint / slice boot-window face es_merge) loses
      host.die_rst_n and takes host.hbm_rst_n -- the same delivered (pipelined, synchronous lane) HBM reset its own
      .hrst_n already reads; bit map identity, stages = its hrst_n edge ('beside').  The HOST releases die_rst_n only after
      every slice's HBM cold-boot check is done & ok, and that check's word passes es_merge, so die_rst_n on kvpc
      deadlocks the boot by construction (KV-TOK flat pcpart sub-bench).  u_slg (slice group) keeps die_rst_n.
  d2d_boot_order (TOK-QK KV-R2 = BO1, main a2757edd53 opt-in source, Codex bound candidate rewire): d2d_kv.host_boot_begin
      loses host.boot_go and takes host.d2d_boot_begin (output of the host variant qkd_host_root_admission_obsx_bo1,
      D2D_BOOT_ORDER=1: the D2D boot epoch waits for the accepted programme); same lane, stages = the boot_go edge.

    mk_rewires_kv44.py ../plan_rewires_v34.json OUT.json
"""
import json, sys
src, out = sys.argv[1:3]
d = json.load(open(src))
kv = []
for q in ('EN', 'ES', 'WN', 'WS'):
    for k in range(32):
        i = f'kvpc_{q}_{k}'
        kv.append((dict(s='host', sp='die_rst_n', d=i, dp='rst_n', bits=1),
                   dict(s='host', sp='hbm_rst_n', d=i, dp='rst_n', bits=1, bit_map='identity',
                        beside=dict(s='host', sp='hbm_rst_n', d=i, dp='hrst_n', bits=1))))
d['classes']['kvpc_hbm_reset'] = dict(removed=[r for r, _ in kv], added=[a for _, a in kv])
bo = dict(s='host', sp='boot_go', d='d2d_kv', dp='host_boot_begin', bits=1)
d['classes']['d2d_boot_order'] = dict(removed=[bo], added=[dict(s='host', sp='d2d_boot_begin', d='d2d_kv', dp='host_boot_begin',
                                                                  bits=1, bit_map='identity', beside=bo)])
d['note'] = d.get('note', '') + '\nKV-BIND 10-24 (mk_rewires_kv44.py): + kvpc_hbm_reset (KV-R1) + d2d_boot_order (KV-R2).'
d.setdefault('summary', {}).update(kvpc_hbm_reset=dict(removed=128, added=128), d2d_boot_order=dict(removed=1, added=1))
json.dump(d, open(out, 'w'), indent=1)
print('wrote', out)
