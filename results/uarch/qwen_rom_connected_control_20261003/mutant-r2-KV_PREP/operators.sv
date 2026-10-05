module ot_qwen_w12_kadd #(parameter integer W = 24) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] s
);
    wire c;
    ot_qwen_w12_ksa #(.W(W)) u (.a(a), .b(b), .cin(1'b0), .s(s), .cout(c));
endmodule

// N rows of W bits reduced carry-save (3:2 per level) to two, kept-level boundaries
module ot_qwen_w12_csa_tree #(parameter integer W = 24, parameter integer N = 8) (
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
            (* keep *) wire [((NL > 0) ? NL : 1)*W-1:0] r;
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

// the sum (mod 2^W) of N rows: carry-save tree, then a kept prefix add
module ot_qwen_w12_ksum #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s
);
    wire [W-1:0] a, b;
    ot_qwen_w12_csa_tree #(.W(W), .N(N)) u_t (.rows(rows), .s(a), .c(b));
    ot_qwen_w12_kadd #(.W(W)) u_a (.a(a), .b(b), .s(s));
endmodule
