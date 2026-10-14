`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cpin (s81-suhc-hier-1011, 2026-10-11): the CENTRE pin tile of the hierarchical S81 HC slab (dsfd_sp_hc
// HIER=1): 575.992 um wide, on the slab face above the combine tile.  It owns the centre third of the face: the
// adapter's controller-clock command / done pins, inp, the VM read slots, the status pins, the y valid / ready and the
// centre chain's y slice -- every pin in a flop, each crossing to the combine tile in one more (registered both sides).
//   y credit: y_rdy (a register) = the beats accepted and not yet popped (cnt: + accept here, - the combine tile's POST
//   beat notices) < TH; the accept pulse goes to the combine tile (with the centre slice) and to both outer roots, whose
//   FIFOs are YD >= TH + the pop lag deep.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cpin #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, TH = 8
) (
    input  wire                cck, crs, sk, srs,
    // die pins
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output reg                 c_done_v,
    output reg  [7:0]          c_done_tag,
    input  wire                inp,
    output reg  [S_RD-1:0]     rq_v,
    output reg  [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output reg                 flt,
    output reg                 online,
    output reg  [3:0]          fcode,
    input  wire                y_v,
    output reg                 y_rdy,
    input  wire [YS1-1:0]      y_s,
    // the outer roots: accept pulse
    (* keep = "true" *) output reg yacc_w,
    (* keep = "true" *) output reg yacc_e,
    // combine tile seam
    output reg                 n_cmd_v,
    output reg  [83:0]         n_cmd_d,
    input  wire                n_done_v,
    input  wire [7:0]          n_done_tag,
    output reg                 n_inp,
    input  wire [S_RD-1:0]     n_rq_v,
    input  wire [S_RD*14-1:0]  n_rq_row,
    output reg  [S_RD-1:0]     n_rs_v,
    output reg  [S_RD*512-1:0] n_rs_d,
    input  wire                n_flt,
    input  wire                n_online,
    input  wire [3:0]          n_fcode,
    (* keep = "true" *) output reg n_yacc,
    output reg  [YS1-1:0]      n_y,
    input  wire                n_ypop
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    // controller-clock domain: command in, done out (pin flops; the seam flops are the combine tile's)
    always @(posedge cck or negedge crs)
        if (!crs) begin n_cmd_v <= 1'b0; c_done_v <= 1'b0; end
        else begin n_cmd_v <= c_cmd_v; c_done_v <= n_done_v; end
    always @(posedge cck) begin n_cmd_d <= c_cmd_d; c_done_tag <= n_done_tag; end
    // slab clock
    reg       pop;
    reg [7:0] cnt;
    // Each identical acceptance pulse has its own physical pin flop. keep=true prevents synthesis from merging
    // the W/E/S copies; the recipe-2 pin hook places each at its own face, with no added cycle.
    wire      acc = y_v && y_rdy;
    always @(posedge sk or negedge srs)
        if (!srs) begin
            n_inp <= 1'b0; rq_v <= 0; n_rs_v <= 0; flt <= 1'b0; online <= 1'b0; fcode <= 0;
            y_rdy <= 1'b0; cnt <= 0; pop <= 1'b0; n_yacc <= 1'b0; yacc_w <= 1'b0; yacc_e <= 1'b0;
        end else begin
            n_inp <= inp; rq_v <= n_rq_v; n_rs_v <= rs_v; flt <= n_flt; online <= n_online; fcode <= n_fcode;
            pop <= n_ypop;
            cnt <= cnt + acc - pop;
            y_rdy <= (cnt + acc - pop) < TH;
            n_yacc <= acc; yacc_w <= acc; yacc_e <= acc;
        end
    always @(posedge sk) begin rq_row <= n_rq_row; n_rs_d <= rs_d; n_y <= y_s; end
endmodule
