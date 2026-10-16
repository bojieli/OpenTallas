#!/usr/bin/env python3
"""Execute one fixed HC-engine programme against an already-built full-shape binary.
Run admitted via ot-run. Each output directory is immutable; use a new directory for every case.
Probe reports RAW0 only: it does not pop the FIFO or measure scalar RS. Full mode needs an
explicit offline-established scalar spacing. No ready or credit signal changes any event time.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--binary', type=Path, required=True)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--mode', choices=('full', 'probe', 'g22'), default='full')
    ap.add_argument('--npos', type=int, choices=range(1, 9), default=1)
    ap.add_argument('--raw0', type=int, default=0)
    ap.add_argument('--rs', type=int, default=0)
    ap.add_argument('--mutant', type=int, choices=range(4), default=0)
    ap.add_argument('--seed', type=int, default=20261016)
    a = ap.parse_args()
    a.binary = a.binary.resolve()
    a.run = a.run.resolve()
    if a.run.exists():
        ap.error('output directory already exists; preserve earlier evidence and choose a new directory')
    if a.mode == 'full' and (a.raw0 <= 0 or a.rs <= 0):
        ap.error('full mode requires positive --raw0 and --rs')
    if a.mode == 'g22' and a.npos != 1:
        ap.error('g22 component case has exactly one position')
    if a.mode == 'probe' and a.npos != 1:
        ap.error('probe without pops uses one position to stay within the raw FIFO')
    cmd = [sys.executable, str(ROOT / 'tools/rtl_hbm_hc_eng_static_gate.py'),
           '--run', str(a.run), '--mode', a.mode, '--npos', str(a.npos),
           '--raw0', str(a.raw0), '--rs', str(a.rs), '--seed', str(a.seed)]
    subprocess.run(cmd, cwd=ROOT, check=True)
    plus = shlex.split((a.run / 'plus.txt').read_text())
    p = subprocess.run([str(a.binary), *plus], cwd=a.run, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (a.run / 'run.log').write_text(log)
    meta = json.loads((a.run / 'case.json').read_text())
    probe = re.search(r'PROBE raw t=(\d+) ss=1 pos=0 idx=\d+', log)
    measured_raw0 = int(probe[1]) - meta['events']['TL'] if probe else None
    if a.mode == 'probe':
        valid = p.returncode == 0 and measured_raw0 is not None and 'HC_ENG_FAULT' not in log
        status = 'PROBE_ONLY' if valid else 'FAIL'
    elif a.mutant:
        valid = p.returncode != 0 and any(s in log for s in (
            'MIX_MISMATCH', 'TAIL_MISMATCH', 'HC_ENG_FAULT'))
        status = 'MUTANT_REJECTED' if valid else 'FAIL'
    else:
        valid = p.returncode == 0 and 'HC_ENG PASS' in log
        status = 'COMPONENT_EXACT_PASS' if valid else 'FAIL'
    report = dict(status=status, passed=valid, mode=a.mode, npos=a.npos, mutant=a.mutant,
                  scope='HC engine component at declared external wave/gathered-mix/table/programme ports',
                  full_die_qualified=False, binary_sha256=hashlib.sha256(a.binary.read_bytes()).hexdigest(),
                  declared_compile_mutant=a.mutant, binary_compile_lineage_must_be_checked_separately=True,
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  rc=p.returncode, measured_raw0=measured_raw0, scalar_spacing=a.rs, programme=meta)
    (a.run / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'programme'}))
    return 0 if valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
