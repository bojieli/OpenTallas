#!/usr/bin/env python3
"""Identity-bound, read-only intake of already running W12 scientific jobs."""
import argparse
import base64
import datetime
import hashlib
import inspect
import json
import os
import socket
import subprocess
import time
from pathlib import Path

JOBS = [
    dict(name='tp4_su64_token', host='ot-pve1', roots=[1217332, 1220907],
         scopes=['/home/ubuntu/w12/rt_tp4d'], record='/home/ubuntu/w12/rt_tp4d_token.json',
         extras=['/home/ubuntu/w12/rt_tp4d/token.log', '/home/ubuntu/w12/rt_tp4d/build_params.json']),
    dict(name='ar256_su64_l0', host='ot-pve1', roots=[1356870, 1366607],
         scopes=['/home/ubuntu/w12bwork/seg/rt'], record='/home/ubuntu/w12bwork/seg/rt_l0.json',
         extras=['/home/ubuntu/w12bwork/seg/rt_l0.out', '/home/ubuntu/w12bwork/seg/rt/token.log']),
    dict(name='tile_i518_replacement', host='ot-pve3', roots=[1921558, 1921625],
         scopes=['/home/ubuntu/w12bwork/keep_i518', 'w12_tile_i518'],
         record='/home/ubuntu/w12bwork/src/results/physical_hdc/asap7/qwen_o4_w12/tile_i518/physical.json',
         extras=['/home/ubuntu/w12bwork/chain_i518.log']),
    dict(name='tile_i560_replacement', host='ot-pve2', roots=[2563050, 2563179],
         scopes=['/home/ubuntu/w12bwork/keep_i560', 'w12_tile_i560'],
         record='/home/ubuntu/w12bwork/src/results/physical_hdc/asap7/qwen_o4_w12/tile_i560/physical.json',
         extras=['/home/ubuntu/w12bwork/chain_i560.log']),
    dict(name='spine_s833b', host='ot-pve2', roots=[3091880, 3091926],
         scopes=['/home/ubuntu/w12work/tmp/abi3-physical-factucn1', 'w12_spine_s833b'],
         record='/home/ubuntu/w12work/repo/results/physical_hdc/asap7/qwen_o4_w12/spine_s833b/physical.json',
         extras=['/home/ubuntu/w12work/spine_s833b.log']),
    dict(name='partition_product_attempt2', host=None, roots=[430286, 430287],
         scopes=['/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2'],
         record='/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2.json',
         extras=['/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2.log',
                 '/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2.rc']),
    dict(name='original_validation_suite', host=None, roots=[2619134, 2619136, 2619302],
         scopes=['/tmp/claude-1000/w12b/pytest_tm.log'],
         record='/tmp/claude-1000/w12b/suite_verdict_20261001/verdict.json',
         extras=['/tmp/claude-1000/w12b/pytest_tm.log']),
]


def read_process(pid):
    p = Path('/proc') / str(pid)
    try:
        stat = p.joinpath('stat').read_text().rsplit(') ', 1)[1].split()
        argv = [x.decode(errors='replace') for x in p.joinpath('cmdline').read_bytes().split(b'\0') if x]
        try:
            cwd = os.readlink(p / 'cwd')
        except OSError:
            cwd = None
        # Verify PID did not recycle during the multi-file read.
        end = p.joinpath('stat').read_text().rsplit(') ', 1)[1].split()
        if stat[19] != end[19]:
            raise RuntimeError('process changed during identity read')
        return dict(pid=int(pid), start_ticks=int(stat[19]), argv=argv,
                    state=end[0], ppid=int(end[1]), cwd=cwd)
    except FileNotFoundError:
        return None


