#!/usr/bin/env python3
"""Four-stack pooled X_IDX adapter token gate, with source-pinned results."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/hdc_v41x_idx_pool_adapt_campaign.json'
WORK = Path('/tmp/claude-1000/idx_pool_adapt_gate')
OBJ = WORK / 'obj'
TOP = 'tb_hdc_v41x_idx_pool_adapt'
SOURCES = [ROOT / f'rtl/hdc/v41x/{n}.sv' for n in (
    'ot_hdc_v41x_idx_pool_adapt', 'ot_hdc_v41x_idx_pool_batch',
    'ot_hdc_v41x_idx_pool_finish', 'ot_hdc_v41x_idx_pcol',
    'ot_hdc_v41x_idx_hsum', 'ot_hdc_v41x_idx_arith',
    'ot_hdc_v41x_idx_pool_replica', 'ot_hdc_v41x_idx_kstream', 'ot_hdc_v41x_idx_hbm',
    'ot_hdc_v41x_wgt_tile', 'ot_hdc_v41x_wgt_mac',
    'ot_hdc_v41x_wgt_bdot', 'ot_hdc_v41x_wgt_red')]
SOURCES += [ROOT / 'rtl/hdc/ot_hdc_fastfp.sv', ROOT / 'rtl/hdc/ot_hdc_delay.sv',
            ROOT / 'rtl/test/tb_hdc_v41x_idx_pool_adapt.sv',
            ROOT / 'rtl/test/hdc_v41_tb_harness.cpp']
PAT = re.compile(r'V41XPOOLADAPT k=(\d+) checked=(\d+) errors=(\d+) keys=(\d+) beats=(\d+) cycles=(\d+)')


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    exe = OBJ / f'V{TOP}'
    stamp = hashlib.sha256(b''.join(p.read_bytes() for p in SOURCES)).hexdigest()
    if not exe.exists() or not (OBJ / 'stamp').exists() or (OBJ / 'stamp').read_text() != stamp:
        cmd = ['verilator', '--cc', '--exe', '--build', '-O1', '--x-assign', 'fast',
               '--x-initial', 'fast', '-Wno-fatal', '-Wno-WIDTH', '-Wno-UNUSED',
               '-Wno-BLKSEQ', '-Wno-DECLFILENAME', '-Wno-WIDTHCONCAT',
               '-Wno-TIMESCALEMOD', '--top-module', TOP,
               '-CFLAGS', f'-DVTOP=V{TOP} -O0', '-j', '4', '--Mdir', str(OBJ)]
        subprocess.run(cmd + [str(p) for p in SOURCES], cwd=ROOT, check=True,
                       stdout=(WORK / 'build.log').open('w'),
                       stderr=subprocess.STDOUT)
        (OBJ / 'stamp').write_text(stamp)
    rows = []
    for k in (32, 128):
        run = subprocess.run([str(exe), f'+KDIM={k}'], cwd=WORK,
                             capture_output=True, text=True, timeout=600, check=True)
        m = PAT.search(run.stdout)
        if not m:
            raise RuntimeError(run.stdout[-2000:] + run.stderr[-2000:])
        kd, checked, errors, keys, beats, cycles = map(int, m.groups())
        row = dict(k=kd, checked=checked, errors=errors, keys=keys, beats=beats, cycles=cycles)
        assert kd == k and checked == 32 and errors == 0 and keys >= 32, row
        rows.append(row)
    rec = dict(schema='opentallas-hdc-v41x-idx-pool-adapt-v1', status='pass', rows=rows,
               limitation='Four-stack zero-key token proves loader/replicated-image group selection/merge/pooled score/VM write coupling. The selector rereads each key-group prefix; HBM bandwidth and tile replication remain unmeasured. Runtime writer is separately unit-gated; core dispatch remains.',
               sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in SOURCES + [Path(__file__).resolve()]})
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
