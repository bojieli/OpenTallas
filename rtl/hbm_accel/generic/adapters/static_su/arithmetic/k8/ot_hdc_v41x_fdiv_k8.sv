`timescale 1ns/1ps
// HBM-KIND9 (10-20): ot_hdc_v41x_fdiv (rtl/hdc/v41x/ot_hdc_v41x_sfu.sv) for the KIND1/KIND2 lane leaves, native-32 form.
// Same ports, same DEPTH 19, same edges, bit for bit (tb_k8_units lockstep vs ot_hdc_v41x_fdiv).
// Census (KIND8 it1): the radix-4 recurrence's quotient-digit signs (!d3/!d2/!d1 [27]) each select the whole 27-bit
// remainder (51-53 loads), and the operand normalisation's normal/subnormal select drives 34 bits (35-53 loads).
// Here every recurrence stage is two kept half-stages (ot_hdc_fdiv_rec_k8, keep_hierarchy): each computes its own
// three differences and digit signs and produces half of the next remainder (the low half also the 2 quotient bits),
// so a sign drives one half (<= ~16 mux loads); the normalisation is two kept halves (ot_hdc_fdiv_norm_k8), each with
// its own normal-select and subnormal shift count.  Added area: one more copy of the 3 x 28-bit differences per stage.
module ot_hdc_v41x_fdiv_k8 (
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

    // operand normalisation: {sig[23:0], exponent[9:0]} as two kept halves (sig[23:12] / sig[11:0] + exponent)
    wire [11:0] na_h, nb_h; wire [21:0] na_l, nb_l;
    ot_hdc_fdiv_norm_k8 #(.HI(1)) u_na_h (.e(a[30:23]), .f(a[22:0]), .y(na_h));
    ot_hdc_fdiv_norm_k8 #(.HI(0)) u_na_l (.e(a[30:23]), .f(a[22:0]), .y(na_l));
    ot_hdc_fdiv_norm_k8 #(.HI(1)) u_nb_h (.e(b[30:23]), .f(b[22:0]), .y(nb_h));
    ot_hdc_fdiv_norm_k8 #(.HI(0)) u_nb_l (.e(b[30:23]), .f(b[22:0]), .y(nb_l));
    wire [33:0] na = {na_h, na_l};
    wire [33:0] nb = {nb_h, nb_l};

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

    // 3 mb, once
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= d_sign; e_zero <= d_zero; e_bad <= d_bad; e_e <= d_e;
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
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            wire [12:0] r_lo; wire [11:0] r_hi; wire [1:0] q, q_unused;
            ot_hdc_fdiv_rec_k8 #(.LO(0),  .W(13)) u_lo (.x(x), .mb(mb), .mb3(mb3), .r(r_lo), .q(q));
            ot_hdc_fdiv_rec_k8 #(.LO(13), .W(12)) u_hi (.x(x), .mb(mb), .mb3(mb3), .r(r_hi), .q(q_unused));
            always @(posedge clk) begin
                r_rem[j]  <= {r_hi, r_lo};
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[NS-1];
    // the leading quotient bit q[26] selects the whole finish-1 word (it3: 53 loads): a kept copy family of the same
    // register (D = r_q[NS-2][25], the bit the last one-bit stage shifts into position 26) drives the selects
    wire lead;
    ot_k9_fam #(.W(1), .N(3)) u_lead (.clk(clk), .d(r_q[NS-2][QB-2]), .q(lead));
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_zero <= r_zero[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (lead) begin
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

// one half of a radix-4 recurrence stage: its own differences + digit signs, remainder bits [LO +: W], digit q
(* keep_hierarchy = "yes" *)
module ot_hdc_fdiv_rec_k8 #(parameter integer LO = 0, parameter integer W = 13) (
    input  wire [26:0] x,
    input  wire [23:0] mb,
    input  wire [25:0] mb3,
    output wire [W-1:0] r,
    output wire [1:0]  q
);
    wire [27:0] d1 = {1'b0, x} - {4'b0, mb};
    wire [27:0] d2 = {1'b0, x} - {3'b0, mb, 1'b0};
    wire [27:0] d3 = {1'b0, x} - {2'b0, mb3};
    assign q = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
    wire [26:0] rr = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
    assign r = rr[LO +: W];
endmodule

// one half of the operand normalisation {sig[23:0], exponent[9:0] signed}: HI 1 -> sig[23:12], HI 0 -> {sig[11:0], exp}
(* keep_hierarchy = "yes" *)
module ot_hdc_fdiv_norm_k8 #(parameter integer HI = 0) (
    input  wire [7:0]  e,
    input  wire [22:0] f,
    output wire [(HI ? 12 : 22)-1:0] y
);
    function automatic [33:0] norm;
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
    wire [33:0] n = norm(e, f);
    generate if (HI) begin : g_h
        assign y = n[33:22];
    end else begin : g_l
        assign y = n[21:0];
    end endgenerate
endmodule
