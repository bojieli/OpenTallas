`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection Sinkhorn unit of the DeepSeek-V4.1 decode core,
// LATENCY-OPTIMISED: one whole normalisation step per clock.
//
// FUNCTION.  tools/hdc_golden_v41.py Model.hc_mixes after the exponential:
// given e = exp(comb - rowmax) (4 x 4, row-major, binary32), return
//     comb = e / seqsum_row(e) + eps               (step 0: rows)
//     comb = comb / (seqsum_col(comb) + eps)        (step 1: columns)
//     (ITERS - 1) x { rows, then columns }          (steps 2 .. 2 ITERS - 1)
// where every sum is SEQUENTIAL in index order, ((a + b) + c) + d, each
// addition and each division one IEEE binary32 operation (RNE, gradual
// underflow, every zero result +0).  2 ITERS = 40 normalisations for V4.1.
// The row max and the exponential stay in the stream unit's SFU (the golden's
// exp is its own polynomial); this unit starts where they end.
//
// WHY.  tools/decode_critical_path.py found V4.1's per-user decode bounded by
// this chain: 80 Sinkhorns per token, each 40 DEPENDENT normalisations, and a
// normalisation on the pipelined units costs 3 chained adds + the eps add +
// the 31-deep divider ot_hdc_fdiv = 51 cycles.  Area is nearly free here (one
// unit per sublayer engine), so this unit spends it on latency:
//
// * no pipeline registers inside a step: the state (16 words) is the only
//   register, and one clock is one normalisation.  A step is a single
//   combinational path  state -> 3 chained adds -> eps add -> seed ->
//   quotient -> state,  so it pays ONE register overhead, not ~51;
// * positive-only adders (ot_hdc_sk_add): every operand here is >= 0, so the
//   cancellation path of a general adder does not exist; S and S + 1 come
//   from one compound prefix adder and rounding only selects;
// * division by multiply-and-check (ot_hdc_sk_seed + ot_hdc_sk_quot): a
//   512-entry quadratic seed R with 1/T - 2^-26 < R <= 1/T (proved for all
//   2^23 significands), M' = floor(X' R) is M or M - 1, and two EXACT
//   remainder signs select M', M'+1 or M'+2: the correctly rounded quotient,
//   bit-identical to IEEE division by construction.  The seed depends only on
//   the denominator, so each row's four quotients share one;
// * all four rows (16 quotients) in parallel; the matrix is written back
//   TRANSPOSED each step, so the next step (columns) again sums storage rows:
//   no row/column select mux anywhere on the path.  40 steps is an even
//   number of transposes, so the result leaves in the input orientation.
//
// Steady-state operand ranges (why the step path needs no subnormal logic):
// after step 0 every element is q + eps >= eps (normal), every step's
// denominator is a positive sum + eps >= eps (normal), and a quotient
// x / (x + ... + eps) lies in [2^-23, 1] (normal).  Step 0 is the only one
// that can see subnormal e, a subnormal row sum or a subnormal quotient, so it
// runs as two cycles on a separate general datapath:
//   A: row sums -> normalise (leading-zero count) -> registers
//   B: seed -> quotient WITH gradual underflow -> + eps -> state
// and the step path is the lean one.  An out-of-range steady quotient cannot
// occur; if it did, `fault` would say so (fail closed).
//
// SCHEDULE.  Accept (in_valid & in_ready) -> A -> B -> 2 ITERS - 1 steps;
// out_valid pulses 2 ITERS + 1 clock edges after the accepting edge (41 for
// ITERS = 20) and `y` holds until the next accept.
//
// FAIL-CLOSED.  A nonfinite or negative (nonzero) input element, an overflow
// of a sum, a zero row sum (0/0) or a quotient out of range raises `fault`
// with out_valid, and y is then all +0 -- the hdc units' convention.  -0 is
// read as +0.
//
// CLOCK.  One step per clock makes this clock the STEP time.  In the ~1 GHz
// decode core the unit runs as a multicycle path (or on a divided clock):
// ceil(step_ns * f_core) core cycles per step.  Routed figures:
// results/physical_abi3/asap7/hdc/v41/ot_hdc_sinkhorn/.
// ---------------------------------------------------------------------------
module ot_hdc_sinkhorn #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD       // hc_eps = 1e-6 in binary32
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [511:0] in_e,                  // element (r, c) at [32 (4r + c) +: 32]
    output reg          out_valid,
    output wire [511:0] y,
    output reg          fault,
    output wire         busy
);
    localparam integer STEPS = 2 * ITERS - 1;  // steady steps after step 0
    localparam [1:0] P_IDLE = 2'd0, P_A = 2'd1, P_B = 2'd2, P_RUN = 2'd3;
    localparam [7:0]  EPS_E = (EPS[30:23] == 8'd0) ? 8'd1 : EPS[30:23];
    localparam [23:0] EPS_M = {EPS[30:23] != 8'd0, EPS[22:0]};

    reg [1:0]  ph;
    reg [7:0]  cnt;
    reg        flt;
    reg [31:0] er [0:15];                      // step-0 inputs
    reg [31:0] st [0:15];                      // the matrix, transposed every step
    // step-0 registers between A and B
    reg [23:0]       a_xm [0:15];
    reg signed [9:0] a_xe [0:15];
    reg              a_xz [0:15];
    reg [23:0]       a_tm [0:3];
    reg signed [9:0] a_te [0:3];

    assign in_ready = (ph == P_IDLE);
    assign busy = (ph != P_IDLE);

    genvar r, c;

    // ======================= step 0, cycle A: row sums, normalise =======================
    wire [15:0] a_bad_in;
    wire [3:0]  a_bad_sum;
    wire [23:0]       nx_m [0:15];
    wire signed [9:0] nx_e [0:15];
    wire              nx_z [0:15];
    wire [23:0]       nt_m [0:3];
    wire signed [9:0] nt_e [0:3];
    generate
        for (r = 0; r < 16; r = r + 1) begin : g_ain
            wire [31:0] w = er[r];
            assign a_bad_in[r] = (w[31] && (w[30:0] != 31'd0)) || (w[30:23] == 8'hFF);
            ot_hdc_sk_norm u_nx (.x(w[30:0]), .m(nx_m[r]), .e(nx_e[r]), .z(nx_z[r]));
        end
        for (r = 0; r < 4; r = r + 1) begin : g_arow
            wire [7:0]  ee [0:3];
            wire [23:0] mm [0:3];
            for (c = 0; c < 4; c = c + 1) begin : g_dec
                wire [31:0] w = er[4*r + c];
                assign ee[c] = (w[30:23] == 8'd0) ? 8'd1 : w[30:23];
                assign mm[c] = {w[30:23] != 8'd0, w[22:0]};
            end
            wire [7:0] e1, e2, e3, g1, g2, g3;
            wire [23:0] m1, m2, m3;
            wire o1, o2, o3, u1, u2, u3, tz;
            ot_hdc_sk_add u_a1 (.ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                                .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
            ot_hdc_sk_add u_a2 (.ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),
                                .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
            ot_hdc_sk_add u_a3 (.ea(g2), .ua(u2), .ma(m2), .eb(ee[3]), .mb(mm[3]),
                                .eg(g3), .up(u3), .e(e3), .m(m3), .ovf(o3));
            wire [30:0] sum = {m3[23] ? e3 : 8'd0, m3[22:0]};
            ot_hdc_sk_norm u_nt (.x(sum), .m(nt_m[r]), .e(nt_e[r]), .z(tz));
            assign a_bad_sum[r] = o1 | o2 | o3 | tz;
        end
    endgenerate

    // ======================= step 0, cycle B: divide with underflow, + eps ==============
    wire [31:0] b_out [0:15];
    wire [15:0] b_bad;
    generate
        for (r = 0; r < 4; r = r + 1) begin : g_brow
            wire [28:0] rs;
            ot_hdc_sk_seed u_seed (.tm(a_tm[r]), .r(rs));
            for (c = 0; c < 4; c = c + 1) begin : g_bel
                wire [30:0] q;
                wire rng, ov;
                ot_hdc_sk_quot #(.SUBN(1)) u_q (.xm(a_xm[4*r + c]), .xe(a_xe[4*r + c]), .xz(a_xz[4*r + c]),
                                                .tm(a_tm[r]), .te(a_te[r]), .r(rs), .y(q), .range(rng));
                wire [7:0]  qe = (q[30:23] == 8'd0) ? 8'd1 : q[30:23];
                wire [23:0] qm = {q[30:23] != 8'd0, q[22:0]};
                wire [7:0]  oe, og;
                wire [23:0] om;
                wire        ou;
                ot_hdc_sk_add u_eps (.ea(qe), .ua(1'b0), .ma(qm), .eb(EPS_E), .mb(EPS_M),
                                     .eg(og), .up(ou), .e(oe), .m(om), .ovf(ov));
                // transposed write: storage row c holds logical column c
                assign b_out[4*c + r] = {1'b0, om[23] ? oe : 8'd0, om[22:0]};
                assign b_bad[4*r + c] = rng | ov;
            end
        end
    endgenerate

    // ======================= steady step: sum, + eps, divide ============================
    wire [31:0] s_out [0:15];
    wire [15:0] s_bad;
    generate
        for (r = 0; r < 4; r = r + 1) begin : g_srow
            wire [7:0]  ee [0:3];
            wire [23:0] mm [0:3];
            wire [3:0]  sub;
            for (c = 0; c < 4; c = c + 1) begin : g_dec
                wire [31:0] w = st[4*r + c];
                assign ee[c]  = (w[30:23] == 8'd0) ? 8'd1 : w[30:23];
                assign mm[c]  = {w[30:23] != 8'd0, w[22:0]};
                assign sub[c] = (w[30:23] == 8'd0);
            end
            wire [7:0] e1, e2, e3, et, g1, g2, g3, gt;
            wire [23:0] m1, m2, m3, mt;
            wire o1, o2, o3, ot, u1, u2, u3, ut;
            // the chain: each add takes the previous one's exponent as eg + up (up resolves last)
            ot_hdc_sk_add u_s1 (.ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                                .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
            ot_hdc_sk_add u_s2 (.ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),
                                .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
            ot_hdc_sk_add u_s3 (.ea(g2), .ua(u2), .ma(m2), .eb(ee[3]), .mb(mm[3]),
                                .eg(g3), .up(u3), .e(e3), .m(m3), .ovf(o3));
            ot_hdc_sk_add u_ae (.ea(g3), .ua(u3), .ma(m3), .eb(EPS_E), .mb(EPS_M),
                                .eg(gt), .up(ut), .e(et), .m(mt), .ovf(ot));
            // t >= eps is normal: its significand is already normalised
            wire signed [9:0] te = $signed({2'b00, et}) - 10'sd127;
            wire [28:0] rs;
            ot_hdc_sk_seed u_seed (.tm(mt), .r(rs));
            for (c = 0; c < 4; c = c + 1) begin : g_sel
                wire [30:0] q;
                wire rng;
                ot_hdc_sk_quot #(.SUBN(0)) u_q (.xm(mm[c]), .xe($signed({2'b00, ee[c]}) - 10'sd127), .xz(1'b0),
                                                .tm(mt), .te(te), .r(rs), .y(q), .range(rng));
                assign s_out[4*c + r] = {1'b0, q};
                assign s_bad[4*r + c] = rng | sub[c] | o1 | o2 | o3 | ot | !mt[23];
            end
        end
    endgenerate

    // ======================= control ===================================================
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= P_IDLE;
            cnt <= 8'd0;
            flt <= 1'b0;
            out_valid <= 1'b0;
            fault <= 1'b0;
        end else begin
            out_valid <= 1'b0;
            case (ph)
                P_IDLE: if (in_valid) begin
                    ph <= P_A;
                    flt <= 1'b0;
                end
                P_A: begin
                    ph <= P_B;
                    flt <= flt | (|a_bad_in) | (|a_bad_sum);
                end
                P_B: begin
                    flt <= flt | (|b_bad);
                    cnt <= STEPS[7:0];
                    if (STEPS == 0) begin
                        ph <= P_IDLE;
                        out_valid <= 1'b1;
                        fault <= flt | (|b_bad);
                    end else ph <= P_RUN;
                end
                default: begin
                    flt <= flt | (|s_bad);
                    cnt <= cnt - 8'd1;
                    if (cnt == 8'd1) begin
                        ph <= P_IDLE;
                        out_valid <= 1'b1;
                        fault <= flt | (|s_bad);
                    end
                end
            endcase
        end
    end

    always @(posedge clk) begin
        for (k = 0; k < 16; k = k + 1) begin
            if (in_ready && in_valid) er[k] <= in_e[32*k +: 32];
            if (ph == P_A) begin
                a_xm[k] <= nx_m[k];
                a_xe[k] <= nx_e[k];
                a_xz[k] <= nx_z[k];
            end
            if (ph == P_B) st[k] <= b_out[k];
            else if (ph == P_RUN) st[k] <= s_out[k];
        end
        for (k = 0; k < 4; k = k + 1) if (ph == P_A) begin
            a_tm[k] <= nt_m[k];
            a_te[k] <= nt_e[k];
        end
    end

    generate
        for (r = 0; r < 16; r = r + 1) begin : g_y
            assign y[32*r +: 32] = fault ? 32'd0 : st[r];
        end
    endgenerate
endmodule
