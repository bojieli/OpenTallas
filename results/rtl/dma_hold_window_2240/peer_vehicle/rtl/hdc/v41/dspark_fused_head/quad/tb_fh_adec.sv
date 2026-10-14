`timescale 1ns/1ps
// Equivalence of ot_hdc_v41_fh_adec with the original subtract-then-compare decode: 3 bases x 4 lanes, every
// boundary (BASE-1..BASE+1, LIM-1..LIM+1, 0, 2^AW-1, each low-bit phase) + 200,000 random addresses per instance.
module tb_fh_adec;
    localparam integer AW = 24, LG = 2, ROWS = 505, NB = 3;
    localparam [3*AW-1:0] BASES = {24'd123457, 24'd4096, 24'd0};
    reg [AW-1:0] a; reg en; integer bad = 0, n = 0, i, k;
    wire [NB*4-1:0] ok; wire [NB*4*9-1:0] row;
    genvar b, g;
    for (b = 0; b < NB; b = b + 1) begin : g_b
        for (g = 0; g < 4; g = g + 1) begin : g_g
            ot_hdc_v41_fh_adec #(.AW(AW), .LG(LG), .ROWS(ROWS), .GA(g), .BASE(BASES[b*AW+:AW])) u (
                .en(en), .a(a), .ok(ok[b*4+g]), .row(row[(b*4+g)*9+:9]));
        end
    end
    task check;
        integer bb, gg; reg [AW-1:0] base, d; reg ok0; reg [8:0] row0;
        begin
            #1;
            for (bb = 0; bb < NB; bb = bb + 1) for (gg = 0; gg < 4; gg = gg + 1) begin
                base = BASES[bb*AW+:AW]; d = a - base;
                ok0 = en && a >= base && d[LG-1:0] == gg && (d >> LG) < ROWS; row0 = 9'(d >> LG);
                n = n + 1;
                if (ok0 !== ok[bb*4+gg] || row0 !== row[(bb*4+gg)*9+:9]) begin
                    bad = bad + 1;
                    if (bad < 5) $display("MISMATCH base=%0d ga=%0d a=%0d ok %b/%b row %0d/%0d", base, gg, a, ok0, ok[bb*4+gg], row0, row[(bb*4+gg)*9+:9]);
                end
            end
        end
    endtask
    initial begin
        en = 1;
        for (k = 0; k < NB; k = k + 1)
            for (i = -4; i <= 4; i = i + 1) begin
                a = BASES[k*AW+:AW] + i; check;
                a = BASES[k*AW+:AW] + (ROWS << LG) + i; check;
            end
        a = 0; check; a = {AW{1'b1}}; check;
        for (i = 0; i < 200000; i = i + 1) begin
            a = (i % 3 == 0) ? $urandom : (BASES[(i % NB)*AW+:AW] + ($urandom % (ROWS * 8))); en = (i % 7) != 0; check;
        end
        if (bad == 0) $display("PASS adec equivalence checks=%0d", n);
        else $fatal(1, "adec equivalence FAILED %0d/%0d", bad, n);
        $finish;
    end
endmodule
