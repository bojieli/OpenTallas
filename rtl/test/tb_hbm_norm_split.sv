`timescale 1ns/1ps
// Transaction-level bench of the partitioned HBM norm engine (stream hbm-norm-split 2026-10-08).  ONE DUT per build:
//   default            : ot_hbm_norm_engine_view (the flat MEM1 view, the reference)
//   +define+OT_NSPLIT_G8  : ot_hbm_norm_split_view_g8   (8 x ot_hbm_norm_grp8 + top)
//   +define+OT_NSPLIT_G16 : ot_hbm_norm_split_view_g16  (4 x ot_hbm_norm_grp16 + top)
//   +define+OT_NSPLIT_G8R / G16R : the REP=1 tops (broadcast flops replicated per group, safe-hbm S-C7)
// Stimulus = tb_su_norm_mem_lockstep's: R rows back to back (row 0 the DS1M golden row, row k the golden x rotated by
// 37k), row k+1's go issued the cycle THIS DUT's rstd appears (overlapping x writes and scale reads), gain ROM
// reloaded (rotated by 11) before row R-1.  Every y vector, q vector and rstd is written in order to stream.txt
// (latency-free: the split adds pipeline cycles); run_split_bench.sh diffs the split's stream against the reference's.
// Row 0 is also checked against the golden ey / eq*.  Prints SPLITBENCH ... then PASS or FAIL (line start).
module tb_hbm_norm_split #(parameter integer R = 4, parameter integer HUB_IN = 33);
    localparam integer N = 64, D = 5120, NV = D / N, NX = 4 * D, NB = D / 32;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] xm [0:NX-1]; reg [31:0] wm [0:D-1]; reg [31:0] cfg [0:5]; reg [31:0] ey [0:D-1];
    reg [255:0] eqc [0:NB-1]; reg [15:0] eqe [0:NB-1]; reg [511:0] eqy [0:NB-1];
    integer fo;
    initial begin
        $readmemh("x.mem", xm); $readmemh("w.mem", wm); $readmemh("cfg.mem", cfg); $readmemh("ey.mem", ey);
        $readmemh("eqc.mem", eqc); $readmemh("eqe.mem", eqe); $readmemh("eqy.mem", eqy);
        fo = $fopen("stream.txt", "w");
    end
    reg rst_n = 1'b0, go = 1'b0, in_v = 1'b0, wl_v = 1'b0;
    reg [7:0] wl_i = 0;
    reg [N*32-1:0] wl_d = 0;
    reg [4*N*32-1:0] in_x = 0;
    wire y_v, r_v, q_v, ro_v, fault;
    wire [7:0] y_i, q_i;
    wire [N*32-1:0] y, ro; wire [31:0] r;
    wire [2*256-1:0] qc; wire [2*10-1:0] qe; wire [2*512-1:0] qy;
`ifdef OT_NSPLIT_G8R
    ot_hbm_norm_split_view_g8r dut (
`elsif OT_NSPLIT_G16R
    ot_hbm_norm_split_view_g16r dut (
`elsif OT_NSPLIT_G8
    ot_hbm_norm_split_view_g8 dut (
`elsif OT_NSPLIT_G16
    ot_hbm_norm_split_view_g16 dut (
`else
    ot_hbm_norm_engine_view dut (
`endif
        .clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre({cfg[3], cfg[2], cfg[1], cfg[0]}),
        .n_f(cfg[4]), .eps(cfg[5]), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(32'd0), .sin_t(32'd0),
        .y_v(y_v), .y_i(y_i), .y(y), .r_v(r_v), .r(r), .q_v(q_v), .q_i(q_i), .q_codes(qc),
        .q_e(qe), .q_y(qy), .ro_v(ro_v), .ro(ro), .fault(fault));
    reg [HUB_IN:0] hv; reg [7:0] hi [0:HUB_IN]; reg [7:0] hr [0:HUB_IN];
    integer cyc = 0, row = -1, iss = NV, gy = 0, gq = 0, ny = 0, nq = 0, nrv = 0, last_act = 0, j, k, e, nro = 0;
    integer ydone = 0, wl_at = -1, wl_n = 0, wl_rot = 0, yrow = 0, qrow = 0, first_y = -1, first_go = -1;
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
        go <= 1'b0;
        if ((row < 0 && cyc == 10 + NV) || (row >= 0 && row < R - 1 && r_v && !(row == R - 2))) begin
            go <= 1'b1; row = row + 1; iss = 0;
            if (first_go < 0) first_go = cyc;
        end
        if (y_v && y_i == NV - 1) ydone = ydone + 1;
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
        if (rst_n) begin
            if (r_v) begin $fwrite(fo, "R %h\n", r); nrv = nrv + 1; end
            if (ro_v) nro = nro + 1;
            if (y_v) begin
                if (first_y < 0) first_y = cyc;
                $fwrite(fo, "Y %0d %h\n", y_i, y);
                ny = ny + 1;
                if (yrow == 0)
                    for (j = 0; j < N; j = j + 1) if (y[j * 32 +: 32] !== ey[y_i * N + j]) gy = gy + 1;
                if (y_i == NV - 1) yrow = yrow + 1;
            end
            if (q_v) begin
                $fwrite(fo, "Q %0d %h %h %h\n", q_i, qc, qe, qy);
                nq = nq + 1;
                if (qrow == 0)
                    for (k = 0; k < 2; k = k + 1) begin
                        e = q_i * 2 + k;
                        if (qc[k * 256 +: 256] !== eqc[e] || qe[k * 10 +: 10] !== eqe[e][9:0] || qy[k * 512 +: 512] !== eqy[e])
                            gq = gq + 1;
                    end
                if (q_i == NV - 1) qrow = qrow + 1;
            end
        end
        if (y_v || q_v || in_v || go) last_act = cyc;
        if (row == R - 1 && cyc > last_act + 400) begin
            $fwrite(fo, "F %b\n", fault);
            $fclose(fo);
            $display("SPLITBENCH rows=%0d y_vecs=%0d q_vecs=%0d rstd=%0d ro=%0d gold_y_err=%0d gold_q_err=%0d fault=%b go0_to_y0=%0d",
                     R, ny, nq, nrv, nro, gy, gq, fault, first_y - first_go);
            if (gy == 0 && gq == 0 && ny == R * NV && nq == R * NV && nrv == R && nro == 0 && fault == 1'b0) $display("PASS");
            else $display("FAIL");
            $finish;
        end
        if (cyc > 20000) begin $display("FAIL timeout"); $finish; end
    end
endmodule
