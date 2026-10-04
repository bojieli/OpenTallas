#!/usr/bin/env python3
"""Build ONE unchanged native SRAM macro C ABI for shared-clock simulation.

No backend RTL regeneration, artificial ACK, protection, physical timing or
selected W11 bank-service claim. The caller owns the clock and must keep
accepted owner debt through enclosing command/commit/receipt RTL.
"""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--verilator', default='verilator')
    p.add_argument('--cxx', default='g++')
    a = p.parse_args()
    version = subprocess.check_output([a.verilator, '--version'], text=True).strip()
    if not version.startswith('Verilator 5.'):
        p.error('native Context ABI requires Verilator 5.x; select the installed 5.050 tool explicitly')
    root = Path(__file__).resolve().parents[1]
    support = root / 'tools/runtime/dsrom'
    macro = root / 'results/uarch/dsrom_native_masked_backend_r2_20261003/inputs/native_sram.v'
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    model = a.output / 'model'
    commands = [
        [a.verilator, '--cc', '--build', '-j', '1', '--top-module',
         'ot_sram_1r1w_512x128_m4_r2c2', '--prefix', 'Vnative_sram',
         '--Mdir', str(model), '-Wno-fatal', '-CFLAGS', '-fPIC', str(macro)],
    ]
    with (a.output / 'build.log').open('x') as log:
        subprocess.run(commands[0], check=True, stdout=log, stderr=subprocess.STDOUT)
        vr = subprocess.check_output([a.verilator, '--getenv', 'VERILATOR_ROOT'], text=True).strip()
        inc = Path(vr) / 'include'
        commands.append([a.cxx, '-std=c++17', '-shared', '-fPIC', '-pthread',
                         '-I'+str(model), '-I'+str(inc), '-I'+str(support),
                         str(support / 's81_minimum_sram.cpp'),
                         str(model / 'Vnative_sram__ALL.a'),
                         str(inc / 'verilated.cpp'), str(inc / 'verilated_threads.cpp'),
                         '-o', str(a.output / 'libdsrom_s81_minimum_sram.so')])
        subprocess.run(commands[1], check=True, stdout=log, stderr=subprocess.STDOUT)
    (a.output / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    print(a.output / 'libdsrom_s81_minimum_sram.so')


if __name__ == '__main__':
    main()
