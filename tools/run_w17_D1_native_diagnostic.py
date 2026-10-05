#!/usr/bin/env python3
"""Run the frozen compiled D1 prefix diagnostic after a verified native join.

No frontend/engine changes, no host wall/file/address-space limits, no token credit.
The compiled 512-cycle stop is a diagnostic outcome, never operation completion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
JOIN_SOURCE = 'ffd319b7acf75aabb3c88b45bb5343f95f80bdc5'
ENGINE_SOURCE = '4e38326d6f361bc85e660f48c59c355e2bb95274'
PROGRAM_SHA = 'dc93faea61a95d04d0a157d09e9c962d7f863bb9559ab92532aed61d7856d1c6'
PROGRAM = Path('/tmp/opentallas-D1-native-r2-execution-20261002/results/uarch/w17_D1_current_core_probe_20261002/prog.hex')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def validate_join(receipt, binary, program):
    if (receipt.get('verdict') != 'PASS_NATIVE_PREFIX_LINK_ONLY'
            or receipt.get('source_head') != JOIN_SOURCE
            or receipt.get('node_source_head') != 'a93ac5a8c2312266213cc4f119aa2bd99175f52a'
            or receipt.get('objects') != 3829
            or receipt.get('archive_compiler_commands') != 0
            or receipt.get('runtime_started') is not False):
        raise ValueError('Native join/source closure unavailable')
    if sha(binary) != receipt.get('binary_sha256') or sha(program) != PROGRAM_SHA:
        raise ValueError('Binary/program hash mismatch')
    with binary.open('rb') as f:
        if f.read(6) != b'\x7fELF\x02\x01':
            raise ValueError('Native ELF identity')

def classify(text, exit_code):
    # Source assertions/ledger sticky faults take precedence over any witness.
    if exit_code != 0 or any(x in text for x in ('%Error', 'D1_SOURCE_OR_LEDGER_FAULT', 'D1_SOURCE_ADMISSION_MISMATCH', 'D1_NO_PENDING_EVENTS_NO_SERVICE_CREDIT', 'D1_UNEXPECTED_TIME_PRECISION_NO_CLOCK_CREDIT')):
        return {'verdict': 'FAIL_DIAGNOSTIC_RUNTIME', 'qualified_prefix': False}
    terminal = re.findall(r'D1_TERMINAL_PREFIX_ONLY evals=(\d+) time_ps=(\d+) cycles=(\d+)', text)
    if len(terminal) != 1:
        return {'verdict': 'FAIL_DIAGNOSTIC_TERMINAL_PROTOCOL', 'qualified_prefix': False}
    gates = re.findall(r'D1_REAL_GATE time=\d+ pc=\d+ me_ready=([01]) kv_ok=([01]) kvd_v=([01]) win_idle=([01]) waited=([01]) q_gate=([01]) m0_gate=([01])', text)
    witness = re.findall(r'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY reads=(\d+) returns=(\d+) writes=(\d+) acks=(\d+)', text)
    descriptors = re.findall(r'D1_REAL_DESCRIPTOR time=\d+ generation=\d+ rows=\d+', text)
    accepts = re.findall(r'D1_REAL_ACCEPT time=\d+ address=\d+ tag=\d+ write=0', text)
    replies = re.findall(r'D1_REAL_RESPONSE time=\d+ tag=\d+ beat=0', text)
    if witness:
        if (len(witness) != 1 or not gates or not descriptors or not accepts or not replies
                or int(witness[0][0]) < 1 or int(witness[0][1]) < 1
                or int(witness[0][1]) > int(witness[0][0])
                or int(witness[0][3]) > int(witness[0][2])):
            return {'verdict': 'FAIL_DIAGNOSTIC_WITNESS_PROTOCOL', 'qualified_prefix': False}
        verdict = 'PASS_CONTROLLED_PREFIX_GATE_AND_FIRST_RETURN_ONLY'
    elif 'D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512' in text and int(terminal[0][2]) == 512:
        verdict = 'INCONCLUSIVE_COMPILED_512_CYCLE_STOP'
    else:
        verdict = 'FAIL_DIAGNOSTIC_WITNESS_PROTOCOL'
    return {'verdict': verdict, 'qualified_prefix': verdict.startswith('PASS_'),
            'actual_gate_records': len(gates), 'actual_descriptors': len(descriptors),
            'actual_read_accept_records': len(accepts), 'actual_response_records': len(replies),
            'terminal': dict(zip(('evals', 'time_ps', 'cycles'), map(int, terminal[0])))}

def run(join, out):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        raise ValueError('Dirty runner source')
    receipt = json.loads((join / 'receipt.json').read_text())
    binary = join / 'D1_current_prefix'
    validate_join(receipt, binary, PROGRAM)
    if sha(join / 'obj/Vtb_D1_scope_core__ALL.a') != receipt['archive_sha256']:
        raise ValueError('Archive changed')
    if out.exists():
        raise ValueError('Fresh output required')
    available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    if available < 128 * 2**30 or shutil.disk_usage(out.parent).free < 48 * 2**30:
        raise ValueError('Existing96GiB reservation plus32GiB host reserve/disk inventory unavailable')
    out.mkdir()
    (out / 'input').mkdir()
    shutil.copy2(PROGRAM, out / 'input/prog.hex')
    before = {'binary': sha(binary), 'program': sha(out / 'input/prog.hex'), 'archive': receipt['archive_sha256']}
    for name, argv in [('ELF', ['readelf', '-h', '-d', '-V', str(binary)]), ('libraries', ['ldd', str(binary)])]:
        result = subprocess.run(argv, capture_output=True, text=True)
        (out / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode or 'not found' in result.stdout:
            raise ValueError('Native ABI unavailable: ' + name)
    record = {'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'engine_source': ENGINE_SOURCE, 'join_source': JOIN_SOURCE,
              'scope': 'FROZEN_FULL_GEOMETRY_CONTROLLED_PREFIX_ONLY',
              'full_token_credit': False, 'original_PC24_cause': 'UNOBSERVED',
              'causal_service_bound': 'BOUND_MISSING', 'no_ECC_successor_selected': False,
              'wall_limit': None, 'per_file_limit': None, 'per_process_AS_limit': None,
              'memory_reservation_bytes': 96 * 2**30, 'input_hashes': before}
    argv = [str(binary), '+DIR=' + str(out / 'input')]
    start = time.monotonic()
    with (out / 'runtime.log').open('wb') as log:
        proc = subprocess.Popen(argv, cwd=out, stdout=log, stderr=subprocess.STDOUT)
        record.update(owned_PID=proc.pid, argv=argv)
        (out / 'start.json').write_text(json.dumps(record, indent=2) + '\n')
        code = proc.wait()
    record.update(exit_code=code, wall_s=time.monotonic()-start)
    record.update(classify((out / 'runtime.log').read_text(errors='replace'), code))
    record['postcheck'] = (sha(binary) == before['binary'] and sha(out / 'input/prog.hex') == before['program'] and sha(join / 'obj/Vtb_D1_scope_core__ALL.a') == before['archive'])
    if not record['postcheck']:
        record.update(verdict='FAIL_RUNTIME_INPUT_POSTCHECK', qualified_prefix=False)
    (out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    return record

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--join', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(run(args.join, args.out)))
