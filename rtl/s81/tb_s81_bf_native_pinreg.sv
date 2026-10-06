`timescale 1ns/1ps
// PINREG=1 (pin-captured inputs, flopped busy/fault) == PINREG=0 one cycle later on pv..ppos and two cycles later on
// busy/fault, cycle for cycle, under random cfg / go / stream traffic (both copies from one stimulus).
// MUT=1: compare without the offset (must FAIL). MUT=2: the DUT's xb_d bit 0 bypasses its pin flop (must FAIL).
module tb_s81_bf_native_pinreg;
 parameter integer MUT=0, CYCLES=20000;
 reg clk=0,rst_n=0; always #0.5 clk=~clk;
 reg cfg_v,go,go_bf,xs_v,xb_v; reg [4:0] cfg_a; reg [47:0] cfg_d; reg [7:0] xs_p; reg [2:0] xs_b,xs_pos,xb_pos,xb_b;
 reg [1:0] xs_sv; reg [255:0] xs_q0,xs_q1; reg [9:0] xs_e0,xs_e1; reg [3:0] xb_sv; reg [31:0] xb_u; reg [1023:0] xb_d,xb_d1;
 localparam integer NB=2, OW=NB*(1+32+16+5+5+1+3);
 wire [OW-1:0] o0,o1; wire b0,b1,f0,f1;
 ot_s81_bf_native #(.PINREG(0)) ref0(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_a(cfg_a),.cfg_d(cfg_d),.go(go),.go_bf(go_bf),
  .xs_v(xs_v),.xs_p(xs_p),.xs_b(xs_b),.xs_sv(xs_sv),.xs_q0(xs_q0),.xs_e0(xs_e0),.xs_q1(xs_q1),.xs_e1(xs_e1),.xs_pos(xs_pos),
  .xb_pos(xb_pos),.xb_v(xb_v),.xb_b(xb_b),.xb_sv(xb_sv),.xb_u(xb_u),.xb_d(xb_d),
  .pv(o0[0+:NB]),.pval(o0[NB+:32*NB]),.prow(o0[33*NB+:16*NB]),.pseg(o0[49*NB+:5*NB]),.pnseg(o0[54*NB+:5*NB]),
  .perr(o0[59*NB+:NB]),.ppos(o0[60*NB+:3*NB]),.busy(b0),.fault(f0));
 // MUT=2: bit 0 of xb_d reaches the DUT one cycle late (one bit mis-staged)
 always @(posedge clk) xb_d1<=xb_d;
 wire [1023:0] xb_d_mut = (MUT==2) ? {xb_d[1023:1], xb_d1[0]} : xb_d;
 ot_s81_bf_native #(.PINREG(1)) dut(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_a(cfg_a),.cfg_d(cfg_d),.go(go),.go_bf(go_bf),
  .xs_v(xs_v),.xs_p(xs_p),.xs_b(xs_b),.xs_sv(xs_sv),.xs_q0(xs_q0),.xs_e0(xs_e0),.xs_q1(xs_q1),.xs_e1(xs_e1),.xs_pos(xs_pos),
  .xb_pos(xb_pos),.xb_v(xb_v),.xb_b(xb_b),.xb_sv(xb_sv),.xb_u(xb_u),.xb_d(xb_d_mut),
  .pv(o1[0+:NB]),.pval(o1[NB+:32*NB]),.prow(o1[33*NB+:16*NB]),.pseg(o1[49*NB+:5*NB]),.pnseg(o1[54*NB+:5*NB]),
  .perr(o1[59*NB+:NB]),.ppos(o1[60*NB+:3*NB]),.busy(b1),.fault(f1));
 reg [OW-1:0] o0d; reg [1:0] b0d,f0d;
 always @(posedge clk) begin o0d<=o0; b0d<={b0d[0],b0}; f0d<={f0d[0],f0}; end
 integer i,k,seed=11,pvs=0,busys=0,gos=0,faults=0;
 function [31:0] rnd; input integer d; rnd=$random(seed); endfunction
 initial begin
  {cfg_v,go,go_bf,xs_v,xb_v,cfg_a,cfg_d,xs_p,xs_b,xs_pos,xb_pos,xb_b,xs_sv,xs_q0,xs_q1,xs_e0,xs_e1,xb_sv,xb_u,xb_d}=0;
  repeat(4)@(negedge clk); rst_n=1;
  for(i=0;i<CYCLES;i=i+1) begin
   @(negedge clk);
   if(i>4) begin
    if(MUT==1 ? (o1!==o0 || b1!==b0d[0] || f1!==f0d[0]) : (o1!==o0d || b1!==b0d[1] || f1!==f0d[1]))
     $fatal(1,"pinreg lockstep %0d",i);
   end
   if(|o1[0+:NB]) pvs=pvs+1; if(b1) busys=busys+1; if(f1) faults=faults+1;
   // phases: configure a few classes, then go and stream beats for a while
   cfg_v=((rnd(0)&7)==0); cfg_a=rnd(0); cfg_d={rnd(0),rnd(0)};
   go=((rnd(0)&255)==0); if(go) gos=gos+1; go_bf=rnd(0);
   xs_v=rnd(0); xs_p=rnd(0); xs_b=rnd(0); xs_sv=rnd(0); xs_pos=rnd(0)%6; xs_e0=rnd(0); xs_e1=rnd(0);
   for(k=0;k<8;k=k+1) begin xs_q0[32*k+:32]=rnd(0); xs_q1[32*k+:32]=rnd(0); end
   xb_v=rnd(0); xb_b=rnd(0); xb_sv=rnd(0); xb_u=rnd(0); xb_pos=rnd(0)%6;
   for(k=0;k<32;k=k+1) xb_d[32*k+:32]=rnd(0);
  end
  if(gos<20||busys<100) $fatal(1,"coverage gos=%0d busy=%0d pv=%0d",gos,busys,pvs);
  $display("PASS bf pinreg lockstep cycles=%0d go=%0d busy=%0d pv=%0d fault=%0d",CYCLES,gos,busys,pvs,faults); $finish;
 end
endmodule
