#!/usr/bin/env python3
"""Run the existing checkpoint chunk8 golden gate with an isolated wake binding.

Only the validation array's element binding changes. Generated source is saved
outside the checkout and hashed by the original gate. Original validation and
golden sources, image addressing and public interfaces stay byte-identical.
"""
import argparse
from pathlib import Path
import sys
from w10_validation import rtl_v41_rom_array as gate


if __name__ == '__main__':
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--binding-dir', type=Path, required=True)
    binding, remainder = ap.parse_known_args()
    if '--front-par' in remainder:
        raise SystemExit('FRONT_PAR is rejected; registered wake requires baseline frontend')
    binding.binding_dir.mkdir(parents=True, exist_ok=False)
    original = 'rtl/test/w10_validation/ot_v41_rom_array_w10_test.sv'
    source = (gate.ROOT/original).read_text()
    source = source.replace('ot_v41_rom_elem_w10 #(', 'ot_v41_rom_elem_wake_w10 #(')
    source = source.replace('.FRONT_PAR(FRONT_PAR),', '.FRONT_PAR(FRONT_PAR), .WAKE_REG(1),')
    if '.WAKE_REG(1)' not in source:
        raise SystemExit('validation binding not found')
    wrapper = binding.binding_dir/'array_wake_binding.sv'
    wrapper.write_text(source)
    gate.RTL = [str(wrapper) if p == original else
                'rtl/v41rom/ot_v41_rom_elem_wake_w10.sv' if p == 'rtl/v41rom/ot_v41_rom_elem_w10.sv' else p
                for p in gate.RTL]
    raise SystemExit(gate.main(remainder))
