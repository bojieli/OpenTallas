`timescale 1ns/1ps
// RF owner side of the connected parent interface. No result capture buffer:
// Maxwell owns capture/storage and must hold cap_* stable under backpressure.
// Actual original RF ACK is the only visibility evidence. One operation and
// one write outstanding; reset invalidates control epochs, never clears SRAM.
module ot_gpu_rf_visibility_fence #(parameter integer ENABLE=0) (
 input wire clk,rst_n,
 input wire op_valid,output wire op_ready,
 input wire [7:0] op_epoch,input wire [9:0] op_vectors,
 input wire cap_valid,output wire cap_ready,
 input wire [7:0] cap_epoch,input wire [8:0] cap_addr,
 input wire cap_last,input wire [4095:0] cap_data,
 input wire producer_done_valid,input wire [7:0] producer_done_epoch,
 output wire host_wr_valid,input wire host_wr_ready,
 output wire [8:0] host_dst,output wire [4095:0] host_wdata,
 input wire host_ack_valid,output wire host_ack_ready,
 input wire ack_retire_enable,
 output wire vector_ACK_visible,output wire [8:0] vector_ACK_addr,output wire [7:0] vector_ACK_epoch,
 output wire writes_visible,output wire fence_valid,input wire fence_ready,output wire [7:0] fence_epoch,
 output wire pending_write,output wire fault
);
 generate if(ENABLE!=0) begin:g_enabled
  reg [9:0] expected,issued,retired;
  reg [7:0] epoch;
  reg [8:0] ACK_addr;
  reg active,pending,producer_done,fault_q;
  wire op_legal=(op_vectors>=1 && op_vectors<=512);
  wire cap_legal=(cap_epoch==epoch && issued<expected && cap_addr==issued[8:0] && cap_last==(issued+10'd1==expected));
  assign op_ready=rst_n && !active && !pending && !fault_q && op_legal;
  assign host_wr_valid=rst_n && active && !pending && !fault_q && cap_valid && cap_legal;
  assign cap_ready=rst_n && active && !pending && !fault_q && cap_legal && host_wr_ready;
  assign host_dst=cap_addr;assign host_wdata=cap_data;
  assign host_ack_ready=rst_n && pending && ack_retire_enable;
  assign vector_ACK_visible=rst_n && pending && host_ack_valid;
  assign vector_ACK_addr=ACK_addr;assign vector_ACK_epoch=epoch;
  assign writes_visible=rst_n && active && !fault_q &&
   ((retired==expected)||(pending && issued==expected && host_ack_valid));
  assign fence_valid=rst_n && active && !fault_q && !pending && producer_done && retired==expected;
  assign fence_epoch=epoch;assign pending_write=pending;assign fault=fault_q;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
    expected<=0;issued<=0;retired<=0;epoch<=0;ACK_addr<=0;
    active<=0;pending<=0;producer_done<=0;fault_q<=0;
   end else begin
    if(op_valid && !active && !pending && !op_legal) fault_q<=1;
    if(op_valid && op_ready) begin
     expected<=op_vectors;issued<=0;retired<=0;epoch<=op_epoch;active<=1;producer_done<=0;
    end
    if(active && cap_valid && !pending && !cap_legal) fault_q<=1;
    if(host_wr_valid && host_wr_ready) begin pending<=1;issued<=issued+1'b1;ACK_addr<=cap_addr;end
    if(host_ack_valid && host_ack_ready) begin pending<=0;retired<=retired+1'b1;end
    if(active && producer_done_valid) begin
     if(producer_done_epoch==epoch) producer_done<=1;
     else fault_q<=1;
    end
    if(fence_valid && fence_ready) active<=0;
   end
  end
 end else begin:g_disabled
  assign op_ready=0;assign cap_ready=0;assign host_wr_valid=0;assign host_dst=0;assign host_wdata=0;
  assign host_ack_ready=0;assign vector_ACK_visible=0;assign vector_ACK_addr=0;assign vector_ACK_epoch=0;
  assign writes_visible=0;assign fence_valid=0;assign fence_epoch=0;assign pending_write=0;assign fault=0;
 end endgenerate
endmodule
