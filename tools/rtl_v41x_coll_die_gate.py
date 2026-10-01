#!/usr/bin/env python3
"""Source-pinned focused gate for V4.1 die collective arithmetic and DMA.

The committed wo_b fixture is the first 64 rows of the real context-200K,
layer-0, TP4 unrounded FP32 partials.  It is a bounded block gate, not a
full-shape token or a chip throughput result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = Path('rtl/test/data/v41x_coll')
RTL = [Path('rtl/chip/ot_chip_v41x_coll_dma.sv'), Path('rtl/chip/ot_chip_v41x_die.sv'),
       Path('rtl/chip/ot_chip_v41x_tile.sv'), Path('rtl/rom/ot_rom_oneshot_px.sv'),
       Path('rtl/hdc/v41x/ot_hdc_core_v41x.sv'),
       Path('rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh')]
BENCH = [Path('rtl/test/tb_v41x_coll_dma.sv'), Path('rtl/test/tb_v41x_coll_pairwise.sv'),
         Path('rtl/test/tb_v41x_coll_wo_b.sv')]
ADD = [Path('rtl/hdc/ot_hdc_fastfp.sv'), Path('rtl/hdc/ot_hdc_fastfp_lat.sv'), Path('rtl/proto/ot_fp32_add_rne_pipe.sv')]
FIXTURE = [FIX / f'wo_b_rank{r}.hex' for r in range(4)] + [FIX / 'wo_b_expected.hex']
ORIGIN_SHA256 = [
    'afeb46f26a82368a279e7e572dcfafa7c604f271f79313e339d75308ace888fd',
    'ed2e52a8f22a51d0a7fcc9b4b0dee1a852e4eb968c7842de2c27323443429d36',
    '52524a8b7a247aed93b255b4198958677d40805c5a9c7a75bb21414a8ec69b5a',
    '99d7b30447ffdfc3571fc67225be0a71a17995284e73378f1607a45b2306ccf1',
]


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f'{cmd!r} failed ({p.returncode}):\n{p.stdout}\n{p.stderr}')
    return p.stdout.strip()


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--output', type=Path, default=Path('results/rtl/v41x_coll_die_gate.json'))
    a.add_argument('--scratch', type=Path)
    args = a.parse_args()
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        raise SystemExit('iverilog and vvp are required')
    scratch = args.scratch or Path(tempfile.mkdtemp(prefix='v41x_coll_gate_'))
    scratch.mkdir(parents=True, exist_ok=True)
    cases = [
        ('dma', 'tb_v41x_coll_dma', [], [BENCH[0], RTL[0]], 'CDMA_PASS'),
        ('pairwise', 'tb_v41x_coll_pairwise', [], [BENCH[1], RTL[3], *ADD], 'PAIRWISE_PASS'),
        ('bad_tag', 'tb_v41x_coll_pairwise', ['-Ptb_v41x_coll_pairwise.BAD_TAG=1'],
         [BENCH[1], RTL[3], *ADD], 'tag_mismatch_fault'),
        ('real_wo_b', 'tb_v41x_coll_wo_b', [], [BENCH[2], RTL[3], *ADD], 'WO_B_PASS'),
    ]
    verdicts = {}
    for name, top, extra, files, expected in cases:
        exe = scratch / f'{name}.vvp'
        run(['iverilog', '-g2012', '-s', top, *extra, '-o', str(exe), *map(str, files)])
        stdout = run(['vvp', str(exe)])
        if expected not in stdout:
            raise RuntimeError(f'{name}: missing {expected!r}: {stdout}')
        verdicts[name] = {'pass': True, 'stdout': stdout}
    src = [Path('tools/rtl_v41x_coll_die_gate.py'), *RTL, *BENCH, *ADD, *FIXTURE]
    hashes = {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in src}
    record = {
        'status': 'PASS', 'scope': 'bounded die collective block; no full-shape token or route claim',
        'source_head': run(['git', 'rev-parse', 'HEAD']),
        'source_sha256': hashes,
        'tools': {'iverilog': run(['iverilog', '-V']).splitlines()[0],
                  'vvp': subprocess.run(['vvp', '-V'], capture_output=True, text=True,
                                        check=True).stderr.splitlines()[0]},
        'cases': verdicts,
        'wo_b_fixture': {'context': 200000, 'layer': 0, 'rows': 64,
                         'partial_format': 'unrounded_fp32',
                         'origin_full_5120_row_partial_sha256_by_rank': ORIGIN_SHA256,
                         'reference': 'FP32 RNE ((r0+r1)+(r2+r3)); +0 canonical'},
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(f'{output}: PASS ({len(cases)} focused cases)')


if __name__ == '__main__':
    main()
