`timescale 1ns/1ps
// Independent duplicated credit/control+descriptor storage. One external stream.
// At the first observed disagreement no ready/valid side effect is exposed.
(* keep_hierarchy *)
module ot_hbrom_control_channel #(parameter integer W=8,P=2,DEPTH=7)(
 input wire clk,rst_n,s_valid,output wire s_ready,input wire[W-1:0]s_data,
 output wire m_valid,input wire m_ready,output wire[W-1:0]m_data,output wire fault);
 wire ar,br,av,bv;wire[W-1:0]ad,bd;
 (* keep *) reg bad,bad_shadow;
 wire mismatch=(ar!=br)||(av!=bv)||(av&&bv&&(ad!=bd));
 assign fault=bad||bad_shadow||mismatch;
 assign s_ready=ar&&br&&!fault;
 assign m_valid=av&&bv&&!fault;
 assign m_data=ad;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin bad<=0;bad_shadow<=0;end
  else begin bad<=bad|bad_shadow|mismatch;bad_shadow<=bad_shadow|bad|mismatch;end
 // Gate offer with both credits, so both copies accept exactly the same beat.
 wire offer=s_valid&&s_ready;
 wire consume=m_ready&&m_valid;
 (* keep_hierarchy *) ot_hbm_accel_smv_chan #(.W(W),.P(P),.DEPTH(DEPTH)) primary(
  .clk(clk),.rst_n(rst_n),.s_valid(offer),.s_ready(ar),.s_data(s_data),
  .m_valid(av),.m_ready(consume),.m_data(ad));
 (* keep_hierarchy *) ot_hbm_accel_smv_chan #(.W(W),.P(P),.DEPTH(DEPTH)) shadow(
  .clk(clk),.rst_n(rst_n),.s_valid(offer),.s_ready(br),.s_data(s_data),
  .m_valid(bv),.m_ready(consume),.m_data(bd));
endmodule
