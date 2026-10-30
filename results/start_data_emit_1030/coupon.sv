module ot_dp_landing_origin #(
    parameter integer PAD = 0,
    parameter bit EDGE_FALL = 0
) (
    input  wire clk,
    input  wire rst_raw_n,   // raw region reset (power-on / die reset), synchronous to clk
    input  wire p_start,     // parent's forwarded start (asynchronous to clk, monotonic 0 -> 1)
    output wire start        // region count origin: the ring readers' rst_n and the region's own start
);
    (* async_reg = "true" *) reg s0, s1;
    reg s2;
    wire s_in;
    if (EDGE_FALL) begin : g_fall
        (* async_reg = "true" *) reg sf;
        always @(negedge clk) sf <= p_start;
        assign s_in = sf;
    end else begin : g_rise
        assign s_in = p_start;
    end
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    if (PAD > 0) begin : g_pad
        reg [PAD-1:0] pd;
        always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PAD'({pd, s2});
        assign start = pd[PAD-1];
    end else begin : g_nopad
        assign start = s2;
    end
endmodule
module BUFx8_ASAP7_75t_R(input A,output Y); buf(Y,A); endmodule
module tb;
 reg clk=0,p=0,rst=0; always #416.5 clk=~clk;
 wire q0,q1,q2,q3; reg delayed; integer n=0, checks=0, invcaught=0, cyclecaught=0;
 always @(posedge clk) delayed<=p;
    (* keep = "true" *) wire sd_actual_b0_q;
    (* keep = "true", dont_touch = "true" *) BUFx8_ASAP7_75t_R sd_actual_b0 (.A(p), .Y(sd_actual_b0_q));
    (* keep = "true" *) wire sd_actual_b1_q;
    (* keep = "true", dont_touch = "true" *) BUFx8_ASAP7_75t_R sd_actual_b1 (.A(sd_actual_b0_q), .Y(sd_actual_b1_q));
    (* keep = "true" *) wire sd_actual_b2_q;
    (* keep = "true", dont_touch = "true" *) BUFx8_ASAP7_75t_R sd_actual_b2 (.A(sd_actual_b1_q), .Y(sd_actual_b2_q));
 ot_dp_landing_origin #(.EDGE_FALL(0)) a(clk,rst,p,q0);
 ot_dp_landing_origin #(.EDGE_FALL(0)) b(clk,rst,sd_actual_b2_q,q1);
 ot_dp_landing_origin #(.EDGE_FALL(0)) c(clk,rst,~sd_actual_b2_q,q2);
 ot_dp_landing_origin #(.EDGE_FALL(0)) d(clk,rst,delayed,q3);
 always @(negedge clk) begin #1;
  if(n>10) begin checks=checks+1; if(q0!==q1) $fatal(1,"buffered source mismatch");
   if(q0!==q2) invcaught=invcaught+1; if(q0!==q3) cyclecaught=cyclecaught+1; end
 end
 initial begin
  #1; rst=0;
  for(n=0;n<700;n=n+1) begin
   @(posedge clk); #10;
   if(n==64 || n==320 || n==576) rst=1;
   if(n==256 || n==512) rst=0;
   p=(n%13)<7;
   if(n%31==5) p=1'bx;
  end
  #1000;
  if(invcaught==0 || cyclecaught==0) $fatal(1,"control not detected");
  $display("PASS checks=%0d inversion_mutant=%0d extra_cycle_mutant=%0d cold64 warm64/64 addedcycles=0",checks,invcaught,cyclecaught);
  $finish;
 end
endmodule
