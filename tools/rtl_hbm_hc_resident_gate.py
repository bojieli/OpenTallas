#!/usr/bin/env python3
"""Run the source-pinned four-row resident HC native-controller component."""
import hashlib
import json
import pathlib
import resource
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
out = root / 'out'
out.mkdir(exist_ok=False)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
sources = sorted([*root.glob('*.sv'), *root.glob('*.v')])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {p.name: sha(p) for p in sources}
(out / 'source.json').write_text(json.dumps(before, indent=2) + '\n')
command = ['verilator', '--binary', '--timing', '-j', '4', '-Wno-fatal',
           '--top-module', 'tb_hgi_hc_prefetch_direct_controller_static',
           '--Mdir', str(out / 'obj'), '-o', 'sim', *map(str, sources)]
with (out / 'compile.log').open('w') as log:
    result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
if result.returncode:
    raise SystemExit(f'compile failed: {out / "compile.log"}')
build = (out / 'compile.log').read_text()
for warning in ['UNOPTFLAT', 'LATCH', 'MULTIDRIVEN']:
    if f'%Warning-{warning}:' in build:
        raise SystemExit(f'forbidden structural warning {warning}')
cases = []
positive = [(period, phase, 3871) for phase in [0, 137, 773] for period in [1080, 1400]]
positive += [(period, 0, 12) for period in [1080, 1400]]
for period, phase, idle in positive:
    name = f'period{period}-phase{phase}-idle{idle}'
    cmd = [str(out / 'obj/sim'), '+IMAGE=../inputs/all24rows.hex',
           f'+PERIOD={period}', f'+PHASE_DELAY={phase}', f'+PRE_IDLE={idle}']
    with (out / f'{name}.log').open('w') as log:
        result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    text = (out / f'{name}.log').read_text()
    if result.returncode or 'HC_PREFETCH_RESIDENT_ACTUAL_CONTROLLER PASS' not in text:
        print(text, flush=True)
        raise SystemExit(f'positive failed: {name}, exit {result.returncode}')
    cases.append({'name': name, 'exit': result.returncode, 'log_sha256': sha(out / f'{name}.log')})
    print(f'HC_RESIDENT_POSITIVE PASS {name}', flush=True)
for flag, expected, success_exit in [
        ('STALE_EPOCH', 'HC_REGION_OWNER_MUTANT PASS', True),
        ('WRONGTAG', 'HC_REGION_OWNER_MUTANT PASS', True),
        ('PAYLOAD_MUTANT', 'actual aperture memory mismatch row0 bank5 position319', False)]:
    name = flag.lower()
    cmd = [str(out / 'obj/sim'), '+IMAGE=../inputs/all24rows.hex', '+PERIOD=1080', f'+{flag}']
    with (out / f'{name}.log').open('w') as log:
        result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    text = (out / f'{name}.log').read_text()
    if expected not in text or (result.returncode == 0) != success_exit:
        print(text, flush=True)
        raise SystemExit(f'mutant failed to reject: {name}, exit {result.returncode}')
    cases.append({'name': name, 'exit': result.returncode, 'expected': expected,
                  'log_sha256': sha(out / f'{name}.log')})
    print(f'HC_RESIDENT_MUTANT PASS {name}', flush=True)
after = {p.name: sha(p) for p in sources}
if before != after:
    raise SystemExit('source changed during gate')
receipt = {'status': 'PASS_NATIVE_CONTROLLER_COMPONENT_ONLY', 'source_sha256': after,
           'source_hashes_match': True, 'cases': cases, 'build_command': command,
           'structural_warnings': {'UNOPTFLAT': 0, 'LATCH': 0, 'MULTIDRIVEN': 0},
           'actual_SRAMs': 320, 'source_SRAMs': 128, 'regions_per_stack': 8,
           'released_rows_per_case': 24, 'readbacks_per_case': 61440,
           'periods': [1080, 1400], 'full_native_chip_qualified': False}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('HC_RESIDENT_GATE PASS source_hashes_match=1 positive_cases=8 mutants=3', flush=True)
