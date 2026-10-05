#!/usr/bin/env python3
"""Add opt-in native full-field DPI scopes to a copied existing host.

Unknown scopes use the original host bindings. Exact inverse, no RTL/frontend,
clock, reset, packet, arithmetic, or selected runtime execution changes.
"""
import argparse
from pathlib import Path

INSERTIONS = {
 'extern "C" void v41rt_rom_register(const char* instance) {':
  '\n    if(dsrom_s81_qe_register_rom(instance))return;',
 'extern "C" void v41rt_cfg_register() {':
  '\n    if(dsrom_s81_qe_register_cfg())return;',
 'extern "C" void v41rt_rom_read(int address,svBitVecVal* q) {':
  '\n    if(dsrom_s81_qe_rom_read(address,q))return;',
 'extern "C" long long v41rt_cfg_read(int address) {':
  '\n    long long native_qe_cfg;\n    if(dsrom_s81_qe_cfg_read(address,native_qe_cfg))return native_qe_cfg;',
}
INCLUDE = '#include "s81_minimum_qe_dpi.hpp"\n'

def instrument(original):
    if 's81_minimum_qe_dpi.hpp' in original:
        raise ValueError('already instrumented host')
    result = INCLUDE + original
    for signature, inserted in INSERTIONS.items():
        if result.count(signature) != 1:
            raise ValueError('exact existing DPI signature required: ' + signature)
        result = result.replace(signature, signature + inserted)
    if inverse(result) != original:
        raise ValueError('native host inverse differs from pinned input')
    return result


def inverse(instrumented):
    if not instrumented.startswith(INCLUDE):
        raise ValueError('native hook include absent')
    result = instrumented[len(INCLUDE):]
    for signature, inserted in INSERTIONS.items():
        if result.count(signature + inserted) != 1:
            raise ValueError('copied host hook missing or changed')
        result = result.replace(signature + inserted, signature)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    with a.output.open('x') as out:
        out.write(instrument(a.source.read_text()))

if __name__ == '__main__':
    main()
