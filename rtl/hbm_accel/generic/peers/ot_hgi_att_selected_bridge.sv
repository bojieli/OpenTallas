`timescale 1ns/1ps
`default_nettype none
// Direct handshaken VM client: no assumption that a valid-only shim admits.
// C's logical packed-byte sectors are stored below4MiB by its real producer.
module ot_hgi_att_selected_bridge #(parameter integer OUT=8)(
 input wire clk,rst_n,enable,allow_window,
 input wire rq_v, output wire rq_rdy,
 input wire [34:0] rq_addr, input wire [7:0] rq_tag,
 output wire [337:0] vmq, input wire vmq_rdy,
 input wire [273:0] vmr,
 output wire hr_v, output wire [7:0] hr_tag,
 output wire [255:0] hr_data, output reg fault
);
 reg [255:0] pending; reg [4:0] count; reg [7:0] epoch; reg [7:0] issued_epoch [0:255];
 wire [7:0] launch_epoch = count==0 ? epoch+8'd1 : epoch;
 wire bounded = allow_window ? (rq_addr>=35'd131072 && rq_addr<35'd139264) : rq_addr<35'd131072;
 wire free_tag = !pending[rq_tag];
 assign vmq = {enable && rq_v && bounded && free_tag && count < OUT && !fault,
               1'b0,rq_addr[26:0],5'd0,256'd0,32'd0,launch_epoch,rq_tag};
 assign rq_rdy = enable && bounded && free_tag && count < OUT && vmq_rdy && !fault;
 wire push = vmq[337] && vmq_rdy;
 wire rv = vmr[273]; wire [7:0] tag = vmr[264:257];
 wire known = pending[tag] && vmr[272:265] == issued_epoch[tag];
 assign hr_v = rv && known && !vmr[256] && !fault;
 assign hr_tag = tag; assign hr_data = vmr[255:0];
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin pending<=0;count<=0;fault<=0;epoch<=8'hA4;end
  else begin
   if(enable && rq_v && !bounded) fault<=1;
   if(rv && (!known || vmr[256] || count==0)) fault<=1;
   if(push) begin pending[rq_tag]<=1;issued_epoch[rq_tag]<=launch_epoch;epoch<=launch_epoch;end
   if(rv && known) pending[tag]<=0;
   count <= count + (push?5'd1:5'd0) - (rv && known?5'd1:5'd0);
  end
endmodule
`default_nettype wire
