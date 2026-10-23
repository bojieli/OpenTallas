`timescale 1ns/1ps
// STW-S81c-TOK4-BAND 10-22: lockstep of the split X band (dsdv_idx_rg3_bx = bxn + bxm{bxmh 0, bxmh 1}) against the flat X
// of 2e189d817 (dsdv_idx_rg3_bx_ref) on random response lanes / S stages, every edge, xr_o and kq_o.  MUTN != 0 mutates
// the split copy only (the run must then report mismatches).  Prints BX_LSW PASS / FAIL.
module tb_dsdv_idx_rg3_bx_lsw;
    parameter integer MUTN = 0;
    parameter integer N = 20000;
    reg ck = 0, rst = 0;
    always #1 ck = ~ck;
    reg [1087:0] rri; reg [17:0] sx;
    wire [67:0] xr_a, xr_b; wire [543:0] kq_a, kq_b;
    dsdv_idx_rg3_bx     #(.MUT(MUTN), .SRAM_MACRO(1), .RH(1)) u_b (.ck(ck), .rst(rst), .rri(rri), .sx_i(sx), .xr_o(xr_b), .kq_o(kq_b));
    dsdv_idx_rg3_bx_ref #(.MUT(0),    .SRAM_MACRO(1), .RH(1)) u_a (.ck(ck), .rst(rst), .rri(rri), .sx_i(sx), .xr_o(xr_a), .kq_o(kq_a));
    integer i, k, bad = 0, live = 0, wr = 0, seed = 1;
    initial begin
        rri = 0; sx = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge ck);
            if (i == 3) rst = 1;
            if (i == N / 2) rst = 0;                    // a mid-run reset pulse
            if (i == N / 2 + 4) rst = 1;
            for (k = 0; k < 34; k = k + 1) rri[32 * k +: 32] = $random(seed);
            // bias the lane valid / pop bits and the S valid up so the landing SRAMs get written and read often
            for (k = 0; k < 4; k = k + 1) begin rri[272 * k] = ($random(seed) & 3) != 0; rri[272 * k + 1] = $random(seed); end
            sx = $random(seed);
            sx[16:13] = {4{($random(seed) & 1)}};
            @(posedge ck); #0.1;
            if (rst && i > 40) begin
                if (xr_a !== xr_b || kq_a !== kq_b) begin
                    bad = bad + 1;
                    if (bad <= 4) $display("BX_LSW MISMATCH cycle %0d xr_eq %0d kq_eq %0d", i, xr_a === xr_b, kq_a === kq_b);
                end
                if (|kq_a[511:0]) live = live + 1;
                if (|u_a.lw_v) wr = wr + 1;
            end
        end
        $display("BX_LSW MUTN=%0d cycles %0d live_key %0d writes %0d mismatches %0d", MUTN, N, live, wr, bad);
        if (MUTN == 0) begin
            if (bad == 0 && live > 100 && wr > 100) $display("BX_LSW PASS"); else $display("BX_LSW FAIL");
        end else begin
            if (bad > 0) $display("BX_LSW MUTANT_CAUGHT"); else $display("BX_LSW FAIL mutant not caught");
        end
        $finish;
    end
endmodule
