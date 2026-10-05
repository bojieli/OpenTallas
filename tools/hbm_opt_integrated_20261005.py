#!/usr/bin/env python3
"""Run source-bound HBM minimum components together through existing owner recipes.

No RTL emission, oracle generation, model composition, or implicit build/retry.
Default-off configuration and candidate measurements are separate from physical
admission. Missing owner source/executable bindings remain explicit holds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / 'results/rtl/hbm_opt_integrated_20261005/config.json'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def get(record, path):
    for key in path:
        record = record[key]
    return record


def pin_errors(pins, root):
    if not pins:
        return ['missing source/input/executable pins']
    errors = []
    for name, expected in pins.items():
        p = root / name
        if not p.is_file():
            errors.append(f'missing file: {name}')
        elif sha(p) != expected:
            errors.append(f'changed file: {name}')
    return errors


def exact_errors(binding, root):
    errors = pin_errors(binding.get('source_sha256'), root)
    receipts = binding.get('exact_receipts', [])
    if not receipts:
        errors.append('missing source-bound exact result')
    for receipt in receipts:
        p = root / receipt['path']
        if not p.is_file() or sha(p) != receipt['sha256']:
            errors.append(f'missing/changed exact receipt: {p}')
            continue
        record = json.loads(p.read_text())
        if get(record, receipt['pass_path']) != receipt['pass_value']:
            errors.append(f'exact receipt did not pass: {p}')
        # Require the passed measurement to name every selected component source.
        source_record = record
        if receipt.get('source_record'):
            source = root / receipt['source_record']
            if (not source.is_file() or sha(source) != receipt['source_record_sha256'] or
                    get(record, receipt['source_record_hash_path']) != receipt['source_record_sha256']):
                errors.append(f'exact result/source record join differs: {p}')
                continue
            source_record = json.loads(source.read_text())
        measured = get(source_record, receipt['source_pins_path'])
        if any(measured.get(k) != v for k, v in binding['source_sha256'].items()):
            errors.append(f'exact receipt source differs: {p}')
    return errors


def physical_errors(binding, root):
    physical = binding.get('physical')
    if not physical:
        return ['selected loaded SS/FF context unbound']
    errors = pin_errors(physical.get('artifact_sha256'), root)
    p = root / physical['receipt']
    if not p.is_file():
        return errors + ['missing physical receipt']
    record = json.loads(p.read_text())
    measured = get(record, physical['source_pins_path'])
    if any(measured.get(k) != v for k, v in binding['source_sha256'].items()):
        errors.append('physical source differs from selected component')
    for corner, metric, required in [('SS', 'setup', 60), ('FF', 'hold', 25)]:
        spec = physical[corner]
        if (get(record, spec['uncertainty_ps_path']) != required or
                get(record, spec['exit_path']) != 0 or
                get(record, spec['slack_ps_path']) < 0):
            errors.append(f'{corner} {metric} does not meet unchanged policy')
    if not physical.get('loaded_context') or not physical.get('clock_period_ps'):
        errors.append('missing loaded parent context/clock period')
    return errors


def prepare(config, root, profile):
    requested = config['profiles'][profile]
    levers, enabled = {}, {}
    for name, item in config['levers'].items():
        sources = {s: sha(root / s) if (root / s).is_file() else None
                   for s in item['source_paths']}
        binding = item['binding']
        errors = exact_errors(binding, root) if binding else [item['missing']]
        if binding and any(s not in binding['source_sha256'] for s in item['source_paths']):
            errors.append('binding omits a required source')
        closure = physical_errors(binding, root) if binding else ['physical binding absent']
        selected = name in requested and not errors
        if name == 'su_physical' or profile == 'admitted_closed':
            selected = selected and not closure
        if selected:
            enabled[name] = binding['parameters']
        levers[name] = dict(owner=item['owner'], requested=name in requested,
                            selected=selected, source_sha256=sources,
                            exact_holds=errors, physical_holds=closure)
    workloads = {}
    for name, item in config['workloads'].items():
        binding = item['binding']
        errors = []
        if not binding:
            errors = ['selected combined minimum-component executable/recipe unbound']
        else:
            for key in ('source_sha256', 'input_sha256', 'executable_sha256'):
                errors.extend(pin_errors(binding.get(key), root))
            if binding.get('applied_levers') != enabled:
                errors.append('recipe flags differ from the selected combined configuration')
            if not binding.get('argv') or not binding.get('result_contract'):
                errors.append('missing callable argv/result contract')
        workloads[name] = dict(holds=errors, binding=binding)
    return dict(schema='opentallas.hbm-opt-integrated-plan.v1', profile=profile,
                enabled=enabled, levers=levers, workloads=workloads,
                first_two_exact=len(enabled) >= 2,
                headline_clock_eligible=bool(enabled) and all(
                    not levers[name]['physical_holds'] for name in enabled),
                full_token_measured=False, composition_owner='Maxwell',
                die_floorplan_owner='Claude')


def save(path, record):
    with Path(path).open('x') as f:
        json.dump(record, f, indent=2)
        f.write('\n')


def run(config, root, profile, out, workload_names=None):
    policy = config['host_policy']
    if socket.gethostname() != policy['new_heavy_host']:
        raise ValueError('Runtime is remote EPYC1 only; local plan is lightweight')
    out = out.resolve()
    if not out.is_relative_to(Path(policy['job_root'])):
        raise ValueError('Use unique EPYC1 jobs-overflow NVMe output')
    plan = prepare(config, root, profile)
    if profile == 'default_off' or not plan['first_two_exact']:
        raise ValueError('Combined candidate requires the first two exact levers')
    selected_workloads = workload_names or list(plan['workloads'])
    if any(plan['workloads'][name]['holds'] for name in selected_workloads):
        raise ValueError('Selected combined minimum-component executable bindings are incomplete')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root).strip():
        raise ValueError('Runtime source must be a pinned clean worktree')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'tmp').mkdir()
    save(out / 'config.json', config)
    save(out / 'plan.json', plan)
    env = dict(os.environ, TMPDIR=str(out / 'tmp'), NUM_CORES='16',
               OT_SYNTH_TIMEOUT_SECONDS='unlimited', OT_FLOW_TIMEOUT_SECONDS='unlimited')
    results = {}
    for name in selected_workloads:
        item = plan['workloads'][name]
        binding = item['binding']
        folder = out / name
        folder.mkdir()
        # Substitution is only for the unique result directory; no shell expansion.
        argv = [arg.replace('{out}', str(folder)) for arg in binding['argv']]
        command = [policy['admit'], str(binding['admit_gib']), '--', *argv]
        save(folder / 'command.json', command)
        with (folder / 'runtime.log').open('x') as log:
            process = subprocess.Popen(command, cwd=binding['cwd'], env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
            save(folder / 'running.json', {'pid': process.pid})
            rc = process.wait()
        save(folder / 'exit.json', {'exit': rc})
        receipt = folder / binding['output_record']
        contract = binding['result_contract']
        if rc or not receipt.is_file():
            results[name] = dict(exit=rc, exact=False, cycles=None,
                                 failure='owner recipe failed or produced no result')
            continue
        measured = json.loads(receipt.read_text())
        exact = get(measured, contract['pass_path']) == contract['pass_value']
        cycles = get(measured, contract['cycles_path'])
        if not isinstance(cycles, int) or cycles < 0:
            results[name] = dict(exit=rc, exact=False, cycles=None,
                                 failure='Result did not report actual integer cycles')
            continue
        source_pins = get(measured, contract['source_pins_path'])
        exact = exact and all(source_pins.get(k) == v
                             for k, v in binding['source_sha256'].items())
        results[name] = dict(exit=rc, exact=exact, cycles=cycles,
                             receipt_sha256=sha(receipt), record=measured)
    stable = prepare(config, root, profile)
    passed = all(r['exact'] for r in results.values()) and stable == plan
    save(out / 'terminal.json', dict(status='pass' if passed else 'fail',
         workloads=results, enabled=plan['enabled'], source_stable=stable == plan,
         headline_clock_eligible=plan['headline_clock_eligible'],
         full_token_measured=False, composition_owner='Maxwell',
         pending_workloads=[n for n in plan['workloads'] if n not in selected_workloads],
         both_workloads_measured=len(results) == len(plan['workloads']),
         interaction_scope='Selected bound minimum components with flags together'))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['plan', 'run'])
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--profile', choices=['default_off', 'candidate_on', 'admitted_closed'],
                        default='default_off')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--workload', action='append', choices=['ds_1m', 'qwen_8k'],
                        help='Run ready workload without waiting for another unbound executable')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.step == 'run':
        if args.out is None:
            parser.error('run requires a fresh --out directory')
        return run(config, args.root.resolve(), args.profile, args.out, args.workload)
    plan = prepare(config, args.root.resolve(), args.profile)
    if args.out:
        save(args.out, plan)
    else:
        print(json.dumps(plan, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
