#!/usr/bin/env python3
"""Independent emitted-LEF/RTL/JSON checks and causal geometry mutants (fleet)."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from build_s81_sc2_prototype_1019 import NEW, OLD, PACKET, ROOT, build

out = Path(sys.argv[1])
build(out)
model = json.loads((PACKET / 'access_model/model.json').read_text())
data = json.loads((PACKET / 'access_model/input.json').read_text())
sheet = json.loads((out / (NEW + '.json')).read_text())
lef = (out / (NEW + '.lef')).read_text()
blocks = {}
for name, body in re.findall(r'^  PIN (\S+)\n(.*?)^  END \1$', lef, re.M | re.S):
    blocks[name] = [list(map(float, r.split())) for r in re.findall(r'RECT ([^;]+);', body)]
assert len(blocks) == 439
for p in model['paths']:
    x, y = p['terminal_nm']
    expected = [[(x-12)/1000, (y-12)/1000, (x+12)/1000, (y+12)/1000]]
    assert blocks[p['pin']] == expected, p['pin']
for net in ('VDD', 'VSS'):
    expected = [[v/1000 for v in p['rect_nm']] for p in model['pg_rectangles'] if p['net'] == net]
    assert blocks[net] == expected, net
assert 'SYMMETRY X Y ;' in lef and 'R90' not in lef
assert 'SIZE 216.840 BY 43.752 ;' in lef
obs = lef.split('  OBS\n')[1].split('  END\n')[0]
parsed_obs = []
for layer, values in re.findall(r'LAYER (\w+) ;\s+RECT ([^;]+);', obs):
    parsed_obs.append(dict(layer=layer, rect_nm=[round(float(v)*1000) for v in values.split()]))
assert parsed_obs == model['proposed_obstruction_rectangles']
assert sheet['access_paths'] == model['paths']
assert sheet['obstruction_rectangles'] == model['proposed_obstruction_rectangles']
assert sheet['timing_roles']['ff_min_hold']['added_minimum_lead_delay_ps'] == 0
assert not list(out.glob('*.lib'))
for suffix in ('.v', '_bb.v'):
    old = (PACKET / 'sc2_prototype/source' / (OLD + suffix)).read_bytes()
    new = (out / (NEW + suffix)).read_bytes()
    assert new.replace(('module ' + NEW + ' (').encode(), ('module ' + OLD + ' (').encode()) == old
print('SC2_EMITTED_CONSISTENCY_PASS signal_pins=437 pg=77 functional_and_blackbox_rename_only=1 roles=4 liberty=NONE', flush=True)
# A changed frozen source must be refused before generating any replacement view.
source_path = PACKET / 'sc2_prototype/source' / (OLD + '.v')
original = source_path.read_bytes()
try:
    source_path.write_bytes(original + b'\n// foreign source\n')
    try:
        build(out)
    except AssertionError:
        print('SC2_FOREIGN_SOURCE_REJECT_PASS', flush=True)
    else:
        raise RuntimeError('foreign source accepted')
finally:
    source_path.write_bytes(original)
# Re-run the original constructive geometry and its two causal mutations.
planner = (ROOT / 'tools/mem_compiler/model_port_access_channels_1019.py').read_text()
cp = subprocess.run([sys.executable, str(ROOT / 'tools/mem_compiler/check_port_access_model_1019.py'), planner, json.dumps(data)], capture_output=True, text=True)
(out / 'geometry_positive.json').write_text(cp.stdout)
(out / 'geometry_witness.log').write_text(cp.stderr)
print(cp.stderr, end='', flush=True)
assert cp.returncode == 0
assert 'MUTANT_UNREVERSED_COLUMNS_FAIL' in cp.stderr
assert 'MUTANT_MISSING_SOURCE_VIA_FAIL' in cp.stderr
print('SC2_GEOMETRY_AND_MUTANTS_PASS', flush=True)
