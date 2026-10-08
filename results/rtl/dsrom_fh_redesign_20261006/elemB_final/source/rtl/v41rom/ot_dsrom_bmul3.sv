`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_bmul3: ot_v41_bmul2 (pinned, unchanged) with its stage-2 8x4 partial products cut once more, for the DS-ROM
// head element (ot_dsrom_head_elem, recovery lever "head").  Routed in that element (r2) the 8x4 product was the SS
// endpoint (g_m[1].u_m.s1_b -> s2_lo, -23.1 ps at 0.833 ns, 60 ps uncertainty).  Stage 2a forms four 8x2 partial
// products, stage 2b sums them pairwise into bmul2's two 8x4 products; everything else is bmul2's.
// Bit-identical to ot_v41_bmul2 (y and fault), LATENCY 6 (bmul2: 5), same ports.
// ---------------------------------------------------------------------------
module ot_dsrom_bmul3 (
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
    wire [17:0] da = dec(a[30:23], a[22:16]);
    wire [17:0] db = dec(b[30:23], b[22:16]);
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [10:0] s1_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= v;
    end
    always @(posedge clk) begin
        s1_s <= a[31] ^ b[31];
        s1_z <= (a[30:16] == 15'd0) || (b[30:16] == 15'd0);
        s1_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_e <= $signed(da[9:0]) + $signed(db[9:0]);
    end
    // stage 2a: four 8x2 partial products
    reg        s2a_v, s2a_s, s2a_z, s2a_nf;
    reg [9:0]  s2a_p [0:3];
    reg signed [10:0] s2a_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2a_v <= 1'b0;
        else s2a_v <= s1_v;
    end
    always @(posedge clk) begin
        s2a_s <= s1_s; s2a_z <= s1_z; s2a_nf <= s1_nf; s2a_e <= s1_e;
        s2a_p[0] <= s1_a * s1_b[1:0]; s2a_p[1] <= s1_a * s1_b[3:2];
        s2a_p[2] <= s1_a * s1_b[5:4]; s2a_p[3] <= s1_a * s1_b[7:6];
    end
    // stage 2b: bmul2's two 8x4 partial products (a*b[3:0] = p0 + 4 p1, a*b[7:4] = p2 + 4 p3; <= 4080, 12 bits)
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [11:0] s2_lo, s2_hi;
    reg signed [10:0] s2_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s2a_v;
    end
    always @(posedge clk) begin
        s2_s <= s2a_s; s2_z <= s2a_z; s2_nf <= s2a_nf; s2_e <= s2a_e;
        s2_lo <= {2'd0, s2a_p[0]} + {s2a_p[1], 2'd0}; s2_hi <= {2'd0, s2a_p[2]} + {s2a_p[3], 2'd0};
    end
    // stage 3 first adds the partial products: a*b = a*b[7:4]*16 + a*b[3:0]; the high 12 bits are a 12-bit
    // keep-prefix add (<= 255*15 + 239 = 4064, no carry out).
    wire [11:0] hi_sum;
    wire        hi_co;
    ot_v41_ksadd #(.W(12)) u_ph (.a(s2_hi), .b({4'd0, s2_lo[11:4]}), .cin(1'b0), .s(hi_sum), .cout(hi_co));
    wire [15:0] pq = {hi_sum, s2_lo[3:0]};
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
        if (pq[15]) begin s3_f <= {pq[14:0], 8'd0}; s3_be <= s2_e + 11'sd128; end
        else          begin s3_f <= {pq[13:0], 9'd0}; s3_be <= s2_e + 11'sd127; end
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

