`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_sm_tcpv_col: the SM's BF16 (tc) column with the ATTENTION PV MODE (H-SM-ATT 2026-10-15, attention on the SM
// engines).  The L lanes are ot_gpu_tc_col's lanes UNCHANGED (exact BF16 x BF16 -> FP32 product ot_hdc_bmul, circulating
// FP32 RNE adder ot_gpu_fadd holding IL = 8 slot sums, each slot's products added strictly in k order from +0), so:
//
//   QK / matvec mode (tag[TAGW-1] = 0): bit-identical to ot_gpu_tc_col: at `last` the L lane chunk sums enter the fixed
//      pairwise tree (ot_gpu_tree) -> one FP32 per slot (lane l = golden chunk g*L + l; the bottom log2 L tree levels).
//   PV mode (tag[TAGW-1] = 1): lane l of slot s holds HEAD DIM d(s, l) (the KV converter's beat s), the k-steps are TOKENS,
//      a chunk is 8 consecutive tokens (golden csum8 over positions).  At `last` the tree is bypassed: each lane's chunk
//      sum enters a per-lane BINARY-COUNTER MERGE = the golden's pairwise tree over chunk sums:
//         chunk c of a run:  v = sum;  for k = 0..: if bit k of c: v = add(stack[k], v) else { stack[k] = v; stop }
//      and at the run's last chunk (tag run_last) a FLUSH folds the stack for the zero-padded power-of-two run:
//         R = +0;  for k = 0 .. LV-1:  R = bit k of n ? add(stack[k], R) : add(R, +0)        (n = chunks of the run)
//      add(x, +0) = x bit for bit (canonical zeros), so this is exactly the golden node over an aligned run of
//      2^m >= n chunks whose missing chunks are the golden's +0 padding.  The run's node (L lanes) leaves on pv_*.
//
// MERGE TIMING (fixed, no arbitration): the ring rotates the slots one per cycle, so slot s's chunk sums always emerge on
// the same cycle residue mod 8.  The merge is a BARREL over 8 entries indexed by a free-running residue counter: the
// entry whose turn it is issues at most one add per lane on the per-lane merge adder (ot_gpu_fadd, LAT 7 = IL - 1, so
// its result is back exactly at the entry's next turn).  Different slots never share a turn; a chain of d carries takes
// 8d cycles and the flush 8(LV + 1); both end before the slot's next chunk (>= 64 cycles) when LV <= 3 or the run gap
// allows it (an event on a busy entry is a FAULT: fail closed, never a stall).
// STACK: one 1R1W 64x512 macro per column (L = 16 lanes x 32 b), word {entry, level}; read issued the cycle before the
// entry's turn (registered macro output), written at the turn.
//
// Tag layout (TAGW >= 6): [TAGW-1] pv, [TAGW-2] run_first, [TAGW-3] run_last, low bits = caller's tag (slot id ...).
// Mutants: MUT 1 = the stack is read one level too high (a carry adds the wrong partial: not the pairwise tree); MUT 2 = the flush's top fold level drops the carried node (R := +0 at level LV-1 when its bit is clear).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_sm_tcpv_col #(
    parameter integer L    = 16,
    parameter integer IL   = 8,
    parameter integer TAGW = 16,
    parameter integer ALAT = 7,
    parameter integer LV   = 4,         // merge stack levels: runs up to 2^(LV-1) chunks
    parameter integer MUT  = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            first,
    input  wire            last,
    input  wire [TAGW-1:0] tag,
    input  wire [L*16-1:0] w,
    input  wire [L*16-1:0] x,
    // QK / matvec result (ot_gpu_tc_col port)
    output wire            ov,
    output wire [31:0]     y,
    output wire [TAGW-1:0] otag,
    // PV result: one run node (L lanes) per output
    output wire            pv_v,
    output wire [L*32-1:0] pv_y,
    output wire [TAGW-1:0] pv_tag,
    output wire            fault
);
    initial if (IL != 8 || ALAT != IL - 1 || L != 16 || LV < 1 || LV > 8)
        $fatal(1, "ot_hbm_sm_tcpv_col: IL 8, ALAT 7, L 16 (one 64x512 stack macro), 1 <= LV <= 8");
    localparam integer FB = IL - ALAT;
    // ---------------- lanes: ot_gpu_tc_col verbatim ----------------
    reg            v_q, first_q, last_q;
    reg [L-1:0]    v_ql;
    reg [TAGW-1:0] tag_q;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v_q <= 1'b0; first_q <= 1'b0; last_q <= 1'b0; v_ql <= {L{1'b0}}; end
        else begin v_q <= v; first_q <= v && first; last_q <= v && last; v_ql <= {L{v}}; end
    end
    always @(posedge clk) begin w_q <= w; x_q <= x; tag_q <= tag; end
    wire [5:0] fl;
    ot_hdc_vline #(.D(5)) u_f (.clk(clk), .rst_n(rst_n), .v(first_q), .vd(fl));
    localparam integer LL = 5 + ALAT;
    wire [LL:0] ll;
    ot_hdc_vline #(.D(LL)) u_l (.clk(clk), .rst_n(rst_n), .v(last_q), .vd(ll));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LL)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d));
    wire [5:0] vl;
    ot_hdc_vline #(.D(5)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vl));
    wire [L*32-1:0] sum;
    wire [L-1:0] lf;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        wire f0, f1;
        wire [15:0] wg = v_ql[l] ? w_q[16*l +: 16] : 16'd0;
        ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q), .a({wg, 16'd0}),
                           .b({x_q[16*l +: 16], 16'd0}), .y(prod), .fault(f0));
        always @(posedge clk) acc_q <= fl[4] ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(vl[5]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        assign lf[l] = f0 | f1;
    end endgenerate
    // ---------------- QK / matvec: the column tree (chunk ends of matvec-mode beats only) ----------------
    wire pvd = tag_d[TAGW-1];
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(L), .TAGW(TAGW), .ALAT(ALAT)) u_tree (.clk(clk), .rst_n(rst_n), .v(ll[LL] && !pvd), .d(sum),
        .tag(tag_d), .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    reg lane_fault, ov_q, tfault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lane_fault <= 1'b0; ov_q <= 1'b0; tfault_q <= 1'b0; end
        else begin lane_fault <= lane_fault | (|lf); ov_q <= t_ov; tfault_q <= tfault_q | tf; end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q; assign y = y_q; assign otag = otag_q;

    // Shared merge leaf: the hierarchical SM can reuse its CLOSED tcl lanes.
    wire merge_fault;
    ot_hbm_sm_pv_merge #(.L(L), .IL(IL), .TAGW(TAGW), .ALAT(ALAT), .LV(LV), .MUT(MUT)) u_pv (
        .clk(clk), .rst_n(rst_n), .ev(ll[LL] && pvd), .sum(sum), .tag_d(tag_d),
        .pv_v(pv_v), .pv_y(pv_y), .pv_tag(pv_tag), .fault(merge_fault),
        .pub_start(1'b0), .pub_slot(3'd0), .pub_v(), .pub_data(), .pub_word(), .pub_out_slot(), .pub_tag(),
        .fold_start(1'b0), .fold_a(3'd0), .fold_b(3'd0));
    assign fault = lane_fault | tfault_q | merge_fault;
endmodule
`default_nettype wire
