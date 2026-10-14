`timescale 1ns/1ps
`default_nettype none
// A real bank pin station receives the compact mover stream. Ready leaves four
// slots reserved for the registered permission, mover launch and pin-capture
// round trip. Native request credits and commit notifications remain distinct.
module ot_hgi_dma_native_write_bank #(
 parameter integer SID=0,BANK=0,NATIVE_CREDITS=10,MUT=0
)(
 input wire clk,rst_n,input wire [279:0] compact,
 output reg producer_ready,output reg [280:0] wq,
 input wire wq_cr,wq_done,output reg commit_done,output reg fault
);
 reg [278:0] pin_data;reg pin_v;reg cr_q,done_q;
 reg [278:0] fifo[0:7];reg [2:0] head,tail;reg [3:0] count;
 reg [4:0] credits;reg [5:0] owed;
 wire push=pin_v && pin_data[278:277]==2'(SID) && pin_data[266:264]==3'(BANK);
 wire issue=count!=0 && credits!=0 && !fault;
 wire [3:0] count_next=count+4'(push)-4'(issue);
 always @(posedge clk)pin_data<=compact[278:0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin pin_v<=0;cr_q<=0;done_q<=0;producer_ready<=1;wq[280]<=0;commit_done<=0;fault<=0;head<=0;tail<=0;count<=0;credits<=5'(NATIVE_CREDITS);owed<=0;end
  else begin
   pin_v<=compact[279];cr_q<=wq_cr;done_q<=wq_done;
   producer_ready<=count_next<4 && !fault;
   commit_done<=done_q;wq[280]<=issue;
   if(push && count==8 && !issue)fault<=1;
   else begin count<=count_next;if(push)begin fifo[tail]<=pin_data;tail<=tail+1'b1;end end
   if(issue)begin
    wq[279:0]<={1'b0,fifo[head]};
    if(MUT==1)wq[8]<=!fifo[head][8];
    head<=head+1'b1;
   end
   credits<=credits+5'(cr_q)-5'(issue);
   owed<=owed+6'(issue)-6'(done_q);
   if((cr_q && credits==NATIVE_CREDITS && !issue)||(done_q && owed==0 && !issue))fault<=1;
  end
 end
endmodule

module ot_hgi_dma_native_write_fabric #(parameter integer HARD_CLOCKS=0,MUT=0)(
 input wire clk,rst_n,input wire [31:0] leaf_clk,input wire [279:0] compact,
 output wire [31:0] producer_ready,output wire [8991:0] native_wq,
 input wire [31:0] native_cr,native_done,output wire [31:0] commit_done,fault
);
 wire [31:0] clocks=HARD_CLOCKS!=0?leaf_clk:{32{clk}};
 for(genvar s=0;s<4;s=s+1)begin:slice
  for(genvar b=0;b<8;b=b+1)begin:bank
   ot_hgi_dma_native_write_bank #(.SID(s),.BANK(b),.MUT(MUT)) u_bank(
    .clk(clocks[s*8+b]),.rst_n(rst_n),.compact(compact),.producer_ready(producer_ready[s*8+b]),
    .wq(native_wq[(s*8+b)*281 +:281]),.wq_cr(native_cr[s*8+b]),.wq_done(native_done[s*8+b]),
    .commit_done(commit_done[s*8+b]),.fault(fault[s*8+b]));
  end
 end
endmodule
`default_nettype wire
`default_nettype none
module ot_hgi_dma_native_write_commit(
 input wire clk,rst_n,input wire [31:0] committed,
 output reg done,output reg fault
);
 reg [31:0] pin_committed;reg [11:0] pending;
 reg [5:0] arrived;
 always @*begin arrived=0;for(integer b=0;b<32;b=b+1)arrived=arrived+6'(pin_committed[b]);end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin pin_committed<=0;pending<=0;done<=0;fault<=0;end
  else begin
   pin_committed<=committed;done<=pending!=0;
   pending<=pending+12'(arrived)-12'(pending!=0);
   if(pending>12'd2048)fault<=1;
  end
 end
endmodule
`default_nettype wire
