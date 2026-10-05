#!/usr/bin/env python3
"""Full-geometry (H16/D512/TD32/NL4/TROWS640) bench of the STREAMING attention engine ot_hdc_v41x_attn_s
(rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv: the current REPL = 2 controller with FPL/FML/NBANKP; tiles _l or, TILE_S = 1,
the head-group tile _s) at a chosen configuration, on the golden vectors of results/rtl/v41_full_attention_numeric
(tools/v41_full_attention_numeric_prepare.py, seed 20260929).

Same bench text and harness as tools/v41_full_attention_numeric_build.py but the _s bench
(rtl/test/tb_hdc_v41x_attn_s.sv) and the streaming sources; FPL = FML = 3, NBANKP = 0 is the as-built engine cycle
for cycle.  Run the built executable with tools/v41_full_attention_numeric_run.py.

    python3 tools/hbm_fmax_attn_full.py --root . --build B --param FPL=7 --param FML=6 --param TILE_S=1 \
        [--param NBANKP=5] [--pwords 2 --param ILV=1 --param REPL=2 --param NSTAGE=2]
"""
import argparse
import hashlib
import json
import resource
import shutil
import subprocess
import time
from pathlib import Path

SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv', 'rtl/hdc/v41x/ot_hdc_v41x_kreg.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
           'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv',
           'rtl/test/tb_hdc_v41x_attn_s.sv']
HIER = 'results/rtl/hbm_accel_fmax_inventory_20261004/attn/attn_l_hierarchy.vlt'
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
    ap.add_argument('--param', action='append', default=[], help='bench parameter NAME=VALUE (FPL, FML, NBANKP, ...)')
    ap.add_argument('--no-hier', action='store_true', help='flat Verilator build (no hierarchical blocks)')
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
    hier = [] if a.no_hier else ['--hierarchical', str(b / HIER)]
    cmd = [str(a.verilator), '--cc', '--exe', '--build', '--top-module', 'tb_hdc_v41x_attn', '--prefix', 'Vtb',
           '-Mdir', str(b / 'obj'), '-j', str(a.jobs), '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD',
           '--output-split', '20000', '--output-split-cfuncs', '2000', '--unroll-count', '1',
           '--unroll-limit', '131072', '-GH=16', '-GD=512', '-GTD=32', '-GNL=4', '-GTROWS=640',
           f'-GPWORDS={a.pwords}', *[f'-G{x}' for x in a.param], *hier, *[str(b / s) for s in SOURCES],
           str(b / HARNESS), '-CFLAGS', '-O1']
    t0 = time.time()
    with (b / 'build.log').open('w') as log:
        r = subprocess.run(cmd, cwd=b, stdout=log, stderr=subprocess.STDOUT)
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    exe = b / 'obj' / 'Vtb'
    status = dict(command=[str(x).replace(str(b), '<build>') for x in cmd], source_sha256=pins, pwords=a.pwords,
                  params=a.param, returncode=r.returncode, elapsed=time.time() - t0, max_rss_kib=rss,
                  executable_sha256=sha(exe) if exe.is_file() else None)
    (b / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({k: status[k] for k in ('returncode', 'elapsed', 'max_rss_kib', 'executable_sha256')}))
    raise SystemExit(r.returncode)


if __name__ == '__main__':
    main()
