#!/usr/bin/env python3
"""Compile the unchanged opt-in 256-macro raw VM subsystem for ACK participants.

This is the owner-authorized minimum bank subsystem, not a field/core array.
Source command/local/macro/old-context ACK pipelines remain in RTL. No mutable
protection, physical latency, selected W11 ports or composed token qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--verilator', required=True)
    a = p.parse_args()
    version = subprocess.check_output([a.verilator, '--version'], text=True).strip()
    if not version.startswith('Verilator 5.'):
        p.error('shared native Context ABI requires the selected Verilator 5.x')
    root = Path(__file__).resolve().parents[1]
    sources = [root / 'rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv',
               root / 'results/uarch/dsrom_seven_class_swap_20261003/inputs/native_sram.v']
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    command = [a.verilator, '--cc', '--build', '-j', '1', '--top-module',
               'ot_v41_vm_bank4_macro_pipe_masked_visible_r2', '--prefix', 'Vnative_vm',
               '--Mdir', str(a.output), '-GMASKED_VISIBLE=1', '-GDEPTH_GROUPS=16',
               '-GAW=15', '-GTAG_W=227', '-DOT_MEM_NO_INIT', '-Wno-fatal',
               '-CFLAGS', '-fPIC', *map(str, sources)]
    metadata = dict(command=command, version=version,
                    source_commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
                    inputs={str(s.relative_to(root)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources})
    (a.output / 'build_inputs.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with (a.output / 'build.log').open('x') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    (a.output / 'exit_code').write_text(str(result.returncode)+'\n')
    if result.returncode:
        raise SystemExit(result.returncode)
    print(a.output / 'Vnative_vm__ALL.a')


if __name__ == '__main__':
    main()
