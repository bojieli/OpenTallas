from pathlib import Path
import sys
b=Path(sys.argv[1]);s=(b/'ot_s81ph_hq_parts.sv').read_text();old=s[s.index('module ot_sram_showahead_1r1w_h2 #'):];old=old[:old.index('endmodule')+9]
new=(b/'new_macro/ot_s81ph_hq_parts.sv').read_text();new=new[new.index('module ot_sram_showahead_1r1w_h2 #'):];new=new[:new.index('endmodule')+9]
h=(b/'ot_s81ph_hq_slice.sv').read_text();h=h[h.index('module ot_s81ph_hlk #'):];h=h[:h.index('endmodule')+9]
h=h.replace('always_latch if (!clk) l <= d;', '''`ifdef FQ_STALE_MUT
        always @(posedge clk) l <= d; // causal mutant: extra cycle on the forwarding hop
`else
        always_latch if (!clk) l <= d;
`endif''')
old=old.replace("    wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata}, raw;","    wire [NB*128-1:0] padded, raw;\n    assign padded={{(NB*128-W){1'b0}},wdata};") # portable split of net declaration only
probe='''`timescale 1ns/1ps
'''+old.replace('module ot_sram_showahead_1r1w_h2 #','module fq_ref #')+'\n'+new.replace('module ot_sram_showahead_1r1w_h2 #','module fq_new #')+'\n'+h+r'''
module ot_sram_1r1w_32x128_m1(input clk,r_ce_in,input[4:0]r_addr_in,output reg[127:0]rd_out,input w_ce_in,input[4:0]w_addr_in,input[127:0]wd_in,w_mask_in);
 reg[127:0]mem[0:31];integer k;initial begin rd_out=0;for(k=0;k<32;k=k+1)mem[k]=0;end
 always @(posedge clk)begin
  if(r_ce_in)rd_out<=mem[r_addr_in];
  if(w_ce_in)for(integer j=0;j<128;j=j+1)if(w_mask_in[j])mem[w_addr_in][j]<=wd_in[j];
 end
endmodule
module tb;
 parameter PREV=0;
 localparam W=137, AW=3;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg[1:0]we=0;reg[2*AW-1:0]wa=0,ra=0;reg[W-1:0]wd=0;
 wire[W-1:0]a,b;
 fq_ref #(.W(W),.AW(AW)) r(clk,rst_n,we,wa,wd,ra,a);
 fq_new #(.W(W),.AW(AW),.HLAT(1),.HLAT_PREV(PREV)) n(clk,rst_n,we,wa,wd,ra,b);
 integer i,j,k,errors=0,checks=0,cur=0,prev=0,raw=0,resets=0,memory_checks=0,write_edges=0;reg[AW-1:0]addr=0,paddr=0;reg[31:0]seed=32'h9812bac1;
 function automatic[31:0]rng(input[31:0]x);reg[31:0]t;begin t=x^(x<<13);t=t^(t>>17);rng=t^(t<<5);end endfunction
 always @(posedge clk)begin
  // This is the actual downstream FF sampling edge, BEFORE source NBA updates.
  if(rst_n && i>5)begin
   checks=checks+1;
   if(a!==b)begin if(errors<4)$display("EDGE_MISMATCH cycle=%0d prevmode=%0d ref=%h new=%h",i,PREV,a,b);errors=errors+1;end
   if(r.g_slice[0].cur_q)cur=cur+1;else if(r.g_slice[0].prev_q)prev=prev+1;else raw=raw+1;
  end
  if(r.wv[0])write_edges=write_edges+1;
  #1;
  if(i>5)for(k=0;k<32;k=k+1)begin
   memory_checks=memory_checks+2;
   if(r.g_bank[0].u_m.mem[k]!==n.g_bank[0].u_m.mem[k])errors=errors+1;
   if(r.g_bank[1].u_m.mem[k]!==n.g_bank[1].u_m.mem[k])errors=errors+1;
  end
  if(i>5 && (r.wdata!==n.wdata || r.prevdata!==n.prevdata))begin errors=errors+1;end
 end
 initial begin
  for(i=0;i<4096;i=i+1)begin
   @(negedge clk);#1;
   rst_n=(i>=3 && i%251!=0);if(!rst_n)resets=resets+1;
   seed=rng(seed);addr=seed[AW-1:0];we={2{seed[4] || seed[5]}};wa={addr,addr};
   case(i%5)
    0:ra={addr,addr};
    1:ra={paddr,paddr};
    default:begin seed=rng(seed);ra={2{seed[AW-1:0]}};end
   endcase
   for(j=0;j<W;j=j+1)begin seed=rng(seed);wd[j]=seed[0];end
   paddr=addr;
   @(posedge clk);#2;
  end
  if(cur==0 || prev==0 || raw==0 || resets<2)$fatal(1,"coverage absent");
`ifdef FQ_STALE_MUT
  if(errors==0)$fatal(1,"stale mutant survived");
  $display("FIFO_HLAT_MUTANT_KILLED prevmode=%0d errors=%0d checks=%0d cur=%0d prev=%0d raw=%0d resets=%0d memory_checks=%0d write_edges=%0d",PREV,errors,checks,cur,prev,raw,resets,memory_checks,write_edges);
`else
  if(errors!=0)$fatal(1,"exact mismatch errors=%0d",errors);
  $display("FIFO_HLAT_EXACT_PASS prevmode=%0d checks=%0d cur=%0d prev=%0d raw=%0d resets=%0d width=%0d memory_checks=%0d write_edges=%0d",PREV,checks,cur,prev,raw,resets,W,memory_checks,write_edges);
`endif
  $finish;
 end
endmodule
'''
(b/'fifo_hlat_probe.sv').write_text(probe)
