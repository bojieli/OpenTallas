`timescale 1ns/1ps
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
module ot_dp_rrelay_nl (input wire clk, input wire d, output reg q);
    (* keep *) reg state;
    always @(posedge clk) state <= d;
    always @(negedge clk) q <= state;
endmodule
module tb;
reg clk=0, raw=0; reg[31:0] rng=32'h73ce19a5;
integer edges=0, checks=0, pulses=0;
always #5 clk=~clk;
wire r0,r1,r2;
ot_dp_rrelay u0 (.clk(clk),.d(raw),.q(r0));
ot_dp_rrelay_nl u1 (.clk(clk),.d(r0),.q(r1));
ot_dp_rrelay u2 (.clk(clk),.d(r1),.q(r2));
    wire cland_raw_copy_0;
    (* keep = "true" *) ot_dp_rrelay_nl u_cland_raw_copy_0 (.clk(clk), .d(r0), .q(cland_raw_copy_0));
    wire cland_raw_copy_1;
    (* keep = "true" *) ot_dp_rrelay u_cland_raw_copy_1 (.clk(clk), .d(cland_raw_copy_0), .q(cland_raw_copy_1));
// Quarter-edge stimulus includes single-half-cycle and multi-cycle pulses.
initial begin
  repeat(8000) begin
    #2.5;
    rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
    if(rng[2:0]==0) begin raw=~raw; pulses=pulses+1; end
  end
  #1; $display("PASS half_edges=%0d checks=%0d pulses=%0d",edges,checks,pulses); $finish;
end
always @(posedge clk or negedge clk) begin
  edges=edges+1;
  #0.01;
  if(edges>20) begin
    if(r1 !== cland_raw_copy_0 || r2 !== cland_raw_copy_1)
      $fatal(1,"PHASE_MISMATCH edge=%0d clk=%0d original=%b%b copy=%b%b",edges,clk,r1,r2,cland_raw_copy_0,cland_raw_copy_1);
    checks=checks+1;
  end
end
endmodule
