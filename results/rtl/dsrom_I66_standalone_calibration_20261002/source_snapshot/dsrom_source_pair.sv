`timescale 1ns/1ps
// Additive simulation-only read-only source observations. No new protocol.
module dsrom_source_pair #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 5,
    parameter integer BF16 = 0,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer PHW = 6,          // phase id bits: 2^PHW phases per die
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    // spine broadcast (after the broadcast wire stages)
    input  wire         cfg_go,
    input  wire [PHW-1:0] cfg_ph,
    input  wire [2:0]   cfg_np,         // positions - 1
    input  wire         go,
    input  wire         go_bf,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    input  wire [2:0]   xb_pos,
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    // the two macros' partials (return-tree leaves 2g, 2g + 1)
    output wire [1:0]   pv,
    output wire [63:0]  pval,
    output wire [31:0]  prow,
    output wire [9:0]   pseg,
    output wire [9:0]   pnseg,
    output wire [1:0]   perr,
    output wire [5:0]   ppos,
    output wire         busy,
    output wire         fault,
    // quiet: no op in flight, no partial pending, no configuration load (the element's clock is gated): clocking
    // a quiet pair changes nothing until cfg_go or go (simulation host uses it to skip evaluations)
    output wire         quiet
,
    output wire obs_cfg_read,
    output wire [14:0] obs_cfg_addr,
    output wire obs_cfg_write,
    output wire [4:0] obs_cfg_word,
    output wire [47:0] obs_cfg_data,
    output wire obs_go_e,
    output wire obs_act,
    output wire obs_issue,
    output wire [13:0] obs_addr,
    output wire obs_capture,
    output wire obs_cap_bank,
    output wire obs_consume,
    output wire [3:0] obs_XFIFO
);
ot_v41_pair_w17w10 #( .NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .BP(BP), .PHW(PHW), .INSTANCE(INSTANCE) ) dut (.*);
assign obs_cfg_read = dut.ld_run;
assign obs_cfg_addr = dut.ld_a;
assign obs_cfg_write = dut.c_v;
assign obs_cfg_word = dut.c_a;
assign obs_cfg_data = dut.c_d;
assign obs_go_e = dut.go_e;
assign obs_act = dut.act;
assign obs_issue = dut.u_e.issue;
assign obs_addr = dut.u_e.a_ctr;
assign obs_capture = dut.u_e.i2x_v;
assign obs_cap_bank = dut.u_e.i2x_bk;
assign obs_consume = dut.u_e.i2_v;
assign obs_XFIFO = dut.u_e.f_cnt;
endmodule
