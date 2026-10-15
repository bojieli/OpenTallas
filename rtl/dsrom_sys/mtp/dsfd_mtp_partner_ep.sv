`timescale 1ns/1ps
// Partner-slab ends of the head-die MTP sequencer links (mtp-fixlat-1011, 2026-10-10).
// dsfd_mtp_seq_rtt's own receivers were RTT-sized in d624193fb; its partners on the capture and VM slabs had no RTL
// (ds-1010 lat-audit: "capture / vm hub tiles have no t_mtp / f_mtp ports").  These are those ends, on the same grant
// protocol (ot_dsrom_mtp_ltx / ot_dsrom_mtp_lrx_rtt, rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_{pair,rtt}.sv):
//   * a transmitter (ltx) launches one flit per grant it has seen, so it is correct over ANY relay count;
//   * a receiver reserves one FIFO slot per grant still in flight over the WHOLE stationed round trip
//     (FORWARD_HOPS + RETURN_HOPS + 3) and is sized D = F + R + 4 for full rate.
// Station counts are the generator's pin-to-pin stages (tools/s81/hub_stage_count.py on head631, lat-audit
// head631_stages.json): capture -> mtp 6, mtp -> capture 7, vm -> mtp 11, mtp -> vm 11.
// The VM receiver runs SEL 1 (c_ready from the VM core selects precomputed next states) and OUTPUT_PIPE 1 (registered
// c_valid / c_data: +1 cycle per draft-head step, pipelined); the VM-core-facing transmitters register c_ready (ltx_rc).
// OT_FIXLAT_MUT_LAT1 (negative control): the VM receiver assumes a latency-1 link (0 relay hops, the legacy 3-cycle
// grant history) at the same depth -> must overflow on the stationed bench.
module dsfd_cap_mtp_ep #(parameter integer FLIT = 512) (
    input  wire [0:0] ck, rst,
    input  wire [0:0] c_rv, output wire [0:0] c_rr, input wire [FLIT-1:0] c_rd,                 // capture core: RESULT flit
    output wire [0:0] t_rv, output wire [FLIT-1:0] t_rd, input wire [0:0] f_rg          // -> dsfd_mtp_seq_rtt u_r
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    ot_dsrom_mtp_ltx #(.W(FLIT)) u_r (.clk(ck[0]), .rst_n(rn), .c_valid(c_rv), .c_ready(c_rr), .c_data(c_rd),
        .l_valid(t_rv[0]), .l_ready(f_rg[0]), .l_data(t_rd));
endmodule

module dsfd_vm_mtp_ep #(parameter integer NW = 21, parameter integer USER_W = 10,
                        parameter integer DW = USER_W + 3 + NW,
                        parameter integer FWD_H = 11,              // mtp -> vm (draft-head step data)
                        parameter integer RET_H = 11,              // vm -> mtp (its grant)
                        parameter integer D_H = FWD_H + RET_H + 4) (
    input  wire [0:0] ck, rst,
    input  wire [0:0] f_hv, input wire [DW-1:0] f_hd, output wire [0:0] t_hg,           // draft-head step from the seq
    output wire [0:0] c_hv, input wire [0:0] c_hr, output wire [DW-1:0] c_hd,
    input  wire [0:0] c_wv, output wire [0:0] c_wr, input wire [USER_W-1:0] c_wd,              // rows ready (VM core)
    output wire [0:0] t_wv, output wire [USER_W-1:0] t_wd, input wire [0:0] f_wg,
    input  wire [0:0] c_qv, output wire [0:0] c_qr, input wire [DW-1:0] c_qd,                  // draft-head result (VM core)
    output wire [0:0] t_qv, output wire [DW-1:0] t_qd, input wire [0:0] f_qg
);
`ifdef OT_FIXLAT_MUT_LAT1
    localparam integer HF = 0, HR = 0;
`else
    localparam integer HF = FWD_H, HR = RET_H;
`endif
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    ot_dsrom_mtp_lrx_rtt #(.W(DW), .D(D_H), .SEL(1), .ENABLE_RTT(1), .OUTPUT_PIPE(1), .FORWARD_HOPS(HF), .RETURN_HOPS(HR)) u_h (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_hv[0]), .l_ready(t_hg[0]), .l_data(f_hd), .c_valid(c_hv), .c_ready(c_hr), .c_data(c_hd));
    ot_dsrom_mtp_ltx_rc #(.W(USER_W)) u_w (.clk(ck[0]), .rst_n(rn), .c_valid(c_wv), .c_ready(c_wr), .c_data(c_wd),
        .l_valid(t_wv[0]), .l_ready(f_wg[0]), .l_data(t_wd));
    ot_dsrom_mtp_ltx_rc #(.W(DW)) u_q (.clk(ck[0]), .rst_n(rn), .c_valid(c_qv), .c_ready(c_qr), .c_data(c_qd),
        .l_valid(t_qv[0]), .l_ready(f_qg[0]), .l_data(t_qd));
endmodule

