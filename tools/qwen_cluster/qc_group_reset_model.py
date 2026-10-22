#!/usr/bin/env python3
"""MODEL ONLY: assign explicit serial reset channels to same-clock group16s.

Preserves every two-capture graph edge; package placement and physical clock
equivalence are deliberately unqualified. Never consumes a production source.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('model', help='generated MODEL directory')
a = p.parse_args()
out = Path(a.model)
meta = json.loads((out / 'model_sources.json').read_text())
assert meta['model_only'] and meta['physical_reset_ledger']
path = out / 'safe_fabric_model.sv'
source = path.read_text()
before = hashlib.sha256(source.encode()).hexdigest()
channels = collections.defaultdict(list)
chains = []
pattern = re.compile(r'cb16_model_reset\s+#\(\.EDGES\((\d+)(\+\(MUT==9\?1:0\))?\)\)\s+(\w+)\s*\(\s*\.ck\((\w+)\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\);')

def replace(m):
    edges, mutant, inst, ck, d, q = m.groups()
    edges = int(edges)
    assert edges % 2 == 0
    count = edges // 2
    wire = 'group_model_' + inst
    lines = [f'wire [{count}:0] {wire}; assign {wire}[0]={d};']
    for stage in range(count):
        channels[ck].append(dict(chain=inst, stage=stage,
                                 d=f'{wire}[{stage}]', q=f'{wire}[{stage+1}]'))
    if mutant:
        lines += [f'generate if(MUT==9) begin:g_mut_{inst}',
                  f'reg late; always @(posedge {ck}) late<={wire}[{count}];',
                  f'assign {q}=late; end else begin:g_normal_{inst}',
                  f'assign {q}={wire}[{count}]; end endgenerate']
    else:
        lines.append(f'assign {q}={wire}[{count}];')
    chains.append(dict(inst=inst, ck=ck, source=d, sink=q,
                       two_capture_channels=count, offset_mutant=bool(mutant)))
    return '\n'.join(lines)

source, matches = pattern.subn(replace, source)
assert matches and 'cb16_model_reset #' not in source
packages = []
lines = []
for ck, items in sorted(channels.items()):
    for start in range(0, len(items), 16):
        active = items[start:start+16]
        name = f'group_model_{ck}_{start//16}'
        lines += [f'wire[15:0] {name}_d,{name}_q;',
                  f'qfd_c_reset_group16_safe {name}(.ck({ck}),.d({name}_d),.q({name}_q));']
        assignments = []
        for i in range(16):
            if i < len(active):
                v = active[i]
                lines += [f'assign {name}_d[{i}]={v["d"]};',
                          f'assign {v["q"]}={name}_q[{i}];']
                assignments.append(dict(channel=i, **v))
            else:
                lines.append(f"assign {name}_d[{i}]=1'b0;")
        packages.append(dict(inst=name, ck=ck, active_channels=len(active),
                             assignments=assignments))
pos = source.rfind('endmodule')
source = source[:pos] + '\n'.join(lines) + '\n' + source[pos:]
path.write_text(source)
assert 2*sum(map(len, channels.values())) == meta['reset_ff_total']
receipt = dict(schema='opentallas.cb16.grouped_reset_model.v1', model_only=True,
               release_ready=False, input_fabric_sha256=before,
               output_fabric_sha256=hashlib.sha256(source.encode()).hexdigest(),
               serial_flops=meta['reset_ff_total'], package_flops=32*len(packages),
               inactive_flops=32*len(packages)-meta['reset_ff_total'],
               clock_channels={k:len(v) for k,v in sorted(channels.items())},
               packages=packages, chains=chains,
               scope='Exact MODEL graph assignment by logical clock net only. '
                     'No package placement, native clock phase, PG, fanout or '
                     '315um routing qualification; no minimum package claim '
                     'under physical constraints. MUT9 adds one deliberate '
                     'diagnostic capture FF outside the normal hardware count.')
(out/'grouped_reset_assignments.json').write_text(json.dumps(receipt,indent=1)+'\n')
meta['generated']['safe_fabric_model.sv'] = receipt['output_fabric_sha256']
meta['grouped_reset_package_flops'] = receipt['package_flops']
meta['grouped_reset_packages'] = len(packages)
(out/'model_sources.json').write_text(json.dumps(meta,indent=1)+'\n')
print('GROUPED_RESET_MODEL', matches, 'chains', len(packages), 'packages',
      receipt['package_flops'], 'FF', receipt['inactive_flops'], 'inactiveFF')
