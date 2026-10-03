`timescale 1ns/1ps
// Actual non-power-of-two topology, physically non-sibling neighbors, mixed
// row/position tags and cancellation. Scalar golden uses the existing RNE
// authority in its original binary csum order.
module tb_dsrom_credit_ragged;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg [9:0]lv=0,le=0;reg[319:0]lt=0,ld=0;wire[9:0]ready;
 wire[1:0]rv,re;wire[31:0]row,bf;wire[5:0]pos;wire[63:0]fp;wire fault,quiet;
 ot_v41_return_credit_generated dut(.clk(clk),.rst_n(rst_n),.lv(lv),.le(le),.lt(lt),.ld(ld),.lready(ready),
 .rv(rv),.re(re),.rrow(row),.rbf16(bf),.rpos(pos),.rfp32(fp),.fault(fault),.quiet(quiet));
 integer sent[0:9];integer k,seg,nseg,r,iter,c=0,got=0;reg[63:0]seen=0;
 function integer segment(input integer leaf);
 case(leaf)0:segment=0;1:segment=2;2:segment=-1;3:segment=1;
 4:segment=4;5:segment=0;6:segment=3;7:segment=1;8:segment=2;default:segment=-1;endcase
 endfunction
 function[31:0]value(input integer iteration,input integer s);
 case(s)0:value=(iteration%2) ? 32'h4b800000 : 32'h3f800001;
 1:value=(iteration%2) ? 32'hcb800000 : 32'hbf800000;
 2:value=32'h3f800000;3:value=32'h3f800000;default:value=32'h33800000;endcase
 endfunction
 function[31:0]gold(input integer iteration,input integer region);
 reg[33:0]a,b,d;begin
 a=ot_fp32_rne_pkg::fp32_add_rne(value(iteration,0),value(iteration,1));
 if(region==0)d=ot_fp32_rne_pkg::fp32_add_rne(a[31:0],value(iteration,2));
 else begin
 b=ot_fp32_rne_pkg::fp32_add_rne(value(iteration,2),value(iteration,3));
 d=ot_fp32_rne_pkg::fp32_add_rne(a[31:0],b[31:0]);
 d=ot_fp32_rne_pkg::fp32_add_rne(d[31:0],value(iteration,4));
 end
 gold=d[31:0];end endfunction
 reg[31:0]expected;reg[32:0]rounded;
 always @(posedge clk)if(rst_n)begin
 c=c+1;
 for(k=0;k<10;k=k+1)if(lv[k]&&ready[k])sent[k]=sent[k]+1;
 if(fault)$fatal(1,"ragged return fault");
 for(r=0;r<2;r=r+1)if(rv[r])begin
  iter=row[16*r+:16];expected=gold(iter,r);rounded={1'b0,expected}+33'h7fff+expected[16];
  if(iter>=32 || seen[32*r+iter] || pos[3*r+:3]!=iter%6 || re[r] || fp[32*r+:32]!=expected || bf[16*r+:16]!=rounded[31:16])
   $fatal(1,"ragged golden mismatch r%0d row%0d fp%h expected%h",r,iter,fp[32*r+:32],expected);
  seen[32*r+iter]=1;got=got+1;
 end
 if(got==64 && quiet)begin $display("RESULT ragged rows=%0d cycles=%0d NP=5 R=2 nodes=8 golden=PASS",got,c);$finish;end
 end
 always @(negedge clk)if(rst_n)begin
 for(k=0;k<10;k=k+1)begin
  seg=segment(k);nseg=k<4 ? 3:5;iter=sent[k];
  lv[k]=seg>=0 && iter<32 && c%(k%3+2)!=0;
  lt[32*k+:32]={3'(iter%6),16'(iter),5'(seg),3'd0,5'(nseg)};
  ld[32*k+:32]=value(iter,seg);
 end
 end
 initial begin for(k=0;k<10;k=k+1)sent[k]=0;#22;rst_n=1;end
 initial begin repeat(8192)@(posedge clk);$fatal(1,"ragged finite workload did not drain");end
endmodule
