#!/usr/bin/env python3
"""d4f sfucore_<q> grant v2 (H-DIE 10-16, H-SU k8 kit claude/hsu-corekit-0700 2191c672a): the hard lane child ot_su12_sfu has
PG + pins on M6, so the core is a cluster routed M2-M7 (as k7): layer_cap / signal_max_layer / pg_layer M7, die straps M8
(same layer contract as the SM slots).  Hardened top = ot_hgi_sfu_core_split2 (store partition in sfus_<q>, E side).
Outline 950.4 x 3132 and the N-face clock entry (clk 380.7-382.86) unchanged.   d4f_sfucore_grant.py GRANTS"""
import json, sys
p = sys.argv[1]; G = json.load(open(p)); n = 0
for s in G['slots']:
    if s['name'].startswith('sfucore_'):
        s.update(cell='ot_hgi_sfu_core_split2', layer_cap='M7', signal_max_layer='M7', pg_layer='M7', strap_layer='M8',
                 kind='cluster', version=2, grant='d4f_sfucore_k8_1016',
                 rtl_owner='H-SU: ot_hgi_sfu_core_split2 (k8 kit hbm_sfucore_k8, claude/hsu-corekit-0700 2191c672a)')
        s['clock_entry'] = dict(pin='clk', face='N', layer='M5', offset=381.78)
        n += 1
G.setdefault('d4f_sfucore_grant', []).append(dict(slots=n, kit='claude/hsu-corekit-0700 2191c672a', layers='M2-M7, die straps M8'))
json.dump(G, open(p, 'w'), indent=1); open(p, 'a').write('\n'); print('sfucore slots', n)
