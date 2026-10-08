`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_chain2u2 (BF rowfix unroll-by-2, 2026-10-07): ot_v41_chain2's per-slot golden chunk chains UNROLLED BY 2 on
// a half-rate gated clock.  Bit-exact and in order: every slot's terms are added sequentially from +0 in arrival order,
// exactly as ot_v41_chain2; only the latency changes (constant, +UL cycles), throughput stays one term per cycle.
//
//   full rate (clk): two input registers (r = newest beat, q = the one before) and the slot-revisit fault check of
//       ot_v41_chain2 (unchanged expression on the r stage).
//   half rate (hclk = clk gated every other cycle by a local ph flop, latch + AND ICG): at each gated edge the pair
//       {q (older), r (newer)} is captured (hs_*), and two ot_v41_fadd (hs_addA for the older beat, hs_addB for the
//       newer) each run at HALF the stages (CUTH: the original stage boundaries merged in pairs, LATH = LAT / 2 slow
//       steps, so a result is back after the same LAT clk cycles).  A slot is revisited >= LAT beats later (the issue
//       side's rule), so the two beats of one step are different slots and a revisit lands LATH or more steps later:
//       its operand is the result leaving EITHER adder in that step (age LATH), else the accumulator file (written at
//       the end of the step a result leaves; two write ports, always different slots).  The step has two clk periods
//       (multicycle 2/1 among the hs_* registers: physical/s81_native_bf/margin/u2_mc.sdc).
//   full rate out: the step's two results leave in order, older beat first, on two consecutive clk cycles.
// Requires LAT even.  Ports as ot_v41_chain2.
// ---------------------------------------------------------------------------
module ot_v41_chain2u2 #(
    parameter integer NCH = 16,
    parameter integer TW = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    // half-rate adder stage mask: CUT's 8 stages {0},{1},{2,3},{4},{5},{6},{7,8},{9} merged in pairs
    parameter [8:0] CUTH = 9'b0_0101_0010
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     v,
    input  wire [$clog2(NCH)-1:0]   slot,
    input  wire                     first,
    input  wire                     last,
    input  wire [31:0]              term,
    input  wire                     term_f,
    input  wire [TW-1:0]            tag,
    output wire                     ov,
    output wire [31:0]              osum,
    output wire                     of,
    output wire [TW-1:0]            otag,
    output reg                      fault
);
    localparam integer SW = $clog2(NCH);
    localparam integer LATH = 1 + CUTH[0] + CUTH[1] + CUTH[2] + CUTH[3] + CUTH[4] + CUTH[5] + CUTH[6] + CUTH[7] + CUTH[8];
`ifndef SYNTHESIS
    initial if (2 * LATH != LAT) $fatal(1, "ot_v41_chain2u2: CUTH must give LAT / 2 stages (LAT %0d, LATH %0d)", LAT, LATH);
`endif
    localparam integer BW = 1 + SW + 3 + 32 + TW;   // {v, slot, first, last, term_f, term, tag}

    // ---------------- full rate: input pair registers, revisit fault ------------------------------------------
    reg [BW-1:0] r_b, q_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin r_b[BW-1] <= 1'b0; q_b[BW-1] <= 1'b0; end
        else begin r_b[BW-1] <= v; q_b[BW-1] <= r_b[BW-1]; end
    always @(posedge clk) begin
        r_b[BW-2:0] <= {slot, first, last, term_f, term, tag};
        q_b[BW-2:0] <= r_b[BW-2:0];
    end
    wire          v_r = r_b[BW-1];
    wire [SW-1:0] slot_r = r_b[BW-2 -: SW];
    reg [LAT-1:0] pv;
    reg [SW-1:0] ps [0:LAT-1];
    integer k;
    reg hazard;
    always @* begin
        hazard = 1'b0;
        for (k = 0; k < LAT - 1; k = k + 1) if (pv[k] && ps[k] == slot_r) hazard = 1'b1;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pv <= '0; fault <= 1'b0; end
        else begin pv <= {pv[LAT-2:0], v_r}; if (v_r && hazard) fault <= 1'b1; end
    always @(posedge clk) begin
        ps[0] <= slot_r;
        for (k = 1; k < LAT; k = k + 1) ps[k] <= ps[k-1];
    end

    // ---------------- half-rate clock ---------------------------------------------------------------------------
    reg ph;                                     // 1 in the clk cycle that ends on a gated edge
    always @(posedge clk or negedge rst_n) if (!rst_n) ph <= 1'b0; else ph <= ~ph;
    wire hclk;
    ot_hdc_cg u_hcg (.clk(clk), .en(ph | !rst_n), .gclk(hclk));

    // ---------------- half rate: the pair, the two adders, the accumulator file ---------------------------------
    reg [BW-1:0] hs_a, hs_b;                    // older (A) and newer (B) beat of the step
    always @(posedge hclk or negedge rst_n)
        if (!rst_n) begin hs_a[BW-1] <= 1'b0; hs_b[BW-1] <= 1'b0; end
        else begin hs_a[BW-1] <= q_b[BW-1]; hs_b[BW-1] <= r_b[BW-1]; end
    always @(posedge hclk) begin hs_a[BW-2:0] <= q_b[BW-2:0]; hs_b[BW-2:0] <= r_b[BW-2:0]; end
    wire          av = hs_a[BW-1],           bv = hs_b[BW-1];
    wire [SW-1:0] as_ = hs_a[BW-2 -: SW],    bs_ = hs_b[BW-2 -: SW];
    wire          afst = hs_a[BW-SW-2],      bfst = hs_b[BW-SW-2];
    wire          alst = hs_a[BW-SW-3],      blst = hs_b[BW-SW-3];
    wire          atf = hs_a[BW-SW-4],       btf = hs_b[BW-SW-4];
    wire [31:0]   atm = hs_a[TW +: 32],      btm = hs_b[TW +: 32];
    wire [TW-1:0] atg = hs_a[TW-1:0],        btg = hs_b[TW-1:0];

    reg [31:0] hs_acc [0:NCH-1];
    reg [NCH-1:0] hs_accf;
    // results leaving the adders in this step: y*, valid sv*, and their slot / last / flag (delayed with the term)
    wire [31:0] ya, yb;
    wire [1:0]  ea, eb;
    wire        sva, svb;
    wire [SW+1+TW+1-1:0] da, db;                // {slot, last, tag, operand-or-term flag}
    wire [SW-1:0] ys_a = da[SW+1+TW+1-1 -: SW], ys_b = db[SW+1+TW+1-1 -: SW];
    wire          yl_a = da[TW+1],            yl_b = db[TW+1];
    wire          yf_a = da[0] | (ea != 2'd0), yf_b = db[0] | (eb != 2'd0);
    wire          na = sva && !yl_a,          nb = svb && !yl_b;   // a running sum (not a chain's last)
    // operands: +0 for a chain's first term, else the slot's sum leaving an adder now, else the stored sum
`ifdef W10_MUTANT_U2
    wire fa_a = 1'b0, fb_a = 1'b0, fa_b = 1'b0, fb_b = 1'b0;   // negative control: no forwarding
