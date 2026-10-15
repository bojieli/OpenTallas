`timescale 1ns/1ps
// Accepted-beat credit return isolates the ready pin from the queue state.
// Keep the head reserved until the registered return pulse retires it. The
// output register holds through arbitrary stalls and reloads only after that
// retirement; maximum one transaction each four clocks. No bypass.
module ot_fence_pin_return #(parameter integer W=8, MUT_RETURN=0)(
 input wire clk, rst_n,
 input wire in_valid, output wire in_ready, input wire [W-1:0] in_data,
 output reg out_valid, input wire out_ready, output reg [W-1:0] out_data
);
 wire q_valid; wire [W-1:0] q_data;
 reg returned, loading;
 wire load = !out_valid && !returned && !loading && q_valid;
 ot_sc_pfifo #(.W(W), .S(2), .G(32)) u_queue(
  .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data),
  .out_valid(q_valid), .out_ready(returned), .out_data(q_data));
 always @(posedge clk) begin
  if(!rst_n) begin out_valid<=0; returned<=0; loading<=0; end
  else begin
   loading <= load;
   returned <= MUT_RETURN ? 1'b0 : out_valid && out_ready;
   if(out_valid) begin if(out_ready) out_valid<=0; end
   else if(loading) out_valid<=1;
  end
 end
 for(genvar g=0;g<(W+31)/32;g=g+1) begin : g_lane
  localparam integer LO=g*32, GW=(W-LO<32)?W-LO:32;
  wire load_lane;
  ot_sc_rep_ff #(.RV(0)) u_load(.clk(clk),.rst_n(rst_n),.d(load),.q(load_lane));
  always @(posedge clk) if(load_lane) out_data[LO+:GW]<=q_data[LO+:GW];
 end
endmodule
