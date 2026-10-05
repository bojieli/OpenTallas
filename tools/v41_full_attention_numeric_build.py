#!/usr/bin/env python3
"""Build the full-geometry (H16/D512/TD32/NL4/TROWS640) attention bench with Verilator's hierarchical flow.

Same sources, hierarchy boundaries and front-end options as results/rtl/v41_full_attention_numeric/status.json,
plus -GPWORDS (two-word probability loader, W11) and --exe --build with the original harness so the executable
is produced in one step.  Sources are copied into --build and pinned in pins.json / status.json.
"""
import argparse
import hashlib
import json
import resource
import shutil
import subprocess
import time
from pathlib import Path

SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
           'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/test/tb_hdc_v41x_attn.sv']
HIER = 'results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt'
HARNESS = 'rtl/test/hdc_v41_harness.cpp'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--build', type=Path, required=True)
    ap.add_argument('--pwords', type=int, default=1)
    ap.add_argument('--verilator', type=Path,
                    default=Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator')
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--param', action='append', default=[],
                    help='extra bench parameter NAME=VALUE (e.g. NJOBMAX=6 NKV=3840 for the verify-6 case)')
    ap.add_argument('--define', action='append', default=[], help='Verilog define (e.g. OT_ATTN_SETCHECK)')
    a = ap.parse_args()
    root, b = a.root.resolve(), a.build.resolve()
    b.mkdir(parents=True, exist_ok=True)
    pins = {}
    for rel in SOURCES + [HIER, HARNESS]:
        dst = b / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, dst)
        pins[rel] = sha(dst)
    (b / 'pins.json').write_text(json.dumps(pins, indent=2) + '\n')
    cmd = [str(a.verilator), '--cc', '--exe', '--build', '--top-module', 'tb_hdc_v41x_attn', '--prefix', 'Vtb',
           '-Mdir', str(b / 'obj'), '-j', str(a.jobs), '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD',
           '--output-split', '20000', '--output-split-cfuncs', '2000', '--unroll-count', '1',
           '--unroll-limit', '131072', '-GH=16', '-GD=512', '-GTD=32', '-GNL=4', '-GTROWS=640',
           f'-GPWORDS={a.pwords}', *[f'-G{x}' for x in a.param], *[f'+define+{x}' for x in a.define], '--hierarchical', str(b / HIER), *[str(b / s) for s in SOURCES],
           str(b / HARNESS), '-CFLAGS', '-O1']
    t0 = time.time()
    with (b / 'build.log').open('w') as log:
        r = subprocess.run(cmd, cwd=b, stdout=log, stderr=subprocess.STDOUT)
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    exe = b / 'obj' / 'Vtb'
    status = dict(command=cmd, source_sha256=pins, pwords=a.pwords, params=a.param, defines=a.define, returncode=r.returncode,
                  elapsed=time.time() - t0, max_rss_kib=rss,
                  executable_sha256=sha(exe) if exe.is_file() else None,
                  verilator_version=subprocess.check_output([str(a.verilator), '--version'], text=True).strip(),
                  status='build_pass' if r.returncode == 0 and exe.is_file() else 'build_fail')
    (b / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({k: v for k, v in status.items() if k != 'command'}))
    raise SystemExit(0 if status['status'] == 'build_pass' else 1)


if __name__ == '__main__':
    main()
