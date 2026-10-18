#!/usr/bin/env python3
"""KVJ-E: run one compiled per-PC controller calendar (targets 6..9) on the actual controller + JEDEC core bench.

    run_kv_static_programme_ctrl.py COMPILE_DIR OUT [--pc 0 127 ...] [--binary PREBUILT]

Reads the PC's 32 boot words from COMPILE_DIR/target{6+stack}.hex (low halves at cfg addr 0..15, high at 16..31),
rebuilds the 16 x 128-b image, derives the RD reservation slot map from the image's own Run descriptors
(controller_calendar_image.Run.events), and runs tools/qwen_static_kv/run_controller_calendar_native.py's bench
(tb_controller_calendar_native: PROFILE0 JEDEC core, 36 frames, 512 reads a frame, PHY + corrected timelines,
open-row / bank / data checks) at jitter 0 / 8 / 16.  Exit 0 iff every run passes.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = [f'rtl/qwen_sys/static_kv_20261014/{n}.sv' for n in ['qkd_controller_hbm_calendar', 'qkd_static_kv_return_calendar',
         'qkd_ctrl_pc_host_static', 'qkd_ctrl_pc_host_static_core', 'qkd_ctrl_pc_children', 'ot_qkd_static_ctrl_pc_emb',
         'ot_qkd_static_kv_timing', 'ot_qkd_static_emb_cdc', 'qkd_static_kv_write_observer']] + \
        ['rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv', 'rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv',
         'rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv', 'rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv',
         'rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv', 'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv',
         'rtl/test/qwen_static_kv/tb_controller_calendar_native.sv']   # = run_controller_calendar_native.py


def decode(word):
    """the Run fields of one 128-b descriptor word (controller_calendar_image.Run.word, inverse)"""
    return dict(edge=(word & 0xffff) + 2, count=(word >> 16) & 1023, burst=((word >> 26) & 15) + 1, gap=(word >> 30) & 255,
                mask=(word >> 81) & 7)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('compile_dir', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--pc', type=int, nargs='+', default=[0, 127])
    ap.add_argument('--binary', type=Path)
    a = ap.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    v = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    binary = a.binary.resolve() if a.binary else out / 'obj' / 'Vtb_controller_calendar_native'
    if not a.binary:
        cmd = [v, '--binary', '--timing', '-Wno-fatal', '-j', '4', '--top-module', 'tb_controller_calendar_native', '-GMUT=0',
               '--Mdir', str(out / 'obj')] + [str(ROOT / f) for f in FILES]
        with (out / 'build.log').open('w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    results, bad = [], 0
    for pc in a.pc:
        s, pcl = divmod(pc, 32)
        words = [int(x, 16) for x in (a.compile_dir / f'target{6 + s}.hex').read_text().split()][32 * pcl:32 * pcl + 32]
        image = [words[n] | (words[16 + n] << 64) for n in range(16)]
        exp = [0] * 4096
        for w in image:
            if not w:
                continue
            d = decode(w)
            if d['mask'] == 1:
                for i in range(d['count']):
                    exp[d['edge'] + i + (i // d['burst']) * d['gap']] = 1
        d = out / f'pc{pc}'
        d.mkdir(exist_ok=True)
        (d / 'image.hex').write_text(''.join(f'{w:032x}\n' for w in image))
        (d / 'expected_rd.hex').write_text(''.join(f'{e:x}\n' for e in exp))
        for jit in (0, 8, 16):
            p = subprocess.run([str(binary), f'+IMAGE={d}/image.hex', f'+JITTER={jit}', f'+EXPECT={d}/expected_rd.hex'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            line = next((l for l in p.stdout.splitlines() if 'PASS native' in l or 'FAIL' in l), p.stdout[-300:])
            ok = p.returncode == 0 and 'PASS native' in p.stdout
            bad += not ok
            results.append(dict(pc=pc, jitter=jit, exit=p.returncode, result=line.strip(), reads=sum(exp)))
    receipt = dict(schema='opentallas.qwen_kv_static.programme_ctrl_rtl.v1', results=results, failed=bad,
                   source_sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES},
                   binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                   scope='compiled per-PC controller calendar words on the actual controller + PROFILE0 JEDEC core bench '
                         '(PHY modeled); not the joined subsystem, not physical')
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'RESULT {"OK" if not bad else "FAIL"} controller compiled runs={len(results)} failed={bad}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
