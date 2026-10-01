#!/usr/bin/env python3
"""Inspect an existing QC long admission hold; release only with explicit --release.

The hold stops only the outer laneA waiter. Greedy generation and MMLU continue.
No job is launched or restarted. Original source/scripts and gate stay unchanged.
"""
import argparse
import json
import os
from pathlib import Path
import signal

import qcnam_finalize_guard as G

HOLD = Path('/tmp/claude-1000/qcnam/long-admission-hold.json')
LANE = str(G.JOBS / 'laneA.sh')


def proc(pid):
    p = Path('/proc') / str(pid)
    fields = p.joinpath('stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, state=fields[0], ppid=int(fields[1]), start_ticks=fields[19],
                exit_code=int(fields[49]), argv=p.joinpath('cmdline').read_bytes().decode().split('\0')[:-1])


def verify_supervisor(p, hold):
    G.require(p['pid'] == hold['supervisor_pid'] and p['start_ticks'] == hold['supervisor_start_ticks'],
              'supervisor PID identity changed; inspect namespace, never restart')
    G.require(p['argv'] == ['/bin/bash', LANE] and p['state'] in ('T', 't'), 'supervisor is not the held laneA waiter')


def verify_finished_waiter(p, hold):
    G.require(p['pid'] == hold['greedy_waiter_pid'] and p['start_ticks'] == hold['greedy_waiter_start_ticks']
              and p['ppid'] == hold['supervisor_pid'], 'greedy waiter identity changed')
    G.require(p['state'] == 'Z' and p['exit_code'] == 0, 'greedy waiter has not exited successfully')


def budget(core_cp, mmlu_cp, mmlu_live, margin=4 * 2**30):
    hidden = (4 * 8192 + 8 * 256) * 4 * 5120 * 2 * 4 * 2
    checkpoint = max(core_cp, mmlu_cp)
    overlap = mmlu_cp if mmlu_live else 0
    return dict(long_hidden_bytes=hidden, hypothetical_long_checkpoint_bytes=checkpoint,
                checkpoint_and_atomic_temporary_bytes=2 * checkpoint, mmlu_temporary_overlap_bytes=overlap,
                growth_margin_bytes=margin, required_available_bytes=hidden + 2 * checkpoint + overlap + margin,
                limitation='Planning budget based on observed checkpoint sizes, not a proven upper bound for long. '
                           'Continue disk watch after admission; growth margin is a resource reserve, not a numerical gate.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--observation', type=Path, required=True)
    ap.add_argument('--release', action='store_true', help='SIGCONT existing waiter only after every admission check passes')
    args = ap.parse_args()
    hold = json.loads(HOLD.read_text())
    observation = json.loads(args.observation.read_text())
    G.require(G.source_identity() == observation['source_sha256'], 'pinned source changed')
    G.require(G.snapshot_identity() == observation['snapshot_identity'], 'snapshot changed')
    G.require({p.name: G.digest(p) for p in G.JOBS.glob('*.sh')} == observation['job_sha256'], 'original scripts changed')
    supervisor = proc(hold['supervisor_pid'])
    verify_supervisor(supervisor, hold)
    G.require(not (G.RUNS / 'long').exists(), 'long has entered; do not signal or restart')
    G.require({f: G.digest(G.RUNS / 'core' / f) for f in hold['core_output_sha256']} == hold['core_output_sha256'],
              'completed core output changed')
    G.completed(G.RUNS / 'core')
    waiter = proc(hold['greedy_waiter_pid'])
    reasons = []
    try:
        verify_finished_waiter(waiter, hold)
        gen = json.loads((G.RUNS / 'gen/gen.json').read_text())
        G.validate_gen(gen)
        G.require(any(l.startswith('done ') for l in (G.RUNS / 'gen/log.txt').read_text().splitlines()),
                  'greedy completion marker absent')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        reasons.append(str(exc))
    live = G.active_jobs()
    mmlu_live = any(str(G.RUNS / 'mmlu1000/work') in r['argv'] for r in live)
    core_cp = (G.RUNS / 'core/work/checkpoint.pt').stat().st_size
    mmlu_cp = (G.RUNS / 'mmlu1000/work/checkpoint.pt').stat().st_size
    admission = budget(core_cp, mmlu_cp, mmlu_live)
    v = os.statvfs(G.RUNS)
    available = v.f_bavail * v.f_frsize
    if available < admission['required_available_bytes']:
        reasons.append('available root disk below long admission budget')
    report = dict(held=True, ready_to_release=not reasons, released=False, supervisor=supervisor,
                  greedy_waiter=waiter, live=live, available_bytes=available, admission=admission, reasons=reasons)
    if args.release and not reasons:
        # A pidfd binds the signal to this process, not a reused numeric PID.
        fd = os.pidfd_open(hold['supervisor_pid'])
        try:
            verify_supervisor(proc(hold['supervisor_pid']), hold)
            verify_finished_waiter(proc(hold['greedy_waiter_pid']), hold)
            G.require(not (G.RUNS / 'long').exists(), 'long entered during admission')
            v = os.statvfs(G.RUNS)
            G.require(v.f_bavail * v.f_frsize >= admission['required_available_bytes'], 'disk fell below admission budget')
            signal.pidfd_send_signal(fd, signal.SIGCONT)
        finally:
            os.close(fd)
        report.update(held=False, released=True)
    print(json.dumps(report, indent=2))
    return 0 if not reasons else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps(dict(held=None, ready_to_release=False, released=False, error=str(exc))))
        raise SystemExit(2)
