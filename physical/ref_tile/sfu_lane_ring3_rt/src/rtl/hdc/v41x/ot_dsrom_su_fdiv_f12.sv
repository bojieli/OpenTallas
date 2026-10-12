`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_su_fdiv_f12: correctly rounded binary32 DIVISION for the 1.2 GHz domain (DS-ROM recovery lever
// su_softmax, default-off, new file).  The function, decode, finish and fault convention are those of
// ot_hdc_v41x_fdiv (rtl/hdc/v41x/ot_hdc_v41x_sfu.sv), bit for bit (rtl/test/tb_dsrom_su_fdiv_f12_eq.sv):
//   y = RN_even(a / b), gradual underflow, every zero result +0; a nonfinite operand, a zero divisor or an
//   overflowing quotient fails closed (fault, y = +0).
// Only the register boundaries move (the 19-deep unit screens -392 ps at 0.833 ns: its radix-4 step, its
// one-stage denormalise and its round-encode-select stage; the step subtract and the round increment are
// keep-prefix adders, ot_hdc_kadd / ot_hdc_kinc K 1):
//   2 decode (normalise | exponent difference) | 27 restoring steps, ONE quotient bit a stage (the same 27 bits and final remainder as the
//   radix-4 unit: floor(2x/mb) = 2 b_k + b_{k+1}) | F1 leading bit, sig, guard, sticky, biased exponent and the
//   subnormal shift | F2 denormalise | F3 round increment | F4 overflow test and select.   DEPTH 33, II 1.
// ---------------------------------------------------------------------------
module ot_dsrom_su_fdiv_f12 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer QB = 27;
    localparam integer DEPTH = 2 + QB + 4;     // 33

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    wire [33:0] na = norm(a[30:23], a[22:0]);
    wire [33:0] nb = norm(b[30:23], b[22:0]);

    // decode in two stages: normalise both operands (subnormal leading-one count and shift) | exponent difference
    reg        n_sign, n_zero, n_bad;
    reg [33:0] n_a, n_b;
    always @(posedge clk) begin
        n_sign <= a[31] ^ b[31];
        n_zero <= (a[30:0] == 31'd0);
        n_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        n_a    <= na;
        n_b    <= nb;
    end
    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= n_sign;
        d_zero <= n_zero;
        d_bad  <= n_bad;
        d_ma   <= n_a[33:10];
        d_mb   <= n_b[33:10];
        d_e    <= $signed({n_a[9], n_a[9:0]}) - $signed({n_b[9], n_b[9:0]});
    end

    reg [24:0]        r_rem  [0:QB-1];
    reg [QB-1:0]      r_q    [0:QB-1];
    reg [23:0]        r_mb   [0:QB-1];
    reg               r_sign [0:QB-1];
    reg               r_zero [0:QB-1];
    reg               r_bad  [0:QB-1];
    reg signed [10:0] r_e    [0:QB-1];
    genvar j;
    generate
        for (j = 0; j < QB; j = j + 1) begin : g_rec
            wire [23:0]   mb  = (j == 0) ? d_mb : r_mb[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [25:0]   x   = (j == 0) ? {2'b0, d_ma} : {r_rem[j-1][24:0], 1'b0};
            wire [26:0]   d1;                                   // x - mb (keep-prefix: ABC cannot re-ripple it)
            wire          bq;                                   // x >= mb: the carry out of x + ~mb + 1
            ot_hdc_kadd #(.W(27), .K(1)) u_sub (.a({1'b0, x}), .b(~{3'b0, mb}), .cin(1'b1), .s(d1), .cout(bq));
            always @(posedge clk) begin
                r_rem[j]  <= bq ? d1[24:0] : x[24:0];
                r_q[j]    <= {qin[QB-2:0], bq};
                r_mb[j]   <= mb;
                r_sign[j] <= (j == 0) ? d_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? d_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? d_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? d_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- F1: leading bit, significand, guard, sticky, biased exponent, subnormal shift ----
    wire [QB-1:0] q = r_q[QB-1];
    wire signed [10:0] be1 = r_e[QB-1] + (q[26] ? 11'sd127 : 11'sd126);
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st, f1_sub, f1_ovf;
    reg [23:0] f1_sig;
    reg [7:0]  f1_field;
    reg [4:0]  f1_sh;
    wire [10:0] sh_full = 11'sd1 - be1;
    always @(posedge clk) begin
        f1_sign <= r_sign[QB-1];
        f1_zero <= r_zero[QB-1];
        f1_bad  <= r_bad[QB-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[QB-1]);
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[QB-1]);
        end
        f1_sub   <= (be1 < 11'sd1);
        f1_ovf   <= (be1 > 11'sd254);
        f1_field <= be1[7:0];
        f1_sh    <= (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    end

    // ---- F2: denormalise a subnormal result ----
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> f1_sh;
    wire [24:0] lost_mask = (25'd1 << f1_sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= f1_ovf;
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_field;
        end
    end

    // ---- F3: round to nearest even ----
    reg        f3_sign, f3_zero, f3_bad, f3_ovf;
    reg [30:0] f3_code;
    wire [30:0] code_inc;
    ot_hdc_kinc #(.W(31), .K(1)) u_rnd (.a({f2_field, f2_sig[22:0]}), .inc(f2_g && (f2_st || f2_sig[0])), .y(code_inc));
    always @(posedge clk) begin
        f3_sign <= f2_sign; f3_zero <= f2_zero; f3_bad <= f2_bad; f3_ovf <= f2_ovf;
        f3_code <= code_inc;
    end

    // ---- F4: overflow and select ----
    wire ovf = f3_ovf || (f3_code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f3_bad || (ovf && !f3_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f3_zero || f3_code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f3_sign, f3_code}; fault <= 1'b0; end
    end
endmodule
