`timescale 1ns/1ps
`default_nettype none
// Compiler-reserved HCX read/write ports, never runtime-arbitrated.
// RL/WL are the implemented native request->return/commit latencies in THIS
// clock domain. No ready pins, queue, credit or commit-gated completion exists.
// Read quarters arrive consecutively in canonical FP32 sector order. One
// physical packed-BF16 row is fetched for quarter 0, cached for quarters 1..3.
// Compiler reserves the generated EPS halfrow write one cycle after comb tail.
// A missed/extra return or commit faults; response timeline never extends.
module ot_s81_hcx_vm_scheduled #(parameter integer RL=4,WL=4,MUT_DROP_EPS=0,READ_BF16=1)(
 input wire clk,rst_n,job_start,
 input wire [13:0] coef_base_row,
 input wire [31:0] norm_eps,
 input wire [337:0] vmq,
 output reg [273:0] vmr,
 output wire rq_v,
 output wire [13:0] rq_row,
 input wire rs_v,
 input wire [511:0] rs_d,
 output wire wq_v,
 output wire [13:0] wq_row,
 output wire [15:0] wq_mask,
 output wire [511:0] wq_d,
 input wire wq_commit,
 output reg fault
);
 wire rd=vmq[337]&&!vmq[336],wr=vmq[337]&&vmq[336];
 wire [26:0] sector=vmq[335:309];
 wire [1:0] quarter=READ_BF16 ? sector[1:0] : {1'b0,sector[0]};
 reg [1:0] wp;
 reg eps_pending;
 reg [31:0] eps_q;
 reg [13:0] base_q;
 assign rq_v=rd && quarter==0;
 assign rq_row=READ_BF16 ? sector[15:2] : sector[14:1];
 assign wq_v=wr || (eps_pending && !MUT_DROP_EPS);
 assign wq_row=eps_pending ? base_q+14'd1 : wp==0 ? coef_base_row+14'd1 : coef_base_row;
 assign wq_mask=eps_pending || wp==2 ? 16'hff00 : 16'h00ff;
 assign wq_d=eps_pending ? {224'd0,eps_q,256'd0} : wp==2 ? {vmq[303:48],256'd0} : {256'd0,vmq[303:48]};
 reg [RL-1:0] rv,rf;
 reg [15:0] rt[0:RL-1];reg [1:0] rq[0:RL-1];reg [13:0] rr[0:RL-1];
 reg [WL-1:0] wv;
 reg [15:0] wt[0:WL-1];
 reg [WL:0] tv;reg [15:0] tt[0:WL];
 reg [WL-1:0] commit_due;
 reg cache_valid;reg [13:0] cache_row;reg [511:0] cache_data;
 reg [26:0] next_sector;reg seen;
 wire [511:0] read_data=rf[RL-1] ? rs_d : cache_data;
 wire [255:0] expanded;
 generate for(genvar i=0;i<8;i=i+1) begin:g_expand
  assign expanded[i*32 +:32]=READ_BF16 ? {read_data[rq[RL-1]*128+i*16 +:16],16'd0} : read_data[rq[RL-1]*256+i*32 +:32];
 end endgenerate
 initial if(RL<1 || WL<1)$error("native HCX fixed latencies must be >=1");
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   rv<=0;rf<=0;wv<=0;tv<=0;commit_due<=0;wp<=0;eps_pending<=0;vmr<=0;fault<=0;cache_valid<=0;seen<=0;
  end else begin
   vmr[273]<=0;
   if(job_start)begin
    if(|rv || |wv || |tv || eps_pending || |commit_due)fault<=1;
    if(coef_base_row[3:0]!=0)fault<=1; // compact VM operand regions: 16-row aligned
    wp<=0;cache_valid<=0;seen<=0;
   end
   rv[0]<=rd;rf[0]<=rq_v;rt[0]<=vmq[15:0];rq[0]<=quarter;rr[0]<=rq_row;
   for(integer i=1;i<RL;i=i+1)begin rv[i]<=rv[i-1];rf[i]<=rf[i-1];rt[i]<=rt[i-1];rq[i]<=rq[i-1];rr[i]<=rr[i-1];end
   wv[0]<=wr&&wp!=2;wt[0]<=vmq[15:0];
   for(integer i=1;i<WL;i=i+1)begin wv[i]<=wv[i-1];wt[i]<=wt[i-1];end
   // Last packet response is one cycle later: the statically generated EPS
   // write must have reached its fixed visibility edge before HC retires.
   tv[0]<=wr&&wp==2;tt[0]<=vmq[15:0];
   for(integer i=1;i<=WL;i=i+1)begin tv[i]<=tv[i-1];tt[i]<=tt[i-1];end
   commit_due[0]<=wq_v;
   for(integer i=1;i<WL;i=i+1)commit_due[i]<=commit_due[i-1];
   eps_pending<=wr&&wp==2;
   if(wr)begin
    if(eps_pending || vmq[47:16]!=32'hffffffff || sector!=({13'd0,coef_base_row,1'b0}+wp))fault<=1;
    wp<=wp==2 ? 0 : wp+1'b1;
    if(wp==2)begin base_q<=coef_base_row;eps_q<=norm_eps;end
   end
   if(rd)begin
    if((READ_BF16 ? |sector[26:16] : |sector[26:15]) || (!seen && quarter!=0) || (seen && sector!=next_sector))fault<=1;
    next_sector<=sector+1'b1;seen<=1;
   end
   if(rs_v!=rf[RL-1] || wq_commit!=commit_due[WL-1])fault<=1;
   if(rf[RL-1])begin cache_data<=rs_d;cache_row<=rr[RL-1];cache_valid<=1;end
   if(rv[RL-1])begin
    if(!rf[RL-1] && (!cache_valid || cache_row!=rr[RL-1]))fault<=1;
    vmr<={1'b1,rt[RL-1],1'b0,expanded};
   end
   if(wv[WL-1] || tv[WL])begin
    if(rv[RL-1] || (wv[WL-1]&&tv[WL]))fault<=1;
    vmr<={1'b1,tv[WL] ? tt[WL] : wt[WL-1],1'b1,256'd0};
   end
  end
 end
endmodule
`default_nettype wire
