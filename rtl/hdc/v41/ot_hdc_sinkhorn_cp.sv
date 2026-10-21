`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// FAM-HBM-B/HCTAIL 10-21 (RELEASE_TREE H.STA.BLK.1): ot_hdc_sinkhorn_cp -- ot_hdc_sinkhorn_ce (below, unchanged function,
// interface and ce calendar) with the one-normalisation step cone cut into REGISTERED STAGES instead of the declared
// multicycle.  The step datapath uses the cut arithmetic of rtl/hdc/v41/ot_hdc_sk_arith_cp.sv (ot_hdc_skc_*): its inputs
// (er, a_*, st) change only on a ce edge and are held until the next one, so free-running cut registers settle the
// exact combinational value D edges after a ce edge, D = the most cuts on any path:
//   steady step  P1 M1 X1(|P2) M2 X2(|P3) M3 X3(|PE) ME XE  S1 S2 S3  Q1 Q2 Q3          D = 15
//   step 0 A     P1 M1 X1 M2 X2 M3 X3 (then sum normalise)                              D = 7
//   step 0 B     S1 S2 S3 Q1 Q2 Q3 QO  P M X (the + eps add)                             D = 10
// The caller's ce period STEP_CYC (the tail child's SDIV) must be >= D + 1 = 16.  Every path is then single-period
// (no multicycle SDC): segments between cuts are <= ~16 ASAP7 logic levels (~600 ps at TT).  CUT = 0 = ot_hdc_sinkhorn_ce.
// ---------------------------------------------------------------------------
module ot_hdc_sinkhorn_cp #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD,      // hc_eps = 1e-6 in binary32
    parameter integer CUT = 1                  // 1 = registered stages (needs STEP_CYC >= 16); 0 = combinational step
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         ce,                    // step enable: one core edge in STEP_CYC
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
            ot_hdc_skc_add #(.CUT(CUT)) u_a1 (.clk(clk), .ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                                .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
            ot_hdc_skc_add #(.CUT(CUT)) u_a2 (.clk(clk), .ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),
                                .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
            ot_hdc_skc_add #(.CUT(CUT)) u_a3 (.clk(clk), .ea(g2), .ua(u2), .ma(m2), .eb(ee[3]), .mb(mm[3]),
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
            ot_hdc_skc_seed #(.CUT(CUT)) u_seed (.clk(clk), .tm(a_tm[r]), .r(rs));
            for (c = 0; c < 4; c = c + 1) begin : g_bel
                wire [30:0] q;
                wire rng, ov;
                ot_hdc_skc_quot #(.SUBN(1), .CUT(CUT), .CUTO(1)) u_q (.clk(clk), .xm(a_xm[4*r + c]), .xe(a_xe[4*r + c]), .xz(a_xz[4*r + c]),
                                                .tm(a_tm[r]), .te(a_te[r]), .r(rs), .y(q), .range(rng));
                wire [7:0]  qe = (q[30:23] == 8'd0) ? 8'd1 : q[30:23];
                wire [23:0] qm = {q[30:23] != 8'd0, q[22:0]};
                wire [7:0]  oe, og;
                wire [23:0] om;
                wire        ou;
                ot_hdc_skc_add #(.CUT(CUT)) u_eps (.clk(clk), .ea(qe), .ua(1'b0), .ma(qm), .eb(EPS_E), .mb(EPS_M),
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
            ot_hdc_skc_add #(.CUT(CUT)) u_s1 (.clk(clk), .ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                                .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
            ot_hdc_skc_add #(.CUT(CUT)) u_s2 (.clk(clk), .ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),
                                .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
            ot_hdc_skc_add #(.CUT(CUT)) u_s3 (.clk(clk), .ea(g2), .ua(u2), .ma(m2), .eb(ee[3]), .mb(mm[3]),
                                .eg(g3), .up(u3), .e(e3), .m(m3), .ovf(o3));
            ot_hdc_skc_add #(.CUT(CUT)) u_ae (.clk(clk), .ea(g3), .ua(u3), .ma(m3), .eb(EPS_E), .mb(EPS_M),
                                .eg(gt), .up(ut), .e(et), .m(mt), .ovf(ot));
            // t >= eps is normal: its significand is already normalised
            wire signed [9:0] te = $signed({2'b00, et}) - 10'sd127;
            wire [28:0] rs;
            ot_hdc_skc_seed #(.CUT(CUT)) u_seed (.clk(clk), .tm(mt), .r(rs));
            for (c = 0; c < 4; c = c + 1) begin : g_sel
                wire [30:0] q;
                wire rng;
                ot_hdc_skc_quot #(.SUBN(0), .CUT(CUT), .CUTO(0)) u_q (.clk(clk), .xm(mm[c]), .xe($signed({2'b00, ee[c]}) - 10'sd127), .xz(1'b0),
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
        end else if (ce) begin
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

    always @(posedge clk) if (ce) begin
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
