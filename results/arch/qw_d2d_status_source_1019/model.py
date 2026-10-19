"""Read preserved SF6U netlist; assign complete source ownership groups."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'qw_d2d_safe6_1019/sf6u_mapped.v.gz'
text = gzip.open(SOURCE, 'rt').read()
pattern = re.compile(r'([\w$]+)\s+(\\\S+|[\w$]+)\s*\((.*?)\);', re.S)
cells = {n: (m, dict(re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)', a)))
         for m, n, a in pattern.findall(text)}
loads = collections.defaultdict(list)
for name, (master, pins) in cells.items():
    for pin, net in pins.items():
        if pin not in ('Y', 'Q', 'QN'):
            loads[net].append((name, pin))
pending, visited, sinks = ['_16598_'], set(), set()
while pending:
    net = pending.pop()
    if net in visited:
        continue
    visited.add(net)
    for name, pin in loads[net]:
        master, pins = cells[name]
        if re.match('(BUF|INV|HB)', master):
            pending.append(pins['Y'])
        else:
            sinks.add((name, pin))
assert len(sinks) == 511
groups = collections.defaultdict(list)
for name, pin in sorted(sinks):
    pending, visited, endpoints = [name], set(), set()
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        master, pins = cells[node]
        if master.startswith('DFF'):
            endpoints.add(node)
        else:
            pending.extend(n for n, _ in loads[pins.get('Y')])
    ownership = set()
    for endpoint in endpoints:
        match = re.search(r'u_st\.r\[(\d+)\]', endpoint)
        if match:
            ownership.add('r_slice_%02d' % (int(match[1]) // 7))
            continue
        match = re.search(r'u_st\.tx_payload\[(\d+)\]', endpoint)
        if match:
            ownership.add('payload_%03d' % int(match[1]))
            continue
        ownership.add(endpoint.split('u_st.')[1].split('$')[0])
    assert len(ownership) == 1, (name, ownership)
    groups[next(iter(ownership))].append(name + '/' + pin)
totals, owners = [0] * 16, {}
for group in sorted(groups, key=lambda x: (-len(groups[x]), x)):
    owner = min(range(16), key=lambda x: (totals[x], x))
    owners[group] = owner
    totals[owner] += len(groups[group])
assert max(totals) <= 32, totals
record = dict(scope='SOURCE MODEL ONLY; actual new mapping required',
              baseline_netlist_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              equation='valid AND (port == 3\'d2)',
              implementation='16 kept useful AND instances; shared genuine port compare',
              source_r_slices=22, additional_ff=0, added_edges=0,
              additional_boolean_cells_minimum=15,
              native_reference_area_delta_minimum_um2=1.3122,
              area_is_upper_bound=False,
              immediate_operand_demands_model=[25,20],
              unchanged_unsafe_roots_not_covered_by_this_step=223,
              baseline_sink_count=511, model_owner_loads=totals,
              owners=owners, baseline_groups=dict(groups))
(HERE / 'source_model.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('owners','baseline_groups')}))
