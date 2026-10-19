#!/usr/bin/env python3
"""Check retained CALPIPE selector replicas in a post-synth Yosys JSON (fleet)."""
import argparse
import collections
import json

p = argparse.ArgumentParser()
p.add_argument('net_json')
p.add_argument('--nu', type=int, default=4)
a = p.parse_args()
modules = json.load(open(a.net_json))['modules']
cells = modules['qfd_dv_cmd_cal_mu']['cells']
selectors = {n: c for n, c in cells.items() if 'qfd_calpipe_selector' in c['type']}
print('SELECTOR_INSTANCES', len(selectors), 'PARAMOD_TYPES', len({c['type'] for c in selectors.values()}))
assert len(selectors) == 12 * a.nu
loads = collections.Counter()
for c in cells.values():
    for port, bits in c['connections'].items():
        if c.get('port_directions', {}).get(port) == 'input':
            loads.update(b for b in bits if isinstance(b, int))
maximum = 0
for name, c in sorted(selectors.items()):
    assert modules[c['type']].get('attributes', {}).get('keep_hierarchy')
    for port in ('sel', 'pending', 'bypass'):
        counts = [loads[b] for b in c['connections'][port] if isinstance(b, int)]
        maximum = max([maximum] + counts)
    print(name, 'sel loads', [loads[b] for b in c['connections']['sel']])
print('SELECTOR_MAX_LOAD', maximum)
assert maximum <= 32, maximum
print('CALPIPE_SELECTOR_INVENTORY_PASS')

for module, count, ports in (
    ('qfd_calpipe_readvalid', 16*a.nu, ('valid',)),
    ('qfd_calpipe_mask', 32, ('mask',)),
):
    copies = {n: c for n, c in cells.items() if module in c['type']}
    print(module, 'INSTANCES', len(copies), 'PARAMOD_TYPES', len({c['type'] for c in copies.values()}))
    assert len(copies) == count
    maxload = 0
    for c in copies.values():
        assert modules[c['type']].get('attributes', {}).get('keep_hierarchy')
        for port in ports:
            maxload = max([maxload] + [loads[b] for b in c['connections'][port] if isinstance(b, int)])
    print(module, 'MAX_LOAD', maxload)
    assert maxload <= 32, maxload
print('CALPIPE_CE_MASK_INVENTORY_PASS')
