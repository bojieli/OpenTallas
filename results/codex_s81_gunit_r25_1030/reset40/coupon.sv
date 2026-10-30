module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
module ot_dp_st #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    input  wire         ea,
    output reg  [W-1:0] q,
    output reg          eq
);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
`timescale 1ps/1ps
module tb;
reg clk=0; always #416.5 clk=~clk;
reg rst_root_n=0; reg[264:0] d=0;reg ea=0;
wire[264:0] qo,qn,qm,qp;wire eo,en,em,ep;
integer n=0,checks=0,depthbad=0,payloadbad=0;
wire rst_n_t19;
wire rst_rl_95;
wire rst_rl_94;
wire rst_rl_93;
wire rst_rl_92;
wire rst_rl_86;
wire rst_rl_85;
wire rst_n_t40;
wire rst_rl_20;
wire rst_rl_19;
wire rst_rl_18;
wire rst_rl_17;
wire rst_rl_16;
wire rst_rl_15;
ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_95), .q(rst_n_t19));
ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_rl_95));
ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));
ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));
ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_86), .q(rst_rl_92));
ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));
ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_root_n), .q(rst_rl_85));
ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t40));
ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));
ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));
ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));
ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));
ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));
ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_root_n), .q(rst_rl_15));

ot_dp_st #(.W(265)) old_station(clk,rst_n_t19,d,ea,qo,eo);
ot_dp_st #(.W(265)) new_station(clk,rst_n_t40,d,ea,qn,en);
ot_dp_st #(.W(265)) bad_depth(clk,rst_rl_20,d,ea,qm,em);
ot_dp_st #(.W(265)) bad_payload(clk,rst_n_t40,d^265'd1,ea,qp,ep);
initial begin
 for(n=0;n<2400;n=n+1)begin
  @(negedge clk);
  if(n==64||n==832||n==1600)rst_root_n=1;
  if(n==768||n==1536)rst_root_n=0;
  d={$random,$random,$random,$random,$random,$random,$random,$random,$random};
  if(n%83==2)d[164:133]=32'hx;
  ea=((n%768)<96||(n%768)>740)?1:(n%2);
  @(posedge clk);#1;
  if(n>=64)begin
   checks=checks+1;
   if(qo!==qn||eo!==en)$fatal(1,"reset localization changed native fullW265 transport at %0d",n);
   if(qo!==qm||eo!==em)depthbad=depthbad+1;
   if(qo!==qp||eo!==ep)payloadbad=payloadbad+1;
  end
 end
 if(depthbad==0||payloadbad==0)$fatal(1,"mutant did not fire");
 $display("PASS833ps checks=%0d resetdepth_mutant=%0d payload_mutant=%0d cold64 warm64/64 addedcycles0",checks,depthbad,payloadbad);$finish;
end
endmodule
