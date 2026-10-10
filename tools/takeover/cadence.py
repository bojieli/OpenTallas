#!/usr/bin/env python3
"""Queue owner-authorized closure drives into the existing takeover session."""
import argparse
import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('/home/ubuntu/codex-takeover-20261010')
HANDOFF = Path('/home/ubuntu/claude-takeover-20261007')
THREAD = '01a125a7-3957-71d1-8206-888977e691ff'
STREAMS = ('bf-arch', 'bf-pinclk', 'hbm-forks', 'hgi-takeover',
           'hgi-adapters', 'hgi-e2e', 'vm8-seam', 'redesign-hbm', 'hbm-sim',
           'kv-die', 'redesign-qwen', 'redesign-ds', 'cont-takeover',
           'sys-takeover', 's81-gen', 'die-evidence-2', 'mtp-lead',
           'struct-close', 'reprice')


def tick(kind, dry_run=False):
    ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    record = {'time': now, 'kind': kind}
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/elements', timeout=60) as response:
            registry = json.load(response)
        path = ROOT / f'registry-{stamp}-{kind}.json'
        path.write_text(json.dumps(registry, indent=2) + '\n')
        record['registry_snapshot'] = str(path)
    except Exception as error:
        record['registry_error'] = str(error)
    if kind == 'review':
        collect = {}
        for stream in STREAMS:
            path = HANDOFF / (stream + '.log')
            if path.exists():
                content = path.read_text(errors='replace')
                lines = content.splitlines()
                starts = [i for i, line in enumerate(lines) if 'COLLECT' in line]
                collect[stream] = {'modified_utc': datetime.datetime.fromtimestamp(
                    path.stat().st_mtime, datetime.timezone.utc).isoformat(),
                    'tail_from_latest_collect': '\n'.join(lines[starts[-1]:] if starts else lines[-80:])}
        path = ROOT / f'collect-{stamp}.json'
        path.write_text(json.dumps(collect, indent=2) + '\n')
        record['collect_snapshot'] = str(path)
    task = {
        'drive': 'Run python3 /home/ubuntu/claude-takeover-20261007/gaps/registry_gaps.py now. Reconcile every IDLE element against assigned stream owners and give each a concrete action. Collect bench-verified closures and merge/push immediately from central main; service closures require independent sb4 PASS. Continue engineering and admitted jobs; preserve progressing work. Check BF full rate and report material changes to owner.',
        'review': 'Perform the owner-authorized hourly review now: fleet CPU/RAM/disk headroom; latest authoritative COLLECT in every stream; resume work without progress for >2h. Run /home/ubuntu/codex-takeover-20261010/fleet_review.py --apply if installed, inspect its results. Retire stale >48h actual compute and idle scratch with .keep/live-use/source/evidence protections. Never git in another agent worktree. Continue all targets; resource guard every large launch.',
        'deadline': 'BF deadline report is due before 09:30 PT today. Inspect BF first-pass re-STA, exact bench and closure adoption evidence now; give owner current final status and measured costs in this chat immediately. Full 1.2GHz is preferred; 900MHz needs owner decision; HALF_PHL fallback remains closed. Continue engineering afterwards.',
    }[kind]
    message = f'[Codex takeover scheduled {kind}, {now}] {task} Snapshot: {record.get("registry_snapshot", "registry unavailable")}. This is a cadence reminder within the existing active goal, not a new task.'
    if not dry_run:
        result = subprocess.run(['/home/ubuntu/.local/bin/codex', 'queue', '--thread', THREAD,
                                 '--message', message], capture_output=True, text=True)
        record.update(queue_rc=result.returncode, queue_output=result.stdout.strip(),
                      queue_error=result.stderr.strip())
    else:
        record['dry_run'] = True
    with (ROOT / 'cadence.jsonl').open('a') as output:
        output.write(json.dumps(record) + '\n')
    print(json.dumps(record))
    return record.get('queue_rc', 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('drive', 'review', 'deadline'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / f'cadence-{args.kind}.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(0)
        raise SystemExit(tick(args.kind, args.dry_run))
