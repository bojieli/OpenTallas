`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DRIVE-S81-IDX4 (10-20, MU.BAL.SX.3 / S81.BIND.2.P, dv_plan --idxrd 4): the slice `iq` query-source port.
//
// dsdv_idx_bsplit  framing-aware split of a C3 slice's band-port-B word stream bo = {pk[511:0], valid} (SVC FRAME
//                  PROTOCOL v1.1: header word [511:508] type, [491:480] len = payload words that follow) into
//                    o_s  -> the svc_rs ENTRY q port (unchanged traffic: every frame whose type is NOT an index frame)
//                    o_i  -> the index query chain (iq -> dsdv_idx_qf qs): frames of type 4 (IDX_S), 8 (IDX_G), 10
//                            (rank-tree frame), 11 (qf CONFIG frame: die uid, S81/PORTFIX-CFG 10-25), the only types
//                            dsdv_idx_qf / dsdv_idx_rg* consume.
//                  The svc entry's job endpoint (ot_s81_svc_job) discards and faults on any q frame without an armed job,
//                  so the index frames must NOT reach it; the svc q types in use are 1, 2, 3, 7, 9, 12, 13, 14
//                  (dsdv_svc_att, dsdv_sm_wire), disjoint from {4, 8, 10, 11}.
//                  Static: the whole frame (header + len valid words, gaps allowed) follows its header's route; no
//                  ready / credit; 1 edge pin -> pin on both outputs (the svc q path +1 edge: handed to the compiler's
//                  band-B schedule, DRIVE-S81-IDX4 README).  Reset: valid / framing state only (2-flop landed release);
//                  the payload copies are reset-free.  Fanout: the route flop drives only the two valid flops; every
//                  payload bit drives two D pins.
// ot_s81sl_slice_iq  the s_3S slice master under --idxrd 4: ot_s81sl_slice (unchanged) + dsdv_idx_bsplit on bo,
//                  exposing iq [512:0].  Same parameters / ports as ot_s81sl_slice plus iq.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_idx_bsplit #(
    parameter integer BW = 513,
    parameter integer MUT = 0      // bench negative control only: 1 = type 10 (tree frame) stays on the svc output, 2 = type 11
) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [BW-1:0]  i,       // {d[511:0], v}
    output reg  [BW-1:0]  o_s,     // -> svc entry q (non-index frames)
    output reg  [BW-1:0]  o_i      // -> index query chain (types 4 / 8 / 10)
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    wire        v    = i[0];
    wire [3:0]  ty   = i[512:509];          // d[511:508]
    wire [11:0] ln   = i[492:481];          // d[491:480]
    // S81/PORTFIX-CFG 10-25: type 11 = the dsdv_idx_qf CONFIG frame (die uid), also routed to the index chain
    wire        hidx = (ty == 4'd4) || (ty == 4'd8) || (ty == 4'd10 && MUT != 1) || (ty == 4'd11 && MUT != 2);
    reg         infr, rt;
    reg  [11:0] left;
    wire        r_now = infr ? rt : hidx;   // route of this word
    always @(posedge ck or negedge rn)
        if (!rn) begin infr <= 1'b0; rt <= 1'b0; left <= 12'd0; o_s[0] <= 1'b0; o_i[0] <= 1'b0; end
        else begin
            o_s[0] <= v && !r_now;
            o_i[0] <= v && r_now;
            if (v) begin
                if (!infr) begin infr <= ln != 12'd0; left <= ln; rt <= hidx; end
                else begin left <= left - 12'd1; if (left == 12'd1) infr <= 1'b0; end
            end
        end
    always @(posedge ck) begin o_s[BW-1:1] <= i[BW-1:1]; o_i[BW-1:1] <= i[BW-1:1]; end
endmodule

module ot_s81sl_slice_iq #(
    parameter integer HB = 0,
    parameter integer DL = 4,
    parameter integer DR = 6,
    parameter integer DX = 6,
    parameter integer VQ_XMEM = 2,
    parameter integer VS_MUT = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [512:0] bo,
    output wire [512:0]    iq,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    output wire            fault
);
    wire [512:0] bo_c;
    ot_s81sl_slice #(.HB(HB), .DL(DL), .DR(DR), .DX(DX), .VQ_XMEM(VQ_XMEM), .VS_MUT(VS_MUT)) u_sl (
        .clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo_c), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(fault));
    dsdv_idx_bsplit #(.BW(513)) u_bs (.ck(clk), .rst_n(rst_n), .i(bo_c), .o_s(bo), .o_i(iq));
endmodule
