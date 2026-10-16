`timescale 1ns/1ps
`default_nettype none
// SFU as one core + four bank-pair LG leaves (H-SU 2026-10-15, die v15 sfu_<q>0..3 + SFU core slot).
// The core (programme, IO calendar, 80 operand SRAMs, 16 lanes) is the unchanged scheduled engine with
// LG_PATH = 1 + R: every VM read/write of pair g crosses R static die relays and the pair's leaf register,
// so the bridge's fixed READ_RETURN/WRITE_RETURN grow by 2(1+R) and the compiler's IO calendar shifts
// arithmetic start and drain by the same constant (make_qswiglu_io_calendar.py SFU_LG_PATH). This module
// is the die-level composition (leaf tiles + relays are die instances); it adds no logic of its own.
module ot_hgi_sfu_split_engine #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW, LWB=15, R=0
)(
 input wire clk,rst_n,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output wire programme_active,programme_done,
 output wire [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output wire io_active,io_done,
 output wire [31:0] io_ordinal,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [15:0] vi_re,
 output wire [383:0] vi_addr,
 input wire [511:0] vi_q,side_y,
 output wire [15:0] ro_v,side_v,kv_we,
 output wire [511:0] ro_x,side_x,kv_wdata,
 output wire [383:0] kv_waddr,
 output wire fault
);
 wire [135:0] c_rq;
 wire [2055:0] c_rr;
 wire [2247:0] c_wq;
 wire [7:0] c_done;
 ot_hgi_sfu_scheduled_engine #(.PAGE_AW(PAGE_AW),.LWB(LWB),.LG_PATH(1+R)) u_core(
  .clk(clk),.rst_n(rst_n),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),.clk_lane(clk_lane),.clk_map(clk_map),
  .rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),
  .cfg_data(cfg_data),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .programme_active(programme_active),.programme_done(programme_done),.programme_ordinal(programme_ordinal),
  .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
  .io_start_v(io_start_v),.io_start_base(io_start_base),.io_start_limit(io_start_limit),.io_start_loops(io_start_loops),
  .io_active(io_active),.io_done(io_done),.io_ordinal(io_ordinal),
  .local_rq(c_rq),.local_rr(c_rr),.local_wq(c_wq),.local_w_done(c_done),
  .vi_re(vi_re),.vi_addr(vi_addr),.vi_q(vi_q),.side_y(side_y),.ro_v(ro_v),.side_v(side_v),.kv_we(kv_we),
  .ro_x(ro_x),.side_x(side_x),.kv_wdata(kv_wdata),.kv_waddr(kv_waddr),.fault(fault));
 for(genvar g=0;g<4;g=g+1)begin:g_pair
  wire [33:0] m_rq;
  wire [561:0] m_wq;
  wire [513:0] m_rr;
  wire [1:0] m_done;
  ot_hgi_sfu_lg_relay #(.R(R)) u_relay(.clk(clk_lg[g]),.rst_n(rst_lg_n[g]),
   .c_rq(c_rq[34*g+:34]),.c_wq(c_wq[562*g+:562]),.c_rr(c_rr[514*g+:514]),.c_w_done(c_done[2*g+:2]),
   .l_rq(m_rq),.l_wq(m_wq),.l_rr(m_rr),.l_w_done(m_done));
  ot_hgi_sfu_lg_pair_leaf u_leaf(.clk(clk_lg[g]),.rst_n(rst_lg_n[g]),
   .c_rq(m_rq),.c_wq(m_wq),.c_rr(m_rr),.c_w_done(m_done),
   .lg_rq(local_rq[34*g+:34]),.lg_wq(local_wq[562*g+:562]),.lg_rr(local_rr[514*g+:514]),.lg_w_done(local_w_done[2*g+:2]));
 end
endmodule
`default_nettype wire
