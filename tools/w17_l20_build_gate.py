#!/usr/bin/env python3
"""W17: adopt completed rank builds, retry missing ranks serially, certify archives.

Never trusts the original unchecked BUILT marker. Each invocation owns a new
attempt directory; original scripts, logs and build directories stay untouched.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

DRIVER_OLD_SHA256 = 'b011388e2aedbd1ccf4edfe9af1d0e2f210b44f357a76dbed3612f395a0a64c7'
DRIVER_NEW_SHA256 = 'be2384333d37e8b2c923bfe27d324a013be4baebcba751b57cf342533160eda6'
DRIVER_DIFF_SHA256 = '11ebc2f878886ebb45c6ae153c1801f4a7f62720f78dda5e7609d5c925c307b6'


def driver_identity(expected, actual):
    """Only the original driver or its reviewed source-coverage fix may run."""
    allowed = {(DRIVER_OLD_SHA256, DRIVER_OLD_SHA256),
               (DRIVER_OLD_SHA256, DRIVER_NEW_SHA256),
               (DRIVER_NEW_SHA256, DRIVER_NEW_SHA256)}
    if (expected, actual) not in allowed:
        raise ValueError(f'unattested driver identity: expected={expected}, actual={actual}')
    return dict(expected_sha256=expected, actual_sha256=actual,
                original_commit='a8c660b2', fixed_commit='b65a087a',
                reviewed_source_diff_sha256=DRIVER_DIFF_SHA256,
                uses_attested_source_coverage_fix=actual == DRIVER_NEW_SHA256)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def live_builds(work):
    """Inspect actual command lines and cwd, excluding this supervisor."""
    found = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            args = [a.decode(errors='replace') for a in args if a]
            if not args or int(proc.name) == os.getpid():
                continue
            name = Path(args[0]).name
            cwd = (proc / 'cwd').resolve()
            compiler = name in ('make', 'gmake', 'g++', 'cc1plus', 'as', 'ar', 'verilator', 'verilator_bin', 'time')
            driver = any(Path(a).name == 'v41_die_rt.py' for a in args) and 'build' in args
            under_work = cwd == work or work in cwd.parents
            targets_work = any(a == str(work) or a.startswith(str(work) + '/') for a in args)
            if (compiler and (under_work or targets_work)) or (driver and targets_work):
                found.append(dict(pid=int(proc.name), argv=args))
        except (OSError, ValueError):
            continue
    return found


def archive_info(path, rank):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'missing/empty rank {rank} archive: {path}')
    members = subprocess.check_output(['ar', 't', str(path)], text=True).splitlines()
    if not members or not any(m.startswith(f'Vdie{rank}') for m in members):
        raise ValueError(f'wrong/empty rank {rank} archive: {path}')
    subprocess.run(['ar', 'p', str(path)], stdout=subprocess.DEVNULL, check=True)
    first = subprocess.check_output(['ar', 'p', str(path), members[0]])
    if not first.startswith(b'\x7fELF'):
        raise ValueError(f'non-ELF rank {rank} archive: {path}')
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size, members=len(members))


def adopted_rank(work, rank):
    # The original driver's stdout is only emitted on success and contains
    # every child exit code. A valid archive alone does not certify a build.
    log = Path(f'{work}.b{rank}.log')
    data = json.loads(log.read_text())
    steps = data.get('steps', [])
    required = {f'verilate_die{rank}.log', f'build_die{rank}.log'}
    if not required <= {s.get('log') for s in steps} or any(s.get('returncode') != 0 for s in steps):
        raise ValueError(f'rank {rank} lacks successful elaboration and make statuses')
    for name in required:
        text = (work / name).read_text()
        if 'Exit status: 0' not in text:
            raise ValueError(f'rank {rank} child log lacks exit 0: {name}')
    return dict(returncode=0, provenance='original driver child statuses',
                driver_log_sha256=sha(log), archive=archive_info(work / f'die{rank}/Vdie{rank}__ALL.a', rank))


def resources(work):
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    return dict(mem_available_kib=int(mem['MemAvailable'].split()[0]),
                load1=os.getloadavg()[0], free_disk_bytes=shutil.disk_usage(work).free)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--adopt-work', type=Path, required=True)
    p.add_argument('--attempt', type=Path, required=True)
    p.add_argument('--original-script', type=Path, required=True)
    p.add_argument('--expected-source-pins', type=Path, required=True)
    p.add_argument('--retry-ranks', default='2')
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--min-memory-gib', type=int, default=100)
    p.add_argument('--min-disk-gib', type=int, default=30)
    p.add_argument('--max-load', type=float, default=28)
    p.add_argument('--poll-seconds', type=float, default=30)
    p.add_argument('--deadline-seconds', type=float, default=86400)
    a = p.parse_args()
    a.source = a.source.resolve(); a.adopt_work = a.adopt_work.resolve()
    a.attempt.mkdir(parents=True, exist_ok=False)
    a.attempt = a.attempt.resolve()
    # One supervisor for this live build group; flock never kills its holder.
    lock = (a.adopt_work / '.w17-l20-gate.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    rec = dict(schema='opentallas.rtl.w17_l20_build_gate.v1', status='FAIL', ranks={},
               original_script_sha256=sha(a.original_script),
               script_sha256=sha(Path(__file__)), claim_boundary='Four L20 die archives only; no RTL exactness or SS/FF closure claim.')
    shutil.copyfile(a.original_script, a.attempt / 'original_l20build.sh')
    shutil.copyfile(a.expected_source_pins, a.attempt / 'expected_source_pins.json')
    failure_log = Path(f'{a.adopt_work}.b2.log')
    if failure_log.exists():
        shutil.copyfile(failure_log, a.attempt / 'original_rank2.driver.log')
    failure_log = a.adopt_work / 'verilate_die2.log'
    if failure_log.exists():
        shutil.copyfile(failure_log, a.attempt / 'original_rank2.verilate.log')
    started = time.monotonic()

    def event(state, **extra):
        with (a.attempt / 'events.jsonl').open('a') as f:
            f.write(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), state=state, **extra)) + '\n')

    def check_deadline():
        if time.monotonic() - started > a.deadline_seconds:
            raise TimeoutError('admission deadline expired; no live jobs killed')

    try:
        retry = {int(r) for r in a.retry_ranks.split(',')}
        if not retry <= set(range(4)) or a.jobs < 1:
            raise ValueError('invalid retry ranks/jobs')
        pins = json.loads(a.expected_source_pins.read_text())
        # Bind the actual executable driver, with exactly one reviewed exception
        # for the source-coverage-only a8c660b2 -> b65a087a diff.
        rec['driver_identity'] = driver_identity(pins['tools/v41_die_rt.py'],
                                                  sha(a.source / 'tools/v41_die_rt.py'))
        for name, h in pins.items():
            if name != 'tools/v41_die_rt.py' and sha(a.source / name) != h:
                raise ValueError(f'RTL/source mismatch; cannot mix rank archives: {name}')
        rec['source_commit'] = subprocess.check_output(['git', '-C', str(a.source), 'rev-parse', 'HEAD'], text=True).strip()
        if subprocess.check_output(['git', '-C', str(a.source), 'status', '--porcelain'], text=True).strip():
            raise ValueError('retry source worktree is dirty')
        rec['source_sha256'] = {name: sha(a.source / name) for name in pins}
        while True:
            live = live_builds(a.adopt_work)
            if not live:
                break
            event('WAIT_LIVE_RANKS', processes=live)
            check_deadline(); time.sleep(a.poll_seconds)
        for rank in sorted(set(range(4)) - retry):
            rec['ranks'][str(rank)] = adopted_rank(a.adopt_work, rank)
        event('PEER_RANKS_VERIFIED')
        for rank in sorted(retry):
            while True:
                live = live_builds(a.adopt_work)
                r = resources(a.attempt)
                if not live and r['mem_available_kib'] >= a.min_memory_gib * 1024**2 and r['free_disk_bytes'] >= a.min_disk_gib * 1024**3 and r['load1'] <= a.max_load:
                    break
                event('WAIT_RESOURCES', resources=r, processes=live)
                check_deadline(); time.sleep(a.poll_seconds)
            # Recheck source cleanliness at admission after potentially long waits.
            if subprocess.check_output(['git', '-C', str(a.source), 'status', '--porcelain'], text=True).strip():
                raise ValueError('source changed while waiting')
            if subprocess.check_output(['git', '-C', str(a.source), 'rev-parse', 'HEAD'], text=True).strip() != rec['source_commit']:
                raise ValueError('source commit changed while waiting')
            if any(sha(a.source / name) != h for name, h in rec['source_sha256'].items()):
                raise ValueError('pinned source changed while waiting')
            event('ADMIT_RANK', rank=rank, resources=r)
            cmd = ['python3', str(a.source / 'tools/v41_die_rt.py'), 'build', '--l20',
                   '--work', str(a.attempt / 'build'), '--only', f'die{rank}', '--jobs', str(a.jobs)]
            log = a.attempt / f'rank{rank}.driver.log'
            with log.open('x') as f:
                child = subprocess.Popen(cmd, cwd=a.source, stdout=f, stderr=subprocess.STDOUT)
                event('RANK_STARTED', rank=rank, pid=child.pid, argv=cmd)
                rc = child.wait()  # check this child's status, never an unchecked wait
            rec['ranks'][str(rank)] = dict(returncode=rc, driver_log_sha256=sha(log))
            if rc:
                raise RuntimeError(f'rank {rank} build failed: exit {rc}')
            data = json.loads(log.read_text())
            if len(data['steps']) != 2 or any(s['returncode'] != 0 for s in data['steps']):
                raise ValueError(f'rank {rank} child status verification failed')
            rec['ranks'][str(rank)]['archive'] = archive_info(a.attempt / f'build/die{rank}/Vdie{rank}__ALL.a', rank)
        # Verify all four again immediately before issuing the new certificate.
        for rank in range(4):
            info = rec['ranks'][str(rank)]['archive']
            if archive_info(Path(info['path']), rank)['sha256'] != info['sha256']:
                raise ValueError(f'rank {rank} archive changed during gate')
        rec['status'] = 'PASS'
    except Exception as e:
        rec['error'] = f'{type(e).__name__}: {e}'
    rec['wall_s'] = round(time.monotonic() - started, 1)
    result = a.attempt / 'result.json'
    with result.open('x') as f:
        f.write(json.dumps(rec, indent=1) + '\n')
    if rec['status'] == 'PASS':
        with (a.attempt / 'BUILT').open('x') as f:
            f.write(f'PASS result.json sha256={sha(result)}\n')
    event('TERMINAL', status=rec['status'])
    return 0 if rec['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
