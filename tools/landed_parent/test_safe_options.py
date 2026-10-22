"""Focused source-generation and ring equivalence checks; run simulation on fleet."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

import lp


def main():
    root = lp.ROOT
    with tempfile.TemporaryDirectory(prefix='safe_lp_', dir=root / 'tools/landed_parent') as td:
        d = Path(td)
        old = d / 'baseline.py'
        old.write_text(Path(os.environ['LP_BASELINE_FILE']).read_text() if 'LP_BASELINE_FILE' in os.environ else
                       subprocess.check_output(['git', '-C', str(root), 'show',
                                                '4d2cb6301:tools/landed_parent/lp.py'], text=True))
        modspec = importlib.util.spec_from_file_location('lp_before_safe_options', old)
        base = importlib.util.module_from_spec(modspec)
        modspec.loader.exec_module(base)
        base.ROOT = root
        (d / 'child.sv').write_text(lp.SELFTEST_CHILD)
        (d / 'top.sv').write_text(lp.SELFTEST_TOP)
        rel = d.relative_to(root)
        spec = dict(top='lpt_top', sources=[f'{rel}/top.sv'], child_sources=[f'{rel}/child.sv'],
                    out_dir=str(rel), params={'W': 1073}, clock_ports=['clk'], clock_pins=['clk'],
                    reset_port='rst_n', reset_pins=['rst_n'],
                    regions=[dict(name='ra', insts=['u0', 'u3'], centre=[0, 0]),
                             dict(name='rb', insts=['u1', 'u2'], centre=[900, 0])])
        for cls in (base.Parent, lp.Parent):
            model = cls(spec)
            plan = model.plan()
            values = (model.emit(plan, 'lpt_top_lp'), model.sdc(plan, 'lpt_top_lp'),
                      json.dumps(model.record(plan, 'lpt_top_lp', dict(zip(
                          ['reset_region', 'hops', 'RB'], model.reset_tree()))), sort_keys=True))
            if cls is base.Parent:
                expected = values
            else:
                assert values == expected, 'default generated RTL/SDC/record drifted'
        print('SAFE_LP DEFAULT_BYTE_IDENTICAL PASS')
        safe = dict(spec, landing_chunk_bits=24, landing_direct_timing=True)
        model = lp.Parent(safe)
        plan = model.plan()
        rtl, _ = model.emit(plan, 'lpt_top_lp')
        sdc = model.sdc(plan, 'lpt_top_lp')
        assert 'ot_pl_land_chunk_w' in rtl and '.CHUNK_BITS(24)' in rtl
        assert 'set_multicycle_path' not in sdc and 'set_false_path' not in sdc
        assert '120.0 + 0.75 * $ot_lp_per' in sdc and '85.0' in sdc
        assert lp.audit(safe, rtl)['ok']
        assert not lp.audit(safe, model.emit(model.plan(mut_unland=True), 'lpt_top_lp')[0])['ok']
        try:
            lp.Parent(dict(safe, E=3))
        except SystemExit:
            pass
        else:
            raise AssertionError('unproved D4/E3 envelope was accepted')
        print('SAFE_LP DIRECT_TIMING_AND_UNLANDED_MUTANT PASS')
        # Compare every physical slot bit and the capture word, including the
        # partial final chunk, through repeated reset, random data and wrapping.
        tb = d / 'tb.sv'
        tb.write_text('''`timescale 1ns/1ps
module tb;
  reg cw=0, cr=0, rsi=0;
  always #0.5 cw=~cw;
  initial begin #0.125; forever #0.5 cr=~cr; end
  reg [1072:0] data=0;
  wire [4291:0] a,b;
  wire [11:0] ae,be; wire[3:0] av; wire[4*((1073+23)/24)-1:0] bv;
  wire[1072:0] ar,br;
  ot_pl_land_w #(.W(1073)) wa(cw,rsi,data,a,ae,av);
  ot_pl_land_chunk_w #(.W(1073),.CHUNK_BITS(24)) wb(cw,rsi,data,b,be,bv);
  ot_pl_land_r #(.W(1073)) ra(cr,rsi,a,ae,av,ar);
  ot_pl_land_chunk_r #(.W(1073),.CHUNK_BITS(24)) rb(cr,rsi,b,be,bv,br);
  integer t,j,c,checks=0;
  initial begin
    for(t=0;t<2000;t=t+1) begin
      @(negedge cw); rsi=!(t<8 || (t>=900 && t<908));
      for(j=0;j<1073;j=j+1) data[j]=$random;
      #0.01;
      if(a!==b || ae!==be) $fatal(1,"CHUNK_BANK_MISMATCH t%0d",t);
      for(c=0;c<(1073+23)/24;c=c+1)
        if(av!==bv[4*c+:4]) $fatal(1,"CHUNK_VALID_MISMATCH t%0d c%0d",t,c);
      checks=checks+1;
    end
    $display("SAFE_LP RING_EQ PASS bank_checks%0d",checks); $finish;
  end
  always @(negedge cr) begin
    if(ar!==br) $fatal(1,"CHUNK_READ_MISMATCH");
  end
endmodule
''')
        env = dict(os.environ)
        pinned = Path.home() / '.local/opentallas-tools/verilator-5.050/bin'
        env['PATH'] = str(pinned) + ':' + env['PATH']
        subprocess.run(['verilator', '--binary', '--timing', '-Wno-fatal', '--top-module', 'tb',
                        '--Mdir', str(d / 'obj'), '-j', '4', str(tb),
                        str(root / 'rtl/common/landed_parent/ot_pl_land.sv')], check=True, env=env)
        subprocess.run([str(d / 'obj/Vtb')], check=True)


if __name__ == '__main__':
    main()
