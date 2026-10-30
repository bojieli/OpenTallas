from pathlib import Path
import re,subprocess
w=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-capchildren-2300');o=Path('/srv/opentallas-scratch2/claude/codex-s81-capchildren-2300/ed_option_miter');o.mkdir(exist_ok=True)
p=w/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv';s=p.read_text();gold=subprocess.check_output(['git','-C',str(w),'show','1abb3fcb1e1e778eace6f9954f35087277bfe227:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv'],text=True).replace('module ot_s81sl_cap_ed','module old_ot_s81sl_cap_ed');(o/'gold.sv').write_text(gold)
mut=s.replace('if (face_fault_i)','if (i_f)');
for name in re.findall(r'^module\s+(\w+)',s,re.M):mut=re.sub(r'\b'+name+r'\b','mut_'+name,mut)
(o/'mut.sv').write_text(mut)
tb='''`timescale 1ps/1ps
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
 rng=random_word(rng);d[31:0]=rng;rng=random_word(rng);d[63:32]=rng;rng=random_word(rng);d[65:64]=rng[1:0];fi=rng[2];if(i%31==7)fi=1'bx;combos[{d[0],fi}]=1;
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
module tb;wire[3:0]done;one#(3)a(done[0]);one#(4)b(done[1]);one#(23)c(done[2]);one#(24)d(done[3]);initial begin wait(&done);$display("CAP_ED_OWNER_OPTION ALL_PASS payload_cycles0 fault_visibility_cycles1 NOT_ADOPTED");$finish;end endmodule
''';(o/'tb.sv').write_text(tb)
files=[w/'rtl/lib/ot_rst_relay.sv',w/'rtl/hdc/ot_hdc_delay_rf.sv',p,o/'gold.sv',o/'mut.sv',o/'tb.sv']
subprocess.run(['iverilog','-g2012','-DOT_S81_CAP_ED_FACE_DELAYED_FAULT','-s','tb','-o',str(o/'sim')]+[str(f) for f in files],check=True);subprocess.run(['vvp',str(o/'sim')],check=True)
