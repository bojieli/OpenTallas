#!/usr/bin/env python3
"""Scoreboard gate for regional rational-FIFO pointers, including resets and stalls.

Run this build through ot-run. Uses the existing payload/epoch/order scoreboard;
regional pointers change placement fanout, so latency and protocol must stay exact.
"""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import itertools
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / 'rtl/common/ot_ratio_cdc_fifo.sv'
TB = ROOT / 'rtl/test/two_clock/tb_ratio_cdc_fifo.cpp'


def build(out, depth, text):
    out.mkdir(parents=True, exist_ok=True)
    source = out / 'fifo.sv'
    source.write_text(text)
    cmd = ['verilator', '--cc', '--exe', '-O3', '--x-assign', 'unique',
           '--x-initial', 'unique', '-Wall', '-Wno-fatal', '-GW=64',
           f'-GDEPTH={depth}', '-GHOLD=2', '-GPTR_GROUP_W=7',
           '--top-module', 'ot_ratio_cdc_fifo', str(source), str(TB),
           '-Mdir', str(out), '-o', 'tb']
    for args, log in [(cmd, 'verilate.log'),
                      (['make', '-s', '-C', str(out), '-f', 'Vot_ratio_cdc_fifo.mk', '-j4'], 'make.log')]:
        r = subprocess.run(args, capture_output=True, text=True)
        (out / log).write_text(r.stdout + r.stderr)
        if r.returncode:
            raise RuntimeError(f'build failed: {out / log}')
    return out / 'tb'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--words', type=int, default=20000)
    a = p.parse_args(); a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    text = RTL.read_text()
    positives = []
    for depth in (4, 8):
        exe = build(a.out / f'depth{depth}', depth, text)
        cases = list(itertools.product(('f2s', 's2f'), ('sparse', 'saturate', 'random', 'backpressure', 'reset'), range(4)))
        def run(case):
            direction, mode, phase = case
            r = subprocess.run([str(exe), f'+dir={direction}', f'+mode={mode}',
                                f'+phase={phase}', f'+words={a.words}', '+seed=17'], capture_output=True, text=True)
            log = a.out / f'd{depth}_{direction}_{mode}_{phase}.log'; log.write_text(r.stdout + r.stderr)
            return dict(depth=depth, direction=direction, mode=mode, phase=phase,
                        ok=r.returncode == 0 and ' errors=0 PASS' in r.stdout, log=str(log))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            positives.extend(ex.map(run, cases))
    mutants = []
    substitutions = {
        'stale_pointer': ('else if (r_take) local_rp <= local_rp + 1\'b1;', 'else if (r_take) local_rp <= rp;'),
        'wrong_region_word': ('sh[local_rp[AW-1:0]][g*PTR_GROUP_W +: BW]', 'sh[local_rp[AW-1:0] + 1\'b1][g*PTR_GROUP_W +: BW]'),
    }
    for name, (old, new) in substitutions.items():
        assert text.count(old) == 1, (name, text.count(old))
        exe = build(a.out / name, 4, text.replace(old, new))
        r = subprocess.run([str(exe), '+dir=s2f', '+mode=reset', '+phase=1',
                            f'+words={a.words}', '+seed=17'], capture_output=True, text=True)
        (a.out / f'{name}.log').write_text(r.stdout + r.stderr)
        mutants.append(dict(name=name, caught=r.returncode != 0 and 'FAIL' in r.stdout))
    ok = all(x['ok'] for x in positives) and all(x['caught'] for x in mutants)
    rec = dict(ok=ok, rtl_sha256=hashlib.sha256(text.encode()).hexdigest(),
               words=a.words, pointer_group_width=7, positives=positives, mutants=mutants)
    (a.out / 'summary.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(f'WFC_RATIO_REGION {"PASS" if ok else "FAIL"} exact={sum(x["ok"] for x in positives)}/{len(positives)} mutants={sum(x["caught"] for x in mutants)}/{len(mutants)}')
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
