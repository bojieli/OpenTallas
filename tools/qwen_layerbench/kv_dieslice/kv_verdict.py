#!/usr/bin/env python3
"""TOK-QK-3 10-27: one verdict for a KV die-slice run (tb_kvslice / tb_kvslice_native).

A process exit 0 is NOT a pass: the bench prints its verdict (KVSLICE_BOOT PASS|FAIL, FAR_LAYER_SUMMARY ... PASS|FAIL)
and calls $finish either way.  This classifier is fail-closed:
  PASS  iff  exit == 0  AND  exactly the first KVSLICE_BOOT line says PASS  AND  (with --layers N) N FAR_LAYER_SUMMARY
        lines exist for layers 0..N-1 and every one says PASS.
Anything else (missing log, missing verdict line, nonzero exit, any FAIL, missing layer) is FAIL with a reason.
  kv_verdict.py RUNDIR [--layers N] [--expect fail]
--expect fail marks a negative control (mutant): the run is CAUGHT iff the verdict is FAIL; a mutant that PASSes is
reported as MUTANT_MISSED.  Writes RUNDIR/verdict ("PASS|FAIL|CAUGHT|MUTANT_MISSED <reason>"); exit 0 only for PASS or CAUGHT.
"""
import argparse, re, sys
from pathlib import Path


def classify(rundir: Path, layers: int = 0):
    log = rundir / 'sim.log'
    if not log.is_file():
        return 'FAIL', 'no sim.log'
    try:
        rc = int((rundir / 'exit').read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return 'FAIL', 'no exit file'
    txt = log.read_text(errors='replace')
    boot = re.findall(r'^KVSLICE_BOOT (PASS|FAIL)\b(.*)$', txt, re.M)
    if not boot:
        return 'FAIL', f'no KVSLICE_BOOT verdict line (exit {rc})'
    if boot[0][0] != 'PASS':
        return 'FAIL', f'KVSLICE_BOOT FAIL{boot[0][1][:160]} (exit {rc})'
    if rc != 0:
        return 'FAIL', f'KVSLICE_BOOT PASS but exit {rc}'
    if layers:
        got = {}
        for m in re.finditer(r'^FAR_LAYER_SUMMARY layer (\d+) .* (PASS|FAIL)\s*$', txt, re.M):
            got.setdefault(int(m.group(1)), m.group(2))
        miss = [n for n in range(layers) if n not in got]
        bad = [n for n in range(layers) if got.get(n) == 'FAIL']
        if miss:
            return 'FAIL', f'boot PASS; FAR_LAYER_SUMMARY missing for {len(miss)}/{layers} layers (first {miss[0]})'
        if bad:
            return 'FAIL', f'boot PASS; layers FAIL {len(bad)}/{layers} (first {bad[0]})'
        return 'PASS', f'boot PASS; layers PASS {layers}/{layers}'
    return 'PASS', 'KVSLICE_BOOT PASS exit 0'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('rundir', type=Path)
    ap.add_argument('--layers', type=int, default=0)
    ap.add_argument('--expect', choices=('pass', 'fail'), default='pass')
    a = ap.parse_args(argv)
    v, why = classify(a.rundir, a.layers)
    if a.expect == 'fail':
        v = 'CAUGHT' if v == 'FAIL' else 'MUTANT_MISSED'
    line = f'{v} {why}'
    try:
        (a.rundir / 'verdict').write_text(line + '\n')
    except OSError:
        pass
    print(line)
    return 0 if v in ('PASS', 'CAUGHT') else 1


if __name__ == '__main__':
    sys.exit(main())
