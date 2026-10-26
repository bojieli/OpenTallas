#!/usr/bin/env python3
"""d4f calendar_<q> outline = actual candidate LEF width 241.92 (Codex H-DIE 4eef8a534: routed candidate wider than the
historical 220.32).  The E (hub) face keeps its 21.6-um channel to vmh_<q>: origin moves west by the width growth.
Native OPEN (no source/clock-ABI proof inherited).     d4f_calendar_grant.py GRANTS"""
import json, sys
p = sys.argv[1]; G = json.load(open(p)); W1 = 241.92; n = 0
for s in G['slots']:
    if s['name'].startswith('calendar_') and abs(s['outline']['w'] - W1) > 1e-6:
        dw = W1 - s['outline']['w']; s['outline']['w'] = W1; s['origin']['x'] = round(s['origin']['x'] - dw, 3)
        s['calendar_geometry_2009'] = dict(actual_lef='physical/ref_tile/hv16_vm_cal_f20_ww/views/hfd_hgi_vm_calendar_f20/hfd_hgi_vm_calendar_f20.lef',
                                           previous_w_um=round(W1 - dw, 3), native='OPEN', moved_west_um=round(dw, 3)); n += 1
json.dump(G, open(p, 'w'), indent=1); open(p, 'a').write('\n'); print('calendars', n)
