#!/usr/bin/env python3
"""Bounded Verilator front-end probe for the real Qwen layer0 RTL top.

This only elaborates/lints the same sources as the layer0 runner. It does not
run a token, build C++, or establish a throughput or bit-exact RTL result.
Run inside an external CPU/memory cgroup when probing large G values.
"""
import argparse
import hashlib
import importlib.util
import json
import resource
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runner', type=Path, required=True)
    ap.add_argument('--verilator', type=Path, required=True)
    ap.add_argument('--groups', type=int, required=True)
    ap.add_argument('--top', choices=('package', 'core', 'matvec'), default='package')
    ap.add_argument('--unroll-count', type=int, required=True)
    ap.add_argument('--unroll-limit', type=int, default=131072)
    ap.add_argument('--hier-vlt', type=Path,
                    help='Optional Verilator control file selecting hierarchy blocks')
    ap.add_argument('--override-root', type=Path,
                    help='Use isolated replacement RTL files without touching the frozen source')
    ap.add_argument('--emit-cc', action='store_true',
                    help='Run --cc front-end instead of --lint-only, without C++ compilation')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.groups < 4 or args.unroll_count < 1:
        ap.error('groups and unroll-count must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.runner.resolve().parent))
    spec = importlib.util.spec_from_file_location('qwen_layer0_runner_probe', args.runner)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    override = args.override_root.resolve() if args.override_root else None
    source_paths = [override / p.relative_to(runner.ROOT)
                    if override and (override / p.relative_to(runner.ROOT)).exists() else p
                    for p in runner.SOURCES]
    sources = {str(p.relative_to(runner.ROOT)) if p.is_relative_to(runner.ROOT)
               else 'override/' + str(p.relative_to(override)): sha(p)
               for p in source_paths}
    command = runner.build_command(args.out / 'obj', 1, 1)
    command[0] = str(args.verilator)
    for flag in (('--exe', '--build') if args.emit_cc else ('--cc', '--exe', '--build')):
        command.remove(flag)
    if not args.emit_cc:
        command.insert(1, '--lint-only')
    for flag, value in (('--unroll-count', args.unroll_count),
                        ('--unroll-limit', args.unroll_limit)):
        command[command.index(flag) + 1] = str(value)
    command[command.index('-GG=6144')] = f'-GG={args.groups}'
    command = command[:command.index(str(runner.HARNESS))]
    if override:
        command = [str(override / Path(arg).relative_to(runner.ROOT))
                   if arg.startswith(str(runner.ROOT)) and
                   (override / Path(arg).relative_to(runner.ROOT)).exists() else arg
                   for arg in command]
    if args.top == 'core':
        command[command.index('tb_hdc_qwen_layer0_tp2_postscale_ab')] = 'ot_hdc_core_vector_weight'
        command.remove('-GPOST_SCALE_HBM=1')
        command += ['-GSW=1024', '-GSU_VEC=1', '-GINT8_WEIGHT=1',
                    '-GINT8_SCALE_WCS_BASE=1', '-GKV_FP8=1']
    elif args.top == 'matvec':
        command[command.index('tb_hdc_qwen_layer0_tp2_postscale_ab')] = 'ot_hdc_matvec'
        command.remove('-GPOST_SCALE_HBM=1')
        command += ['-GINT8_WEIGHT=1', '-GINT8_SCALE_WCS_BASE=1']
    if args.hier_vlt:
        command += ['--hierarchical', str(args.hier_vlt.resolve())]
    before = time.monotonic()
    with (args.out / 'frontend.log').open('w') as log:
        completed = subprocess.run(command, cwd=runner.ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, check=False)
    result = {
        'schema': 'opentallas.qwen-verilator-frontend-probe.v1',
        'claim_boundary': 'Verilator front-end only; no C++ compilation, RTL token, P&R, or rate.',
        'runner': str(args.runner.resolve()), 'verilator': str(args.verilator.resolve()),
        'verilator_version': subprocess.check_output([args.verilator, '--version'], text=True).strip(),
        'groups': args.groups, 'top': args.top, 'emit_cc': args.emit_cc,
        'unroll_count': args.unroll_count,
        'unroll_limit': args.unroll_limit, 'command': command,
        'hier_vlt_sha256': sha(args.hier_vlt) if args.hier_vlt else None,
        'returncode': completed.returncode, 'wall_seconds': round(time.monotonic() - before, 3),
        'child_maxrss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'source_sha256': sources, 'source_stable': sources ==
            {str(p.relative_to(runner.ROOT)) if p.is_relative_to(runner.ROOT)
             else 'override/' + str(p.relative_to(override)): sha(p)
             for p in source_paths},
        'frontend_log_sha256': sha(args.out / 'frontend.log'),
    }
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('groups', 'unroll_count', 'returncode',
                                             'wall_seconds', 'child_maxrss_kib',
                                             'source_stable')}))
    raise SystemExit(completed.returncode)


if __name__ == '__main__':
    main()