def capture(job, monitored):
    host = dict(hostname=socket.gethostname(), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    processes = {}
    for p in Path('/proc').iterdir():
        if p.name.isdigit() and int(p.name) != os.getpid():
            info = read_process(int(p.name))
            if info is not None:
                processes[p.name] = info
    associated = set(map(int, job['roots'])) | set(map(int, monitored))
    for pid, p in processes.items():
        if any(scope in arg for scope in job['scopes'] for arg in p['argv']) or any(
                p['cwd'] and (p['cwd'] == scope or p['cwd'].startswith(scope + '/')) for scope in job['scopes']):
            associated.add(int(pid))
    # Include descendants and remember them across polls even after reparenting.
    while True:
        added = {int(pid) for pid, p in processes.items() if p['ppid'] in associated}
        if added <= associated:
            break
        associated |= added
    return dict(host=host, processes={pid: p for pid, p in processes.items() if int(pid) in associated})


def evaluate(binding, snapshot):
    """Identity changes are inconclusive; wrapper exit cannot hide live children."""
    if binding['host'] != snapshot['host']:
        return dict(state='identity_changed', qualification='inconclusive', reason='host or boot changed')
    for pid, expected in binding['processes'].items():
        actual = snapshot['processes'].get(pid)
        if actual is None:
            continue
        if actual['start_ticks'] != expected['start_ticks'] or (
                actual['state'] != 'Z' and actual['argv'] != expected['argv']):
            return dict(state='identity_changed', qualification='inconclusive', pid=int(pid))
    live = [int(pid) for pid, p in snapshot['processes'].items() if p['state'] != 'Z']
    if live:
        return dict(state='live' if any(pid in live for pid in binding['roots'][:1]) else 'children_live',
                    live_pids=sorted(live))
    return dict(state='eligible_for_intake')


def intake(job):
    """Only JSON's own status is a verdict; wrapper .rc is raw evidence."""
    record = Path(job['record'])
    paths = [record] + [Path(p) for p in job['extras']]
    if record.name == 'physical.json':
        paths += list(record.parent.glob('*.log')) + list(record.parent.glob('corners/*.json'))
    files = {}
    for p in paths:
        if p.is_file() and p.stat().st_size <= 2 * 1024 * 1024:
            data = p.read_bytes()
            files[str(p)] = dict(sha256=hashlib.sha256(data).hexdigest(), base64=base64.b64encode(data).decode())
    status = None
    if str(record) in files:
        status = json.loads(base64.b64decode(files[str(record)]['base64'])).get('status')
    return dict(raw_status=status, qualification='unreviewed' if status in ('pass', 'fail', 'error') else 'inconclusive', files=files)


def remote_probe(job, binding, collect):
    snapshot = capture(job, binding['processes'] if binding else {})
    if binding is None:
        missing = [p for p in job['roots'] if str(p) not in snapshot['processes'] or snapshot['processes'][str(p)]['state'] == 'Z']
        return dict(state='identity_unbound' if missing else 'binding_available', snapshot=snapshot, missing_roots=missing)
    state = evaluate(binding, snapshot)
    state['snapshot'] = snapshot
    if collect and state['state'] == 'eligible_for_intake':
        evidence = intake(job)
        second = capture(job, binding['processes'])
        guard = evaluate(binding, second)
        if guard['state'] != 'eligible_for_intake':
            return dict(**guard, snapshot=second)
        # Do not archive text that changed during intake, even if roots exited.
        for source, item in evidence['files'].items():
            if hashlib.sha256(Path(source).read_bytes()).hexdigest() != item['sha256']:
                return dict(state='record_changed', qualification='inconclusive', snapshot=second)
        return dict(state='terminal', snapshot=second, **evidence)
    return state


def poll(job, binding=None, collect=False):
    if binding and binding['endpoint'] != (job['host'] or 'local'):
        return dict(state='identity_changed', qualification='inconclusive', reason='endpoint changed')
    preamble = 'import base64,hashlib,json,os,socket\nfrom pathlib import Path\n'
    code = preamble + '\n'.join(inspect.getsource(f) for f in (read_process, capture, evaluate, intake, remote_probe))
    code += '\nprint(json.dumps(remote_probe(' + repr(job) + ',' + repr(binding) + ',' + repr(collect) + ')))\n'
    cmd = ['python3', '-'] if job['host'] is None else ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', job['host'], 'python3', '-']
    p = subprocess.run(cmd, input=code, capture_output=True, text=True, timeout=40)
    if p.returncode:
        raise RuntimeError(p.stderr[-1000:])
    return json.loads(p.stdout)


def write_new(path, value):
    with path.open('x') as f:
        f.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--control', type=Path, required=True)
    ap.add_argument('--spool', type=Path, required=True)
    ap.add_argument('--bind', action='store_true')
    ap.add_argument('--once', action='store_true')
    args = ap.parse_args()
    args.control.mkdir(exist_ok=True)
    args.spool.mkdir(exist_ok=True)
    if args.bind:
        bindings = {}
        for job in JOBS:
            data = poll(job)
            if data['state'] != 'binding_available':
                raise RuntimeError(f"Cannot bind {job['name']}: {data['state']}")
            bindings[job['name']] = dict(endpoint=job['host'] or 'local', roots=job['roots'], **data['snapshot'])
        write_new(args.control / 'bindings.json', bindings)
        print('Bound all scientific roots and discovered descendants')
        return
    bindings = json.loads((args.control / 'bindings.json').read_text())
    observed_path = args.control / 'observed.json'
    if observed_path.exists():
        bindings = json.loads(observed_path.read_text())
    alerts_path = args.control / 'identity_alerts.json'
    alerts = json.loads(alerts_path.read_text()) if alerts_path.exists() else {}
    while True:
        states = {}
        for job in JOBS:
            name = job['name']
            dest = args.spool / name
            if name in alerts:
                states[name] = alerts[name]
                continue
            if dest.exists():
                states[name] = dict(state='archive_present' if (dest / 'archive.json').exists() else 'partial_archive', qualification='unreviewed')
                continue
            try:
                data = poll(job, bindings[name], True)
            except Exception as exc:
                states[name] = dict(state='probe_error', qualification='inconclusive', error=str(exc))
                continue
            states[name] = {k: v for k, v in data.items() if k not in ('files', 'snapshot')}
            if data['state'] == 'identity_changed':
                # Never rebind a recycled PID to make it look like the old job.
                alerts[name] = states[name]
                continue
            for pid, p in data['snapshot']['processes'].items():
                bindings[name]['processes'].setdefault(pid, p)
            if data['state'] != 'terminal':
                continue
            dest.mkdir(exist_ok=False)
            mapping = {}
            for i, (source, item) in enumerate(data['files'].items()):
                raw = base64.b64decode(item['base64'])
                assert hashlib.sha256(raw).hexdigest() == item['sha256']
                local = dest / f'{i:02d}_{Path(source).name}'
                with local.open('xb') as f:
                    f.write(raw)
                mapping[source] = dict(local_file=local.name, sha256=item['sha256'])
            write_new(dest / 'archive.json', dict(job=name, endpoint=job['host'] or 'local',
                      collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      raw_status=data['raw_status'], qualification=data['qualification'], files=mapping,
                      bound_host=bindings[name]['host'], monitored_processes=bindings[name]['processes'],
                      claim_boundary='Intake only; review source pins, exactness and SS/FF. Wrapper rc is not a scientific verdict. TP4 SU64 is not SU1024 product.'))
        for path, value in [(observed_path, bindings), (alerts_path, alerts), (args.control / 'state.json', dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), jobs=states))]:
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
            temp.replace(path)
        if args.once or all(v['state'] == 'archive_present' for v in states.values()):
            print(json.dumps(states, indent=2, sort_keys=True))
            return
        time.sleep(45)


if __name__ == '__main__':
    main()
