`timescale 1ns/1ps
`default_nettype none
// HBM-P5-PINS: lock-step check ot_hbm_sm_attn_tile (as built) == ot_hbm_sm_attn_tile_q (tp + 2 x (lx + ln)).
// Random rin / bin / gin every cycle (valid bits included), fixed straps; every output compared every edge.
// +define+OT_TQ_MUT: the reference tile sees a different attn_column strap (negative control: must FAIL).
module tb_sm_attn_tile_q;
    localparam integer RBW = 818, BBW = 2069, NCYC = 4000;
    reg clk = 0, rst_n = 0;
    reg [2*RBW-1:0] rin; reg [BBW-1:0] bin; reg [99:0] gin;
    wire [2*RBW-1:0] rout_a, rout_b; wire [BBW-1:0] bout_a, bout_b; wire [199:0] gout_a, gout_b;
    wire [2:0] col = 3'd5;
`ifdef OT_TQ_MUT
    wire [2:0] col_ref = 3'd4;
`else
    wire [2:0] col_ref = 3'd5;
`endif
    ot_hbm_sm_attn_tile   u_a (.clk(clk), .rst_n(rst_n), .attn_column(col_ref), .attn_rowbase(2'd2), .xs_a1(18'h2a5a5),
        .xs_g1(10'h155), .xs_a2(14'h1a5a), .xs_g2(10'h0aa), .rin(rin), .bin(bin), .rout(rout_a), .bout(bout_a), .gin(gin), .gout(gout_a));
    ot_hbm_sm_attn_tile_q u_b (.clk(clk), .rst_n(rst_n), .attn_column(col), .attn_rowbase(2'd2), .xs_a1(18'h2a5a5),
        .xs_g1(10'h155), .xs_a2(14'h1a5a), .xs_g2(10'h0aa), .rin(rin), .bin(bin), .rout(rout_b), .bout(bout_b), .gin(gin), .gout(gout_b));
    always #1 clk = ~clk;
    integer i, k, mism = 0, gact = 0, cyc = 0;
    task rnd; begin
        for (k = 0; k < 2*RBW; k = k + 32) rin[k +: 32] = $random;
        for (k = 0; k < BBW; k = k + 32) bin[k +: 32] = $random;
        for (k = 0; k < 100; k = k + 32) gin[k +: 32] = $random;
    end endtask
    initial begin
        rin = 0; bin = 0; gin = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        for (i = 0; i < NCYC; i = i + 1) begin
            @(negedge clk); rnd;
            cyc = cyc + 1;
            if (rout_a !== rout_b || bout_a !== bout_b || gout_a !== gout_b) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH cycle %0d gout %h / %h", i, gout_a, gout_b);
            end
            if (gout_a[49] | gout_a[99] | gout_a[149] | gout_a[199]) gact = gact + 1;
        end
        $display("TILE_Q cycles %0d mismatches %0d gather_valid_cycles %0d -> %s", cyc, mism, gact, mism ? "FAIL" : "PASS");
        $finish;
    end
endmodule
`default_nettype wire
