// Experimental companion: FAST/PP/BP default off; no adoption or clock claim.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_field_w17w10_sys: default-off successor of ot_v41_field_w17w10 (rtl/v41die/ot_v41_field_w17w10.sv,
// pinned and unchanged).  With FAULT_TIE = 0 and RET_CREDIT = 0 the original ports behave exactly as the
// original's (same pairs, nodes, roots and wiring); the added ports are then constants (r_near_full = 0,
// ret_ovf = 0, r_occ = 0) or pure observation (r_push = the roots' r_v).
//
// FAULT_TIE (gap review D1/S1).  n_fault is [NL-1:0]; the LS node levels drive indices 0 .. NL-R-1 and the
// original ties only bit NL-1, so the R-1 bits NL-R .. NL-2 are undriven and ORed into `fault` (X in a 4-state
// simulator, floating in synthesis).  FAULT_TIE = 1 ties every undriven bit to 0, so `fault` is always 0/1.
//
// RET_CREDIT (gap review B2a).  The element -> return tree -> VM row-write path has no ready: nodes and roots
// raise only an overflow fault and the spine writes rows with w_we and no ACK.  RET_CREDIT = 1 adds, per return
// region, a row FIFO of RET_OD entries after the region's root (fall-through: empty + ready forwards the root's
// registered row in the same cycle, so no cycle is added at full rate) popped by r_ready (the spine's VM write
// port ready, ot_v41_spine_w17w10_sys), and a credit signal r_near_full[g] = (RET_OD - occupancy_g < RET_H)
// that the spine uses to stop ISSUING x beats.  The tree itself is never stalled: the roots keep accepting
// partials, so no node or root FIFO sees any change in pressure from a stalled VM writer, and no node/root
// arithmetic or order changes (results are bit-identical; only the beat calendar gains idle beats, which the
// elements already tolerate: "an idle beat is always safe", ot_v41_spine_w17w10.sv).
//
// Why the credit is a row-slot headroom and not a per-row reservation: the elements have no stall input and the
// beat -> row map lives in the per-element configuration ROMs, not at the spine, so the spine cannot reserve one
// slot per row before the row's first beat.  The credit reserves RET_H row slots per region instead; it is sound
// when RET_H >= F + 1, F = the rows a region can still emit after the last issued beat (rows in flight), and the
// +1 covers the spine's registered gate.  F <= the region's rows in one phase (a phase's FIFO is empty when the
// next phase starts: the spine is single-outstanding and finishes a phase only after its last row is written), so
// RET_H = max rows/region/phase + 1 is a proof for a given image set; a tighter RET_H needs the issue/return
// calendar walker (tools/model_dsrom_issue_return_calendar.py).  The invariant is checked in hardware: a push
// into a full FIFO sets ret_ovf (sticky, folded into fault).
// ---------------------------------------------------------------------------
module ot_v41_field_w17w10_sys #(
    parameter integer NP = 8,           // element pairs (power of two)
    parameter integer R = 2,            // return regions / roots (power of two, <= 2*NP / 2)
    parameter integer NBF = 2,          // pairs with BF16 lanes
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XFQ = 4,
    parameter integer XFB = 8,
    parameter integer LV = 5,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer BYPASS = 1,
    parameter integer RST = 1,
    parameter integer RD = 64,
    parameter integer ROOTD = 128,
    parameter integer PHW = 6,
    parameter integer FAULT_TIE = 0,    // 1: every n_fault bit driven (undriven ones tied 0)
    parameter integer RET_CREDIT = 0,   // 1: per-region row FIFO + ready + issue credit
    parameter integer RET_OD = 16,      // row FIFO entries per region (power of two)
    parameter integer RET_H = 16        // row slots reserved per region before a beat may issue (<= RET_OD)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_go,
    input  wire [PHW-1:0] cfg_ph,
    input  wire [2:0]   cfg_np,
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
    output wire [R-1:0]    r_v,
    output wire [16*R-1:0] r_row,
    output wire [3*R-1:0]  r_pos,
    output wire [32*R-1:0] r_fp32,
    output wire [16*R-1:0] r_bf16,
    output wire [R-1:0]    r_e,
    output wire         busy,
    output wire         fault,
    // RET_CREDIT
    input  wire [R-1:0]    r_ready,       // the consumer takes r_v[g] this cycle (ignored when RET_CREDIT = 0)
    output wire [R-1:0]    r_near_full,   // issue credit exhausted in region g (0 when RET_CREDIT = 0)
    output wire [R-1:0]    r_push,        // root g finished a row this cycle (observation)
    output wire [8*R-1:0]  r_occ,         // row FIFO occupancy per region (observation; 0 when RET_CREDIT = 0)
    output wire            ret_ovf        // sticky: a row was pushed into a full FIFO (0 when RET_CREDIT = 0)
);
    localparam integer NL = 2 * NP;               // leaves (macros)
    localparam integer L = $clog2(NL);
    localparam integer LR = $clog2(R);
    localparam integer LS = L - LR;               // levels inside a region
    function automatic is_bf(input integer p);
        integer i;
        begin
            is_bf = 1'b0;
            for (i = 0; i < NBF; i = i + 1) if ((i * NP) / NBF == p) is_bf = 1'b1;
        end
    endfunction
    wire        nv [0:LS][0:NL-1];
    wire [31:0] nt [0:LS][0:NL-1];
    wire [31:0] nd [0:LS][0:NL-1];
    wire        ne [0:LS][0:NL-1];
    wire [NP-1:0] p_busy, p_fault;
    wire [NL-1:0] n_fault;
    genvar g, l;
    generate for (g = 0; g < NP; g = g + 1) begin : g_p
        wire [1:0] pv, perr;
        wire [63:0] pval;
        wire [31:0] prow;
        wire [9:0] pseg, pnseg;
        wire [5:0] ppos;
        ot_v41_pair_w17w10 #(.NSEG(NSEG), .NCH(NCH), .XF(is_bf(g) ? XFB : XFQ), .LV(LV), .BF16(is_bf(g) ? 1 : 0),
                      .FAST(FAST), .PP(PP), .BP(BP), .MTP(MTP), .EARLY(EARLY), .PHW(PHW), .INSTANCE($sformatf("e%0d", g))) u_p (
            .clk(clk), .rst_n(rst_n), .cfg_go(cfg_go), .cfg_ph(cfg_ph), .cfg_np(cfg_np), .go(go), .go_bf(go_bf),
            .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
            .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv),
            .xb_u(xb_u), .xb_d(xb_d), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg),
            .perr(perr), .ppos(ppos), .busy(p_busy[g]), .fault(p_fault[g]), .quiet());
        genvar m;
        for (m = 0; m < 2; m = m + 1) begin : g_m
            assign nv[0][2*g+m] = pv[m];
            assign nt[0][2*g+m] = {ppos[3*m +: 3], prow[16*m +: 16], pseg[5*m +: 5], 3'd0, pnseg[5*m +: 5]};
            assign nd[0][2*g+m] = pval[32*m +: 32];
            assign ne[0][2*g+m] = perr[m];
        end
    end endgenerate
    generate for (l = 0; l < LS; l = l + 1) begin : g_lv
        for (g = 0; g < (NL >> (l + 1)); g = g + 1) begin : g_n
            ot_v41_retn_w17w10 #(.RD(RD), .RST(RST), .BYPASS(BYPASS)) u_n (.clk(clk), .rst_n(rst_n),
                .a_v(nv[l][2*g]), .a_t(nt[l][2*g]), .a_d(nd[l][2*g]), .a_e(ne[l][2*g]),
                .b_v(nv[l][2*g+1]), .b_t(nt[l][2*g+1]), .b_d(nd[l][2*g+1]), .b_e(ne[l][2*g+1]),
                .o_v(nv[l+1][g]), .o_t(nt[l+1][g]), .o_d(nd[l+1][g]), .o_e(ne[l+1][g]),
                .fault(n_fault[NL - (NL >> l) + g]), .quiet());     // level l starts after NL - NL/2^l nodes
        end
    end endgenerate
    // the roots (their registered outputs: q_*)
    wire [R-1:0]    q_v, q_e, rf;
    wire [16*R-1:0] q_row, q_bf16;
    wire [3*R-1:0]  q_pos;
    wire [32*R-1:0] q_fp32;
    generate for (g = 0; g < R; g = g + 1) begin : g_r
        ot_v41_ret_root #(.D(ROOTD), .QD(ROOTD)) u_root (.clk(clk), .rst_n(rst_n), .i_v(nv[LS][g]), .i_t(nt[LS][g]),
            .i_d(nd[LS][g]), .i_e(ne[LS][g]), .r_v(q_v[g]), .r_row(q_row[16*g +: 16]), .r_pos(q_pos[3*g +: 3]),
            .r_fp32(q_fp32[32*g +: 32]), .r_bf16(q_bf16[16*g +: 16]), .r_e(q_e[g]), .fault(rf[g]));
    end endgenerate
    assign r_push = q_v;
    // ------------------------------------------------------------------ D1: fault vector
    assign n_fault[NL-1] = 1'b0;
    generate if (FAULT_TIE != 0 && R > 1) begin : g_ftie
        assign n_fault[NL-2:NL-R] = {(R-1){1'b0}};
    end endgenerate
    // ------------------------------------------------------------------ B2a: row FIFO + credit
    wire [R-1:0] o_ovf;
    generate if (RET_CREDIT != 0) begin : g_cr
        localparam integer OW = $clog2(RET_OD);
        localparam integer EW = 16 + 3 + 32 + 16 + 1;
        for (g = 0; g < R; g = g + 1) begin : g_f
            reg [EW-1:0] mem [0:RET_OD-1];
            reg [OW-1:0] rd, wr;
            reg [OW:0]   occ;
            reg          ovf;
            wire [EW-1:0] din = {q_row[16*g +: 16], q_pos[3*g +: 3], q_fp32[32*g +: 32], q_bf16[16*g +: 16], q_e[g]};
            wire          emp = occ == 0;
            wire [EW-1:0] dout = emp ? din : mem[rd];
            wire          ov = !emp || q_v[g];
            wire          pop = !emp && r_ready[g];
            wire          push = q_v[g] && !(emp && r_ready[g]);     // fall-through: empty + ready takes the root's row
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin rd <= 0; wr <= 0; occ <= 0; ovf <= 1'b0; end
                else begin
                    if (push && occ == RET_OD && !pop) ovf <= 1'b1;
                    else begin
                        if (push) wr <= wr + 1'b1;
                        occ <= occ + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
                    end
                    if (pop) rd <= rd + 1'b1;
                end
            end
            always @(posedge clk) if (push && !(occ == RET_OD && !pop)) mem[wr] <= din;
            assign r_v[g] = ov;
            assign {r_row[16*g +: 16], r_pos[3*g +: 3], r_fp32[32*g +: 32], r_bf16[16*g +: 16], r_e[g]} = dout;
            assign r_near_full[g] = ({1'b0, occ} + (OW + 2)'(RET_H)) > (OW + 2)'(RET_OD);
            assign r_occ[8*g +: 8] = 8'(occ);
            assign o_ovf[g] = ovf;
        end
    end else begin : g_nocr
        assign r_v = q_v; assign r_row = q_row; assign r_pos = q_pos; assign r_fp32 = q_fp32;
        assign r_bf16 = q_bf16; assign r_e = q_e;
        assign r_near_full = {R{1'b0}};
        assign r_occ = {(8*R){1'b0}};
        assign o_ovf = {R{1'b0}};
    end endgenerate
    assign ret_ovf = |o_ovf;
    assign busy = |p_busy;
    assign fault = (|p_fault) | (|n_fault) | (|rf) | ret_ovf;
endmodule
