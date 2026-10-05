#!/usr/bin/env python3
"""Bit-exact reduced Qwen TP2 replay with Verilator leaf hierarchy enabled."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--images', type=Path, required=True)
    ap.add_argument('--verilator', type=Path, required=True)
    ap.add_argument('--hier-vlt', type=Path,
                    help='Use reusable arithmetic hierarchy; omit for matched flat control')
    ap.add_argument('--override-root', type=Path,
                    help='Replace selected RTL files with source-pinned historical versions')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reuse-build', action='store_true',
                    help='Replay an existing compiled binary after restoring exact images')
    ap.add_argument('--adopt-sim-log', type=Path,
                    help='Record a prior successful binary replay from this build')
    args = ap.parse_args()
    root = args.source_root.resolve()
    images = args.images.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root / 'tools'))
    import rtl_hdc_decode_campaign as C  # noqa: E402
    rtl = [*C.HDC, *C.PIPES,
           *(root / f'rtl/hdc/{name}.sv' for name in
             ('ot_hdc_dyn_ttiles', 'ot_hdc_qwen_int8_arith',
              'ot_hdc_qwen_int8_embed_decode', 'ot_hdc_core_vector_weight')),
           *(root / f'rtl/rom/{name}.sv' for name in
             ('ot_rom_pkg_link', 'ot_rom_pkg_ctrl', 'ot_rom_oneshot_allreduce',
              'ot_rom_tp_seq')),
           root / 'rtl/test/tb_hdc_package_tp_int8.sv']
    if args.override_root:
        override = args.override_root.resolve()
        rtl = [override / p.relative_to(root) if (override / p.relative_to(root)).exists()
               else p for p in rtl]
    harness = root / 'rtl/test/hdc_package_tp_int8_harness.cpp'
    sources = [*rtl, harness, C.ISA_SVH]
    def label(p):
        return str(p.relative_to(root)) if p.is_relative_to(root) else \
            'override/' + str(p.relative_to(override))
    pins = {label(p): sha(p) for p in sources}
    image_pins = {str(p.relative_to(images)): sha(p)
                  for p in sorted(images.rglob('*.hex'))}
    needed = {f'die{die}/{name}.hex' for die in (0, 1)
              for name in ('matrix_int8', 'matrix_scale_bf16',
                           'embed_int8', 'embed_scale_bf16')}
    needed |= {'prompt.hex', 'expect_steps.hex'}
    if missing := sorted(needed - image_pins.keys()):
        ap.error(f'incomplete image tree; missing: {missing}')
    obj = args.out / 'obj'
    cmd = [str(args.verilator), '--cc', '--exe', '--build', '-O1',
           *(['--hierarchical', str(args.hier_vlt.resolve())] if args.hier_vlt else []),
           '--unroll-count', '32', '--unroll-limit', '131072',
           '-Wno-fatal', '-Wno-WIDTH', '-Wno-UNUSED', '-Wno-BLKSEQ',
           '-Wno-TIMESCALEMOD', '-Wno-PINMISSING',
           '--top-module', 'tb_hdc_package_tp_int8',
           '-GD=2', '-GNODES=1', '-GUSERS=1', '-GWROM_WORDS=16384',
           '-Mdir', str(obj), f'-I{C.ISA_SVH.parent}',
           *map(str, rtl), str(harness), '-CFLAGS', '-O1', '-j', '2']
    begin = time.monotonic()
    if args.reuse_build:
        if not (args.out / 'build.log').exists() or not (obj / 'Vtb_hdc_package_tp_int8').exists():
            ap.error('--reuse-build requires the original build.log and compiled binary')
        build_returncode = 0
    else:
        with (args.out / 'build.log').open('w') as stream:
            build = subprocess.run(cmd, cwd=root, stdout=stream,
                                   stderr=subprocess.STDOUT, check=False)
        build_returncode = build.returncode
    sim = None
    if build_returncode == 0 and args.adopt_sim_log:
        (args.out / 'sim.log').write_bytes(args.adopt_sim_log.read_bytes())
        sim_returncode = 0 if 'PASS' in (args.out / 'sim.log').read_text() else 1
    elif build_returncode == 0:
        with (args.out / 'sim.log').open('w') as stream:
            sim = subprocess.run([str(obj / 'Vtb_hdc_package_tp_int8'),
                                  f'+DIR={images}', '+NGEN=3', '+NUSERS=1'],
                                 cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                                 check=False)
        sim_returncode = sim.returncode
    else:
        sim_returncode = None
    log = (args.out / 'sim.log').read_text() if sim_returncode is not None else ''
    match = re.search(r'PKG_TP nodes=(\d+) dies=(\d+) users=(\d+) generated=(\d+) '
                      r'steps_checked=(\d+) mismatches=(\d+) kv_mismatches=(\d+) '
                      r'vm_mismatches=(\d+) total_cycles=(\d+)', log)
    values = dict(zip(('nodes', 'dies', 'users', 'generated', 'steps_checked',
                       'mismatches', 'kv_mismatches', 'vm_mismatches', 'total_cycles'),
                      map(int, match.groups()))) if match else {}
    exact = (build_returncode == 0 and sim_returncode == 0
             and values.get('generated') == 3 and values.get('steps_checked') == 18
             and values.get('mismatches') == values.get('kv_mismatches') ==
             values.get('vm_mismatches') == 0 and 'PASS' in log)
    result = {'schema': 'opentallas.qwen-reduced-hier-exact.v1',
              'status': 'pass' if exact else 'fail',
              'claim_boundary': 'Reduced unfolded-norm G4 TP2 exact arithmetic; hierarchy compile equivalence only, not full O4 throughput.',
              'rtl': values, 'build_returncode': build_returncode,
              'reused_build': args.reuse_build,
              'sim_returncode': sim_returncode,
              'wall_seconds': round(time.monotonic()-begin, 3),
              'verilator_version': subprocess.check_output([args.verilator, '--version'], text=True).strip(),
              'source_sha256': pins, 'image_sha256': image_pins,
              'binary_sha256': sha(obj/'Vtb_hdc_package_tp_int8') if build_returncode == 0 else None,
              'source_stable': pins == {label(p): sha(p) for p in sources},
              'image_stable': image_pins == {str(p.relative_to(images)): sha(p)
                                            for p in sorted(images.rglob('*.hex'))},
              'hier_vlt_sha256': sha(args.hier_vlt) if args.hier_vlt else None,
              'build_log_sha256': sha(args.out/'build.log'),
              'sim_log_sha256': sha(args.out/'sim.log') if sim_returncode is not None else None,
              'command': cmd}
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'rtl', 'wall_seconds',
                                             'source_stable', 'build_returncode',
                                             'sim_returncode')}))
    raise SystemExit(0 if exact else 1)


if __name__ == '__main__':
    main()
