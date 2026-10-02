#!/usr/bin/env python3
"""Fresh native compilation of enrolled D1 output; never runs the simulator."""
import argparse
import hashlib
import json
import os
import resource
from pathlib import Path
import shutil
import signal
import subprocess
import time

from w17_D1_generated_native_guard import review
from w17_D1_current_core_admission import verify_host_tools

ROOT = Path(__file__).resolve().parents[1]
E = 'results/uarch/w17_D1_parent_native_r2_20261002'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def run(go_path):
    go = json.loads(go_path.read_bytes())
    if go['authorized_phase'] != 'compile_link_only' or go['runtime_authorized'] is not False:
        raise ValueError('Native compilation only')
    if ROOT.resolve() != Path(go['source_root']).resolve():
        raise ValueError('Source root')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != go['source_commit']:
        raise ValueError('Source commit')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        raise ValueError('Clean source required')
    model_path = ROOT / E / 'model.json'
    if sha(model_path) != go['model_sha256'] or sha(__file__) != go['runner_sha256']:
        raise ValueError('Model/runner hash')
    model = json.loads(model_path.read_bytes()); caps = model['caps']
    resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    if resource.getrlimit(resource.RLIMIT_FSIZE) != (resource.RLIM_INFINITY, resource.RLIM_INFINITY):
        raise ValueError('Unlimited file size required')
    contract = json.loads((ROOT / model['contract']).read_bytes())
    front = Path(go['frontend_output'])
    review(front, contract, ROOT); verify_host_tools(ROOT)
    if sorted(os.sched_getaffinity(0)) != caps['affinity']:
        raise ValueError('Kernel affinity')
    line = next(x for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
    cg = Path('/sys/fs/cgroup') / line.split('::', 1)[1].lstrip('/')
    for name, value in [('memory.max', caps['memory_bytes']), ('memory.swap.max', 0), ('pids.max', caps['pids'])]:
        if (cg / name).read_text().strip() != str(value):
            raise ValueError('Cgroup ' + name)
    available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    if available < caps['memory_bytes'] + caps['host_memory_reserve'] + go['parallel_memory_reservation']:
        raise ValueError('Memory headroom')
    out = Path(go['output_root'])
    if out.exists() or shutil.disk_usage(out.parent).free < caps['output_bytes'] + caps['host_disk_reserve']:
        raise ValueError('Fresh output/disk headroom')
    out.mkdir(); start = time.monotonic()
    receipt = {'source_commit': go['source_commit'], 'GO_sha256': sha(go_path), 'model_sha256': sha(model_path),
               'frontend_receipt_sha256': sha(front / 'verdict.json'), 'runtime_authorized': False,
               'file_size_limits': list(resource.getrlimit(resource.RLIMIT_FSIZE)), 'phases': []}
    (out / 'start.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    shutil.copytree(front / 'obj', out / 'obj')
    compiler = model['compiler']
    wrapper = out / 'cxx_capped'
    wrapper.write_text('#!/bin/sh\nexec /usr/bin/prlimit --as=' +
                       str(caps['CXX_AS']) + ' --fsize=unlimited:unlimited -- ' + compiler + ' "$@"\n')
    wrapper.chmod(0o755)
    substitutions = {'{ROOT}': str(ROOT), '{OUT}': str(out), '{GXX}': compiler,
                     '{VINC}': model['verilator_include'], '{CXX}': str(wrapper)}
    for phase in ['compile', 'link']:
        argv = []
        for item in model['commands'][phase]:
            for key, value in substitutions.items(): item = item.replace(key, value)
            if '{' in item: raise ValueError('Unresolved command')
            argv.append(item)
        argv = ['/usr/bin/prlimit', '--fsize=unlimited:unlimited'] + (
            ['--as=' + str(caps['link_AS'])] if phase == 'link' else []) + ['--'] + argv
        log_path = out / (phase + '.log'); reason = None; phase_start = time.monotonic()
        with log_path.open('wb') as log:
            proc = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while proc.poll() is None:
                total = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
                if time.monotonic() - start > caps['seconds']: reason = 'NATIVE_WALL_CAP'
                elif total > caps['output_bytes'] or log_path.stat().st_size > caps['log_bytes']: reason = 'NATIVE_OUTPUT_CAP'
                if reason:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                    break
                time.sleep(1)
            status = proc.wait()
        receipt['phases'].append({'phase': phase, 'argv': argv, 'exit_code': status, 'termination_reason': reason,
                                  'wall_s': time.monotonic() - phase_start, 'log_sha256': sha(log_path)})
        if status != 0 or reason: break
    receipt['verdict'] = 'PASS_NATIVE_BUILD_ONLY' if len(receipt['phases']) == 2 and all(
        p['exit_code'] == 0 and p['termination_reason'] is None for p in receipt['phases']) else 'FAIL_NATIVE_BUILD'
    review(front, contract, ROOT)
    original = json.loads((front / 'verdict.json').read_bytes())
    for entry in original['generated_files']:
        if entry['path'].startswith('obj/') and sha(out / entry['path']) != entry['sha256']:
            raise ValueError('Generated source modified by native build')
    receipt.update(wall_s=time.monotonic() - start, memory_peak=(cg / 'memory.peak').read_text().strip(),
                   memory_events=(cg / 'memory.events').read_text(),
                   artifacts=[{'path': str(p.relative_to(out)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                              for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'start.json'],
                   numerical_credit=False, physical_credit=False, token_credit=False)
    (out / 'verdict.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(receipt['verdict'], flush=True)
    return 0 if receipt['verdict'] == 'PASS_NATIVE_BUILD_ONLY' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--go', type=Path, required=True)
    raise SystemExit(run(p.parse_args().go))
