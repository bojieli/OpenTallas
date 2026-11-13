`timescale 1ps/1fs
// tb_s81_col_rlat (S81-SERDES-RST-TREE / form vB, DIE-S81-85 2026-11-09): fixed beat latency of ot_pdie_serdes_col in PMA
// loopback (pma_rx = pma_tx, pma_rck = pma_tck = clk, so rck and clk cycles are the same unit), LOCKSAFE=1, HOLD_EDGES=64.
// Every clk a tagged beat (tag = clk count in bits 63:32) except one IDLE per 256; latency = clk count at rx - tag.
// Build once per define set; the min / max latency difference between two builds is that form's added cycles (the TX
// side of every form in the vB set is unchanged, so a loopback delta is an RX delta).  OT_S81_SERDES_TXL4 adds 2 TX clk.
// EXPECT_LAT != 0: PASS needs lat_min == lat_max == EXPECT_LAT (TXL mutant MUT=8 removes one u_txl row: must FAIL).
// RST_EDGES (default 8 = the bench as it was): clk edges the die reset is held at power-up.  Forms whose unreset row
// registers need more than 8 edges to flush (LANE_RXO 6 behind the staged rate matcher: 12) are run with 64, the owner
// boot rule (rst_n >= 64 clk).
module tb_s81_col_rlat #(parameter integer MUT = 0, parameter integer EXPECT_LAT = 0, parameter integer RST_EDGES = 8);
    reg clk = 0, rst = 0;
    always #416.5 clk = ~clk;
    reg [511:0] tx = 512'd2; wire [511:0] rx; wire [1:0] st; wire [543:0] pt; wire tc;
    ot_pdie_serdes_col #(.LOCKSAFE(1), .HOLD_EDGES(64), .MUT(MUT)) u_c (.clk(clk), .rst(rst), .tx(tx), .rx(rx), .st(st), .pma_tx(pt),
        .pma_tck(tc), .pma_rx(pt), .pma_rck(tc), .pma_lock(1'b1));
    integer cyc = 0, n = 0, lmin = 1 << 30, lmax = -1, bad = 0, lat;
    always @(negedge clk) begin
        cyc = cyc + 1;
        tx <= (cyc % 256 == 0) ? 512'd2 : {384'h0, 32'h5A5A0000 ^ cyc, 32'(cyc), 30'h0, 2'b00};
    end
    always @(posedge clk) begin #1;
        if (rst && !(rx[1] && !rx[0])) begin
            lat = cyc - rx[63:32];
            if (rx[95:64] !== (32'h5A5A0000 ^ rx[63:32])) bad = bad + 1;
            n = n + 1; if (lat < lmin) lmin = lat; if (lat > lmax) lmax = lat;
        end
    end
    initial begin
        repeat (RST_EDGES) @(posedge clk); #100 rst = 1;
        repeat (6000) @(posedge clk);
        $display("TB_S81_COL_RLAT beats=%0d bad=%0d lat_min=%0d lat_max=%0d st=%b", n, bad, lmin, lmax, st);
        if (n > 4000 && bad == 0 && st == 2'b10 && (EXPECT_LAT == 0 || (lmin == EXPECT_LAT && lmax == EXPECT_LAT))) $display("TB_S81_COL_RLAT PASS"); else $display("TB_S81_COL_RLAT FAIL");
        $finish;
    end
endmodule
