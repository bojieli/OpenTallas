`timescale 1ns/1ps
`default_nettype none
module ot_hgi_qdq_fr_pin_capture #(parameter integer PIN_CAPTURE=0,FACE_FF=0,MUT_ORDER=0,MUT_END=0)(
 input wire clk,rst_n,input wire[682:0]rec,
 output wire s1_v,s3_v,output wire[189:0]s3,output wire nfault
);
 generate if(PIN_CAPTURE==0)begin:g_closed
  ot_hgi_qdq_fr u_general(.*);
 end else begin:g_mix
  wire gs1,gv,gfault,fs1,one_s1,ffault,overflow;
  wire[189:0]gp,fp;
  ot_hgi_qdq_fr u_general(.clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(gs1),.s3_v(gv),.s3(gp),.nfault(gfault));
  if(FACE_FF==0)begin:g_shared_face
`ifdef OT_HARD_CHILDREN
  ot_hgi_qdq_fr_one_payload u_one(
`else
  ot_hgi_qdq_fr_one_payload #(.MUT_END(MUT_END))u_one(
`endif
   .clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(fs1),.one_s1(one_s1),.payload(fp),.nfault(ffault));
  end else begin:g_dedicated_face
`ifdef OT_HARD_CHILDREN
  ot_hgi_qdq_fr_one_payload_face u_one(
`else
  ot_hgi_qdq_fr_one_payload_face #(.MUT_END(MUT_END))u_one(
`endif
   .clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(fs1),.one_s1(one_s1),.payload(fp),.nfault(ffault));
  end
`ifdef OT_HARD_CHILDREN
  ot_hgi_qdq_fr_capture_retire u_retire(
`else
  ot_hgi_qdq_fr_capture_retire #(.MUT_ORDER(MUT_ORDER))u_retire(
`endif
   .clk(clk),.rst_n(rst_n),.accept(fs1),.accept_one(one_s1),.fast_payload(fp),
   .general_v(gv),.general_payload(gp),.s3_v(s3_v),.s3(s3),.overflow(overflow));
  assign s1_v=fs1;assign nfault=gfault|ffault|overflow;
 end endgenerate
endmodule
`default_nettype wire
