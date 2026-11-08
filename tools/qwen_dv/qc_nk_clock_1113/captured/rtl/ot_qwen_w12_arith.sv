`timescale 1ns/1ps
// Isolated W12 candidate arithmetic; never replaces shared HDC modules.
module ot_qwen_w12_ksa #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    localparam integer L = $clog2(W + 1);
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_lv
            (* keep *) wire [W:0] g, p;
            if (l == 0) begin : g_init
                assign g = {a & b, cin};
                assign p = {a ^ b, 1'b0};
            end else begin : g_step
                for (i = 0; i <= W; i = i + 1) begin : g_bit
                    if (i >= (1 << (l - 1))) begin : g_op
                        assign g[i] = g_lv[l-1].g[i] | (g_lv[l-1].p[i] & g_lv[l-1].g[i - (1 << (l - 1))]);
                        assign p[i] = g_lv[l-1].p[i] & g_lv[l-1].p[i - (1 << (l - 1))];
                    end else begin : g_pass
                        assign g[i] = g_lv[l-1].g[i];
                        assign p[i] = g_lv[l-1].p[i];
                    end
                end
            end
        end
    endgenerate
    assign s = (a ^ b) ^ g_lv[L].g[W-1:0];
    assign cout = g_lv[L].g[W];
endmodule
module ot_qwen_w12_bmul #(
    parameter integer LAT = 5           // 6: the product is cut after its carry-save rows (1.2 GHz @ SS)
                                        // 7: + a kept input register (each lane its own copy of the shared x
                                        //    operand: the 16-lane fanout leaves the decode cone)
                                        // 8: + the decoded operands registered before the exponent add
                                        //    (margin rule 2026-10-06: tile_tp2_t4 SS -83.8 ps on s3_x -> dec -> s1_e)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    // stage 1: decode; a subnormal significand is normalised by its top bit
    function automatic [17:0] dec;   // {sig[7:0], E[9:0] signed}
        input [7:0] e;
        input [6:0] m;
        integer i;
        reg [2:0] p;
        begin
            if (e != 0) dec = {1'b1, m, e - 10'sd127};
            else begin
                p = 0;
                for (i = 0; i < 7; i = i + 1) if (m[i]) p = i[2:0];
                dec = {({1'b0, m} << (7 - p)), $signed(-10'sd133) + $signed({7'd0, p})};
            end
        end
    endfunction
    // LAT >= 7: kept input register (values and timing of every later stage unchanged, one cycle later)
    wire [31:0] a_i, b_i;
    wire        v_i;
    generate if (LAT >= 7) begin : g_inreg
        (* keep *) reg [31:0] a_r;
        (* keep *) reg [31:0] b_r;
        reg v_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) v_r <= 1'b0; else v_r <= v;
        always @(posedge clk) begin a_r <= a; b_r <= b; end
        assign a_i = a_r; assign b_i = b_r; assign v_i = v_r;
    end else begin : g_noinreg
        assign a_i = a; assign b_i = b; assign v_i = v;
    end endgenerate
    wire [17:0] da0 = dec(a_i[30:23], a_i[22:16]);
    wire [17:0] db0 = dec(b_i[30:23], b_i[22:16]);
    wire        s0_s = a_i[31] ^ b_i[31];
    wire        s0_z = (a_i[30:16] == 15'd0) || (b_i[30:16] == 15'd0);
    wire        s0_nf = (a_i[30:23] == 8'hFF) || (b_i[30:23] == 8'hFF);
    // LAT >= 8: the decoded operands and side bits registered before the exponent add
    wire [17:0] da, db;
    wire        d_s, d_z, d_nf, d_v;
    generate if (LAT >= 8) begin : g_decreg
        reg [17:0] da_r, db_r;
        reg        s_r, z_r, nf_r, v_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) v_r <= 1'b0; else v_r <= v_i;
        always @(posedge clk) begin da_r <= da0; db_r <= db0; s_r <= s0_s; z_r <= s0_z; nf_r <= s0_nf; end
        assign da = da_r; assign db = db_r; assign d_s = s_r; assign d_z = z_r; assign d_nf = nf_r; assign d_v = v_r;
    end else begin : g_nodecreg
        assign da = da0; assign db = db0; assign d_s = s0_s; assign d_z = s0_z; assign d_nf = s0_nf; assign d_v = v_i;
    end endgenerate
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [10:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= d_v;
    end
    always @(posedge clk) begin
        s1_s <= d_s;
        s1_z <= d_z;
        s1_nf <= d_nf;
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_e <= $signed(da[9:0]) + $signed(db[9:0]);
    end
    // stage 2: the 8x8 product, a carry-save tree and a kept prefix adder (a flattened `*` is re-mapped by
    // ABC as a ripple carry chain: -496 ps at 0.833 ns SS); the product is unchanged
    wire [15:0] p8x8;
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [15:0] s2_p;
    reg signed [10:0] s2_e;
    generate if (LAT >= 6) begin : g_cut
        // the 8x8 product's two carry-save rows registered: stage 1b, every side signal delayed with it
        wire [15:0] ps, pc;
        ot_qwen_w12_mul8x8_cs #(.CUT(1)) u_m (.a(s1_a), .b(s1_b), .p(), .rs(ps), .rc(pc));
        reg [15:0] r_s, r_c;
        reg        b_v, b_s, b_z, b_nf;
        reg signed [10:0] b_e;
        always @(posedge clk or negedge rst_n) if (!rst_n) b_v <= 1'b0; else b_v <= s1_v;
        always @(posedge clk) begin r_s <= ps; r_c <= pc; b_s <= s1_s; b_z <= s1_z; b_nf <= s1_nf; b_e <= s1_e; end
        wire c_unused;
        ot_qwen_w12_ksa #(.W(16)) u_a (.a(r_s), .b(r_c), .cin(1'b0), .s(p8x8), .cout(c_unused));
        always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= b_v;
        always @(posedge clk) begin s2_s <= b_s; s2_z <= b_z; s2_nf <= b_nf; s2_e <= b_e; s2_p <= p8x8; end
    end else begin : g_nocut
        ot_qwen_w12_mul8x8_cs u_m (.a(s1_a), .b(s1_b), .p(p8x8), .rs(), .rc());
        always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= s1_v;
        always @(posedge clk) begin s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf; s2_e <= s1_e; s2_p <= p8x8; end
    end endgenerate

    // stage 3: normalise (leading bit 15 or 14) and bias
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf;
        if (s2_p[15]) begin s3_f <= {s2_p[14:0], 8'd0}; s3_be <= s2_e + 11'sd128; end
        else          begin s3_f <= {s2_p[13:0], 9'd0}; s3_be <= s2_e + 11'sd127; end
    end
    // stage 4: encode; a subnormal result shifts right by 1 - biased (<= 7)
    reg        s4_v, s4_bad;
    reg [31:0] s4_y;
    wire [23:0] sig24 = {1'b1, s3_f};
    wire [3:0]  sub_sh = 4'd1 - s3_be[3:0];
    wire [23:0] sub_v = sig24 >> sub_sh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= s3_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (s3_z && !s3_nf) s4_y <= 32'd0;
        else if (s3_nf || s3_be > 11'sd254 || s3_be < -11'sd6) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (s3_be >= 11'sd1) s4_y <= {s3_s, s3_be[7:0], s3_f};
        else s4_y <= {s3_s, 8'd0, sub_v[22:0]};
    end
    // stage 5: output register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
endmodule

// 8 x 8 unsigned product: AND array, 3:2 carry-save levels (8 -> 6 -> 4 -> 3 -> 2 rows), kept Kogge-Stone final add
module ot_qwen_w12_mul8x8_cs #(parameter integer CUT = 0) (
    input  wire [7:0]  a,
    input  wire [7:0]  b,
    output wire [15:0] p,
    output wire [15:0] rs,          // the two carry-save rows (p = rs + rc)
    output wire [15:0] rc
);
    function automatic [31:0] csa;        // {carry, sum} of three 16-bit rows
        input [15:0] r0, r1, r2;
        begin
            csa[15:0] = r0 ^ r1 ^ r2;
            csa[31:16] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [16*8-1:0] l0;
    genvar i;
    generate for (i = 0; i < 8; i = i + 1) begin : g_pp
        assign l0[16*i +: 16] = {8'd0, a & {8{b[i]}}} << i;
    end endgenerate
    (* keep *) wire [16*6-1:0] l1;
    (* keep *) wire [16*4-1:0] l2;
    (* keep *) wire [16*3-1:0] l3;
    (* keep *) wire [16*2-1:0] l4;
    assign l1[0 +: 32]  = csa(l0[0 +: 16], l0[16 +: 16], l0[32 +: 16]);
    assign l1[32 +: 32] = csa(l0[48 +: 16], l0[64 +: 16], l0[80 +: 16]);
    assign l1[64 +: 32] = l0[96 +: 32];
    assign l2[0 +: 32]  = csa(l1[0 +: 16], l1[16 +: 16], l1[32 +: 16]);
    assign l2[32 +: 32] = csa(l1[48 +: 16], l1[64 +: 16], l1[80 +: 16]);
    assign l3[0 +: 32]  = csa(l2[0 +: 16], l2[16 +: 16], l2[32 +: 16]);
    assign l3[32 +: 16] = l2[48 +: 16];
    assign l4 = csa(l3[0 +: 16], l3[16 +: 16], l3[32 +: 16]);
    assign rs = l4[0 +: 16];
    assign rc = l4[16 +: 16];
    // kept prefix levels (as ot_qwen_w12_ksa, local so this file stands alone)
    localparam integer L = 4;
    generate
        for (i = 0; i <= L; i = i + 1) begin : g_lv
            (* keep *) wire [15:0] g, q;
            if (i == 0) begin : g0
                assign g = l4[0 +: 16] & l4[16 +: 16];
                assign q = l4[0 +: 16] ^ l4[16 +: 16];
            end else begin : gi
                genvar j;
                for (j = 0; j < 16; j = j + 1) begin : g_b
                    if (j >= (1 << (i - 1))) begin : g_op
                        assign g[j] = g_lv[i-1].g[j] | (g_lv[i-1].q[j] & g_lv[i-1].g[j - (1 << (i - 1))]);
                        assign q[j] = g_lv[i-1].q[j] & g_lv[i-1].q[j - (1 << (i - 1))];
                    end else begin : g_pass
                        assign g[j] = g_lv[i-1].g[j];
                        assign q[j] = g_lv[i-1].q[j];
                    end
                end
            end
        end
    endgenerate
    assign p = (l4[0 +: 16] ^ l4[16 +: 16]) ^ {g_lv[L].g[14:0], 1'b0};
endmodule
