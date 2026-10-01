#!/usr/bin/env python3
"""Pinned QC-NAM admission watcher: release existing waiter, never launch a lane.

Every check and release response is written to a new immutable event file.
Provenance/identity failures stop the watcher; disk pressure or running greedy
keep the hold. This tool never invokes the QC finalizer or changes gate rules.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import qcnam_finalize_guard as G


def disposition(check):
    if check.get('released'):
        return 'released'
    if check.get('error') or not check.get('held'):
        return 'blocked'
    if check.get('ready_to_release'):
        return 'ready'
    waiter = check.get('greedy_waiter', {})
    if waiter.get('state') == 'Z' and waiter.get('exit_code') != 0:
        return 'blocked'
    allowed = {'greedy waiter has not exited successfully', 'available root disk below long admission budget'}
    reasons = check.get('reasons', [])
    return 'wait' if reasons and set(reasons) <= allowed else 'blocked'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--observation', type=Path, required=True)
    ap.add_argument('--events', type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.events.mkdir(parents=True, exist_ok=True)
    identity = {p.name: G.digest(p) for p in Path(__file__).parent.glob('qcnam*.py')}
    observation_sha = G.digest(args.observation)
    hold_path = Path('/tmp/claude-1000/qcnam/long-admission-hold.json')
    hold_sha = G.digest(hold_path)

    def record(kind, data):
        event = dict(kind=kind, utc_ns=time.time_ns(), watcher_source_commit=args.source_commit,
                     watcher_source_sha256=identity, observation_sha256=observation_sha,
                     hold_sha256=hold_sha, data=data)
        p = args.events / f"{event['utc_ns']}_{kind}.json"
        with p.open('x') as f:
            json.dump(event, f, indent=2)
            f.write('\n')

    def pinned():
        head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip()
        G.require(head == args.source_commit and not dirty, 'watcher checkout must remain clean at its source pin')
        G.require(identity == {p.name: G.digest(p) for p in Path(__file__).parent.glob('qcnam*.py')}, 'watcher source changed')
        G.require(G.digest(args.observation) == observation_sha and G.digest(hold_path) == hold_sha,
                  'observation or original hold identity changed')

    def check(release=False):
        pinned()
        command = ['python3', str(root / 'tools/qcnam_long_admission.py'), '--observation', str(args.observation)]
        if release:
            command.append('--release')
        p = subprocess.run(command, cwd=root, capture_output=True, text=True)
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            data = dict(error='admission checker returned invalid output', returncode=p.returncode,
                        stdout=p.stdout, stderr=p.stderr)
        record('release_attempt' if release else 'readiness', data)
        return data

    record('started', dict(pid=os.getpid(), start_ticks=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]))
    while True:
        try:
            data = check()
            state = disposition(data)
            if state == 'ready':
                data = check(release=True)
                state = disposition(data)
            if state == 'released':
                time.sleep(5)
                record('post_release_handles', dict(live=G.active_jobs(),
                       gen_status=(G.RUNS / 'gen/status').read_text(),
                       long_status=(G.RUNS / 'long/status').read_text() if (G.RUNS / 'long/status').exists() else None,
                       available_bytes=os.statvfs(G.RUNS).f_bavail * os.statvfs(G.RUNS).f_frsize,
                       finalized=False, adopted=False))
                return 0
            if state == 'blocked':
                record('blocked', data)
                return 2
        except (OSError, ValueError, KeyError) as exc:
            record('blocked', dict(error=str(exc), released=False))
            return 2
        time.sleep(60)


if __name__ == '__main__':
    raise SystemExit(main())
