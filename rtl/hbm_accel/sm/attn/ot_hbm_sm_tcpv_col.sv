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
// Mutants: MUT 1 = merge adds (v, stack) in swapped order (non-commutative only through rounding: caught by exact
// compare); MUT 2 = flush skips the +0 fold (drops the top-level node of a padded run).
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
    output reg             pv_v,
    output reg  [L*32-1:0] pv_y,
    output reg  [TAGW-1:0] pv_tag,
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

    // ---------------- PV: barrel binary-counter merge ----------------
    localparam integer KW = 3;
    reg  [2:0]  bp;                                   // entry whose turn it is
    always @(posedge clk or negedge rst_n) if (!rst_n) bp <= 3'd0; else bp <= bp + 3'd1;
    wire [2:0]  nb = bp + 3'd1;
    reg  [7:0]  e_busy, e_fl, e_fin;                  // busy / flushing / flush after chain
    reg  [KW:0] e_k   [0:7];                          // level of the next turn (chain: carry level; flush: fold level)
    reg  [7:0]  e_c   [0:7];                          // chunk index being merged (chain)
    reg  [8:0]  e_n   [0:7];                          // chunks of the run so far
    reg  [TAGW-1:0] e_tag [0:7];
    // events of this cycle (lane chunk sums of a PV beat)
    wire        ev  = ll[LL] && pvd;
    // stack read for entry nb, landing at its turn (next cycle)
    wire [KW:0] rk = e_busy[nb] ? e_k[nb] : {(KW+1){1'b0}};
    wire [5:0]  sr_a = {nb, rk[2:0]};
    wire [L*32-1:0] st_rd;
    reg         sw_ce;
    reg  [5:0]  sw_a;
    reg  [L*32-1:0] sw_d;
    ot_sram_1r1w_64x512_m1_r2c2 u_stack (.clk(clk), .r_ce_in(1'b1), .r_addr_in(sr_a), .rd_out(st_rd),
        .w_ce_in(sw_ce), .w_addr_in(sw_a), .wd_in(sw_d), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // merge adder operands of this turn
    reg  [L*32-1:0] ma, mb;
    reg             mv;
    wire [L*32-1:0] my;
    wire [L-1:0]    mf;
    reg  [L*32-1:0] vreg;                             // adder result, back at the entry's next turn
    generate for (l = 0; l < L; l = l + 1) begin : g_madd
        ot_gpu_fadd #(.LAT(ALAT)) u_m (.clk(clk), .rst_n(rst_n), .v(mv), .a(ma[32*l +: 32]), .b(mb[32*l +: 32]),
                                       .y(my[32*l +: 32]), .fault(mf[l]));
    end endgenerate
    always @(posedge clk) vreg <= my;
    // turn logic (combinational) for entry r = bp
    wire [2:0] r = bp;
    wire       ev_first = tag_d[TAGW-2], ev_last = tag_d[TAGW-3];
    wire [7:0] ev_c = ev_first ? 8'd0 : e_n[r][7:0];
    reg        m_fault;
    always @(*) begin
        mv = 1'b0; ma = {L*32{1'b0}}; mb = {L*32{1'b0}};
        sw_ce = 1'b0; sw_a = {r, 3'd0}; sw_d = sum;
        if (ev) begin
            if (ev_c[0]) begin mv = 1'b1; if (MUT == 1) begin ma = sum; mb = st_rd; end else begin ma = st_rd; mb = sum; end end
            else begin sw_ce = 1'b1; sw_a = {r, 3'd0}; sw_d = sum; end
        end else if (e_busy[r] && !e_fl[r]) begin
            if (e_c[r][e_k[r][2:0]]) begin mv = 1'b1; if (MUT == 1) begin ma = vreg; mb = st_rd; end else begin ma = st_rd; mb = vreg; end end
            else begin sw_ce = 1'b1; sw_a = {r, e_k[r][2:0]}; sw_d = vreg; end
        end else if (e_busy[r] && e_fl[r] && e_k[r] < LV) begin
            mv = 1'b1;
            if (e_n[r][e_k[r][2:0]]) begin ma = st_rd; mb = (e_k[r] == 0) ? {L*32{1'b0}} : vreg; end
            else begin ma = (e_k[r] == 0) ? {L*32{1'b0}} : vreg; mb = {L*32{1'b0}};
                       if (MUT == 2 && e_k[r] == LV - 1) mv = 1'b0; end
        end
    end
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e_busy <= 8'd0; e_fl <= 8'd0; e_fin <= 8'd0; pv_v <= 1'b0; m_fault <= 1'b0;
            for (i = 0; i < 8; i = i + 1) begin e_k[i] <= 0; e_c[i] <= 8'd0; e_n[i] <= 9'd0; end
        end else begin
            pv_v <= 1'b0;
            if (|mf) m_fault <= 1'b1;
            if (ev) begin
                if (e_busy[r]) m_fault <= 1'b1;                       // chunk arrived while the entry still merges
                if (ev_c >= (8'd1 << (LV - 1))) m_fault <= 1'b1;      // run longer than the stack
                e_tag[r] <= tag_d;
                e_n[r] <= {1'b0, ev_c} + 9'd1;
                e_c[r] <= ev_c;
                if (ev_c[0]) begin e_busy[r] <= 1'b1; e_fl[r] <= 1'b0; e_k[r] <= 1; e_fin[r] <= ev_last; end
                else if (ev_last) begin e_busy[r] <= 1'b1; e_fl[r] <= 1'b1; e_k[r] <= 0; end
            end else if (e_busy[r] && !e_fl[r]) begin
                if (e_c[r][e_k[r][2:0]]) e_k[r] <= e_k[r] + 1;
                else if (e_fin[r]) begin e_fl[r] <= 1'b1; e_k[r] <= 0; end
                else e_busy[r] <= 1'b0;
            end else if (e_busy[r] && e_fl[r]) begin
                if (e_k[r] < LV) e_k[r] <= e_k[r] + 1;
                else begin e_busy[r] <= 1'b0; e_fl[r] <= 1'b0; pv_v <= 1'b1; end
            end
        end
    end
    always @(posedge clk) if (e_busy[r] && e_fl[r] && !(e_k[r] < LV) && !ev) begin pv_y <= vreg; pv_tag <= e_tag[r]; end
    assign fault = lane_fault | tfault_q | m_fault;
endmodule
`default_nettype wire
