`timescale 1ns/1ps
// Additive input-boundary successor. Reservations start at issue and cover the
// hub flight, this optional capture stage, queue residency and output launch.
module ot_ha2_hub_credit_sender_capture #(
 parameter integer W=544, INJ=2, AW=6, CAPTURE=0, HUB_CYCLES=35, MUTANT=0
)(input wire clk,rst_n,
 input wire [INJ-1:0] issue_v,arrival_v,receiver_ready,
 input wire [INJ*W-1:0] arrival_data,
 output wire [INJ-1:0] issue_ready,send_v,
 output wire [INJ*W-1:0] send_data,
 output wire quiet,fault);
 wire [INJ-1:0] qv;
 wire [INJ*W-1:0] qd;
 wire inner_quiet;
 initial if((1<<AW)<HUB_CYCLES+2+(CAPTURE?1:0))
  $fatal(1,"HA2 capture sender credits do not cover flight");
 if(CAPTURE)begin:g_capture
  reg [INJ-1:0] v;
  reg [INJ*W-1:0] d;
  always @(posedge clk or negedge rst_n)if(!rst_n)v<=0;else v<=arrival_v;
  always @(posedge clk)d<=arrival_data;
  assign qv=v;assign qd=d;
 end else begin:g_direct
  assign qv=arrival_v;assign qd=arrival_data;
 end
 ot_ha2_hub_credit_sender #(.W(W),.INJ(INJ),.AW(AW),.MUTANT(MUTANT)) u_sender
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(qv),
   .arrival_data(qd),.receiver_ready(receiver_ready),.issue_ready(issue_ready),
   .send_v(send_v),.send_data(send_data),.quiet(inner_quiet),.fault(fault));
 assign quiet=inner_quiet&&!(|qv);
endmodule
