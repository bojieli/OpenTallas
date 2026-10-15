`timescale 1ns/1ps
// Fixed scheduled duplex physical hop for NBANK complete bank routes.
// Independent actual clock pins permit native phi-R request/response delivery.
// No availability state, arbitration, handshake, queues or schedule extension.
// Commit metadata is transported unchanged after the real macro edge; relay
// output timing is observation timing, not the underlying write visibility.
module dsfd_vm_static_relay128 #(parameter integer NBANK=8)(
 input wire ck_req,ck_rsp,rst_n,
 input wire [NBANK-1:0] i_rv,i_wv,input wire [9*NBANK-1:0] i_ra,i_wa,
 input wire [8*NBANK-1:0] i_rt,i_wt,input wire [4*NBANK-1:0] i_wm,
 input wire [128*NBANK-1:0] i_wd,
 output reg [NBANK-1:0] o_rv,o_wv,output reg [9*NBANK-1:0] o_ra,o_wa,
 output reg [8*NBANK-1:0] o_rt,o_wt,output reg [4*NBANK-1:0] o_wm,
 output reg [128*NBANK-1:0] o_wd,
 input wire [NBANK-1:0] i_sv,i_cv,input wire [128*NBANK-1:0] i_sd,
 input wire [8*NBANK-1:0] i_st,i_ct,input wire [9*NBANK-1:0] i_ca,
 input wire [4*NBANK-1:0] i_cm,
 output reg [NBANK-1:0] o_sv,o_cv,output reg [128*NBANK-1:0] o_sd,
 output reg [8*NBANK-1:0] o_st,o_ct,output reg [9*NBANK-1:0] o_ca,
 output reg [4*NBANK-1:0] o_cm
);
 reg [1:0] rr,sr;
 always @(posedge ck_req or negedge rst_n)if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 always @(posedge ck_rsp or negedge rst_n)if(!rst_n)sr<=0;else sr<={sr[0],1'b1};
 always @(posedge ck_req or negedge rr[1])
  if(!rr[1])begin o_rv<=0;o_wv<=0;end else begin o_rv<=i_rv;o_wv<=i_wv;end
 always @(posedge ck_req)begin o_ra<=i_ra;o_rt<=i_rt;o_wa<=i_wa;o_wt<=i_wt;o_wm<=i_wm;o_wd<=i_wd;end
 always @(posedge ck_rsp or negedge sr[1])
  if(!sr[1])begin o_sv<=0;o_cv<=0;end else begin o_sv<=i_sv;o_cv<=i_cv;end
 always @(posedge ck_rsp)begin o_sd<=i_sd;o_st<=i_st;o_ca<=i_ca;o_cm<=i_cm;o_ct<=i_ct;end
endmodule
