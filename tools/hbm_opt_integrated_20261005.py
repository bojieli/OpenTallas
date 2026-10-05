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


def workload_parameters(config, workload, enabled):
    """Apply only levers eligible for the actual selected target implementation."""
    return {name: parameters for name, parameters in enabled.items()
            if workload in config['levers'][name].get('eligible_workloads', config['workloads'])}


def source_inventory(item, root):
    """Resolve owner candidate objects for inventory; never grant exact enable."""
    sources, origins, holds = {}, {}, []
    for name in item['source_paths']:
        candidate = item.get('source_candidates', {}).get(name)
        path = root / name
        if path.is_file():
            digest = sha(path)
            origins[name] = 'worktree'
        elif candidate:
            try:
                data = subprocess.check_output(
                    ['git', 'show', candidate['commit'] + ':' + name],
                    cwd=root, stderr=subprocess.DEVNULL)
                digest = hashlib.sha256(data).hexdigest()
                origins[name] = candidate['commit']
            except subprocess.CalledProcessError:
                digest = None
        else:
            digest = None
        sources[name] = digest
        if digest is None or (candidate and digest != candidate['sha256']):
            holds.append('missing/changed owner candidate source: ' + name)
    return sources, origins, holds


def prepare(config, root, profile):
    requested = config['profiles'][profile]
    levers, enabled = {}, {}
    for name, item in config['levers'].items():
        sources, origins, source_holds = source_inventory(item, root)
        binding = item['binding']
        errors = exact_errors(binding, root) if binding else [item['missing']]
        errors.extend(source_holds)
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
                            source_origins=origins, source_holds=source_holds,
                            exact_holds=errors, physical_holds=closure)
    workloads = {}
    for name, item in config['workloads'].items():
        binding = item['binding']
        target_enabled = workload_parameters(config, name, enabled)
        errors = []
        if not binding:
            errors = ['selected combined minimum-component executable/recipe unbound']
        else:
            for key in ('source_sha256', 'input_sha256', 'executable_sha256'):
                errors.extend(pin_errors(binding.get(key), root))
            if binding.get('applied_levers') != target_enabled:
                errors.append('recipe flags differ from the selected combined configuration')
            if not binding.get('argv') or not binding.get('result_contract'):
                errors.append('missing callable argv/result contract')
        workloads[name] = dict(holds=errors, binding=binding, enabled=target_enabled,
                              inapplicable=[n for n in requested if name not in
                                  config['levers'][n].get('eligible_workloads', config['workloads'])])
    return dict(schema='opentallas.hbm-opt-integrated-plan.v1', profile=profile,
                enabled=enabled, levers=levers, workloads=workloads,
                first_two_exact=len(enabled) >= 2,
                headline_clock_eligible=bool(enabled) and all(
                    not levers[name]['physical_holds'] for name in enabled),
                full_token_measured=False, composition_owner='Maxwell',
                die_floorplan_owner='Claude',
                index_order_source_join=index_order_source_files(config, root)
                    if config.get('index_order_adapter') else None)


def save(path, record):
    with Path(path).open('x') as f:
        json.dump(record, f, indent=2)
        f.write('\n')


def index_order_source_files(config, root):
    """Join Sagan's measured adapter sources without granting enclosing enable.

    W15 scores and IDs are separate words. Their checked pair formatter and the
    exclusive gather/publication owner remain Sagan/parent dependencies; source
    enrollment must never treat that storage as interleaved adapter responses.
    """
    spec = config['index_order_adapter']
    sources, origins, errors = source_inventory(spec, root)
    binding = spec['component_binding']
    errors.extend(exact_errors(binding, root))
    return dict(source_paths=spec['source_paths'], source_sha256=sources,
                source_origins=origins,
                ordered_source_files=[str(root / name) for name in spec['source_paths']],
                source_holds=errors, component_exact=not errors,
                component_geometry={'N': 2, 'NPER': 16},
                target_geometry={'N': 96, 'NPER': 512},
                formatter=spec['formatter'],
                enclosing_holds=spec['enclosing_holds'],
                enclosing_ready=False, parameters={'ENABLE': 0},
                global_ordered_gather_qualified=False,
                planning=spec['planning'], rate_credit=False)