`else
    wire fa_a = na && ys_a == as_, fb_a = nb && ys_b == as_;
    wire fa_b = na && ys_a == bs_, fb_b = nb && ys_b == bs_;
`endif
    wire [31:0] opa = afst ? 32'd0 : fa_a ? ya : fb_a ? yb : hs_acc[as_];
    wire        ofa = afst ? 1'b0 : fa_a ? yf_a : fb_a ? yf_b : hs_accf[as_];
    wire [31:0] opb = bfst ? 32'd0 : fa_b ? ya : fb_b ? yb : hs_acc[bs_];
    wire        ofb = bfst ? 1'b0 : fa_b ? yf_a : fb_b ? yf_b : hs_accf[bs_];
    ot_v41_fadd #(.CUT(CUTH)) hs_addA (.clk(hclk), .rst_n(rst_n), .valid_in(av), .a(opa), .b(atm), .y(ya), .err(ea), .valid_out(sva));
    ot_v41_fadd #(.CUT(CUTH)) hs_addB (.clk(hclk), .rst_n(rst_n), .valid_in(bv), .a(opb), .b(btm), .y(yb), .err(eb), .valid_out(svb));
    ot_hdc_delay #(.W(SW + 1 + TW + 1), .D(LATH)) hs_dA (.clk(hclk), .rst_n(rst_n), .d({as_, alst, atg, ofa | atf}), .q(da));
    ot_hdc_delay #(.W(SW + 1 + TW + 1), .D(LATH)) hs_dB (.clk(hclk), .rst_n(rst_n), .d({bs_, blst, btg, ofb | btf}), .q(db));
    always @(posedge hclk or negedge rst_n)
        if (!rst_n) hs_accf <= '0;
        else begin
            if (na) hs_accf[ys_a] <= yf_a;
            if (nb) hs_accf[ys_b] <= yf_b;
        end
    always @(posedge hclk) begin
        if (na) hs_acc[ys_a] <= ya;
        if (nb) hs_acc[ys_b] <= yb;
    end

    // ---------------- full rate out: older result, then newer ---------------------------------------------------
    // ph = 0 in the clk cycle right after a gated edge (the step's results are the adders' output registers)
    reg          o_v, h_v;
    reg [31:0]   o_s, h_s;
    reg          o_f, h_f;
    reg [TW-1:0] o_t, h_t;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; h_v <= 1'b0; end
        else if (!ph) begin o_v <= sva && yl_a; h_v <= svb && yl_b; end
        else o_v <= h_v;
    always @(posedge clk)
        if (!ph) begin
            o_s <= ya; o_f <= yf_a; o_t <= da[TW:1];
            h_s <= yb; h_f <= yf_b; h_t <= db[TW:1];
        end else begin
            o_s <= h_s; o_f <= h_f; o_t <= h_t;
        end
    assign ov = o_v;
    assign osum = o_s;
    assign of = o_f;
    assign otag = o_t;
`ifndef SYNTHESIS
    integer n_same = 0, n_cross = 0;
    always @(posedge hclk) if (rst_n) begin
        if (av && !afst && fa_a) n_same = n_same + 1;
        if (av && !afst && fb_a) n_cross = n_cross + 1;
        if (bv && !bfst && fb_b) n_same = n_same + 1;
        if (bv && !bfst && fa_b) n_cross = n_cross + 1;
    end
`endif
endmodule
