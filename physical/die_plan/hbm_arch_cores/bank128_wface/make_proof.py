from pathlib import Path
import re
r=Path(__file__).resolve().parents[4]; q=r/'physical/die_plan/hbm_arch_cores/bank128_wface'; o=q/'proof';o.mkdir(exist_ok=True)
s=(r/'rtl/hbm_accel/cores_split/ot_hbm_hc_native128/ot_hbm_hc_bank128_pair_core.sv').read_text().split('endmodule',1)[0]+'endmodule\n'
# Retain real top-level SRAM wiring; replace unchanged arithmetic leaves with
# cut stubs because this proof is the programming/SRAM boundary mechanism.
mods=re.findall(r'(?m)^  (\\ot_hdc_v41x_hcp_lanes\$\S+)  ',s)
stubs='\n'.join('module '+m+' (clk,y,rst_n,fst,gov_i,lv_i,ss_i,w_i,x_i,s_i,lf); input clk,rst_n,fst,gov_i,ss_i; input[7:0]lv_i; input[255:0]w_i,s_i; input[127:0]x_i; output[255:0]y; output lf; assign y=0;assign lf=0; endmodule' for m in mods)
for name,change in [('good',None),('mut_data',('wface_data <= write_data;','wface_data <= write_data ^ 512\'h1;')),('mut_enable',('wface_we1 <= weight_we1;','wface_we1 <= weight_we0;')),('mut_addr',('wface_addr <= write_addr;','wface_addr <= write_addr ^ 10\'h1;'))]:
 t=s
 if change:assert change[0] in t;t=t.replace(*change)
 (o/(name+'.sv')).write_text('`define OT_HC128_WFACE\n'+t.replace('module ot_hbm_hc_bank128_pair_core(','module bank_new(',1)+'`undef OT_HC128_WFACE\n'+s.replace('module ot_hbm_hc_bank128_pair_core(','module bank_old(',1)+stubs+'\n')
mem=''
for name,aw in [('ot_sram_1r1w_1024x256_m2_r2c2',10),('ot_sram_1r1w_128x256_m1_r2c2',7)]:
 mem+=f'''module {name}(input clk,input[1:0] cr_en,input[15:0]cr_sel,input[{aw-1}:0]r_addr_in,input r_ce_in,output reg[255:0]rd_out,input[{2*aw-3}:0]rr_addr,input[1:0]rr_en,input[{aw-1}:0]w_addr_in,input w_ce_in,input[255:0]w_mask_in,wd_in);
reg[255:0]mem[0:{(1<<aw)-1}]; integer b;
always @(posedge clk) begin
 if(r_ce_in)rd_out<=mem[r_addr_in];
 if(w_ce_in)for(b=0;b<256;b=b+1)if(w_mask_in[b])mem[w_addr_in][b]<=wd_in[b];
end endmodule
'''
(o/'mem.sv').write_text(mem)
ports='''.clk(clk),.rst_n(rst_n),.go(1'b0),.lane_valid(16'b0),.square(1'b0),.sum_in(512'b0),.weight_addr(ra),.weight_read(re),.x_addr(ra[6:0]),.x_read(re),.sum_out(),.fault()'''
tb='''module tb; reg clk=0;always #5 clk=~clk;reg rst_n=0;reg[511:0]wd,wdq;reg[9:0]wa,waq,ra;reg we0,we1,xwe,we0q,we1q,xweq,re;integer i,j,checks=0;integer seed=32'h2891;
always @(posedge clk)begin wdq<=wd;waq<=wa;if(!rst_n)begin we0q<=0;we1q<=0;xweq<=0;end else begin we0q<=we0;we1q<=we1;xweq<=xwe;end end
bank_new n('''+ports+''',.write_data(wd),.write_addr(wa),.weight_we0(we0),.weight_we1(we1),.x_write(xwe));
bank_old g('''+ports+''',.write_data(wdq),.write_addr(waq),.weight_we0(we0q),.weight_we1(we1q),.x_write(xweq));
initial begin wd=0;wa=0;ra=0;we0=0;we1=0;xwe=0;re=0;
for(i=0;i<3000;i=i+1)begin @(negedge clk);rst_n=(i>=3 && i%317!=0);wa=$random(seed)&31;ra=$random(seed)&31;re=1;
we0=rst_n&$random(seed);we1=rst_n&$random(seed);xwe=rst_n&$random(seed);for(j=0;j<16;j=j+1)wd[j*32+:32]=$random(seed);
@(posedge clk);#1;
'''
for m in ['g_w[0]','g_w[1]','g_x[0]']:
 inst='\\u_c.u_b.'+m+'.u_m '
 tb+=f'if(n.{inst}.rd_out !== g.{inst}.rd_out)$fatal(1,"read mismatch cycle%0d {m}",i);\n'
 tb+=f'if(n.{inst}.w_ce_in !== g.{inst}.w_ce_in)$fatal(1,"enable mismatch cycle%0d {m}",i);\n'
 tb+=f'if(n.{inst}.w_ce_in && (n.{inst}.wd_in !== g.{inst}.wd_in || n.{inst}.w_addr_in !== g.{inst}.w_addr_in))$fatal(1,"write cohort mismatch cycle%0d {m}",i);\n'
tb+='checks=checks+9;end $display("PASS bank128 write-face cut checks=%0d cycles=3000",checks);$finish;end endmodule\n'
(o/'tb.sv').write_text(tb)
(o/'run.sh').write_text('''#!/bin/bash
set -eu
cd "$(dirname "$0")"
for variant in good mut_data mut_enable mut_addr; do
  iverilog -g2012 -s tb -o "$variant.vvp" "$variant.sv" mem.sv tb.sv >"$variant.compile.log" 2>&1
  if vvp "$variant.vvp" >"$variant.log" 2>&1; then
    cat "$variant.log"
    test "$variant" = good || { echo "MUTANT ESCAPED: $variant"; exit 1; }
  else
    cat "$variant.log"
    test "$variant" != good || exit 1
    echo "MUTANT CAUGHT: $variant"
  fi
done
''')
print('proof emitted',o)
