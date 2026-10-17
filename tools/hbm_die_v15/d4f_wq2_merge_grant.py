#!/usr/bin/env python3
"""d4f grant: hfd_vms_wq2_merge leaf vmm_NW<b> beside each NW VM bank (H-SM 10-16; route hfd_vms_wq2_merge-m1-8500666e1
CLOSED, native PASS, main 035a607b4).  59.4 x 59.4, R0, 21.6 um east of vmb_NW<b>, vertically centred: W face (wq_m/done_m)
faces the bank wq1; N face wq2 from hb_quant_NW; E face wq1 from the NW SM writer side; S face clk/rst_n/flt.
Pins = the closed view's LEF.   d4f_wq2_merge_grant.py GRANTS PLAN_DIR"""
import json, sys
g, pd = sys.argv[1], sys.argv[2]
G = json.load(open(g)); P = json.load(open(pd + '/compact.P.json'))
names = {s['name'] for s in G['slots']}; L = 59.4; n = 0
for b in range(8):
    k = f'vmm_NW{b}'; v = P[f'vmb_NW{b}']
    s = dict(name=k, cell='hfd_vms_wq2_merge', kind='tile', parent='die', outline=dict(w=L, h=L),
             origin=dict(x=round(v['x'] + v['w'] + 21.6, 3), y=round(v['y'] + (v['h'] - L) / 2, 3), orient='R0'),
             view='physical/ref_tile/hfd_vms_wq2_merge/views/hfd_vms_wq2_merge', pin_status='MACRO_LEF_PINS',
             grant='d4f_wq2_merge_1016', rtl_owner='H-SM: hfd_vms_wq2_merge (NW q2 bank write merge)',
             native=dict(launch=181.3, capture=152.6, R=96.1, spread=19.5, closed='TT +335.22 / FF +21.14 / DRC 0', main='035a607b4'),
             notes=f'beside vmb_NW{b} (east, 21.6 um channel); W face to the bank wq1/wq_done1')
    if k in names:
        G['slots'] = [x for x in G['slots'] if x['name'] != k]
    G['slots'].append(s); n += 1
json.dump(G, open(g, 'w'), indent=1); open(g, 'a').write('\n'); print('vmm slots', n)
