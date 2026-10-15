#!/usr/bin/env python3
"""Recover a parser-failed v2 gate without repeating physical work.

Requires the original full shipping sidecar, source tree, execution script and
log. Reruns local checks, then uses exactly the live gate's remote-output parser.
The frozen source binding is retained; mismatch with the explicitly requested
route commit or current daemon overlay FAILs qualification. Never infers HEAD.
"""
import argparse
import json
import subprocess
from pathlib import Path

import pre_route_gate as PG
import source_binding as SB


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kit', type=Path)
    ap.add_argument('--host', required=True)
    ap.add_argument('--run', required=True, help='original remote R, adjacent to R.source_snapshot.json')
    ap.add_argument('--script', required=True, help='original remote execution script')
    ap.add_argument('--log', required=True, type=Path)
    ap.add_argument('--route-commit', required=True, help='explicit candidate source commit, never inferred from HEAD')
    ap.add_argument('--frozen-helper-recovery', action='store_true',
                    help='verify committed original helpers and actual staged bytes; recover original evidence only')
    ap.add_argument('--staged-remeasurement', action='store_true', help='verify persisted NEW measurements on original CTS artifacts; original archive stdout remains unavailable')
    ap.add_argument('--cts', action='store_true')
    ap.add_argument('--synth-cap', type=int, default=1800)
    a = ap.parse_args()
    kd = a.kit.resolve()
    log = a.log.read_bytes()
    module = Path(SB.__file__).read_text()
    if a.staged_remeasurement and a.frozen_helper_recovery:
        ap.error('staged remeasurement requires current route/overlay matching, not frozen-helper recovery')
    if a.staged_remeasurement:
        code = ('exec(' + repr(module) + ')\n'
                'binding=json.loads(Path(' + repr(a.run + '.source_snapshot.json') + ').read_text())\n'
                'recovered=recover_staged_remeasurement(binding,Path(' + repr(a.run) + '),'
                + repr(a.script) + ',' + repr(log) + ')\nprint(json.dumps(recovered))\n')
    else:
        code = ('exec(' + repr(module) + ')\n'
                'binding=json.loads(Path(' + repr(a.run + '.source_snapshot.json') + ').read_text())\n'
                'recovered=recover_verified_snapshot(binding,Path(' + repr(a.run + '/src') + '),'
                + repr(log) + ',Path(' + repr(a.script) + ').read_bytes())\n'
                'print(json.dumps(recovered))\n')
    remote = subprocess.run(['ssh', a.host, 'python3 -'], input=code, capture_output=True, text=True)
    if remote.returncode:
        ap.exit(1, 'Original snapshot verification failed: ' + remote.stderr[-1500:] + '\n')
    binding = json.loads(remote.stdout)
    if a.frozen_helper_recovery:
        HO = SB.overlay_module()
        frozen = binding.get('route_overlay_plan')
        try:
            HO.committed_frozen_payloads(PG.ROOT, frozen)
            paths = sorted(e['path'] for e in binding['files'] if e['source'] == 'daemon_overlay')
            code = ('exec(' + repr(Path(HO.__file__).read_text()) + ')\n'
                    'print(json.dumps(verify_staged_helpers(' + repr(a.run + '/src') + ','
                    + repr(frozen) + ',' + repr(paths) + ')))\n')
            check = subprocess.run(['ssh', a.host, 'python3 -'], input=code, capture_output=True, text=True)
            if check.returncode:
                raise ValueError(check.stderr[-1500:])
            receipt = json.loads(check.stdout)
            receipt['manifest_sha256'] = binding['manifest_sha256']
            binding['helper_recovery'] = receipt
        except (OSError, ValueError, TypeError, subprocess.SubprocessError) as ex:
            ap.exit(1, 'Original executed helper verification failed: ' + str(ex) + '\n')
    g = PG.Gate()
    g.source_binding = binding
    g.remote_host = a.host
    job = json.loads((kd / 'job.json').read_text()) if (kd / 'job.json').exists() else None
    spec = PG.check_kit(g, kd, job, a.route_commit)
    ok, why = SB.validate(binding, PG.ROOT, PG.DAEMON_TREE, a.route_commit,
                          frozen_recovery=a.frozen_helper_recovery)
    g.add('INFO' if ok else 'FAIL', 'source_binding', why,
          '' if ok else 'regenerate a fresh gate for the changed route source/tools')
    PG.analyse_remote(g, kd, spec, log.decode(errors='replace'), a.cts, binding, a.synth_cap, a.host)
    g.print()
    if getattr(g, 'clock', None):
        PG.write_gate_result(g, kd, a.cts, a.host)
    return 1 if g.verdict == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
