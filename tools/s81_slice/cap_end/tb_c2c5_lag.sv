`timescale 1ns/1ps
// DIE-S81-56/IQKV (11-04): capture lag of the one plan master ot_s81sl_capc5r, dead lanes tied, single clock, against the 10-25
// row-end master ot_s81sl_capc2_w3 (slice_w3, s_3N sukv_raw512 + s_3S slice_iq).  Same random stimulus on lanes 0..2; capc5r's cw
// stream must equal capc2_w3's delayed by one fixed lag, valid bits every edge, address + data on valid lanes.  Per-lag mismatch
// table; PASS iff exactly one lag <= LMAX has 0 cw mismatches and the stream is not empty.
//   -GN=edges -GSEED; -GCMUT=1: capc5r lane 2 tied too (must FAIL: live lane is observable).
module tb_c2c5_lag #(parameter integer N = 200000, parameter integer SEED = 1, parameter integer CMUT = 0, parameter integer LMAX = 40);
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg cfg_v; reg [159:0] cfg_d;
    reg [209:0] lanes;
    wire [279:0] m_w = (CMUT == 1) ? {140'd0, lanes[139:0]} : {70'd0, lanes};
    wire [5:0] sv0, sv1; wire [71:0] sa0, sa1; wire [191:0] sd0, sd1; wire [3:0] nv0, nv1; wire [47:0] na0, na1; wire [127:0] nd0, nd1;
    wire f0, f1;
    ot_s81sl_capc2_w3 u_old (.clk(clk), .rst_n(rst_n), .rt_w(lanes), .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(sv0), .cw_s_a(sa0), .cw_s_d(sd0), .cw_n_v(nv0), .cw_n_a(na0), .cw_n_d(nd0), .fault(f0));
    ot_s81sl_capc5r u_new (.ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
        .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n),
        .rt_w(m_w), .rt_e(280'd0), .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(sv1), .cw_s_a(sa1), .cw_s_d(sd1), .cw_n_v(nv1), .cw_n_a(na1), .cw_n_d(nd1), .fault(f1));
    localparam integer WW = 6 + 72 + 192 + 4 + 48 + 128 + 1;
    reg [WW-1:0] hist [0:LMAX];
    integer mism [0:LMAX];
    integer fmis [0:LMAX];
    integer seed, cyc, l, rv, i, j, outs, fe, best, nbest, fbest, cnt;
    wire [WW-1:0] cur_old = {f0, nd0, na0, nv0, sd0, sa0, sv0};
    function automatic integer differs(input [WW-1:0] a, input [5:0] v1s, input [3:0] v1n, input [71:0] a1s, input [191:0] d1s, input [47:0] a1n, input [127:0] d1n);
        reg [5:0] v0s; reg [71:0] a0s; reg [191:0] d0s; reg [3:0] v0n; reg [47:0] a0n; reg [127:0] d0n; integer k;
        begin
            {v0s} = a[5:0]; a0s = a[77:6]; d0s = a[269:78]; v0n = a[273:270]; a0n = a[321:274]; d0n = a[449:322];
            differs = 0;
            if (v0s !== v1s || v0n !== v1n) differs = 1;
            for (k = 0; k < 6; k = k + 1) if (v1s[k] === 1'b1 && (a0s[12*k +: 12] !== a1s[12*k +: 12] || d0s[32*k +: 32] !== d1s[32*k +: 32])) differs = 1;
            for (k = 0; k < 4; k = k + 1) if (v1n[k] === 1'b1 && (a0n[12*k +: 12] !== a1n[12*k +: 12] || d0n[32*k +: 32] !== d1n[32*k +: 32])) differs = 1;
        end
    endfunction
    function [31:0] tag(input integer r);
        reg [2:0] pos; reg [15:0] row; reg [4:0] lo, n; reg [2:0] k;
        begin
            pos = r[1:0]; row = {14'd0, r[3:2]}; k = r[6:4] % 5; n = 5'd1 + r[11:7] % 31;
            lo = r[16:12] & ~((5'd1 << k) - 5'd1);
            tag = {pos, row, lo, k, n};
        end
    endfunction
    task drive;
        begin
            for (l = 0; l < 3; l = l + 1) begin
                rv = $random(seed);
                lanes[70 * l + 0] = 1'b1;
                lanes[70 * l + 1] = rv[0] & rv[1] & rv[2];
                lanes[70 * l + 2] = rv[3];
                lanes[70 * l + 3 +: 32] = tag($random(seed));
                lanes[70 * l + 35 +: 32] = $random(seed);
                lanes[70 * l + 67] = 1'b0;
                lanes[70 * l + 68] = rv[4];
                lanes[70 * l + 69] = 1'b0;
            end
        end
    endtask
    initial begin
        seed = SEED; outs = 0; fe = 0; lanes = 0; cfg_v = 0; cfg_d = 0;
        for (i = 0; i <= LMAX; i = i + 1) begin mism[i] = 0; fmis[i] = 0; hist[i] = 0; end
        repeat (80) @(negedge clk);
        rst_n = 1;
        repeat (40) @(negedge clk);
        cfg_d = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
        cfg_d[28:27] = 2'd1; cfg_d[26:24] = 3'd3; cfg_d[44:29] = 16'd0; cfg_d[55:45] = 11'd4;
        cfg_v = 1; @(negedge clk); cfg_v = 0;
        repeat (60) @(negedge clk);
        for (cyc = 0; cyc < N; cyc = cyc + 1) begin
            @(negedge clk); #0.1;
            for (j = LMAX; j > 0; j = j - 1) hist[j] = hist[j-1];
            hist[0] = cur_old;
            if (cyc > LMAX + 2) begin
                for (j = 0; j <= LMAX; j = j + 1) begin
                    if (differs(hist[j], sv1, nv1, sa1, sd1, na1, nd1) != 0) mism[j] = mism[j] + 1;
                    if (hist[j][WW-1] !== f1) fmis[j] = fmis[j] + 1;
                end
            end
            if (|sv1 || |nv1) outs = outs + 1;
            if (f1 === 1'b1) fe = fe + 1;
            drive;
        end
        best = -1; nbest = 0; fbest = -1;
        for (j = 0; j <= LMAX; j = j + 1) begin
            if (mism[j] == 0) begin best = j; nbest = nbest + 1; end
            if (fmis[j] == 0 && fbest < 0) fbest = j;
            if (j < 20) $display("LAG %0d cw_mism %0d fault_mism %0d", j, mism[j], fmis[j]);
        end
        $display("C2C5_LAG SEED=%0d CMUT=%0d %s edges %0d lag %0d zero_lags %0d cw_valid_edges %0d fault_edges %0d", SEED, CMUT,
            (nbest == 1 && outs > 0) ? "PASS" : "FAIL", N, best, nbest, outs, fe);
        $finish;
    end
endmodule
