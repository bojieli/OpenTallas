`timescale 1ns/1ps
// S81-SLICE beat-leaf norm bench (stream 0cm): the 5 beat leaves of slice SG (real ot_s81sl_vn + ot_s81sl_vq each) on the
// DS1M golden hc_pre + RMSNorm row (results/rtl/hbm_norm_engine_view_20261006/gold; bp.mem / rstd.mem from
// tools/s81_slice/norm_gold.py).  Checks, per leaf k (global beat b = 5 SG + k):
//   beat partial p == bp[b] (the golden csum subtree, = G64's s), y == ey[64 b ..], FP8 codes / exponents of blocks
//   2b, 2b+1 == eqc / eqe, BF16 family == ey (BF16 bits), no fault.
// The rstd is the golden one (the xfin's exchange + finish is benched by S81-DV's tb_s81dv_xfin16); it is presented at a
// fixed offset after the last partial.  Prints SLBEATNORM ... then PASS / FAIL with the measured latencies.
// Negative control: +define+OT_S81SL_MUT_TREE (vn's node 4 adds n0 + n2: golden association broken).
module tb_s81sl_beatnorm #(parameter integer SG = 0, parameter integer RB_GAP = 4);
    localparam integer D = 5120, NL = 5;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] xm [0:4*D-1]; reg [31:0] wm [0:D-1]; reg [31:0] cfg [0:5]; reg [31:0] ey [0:D-1];
    reg [31:0] bp [0:79]; reg [31:0] rs [0:0]; reg [255:0] eqc [0:159]; reg [15:0] eqe [0:159];
    initial begin
        $readmemh("x.mem", xm); $readmemh("w.mem", wm); $readmemh("cfg.mem", cfg); $readmemh("ey.mem", ey);
        $readmemh("bp.mem", bp); $readmemh("rstd.mem", rs); $readmemh("eqc.mem", eqc); $readmemh("eqe.mem", eqe);
    end
    reg rst_n = 1'b0, hw_v = 1'b0, go = 1'b0, wl_v = 1'b0, rb_v = 1'b0;
    reg [2:0] hw_j = 0, wl_i = 0; reg hw_hf = 0;
    wire [NL-1:0] p_v, y_v, xq_v, xb_v, fv, fq;
    wire [31:0] p_d [0:NL-1]; wire [2:0] y_i [0:NL-1]; wire [255:0] y [0:NL-1];
    wire [531:0] xq_d [0:NL-1]; wire [1023:0] xb_d [0:NL-1];
    reg [255:0] hw_d [0:NL-1]; reg [255:0] wl_d [0:NL-1];
    integer k, c, i;
    always @(*)
        for (k = 0; k < NL; k = k + 1) begin
            for (c = 0; c < 4; c = c + 1) for (i = 0; i < 4; i = i + 1)
                hw_d[k][(4 * c + i) * 16 +: 16] = xm[c * D + 64 * (5 * SG + k) + 8 * hw_j + 4 * hw_hf + i][31:16];
            for (i = 0; i < 8; i = i + 1) wl_d[k][i * 32 +: 32] = wm[64 * (5 * SG + k) + 8 * wl_i + i];
        end
    genvar g;
    generate for (g = 0; g < NL; g = g + 1) begin : lf
        wire hq_v; wire [255:0] hq_d;
        ot_s81sl_vn u_n (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d[g]),
            .hr_v(1'b0), .hr_j(3'd0), .hr_hf(1'b0), .hq_v(hq_v), .hq_d(hq_d),
            .n_go(go), .n_pre({cfg[3], cfg[2], cfg[1], cfg[0]}), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d[g]),
            .rb_v(rb_v), .rb_d(rs[0]), .p_v(p_v[g]), .p_d(p_d[g]), .y_v(y_v[g]), .y_i(y_i[g]), .y(y[g]), .fault(fv[g]));
        ot_s81sl_vq u_q (.clk(clk), .rst_n(rst_n), .y_v(y_v[g]), .y_i(y_i[g]), .y(y[g]), .xq_v(xq_v[g]), .xq_d(xq_d[g]),
            .xb_v(xb_v[g]), .xb_d(xb_d[g]), .fault(fq[g]));
    end endgenerate
    integer cyc = 0, err = 0, np = 0, ny = 0, nq = 0, t_go = -1, t_p = -1, t_rb = -1, t_y = -1, t_q = -1, b;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        hw_v <= 1'b0; wl_v <= 1'b0; go <= 1'b0; rb_v <= 1'b0;
        if (cyc >= 10 && cyc < 26) begin hw_v <= 1'b1; hw_j <= (cyc - 10) >> 1; hw_hf <= (cyc - 10) & 1; end
        if (cyc >= 30 && cyc < 38) begin wl_v <= 1'b1; wl_i <= cyc - 30; end
        if (cyc == 50) begin go <= 1'b1; t_go = cyc; end
        if (t_p >= 0 && cyc == t_p + RB_GAP) begin rb_v <= 1'b1; t_rb = cyc; end
        for (k = 0; k < NL; k = k + 1) begin
            b = 5 * SG + k;
            if (p_v[k]) begin
                np = np + 1; if (t_p < 0 || cyc > t_p) t_p = cyc;
                if (p_d[k] !== bp[b]) begin err = err + 1; $display("P MISMATCH leaf %0d got %h want %h", k, p_d[k], bp[b]); end
            end
            if (y_v[k]) begin
                ny = ny + 1; if (t_y < 0) t_y = cyc;
                for (i = 0; i < 8; i = i + 1)
                    if (y[k][i * 32 +: 32] !== ey[64 * b + 8 * y_i[k] + i]) begin
                        if (err < 10) $display("Y MISMATCH leaf %0d j %0d lane %0d got %h want %h", k, y_i[k], i,
                                               y[k][i * 32 +: 32], ey[64 * b + 8 * y_i[k] + i]);
                        err = err + 1;
                    end
            end
            if (xq_v[k]) begin
                nq = nq + 1; if (t_q < 0) t_q = cyc;
                if (xq_d[k][255:0] !== eqc[2 * b] || xq_d[k][265:256] !== eqe[2 * b][9:0] ||
                    xq_d[k][521:266] !== eqc[2 * b + 1] || xq_d[k][531:522] !== eqe[2 * b + 1][9:0]) begin
                    err = err + 1; $display("Q MISMATCH leaf %0d", k);
                end
                for (i = 0; i < 64; i = i + 1)
                    if (xb_d[k][16 * i +: 16] !== ey[64 * b + i][31:16]) begin
                        if (err < 10) $display("B MISMATCH leaf %0d lane %0d", k, i); err = err + 1;
                    end
            end
        end
        if (cyc == 1500) begin
            $display("SLBEATNORM SG=%0d leaves=%0d partials=%0d ybeats=%0d qbeats=%0d err=%0d fault=%b/%b go_to_partial=%0d rstd_to_first_y=%0d rstd_to_xq=%0d",
                     SG, NL, np, ny, nq, err, fv, fq, t_p - t_go, t_y - t_rb, t_q - t_rb);
            if (err == 0 && np == NL && ny == 8 * NL && nq == NL && fv == 0 && fq == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
