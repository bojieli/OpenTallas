`timescale 1ns/1ps
`default_nettype none
// Opt-in two-native-tile prototype; explicit actual clock roots, no timing exceptions.
module ot_hbm_xcal_partition_t #(parameter integer MUT = 0, parameter integer PAW = 11, parameter integer PREL = 1,
    parameter integer DD = 256, parameter integer DAW = (DD > 128) ? 8 : 7) (
    input  wire          clk_desc,
    input  wire          clk_prog,
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
    wire cw,sv,pdone,pfault,pactive;wire [PAW-1:0] ca,sb;
    wire [255:0] cd;wire [PAW:0] sl;wire [15:0] sn;wire [4:0] sx;
    ot_hbm_xcal_desc_host_native #(.MUT(MUT),.PAW(PAW),.PREL(PREL),.DD(DD),.DAW(DAW)) u_host(
      .clk_desc(clk_desc),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.done(done),.configured(configured),.fault(fault),.active(active),.pdone(pdone),.pfault(pfault),.cw(cw),.ca(ca),.cd(cd),.sv(sv),.sb(sb),.sl(sl),.sn(sn),.sx(sx));
    ot_hbm_xcal_prog_native #(.MUT(MUT),.PAW(PAW),.PREL(PREL)) u_prog(
      .clk(clk_prog),.rst_n(rst_n),.cfg_we(cw),.cfg_addr(ca),.cfg_data(cd),
      .start_v(sv),.start_base(sb),.start_limit(sl),.start_loops(sn),.start_ctx(sx),
      .cmd_ext(cmd_ext),.kv_desc(kv_desc),.active(pactive),.done(pdone),.fault(pfault));
endmodule
`default_nettype wire
