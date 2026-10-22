#!/usr/bin/env python3
"""Run the original full protocol against the exact route candidate.

Only the module/ROM names and ROM initialization INSTANCE are adapted for
simulation. The physical source, sequential declarations and edges are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

p = argparse.ArgumentParser(__doc__)
p.add_argument('out')
p.add_argument('variant', choices=['qfd_sys_face_n32ob', 'qfd_sys_face_n32obo'])
p.add_argument('--mutant', action='store_true')
a = p.parse_args()
here = Path(__file__).resolve().parent
root = here.parents[2]
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=True)
fixture = out / 'fixture'
shutil.copytree(here / 'protocol_fixture', fixture, dirs_exist_ok=True)
kit = root / 'physical/ref_tile' / a.variant
spec = json.loads((kit / 'spec.json').read_text())
source = root / spec['sources'][0]
text = source.read_text()
oldname = spec['top']
assert text.count('module ' + oldname + '(') == 1
text = text.replace('module ' + oldname + '(', 'module qfd_sys_face_n32_opt(', 1)
roms = re.findall(r'\b(ot_rom_4096x72_m8(?:_escape_p192)?)\s+(\\u_ot_pr_core\.u_rom\s+)\(', text)
assert len(roms) == 1, roms
rom = roms[0][0]
text = text.replace(rom + ' ' + roms[0][1] + '(', 'ot_rom_4096x72_m8 #(.INSTANCE("sys_face_cfg")) ' + roms[0][1] + '(', 1)
reference = (here / 'protocol_fixture/protocol_bounded.sv').read_text()
assert text == reference, 'route candidate differs from source-pinned full protocol fixture'
helpers = root / 'rtl/qwen_split/qfd_sysface32_helpers.sv'
assert helpers.read_bytes() == (fixture / 'protocol_bounded_helpers.sv').read_bytes()
if a.mutant:
    actual = 'u_7159(.C(n_2),.D(n_589),.Q(n_8985))'
    assert text.count(actual) == 1
    text = text.replace(actual, actual.replace('.C(n_2)', '.C(~n_2)'), 1)
(fixture / 'protocol_bounded.sv').write_text(text)
(out / 'binding.json').write_text(json.dumps({
    'variant': a.variant,
    'source': str(source.relative_to(root)),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'simulation_sha256': hashlib.sha256(text.encode()).hexdigest(),
    'adaptations': ['module name', 'equivalent ROM functional model and INSTANCE'],
    'actual_producer_clock_mutant': a.mutant,
    'comparison': 'exact complete source equality after the listed simulation adaptations',
}, indent=2) + '\n')
r = subprocess.run(['bash', str(here / 'run_protocol_base.sh'), str(out / 'run'), str(fixture), '0'])
if a.mutant:
    log = out / 'run/run.log'
    assert log.is_file() and 'SYSFACE32_WRAPPER_MISMATCH' in log.read_text()
    assert r.returncode != 0
    print('SYSFACE_ROUTE_ACTUAL_PRODUCER_CLOCK_MUTANT_CAUGHT', flush=True)
    raise SystemExit(1)
assert r.returncode == 0, r.returncode
print('SYSFACE_ROUTE_EXACT_PASS ' + a.variant, flush=True)
