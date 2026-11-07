`timescale 1ns/1ps
module ot_sram_1r1w_32x64_m1(input wire clk,r_ce_in,w_ce_in,input wire[4:0] r_addr_in,w_addr_in,output reg[63:0] rd_out,input wire[63:0] wd_in,w_mask_in);
 reg [63:0] m[0:31]; integer i;
 always @(posedge clk) begin if(r_ce_in) rd_out<=m[r_addr_in]; if(w_ce_in) m[w_addr_in]<=(m[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in); end
endmodule
module tb; parameter integer D=4, W=512, MUT=0, RCYC=3;
 reg ck=0,rst_n=0; reg [W-1:0] d=0; wire [W-1:0] a,b; integer c=0,bad=0,seen=0,i,cmp=0,k;
 qfd_dv_s8s_sram_delay #(.W(W),.D(D)) u_a(.ck(ck),.rst_n(rst_n),.d(d),.q(a));
 qfd_dv_s8s_sram_delay_oq #(.W(W),.D(D),.MUT(MUT)) u_b(.ck(ck),.rst_n(rst_n),.d(d),.q(b));
 always #1 ck=~ck;
 always @(negedge ck) begin
   if(c>=1) begin cmp=cmp+1; if(a!==b) begin bad=bad+1; if(bad<4) $display("DIFF c=%0d rst=%b a=%h b=%h",c,rst_n,a[31:0],b[31:0]); end end
   if(a!=0 && a!==512'bx) seen=seen+1;
   c=c+1;
   for(i=0;i<W;i=i+32) d[i+:32]=$random;
   if(c%97==0) d={W{1'b0}};
   if(c==RCYC) rst_n=1;
   if(c==3000) begin rst_n=0; end
   if(c==3000+RCYC) rst_n=1;
   if(c==6000) begin $display("RESULT D=%0d MUT=%0d cmp=%0d bad=%0d nonzero=%0d",D,MUT,cmp,bad,seen); $finish; end
 end
endmodule
