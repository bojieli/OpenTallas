#!/usr/bin/env python3
"""Resume the pinned Qwen system async builds; retain failed launch evidence.

Reuses Verilator-generated makefiles and completed objects. Supply the original
source tree, build root, and both already generated image directories. Runs only
the seven new SEQ_ASYNC cases, never golden generation or the old campaign.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shlex
from pathlib import Path
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd, log):
    start = time.monotonic()
    with log.open('x') as stream:
        rc = subprocess.run(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
    return {'command': args, 'returncode': rc, 'wall_s': round(time.monotonic()-start, 2),
            'log': log.name, 'log_sha256': digest(log)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--build-root', type=Path, required=True)
    ap.add_argument('--img', type=Path, required=True)
    ap.add_argument('--async-img', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--admit', type=Path, required=True)
    ap.add_argument('--expected-peak-gb', type=int, default=40)
    ap.add_argument('--jobs', type=int, default=24)
    a = ap.parse_args()
    for name in ('source_root', 'build_root', 'img', 'async_img', 'out', 'admit'):
        setattr(a, name, getattr(a, name).resolve())
    if a.out.exists():
        ap.error('output directory already exists; failed verdicts are immutable')
    for p in (a.img, a.async_img):
        if not (p/'expect.json').is_file():
            ap.error(f'missing existing image: {p}')
    # Refuse to resume if the makefile does not describe the pinned async shape.
    sources = set()
    generated = {}
    dirs = {v: a.build_root/f'obj_{v}' for v in ('c0p0a', 'c1p1a')}
    for v, d in dirs.items():
        text = (d/'Vtb_qwen_rom_sys__verFiles.dat').read_text()
        for param in ('-GSEQ_ASYNC=1', f'-GME_CDC={int(v == "c1p1a")}',
                      f'-GKV_PREFETCH={int(v == "c1p1a")}'):
            if param not in text:
                ap.error(f'{v}: generated build missing {param}')
        generated[v] = digest(d/'Vtb_qwen_rom_sys__verFiles.dat')
        for line in text.splitlines():
            if line.startswith('S '):
                source = Path(shlex.split(line)[-1])
                if not source.is_absolute():
                    source = a.source_root/source
                sources.add(source)
        sources.add(a.source_root/'rtl/test/qwen_sys/qsys_harness2.cpp')
    a.out.mkdir(parents=True)
    record = {'schema': 'opentallas.qwen-rom-system-async-resume.v1',
              'source_root': str(a.source_root), 'build_root': str(a.build_root),
              'status': 'fail', 'builds': {}, 'runs': {},
              'claim_boundary': 'Reduced TP4 system RTL only; no full-shape or SS/FF claim.',
              'runner_sha256': digest(Path(__file__)),
              'generated_build_sha256': generated,
              'source_sha256': {str(p): digest(p) for p in sorted(sources)},
              'images_sha256': {str(p): digest(p) for directory in (a.img, a.async_img)
                                for p in sorted(directory.glob('*.hex'))},
              'prior_failure_sha256': {p.name: digest(p)
                                       for p in sorted(a.build_root.glob('build_*.log'))}}
    # make consumes one quoting level: retain literal quotes in the compiler macro.
    flags = r'-DQSYS_TOP=Vtb_qwen_rom_sys -DQSYS_TOPH=\"Vtb_qwen_rom_sys.h\"'
    for v, d in dirs.items():
        args = [str(a.admit), str(a.expected_peak_gb), '--', 'make', '-C', str(d),
                '-f', 'Vtb_qwen_rom_sys.mk', '-j', str(a.jobs), '-W', 'Vtb_qwen_rom_sys__pch.h', 'VM_USER_CFLAGS='+flags]
        record['builds'][v] = command(args, a.source_root, a.out/f'build_{v}.log')
        if record['builds'][v]['returncode'] or not (d/'Vtb_qwen_rom_sys').is_file():
            (a.out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
            return 1
        record['builds'][v]['binary_sha256'] = digest(d/'Vtb_qwen_rom_sys')
    cases = [
        ('c0p0a_u1', 'c0p0a', a.async_img, ['+USERS=1']),
        ('c0p0a_u2', 'c0p0a', a.async_img, ['+USERS=2']),
        ('c0p0a_u1_legacyimg', 'c0p0a', a.img, ['+USERS=1']),
        ('c1p1a_u1', 'c1p1a', a.async_img, ['+USERS=1']),
        ('c1p1a_u2_flip97', 'c1p1a', a.async_img, ['+USERS=2', '+FLIP=97']),
        ('c1p1a_u1_fphase1', 'c1p1a', a.async_img, ['+USERS=1', '+FPHASE=1']),
        ('c1p1a_u4_flip23', 'c1p1a', a.async_img, ['+USERS=4', '+FLIP=23']),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cases)) as pool:
        pending = {}
        for name, v, image, extra in cases:
            args = [str(dirs[v]/'Vtb_qwen_rom_sys'), '+DIR='+str(image),
                    '+CLK='+('split' if v == 'c1p1a' else 'slow'), *extra]
            pending[name] = pool.submit(command, args, dirs[v], a.out/f'{name}.log')
        for name, job in pending.items():
            r = job.result()
            lines = (a.out/r['log']).read_text().splitlines()
            r['pass'] = r['returncode'] == 0 and 'PASS' in lines and 'FAIL' not in lines
            r['summary'] = [line for line in lines if line.startswith(('SYS', 'DIE', 'COUNTERS', 'CQ', 'FAULT_STATUS', 'STEP_MISMATCH', 'TIMEOUT'))]
            record['runs'][name] = r
    record['source_stable'] = all(digest(Path(p)) == h for p, h in record['source_sha256'].items())
    record['images_stable'] = all(digest(Path(p)) == h for p, h in record['images_sha256'].items())
    record['status'] = 'pass' if all(r['pass'] for r in record['runs'].values()) and record['source_stable'] and record['images_stable'] else 'fail'
    (a.out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'status': record['status'], 'runs': {n:r['pass'] for n,r in record['runs'].items()}}), flush=True)
    return int(record['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
