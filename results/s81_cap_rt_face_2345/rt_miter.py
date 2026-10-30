from pathlib import Path
import re,subprocess
w=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-capchildren-2300');o=Path('/srv/opentallas-scratch2/claude/codex-s81-capchildren-2300/rt_miter');o.mkdir(exist_ok=True)
p=w/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv';s=p.read_text();gold=subprocess.check_output(['git','-C',str(w),'show','1abb3fcb1e1e778eace6f9954f35087277bfe227:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv'],text=True)
for name in re.findall(r'^module\s+(\w+)',gold,re.M):gold=re.sub(r'\b'+name+r'\b','old_'+name,gold)
(o/'gold.sv').write_text(gold)
mut=s.replace('module ot_s81sl_cap_rt #','module mut_ot_s81sl_cap_rt #').replace('assign fault = fault_p;','assign fault = fault_p ^ cfg_d[159];')
# Mutant uses the same helpers; rename all its module definitions and references.
for name in re.findall(r'^module\s+(\w+)',s,re.M):
 if name!='ot_s81sl_cap_rt':mut=re.sub(r'\b'+name+r'\b','mut_'+name,mut)
(o/'mut.sv').write_text(mut)
tb='''`timescale 1ps/1ps
module tb;
reg clk=0,rst=0,wv=0,ev=0,we=0,ee=0,wf=0,ef=0,cv=0;reg[31:0]wt=0,et=0,wd=0,ed=0;reg[159:0]cd=0;wire[647:0]a,b,m;
`define CON .clk(clk),.rst_n(rst),.w_v(wv),.w_t(wt),.w_d(wd),.w_e(we),.w_f(wf),.e_v(ev),.e_t(et),.e_d(ed),.e_e(ee),.e_f(ef),.cfg_v(cv),.cfg_d(cd)
old_ot_s81sl_cap_rt gold(`CON,.cw_s_v(a[5:0]),.cw_s_a(a[77:6]),.cw_s_d(a[269:78]),.cw_n_v(a[273:270]),.cw_n_a(a[321:274]),.cw_n_d(a[449:322]),.fault(a[450]));
ot_s81sl_cap_rt dut(`CON,.cw_s_v(b[5:0]),.cw_s_a(b[77:6]),.cw_s_d(b[269:78]),.cw_n_v(b[273:270]),.cw_n_a(b[321:274]),.cw_n_d(b[449:322]),.fault(b[450]));
mut_ot_s81sl_cap_rt mutant(`CON,.cw_s_v(m[5:0]),.cw_s_a(m[77:6]),.cw_s_d(m[269:78]),.cw_n_v(m[273:270]),.cw_n_a(m[321:274]),.cw_n_d(m[449:322]),.fault(m[450]));
reg[31:0]rng=32'h63948271;integer errors=0,muterrors=0,resets=0,configs=0,words=0,faults=0;
function automatic[31:0]random_word(input[31:0]x);reg[31:0]y;y=x^(x<<13);y=y^(y>>17);random_word=y^(y<<5);endfunction
initial forever begin #416 clk=1;#417 clk=0;end
initial begin
repeat(12)@(negedge clk);
for(int i=0;i<12000;i++)begin
 rng=random_word(rng);wv=rng[0];ev=rng[1];we=rng[2];ee=rng[3];wf=(i%233==42);ef=(i%379==65);cv=(i%19==2);
 rng=random_word(rng);wt={rng[31:13],5'd0,3'd0,5'd2};et={rng[31:13],5'd1,3'd0,5'd2};
 rng=random_word(rng);wd=rng;rng=random_word(rng);ed=rng;
 for(int j=0;j<5;j++)begin rng=random_word(rng);cd[j*32+:32]=rng;end
 rst=(i%257>10);if(!rst)resets++;if(cv)configs++;if(wv||ev)words++;
 @(posedge clk);#2;
 if(a[450:0]!==b[450:0])begin if(errors<2)$display("RT_DIFF c=%0d gold=%h dut=%h",i,a[450:0],b[450:0]);errors++;end
 if(a[450:0]!==m[450:0])muterrors++;
 if(a[450]===1)faults++;
 @(negedge clk);
end
if(errors||!muterrors||!faults||configs<100||words<100)$fatal(1,"RT_FAIL mism=%0d mutant=%0d faultedges=%0d cfg=%0d words=%0d",errors,muterrors,faults,configs,words);
$display("CAP_RT_FACE PASS cycles12000 mismatch0 mutant_caught%0d reset_edges%0d fault_edges%0d configs%0d word_edges%0d added_cycles0",muterrors,resets,faults,configs,words);$finish;
end
endmodule
''';(o/'tb.sv').write_text(tb)
files=[w/'rtl/lib/ot_rst_relay.sv',w/'rtl/hdc/ot_hdc_delay.sv',w/'rtl/hdc/ot_hdc_delay_rf.sv',w/'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',p,o/'gold.sv',o/'mut.sv',o/'tb.sv']
subprocess.run(['iverilog','-g2012','-DOT_S81_CAP_RT_FACE_REGS','-s','tb','-o',str(o/'sim')]+[str(f) for f in files],check=True)
subprocess.run(['vvp',str(o/'sim')],check=True)
