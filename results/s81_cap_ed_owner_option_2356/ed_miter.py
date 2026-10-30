#!/usr/bin/env python3
"""CAP_ED owner option (A) lockstep miter, repo-relative (port of Codex 1349c5e86 ed_miter.py / ed_miter_4state.py).

gold  = ot_s81sl_cap_ed.sv at --gold-rev (main before the option; renamed old_ot_s81sl_cap_ed)
dut   = the working-tree ot_s81sl_cap_ed.sv built with -DOT_S81_CAP_ED_FACE_DELAYED_FAULT (the adopted form)
mut   = dut with the raw-fault pin flop bypassed (`if (face_fault_i)` -> `if (i_f)`): the wrong-edge control
Per D in 3/4/23/24, 12000 random edges at 833 ps with 2 reset pulses / 97 edges: every payload/valid bit identical,
dut fault == gold fault delayed exactly one edge (same reset), wrong-edge mutant must mismatch, and the ORIGINAL
0-cycle fault contract must differ (proves the +1 is real and checked).  --four-state injects X on i_f every 31 edges.
    python3 ed_miter.py [--repo .] [--gold-rev 3fc2fcf0d14] [--out DIR] [--four-state]
"""
import argparse, re, subprocess
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument('--repo', default='.'); ap.add_argument('--gold-rev', default='3fc2fcf0d14')
ap.add_argument('--out', default='ed_option_miter'); ap.add_argument('--four-state', action='store_true')
a = ap.parse_args()
w = Path(a.repo).resolve(); o = Path(a.out).resolve(); o.mkdir(parents=True, exist_ok=True)
p = w / 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv'; s = p.read_text()
gold = subprocess.check_output(['git', '-C', str(w), 'show', f'{a.gold_rev}:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv'],
                               text=True).replace('module ot_s81sl_cap_ed', 'module old_ot_s81sl_cap_ed')
assert 'OT_S81_CAP_ED_FACE_DELAYED_FAULT' not in gold, 'gold must be the pre-option RTL'
(o / 'gold.sv').write_text(gold)
assert s.count('if (face_fault_i)') == 1
mut = s.replace('if (face_fault_i)', 'if (i_f)')
for name in re.findall(r'^module\s+(\w+)', s, re.M):
    mut = re.sub(r'\b' + name + r'\b', 'mut_' + name, mut)
(o / 'mut.sv').write_text(mut)
xinj = "if(i%31==7)fi=1'bx;" if a.four_state else ''
tb = '''`timescale 1ps/1ps
module one #(parameter D=24)(output reg done=0);
reg clk=0,rst=0;reg[65:0]d=0;reg fi=0;wire[65:0]a,b,m;wire af,bf,mf;reg expected_f;
`define CON .clk(clk),.rst_n(rst),.i_v(d[0]),.i_t(d[32:1]),.i_d(d[64:33]),.i_e(d[65]),.i_f(fi)
old_ot_s81sl_cap_ed #(D) gold(`CON,.o_v(a[0]),.o_t(a[32:1]),.o_d(a[64:33]),.o_e(a[65]),.o_f(af));
ot_s81sl_cap_ed #(D) dut(`CON,.o_v(b[0]),.o_t(b[32:1]),.o_d(b[64:33]),.o_e(b[65]),.o_f(bf));
mut_ot_s81sl_cap_ed #(D) mutant(`CON,.o_v(m[0]),.o_t(m[32:1]),.o_d(m[64:33]),.o_e(m[65]),.o_f(mf));
always @(posedge clk or negedge gold.rsv[1])if(!gold.rsv[1])expected_f<=0;else expected_f<=af;
reg[31:0]rng=32'h67128493+D;integer errors=0,muterrors=0,zerodiff=0,resets=0;reg[3:0]combos=0;
function automatic[31:0]random_word(input[31:0]x);reg[31:0]y;y=x^(x<<13);y=y^(y>>17);random_word=y^(y<<5);endfunction
initial forever begin #416 clk=1;#417 clk=0;end
initial begin
repeat(8)@(negedge clk);
for(int i=0;i<12000;i++)begin
 rng=random_word(rng);d[31:0]=rng;rng=random_word(rng);d[63:32]=rng;rng=random_word(rng);d[65:64]=rng[1:0];fi=rng[2];XINJcombos[{d[0],fi}]=1;
 rst=(i%97!=41)&&(i%97!=42);if(!rst)resets++;
 @(posedge clk);#2;
 if(a!==b||bf!==expected_f)begin if(errors<2)$display("ED_OPTION_DIFF D=%0d c=%0d data=%b fault=%b/%b",D,i,a!==b,bf,expected_f);errors++;end
 if(mf!==expected_f)muterrors++;if(bf!==af)zerodiff++;
 @(negedge clk);
end
if(errors||!muterrors||!zerodiff||combos!=15)$fatal(1,"ED_OPTION_FAIL D=%0d err=%0d mut=%0d zero=%0d",D,errors,muterrors,zerodiff);
$display("CAP_ED_OWNER_OPTION PASS D=%0d cycles12000 payload_mismatch0 fault_plus1_mismatch0 wrongedge_mutant%0d OLD_FAULT_CONTRACT_DIFFERENCES%0d reset_edges%0d",D,muterrors,zerodiff,resets);done=1;
end
endmodule
module tb;wire[3:0]done;one#(3)a(done[0]);one#(4)b(done[1]);one#(23)c(done[2]);one#(24)d(done[3]);initial begin wait(&done);$display("CAP_ED_OWNER_OPTION ALL_PASS payload_cycles0 fault_visibility_cycles1 FOURSTATE=%0d",FS);$finish;end endmodule
'''.replace('XINJ', xinj).replace('FS', '1' if a.four_state else '0')
(o / 'tb.sv').write_text(tb)
files = [w / 'rtl/lib/ot_rst_relay.sv', w / 'rtl/hdc/ot_hdc_delay_rf.sv', p, o / 'gold.sv', o / 'mut.sv', o / 'tb.sv']
subprocess.run(['iverilog', '-g2012', '-DOT_S81_CAP_ED_FACE_DELAYED_FAULT', '-s', 'tb', '-o', str(o / 'sim')] + [str(f) for f in files], check=True)
subprocess.run(['vvp', '-n', str(o / 'sim')], check=True)
