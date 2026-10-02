// Offline source characterization harness only, engine opt-in remains off.
module ot_rom_secded_clean_checker #(parameter integer K=256,R=9,N=K+R+1)
(input wire[N-1:0] cw, output wire[R-1:0] syn,
 output wire overall, output wire clean);
    function automatic integer pos_of(input integer j);
        integer p, n;
        begin
            p = 3; n = 0; pos_of = 3;
            while (n <= j) begin
                if ((p & (p - 1)) != 0) begin
                    if (n == j) pos_of = p;
                    n = n + 1;
                end
                p = p + 1;
            end
        end
    endfunction
    genvar gi;
    generate
        for (gi = 0; gi < R; gi = gi + 1) begin : g_chk
            wire [K-1:0] t;
            genvar gj;
            for (gj = 0; gj < K; gj = gj + 1) begin : g_bit
                localparam integer PJ = pos_of(gj);
                assign t[gj] = (((PJ >> gi) & 1) != 0) ? cw[gj] : 1'b0;
            end
            assign syn[gi] = cw[K + gi] ^ (^t);
        end
    endgenerate
    assign overall = ^cw;
    wire syn_zero = (syn == {R{1'b0}});
    assign clean = syn_zero & ~overall;
endmodule
