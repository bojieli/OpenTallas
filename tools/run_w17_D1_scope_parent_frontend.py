#!/usr/bin/env python3
"""Execute only the reviewed scope-corrected current-core frontend; no native/runtime credit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from w17_D1_scope_corrected_probe import E as EVIDENCE, verify
from w17_D1_current_core_admission import verify_host_tools

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(go_path):
    go = json.loads(go_path.read_text())
    if go['authorized_phase'] != 'frontend_only' or go['runtime_authorized'] is not False:
        raise ValueError('Only frontend execution is authorized')
    if Path(go['source_root']).resolve() != ROOT.resolve():
        raise ValueError('Wrong clean source root')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != go['source_commit']:
        raise ValueError('Wrong source commit')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        raise ValueError('Source worktree must be clean')
    plan_path = ROOT / EVIDENCE / 'plan.json'
    if digest(plan_path) != go['plan_sha256'] or digest(Path(__file__)) != go['runner_sha256']:
        raise ValueError('Plan or runner hash mismatch')
    verify(ROOT)
    verify_host_tools(ROOT)
    plan = json.loads(plan_path.read_text())
    caps = plan['caps']
    if sorted(os.sched_getaffinity(0)) != caps['frontend_affinity']:
        raise ValueError('Frontend kernel affinity mismatch')
    cg_line = next(x for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
    cg = Path('/sys/fs/cgroup') / cg_line.split('::', 1)[1].lstrip('/')
    for name, expected in [('memory.max', caps['aggregate_memory_bytes']), ('memory.swap.max', 0), ('pids.max', caps['pids_max'])]:
        if (cg / name).read_text().strip() != str(expected):
            raise ValueError('Cgroup mismatch: ' + name)
    available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    if available < caps['aggregate_memory_bytes'] + caps['host_memory_reserve_bytes'] + go['parallel_memory_reservation_bytes']:
        raise ValueError('Insufficient host headroom including parallel reservation')
    out = Path(go['output_root'])
    if out.exists():
        raise ValueError('Fresh output required; no overwrite or restart')
    if __import__('shutil').disk_usage(out.parent).free < caps['output_bytes'] + caps['host_disk_reserve_bytes']:
        raise ValueError('Insufficient output/disk reserve')
    out.mkdir()
    replacements = {'{ROOT}': str(ROOT), '{SCRATCH}': str(out), '{VERILATOR}': '/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'}
    argv = []
    for value in plan['commands']['frontend']:
        for key, replacement in replacements.items():
            value = value.replace(key, replacement)
        if '{' in value:
            raise ValueError('Unresolved frontend placeholder')
        argv.append(value)
    argv = ['/usr/bin/prlimit', '--as=' + str(caps['frontend_AS_bytes']), '--fsize=' + str(caps['file_bytes']), '--'] + argv
    start = time.monotonic()
    receipt = dict(schema='opentallas.D1.parent-frontend.v1', source_commit=go['source_commit'], plan_sha256=go['plan_sha256'], GO_sha256=digest(go_path), argv=argv, frontend_only=True, native_credit=False, runtime_credit=False, token_credit=False, physical_credit=False)
    (out / 'start.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    reason = None
    with (out / 'frontend.log').open('wb') as log:
        proc = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipt['pid'] = proc.pid
        while proc.poll() is None:
            total = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
            if time.monotonic() - start > caps['frontend_seconds']:
                reason = 'FRONTEND_WALL_CAP'
            elif total > caps['output_bytes'] or log.tell() > caps['log_bytes']:
                reason = 'FRONTEND_OUTPUT_CAP'
            if reason:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                break
            time.sleep(1)
        receipt.update(exit_code=proc.wait(), wall_s=time.monotonic() - start, termination_reason=reason)
    receipt['verdict'] = 'PASS_FRONTEND_ONLY' if receipt['exit_code'] == 0 and reason is None else 'FAIL_FRONTEND'
    receipt['log_sha256'] = digest(out / 'frontend.log')
    receipt['memory_events'] = (cg / 'memory.events').read_text()
    receipt['memory_peak_bytes'] = (cg / 'memory.peak').read_text().strip()
    receipt['generated_files'] = [{'path': str(p.relative_to(out)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'start.json']
    (out / 'verdict.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: receipt[k] for k in ('verdict', 'exit_code', 'wall_s', 'termination_reason')}, sort_keys=True), flush=True)
    return 0 if receipt['verdict'] == 'PASS_FRONTEND_ONLY' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--go', required=True, type=Path)
    raise SystemExit(run(parser.parse_args().go))
