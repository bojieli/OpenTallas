#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: re-point the START-tree raw-reset uses (plan landing_network.start_tree.uses and sidecar
count_aligned.start_pins.reset_inputs) from host.rst_start_raw_0..3 to the host_e exports chosen in raw_exports.json."""
import json, sys
d = sys.argv[1]; rx = json.load(open(sys.argv[2]))
p = json.load(open(d + '/source_plan.json')); s = json.load(open(d + '/source_sidecar.json'))
ports = sorted({(r['new']['part'], r['new']['port']) for r in rx['stages']})
st = p['clock']['landing_network']['start_tree']
old = [u for u in st['uses'] if u['part'] == 'host']
st['uses'] = [u for u in st['uses'] if u['part'] != 'host'] + [dict(part=pn, pin=pt, net=f'wr_{pn}__{pt}') for pn, pt in ports]
ri = s['count_aligned']['start_pins']['reset_inputs']
oldr = [r for r in ri if r.get('src_part') in ('host', 'host_w', 'host_e')]
s['count_aligned']['start_pins']['reset_inputs'] = [r for r in ri if r.get('src_part') not in ('host', 'host_w', 'host_e')] + \
    [dict(src_part=pn, src_port=pt, net=f'wr_{pn}__{pt}') for pn, pt in ports]
json.dump(p, open(d + '/source_plan.json', 'w'), indent=1); json.dump(s, open(d + '/source_sidecar.json', 'w'), indent=1)
print('uses', len(old), '->', len(ports), ports, '| reset_inputs', len(oldr), '->', len(ports))
