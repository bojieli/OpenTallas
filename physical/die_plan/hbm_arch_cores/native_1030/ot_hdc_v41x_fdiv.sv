
// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION: II 1, fixed DEPTH 19.
//
// The function, the operand decode, the finish and the fault convention are
// those of rtl/hdc/v41/ot_hdc_fdiv.sv, transcribed unchanged:
//   y = RN_even(a / b), gradual underflow, every zero result +0; a nonfinite
//   operand, a zero divisor or an overflowing quotient fails closed
//   (fault, y = +0).
// What changes is the recurrence.  It forms the same 27 quotient bits and the
// same final remainder, but TWO bits per register stage.  A stage takes x = 4R
// (2 ma in the first stage), with R < mb the running remainder, so x < 4 mb.
// It forms x - mb, x - 2 mb and x - 3 mb in parallel, and the digit
// q = floor(x / mb) in [0, 3] is the largest with a non-negative difference.
// That is one subtract and a select, not two subtracts in series: the routed
// SFU lane measured two serial restoring steps at 907 MHz.  3 mb is formed
// once, in a stage after the decode.  The last stage forms one bit.  A
// correctly rounded quotient is unique, so the result is the same bit for bit.
// Stages: 1 decode, 1 (3 mb), 14 recurrence, 3 finish.
// ---------------------------------------------------------------------------
// ZERO_RST (HBM-CORES-REBAL-6 10-28; default 0 = the qualified form, unchanged): the 18-stage zero-flag pipeline
// (d_zero .. f2_zero) gets an asynchronous reset to 0.  With a constant nonzero dividend (side_rest / side u_div,
// a = 1.0) that flag is constant 0 through 18 unreset stages; synthesis removes it (legal), and LEC can give an
// unreset constant a base case only inside its reset window (4 + 8 edges), so y/fault became NOT EQUIVALENT.
// Reset to its constant value, the flag is constant from the reset state: safe by construction, 18 reset flops.
module ot_hdc_v41x_fdiv #(
    parameter integer ZERO_RST = 0
) (
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
    localparam integer NS = (QB + 1) / 2;      // 14
    localparam integer DEPTH = 2 + NS + 3;     // 19

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

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // 3 mb, once
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= d_sign; e_bad <= d_bad; e_e <= d_e;
        e_ma <= d_ma; e_mb <= d_mb; e_mb3 <= {2'b0, d_mb} + {1'b0, d_mb, 1'b0};
    end

    reg [24:0]        r_rem  [0:NS-1];
    reg [QB-1:0]      r_q    [0:NS-1];
    reg [23:0]        r_mb   [0:NS-1];
    reg [25:0]        r_mb3  [0:NS-1];
    reg               r_sign [0:NS-1];
    reg               r_zero [0:NS-1];
    reg               r_bad  [0:NS-1];
    reg signed [10:0] r_e    [0:NS-1];

    genvar j;
    generate
        for (j = 0; j < NS; j = j + 1) begin : g_rec
            // quotient bits 2j and 2j+1 (bit 2^-k is restoring step k); stage NS-1 forms one bit
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            wire [27:0]   d1 = {1'b0, x} - {4'b0, mb};
            wire [27:0]   d2 = {1'b0, x} - {3'b0, mb, 1'b0};
            wire [27:0]   d3 = {1'b0, x} - {2'b0, mb3};
            wire [1:0]    q  = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
            wire [26:0]   r  = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
            always @(posedge clk) begin
                r_rem[j]  <= r[24:0];
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
            if (ZERO_RST != 0) begin : g_zr
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) r_zero[j] <= 1'b0; else r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
            end else begin : g_z
                always @(posedge clk) r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
            end
        end
        if (ZERO_RST != 0) begin : g_zr
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin d_zero <= 1'b0; e_zero <= 1'b0; f1_zero <= 1'b0; f2_zero <= 1'b0; end
                else begin d_zero <= (a[30:0] == 31'd0); e_zero <= d_zero; f1_zero <= r_zero[NS-1]; f2_zero <= f1_zero; end
        end else begin : g_z
            always @(posedge clk) begin
                d_zero <= (a[30:0] == 31'd0); e_zero <= d_zero; f1_zero <= r_zero[NS-1]; f2_zero <= f1_zero;
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[NS-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd126;
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
