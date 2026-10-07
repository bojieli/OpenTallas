`timescale 1ns/1ps
// Qwen ROM die LINK station (r21 masters qfd_lst_v / _v_split / _h_e / _h_w / _c / _c_split): one registered stage of
// NL stack links.  A die link bundle is 1,056 tracks = 528 a direction (512 data + 16 control: valid / credit / tag,
// LINK_TRACKS "512 each way + 32 control"); the link protocol is credit-based end to end (endpoint FIFOs sized to the
// round trip), so a station is a pure one-cycle delay in both directions with no same-cycle handshake.
// Every boundary is register-to-register (margin rule): inputs captured at the pin, every output driven by its own
// kept flop (no shared drivers across faces).
//   SHAPE 0 (straight, lst_v / lst_v_split / lst_h): a <-> b, NL links.
//   SHAPE 1 (corner, lst_c, NL = 2): v link 0 <-> w, v link 1 <-> e.
//   SHAPE 2 (corner split, lst_c_split, NL = 1): v -> w and v -> e (kept copies); toward v: w or e by the static
//            strap sel_e (the instance's mirror; a die tie-off, not a timed path).
// Control bits (low CW of each direction word) are reset (two-flop synchronised rst_n); data is not (valid qualifies).
module ot_qwen_die_link_stn #(
    parameter integer NL = 1,
    parameter integer SHAPE = 0,
    parameter integer LW = 528,
    parameter integer CW = 16,
    localparam integer BW = (SHAPE == 0) ? NL * LW : 1,   // unused faces shrink to one tied bit
    localparam integer CWW = (SHAPE == 0) ? 1 : LW
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               sel_e,
    // straight: a face / b face
    input  wire [NL*LW-1:0]   a_i,
    output wire [NL*LW-1:0]   a_o,
    input  wire [BW-1:0]      b_i,
    output wire [BW-1:0]      b_o,
    // corner: w face / e face (one link each)
    input  wire [CWW-1:0]     w_i,
    output wire [CWW-1:0]     w_o,
    input  wire [CWW-1:0]     e_i,
    output wire [CWW-1:0]     e_o
);
    reg r0, r1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin r0 <= 1'b0; r1 <= 1'b0; end else begin r0 <= 1'b1; r1 <= r0; end
    wire rs = r1;   // synchronised, active-high run
    function automatic [LW-1:0] gate(input [LW-1:0] x, input run);
        gate = {x[LW-1:CW], run ? x[CW-1:0] : {CW{1'b0}}};
    endfunction
    genvar k;
    generate if (SHAPE == 0) begin : g_straight
        (* keep *) reg [NL*LW-1:0] ab_q, ba_q;
        for (k = 0; k < NL; k = k + 1) begin : g_l
            always @(posedge clk) begin
                ab_q[k*LW +: LW] <= gate(a_i[k*LW +: LW], rs);
                ba_q[k*LW +: LW] <= gate(b_i[k*LW +: LW], rs);
            end
        end
        assign b_o = ab_q;
        assign a_o = ba_q;
        assign w_o = 1'b0;
        assign e_o = 1'b0;
    end else if (SHAPE == 1) begin : g_corner
        (* keep *) reg [LW-1:0] vw_q, ve_q, wv_q, ev_q;
        always @(posedge clk) begin
            vw_q <= gate(a_i[0 +: LW], rs);
            ve_q <= gate(a_i[LW +: LW], rs);
            wv_q <= gate(w_i, rs);
            ev_q <= gate(e_i, rs);
        end
        assign w_o = vw_q;
        assign e_o = ve_q;
        assign a_o = {ev_q, wv_q};
        assign b_o = 1'b0;
    end else begin : g_split
        (* keep *) reg [LW-1:0] vw_q, ve_q, xv_q;
        always @(posedge clk) begin
            vw_q <= gate(a_i[0 +: LW], rs);
            ve_q <= gate(a_i[0 +: LW], rs);
            xv_q <= gate(sel_e ? e_i : w_i, rs);   // sel_e: static strap
        end
        assign w_o = vw_q;
        assign e_o = ve_q;
        assign a_o = xv_q;
        assign b_o = 1'b0;
    end endgenerate
endmodule
