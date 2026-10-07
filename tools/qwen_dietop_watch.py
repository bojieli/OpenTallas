#!/usr/bin/env python3
"""One-shot, read-only observer for legacy Qwen die cases (run on the Docker host).

Print JSON to stdout; redirect to a NEW evidence file. Never starts, stops, waits
for or removes containers. Never substitutes a same-name container for --container.
Legacy writable inputs cannot be certified retroactively by this observer. Its
physical observations are not source acceptance or permission to launch PDN/GRT.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

INPUTS = ('manifest.json', 'run.tcl', 'run_pdn.tcl', 'die.v', 'elements.lef',
          'phy_ew.lef', 'snap.tcl', 'place.tcl', 'pdn.tcl')
BLOCKERS = [
    'No launch-time immutable input/source binding for this legacy case',
    'Real qfd_rly implementation netlists and matching closed LEF/lib views missing',
    'Same-RTL east-seam pin-plan reroute and matching real views unverified',
]


def command(argv):
    p = subprocess.run(argv, text=True, capture_output=True)
    return dict(argv=argv, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inspect(cid):
    result = command(['docker', 'inspect', cid])
    if result['returncode']:
        return None, result
    data = json.loads(result['stdout'])[0]
    # Capture relevant execution identity, without unrelated environment secrets.
    selected = {k: data[k] for k in ('Id', 'Name', 'Image', 'Created', 'State', 'Mounts')}
    selected['command'] = data['Config']['Cmd']
    selected['limits'] = {k: data['HostConfig'].get(k) for k in ('Memory', 'NanoCpus', 'AutoRemove')}
    return selected, None


def epoch(stamp):
    return datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()


def terminal(state):
    return (state.get('Status') == 'exited' and not state.get('Running')
            and not state.get('OOMKilled') and state.get('ExitCode') == 0
            and bool(state.get('FinishedAt')) and not state['FinishedAt'].startswith('0001-'))


def physical(case, phase, data):
    """Observation only. Artifact must belong temporally to this exact execution."""
    log, artifact, checks = {
        'placement': ('run.log', 'floorplan.odb', [r'OT_LEGAL instances=\d+ overlaps=0 outside=0\b',
                                                r'OT_ASSERT PASS\b', r'OT_PA DONE\b']),
        'pdn': ('run_pdn.log', 'floorplan_pdn.odb', [r'OT_PDN PASS\b',
                 r'OT_PGCHECK VDD PASS\b', r'OT_PGCHECK VSS PASS\b']),
    }[phase]
    state = data['State']
    if not terminal(state):
        return dict(status='NO_SUCCESSFUL_CONTAINER_TERMINAL')
    started, finished = epoch(state['StartedAt']), epoch(state['FinishedAt'])
    for name in (log, artifact):
        p = case / name
        if (not p.is_file() or p.is_symlink() or p.stat().st_size == 0
                or not started <= p.stat().st_mtime <= finished):
            return dict(status='MISSING_OR_OUT_OF_EXECUTION_ARTIFACT', file=name)
    before = {n: (case / n).stat() for n in (log, artifact)}
    text = (case / log).read_text(errors='replace')
    if re.search(r'\bOT_(?:ASSERT|PA|PDN) FAIL\b|\bOT_PGCHECK \S+ FAIL\b|\[ERROR ', text):
        return dict(status='PHYSICAL_FAIL')
    if not all(re.search(c, text) for c in checks):
        return dict(status='MISSING_PHYSICAL_SUCCESS_MARKERS')
    hashes = {n: sha(case / n) for n in (log, artifact)}
    for n, s in before.items():
        now = (case / n).stat()
        if (s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns) != (now.st_ino, now.st_size, now.st_mtime_ns, now.st_ctime_ns):
            return dict(status='ARTIFACT_CHANGED_DURING_READ')
    return dict(status='PHYSICAL_PASS_SOURCE_UNVERIFIED', sha256=hashes)


def observe(case, cid, phase):
    start = time.time()
    data, error = inspect(cid)
    result = dict(schema='opentallas.qwen-dietop-legacy-observation.v1',
                  observed_at=datetime.now(timezone.utc).isoformat(), case=str(case),
                  expected_container_id=cid, phase=phase, container=data,
                  inspect_error=error, source_verified=False, continuation_allowed=False,
                  grt_complete=False, drt_complete=False, ssff_closed=False,
                  blockers=BLOCKERS, inputs={}, physical=dict(status='NOT_HARVESTED'))
    # Discovery is evidence only: never inspect/use a replacement as the target.
    result['same_name_inventory'] = command(['docker', 'ps', '-a', '--no-trunc',
                                            '--filter', 'name=qfd', '--format', '{{json .}}'])
    for name in INPUTS:
        p = case / name
        if p.is_file() and not p.is_symlink():
            before = p.stat()
            h = sha(p)
            after = p.stat()
            result['inputs'][name] = dict(sha256=h, size=after.st_size,
                mtime_ns=after.st_mtime_ns, ctime_ns=after.st_ctime_ns,
                stable_during_read=((before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    == (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)),
                modified_after_start=(after.st_mtime > epoch(data['State']['StartedAt'])) if data else None)
    for name in ('case.done', 'run.log.exit', 'run.log.start', 'run.log.end',
                 'run_pdn.log.exit', 'run_pdn.log.start', 'run_pdn.log.end'):
        p = case / name
        if p.is_file():
            result.setdefault('untrusted_markers', {})[name] = p.read_text(errors='replace')
    log = case / ('run.log' if phase == 'placement' else 'run_pdn.log')
    if log.is_file():
        text = log.read_text(errors='replace')
        result['log_observation'] = dict(size=log.stat().st_size, head=text.splitlines()[:18],
            tail=text.splitlines()[-15:])
    if data and data['Id'] == cid:
        result['processes'] = command(['docker', 'top', cid, '-eo', 'pid,ppid,etime,rss,args'])
        mounts = data['Mounts']
        mounted = any(m.get('Type') == 'bind' and m.get('Destination') == '/work'
                      and Path(m['Source']).resolve() == case for m in mounts)
        expected_tcl = '/work/' + ('run.tcl' if phase == 'placement' else 'run_pdn.tcl')
        if mounted and expected_tcl in ' '.join(data['command'] or []):
            result['physical'] = physical(case, phase, data)
        else:
            result['physical'] = dict(status='CASE_OR_PHASE_IDENTITY_MISMATCH')
        final, error = inspect(cid)
        result['container_after'] = final
        if error or final != data:
            result['physical'] = dict(status='CONTAINER_CHANGED_DURING_OBSERVATION')
        result['next_step'] = ('PRESERVE_LIVE_RUN' if data['State'].get('Running') else
                              'RECONCILE_SOURCE_AND_TERMINAL_BEFORE_ANY_NEW_LAUNCH')
    else:
        result['next_step'] = 'RECOVER_EXACT_ID_TERMINAL; DO_NOT_FOLLOW_REUSED_NAME'
    # Finite historical query, no event-stream wait; events may have been evicted.
    result['recent_events'] = command(['docker', 'events', '--since', str(int(start)-86400),
        '--until', str(int(start)), '--filter', 'container='+cid, '--format', '{{json .}}'])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case', required=True, type=Path)
    p.add_argument('--container', required=True)
    p.add_argument('--phase', choices=('placement', 'pdn'), default='placement')
    a = p.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', a.container):
        p.error('--container requires a full immutable container ID')
    print(json.dumps(observe(a.case.resolve(), a.container, a.phase), indent=2))


if __name__ == '__main__':
    main()
