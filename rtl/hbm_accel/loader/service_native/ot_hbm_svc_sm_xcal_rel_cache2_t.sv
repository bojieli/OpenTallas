`timescale 1ns/1ps
`default_nettype none
module ot_hbm_svc_sm_xcal_rel_cache2_t #(parameter integer MUT = 0, parameter integer PAW = 11, parameter integer PREL = 1,
    parameter integer DD = 256, parameter integer DAW = (DD > 128) ? 8 : 7) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tgt,
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    output wire [108:0]  cmd_ext,
    output wire [63:0]   kv_desc,
    output wire          done,
    output wire          configured,
    output wire          fault,
    output wire          active
);
 // Opt-in cache-only alignment: two real captures of the full173bit mirror.
 // No change to descriptor/GO issue or READ admission. MUT6 deletes one edge.
 wire[172:0]command0;wire done0,active0;
 reg[172:0]command1,command2;reg[1:0]done_q,active_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin command1<=0;command2<=0;done_q<=0;active_q<=0;end
  else begin command1<=command0;command2<=command1;done_q<={done_q[0],done0};active_q<={active_q[0],active0};end
 assign {kv_desc,cmd_ext}=MUT==6?command1:command2;
 assign done=done_q[1];assign active=active_q[1];
 ot_hbm_svc_sm_xcal_rel_t #(.MUT(MUT==6?0:MUT),.PAW(PAW),.PREL(PREL),.DD(DD),.DAW(DAW)) u_base(
  .clk(clk),
  .rst_n(rst_n),
  .tgt(tgt),
  .cfg_v(cfg_v),
  .cfg_target(cfg_target),
  .cfg_addr(cfg_addr),
  .cfg_data(cfg_data),
  .desc_v(desc_v),
  .desc_base(desc_base),
  .desc_limit(desc_limit),
  .desc_loops(desc_loops),
  .launch_v(launch_v),
  .cmd_ext(command0[108:0]),
  .kv_desc(command0[172:109]),
  .done(done0),
  .configured(configured),
  .fault(fault),
  .active(active0));
endmodule
`default_nettype wire
