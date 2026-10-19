"""Record complete native proof limits, without relabeling whole-block fanout."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re

R = Path.cwd()
N = R / 'native'
A = R / 'results/arch/qw_d2d_status_source_1019'
rows = list(csv.DictReader((N/'all_roots_full.tsv').open(), delimiter='\t'))
cells = list(csv.DictReader((N/'cells.tsv').open(), delimiter='\t'))
for row in rows:
    row['loads'] = int(row['loads'])
    sinks = row['examples'].split(',') if row['examples'] else []
    assert len(sinks) == row['loads'] == len(set(sinks)), row['root']
helpers = [r for r in rows if 'g_slot_decode' in r['root']]
assert len(helpers) == 16
assert sorted(r['loads'] for r in helpers) == [31] + [32]*15
operands = [r for r in rows if 'g_slot_decode' in r['examples']]
operand_rows = []
for row in operands:
    pins = [p for p in row['examples'].split(',') if 'g_slot_decode' in p]
    assert len(pins) == 16, (row['root'], len(pins))
    assert row['loads'] <= 32
    operand_rows.append(row)
assert len(operand_rows) == 2
softarea = sum(float(c['area_um2']) for c in cells if c['kind'] != 'macro')
ff = sum(c['kind'] == 'ff' for c in cells)
assert ff == 11555
unsafe = [r for r in rows if r['loads'] > 32]
summary = dict(scope='partial source fanout closure only; whole-block HOLD',
    source_sha256={str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted((R/'rtl/qwen_sys/d2d_static_20261015').glob('*6s.sv'))},
    odb_sha256=hashlib.sha256((N/'results/asap7/sf6s_source_census/base/1_synth.odb').read_bytes()).hexdigest(),
    roots=len(rows), cells=len(cells), ff=ff, macros=sum(c['kind']=='macro' for c in cells),
    softarea_um2=round(softarea, 8), sf6u_softarea_um2=5911.86924,
    softarea_delta_vs_sf6u_um2=round(softarea-5911.86924,8),
    ff_delta_vs_sf6u=0, added_edges=0,
    private_status_helpers=helpers, private_status_operand_roots=operand_rows,
    max_loads_by_role={k:max(r['loads'] for r in rows if r['kind']==k)
                       for k in sorted(set(r['kind'] for r in rows))},
    unsafe_roots=len(unsafe), unsafe_by_role=dict(collections.Counter(r['kind'] for r in unsafe)),
    unsafe=unsafe,
    inherited_unsafe_roots_previous_count=224,
    unsafe_count_delta_is_not_per_cone_closure_certificate=True,
    ff_hold_setup_clock_pg_reach_parent_fit_qualified=False)
(A/'native_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('unsafe','private_status_helpers','private_status_operand_roots')}))
