`timescale 1ns/1ps
// Lockstep bench of ot_hbm_norm_engine_view with the feasibility fixes (RLY=1: the rst_n port drives only
// ot_rst_relay instances, the engine's lanes / chunks / act-quant blocks / tail reset from 4 + 1 regional relay flops;
// XST=1: a second input register stage on every input, so the in_x / wl_d capture -> engine wire is two stages)
// against the pinned view (RLY=0, XST=0).  Same stimulus as tb_su_norm_mem_lockstep (DS1M golden row + 3 rotated,
// overlapped rows, gain reload before the last row).  The new view's outputs must equal the reference view's outputs
// XST cycles later, every cycle (valids, indices, r, fault; data whenever valid), and its row 0 must match the golden
// ey / eq*.  Prints LOCKSTEP ... then PASS or FAIL (line start).
// Negative control OT_NEV_MUT_SKEW: the XST stage skips wl_d (gain data one cycle ahead of wl_v / wl_i) -> FAIL.
module tb_norm_view_rly_lockstep #(parameter integer R = 4, parameter integer HUB_IN = 33);
    localparam integer N = 64, D = 5120, NV = D / N, NX = 4 * D, NB = D / 32, LAG = 1;
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
    // g = 0: pinned view (reference); g = 1: RLY=1 XST=1
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_dut
        ot_hbm_norm_engine_view #(.RLY(g), .XST(g)) dut (
            .clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre({cfg[3], cfg[2], cfg[1], cfg[0]}),
            .n_f(cfg[4]), .eps(cfg[5]), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(32'd0), .sin_t(32'd0),
            .y_v(y_v[g]), .y_i(y_i[g]), .y(y[g]), .r_v(r_v[g]), .r(r[g]), .q_v(q_v[g]), .q_i(q_i[g]), .q_codes(qc[g]),
            .q_e(qe[g]), .q_y(qy[g]), .ro_v(ro_v[g]), .ro(ro[g]), .fault(fault[g]));
    end endgenerate
    // the reference's outputs delayed LAG cycles
    reg d_y_v, d_r_v, d_q_v, d_ro_v, d_fault; reg [7:0] d_y_i, d_q_i; reg [N*32-1:0] d_y, d_ro; reg [31:0] d_r;
    reg [2*256-1:0] d_qc; reg [2*10-1:0] d_qe; reg [2*512-1:0] d_qy;
    always @(posedge clk) begin
        d_y_v <= y_v[0]; d_r_v <= r_v[0]; d_q_v <= q_v[0]; d_ro_v <= ro_v[0]; d_fault <= fault[0];
        d_y_i <= y_i[0]; d_q_i <= q_i[0]; d_y <= y[0]; d_ro <= ro[0]; d_r <= r[0]; d_qc <= qc[0]; d_qe <= qe[0]; d_qy <= qy[0];
    end
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
        // lagged lockstep compare (from 12 cycles after reset release: both views out of reset)
        if (cyc > 15) begin
            if (d_y_v !== y_v[1] || d_r_v !== r_v[1] || d_q_v !== q_v[1] || d_ro_v !== ro_v[1] || d_fault !== fault[1]
                || (d_y_v && (d_y_i !== y_i[1] || d_y !== y[1])) || (d_r_v && d_r !== r[1])
                || (d_q_v && (d_q_i !== q_i[1] || d_qc !== qc[1] || d_qe !== qe[1] || d_qy !== qy[1]))
                || (d_ro_v && d_ro !== ro[1])) begin
                if (mism < 5) $display("MISMATCH cyc %0d y_v %b%b y_i %0d/%0d q_v %b%b fault %b%b", cyc, d_y_v, y_v[1],
                                       d_y_i, y_i[1], d_q_v, q_v[1], d_fault, fault[1]);
                mism = mism + 1;
            end
        end
        if (r_v[1]) nrv = nrv + 1;
        if (y_v[0] || y_v[1] || q_v[0] || q_v[1] || in_v || go) last_act = cyc;
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
