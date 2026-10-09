#!/usr/bin/env python3
"""Evacuate explicitly named terminal localhost jobs while preserving full checkpoints.

Run only for the owner-authorized localhost retirement. No surviving process is
stopped. Source/configuration snapshots and completed ORFS objects retain paths
and mtimes through a remote NVMe-backed alias. Normal fleet admission controls
subsequent compute; this tool performs transfer and remote make dry-run only.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

# Use the active coordinator helpers, including newer deployed flow fixes.
sys.path.insert(0, os.environ.get('CL_CODE_ROOT', '/home/ubuntu/OpenTallas/tools/closure_loop'))
import closure_loop as cl
from ssh_transport import command


def verify_terminal(j):
    if j.get('host') != 'localhost' or j.get('status') not in ('READY', 'NEEDS_HUMAN'):
        raise RuntimeError('requires terminal/retry-ready localhost state')
    run = Path(j['run'])
    if run.parent != Path(cl.host_cfg('localhost')['base']):
        raise RuntimeError('run is outside retired localhost inventory')
    observations = []
    for p in (run / 'cl').glob('*.pid'):
        pid = int(p.read_text().strip())
        proc = Path('/proc') / str(pid) / 'cmdline'
        if proc.exists() and str(run) in proc.read_bytes().decode(errors='replace').replace('\x00', ' '):
            raise RuntimeError(f'producer survives: {pid} ({p.name})')
        observations.append({'pid_file': str(p), 'pid': pid, 'matching_process': False})
    r = subprocess.run(['docker', 'ps', '-q'], check=True, capture_output=True, text=True)
    ids = r.stdout.split()
    if ids:
        containers = subprocess.run(['docker', 'inspect', *ids], check=True, capture_output=True, text=True)
        for c in json.loads(containers.stdout):
            if any(str(run) in m.get('Source', '') for m in c.get('Mounts', [])):
                raise RuntimeError(f'container survives: {c["Id"]}')
    return observations


def recover(name, host):
    if cl.is_local(host):
        raise RuntimeError('destination must be remote')
    with cl.job_lock(name):
        j = cl.load_job(name)
        observations = verify_terminal(j)
        fleet = cl.Fleet()
        ok, reason = fleet.fits(host, j['spec'].get('threads', 16), j['spec'].get('peak_ram_gb', 32), job=name)
        if not ok:
            raise RuntimeError(f'admission refused: {reason}')
        if not fleet.compatible(host, j['spec']):
            raise RuntimeError('destination toolchain is incompatible')
        run = j['run']
        actual = cl.host_cfg(host)['base'] + '/' + name
        archive = cl.STATE / 'localhost_evacuations' / name
        archive.mkdir(parents=True, exist_ok=True)
        original = cl.jpath(name).read_bytes()
        if (archive / 'state_before.json').exists():
            raise RuntimeError('explicit evacuation already attempted; inspect preserved attempt')
        (archive / 'state_before.json').write_bytes(original)
        (archive / 'terminal_handles.json').write_text(json.dumps(observations, indent=2) + '\n')
        j.update(status='MIGRATING', wait=None)
        cl.event(j, f'owner-authorized terminal localhost evacuation to {host}; no surviving producer stopped')
        cl.save_job(j)
        try:
            # Preserve absolute generated-Makefile paths while locating bulk data on NVMe.
            setup = ('set -eu; '
                     f'test ! -e {shlex.quote(actual)}; test ! -e {shlex.quote(run)}; '
                     f'mkdir -p {shlex.quote(actual)} {shlex.quote(str(Path(run).parent))}; '
                     f'ln -s {shlex.quote(actual)} {shlex.quote(run)}')
            cl.ssh(host, setup, check=True)
            with ExitStack() as stack:
                prefixes = {h: stack.enter_context(command(h)) for h in ('localhost', host)}
                read = shlex.join(prefixes['localhost'] + [f'tar -C {shlex.quote(run)} -cf - .'])
                write = shlex.join(prefixes[host] + [f'tar -C {shlex.quote(actual)} -xf -'])
                transfer = subprocess.run(['bash', '-o', 'pipefail', '-c', read + ' | ' + write],
                                          capture_output=True, text=True)
            if transfer.returncode:
                raise RuntimeError('checkpoint transfer failed: ' + transfer.stderr[-800:])
            cl.ship_helpers(host, run)
            cl.ssh(host, f'python3 {shlex.quote(run)}/cl/resume_patch.py {shlex.quote(run)}/src', check=True)
            stl = cl.stage_list(j['spec'])
            st = stl[j.get('stage_idx', 0)]
            if st['kind'] == 'calibrate':
                base = cl.subst(j['spec']['stages']['calibrate']['base'], j)
                locate = f'ls -d {base} | tail -1'
            else:
                dm = cl.subst(j['spec']['verdict']['drc_metrics'], j)
                base = dm.split('/logs/')[0] + '/results/asap7/*/base'
                locate = f'ls -d {base} | tail -1'
            # Inventory and make -n are remote metadata checks, not resumed compute.
            dry = cl.ssh(host, f'''set -eu
B=$({locate}); O=${{B%/results/*}}
test -n "$(find "$B" -maxdepth 1 -name '*.odb' -print -quit)"
docker run --rm -v {shlex.quote(run)}/src:/src:ro -v "$O":/work -w /OpenROAD-flow-scripts/flow {cl.LOCAL_ORFS_REF} bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish'
''', timeout=600)
            (archive / 'next_stage_dryrun.txt').write_text(dry.stdout + dry.stderr)
            if dry.returncode:
                raise RuntimeError('remote preserved-checkpoint make dry-run failed')
            stages = sorted(set(re.findall(r'do-([0-9]_[0-9]_[a-z_]+)', dry.stdout)))
            if not stages:
                raise RuntimeError('no executable stage in dry-run; separate final-state review required')
            j['resume'] = dict(from_host='localhost', to_host=host, run=run,
                               physical_run=actual, at=cl.now_iso(), checkpoint_transfer_verified=True,
                               next_stage_dryrun=dict(host=host, run=run, stages=stages,
                                                     owner_review='resume unfinished stages after verified terminal owner kill'))
            j['checkpoint_affinity'] = dict(host=host, run=run)
            j.setdefault('hosts_tried', []).append(host)
            j.update(host=host, status='READY', attempt=j.get('attempt', 1) + 1,
                     retries_used=0, errors=[], wait=None)
            cl.event(j, f'full localhost checkpoint preserved on {host} NVMe {actual}; remote next stages {stages}')
            cl.save_job(j)
            receipt = dict(name=name, source_spec=j['spec'], from_host='localhost', to_host=host,
                           state_before_sha256=hashlib.sha256(original).hexdigest(), run=run,
                           physical_run=actual, next_stages=stages, status='READY', at=cl.now_iso())
            (archive / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
            print(json.dumps(receipt))
        except Exception as exc:
            j.update(status='NEEDS_HUMAN', reason=f'checkpoint evacuation: {exc}')
            cl.event(j, j['reason'])
            cl.save_job(j)
            raise


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('name')
    ap.add_argument('host')
    args = ap.parse_args()
    recover(args.name, args.host)
