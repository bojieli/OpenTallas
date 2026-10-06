#!/usr/bin/env python3
"""Reproduce the minimum full-depth protected-ring component gate."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/lib/ot_reset_sync.sv',
    'rtl/hdc/kv/ot_qwen_s4_checked_state.sv',
    'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv',
    'rtl/test/qwen_rom_runtime/realmem/tb_qwen_s4_protected_ring.sv',
]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)  # preserve prior verdicts
    rows = []
    with tempfile.TemporaryDirectory(prefix='qwen-s4-ring-') as scratch:
        for name, width, depth, kind in [('landing', 281, 64, 0),
                                       ('write', 289, 16, 1),
                                       ('write_done', 9, 64, 2)]:
            exe = Path(scratch) / f'{name}.vvp'
            cmd = ['iverilog', '-g2012', '-s', 'tb_qwen_s4_protected_ring']
            for param, value in [('WIDTH', width), ('DEPTH', depth), ('KIND', kind)]:
                cmd += ['-P', f'tb_qwen_s4_protected_ring.{param}={value}']
            cmd += ['-o', str(exe)] + SOURCES
            b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            (args.output / f'{name}.build.log').write_text(b.stdout + b.stderr)
            r = subprocess.run(['vvp', str(exe)], capture_output=True, text=True) if b.returncode == 0 else b
            (args.output / f'{name}.run.log').write_text(r.stdout + r.stderr)
            rows.append(dict(name=name, width=width, depth=depth, kind=kind,
                             build_argv=cmd, build_exit=b.returncode, exit=r.returncode))
            print(name, r.returncode, r.stdout.strip(), flush=True)
    pins = SOURCES + ['tools/qwen_stream4_protected_ring_check.py',
                      'tools/qwen_stream4_protected_model.py',
                      'results/rtl/qwen_stream4_protected_20261005/prebuild_model.json']
    ok = all(x['build_exit'] == 0 and x['exit'] == 0 for x in rows)
    record = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  verdict='PASS_COMPONENT_RING_ONLY' if ok else 'FAIL_COMPONENT_RING',
                  rows=rows, source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                  CLK_ps=833.333, HCLK_ps=1024,
                  scope='one full-depth ring each; ordered180, capacity-held admission pause, CE3, UE, valid wrong-PC seal, primary Gray pointer upset',
                  adopted=False, whole_interface_exact32=False, physical_qualified=False,
                  unimplemented=['per-PC write-cache/port wiring',
                                 'shared descriptor/GO protection and exact inventory',
                                 'actual warm-reset boundary binding'])
    (args.output/'terminal.json').write_text(json.dumps(record, indent=2)+'\n')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
