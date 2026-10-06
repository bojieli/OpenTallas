#!/usr/bin/env python3
"""Bind retained mapped gates, actual boundary nets and four root loads.

Consumes completed synthesis/affinity objects; never runs ABC or a golden gate.
The generated region memberships are for the accepted finite parent geometry.
An actual cut deficit is a failed physical admission, not a constraint waiver.
"""
import hashlib
import json
import subprocess
import sys
from array import array
from collections import Counter
from pathlib import Path

import run_abi3_physical as D

loads, affinity, out = map(Path, sys.argv[1:])
assert not out.exists()
source = json.loads((loads / 'summary.json').read_text())
binding = json.loads((affinity / 'summary.json').read_text())
assert source['mapped_sha256'] == binding['source_mapped_sha256']
assert binding['all_comb_dependencies_resolved']
out.mkdir(parents=True)
extract = '''import gzip,json,re
from pathlib import Path
cells={}
for p in Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*_RVT_SS_*.lib*'):
 text=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
 for m in re.finditer(r'cell\\s*\\(\\s*(\\w+)\\s*\\)\\s*\\{(.*?)(?=\\n\\s*cell\\s*\\(|\\Z)',text,re.S):
  area=re.search(r'\\barea\\s*:\\s*([0-9.eE+-]+)',m[2]);assert area,m[1]
  cells[m[1]]=float(area[1])
Path('/work/library_areas_um2.json').write_text(json.dumps(cells)+'\\n')
'''
(out / 'extract_areas.py').write_text(extract)
subprocess.run(['docker', 'run', '--rm', '-v', f'{out}:/work', D.ORFS_IMAGE,
                'bash', '-lc', "python3 /work/extract_areas.py; rc=$?; chmod -R a+rwX /work; exit $rc"], check=True)
areas = json.loads((out / 'library_areas_um2.json').read_text())
caps = json.loads((loads / 'library_input_caps_ff.json').read_text())
modules = json.loads((loads / 'mapped.json').read_text())['modules']
top = next(name for name in modules if name.startswith('ot_gpu_coll_item9_context32'))
net = modules[top]
regions = {'hb_coll': 32, **{f'caller_{i}': i for i in range(32)}}
names = {}
region_area = Counter()
with (affinity / 'actual_cell_affinity.jsonl').open() as f:
 for line in f:
  c = json.loads(line)
  assert c['instance'] not in names
  names[c['instance']] = regions[c['allocation']]
  region_area[c['allocation']] += areas[c['master']]
assert len(names) == binding['mapped_flops'] + binding['mapped_comb_cells']
maximum = max(b for c in net['cells'].values() for bits in c['connections'].values()
              for b in bits if isinstance(b, int))
members = array('Q', [0]) * (maximum + 1)
roots = {p: net['ports'][p]['bits'][0] for p in ('clk_sm', 'clk_link', 'clk_mem', 'clk_host')}
clock_loads = {corner: {p: dict(input_pins=0, capacitance_fF=0.) for p in roots} for corner in caps}
for name, cell in net['cells'].items():
 if cell['type'] == '$scopeinfo':
  assert not cell['connections']
  continue
 mask = 1 << names[name]
 for pin, bits in cell['connections'].items():
  for bit in bits:
   if isinstance(bit, int):
    members[bit] |= mask
    for root, root_bit in roots.items():
     if bit != root_bit:
      continue
     for corner, lib in caps.items():
      if pin in lib[cell['type']]:
       row = clock_loads[corner][root]
       row['input_pins'] += 1
       row['capacitance_fF'] += lib[cell['type']][pin]
# Real source/capture projections stay with their caller, never at a perimeter bank.
port_strides = dict(issue=1, issue_mode=1, issue_count=8, issue_va=4096,
                    caller_idle=1, caller_done=1, caller_vr=4096)
for port, row in net['ports'].items():
 stride = port_strides.get(port)
 for i, bit in enumerate(row['bits']):
  if isinstance(bit, int):
   region = i // stride if stride else 32
   assert region <= 32, (port, i, stride)
   members[bit] |= 1 << region
boxes = binding['local_allocations']
west = sum(1 << int(i) for i, box in boxes.items()
            if (box[0] + box[2]) / 2 < 10861.776)
east = ((1 << 33) - 1) ^ west
assert west.bit_count() == 16
clock_bits = set(roots.values())
crossing = [b for b, mask in enumerate(members)
            if mask & west and mask & east and b not in clock_bits]
per_region = {name: sum(bool(mask & (1 << idx)) and bool(mask & ~(1 << idx))
                       for bit, mask in enumerate(members) if bit not in clock_bits)
              for name, idx in regions.items()}
with (out / 'actual_region_cells.tsv').open('w') as f:
 for name, idx in names.items():
  f.write(f'{name}\t{idx}\n')
(out / 'actual_west_crossing_net_bits.json').write_text(json.dumps(crossing) + '\n')
summary = dict(source_mapped_sha256=source['mapped_sha256'],
 affinity_sha256=hashlib.sha256((affinity / 'summary.json').read_bytes()).hexdigest(),
 actual_region_cell_area_um2=dict(region_area),
 actual_total_cell_area_um2=sum(region_area.values()),
 actual_region_boundary_net_counts=per_region,
 actual_west16_cut_signal_nets=len(crossing),
 optimistic_four_layer_track_upper_before_other_claims=50594,
 actual_west_cut_deficit_before_other_claims=max(0, len(crossing)-50594),
 four_source_root_connected_library_loads=clock_loads,
 region_bboxes_um={**boxes, '32': binding['endpoint_allocation']},
 actual_cell_memberships=str(out / 'actual_region_cells.tsv'),
 actual_member_count=len(names), source_new_cycles=0,
 all_other_claim_corridors_reserved=False, wire_RC_and_CTS_measured=False,
 physical_admission=False, physical_qualified=False, adopted=False)
for corner in caps:
 assert clock_loads[corner]['clk_sm']['input_pins'] == source['corners'][corner]['clk_sm_connected_input_pins']
 assert abs(clock_loads[corner]['clk_sm']['capacitance_fF'] - source['corners'][corner]['clk_sm_total_connected_input_pin_load_fF']) < 1e-6
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
