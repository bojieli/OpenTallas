#!/usr/bin/env python3
"""Run generated Qwen floorplan -> PDN in a new, never-reused directory.

Requires a clean pinned source checkout and generated a_pdn inputs. No remote
installation or existing-run mutation. Retains containers and failure receipts;
never retries, removes a container, or launches GRT/DRT. Use the shared host
admission guard; --peak-gib is a measured scheduling estimate, not a memory cap.
The guard must implement the current fleet policy. An additional check immediately
after admission enforces peak + max(10% HOST TOTAL, 32 GiB).
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

INPUTS = ('manifest.json', 'run.tcl', 'run_pdn.tcl', 'die.v', 'elements.lef',
          'phy_ew.lef', 'snap.tcl', 'place.tcl', 'pdn.tcl')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def receipt(path, data):
    # Exclusive creation: a previous verdict is never overwritten.
    with path.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def output(argv, **kwargs):
    return subprocess.check_output(argv, text=True, **kwargs).strip()


def admitted_start(cid, peak):
    mem = {line.split(':')[0]: int(line.split()[1]) * 1024
           for line in Path('/proc/meminfo').read_text().splitlines()
           if line.startswith(('MemTotal:', 'MemAvailable:'))}
    required = peak * 2**30 + max(mem['MemTotal'] * 0.1, 32 * 2**30)
    if mem['MemAvailable'] < required:
        print('Admission headroom changed; container remains unstarted', file=sys.stderr)
        return 75
    return subprocess.call(['docker', 'start', '--attach', cid])


def physical_gate(work, phase, text):
    if re.search(r'\bOT_(?:ASSERT|PA|PDN) FAIL\b|\bOT_PGCHECK \S+ FAIL\b|\[ERROR ', text):
        raise RuntimeError(f'{phase}: physical failure in log despite process status')
    if phase == 'placement':
        checks = (r'OT_LEGAL instances=\d+ overlaps=0 outside=0\b',
                  r'OT_ASSERT PASS\b', r'OT_PA DONE\b')
        artifact = work / 'floorplan.odb'
    else:
        checks = (r'OT_PDN PASS\b', r'OT_PGCHECK VDD PASS\b', r'OT_PGCHECK VSS PASS\b')
        artifact = work / 'floorplan_pdn.odb'
    if not all(re.search(c, text) for c in checks) or not artifact.is_file() or artifact.stat().st_size == 0:
        raise RuntimeError(f'{phase}: missing physical success marker or nonempty {artifact.name}')
    return {artifact.name: digest(artifact)}


def run(a):
    source = a.source_root.resolve()
    if output(['git', 'rev-parse', 'HEAD'], cwd=source) != a.source:
        raise ValueError('source HEAD does not match --source')
    if output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=source):
        raise ValueError('source checkout is not clean')
    inputs = a.inputs.resolve()
    dest = a.run.resolve()
    if dest == inputs or dest.is_relative_to(inputs) or dest.is_relative_to(source):
        raise ValueError('--run must be outside the input directory and source checkout')
    if not math.isfinite(a.peak_gib) or a.peak_gib <= 0 or a.threads <= 0:
        raise ValueError('positive measured peak and thread count required')
    if not a.admit.is_file():
        raise ValueError('shared host admission guard is missing')
    # Atomic ownership claim, before any docker operation or receipt write.
    dest.mkdir(parents=False, exist_ok=False)
    token = uuid.uuid4().hex
    try:
        frozen = dest / 'inputs'
        frozen.mkdir()
        work = dest / 'work'
        work.mkdir()
        hashes = {}
        for name in INPUTS:
            src = inputs / name
            if src.is_symlink() or not src.is_file():
                raise ValueError(f'input must be a regular non-symlink file: {src}')
            before = digest(src)
            shutil.copyfile(src, frozen / name)
            hashes[name] = digest(frozen / name)
            if before != hashes[name] or digest(src) != before:
                raise ValueError(f'input changed while snapshotting: {name}')
            (frozen / name).chmod(0o444)
        manifest = json.loads((frozen / 'manifest.json').read_text())
        if manifest.get('execution_order') != ['run.tcl', 'run_pdn.tcl']:
            raise ValueError('expected generated placement -> PDN execution_order')
        # Recheck the entire source set after copying; later source edits cannot
        # reach the read-only per-file mounts in the claimed run directory.
        if any(digest(inputs / n) != h for n, h in hashes.items()):
            raise ValueError('input set changed during snapshot')
        frozen.chmod(0o555)
        image = output(['docker', 'image', 'inspect', a.image, '--format', '{{.Id}}'])
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
            raise RuntimeError('image did not resolve to an immutable ID')
        receipt(dest / 'launch.json', dict(run_id=token, source_commit=a.source,
                source_root=str(source), input_origin=str(inputs), input_sha256=hashes,
                launcher_sha256=digest(Path(__file__)), image=image,
                peak_gib=a.peak_gib, threads=a.threads))
        for phase, tcl, log in [('placement', 'run.tcl', 'run.log'),
                                ('pdn', 'run_pdn.tcl', 'run_pdn.log')]:
            name = f'qfd_{token}_{phase}'
            # No shell interpolation of paths or thread values. Read-only bind
            # mounts shadow inputs inside /work; only outputs are writable.
            command = ['docker', 'create', '--name', name,
                       '--label', f'opentallas.run={token}',
                       '--label', f'opentallas.phase={phase}',
                       '-v', f'{work}:/work', '-w', '/work']
            for n in INPUTS:
                command += ['-v', f'{frozen / n}:/work/{n}:ro']
            command += [image, 'bash', '-lc',
                        'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && '
                        'exec /usr/bin/time -v openroad -threads "$1" -no_init -exit "$2"',
                        'qwen-dietop', str(a.threads), f'/work/{tcl}']
            created = subprocess.run(command, text=True, capture_output=True)
            receipt(dest / f'{phase}.create.json', dict(argv=command, exit_code=created.returncode,
                    stdout=created.stdout, stderr=created.stderr))
            if created.returncode:
                raise RuntimeError(f'{phase}: docker create failed ({created.returncode}); no owned container')
            cid = created.stdout.strip()
            if not re.fullmatch(r'[0-9a-f]{64}', cid):
                raise RuntimeError(f'{phase}: invalid created container ID')
            # Identity checked before start AND at terminal. Never look up by name
            # after create, and never trust a stale .exit or case.done.
            def inspect():
                data = json.loads(output(['docker', 'inspect', cid]))[0]
                if (data['Id'] != cid or data['Image'] != image or
                    data['Config']['Labels'].get('opentallas.run') != token or
                    data['Config']['Labels'].get('opentallas.phase') != phase):
                    raise RuntimeError(f'{phase}: container identity mismatch')
                return data
            initial = inspect()
            if initial['State']['Status'] != 'created':
                raise RuntimeError(f'{phase}: container is not freshly created')
            receipt(dest / f'{phase}.container.json', initial)
            with (work / log).open('x') as stream:
                rc = subprocess.call([str(a.admit.resolve()), str(a.peak_gib), '--',
                        sys.executable, str(Path(__file__).resolve()),
                        '--_admitted-start', cid, str(a.peak_gib)],
                        stdout=stream, stderr=subprocess.STDOUT)
            final = inspect()
            receipt(dest / f'{phase}.state.json', final)
            state = final['State']
            if (rc != 0 or state['Status'] != 'exited' or state['Running'] or
                state.get('OOMKilled') or state['ExitCode'] != 0 or
                not state.get('FinishedAt') or state['FinishedAt'].startswith('0001-')):
                raise RuntimeError(f'{phase}: attach/admission={rc}, container state={state}')
            artifacts = physical_gate(work, phase, (work / log).read_text())
            if any(digest(frozen / n) != h for n, h in hashes.items()):
                raise RuntimeError(f'{phase}: immutable input hash changed')
            receipt(dest / f'{phase}.complete.json', dict(container_id=cid,
                    exit_code=state['ExitCode'], finished_at=state['FinishedAt'],
                    artifact_sha256=artifacts, log_sha256=digest(work / log)))
        receipt(dest / 'complete.json', dict(run_id=token, status='PLACEMENT_PDN_COMPLETE',
                grt_complete=False, drt_complete=False, ssff_closed=False))
        return 0
    except Exception as exc:
        receipt(dest / 'failure.json', dict(run_id=token, error=str(exc)))
        print(str(exc), file=sys.stderr)
        return 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--_admitted-start':
        return admitted_start(sys.argv[2], float(sys.argv[3]))
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', required=True, type=Path)
    p.add_argument('--run', required=True, type=Path, help='new directory; parent must already exist')
    p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--source', required=True, help='full commit SHA of clean producer checkout')
    p.add_argument('--threads', type=int, default=16)
    p.add_argument('--peak-gib', type=float, required=True, help='measured peak; no cgroup limit imposed')
    p.add_argument('--admit', type=Path, default=Path('/srv/opentallas-scratch/admit.sh'))
    p.add_argument('--image', default='openroad/orfs:asap7lock')
    try:
        return run(p.parse_args())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
