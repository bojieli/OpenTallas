#!/usr/bin/env python3
"""Compact source-ID candidate against the unchanged full53 stripe bench."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
OUT = ROOT / 'results/arch/s81_vm_area_1417/idstripe_proof.json'
SOURCES = ['tools/s81_vm/area_id_candidate.sv', 'tools/s81_vm/area_id_gate.py',
           'tools/s81_vm/area_stripe_bench.sv'] + [
               f'rtl/dsrom_sys/s81_ph/vm/{name}.sv' for name in
               ['dsfd_vm_static_wdispatch128', 'dsfd_vm_static_wstage128',
                'dsfd_vm_static_write_capture128']]


def check_lock():
    if json.loads(LOCK.read_text())['owner'] != 'codex':
        raise RuntimeError('coordinator ownership changed')


def run(cmd):
    check_lock()
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    check_lock()
    return result


def main():
    records = []
    with tempfile.TemporaryDirectory(prefix='s81-idstripe-') as temporary:
        for base in (0, 8, 16, 24):
            for variant, define in [('gold', None), ('selector', 'S81_AREA_MUT_SELECTOR'),
                                    ('data', 'S81_AREA_MUT_DATA')]:
                executable = str(Path(temporary) / f'b{base}_{variant}.vvp')
                cmd = ['iverilog', '-g2012', '-s', 'tb', f'-Ptb.BASE={base}', '-o', executable]
                if define:
                    cmd.append('-D' + define)
                cmd += [SOURCES[0], SOURCES[2]] + SOURCES[3:]
                build = run(cmd)
                if build.returncode:
                    raise RuntimeError(build.stdout + build.stderr)
                for mode in (range(5) if variant == 'gold' else (0,)):
                    result = run(['vvp', executable, f'+mode={mode}'])
                    passed = result.returncode == 0 and 'PASS full53sources' in result.stdout
                    rejected = result.returncode != 0 and 'FATAL:' in result.stdout
                    if not (passed if variant == 'gold' else rejected):
                        raise RuntimeError(f'{base}/{variant}/{mode}: {result.stdout}{result.stderr}')
                    records.append(dict(base=base, variant=variant, mode=mode,
                                        exit_code=result.returncode, stdout=result.stdout,
                                        stderr=result.stderr, gold_pass=passed,
                                        mutant_rejected=rejected))
                    print(f'BASE={base} variant={variant} mode={mode} exit={result.returncode}', flush=True)
    proof = dict(status='PASS_ISOLATED_COMPACT_ID_FULL53_QUARTER_NOT_PRODUCTION_OR_PHYSICALLY_QUALIFIED',
                 selector=dict(records=24, bits_per_record=7, total_bits=168,
                               encoding='valid bit6, sourceID bits5:0; source indices0..52'),
                 model='8 W16 data stripes + W26 metadata stripe + shared registered compact-ID selector',
                 timing='unchanged E0 source -> E1 select -> E2 stripe pin -> E3 mux -> E4 slot -> E5+lane drain; II1',
                 clock_scope='separate leaf pins, functionally tied by unchanged bench; no physical clock-delivery proof',
                 exactness_scope='legal payloads exactly match existing old-quarter gold; invalid schedules prove sticky fault only',
                 duplicate_scope='highest sourceID wins; legacy bitwise-OR duplicate payload is intentionally not represented',
                 checks=dict(gold_cases=20, mutants_rejected=8, bases=[0, 8, 16, 24],
                             modes=['three_slot_burst', 'duplicate', 'invalid_lane', 'empty_drain', 'sustained_II1_lane0'],
                             sources=53, banks_per_quarter=8, slots_per_bank=3,
                             full_row_mask_tag_data=True, reset_clears_fault_and_valid=True),
                 sources={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES},
                 records=records)
    check_lock()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    check_lock()
    OUT.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(dict(status=proof['status'], gold_cases=20, mutants_rejected=8)))


if __name__ == '__main__':
    main()
