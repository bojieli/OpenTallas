`timescale 1ns/1ps
// Q is binary32 in the real central VM, rows856..887. Export only after
// every word committed in this epoch. commit_mask comes from actual SRAM
// write pins, never SU offers or an elapsed-time prediction. Row service
// is admitted ready/valid, its response is tagged by the wrapper arbiter.
// The link consumes pulse-valid with INITIAL_CREDITS credits and returns
// one q_cr per consumed word. No precision conversion occurs here.
module ot_qfd_vm_q_export #(
 parameter integer ENABLE=0, INITIAL_CREDITS=2, MUT_BEAT=0, MUT_FENCE=0
)(
 input wire clk,rst_n,epoch_begin,input wire [511:0] commit_mask,
 input wire start_v,output wire start_ready,output wire qr_committed,
 output wire read_v,output wire [19:0] read_row,input wire read_ready,
 input wire rsp_v,input wire [511:0] rsp_data,
 output reg [523:0] q,input wire q_cr,
 output reg emitted_done,output reg fault
);
 reg [511:0] committed;
 reg active,pending,have;
 reg [4:0] beat;
 reg [511:0] buffer_data;
 reg [2:0] credits;
 wire take_read=read_v&&read_ready;
 wire send=active&&have&&(credits!=0)&&!fault;
 assign qr_committed=&committed;
 assign start_ready=ENABLE!=0&&!active&&!pending&&!have&&!fault&&
                    ((MUT_FENCE!=0)||qr_committed)&&!epoch_begin;
 assign read_v=ENABLE!=0&&active&&!pending&&!have&&!fault;
 assign read_row=20'd856+{15'd0,beat};
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   committed<=0;active<=0;pending<=0;have<=0;beat<=0;
   credits<=INITIAL_CREDITS;q<=0;emitted_done<=0;fault<=0;
  end else if(ENABLE!=0)begin
   q[523]<=0;emitted_done<=0;
   if(epoch_begin)begin
    committed<=commit_mask;
    if(active||pending||have)fault<=1;
   end else committed<=committed|commit_mask;
   if(start_v&&start_ready)begin active<=1;beat<=0;end
   if(take_read)pending<=1;
   if(rsp_v)begin
    if(!active||!pending||have||fault)fault<=1;
    else begin pending<=0;have<=1;buffer_data<=rsp_data;end
   end
   if(q_cr&&!send&&credits==INITIAL_CREDITS)fault<=1;
   credits<=credits+q_cr-send;
   if(send)begin
    q<={1'b1,3'b001,2'b00,1'b0,(beat^(MUT_BEAT!=0?5'd1:5'd0)),buffer_data};
    have<=0;
    if(beat==31)begin active<=0;emitted_done<=1;end
    else beat<=beat+1'b1;
   end
   if(fault)begin active<=0;q[523]<=0;end
  end
 end
endmodule
