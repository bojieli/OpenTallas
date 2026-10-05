#!/usr/bin/env python3
"""Continue verified generated native compilation, with no elapsed-time cutoff."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def run(model_path, out):
    model = json.loads(model_path.read_text())
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        raise ValueError('Runner source must be clean')
    resource.setrlimit(resource.RLIMIT_FSIZE, (-1, -1))
    if sorted(os.sched_getaffinity(0)) != model['affinity']:
        raise ValueError('Affinity mismatch')
    line = next(x for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
    cg = Path('/sys/fs/cgroup') / line.split('::', 1)[1].lstrip('/')
    for name, expected in [('memory.max', model['memory_bytes']), ('memory.swap.max', 0), ('pids.max', model['pids'])]:
        if (cg / name).read_text().strip() != str(expected):
            raise ValueError('Cgroup mismatch: ' + name)
    available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    if available < model['memory_bytes'] + model['host_memory_reserve']:
        raise ValueError('Memory headroom')
    previous = Path(model['previous_output'])
    if sha(model['baseline_model']) != model['baseline_model_sha256']:
        raise ValueError('Baseline model changed')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=model['original_source_root'], text=True).strip() != model['original_source_commit']:
        raise ValueError('Original source commit changed')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=model['original_source_root']):
        raise ValueError('Original source must remain clean')
    old = json.loads((previous / 'verdict.json').read_text())
    if sha(previous / 'verdict.json') != model['previous_verdict_sha256']:
        raise ValueError('Previous receipt changed')
    front = Path(model['frontend_output'])
    if sha(front / 'verdict.json') != model['frontend_verdict_sha256']:
        raise ValueError('Frontend receipt changed')
    fv = json.loads((front / 'verdict.json').read_text())
    for entry in fv['generated_files']:
        if entry['path'].startswith('obj/') and sha(previous / entry['path']) != entry['sha256']:
            raise ValueError('Generated source changed: ' + entry['path'])
    retained = [x for x in old['artifacts'] if x['path'].endswith(('.o', '.gch'))]
    if len(retained) != 30:
        raise ValueError('Expected 28 objects and 2 PCH files')
    for entry in retained:
        if sha(previous / entry['path']) != entry['sha256']:
            raise ValueError('Retained object changed')
    if out.exists() or shutil.disk_usage(out.parent).free < model['output_bytes'] + model['host_disk_reserve']:
        raise ValueError('Fresh output/disk headroom')
    out.mkdir()
    receipt = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'model_sha256': sha(model_path), 'runner_sha256': sha(__file__),
               'previous_verdict_sha256': model['previous_verdict_sha256'], 'retained_artifacts': retained,
               'elapsed_time_limit': None, 'runtime_authorized': False, 'phases': []}
    (out / 'start.json').write_text(json.dumps(receipt, indent=2) + '\n')
    shutil.copytree(previous / 'obj', out / 'obj', copy_function=shutil.copy2)
    wrapper = out / 'cxx'
    wrapper.write_text('#!/bin/sh\nexec /usr/bin/prlimit --as=' + str(model['CXX_AS']) + ' --fsize=unlimited:unlimited -- /usr/bin/g++-11 "$@"\n')
    wrapper.chmod(0o755)
    baseline = json.loads(Path(model['baseline_model']).read_text())
    substitutions = {'{ROOT}': model['original_source_root'], '{OUT}': str(out), '{CXX}': str(wrapper),
                     '{GXX}': '/usr/bin/g++-11', '{VINC}': baseline['verilator_include']}
    started = time.monotonic()
    for phase in ['compile', 'link']:
        argv = []
        for arg in baseline['commands'][phase]:
            for key, value in substitutions.items():
                arg = arg.replace(key, value)
            if arg == '-j16':
                arg = '-j' + str(model['workers'])
            argv.append(arg)
        if phase == 'link':
            argv = ['/usr/bin/prlimit', '--as=' + str(model['link_AS']), '--fsize=unlimited:unlimited', '--'] + argv
        phase_started = time.monotonic()
        reason = None
        with (out / (phase + '.log')).open('wb') as log:
            proc = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while proc.poll() is None:
                total = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
                if total > model['output_bytes'] or shutil.disk_usage(out).free < model['host_disk_reserve']:
                    reason = 'AGGREGATE_DISK_GUARD'
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                progress = {'phase': phase, 'pid': proc.pid, 'objects': len(list((out / 'obj').glob('*.o'))),
                            'output_bytes': total, 'wall_s': time.monotonic() - started, 'elapsed_time_limit': None}
                (out / 'progress.json').write_text(json.dumps(progress, indent=2) + '\n')
                if reason:
                    break
                time.sleep(10)
            status = proc.wait()
        receipt['phases'].append({'phase': phase, 'argv': argv, 'exit_code': status, 'termination_reason': reason,
                                  'wall_s': time.monotonic() - phase_started, 'log_sha256': sha(out / (phase + '.log'))})
        if status != 0 or reason:
            break
    receipt.update(verdict='PASS_NATIVE_BUILD_ONLY' if len(receipt['phases']) == 2 and all(x['exit_code'] == 0 for x in receipt['phases']) else 'FAIL_NATIVE_BUILD',
                   wall_s=time.monotonic() - started, memory_peak=(cg / 'memory.peak').read_text().strip(),
                   memory_events=(cg / 'memory.events').read_text(), numerical_credit=False, physical_credit=False, token_credit=False)
    (out / 'verdict.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['verdict'], flush=True)
    return 0 if receipt['verdict'] == 'PASS_NATIVE_BUILD_ONLY' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    raise SystemExit(run(args.model, args.out))
