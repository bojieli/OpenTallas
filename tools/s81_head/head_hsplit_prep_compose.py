#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: pre-compose cleanup of the RAW split plan (new file only).
The split delta drops hd_host's landing_contract but keeps its generated landing pins as plain buses on host_w
(some at E positions) and its forwarded-clock edge clocks; a fresh compose owns those, so remove them (the same
records clear_generated_landing_infra would remove had the contract been kept). Also split clock.sink_sites_um
by x (E shifted -648) and drop the HEAD post-compose stage keys + old lec_hints (re-derived for the new types)."""
import json, sys
SPLIT_X = 648.0
split_path, base_path, out = sys.argv[1:4]
p = json.load(open(split_path)); base = json.load(open(base_path))
old = base['partition_types']['hd_host']['clock']['landing_contract']
names = {q['name'] for q in old['pins']}
rep = {}
for tn in ('hd_host_w', 'hd_host_e'):
    t = p['partition_types'][tn]; ck = t['clock']; east = tn.endswith('_e')
    nb = len(t['buses']); t['buses'] = [b for b in t['buses'] if b['name'] not in names]
    ne = len(ck.get('edge_clocks', [])); ck['edge_clocks'] = [e for e in ck.get('edge_clocks', []) if e['port'] not in names]
    ss = ck.get('sink_sites_um', [])
    ck['sink_sites_um'] = [[round(s[0] - SPLIT_X, 6)] + s[1:] if east else s for s in ss if (s[0] >= SPLIT_X) == east]
    d = [k for k in list(ck) if k.startswith('landing_') and k != 'landing_export_form']
    for k in d: ck.pop(k)
    for k in ('lec_hints',):
        if t.pop(k, None) is not None: d.append(k)
    rep[tn] = dict(buses_removed=nb - len(t['buses']), edge_clocks_removed=ne - len(ck['edge_clocks']),
                   sink_sites=len(ck['sink_sites_um']), dropped=d, buses=[b['name'] for b in t['buses']])
# E START capture beside the die START origin stage b1745 (88 um), same y as W's capture; W keeps its l48uo site
p['partition_types']['hd_host_e']['clock']['start_capture_um'] = [10.8, 552.992]
json.dump(p, open(out, 'w'), indent=1)
print(json.dumps(rep))
