`timescale 1ns/1ps
// Canonical finite HC quarter, first real operation = golden HC_POST.
// Full 1280-MAC quarter shape = 64 groups of four outputs (20 muls/group). The source-pinned
// Historical m6a5 timing closes but this arithmetic source has exactness FAILs.
// Corrected source-owner pin + one-group golden required before enabled build.
// HC_PRE/projection/Sinkhorn remain explicit dependencies, not invented stubs.
module ot_hbm_hc_quarter #(parameter integer ENABLE=0,NG=64)(
 input wire clk,rst_n,
 input wire req_v,output wire req_r,input wire [31:0] req_tag,
 input wire [NG*128-1:0] req_rdata,input wire [NG*32-1:0] req_y,
 input wire [511:0] req_comb,input wire [127:0] req_post,
 output wire rsp_v,input wire rsp_r,output wire [31:0] rsp_tag,
 output wire [NG*128-1:0] rsp_data,output wire rsp_error,output wire fault
);
 generate if(!ENABLE)begin:g_off
  assign req_r=0;assign rsp_v=0;assign rsp_tag=0;assign rsp_data=0;assign rsp_error=0;assign fault=0;
 end else begin:g_on
  localparam integer IW=NG*160+672,OW=NG*128+33;
  wire launch,engine_clk,engine_rst_n,engine_error_seen;wire [IW-1:0] payload;wire [OW-1:0] response;
  wire [NG*128-1:0] outputs;
  wire [NG-1:0] valids,errors;
  wire [511:0] comb=payload[NG*160+:512];
  wire [127:0] post=payload[NG*160+512+:128];
  wire [31:0] tag=payload[NG*160+640+:32];
  ot_hbm_compute_held_exec #(.IW(IW),.OW(OW)) u_hold(
   .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_r(req_r),
   .req_d({req_tag,req_post,req_comb,req_y,req_rdata}),
   .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_d(response),.launch(launch),.engine_clk(engine_clk),.engine_rst_n(engine_rst_n),.engine_error_seen(engine_error_seen),.engine_d(payload),
   .engine_v(&valids),.engine_q({tag,(|errors)|engine_error_seen,outputs}),.engine_fault(|errors),.fault(fault));
  assign {rsp_tag,rsp_error,rsp_data}=response;
  for(genvar g=0;g<NG;g=g+1)begin:g_group
   ot_dsrom_su_hcpost_group #(.WIN(0),.WOUT(0),.ML(6),.AL(5)) u(
    .clk(engine_clk),.rst_n(engine_rst_n),.in_v(launch),.r(payload[128*g+:128]),
    .y(payload[NG*128+32*g+:32]),.c(comb),.p(post),
    .out_v(valids[g]),.o(outputs[128*g+:128]),.fault(errors[g]));
  end
 end endgenerate
endmodule
