"""Exact recorded policy targets only; no inventory expansion, per-PID sleeps, or DELETE."""
import datetime
import glob
import json
import os
import pathlib
import re
import signal
import subprocess
import time


def targets(snapshot):
    found = {}
    for kind in ('units', 'docker', 'procs', 'stale'):
        for x in snapshot['inventory'].get(kind, []):
            if x.get('unit'):
                key, expected = ('unit', x['unit']), x.get('cg_inode')
            elif x.get('name'):
                key, expected = ('docker', x.get('id')), (x.get('id'), x.get('started_at'))
                if not x.get('id') or not x.get('started_at'):
                    expected = None
            elif x.get('pid'):
                key, expected = ('pid', int(x['pid'])), x.get('start_ticks')
            else:
                continue
            found[key] = dict(kind=key[0], id=key[1], expected=expected)
    return list(found.values())


def run_plan(records, identity, send, sleep=time.sleep, dry_run=False):
    eligible = [x for x in records if x['expected'] is not None and identity(x) == x['expected']]
    receipt = dict(recorded=len(records), eligible=eligible, refused=[x for x in records if x not in eligible], term=[], kill=[])
    if dry_run:
        return receipt
    send('TERM', eligible)
    receipt['term'] = eligible
    sleep(5)  # exactly one shared grace; no stop-wait or sleep per target
    alive = [x for x in eligible if identity(x) == x['expected']]
    send('KILL', alive)
    receipt['kill'] = alive
    return receipt


def execute(snapshot, dry_run=False):
    assert os.uname().nodename == 'ot-epyc6', 'wrong SSH machine'
    assert snapshot['inventory']['hostname'] == 'ot-epyc6'
    due = datetime.datetime.fromisoformat(snapshot['deadline']).timestamp()
    if not dry_run:
        assert time.time() >= due, 'before owner deadline'
        assert datetime.datetime.fromisoformat(snapshot['at']).timestamp() >= due, 'old partial snapshot'
    records = targets(snapshot)
    docker_ids = [x['id'] for x in records if x['kind'] == 'docker' and x['expected'] is not None]

    def docker_state():
        if not docker_ids:
            return {}
        r = subprocess.run(['docker', 'inspect', *docker_ids], capture_output=True, text=True, timeout=15)
        try:
            return {x['Id']: (x['Id'], x['State']['StartedAt']) for x in json.loads(r.stdout) if x['State']['Running']}
        except (ValueError, KeyError):
            return {}

    cache = docker_state()

    def identity(x):
        try:
            if x['kind'] == 'unit':
                assert re.fullmatch(r'oth-[\w.-]+', x['id'])
                hits = glob.glob('/sys/fs/cgroup/user.slice/user-*.slice/user@*.service/app.slice/'+x['id']+'.scope')
                return os.stat(hits[0]).st_ino if len(hits) == 1 and pathlib.Path(hits[0], 'cgroup.procs').read_text().strip() else None
            if x['kind'] == 'docker':
                return cache.get(x['id'])
            p = pathlib.Path('/proc')/str(x['id'])
            if p.stat().st_uid != os.getuid():
                return None
            return int((p/'stat').read_text().rsplit(')', 1)[1].split()[19])
        except (OSError, ValueError, IndexError):
            return None

    commands = []

    def send(sig, xs):
        units = [x['id']+'.scope' for x in xs if x['kind'] == 'unit']
        containers = [x['id'] for x in xs if x['kind'] == 'docker']
        if units:
            commands.append(subprocess.Popen(['systemctl', '--user', 'kill', '--signal='+sig, *units], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        if containers:
            commands.append(subprocess.Popen(['docker', 'kill', '--signal='+sig, *containers], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for x in xs:
            if x['kind'] == 'pid' and identity(x) == x['expected']:
                try:
                    os.kill(x['id'], getattr(signal, 'SIG'+sig))
                except ProcessLookupError:
                    pass

    def grace(seconds):
        nonlocal cache
        time.sleep(seconds)
        cache = docker_state()

    receipt = run_plan(records, identity, send, grace, dry_run)
    # Signal clients run concurrently; only our own client processes are bounded here.
    end = time.monotonic()+2
    while any(p.poll() is None for p in commands) and time.monotonic() < end:
        time.sleep(.02)
    receipt['signal_clients'] = []
    for p in commands:
        rc = p.poll()
        if rc is None:
            p.terminate()
        receipt['signal_clients'].append(dict(pid=p.pid, rc=rc, bounded_client=rc is None))
    receipt.update(at=datetime.datetime.now().astimezone().isoformat(), dry_run=dry_run, hostname=os.uname().nodename)
    return receipt
