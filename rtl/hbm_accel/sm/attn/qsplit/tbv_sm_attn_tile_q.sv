// HBM-P5-PINS: Verilator lock-step tile == tile_q (C++ clock: tbv_main.cpp). MUT 1 = reference strap differs (must FAIL).
// verilator --cc --exe --build --timescale 1ns/1ps -DOT_SMH_FC_HIER -DOT_SMH_HIER -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0
//   -DOT_SMH_RSTRELAY -GMUT=0|1 --top-module tbv_sm_attn_tile_q tbv_sm_attn_tile_q.sv tbv_main.cpp <SM view file list + qsplit/*.sv>
`default_nettype none
module tbv_sm_attn_tile_q #(parameter integer MUT = 0) (input wire clk);
    localparam integer RBW = 818, BBW = 2069, NCYC = 4000;
    reg rst_n = 0;
    reg [2*RBW-1:0] rin = 0; reg [BBW-1:0] bin = 0; reg [99:0] gin = 0;
    wire [2*RBW-1:0] rout_a, rout_b; wire [BBW-1:0] bout_a, bout_b; wire [199:0] gout_a, gout_b;
    wire [2:0] col = 3'd5;
    wire [2:0] col_ref = MUT ? 3'd4 : 3'd5;
    ot_hbm_sm_attn_tile   u_a (.clk(clk), .rst_n(rst_n), .attn_column(col_ref), .attn_rowbase(2'd2), .xs_a1(18'h2a5a5),
        .xs_g1(10'h155), .xs_a2(14'h1a5a), .xs_g2(10'h0aa), .rin(rin), .bin(bin), .rout(rout_a), .bout(bout_a), .gin(gin), .gout(gout_a));
    ot_hbm_sm_attn_tile_q u_b (.clk(clk), .rst_n(rst_n), .attn_column(col), .attn_rowbase(2'd2), .xs_a1(18'h2a5a5),
        .xs_g1(10'h155), .xs_a2(14'h1a5a), .xs_g2(10'h0aa), .rin(rin), .bin(bin), .rout(rout_b), .bout(bout_b), .gin(gin), .gout(gout_b));
    integer cyc = 0, mism = 0, gact = 0, k;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1;
        for (k = 0; k < 2*RBW; k = k + 32) rin[k +: 32] <= $random;
        for (k = 0; k < BBW; k = k + 32) bin[k +: 32] <= $random;
        for (k = 0; k < 100; k = k + 32) gin[k +: 32] <= $random;
        if (cyc > 4) begin
            if (rout_a != rout_b || bout_a != bout_b || gout_a != gout_b) mism <= mism + 1;
            if (gout_a[49] | gout_a[99] | gout_a[149] | gout_a[199]) gact <= gact + 1;
        end
        if (cyc == NCYC) begin
            $display("TILE_Q MUT %0d cycles %0d mismatches %0d gather_valid_cycles %0d -> %s", MUT, cyc - 5, mism, gact,
                     mism != 0 ? "FAIL" : "PASS");
            $finish;
        end
    end
endmodule
