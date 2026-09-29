`timescale 1ns/1ps
// Experimental 256KiB G4 memory boundary, not connected to production core.
// Request sampled on edge; synchronous macro output visible after that edge.
// All illegal conflicts are atomic fail: suppress memory requests, latch fault.
module ot_qwen_g4_vm_skew_candidate (
 input wire clk, rst_n,
 input wire [3:0] re, we,
 input wire [4*16-1:0] raddr,
 input wire [4*12-1:0] waddr,
 input wire [4*16-1:0] wmask,
 input wire [4*512-1:0] wdata,
 output reg [3:0] rv,
 output wire [4*32-1:0] rdata,
 output reg fault
);
 function automatic [2:0] bank(input [11:0] word_addr);
  bank=word_addr[2:0]^word_addr[4:2];
 endfunction
 reg [7:0] bre,bwe;
 reg [8:0] bra[0:7],bwa[0:7];
 reg [511:0] bwd[0:7],bwm[0:7];
 wire [511:0] bq[0:7];
 reg [2:0] rb[0:3];
 reg [3:0] rl[0:3];
 reg bad;
 integer i,j,b;
 reg [11:0] word_a;
 reg [15:0] mask_a;
 always @* begin
  bad=0;bre=0;bwe=0;
  for(i=0;i<8;i=i+1) begin bra[i]=0;bwa[i]=0;bwd[i]=0;bwm[i]=0;end
  for(i=0;i<4;i=i+1) begin
   if(re[i]) begin
    word_a=raddr[i*16+4 +:12];b=bank(word_a);
    if(bre[b] && bra[b]!=word_a[11:3]) bad=1;
    bre[b]=1;bra[b]=word_a[11:3];
   end
   if(we[i] && |wmask[i*16 +:16]) begin
    word_a=waddr[i*12 +:12];mask_a=wmask[i*16 +:16];b=bank(word_a);
    if(bwe[b] && bwa[b]!=word_a[11:3]) bad=1;
    bwe[b]=1;bwa[b]=word_a[11:3];
    for(j=0;j<16;j=j+1) if(mask_a[j]) begin
     if(bwm[b][j*32]) bad=1; // overlap rejected, no hidden priority
     bwm[b][j*32 +:32]=32'hffffffff;
     bwd[b][j*32 +:32]=wdata[i*512+j*32 +:32];
    end
   end
  end
 end
 always @(posedge clk) begin
  if(!rst_n) begin fault<=0;rv<=0;end
  else begin
   if(bad) fault<=1;
   rv<=bad||fault?0:re;
   for(integer k=0;k<4;k=k+1) begin
    rb[k]<=bank(raddr[k*16+4 +:12]);rl[k]<=raddr[k*16 +:4];
   end
  end
 end
 genvar g,s;
 generate for(g=0;g<8;g=g+1) begin: banks
  for(s=0;s<4;s=s+1) begin: slices
   ot_sram_1r1w_512x128_m4_r2c2 u_mem(
    .clk(clk),.r_ce_in(rst_n&&!fault&&!bad&&bre[g]),.r_addr_in(bra[g]),.rd_out(bq[g][s*128 +:128]),
    .w_ce_in(rst_n&&!fault&&!bad&&bwe[g]),.w_addr_in(bwa[g]),
    .wd_in(bwd[g][s*128 +:128]),.w_mask_in(bwm[g][s*128 +:128]),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
  end
 end
 for(g=0;g<4;g=g+1)begin: outputs
  assign rdata[g*32 +:32]=bq[rb[g]][rl[g]*32 +:32];
 end endgenerate
endmodule
