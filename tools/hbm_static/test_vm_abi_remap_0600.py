#!/usr/bin/env python3
"""Compiler-only semantic migration proof native-compact-0253 -> native-retire-0600; not a native VM tile qualification."""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hbm_vm_static_calendar import layout, compile_schedule, ROOT
from vm_abi_remap_0253 import packed
from vm_abi_remap_0600 import migrate

abi = json.loads((ROOT / 'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
new = copy.deepcopy(abi)
shape = dict(SW=dict(NC=2, CW=2, RG=5, WG=2), SE=dict(NC=0, CW=1, RG=4, WG=2),
             NW=dict(NC=0, CW=1, RG=5, WG=3), NE=dict(NC=0, CW=1, RG=4, WG=2))
for q, p in shape.items():
    new['quadrants'][q]['params'].update(p)
    for port in new['quadrants'][q]['ports']:
        n = port['name']
        if n in ('client_seq', 'response_seq'): port['bits'] = 2 * (p['NC'] + 1)
        elif n == 'response_enable': port['bits'] = p['NC'] + 1
        elif n == 'bank_client': port['bits'] = 8 * p['CW']
        elif n == 'hub_ring_client': port['bits'] = 2 * p['CW']
# SW: ARGMAX client0, IDX client2 -> 1, replay 3 -> 2
sw = dict(base=5, loops=2, cycles=[dict(client_seq=packed([1, 0, 3, 2], 2), response_enable=0b1101,
          response_seq=packed([2, 0, 1, 3], 2), bank_enable=0b11110111, bank_client=packed([0, 2, 3, 1, 2, 0, 3, 2], 2),
          hub_ring_enable=3, hub_ring_client=packed([3, 2], 2))])
v = migrate(sw, 'SW')['cycles'][0]
assert v['client_seq'] == packed([1, 3, 2], 2) and v['response_enable'] == 0b111
assert v['response_seq'] == packed([2, 1, 3], 2)
assert v['bank_client'] == packed([0, 1, 2, 0, 1, 0, 2, 1], 2)
assert v['hub_ring_client'] == packed([2, 1], 2)
compile_schedule(layout(new, 'SW', True), migrate(sw, 'SW'))
# NW: replay only
nw = dict(cycles=[dict(client_seq=packed([0, 0, 0, 2], 2), response_enable=0b1000, response_seq=packed([0, 0, 0, 1], 2),
          bank_enable=255, bank_client=packed([3] * 8, 2), hub_ring_enable=1, hub_ring_client=packed([3, 1], 2))])
v = migrate(nw, 'NW')['cycles'][0]
assert (v['client_seq'], v['response_enable'], v['response_seq'], v['bank_client'], v['hub_ring_client']) == (2, 1, 1, 0, 0)
compile_schedule(layout(new, 'NW', True), migrate(nw, 'NW'))
# NE: COLL read group 4 -> 3, packet 5 -> 4; write codes >= 3 decrement
ne = dict(cycles=[dict(rslot_v=0b11110111, rslot=packed([0, 1, 2, 3, 4, 5, 4, 1], 3),
          wslot_v=0b11111011, wslot=packed([0, 1, 2, 3, 4, 5, 6, 7], 3))])
v = migrate(ne, 'NE')['cycles'][0]
assert v['rslot'] == packed([0, 1, 2, 0, 3, 4, 3, 1], 3)
assert v['wslot'] == packed([0, 1, 0, 2, 3, 4, 5, 6], 3)
compile_schedule(layout(new, 'NE', True), migrate(ne, 'NE'))
# Negatives: every retired resource referenced while active is rejected
for q, field, value, extra in [('SW', 'client_seq', packed([0, 1, 0, 0], 2), {}),
                               ('SW', 'bank_client', packed([1] + [0] * 7, 2), dict(bank_enable=1)),
                               ('NW', 'response_enable', 0b0001, {}),
                               ('NW', 'bank_client', packed([2] + [3] * 7, 2), dict(bank_enable=1)),
                               ('NE', 'rslot', packed([3] + [0] * 7, 3), dict(rslot_v=1)),
                               ('NE', 'wslot', packed([2] + [0] * 7, 3), dict(wslot_v=1))]:
    bad = dict(cycles=[dict({field: value}, **extra)])
    try:
        migrate(bad, q)
    except ValueError:
        continue
    raise AssertionError(f'retired resource silently retained: {q} {field}')
print('VM_ABI_RETIRE_0600 PASS SW client2->1/replay3->2, NW replay-only, NE COLL rg4->3/packet5->4/write>=3-1; '
      '6 retired-resource negatives rejected; W187 universal layout compiles')
