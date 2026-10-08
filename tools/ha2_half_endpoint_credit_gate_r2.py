#!/usr/bin/env python3
"""One-endpoint exactness gate with an explicit dispatch-credit mutation.

The earlier hierarchical force was ineffective: its negative ran identically
to the baseline. Keep production RTL immutable and compile a private copy with
one audited, plusarg-controlled mutation at the actual dispatch predicate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import ha2_hub_credit_gate as source

TOP = 'tb_ha2_half_endpoint_credit_r2'
ENDPOINT = 'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner.sv'
BENCH = 'rtl/hbm_accel/ha2_ar/' + TOP + '.sv'
PREDICATE = '!invalid_partial_port[p] && owner_p_r[p]) rb_pop[p]'
MUTATION = ('!invalid_partial_port[p] && '
            '(owner_p_r[p] || $test$plusargs("IGNORE_PEER_CREDIT"))) rb_pop[p]')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be positive')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    files = list(dict.fromkeys(source.PARENT + source.HALF + [BENCH]))
    pinned = files + ['tools/ha2_half_endpoint_credit_gate_r2.py',
                      'tools/ha2_hub_credit_gate.py']
    pins = {s: sha(source.ROOT / s) for s in pinned}
    text = (source.ROOT / ENDPOINT).read_text()
    if text.count(PREDICATE) != 1:
        raise RuntimeError('Expected exactly one dispatch-credit predicate')
    private = out / 'mutated_dispatch_endpoint.sv'
    private.write_text(text.replace(PREDICATE, MUTATION))
    manifest = dict(source_sha256=pins, private_source_sha256=sha(private),
                    original_predicate=PREDICATE, replacement=MUTATION,
                    mutation='One dispatch predicate; enabled only by +IGNORE_PEER_CREDIT')
    (out / 'source_pins.json').write_text(json.dumps(manifest, indent=2) + '\n')
    cmd = ['verilator', '--binary', '--timing', '-O0', '-Wno-fatal',
           '-Wno-WIDTH', '--top-module', TOP, '--Mdir', str(out / 'obj'),
           '--build-jobs', str(args.threads)]
    cmd += [str(private) if s == ENDPOINT else str(source.ROOT / s) for s in files]
    (out / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
    if args.prepare_only:
        print('PREPARED_ONLY: mutation and source manifest; no numerical verdict')
        return 0
    with (out / 'build.log').open('w') as log:
        build = subprocess.run(cmd, cwd=source.ROOT, stdout=log, stderr=subprocess.STDOUT)
    (out / 'build.exit').write_text(str(build.returncode) + '\n')
    if build.returncode:
        return build.returncode
    checks = {}
    for mode in ['baseline', 'CORRUPT_GOLDEN', 'IGNORE_PEER_CREDIT']:
        command = [str(out / 'obj' / ('V' + TOP))]
        if mode != 'baseline':
            command.append('+' + mode)
        with (out / (mode + '.log')).open('w') as log:
            run = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT)
        output = (out / (mode + '.log')).read_text()
        if mode == 'baseline':
            correct = run.returncode == 0 and 'PASS_HA2_HALF_ENDPOINT_CREDIT_R2 ' in output
        elif mode == 'CORRUPT_GOLDEN':
            correct = run.returncode != 0 and 'ENDPOINT_FAIL numerical or identity mismatch' in output
        else:
            correct = run.returncode != 0 and 'ENDPOINT_CREDIT_VIOLATION ' in output
        checks[mode] = dict(returncode=run.returncode, correct=correct, output=output)
    assert pins == {s: sha(source.ROOT / s) for s in pinned}, 'Source changed during gate'
    assert sha(private) == manifest['private_source_sha256'], 'Mutation changed during gate'
    passed = all(check['correct'] for check in checks.values())
    record = dict(passed=passed, checks=checks, **manifest,
                  scope='One full-width PF384 endpoint; exactness and credit dispatch guard only. Physical qualification and collective composition remain pending.')
    (out / 'terminal.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(passed=passed, checks={k:v['correct'] for k,v in checks.items()})))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
