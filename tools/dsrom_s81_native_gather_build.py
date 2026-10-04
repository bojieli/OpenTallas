#!/usr/bin/env python3
"""Build only the native TP4 gather archive and its shared-runtime provider.

No whole core, VM or model sweep. Existing W15 native link module is extracted
byte-for-byte; archive-only build does not supply peer operands or publication.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    'rtl/test/dsrom_s81_native_gather/DsromTp4Gather.sv',
    'rtl/chip/ot_w15_coll_dma.sv', 'rtl/chip/ot_chip_v41x_coll_transpose.sv',
    'rtl/rom/ot_rom_oneshot_px.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
    'rtl/proto/ot_fp32_add_rne_pipe.sv',
]
LINK_SOURCE = 'rtl/test/tb_v41_stage_collective_px.sv'


def link_module(root=ROOT):
    source = (root / LINK_SOURCE).read_text()
    begin = source.index('module ot_v41px_link #(')
    end = source.index('endmodule', begin) + len('endmodule')
    return source[begin:end] + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--reuse-archive', type=Path,
                        help='source-matched completed native archive; compile provider only')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('positive build allocation required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise RuntimeError('use a pinned clean worktree')
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    obj = args.out / 'obj'
    link = args.out / 'ot_v41px_link.sv'
    link.write_text(link_module())
    include = ROOT / 'tools/runtime/dsrom'
    cmd = [args.verilator, '--cc', '--top-module', 'DsromTp4Gather',
           '--prefix', 'VDsromTp4Gather', '--Mdir', str(obj), '-Wno-fatal',
           '--output-split', '20000', '--output-split-cfuncs', '200',
           *[str(ROOT / p) for p in SOURCES], str(link)]
    record = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_pins': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES + [LINK_SOURCE]},
              'supervisor_pid': os.getpid(), 'commands': [], 'stages': [],
              'scope': 'native TP4 gather archive/provider, not joined first-token or physical qualification'}
    if args.reuse_archive:
        retained = args.reuse_archive.resolve()
        prior = json.loads((retained / 'terminal.json').read_text())
        if prior['source_pins'] != record['source_pins']:
            raise RuntimeError('retained RTL archive source mismatch')
        stages = {stage['name']: stage['exit'] for stage in prior['stages']}
        if stages.get('frontend') != 0 or stages.get('archive') != 0:
            raise RuntimeError('retained archive was not completed')
        obj = retained / 'obj'
        archive = obj / 'VDsromTp4Gather__ALL.a'
        record['reused_archive'] = {'path': str(archive), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    exit_code = 1
    try:
        commands = [('frontend', cmd), ('archive', ['make', '-C', str(obj), '-f', 'VDsromTp4Gather.mk',
                    '-j' + str(args.jobs), 'OPT_FAST=-O0', 'OPT_SLOW=-O0', 'VDsromTp4Gather__ALL.a'])]
        if args.reuse_archive:
            commands = []
        verilator_root = next(line.split('=', 1)[1].strip() for line in
                             (obj / 'VDsromTp4Gather.mk').read_text().splitlines()
                             if line.startswith('VERILATOR_ROOT =')) if args.reuse_archive else None
        # The selected tool installs headers in share/verilator/include.
        vinclude = Path(verilator_root) / 'include' if verilator_root else Path(args.verilator).resolve().parents[1] / 'share/verilator/include'
        commands.append(('provider', ['g++', '-std=c++17', '-O0', '-pthread',
                         '-I' + str(include), '-I' + str(obj),
                         '-I' + str(ROOT / 'rtl/test/v41_runtime'),
                         '-I' + str(ROOT / 'rtl/test/v41_runtime/s81_selected'),
                         '-I' + str(vinclude),
                         '-c', str(include / 's81_minimum_tp4_gather.cpp'),
                         '-o', str(args.out / 's81_minimum_tp4_gather.o')]))
        for name, command in commands:
            record['commands'].append(command)
            start = time.monotonic()
            with (args.out / (name + '.log')).open('x') as log:
                proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                record['active_pid'] = proc.pid
                (args.out / 'start.json').write_text(json.dumps(record, indent=2) + '\n')
                exit_code = proc.wait()
            record['stages'].append({'name': name, 'exit': exit_code, 'wall_seconds': time.monotonic() - start})
            if exit_code:
                break
        if not exit_code:
            artifacts = [obj / 'VDsromTp4Gather.h', obj / 'VDsromTp4Gather__ALL.a', args.out / 's81_minimum_tp4_gather.o']
            record['artifacts'] = {str(p): {'bytes': p.stat().st_size,
                                   'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in artifacts}
    finally:
        record['exit'] = exit_code
        record['verdict'] = 'PASS_ARCHIVE_PROVIDER_ONLY' if not exit_code else 'FAIL_PRESERVED'
        (args.out / 'terminal.json').write_text(json.dumps(record, indent=2) + '\n')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
