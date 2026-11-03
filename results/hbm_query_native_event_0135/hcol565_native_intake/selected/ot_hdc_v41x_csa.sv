module ot_hdc_v41x_csa #(
    parameter integer N = 32,
    parameter integer M = 2,
    parameter integer W = 14
) (
    input  wire [N*W-1:0] d,
    output wire [M*W-1:0] q
);
    function automatic integer nxt(input integer n);
        nxt = 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer nlev(input integer n, input integer m);
        integer c, k;
        begin
            nlev = 0; c = n;
            for (k = 0; k < 64; k = k + 1)
                if (c > m) begin c = nxt(c); nlev = nlev + 1; end
        end
    endfunction
    function automatic integer cnt(input integer n, input integer l);
        integer k;
        begin
            cnt = n;
            for (k = 0; k < l; k = k + 1) cnt = nxt(cnt);
        end
    endfunction
    function automatic integer off(input integer n, input integer l);
        integer k, c;
        begin
            off = 0; c = n;
            for (k = 0; k < l; k = k + 1) begin off = off + c; c = nxt(c); end
        end
    endfunction
    localparam integer L = nlev(N, M);
    localparam integer NF = cnt(N, L);
    localparam integer OL = off(N, L);
    localparam integer TOT = OL + NF;
    wire [W-1:0] op [0:TOT-1] /*verilator split_var*/;
    genvar i, l;
    generate
        for (i = 0; i < N; i = i + 1) begin : g_in
            assign op[i] = d[W*i +: W];
        end
        for (l = 0; l < L; l = l + 1) begin : g_lvl
            localparam integer NI = cnt(N, l);
            localparam integer OI = off(N, l);
            localparam integer OO = off(N, l + 1);
            localparam integer G3 = NI / 3;
            for (i = 0; i < G3; i = i + 1) begin : g_fa
                wire [W-1:0] a = op[OI + 3*i];
                wire [W-1:0] b = op[OI + 3*i + 1];
                wire [W-1:0] c = op[OI + 3*i + 2];
                wire [W-1:0] mj = (a & b) | (a & c) | (b & c);
                assign op[OO + 2*i] = a ^ b ^ c;
                assign op[OO + 2*i + 1] = {mj[W-2:0], 1'b0};
            end
            for (i = 0; i < NI % 3; i = i + 1) begin : g_pass
                assign op[OO + 2*G3 + i] = op[OI + 3*G3 + i];
            end
        end
        for (i = 0; i < M; i = i + 1) begin : g_out
            if (i < NF) begin : g_op
                assign q[W*i +: W] = op[OL + i];
            end else begin : g_zero
                assign q[W*i +: W] = {W{1'b0}};
            end
        end
    endgenerate
endmodule
