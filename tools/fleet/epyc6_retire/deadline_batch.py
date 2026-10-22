"""Operational supplement: existing enforcer owns snapshot/metadata/final copy; this only stops recorded jobs promptly."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import runpy
import subprocess
import time


def durable(path):
    with path.open('rb') as f:
        os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--wait', action='store_true')
    a = ap.parse_args()
    here = pathlib.Path(__file__).resolve().parent
    m = runpy.run_path(str(here/'epyc6_retire.py'), run_name='deadline_batch_parent')
    state = pathlib.Path(m['STATE'])
    worker = (here/'remote_deadline_batch.py').read_text()
    until = time.monotonic()+1200
    while not a.dry_run:
        now = datetime.datetime.now().astimezone()
        path = state/'deadline_partial_snapshot.json'
        if now >= m['DEADLINE'] and path.exists():
            snapshot = json.loads(path.read_text())
            if datetime.datetime.fromisoformat(snapshot['at']) >= m['DEADLINE']:
                break
        if not a.wait or time.monotonic() >= until:
            raise SystemExit('no verified durable deadline snapshot; no signals')
        time.sleep(1)
    if not a.dry_run:
        durable(path)
    ok, identity = m['verify_identity']()
    assert ok, identity
    if a.dry_run:
        inventory = m['host_py']('remote_host_state.py', timeout=120)
        snapshot = dict(at=m['now'](), deadline=m['DEADLINE'].isoformat(), inventory=inventory, identity=identity)
    assert snapshot['identity'] == identity, 'snapshot identity differs from current provider/SSH identity'
    arm = dict(at=m['now'](), mode='dry-run' if a.dry_run else 'deadline', identity=identity,
               snapshot_at=snapshot['at'], worker_sha=hashlib.sha256(worker.encode()).hexdigest(), delete=False)
    m['jsave'](str(state/'batch_arm_receipt.json'), arm)
    durable(state/'batch_arm_receipt.json')
    code = worker+'\nprint(json.dumps(execute(json.loads('+repr(json.dumps(snapshot))+'), dry_run='+repr(a.dry_run)+')))\n'
    r = subprocess.run(m['SSH_H']+[m['HOST'], 'python3', '-'], input=code, capture_output=True, text=True, timeout=90)
    receipt = dict(arm=arm, rc=r.returncode, stdout=r.stdout, stderr=r.stderr)
    m['jsave'](str(state/('batch_dry_run.json' if a.dry_run else 'batch_deadline_result.json')), receipt)
    print(json.dumps(receipt), flush=True)
    assert r.returncode == 0


if __name__ == '__main__':
    main()
