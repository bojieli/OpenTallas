`timescale 1ns/1ps
`default_nettype none
// Pin-local ownership/mux root. All three requests and their owners share one capture edge.
module ot_hgi_b2_dma_vmface #(parameter integer MUT_SEAM=0)(
 input wire clk,rst_n,serial_owner,il_owner,
 input wire [337:0] fast_request,serial_request,il_request,
 output reg [337:0] vmq,input wire [273:0] vmr,
 output reg [273:0] mover_response,il_response
);
 reg [1:0] reset_release;always @(posedge clk or negedge rst_n)
   if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg serial_q,il_q;reg [337:0] fast_q,serial_packet_q,il_packet_q;
 always @(posedge clk or negedge rn)begin
   if(!rn)begin serial_q<=0;il_q<=0;fast_q[337]<=0;serial_packet_q[337]<=0;il_packet_q[337]<=0;vmq[337]<=0;mover_response[273]<=0;il_response[273]<=0;end
   else begin
     serial_q<=serial_owner;il_q<=il_owner;
     fast_q[337]<=fast_request[337];serial_packet_q[337]<=serial_request[337];il_packet_q[337]<=il_request[337];
     vmq[337]<=il_q?il_packet_q[337]:serial_q?serial_packet_q[337]:fast_q[337];
     mover_response[273]<=!il_q&&vmr[273];il_response[273]<=il_q&&vmr[273];
   end
 end
 always @(posedge clk)begin
   fast_q[336:0]<=fast_request[336:0];serial_packet_q[336:0]<=serial_request[336:0];il_packet_q[336:0]<=il_request[336:0];
   vmq[336:0]<=il_q?il_packet_q[336:0]:serial_q?serial_packet_q[336:0]:fast_q[336:0];
   mover_response[272:0]<=il_q?273'd0:vmr[272:0];
   il_response[272:0]<=il_q?(vmr[272:0]^((MUT_SEAM==2)?273'd1:273'd0)):273'd0;
 end
endmodule
`default_nettype wire
