`timescale 1ns/1ps
// Candidate-only exact combinational copies. Allow optimizer to remove unused transport.
// All original equations, widths, carry order and state edges are retained.
module ot_qce_banked_v1_prunable_ksa #(parameter integer W = 8) (
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
            wire [W:0] g, p;
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

module ot_qce_banked_v1_prunable_kadd #(parameter integer W = 24) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] s
);
    wire c;
    ot_qce_banked_v1_prunable_ksa #(.W(W)) u (.a(a), .b(b), .cin(1'b0), .s(s), .cout(c));
endmodule

module ot_qce_banked_v1_prunable_csa_tree #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s,
    output wire [W-1:0]   c
);
    function automatic integer nxt(input integer n);
        nxt = (n <= 2) ? n : 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer cnt(input integer l);
        integer i, n;
        begin n = N; for (i = 0; i < l; i = i + 1) n = nxt(n); cnt = n; end
    endfunction
    function automatic integer depth(input integer d);
        integer n, l;
        begin n = N; l = 0; while (n > 2) begin n = nxt(n); l = l + 1; end depth = l; end
    endfunction
    localparam integer L = depth(0);
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_l
            localparam integer NL = cnt(l);
            wire [((NL > 0) ? NL : 1)*W-1:0] r;
            if (l == 0) begin : g0
                assign r = rows;
            end else begin : gn
                localparam integer NP = cnt(l - 1);
                for (i = 0; i < NP / 3; i = i + 1) begin : g_c
                    wire [W-1:0] x = g_l[l-1].r[(3*i)*W +: W], y = g_l[l-1].r[(3*i+1)*W +: W],
                                 z = g_l[l-1].r[(3*i+2)*W +: W];
                    assign r[(2*i)*W +: W] = x ^ y ^ z;
                    assign r[(2*i+1)*W +: W] = ((x & y) | (x & z) | (y & z)) << 1;
                end
                for (i = 0; i < NP % 3; i = i + 1) begin : g_p
                    assign r[(2*(NP/3)+i)*W +: W] = g_l[l-1].r[(3*(NP/3)+i)*W +: W];
                end
            end
        end
    endgenerate
    assign s = g_l[L].r[0 +: W];
    assign c = (cnt(L) > 1) ? g_l[L].r[W +: W] : {W{1'b0}};
endmodule

module ot_qce_banked_v1_prunable_ksum #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s
);
    wire [W-1:0] a, b;
    ot_qce_banked_v1_prunable_csa_tree #(.W(W), .N(N)) u_t (.rows(rows), .s(a), .c(b));
    ot_qce_banked_v1_prunable_kadd #(.W(W)) u_a (.a(a), .b(b), .s(s));
endmodule
