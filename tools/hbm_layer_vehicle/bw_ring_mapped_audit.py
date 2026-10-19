#!/usr/bin/env python3
"""Audit retained K state, pin identities and buffer-collapsed local loads."""
import hashlib
import json
from pathlib import Path
import re
import sys

base = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(base/'src/tools'))
import textbook_lint as T

netlist = base/'routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_svc_pc_ctrl_leaf_cfg_safe_asap7_ref_gate/base/1_2_yosys.v'
g, top = T.flatten(T.parse_verilog(netlist.read_text()), 'ot_hbm_svc_pc_ctrl_leaf_cfg_safe')
a = T.build(g, None)
clks, _ = T.clock_nets(g, a)


def origin(x):
    """Return a net and inversion parity through only real BUF/INV cells."""
    invert = 0
    seen = set()
    while x not in seen:
        seen.add(x)
        ci, _ = a['driver'].get(x, (-1, ''))
        if ci < 0 or a['kind'][ci] != 'buf':
            return [g.net_name[x], invert]
        t, _, pins = g.cells[ci]
        invert ^= int('INV' in t.upper() or 'NOT' in t.upper())
        inputs = [v for p, vs in pins.items() if a['pin_dir'][ci].get(p) == 'in' for v in vs]
        assert len(inputs) == 1
        x = inputs[0]
    raise AssertionError('buffer cycle')


rows = []
families = {'valid': [], 'ready': [], 'consumer_count': [], 'ring_count': [], 'kr_valid': []}
for ci, (t, name, pins) in enumerate(g.cells):
    if a['kind'][ci] != 'ff' or not any(s in name for s in ('.g_kreg.', '.g_krreg.')):
        continue
    family = None
    if '.kv_regions[' in name:
        family = 'valid'
    elif '.ready_seen_regions[' in name:
        family = 'ready'
    elif re.search(r'\.g_control\[\d+\]\.count_q\[', name):
        family = 'consumer_count'
    elif re.search(r'\.g_control\[\d+\]\.g_local\.count_q\[', name):
        family = 'ring_count'
    elif '.head_valid_regions[' in name:
        family = 'kr_valid'
    outputs = [x for p, xs in pins.items() if a['pin_dir'][ci].get(p) == 'out' for x in xs]
    loads = max([T.bufinv_fanout(g, a, x, clks)[0] for x in outputs] or [0])
    row = dict(cell=name, library=t, family=family, max_loads=loads,
               input_identity={p: [origin(x) for x in xs] for p, xs in pins.items() if a['pin_dir'][ci].get(p) == 'in'})
    rows.append(row)
    if family:
        families[family].append(row)

expected = dict(valid=22, ready=22, consumer_count=154, ring_count=66, kr_valid=18)
errors = []
for key, number in expected.items():
    if len(families[key]) != number:
        errors.append(f'{key}: expected {number}, actual {len(families[key])}')
    clocks = {json.dumps(r['input_identity'].get('CLK')) for r in families[key]}
    if len(clocks) != 1 or 'null' in clocks:
        errors.append(f'{key}: inconsistent clock identity')
for key in ('valid', 'ready', 'kr_valid'):
    ds = {json.dumps(r['input_identity'].get('D')) for r in families[key]}
    if len(ds) != 1 or 'null' in ds:
        errors.append(f'{key}: different source D pins')
shared_d_loads = {}
# The unkept architectural counter may legally merge into one retained
# copy. Audit the22 surviving captures per bit directly, without requiring
# a discarded RTL alias to remain a mapped register name.
for family in ('consumer_count', 'ring_count'):
    for bit in range(7 if family == 'consumer_count' else 3):
        group = [r for r in families[family] if f'count_q[{bit}]' in r['cell']]
        if len(group) != 22:
            errors.append(f'{family} bit{bit}: expected22 actual{len(group)}')
            continue
        for pin in ('D', 'CLK', 'RESETN', 'SETN'):
            identities = {json.dumps(r['input_identity'].get(pin)) for r in group}
            if len(identities) != 1:
                errors.append(f'{family} bit{bit}: different same-edge {pin} identity')
        d_identity = group[0]['input_identity'].get('D')
        if d_identity and len(d_identity) == 1:
            net = g.find(g.net_id[d_identity[0][0]])
            fanout = T.bufinv_fanout(g, a, net, clks)[0]
            shared_d_loads[f'{family}[{bit}]'] = fanout
            if fanout > 32:
                errors.append(f'{family} bit{bit}: shared D root has{fanout} loads')
for row in rows:
    if row['max_loads'] > 32:
        errors.append(f"{row['cell']}: {row['max_loads']} loads")

receipt = dict(schema='opentallas.bw_ring_mapped_audit.v1', verdict='PASS' if not errors else 'FAIL',
               netlist_sha256=hashlib.sha256(netlist.read_bytes()).hexdigest(),
               family_counts={k: len(v) for k, v in families.items()}, expected_counts=expected, shared_next_count_d_loads=shared_d_loads,
               max_k_register_loads=max([r['max_loads'] for r in rows] or [0]),
               scope='Retained K registers and capture D/clock identities only; global reset/comb roots and physical timing remain separate.',
               errors=errors, cells=rows)
(base/'ring_mapped_audit.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'cells'}))
raise SystemExit(bool(errors))
