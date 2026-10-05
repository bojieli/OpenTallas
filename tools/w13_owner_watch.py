#!/usr/bin/env python3
"""Poll W13 global ownership; hold only the authorized waiting supervisor on conflict."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import signal
import time


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        return {'pid': pid, 'start_ticks': fields[19], 'state': fields[0]}
    except FileNotFoundError:
        return None


def conflicts(coord, proc_root=Path('/proc')):
    authorized = coord['active_successor']
    issues = []
    current = identity(authorized['pid'])
    if not current or current['start_ticks'] != authorized['start_ticks'] or current['state'] == 'Z':
        issues.append({'reason': 'authorized_supervisor_absent_or_reused', 'identity': current})
    for old in coord.get('parked_predecessors', []):
        handle = identity(old['pid'])
        if not handle or handle['start_ticks'] != old['start_ticks'] or handle['state'] not in ('T', 't'):
            issues.append({'reason': 'parked_predecessor_changed_or_resumed', 'expected': old, 'identity': handle})
    for process in proc_root.iterdir():
        if not process.name.isdigit():
            continue
        try:
            args = (process / 'cmdline').read_bytes().split(b'\0')
        except OSError:
            continue
        if not any(arg.endswith(b'/w13_chain_successor.py') for arg in args):
            continue
        handle = identity(int(process.name))
        if handle and handle['state'] not in ('T', 't', 'Z') and handle['pid'] != authorized['pid']:
            issues.append({'reason': 'other_runnable_supervisor', 'identity': handle, 'argv': [a.decode(errors='replace') for a in args if a]})
    return issues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coordination', type=Path, required=True)
    p.add_argument('--takeover-key', required=True)
    p.add_argument('--events', type=Path, required=True)
    p.add_argument('--once', action='store_true')
    a = p.parse_args()
    with Path(str(a.events) + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            coord = json.loads(a.coordination.read_text())
            if coord['takeover_key'] != a.takeover_key:
                status, issues = 'OWNER_CHANGED_MONITOR_EXIT', []
            else:
                issues = conflicts(coord)
                status = 'CONFLICT' if issues else 'EXCLUSIVE'
            record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': status,
                      'active_successor': coord.get('active_successor'), 'issues': issues}
            if issues:
                handle = coord['active_successor']
                current = identity(handle['pid'])
                if current and current['start_ticks'] == handle['start_ticks'] and current['state'] not in ('T', 't', 'Z'):
                    # Hold the dispatcher only. Existing remote work and unowned supervisors are untouched.
                    fd = os.pidfd_open(handle['pid'])
                    try:
                        fresh = identity(handle['pid'])
                        if fresh and fresh['start_ticks'] == handle['start_ticks']:
                            signal.pidfd_send_signal(fd, signal.SIGSTOP)
                            record['action'] = 'authorized_supervisor_only_SIGSTOP'
                    finally:
                        os.close(fd)
            with a.events.open('a') as log:
                log.write(json.dumps(record, sort_keys=True) + '\n')
                log.flush()
                os.fsync(log.fileno())
            if status != 'EXCLUSIVE' or a.once:
                return 0 if status == 'EXCLUSIVE' else 1
            time.sleep(10)


if __name__ == '__main__':
    raise SystemExit(main())
