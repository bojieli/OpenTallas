#!/usr/bin/env python3
"""Lint the changed full-shape join against retained authoritative core leaves.

Run remotely inside the unchanged admission guard. Does not compile C++,
run a token, mutate the retained build or launch its prepared test cases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

TOP = 'ot_qwen_rom_combined_p0_20261005'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authority-job', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verilator', required=True)
    args = parser.parse_args()
    if float(Path('/proc/loadavg').read_text().split()[0]) >= 128:
        raise RuntimeError('E2 immediate post-guard load >=128; no lint launched')
    job, root, output = args.authority_job, args.source_root, args.output
    output.mkdir(parents=True, exist_ok=False)
    text = (job/'top.args.f').read_text()
    paths = []
    replace = {'ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv':
               'rtl/experimental/qwen_rom_combined_p0_20261005/'+TOP+'.sv',
               'ot_qwen_hbm_stream4_tagged.sv':'rtl/hdc/kv/ot_qwen_hbm_stream4_cdc.sv',
               'ot_hbm_r14_stream_pc.sv':'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv',
               'ot_hbm_r14_stream_stack.sv':'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv'}
    for line in text.splitlines():
        if line.startswith('--top-module'):
            break
        path = Path(line)
        path = root/replace[path.name] if path.name in replace else path
        if not path.is_absolute():
            path = job/'die'/path
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.append(path)
    deps = [root/p for p in (
        'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/lib/ot_reset_sync.sv',
        'rtl/hdc/kv/ot_qwen_s4_checked_state.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_pc.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_control.sv',
        'rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv')]
    paths = deps+paths
    selection = json.loads((job/'selection.json').read_text())
    params = selection['parameters']['die']
    params = [v for v in params if not v.startswith('-GHBM_PULLIN=')]
    params += ['-GHBM_PULLIN=0', '-GPROTECTED_STREAM4=1']
    hierarchy = []
    for line in text.splitlines():
        if line.startswith('--hierarchical-block'):
            hierarchy += shlex.split(line)
    include = '/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc'
    command = [args.verilator, '--lint-only', '--top-module', TOP,
               '--prefix', 'Vdie', '--Mdir', str(output/'lint'),
               '-Wno-fatal', '-Wno-TIMESCALEMOD', '-I'+include,
               *hierarchy, *params, *map(str, paths)]
    pins = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (output/'command.json').write_text(json.dumps(command, indent=2)+'\n')
    (output/'source_sha256.json').write_text(json.dumps(pins, indent=2)+'\n')
    with (output/'lint.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    stable = all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
    (output/'terminal.json').write_text(json.dumps(dict(
        exit=result.returncode, source_stable=stable,
        scope='Changed actual fullshape consumer/protected simulation backend elaboration only',
        full_token_run=False, physical_qualified=False, adopted=False), indent=2)+'\n')
    return result.returncode if stable else 1


if __name__ == '__main__':
    raise SystemExit(main())