def expert_w2_service_inputs(config, root, layer, service_dir):
    """Bind existing Hubble service bytes/configuration; grant no arithmetic credit.

    The production caller consumes these literal files together. No legacy seam
    reconstruction, router inference, activation generation or build is performed.
    """
    item = config['levers']['expert_workgroup']
    _, _, errors = source_inventory(item, root)
    spec = item['service_binding']
    receipt = root / spec['receipt']
    if not receipt.is_file() or sha(receipt) != spec['receipt_sha256']:
        raise ValueError('missing/changed W2 service receipt')
    record = json.loads(receipt.read_text())
    if record['status'] != 'PASS_SERVICE_BYTES_ONLY':
        raise ValueError('W2 byte service did not pass')
    for name, expected in record['source_sha256'].items():
        candidate = item['source_candidates'].get(name)
        if candidate and candidate['sha256'] != expected:
            errors.append('selected source differs from measured W2 service: ' + name)
    cases = [c for c in record['cases'] if c['layer'] == layer]
    if len(cases) != 1 or not cases[0]['exact_bytes'] or cases[0]['exit'] != 0:
        raise ValueError('missing exact released layer service case')
    case = cases[0]
    service_dir = Path(service_dir).resolve()
    files = {}
    for name in ('w2.hex', 'cfg_lines.hex', 'cfg_lut.hex'):
        path = service_dir / name
        if not path.is_file() or sha(path) != case['input_sha256'][name]:
            errors.append('missing/changed released W2 service input: ' + name)
        files[name] = str(path)
    if errors:
        raise ValueError('; '.join(errors))
    counts = [int(x, 16) for x in Path(files['cfg_lines.hex']).read_text().split()]
    lut = [int(x, 16) for x in Path(files['cfg_lut.hex']).read_text().split()]
    if counts != spec['counts'] or len(lut) != spec['transport_lines_per_expert']:
        raise ValueError('literal W2 configuration differs from enrolled service')
    # Consume the owner's exact line ownership; do not regenerate a uniform map.
    return dict(layer=layer, die=case['die'], stack=case['stack'], ids=case['ids'],
                files=files, input_sha256={n: case['input_sha256'][n] for n in files},
                cfg_lines=counts, cfg_lut=lut, receipt_sha256=spec['receipt_sha256'],
                source_sha256=record['source_sha256'],
                scope='released W2 byte delivery and literal configuration only',
                arithmetic_qualified=False, rate_credit=False,
                production_provider_connected=False, adopted=False)


def run(config, root, profile, out, workload_names=None):
    policy = config['host_policy']
    host = policy['new_heavy_hosts'].get(socket.gethostname())
    if host is None:
        raise ValueError('Runtime is remote EPYC1/2 only; local plan is lightweight')
    out = out.resolve()
    if not out.is_relative_to(Path(host['job_root'])):
        raise ValueError('Use the selected host\'s unique NVMe job output')
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
        command = [host['admit'], str(binding['admit_gib']), '--', *argv]
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
    parser.add_argument('step', choices=['plan', 'run', 'w2-service'])
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--profile', choices=['default_off', 'candidate_on', 'admitted_closed'],
                        default='default_off')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--layer', type=int, choices=[3, 20])
    parser.add_argument('--service-dir', type=Path,
                        help='Existing Hubble released W2 service directory; no generation')
    parser.add_argument('--workload', action='append', choices=['ds_1m', 'qwen_8k'],
                        help='Run ready workload without waiting for another unbound executable')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.step == 'w2-service':
        if args.layer is None or args.service_dir is None:
            parser.error('w2-service requires --layer and --service-dir')
        record = expert_w2_service_inputs(config, args.root.resolve(), args.layer,
                                         args.service_dir)
        if args.out:
            save(args.out, record)
        else:
            print(json.dumps(record, indent=2))
        return 0
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
