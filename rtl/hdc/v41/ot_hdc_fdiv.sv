`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION, fully pipelined: II 1, fixed DEPTH 31.
//
// WHY A NEW DIVIDER.  The repository's qualified correctly rounded divider,
// rtl/abi3/ot_a3_fp32_div_rne_pipe.sv, is a bisection FSM: one operand in
// flight, an in_ready handshake and ~50 cycles per quotient.  The decode core
// streams one operand per cycle, so it needs the same function as a systolic
// pipe.  This is the digit recurrence that rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv
// uses for the square root, applied to division: one quotient bit per stage,
// a 25-bit compare-and-subtract per stage, no multiplier anywhere.
//
// FUNCTION.  y = RN_even(a / b) in binary32 with gradual underflow, and every
// zero result canonical +0 -- the arithmetic of tools/hdc_golden_v41.div and of
// the qualified add/mul pipes.  Operands may be subnormal.  A nonfinite
// operand, a zero divisor or an overflowing quotient FAILS CLOSED: `fault` on
// that result and y = +0 (the pipes' convention; never an infinity).
//
// EXACTNESS.  Both significands are normalised to [2^23, 2^24).  The recurrence
// forms Q = floor(ma * 2^26 / mb), 26 or 27 significant bits, and the final
// remainder; the remainder is nonzero exactly when the quotient is inexact, so
// {Q, remainder != 0} carries the guard and a true sticky bit.  A subnormal
// result shifts {significand, guard} right with the shifted-out bits ORed into
// the sticky, then rounds once.  So the result is rounded exactly once, from
// the exact quotient.
//
// Stages: 1 decode/normalise, 27 recurrence (quotient bits 2^0 .. 2^-26),
// 3 finish (select and exponent, subnormal shift, round and encode).
// ---------------------------------------------------------------------------
module ot_hdc_fdiv (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer DEPTH = 31;
    localparam integer QB = 27;

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- decode: normalise both significands (priority encoder + shift) ------
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

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_zero <= (a[30:0] == 31'd0);
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // ---- recurrence: stage j forms quotient bit 2^-j -----------------------------
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
            wire [24:0] src_rem = (j == 0) ? {1'b0, d_ma} : {r_rem[j-1][23:0], 1'b0};
            wire [23:0] src_mb  = (j == 0) ? d_mb : r_mb[j-1];
            wire [QB-1:0] src_q = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [25:0] diff = {1'b0, src_rem} - {2'b0, src_mb};
            wire take = !diff[25];
            always @(posedge clk) begin
                r_rem[j]  <= take ? diff[24:0] : src_rem;
                r_q[j]    <= {src_q[QB-2:0], take};
                r_mb[j]   <= src_mb;
                r_sign[j] <= (j == 0) ? d_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? d_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? d_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? d_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[QB-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[QB-1];
        f1_zero <= r_zero[QB-1];
        f1_bad  <= r_bad[QB-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[QB-1]);
            f1_be  <= r_e[QB-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[QB-1]);
            f1_be  <= r_e[QB-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = (25'd1 << sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3: round to nearest even, encode ----------------------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    wire [30:0] code = {f2_field, f2_sig[22:0]} + {30'd0, rup};
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule
