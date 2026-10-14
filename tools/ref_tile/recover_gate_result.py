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
    ap.add_argument('--cts', action='store_true')
    ap.add_argument('--synth-cap', type=int, default=1800)
    a = ap.parse_args()
    kd = a.kit.resolve()
    log = a.log.read_bytes()
    module = Path(SB.__file__).read_text()
    code = ('exec(' + repr(module) + ')\n'
            'binding=json.loads(Path(' + repr(a.run + '.source_snapshot.json') + ').read_text())\n'
            'recovered=recover_verified_snapshot(binding,Path(' + repr(a.run + '/src') + '),'
            + repr(log) + ',Path(' + repr(a.script) + ').read_bytes())\n'
            'print(json.dumps(recovered))\n')
    remote = subprocess.run(['ssh', a.host, 'python3 -'], input=code, capture_output=True, text=True)
    if remote.returncode:
        ap.exit(1, 'Original snapshot verification failed: ' + remote.stderr[-1500:] + '\n')
    binding = json.loads(remote.stdout)
    g = PG.Gate()
    g.source_binding = binding
    g.remote_host = a.host
    job = json.loads((kd / 'job.json').read_text()) if (kd / 'job.json').exists() else None
    spec = PG.check_kit(g, kd, job, a.route_commit)
    ok, why = SB.validate(binding, PG.ROOT, PG.DAEMON_TREE, a.route_commit)
    g.add('INFO' if ok else 'FAIL', 'source_binding', why,
          '' if ok else 'regenerate a fresh gate for the changed route source/tools')
    PG.analyse_remote(g, kd, spec, log.decode(errors='replace'), a.cts, binding, a.synth_cap, a.host)
    g.print()
    if getattr(g, 'clock', None):
        PG.write_gate_result(g, kd, a.cts, a.host)
    return 1 if g.verdict == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
