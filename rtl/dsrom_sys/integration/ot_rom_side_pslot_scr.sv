`timescale 1ns/1ps
// Timing-screen frame of ot_rom_side_pslot (DS-ROM correctness, 2026-10-04): every input is launched from a
// register, as in the controller (hdr_user / hdr_pos, side_user / side_pos, the link's registered header word), so
// the screened reg-to-reg paths are the in-context ones (the screen false-paths IO).  sel_new gates ok_q only.
module ot_rom_side_pslot_scr #(
    parameter integer MAXU = 866,
    parameter integer USER_W = 10,
    parameter integer NW = 21,
    parameter integer PSL = 3,
    parameter integer SIDE_IN = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              rx_hdr,
    input  wire [USER_W-1:0] in_user,
    input  wire [NW-1:0]     in_pos,
    input  wire [USER_W-1:0] hdr_user,
    input  wire [NW-1:0]     hdr_pos,
    input  wire              inc_v,
    input  wire [USER_W-1:0] inc_user,
    input  wire [NW-1:0]     inc_pos,
    input  wire              dec_v,
    input  wire              chk_v,
    output wire              ok_q,
    output wire              conflict
);
    reg              r_rx_hdr, r_inc_v, r_dec_v, r_chk_v;
    reg [USER_W-1:0] r_in_user, r_hdr_user, r_inc_user;
    reg [NW-1:0]     r_in_pos, r_hdr_pos, r_inc_pos;
    always @(posedge clk) begin
        r_rx_hdr <= rx_hdr; r_inc_v <= inc_v; r_dec_v <= dec_v; r_chk_v <= chk_v;
        r_in_user <= in_user; r_hdr_user <= hdr_user; r_inc_user <= inc_user;
        r_in_pos <= in_pos; r_hdr_pos <= hdr_pos; r_inc_pos <= inc_pos;
    end
    ot_rom_side_pslot #(.MAXU(MAXU), .USER_W(USER_W), .NW(NW), .PSL(PSL), .SIDE_IN(SIDE_IN)) u (
        .clk(clk), .rst_n(rst_n),
        .sel_new(r_rx_hdr), .sel_user(r_hdr_user), .sel_pos(r_hdr_pos), .ok_q(ok_q),
        .inc_v(r_inc_v), .inc_user(r_inc_user), .inc_pos(r_inc_pos),
        .dec_v(r_dec_v), .dec_user(r_hdr_user), .dec_pos(r_hdr_pos),
        .chk_v(r_chk_v), .chk_user(r_in_user), .chk_pos(r_in_pos), .conflict(conflict));
endmodule
