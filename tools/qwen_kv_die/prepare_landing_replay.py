#!/usr/bin/env python3
"""Prepare source-pinned actual controller/canonical-V/mapped-landing replay.

This prepares a component gate with common leaf clocks, fixture EXP input and
actual off-chip HBM storage. It does not qualify the native attention programme.
Run the resulting run.sh only through resource admission on a compute host.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

P = 'rtl/qwen_sys/static_kv_20261014/'
CONTROLLER = [P + n + '.sv' for n in (
    'ot_qkd_static_emb_cdc', 'qkd_static_kv_write_observer', 'qkd_ctrl_pc_host_static',
    'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_kv_timing')]
CONTROLLER += ['rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv',
               'rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv',
               'rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv',
               'rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv',
               'rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv',
               'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixtures', type=Path, required=True, help='Frozen p137/p637 tree from a separate compiler execution')
    ap.add_argument('--out', type=Path, required=True, help='Fresh input directory')
    ap.add_argument('--source-revision', default='HEAD')
    args = ap.parse_args()
    if args.out.exists():
        raise ValueError('output must be a fresh directory; preserve existing gate inputs')
    revision = subprocess.check_output(['git', 'rev-parse', args.source_revision], text=True).strip()
    args.out.mkdir(parents=True)
    source = args.out / 'source'
    origins = {}

    def export(rev, original, destination=None):
        data = subprocess.check_output(['git', 'show', rev + ':' + original])
        name = destination or original
        dst = source / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        origins[name] = dict(revision=rev, original=original, sha256=hashlib.sha256(data).hexdigest())

    for name in CONTROLLER:
        export('3221e4f5e', name)
    export('df5c31ed0', P + 'qkd_static_kv_return_slots.sv')
    export('8539ea1ef', P + 'qkd_static_kv_return_calendar.sv')
    for name in ('qkd_static_kv_landing', 'qkd_static_kv_landing_physical', 'qkd_static_kv_hop'):
        export(revision, P + name + '.sv')
    export(revision, 'rtl/test/qwen_static_kv/tb_static_paced_v_landing_full128.sv')
    export('385bc2d8b', 'rtl/hdc/nearhbm/ot_qwen_tp8_vrow_static.sv')
    export(revision, 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
           'physical_macro_model/ot_sram_1r1w_128x256_m1_r2c2.sv')
    shutil.copytree(args.fixtures, args.out / 'fixtures')
    runner = subprocess.check_output(['git', 'show', revision + ':tools/qwen_static_kv/run_paced_v_landing_full128.sh'])
    (args.out / 'run.sh').write_bytes(runner)
    compiler_name = 'tools/qwen_kv_die/return_landing_admission.py'
    compiler_data = subprocess.check_output(['git', 'show', revision + ':' + compiler_name])
    compiler = args.out / 'compile_requests.py'
    compiler.write_bytes(compiler_data)
    subprocess.run([sys.executable, str(compiler), '--fixture-directory', str(args.out / 'fixtures'),
                    '--output', str(args.out / 'capacity.json'), '--calendar-directory', str(args.out / 'landing_calendar')], check=True)
    fixture_hashes = {p.relative_to(args.out / 'fixtures').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((args.out / 'fixtures').rglob('*.mem'))}
    if len(fixture_hashes) != 256:
        raise ValueError('full128 two-phase replay requires 256 frozen fixtures')
    (args.out / 'input_manifest.json').write_text(json.dumps(dict(
        scope='COMPONENT_ONLY: actual controller/canonical two V issuers/mapped landing; physical/native programme OPEN',
        source_revision=revision, sources=origins, fixtures=fixture_hashes,
        compiler=dict(revision=revision, original=compiler_name, sha256=hashlib.sha256(compiler_data).hexdigest()),
        runner_sha256=hashlib.sha256(runner).hexdigest()), indent=2) + '\n')
    print(f'Prepared {len(origins)} RTL/provider inputs and 256 fixtures: {args.out}')


if __name__ == '__main__':
    main()
