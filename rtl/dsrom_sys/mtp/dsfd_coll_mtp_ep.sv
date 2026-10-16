`timescale 1ns/1ps
// dsfd_coll_mtp_ep (ds-1010 lat-audit, 2026-10-10): the collective slab's end of the head-die MTP sequencer links,
// RTT-sized to the generator's real pin-to-pin stages (tools/s81/hub_stage_count.py, head631: mtp -> collective 8,
// collective -> mtp 8; the chain record alone says 6 / 7).  Receivers of the sequencer's token return (t_tv / t_td) and
// seed (t_sv / t_sd): ot_dsrom_mtp_lrx_rtt with FORWARD_HOPS = mtp -> collective, RETURN_HOPS = collective -> mtp,
// depth F + R + 4 (full rate).  A legacy ot_dsrom_mtp_lrx (3-cycle grant history) here overflows; a receiver sized for
// fewer stages than the die builds overflows (tools/mtp_seq_rtt_link_gate.py pass_c / fail_stale_c / fail_legacy_c).
// The consumer takes c_* valid / ready.  Bound into dsfd_sp_collective's dedicated MTP lane (mtp-colllane-1011):
// rtl/dsrom_sys/s81_ph/coll/dsfd_coll_mtp_lane.sv, OPIPE = 1 (registered c_* outputs, ot_dsrom_mtp_lrx_rtt OUTPUT_PIPE).
module dsfd_coll_mtp_ep #(parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
                          parameter integer SW = USER_W + 3 * NW + 4,
                          parameter integer FWD_C = 8, parameter integer RET_C = 8,
                          parameter integer D_C = FWD_C + RET_C + 4, parameter integer OPIPE = 0) (
    input  wire [0:0] ck, rst,
    input  wire [0:0] f_tv, input wire [FLIT-1:0] f_td, output wire [0:0] t_tg,   // token return from dsfd_mtp_seq_rtt
    input  wire [0:0] f_sv, input wire [SW-1:0] f_sd, output wire [0:0] t_sg,     // seed from dsfd_mtp_seq_rtt
    output wire       c_tv, input wire c_tr, output wire [FLIT-1:0] c_td,
    output wire       c_sv, input wire c_sr, output wire [SW-1:0] c_sd
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    ot_dsrom_mtp_lrx_rtt #(.W(FLIT), .D(D_C), .ENABLE_RTT(1), .OUTPUT_PIPE(OPIPE), .FORWARD_HOPS(FWD_C), .RETURN_HOPS(RET_C)) u_t (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_tv[0]), .l_ready(t_tg[0]), .l_data(f_td), .c_valid(c_tv), .c_ready(c_tr), .c_data(c_td));
    ot_dsrom_mtp_lrx_rtt #(.W(SW), .D(D_C), .ENABLE_RTT(1), .OUTPUT_PIPE(OPIPE), .FORWARD_HOPS(FWD_C), .RETURN_HOPS(RET_C)) u_s (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_sv[0]), .l_ready(t_sg[0]), .l_data(f_sd), .c_valid(c_sv), .c_ready(c_sr), .c_data(c_sd));
endmodule
