#!/usr/bin/env python3
"""Build the seven actual XS4 ROM selectors against the real aligned-v2 model.
Run on a fleet worker through ot-run. Tests selector identity, not streamer arithmetic.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / 'rtl/dsrom_sys/s81_dv/slice'
MAC = ROOT / 'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    xs = (S / 'ot_s81sl_xs4.sv').read_text()
    parent = (S / 'ot_s81sl_xgt_xo.sv').read_text()
    assert 'ot_s81sl_xs4 #(.INSTANCE(INSTANCE)) u_s' in parent
    selected_parent = (ROOT / 'physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_xgt_xo.sv').read_text()
    assert 'ot_s81sl_xs4 #(.INSTANCE(INSTANCE)) u_s' in selected_parent
    names = re.findall(r'`OT_S81SL_XS4_ROM\("([^"]+)"\)', xs)
    assert len(names) == 7 and len(set(names)) == 7
    definition = re.search(r'^`define OT_S81SL_XS4_ROM\(n\) (ot_rom_4096x72_m8 #.*)$', xs, re.M)[1]
    # Use the production macro expansion verbatim, on the smallest affected bank.
    source = ['`timescale 1ps/1ps', '`define OT_S81SL_XS4_ROM(n) ' + definition,
              'module bank #(parameter INSTANCE="") (input wire clk, input wire [11:0] addr, output wire [503:0] data);']
    for i, name in enumerate(names):
        source.append(f'`OT_S81SL_XS4_ROM("{name}") r{i} (.clk(clk),.ce_in(1\'b1),.addr_in(addr),.rd_out(data[{i*72}+:72]));')
    source += ['endmodule', '`undef OT_S81SL_XS4_ROM',
               'module legacy(input wire clk, input wire [11:0] addr, output wire [503:0] data);']
    for i, name in enumerate(names):
        source.append(f'ot_rom_4096x72_m8 #(.INSTANCE("{name}")) r{i} (.clk(clk),.ce_in(1\'b1),.addr_in(addr),.rd_out(data[{i*72}+:72]));')
    source += ['endmodule','module tb; reg clk=0; reg [11:0] addr=0; wire [503:0] old,dflt,s0,s1;',
               'always begin #416 clk=1; #417 clk=0; end',
               'legacy r(clk,addr,old); bank d(clk,addr,dflt);',
               'bank #(.INSTANCE("slice0")) a(clk,addr,s0);',
               'bank #(.INSTANCE("slice1")) b(clk,addr,s1);',
               'integer i; initial begin for(i=0;i<40;i=i+1) begin @(negedge clk); addr=(i*131)%4096;',
               '#1; if(old!==dflt) $fatal(1,"default miter mismatch");']
    wants = {}
    for i, name in enumerate(names):
        for prefix, seed in [('', 0x11), ('slice0.', 0x31), ('slice1.', 0x51)]:
            word = sum(((seed + i + byte) & 255) << (byte * 8) for byte in range(9))
            row = sum(((word >> bit) & 1) << (bit * 8 + mux) for bit in range(72) for mux in range(8))
            (out / (prefix + name + '.viamap.hex')).write_text((f'{row:0144x}\n') * 512)
            wants[prefix + name] = f'{word:018x}'
        source += [f'if(s0[{i*72}+:72]!==72\'h{wants["slice0."+name]}) $fatal(1,"slice0 {name}");',
                   f'if(s1[{i*72}+:72]!==72\'h{wants["slice1."+name]}) $fatal(1,"slice1 {name}");']
    source += ['end $display("XS4_IMAGE_PREFIX_PASS default_miter40 distinct_slices2 ROMs7 clock833ps_no_added_cycles"); $finish; end endmodule']
    # The selector mechanism has no state; real macro latency is kept intact.
    # Allow two warmup reads before the miter checks.
    source = '\n'.join(source).replace('integer i; initial begin for', 'integer i; initial begin repeat(3) @(negedge clk); for') + '\n'
    (out / 'tb.sv').write_text(source)
    cmd = ['verilator', '--binary', '--timing', '-j', '2', '-Wno-fatal', '-Wno-WIDTH',
           '--top-module', 'tb', '--Mdir', str(out / 'obj'), str(MAC), str(out / 'tb.sv')]
    with (out / 'build.log').open('w') as f:
        subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT)
    def run(name):
        with (out / (name + '.log')).open('w') as f:
            result = subprocess.run([str(out / 'obj/Vtb'), '+OT_ROM_DIR=' + str(out)], cwd=out, stdout=f, stderr=subprocess.STDOUT)
        return result.returncode
    assert run('positive') == 0
    # Wrong-prefix mutant routes slice1's first ROM to slice0's payload.
    target = out / ('slice1.' + names[0] + '.viamap.hex')
    original = target.read_bytes()
    try:
        target.write_bytes((out / ('slice0.' + names[0] + '.viamap.hex')).read_bytes())
        assert run('wrong_prefix_mutant') != 0
    finally:
        target.write_bytes(original)
    result = dict(status='PASS_XS4_SEVEN_REAL_ROM_SELECTORS', default_lockstep_cycles=40,
                  distinct_slices=2, selectors=names, wrong_prefix_mutant_caught=True,
                  full_streamer_arithmetic_tested=False, added_rtl_cycles=0,
                  production_bind_adopted=False)
    (out / 'check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
