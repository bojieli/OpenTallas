from pathlib import Path
import re,subprocess
w=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-capchildren-2300');o=Path('/srv/opentallas-scratch2/claude/codex-s81-capchildren-2300/ld_miter');o.mkdir(exist_ok=True)
p=w/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv';s=p.read_text();gold=subprocess.check_output(['git','-C',str(w),'show','1abb3fcb1e1e778eace6f9954f35087277bfe227:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv'],text=True).replace('module ot_s81sl_cap_ld','module old_ot_s81sl_cap_ld');(o/'gold.sv').write_text(gold)
mut=s.replace('module ot_s81sl_cap_ld','module mut_ot_s81sl_cap_ld').replace('(primed || cnt == D[CW-1:0])','primed');(o/'mut.sv').write_text(mut)
tb='''`timescale 1ps/1ps
module one #(parameter D=16)(output reg done=0);
reg clk=0,rst=0;reg[69:0] data=0;wire[69:0] a,b,m;integer errors=0,muterrors=0,resets=0;reg[31:0] rng=32'h47219385+D;reg[3:0] combos=0;
old_ot_s81sl_cap_ld #(D) gold(clk,rst,data,a);
ot_s81sl_cap_ld #(D) dut(clk,rst,data,b);
mut_ot_s81sl_cap_ld #(D) mutant(clk,rst,data,m);
initial forever begin #416 clk=1;#417 clk=0;end
function automatic[31:0] random_word(input[31:0] x);reg[31:0] y;y=x^(x<<13);y=y^(y>>17);random_word=y^(y<<5);endfunction
initial begin
repeat(5)@(negedge clk);
for(int i=0;i<12000;i++)begin
 rng=random_word(rng);data[31:0]=rng;rng=random_word(rng);data[63:32]=rng;rng=random_word(rng);data[69:64]=rng[5:0];
 rst=(i%97!=41)&&(i%97!=42);if(!rst)resets++;
 combos[{data[1],data[0]}]=1;
 @(posedge clk);#2;
 if(a!==b)begin if(errors<2)$display("LD_DIFF D=%0d c=%0d a=%h b=%h",D,i,a,b);errors++;end
 if(a!==m)muterrors++;
 @(negedge clk);
end
if(errors || !muterrors || combos!=15)$fatal(1,"LD_FAIL D=%0d mism=%0d mutant=%0d combos=%h",D,errors,muterrors,combos);
$display("CAP_LD_FACE PASS D=%0d cycles=12000 mismatch=0 reset_edges=%0d mutant_caught=%0d input_pairs=%h",D,resets,muterrors,combos);done=1;
end
endmodule
module tb;wire[3:0]done;one#(3)a(done[0]);one#(4)b(done[1]);one#(8)c(done[2]);one#(16)d(done[3]);initial begin wait(&done);$display("CAP_LD_FACE ALL_PASS added_cycles=0 clock_ps=833");$finish;end endmodule
''';(o/'tb.sv').write_text(tb)
cmd=['iverilog','-g2012','-DOT_S81_CAP_LD_FACE_VALID','-s','tb','-o',str(o/'sim'),str(w/'rtl/lib/ot_rst_relay.sv'),str(w/'rtl/hdc/ot_hdc_delay_rf.sv'),str(p),str(o/'gold.sv'),str(o/'mut.sv'),str(o/'tb.sv')]
subprocess.run(cmd,check=True);subprocess.run(['vvp',str(o/'sim')],check=True)
