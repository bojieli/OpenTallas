`timescale 1ns/1ps
// Lockstep bench of ot_dsrom_su_norm MEM=1 (x wait line + gain ROM on shared-address SRAM macros) against MEM=0 (the
// per-lane flop arrays), at the HBM norm view's library selection (N64 D5120 HC1 QUANT1 LM5 LA6 RXS1 SXC1 FREG1 RW9 BW9).
// R rows back to back: row 0 is the DS1M golden row (also checked against ey / eq*), row k > 0 is the golden x rotated
// by 37k elements; row k+1's go is issued the cycle row k's rstd appears, so row k+1's x is written while row k's
// scale pass still reads (overlap).  The gain ROM is reloaded (rotated by 11) after row R-2's last output, then row R-1.
// Every cycle: valids, indices, r and fault must match; y / ro / q data must match whenever valid.
// Prints LOCKSTEP rows=.. y_vecs=.. mism=.. gold_y_err=.. gold_q_err=.. then PASS or FAIL (line start).
module tb_su_norm_mem_lockstep #(parameter integer R = 4, parameter integer HUB_IN = 33);
    localparam integer N = 64, D = 5120, NV = D / N, NX = 4 * D, NB = D / 32;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] xm [0:NX-1]; reg [31:0] wm [0:D-1]; reg [31:0] cfg [0:5]; reg [31:0] ey [0:D-1];
    reg [255:0] eqc [0:NB-1]; reg [15:0] eqe [0:NB-1]; reg [511:0] eqy [0:NB-1];
    initial begin
        $readmemh("x.mem", xm); $readmemh("w.mem", wm); $readmemh("cfg.mem", cfg); $readmemh("ey.mem", ey);
        $readmemh("eqc.mem", eqc); $readmemh("eqe.mem", eqe); $readmemh("eqy.mem", eqy);
    end
    reg rst_n = 1'b0, go = 1'b0, in_v = 1'b0, wl_v = 1'b0;
    reg [7:0] wl_i = 0;
    reg [N*32-1:0] wl_d = 0;
    reg [4*N*32-1:0] in_x = 0;
    wire [1:0] y_v, r_v, q_v, ro_v, fault;
    wire [7:0] y_i [0:1]; wire [7:0] q_i [0:1];
    wire [N*32-1:0] y [0:1]; wire [N*32-1:0] ro [0:1]; wire [31:0] r [0:1];
    wire [2*256-1:0] qc [0:1]; wire [2*10-1:0] qe [0:1]; wire [2*512-1:0] qy [0:1];
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_dut
        ot_dsrom_su_norm #(.N(N), .D(D), .HC(1), .RD(0), .QUANT(1), .RW(9), .BW(9), .LM(5), .LA(6), .RXS(1), .SXC(1),
                           .FREG(1), .MEM(g)) dut (
            .clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre({cfg[3], cfg[2], cfg[1], cfg[0]}),
            .n_f(cfg[4]), .eps(cfg[5]), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(32'd0), .sin_t(32'd0),
            .y_v(y_v[g]), .y_i(y_i[g]), .y(y[g]), .r_v(r_v[g]), .r(r[g]), .q_v(q_v[g]), .q_i(q_i[g]), .q_codes(qc[g]),
            .q_e(qe[g]), .q_y(qy[g]), .ro_v(ro_v[g]), .ro(ro[g]), .fault(fault[g]));
    end endgenerate
    reg [HUB_IN:0] hv; reg [7:0] hi [0:HUB_IN]; reg [7:0] hr [0:HUB_IN];
    integer cyc = 0, row = -1, iss = NV, mism = 0, gy = 0, gq = 0, ny = 0, nq = 0, nrv = 0, last_act = 0, j, k, e;
    integer ydone = 0, wl_at = -1, wl_n = 0, wl_rot = 0, yrow = 0, qrow = 0;
    reg [7:0] vi, vr;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        wl_v <= 1'b0;
        if (cyc == 5) begin wl_at = 5; wl_n = 0; wl_rot = 0; end
        if (wl_at >= 0 && wl_n < NV) begin
            wl_v <= 1'b1; wl_i <= wl_n;
            for (j = 0; j < N; j = j + 1) wl_d[j * 32 +: 32] <= wm[(wl_n * N + j + wl_rot) % D];
            wl_n = wl_n + 1;
        end
        // rows: row 0 at cycle 10 + NV; row k+1 when row k's rstd appears (reference DUT); gain reload before row R-1
        go <= 1'b0;
        if ((row < 0 && cyc == 10 + NV) || (row >= 0 && row < R - 1 && r_v[0] && !(row == R - 2))) begin
            go <= 1'b1; row = row + 1; iss = 0;
        end
        if (y_v[0] && y_i[0] == NV - 1) ydone = ydone + 1;
        if (row == R - 2 && ydone == R - 1 && wl_at == 5) begin wl_at = cyc; wl_n = 0; wl_rot = 11; end
        if (row == R - 2 && wl_at > 5 && wl_n == NV && !wl_v) begin go <= 1'b1; row = row + 1; iss = 0; end
        hv[0] <= (go && iss < NV) || (iss > 0 && iss < NV);
        hi[0] <= iss; hr[0] <= row;
        if ((go && iss < NV) || (iss > 0 && iss < NV)) iss = iss + 1;
        for (k = 1; k <= HUB_IN; k = k + 1) begin hv[k] <= hv[k - 1]; hi[k] <= hi[k - 1]; hr[k] <= hr[k - 1]; end
        in_v <= hv[HUB_IN - 1];
        vi = hi[HUB_IN - 1]; vr = hr[HUB_IN - 1];
        for (k = 0; k < 4; k = k + 1)
            for (j = 0; j < N; j = j + 1)
                in_x[(k * N + j) * 32 +: 32] <= xm[k * D + (vi * N + j + 37 * vr) % D];
        // lockstep compare
        if (rst_n) begin
            if (y_v[0] !== y_v[1] || r_v[0] !== r_v[1] || q_v[0] !== q_v[1] || ro_v[0] !== ro_v[1] || fault[0] !== fault[1]
                || (y_v[0] && (y_i[0] !== y_i[1] || y[0] !== y[1])) || (r_v[0] && r[0] !== r[1])
                || (q_v[0] && (q_i[0] !== q_i[1] || qc[0] !== qc[1] || qe[0] !== qe[1] || qy[0] !== qy[1]))
                || (ro_v[0] && ro[0] !== ro[1])) begin
                if (mism < 5) $display("MISMATCH cyc %0d y_v %b%b y_i %0d/%0d q_v %b%b fault %b%b", cyc, y_v[0], y_v[1],
                                       y_i[0], y_i[1], q_v[0], q_v[1], fault[0], fault[1]);
                mism = mism + 1;
            end
        end
        if (r_v[0]) nrv = nrv + 1;
        if (y_v[0] || y_v[1] || q_v[0] || in_v || go) last_act = cyc;
        if (y_v[1]) begin
            ny = ny + 1;
            if (yrow == 0)
                for (j = 0; j < N; j = j + 1) if (y[1][j * 32 +: 32] !== ey[y_i[1] * N + j]) gy = gy + 1;
            if (y_i[1] == NV - 1) yrow = yrow + 1;
        end
        if (q_v[1]) begin
            nq = nq + 1;
            if (qrow == 0)
                for (k = 0; k < 2; k = k + 1) begin
                    e = q_i[1] * 2 + k;
                    if (qc[1][k * 256 +: 256] !== eqc[e] || qe[1][k * 10 +: 10] !== eqe[e][9:0] || qy[1][k * 512 +: 512] !== eqy[e])
                        gq = gq + 1;
                end
            if (q_i[1] == NV - 1) qrow = qrow + 1;
        end
        if (row == R - 1 && cyc > last_act + 400) begin
            $display("LOCKSTEP rows=%0d y_vecs=%0d q_vecs=%0d rstd=%0d mism=%0d gold_y_err=%0d gold_q_err=%0d fault=%b%b",
                     R, ny, nq, nrv, mism, gy, gq, fault[0], fault[1]);
            if (mism == 0 && gy == 0 && gq == 0 && ny == R * NV && nq == R * NV && nrv == R && fault == 2'b00) $display("PASS");
            else $display("FAIL");
            $finish;
        end
        if (cyc > 20000) begin $display("FAIL timeout"); $finish; end
    end
endmodule
