`timescale 1ns/1ps
// S81-SLICE beat-leaf bench (stream 0cm): ONE beat leaf = real ot_s81sl_vp + ot_s81sl_vn + ot_s81sl_vq on the 1M token's
// real layer chain (tools/s81_slice/leaf_gold.py: su_cases via hc_gate.chains_golden), commands on vp's command port only:
//   row writes (gains, coefficients, hc_post y, h0) -> HLOAD -> GAIN a -> NORM a -> [rstd a] -> POST a -> HSTORE/RDOUT
//   (h1 check) -> GAIN f -> NORM f -> [rstd f] -> POST f -> HSTORE/RDOUT (h2 check).
// Checks: beat partial == golden csum subtree, y == golden normed y, FP8 codes / exponents == golden act-quant, BF16
// family == y, h after each hc_post == golden (all 4 copies x 64), no fault.  The rstd is the golden full-row rstd
// (presented RB_GAP edges after the partial: the xfin's exchange is benched by S81-DV).  Prints SLBEAT + latencies.
// Negative controls: +define+OT_S81SL_MUT_TREE (vn tree association), +define+OT_S81SL_TB_MUT_COEF (bench swaps two
// comb words in the leaf store: hc_post must then mismatch -- proves the h check sees the coefficient path).
module tb_s81sl_beat #(parameter integer RB_GAP = 4);
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [15:0] h0 [0:255];
    reg [15:0] hn [0:511];
    reg [31:0] pre [0:7];
    reg [31:0] gw [0:127];
    reg [31:0] rstd [0:1];
    reg [31:0] bp [0:1];
    reg [31:0] ey [0:127];
    reg [255:0] eq [0:3];
    reg [9:0] ee [0:3];
    reg [31:0] comb [0:31];
    reg [31:0] post [0:7];
    reg [31:0] yp [0:127];
    initial begin
        $readmemh("h0.mem", h0);
        $readmemh("a_hn.mem", hn, 0, 255); $readmemh("f_hn.mem", hn, 256, 511);
        $readmemh("a_pre.mem", pre, 0, 3); $readmemh("f_pre.mem", pre, 4, 7);
        $readmemh("a_w.mem", gw, 0, 63); $readmemh("f_w.mem", gw, 64, 127);
        $readmemh("a_rstd.mem", rstd, 0, 0); $readmemh("f_rstd.mem", rstd, 1, 1);
        $readmemh("a_bp.mem", bp, 0, 0); $readmemh("f_bp.mem", bp, 1, 1);
        $readmemh("a_y.mem", ey, 0, 63); $readmemh("f_y.mem", ey, 64, 127);
        $readmemh("a_q.mem", eq, 0, 1); $readmemh("f_q.mem", eq, 2, 3);
        $readmemh("a_e.mem", ee, 0, 1); $readmemh("f_e.mem", ee, 2, 3);
        $readmemh("a_comb.mem", comb, 0, 15); $readmemh("f_comb.mem", comb, 16, 31);
        $readmemh("a_post.mem", post, 0, 3); $readmemh("f_post.mem", post, 4, 7);
        $readmemh("a_yp.mem", yp, 0, 63); $readmemh("f_yp.mem", yp, 64, 127);
    end
    // leaf-store map (rows)
    localparam integer R_GA = 0, R_GF = 16, R_CA = 32, R_CF = 40, R_YA = 48, R_YF = 64, R_H0 = 96, R_HS = 128;
    reg rst_n = 1'b0, c_v = 1'b0, sw_v = 1'b0, rb_v = 1'b0;
    reg [159:0] c_d = 0; reg [9:0] sw_a = 0; reg [127:0] sw_d = 0; reg [31:0] rb_d = 0;
    wire lo_v, hw_v, hr_v, hq_v, n_go, wl_v, fp, fn, fq, p_v, y_v, xq_v, xb_v, hw_hf, hr_hf;
    wire [255:0] lo_d, hw_d, hq_d, wl_d, y; wire [2:0] hw_j, hr_j, wl_i, y_i; wire [127:0] n_pre; wire [31:0] p_d;
    wire [531:0] xq_d; wire [1023:0] xb_d;
    ot_s81sl_vp u_p (.clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(4'hf), .sw_d(sw_d),
        .cw_v(2'b00), .cw_a(24'd0), .cw_d(64'd0), .lo_v(lo_v), .lo_d(lo_d),
        .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d), .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf),
        .hq_v(hq_v), .hq_d(hq_d), .n_go(n_go), .n_pre(n_pre), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .fault(fp));
    ot_s81sl_vn u_n (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d),
        .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hq_v), .hq_d(hq_d), .n_go(n_go), .n_pre(n_pre),
        .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .rb_v(rb_v), .rb_d(rb_d), .p_v(p_v), .p_d(p_d),
        .y_v(y_v), .y_i(y_i), .y(y), .fault(fn));
    ot_s81sl_vq u_q (.clk(clk), .rst_n(rst_n), .y_v(y_v), .y_i(y_i), .y(y), .xq_v(xq_v), .xq_d(xq_d),
        .xb_v(xb_v), .xb_d(xb_d), .fault(fq));

    // row image to write: {row, data}
    reg [127:0] img [0:159]; reg [159:0] wr_ok;
    integer i, k, r, w;
    initial begin
        for (r = 0; r < 160; r = r + 1) begin img[r] = 128'd0; wr_ok[r] = 1'b0; end
        for (k = 0; k < 2; k = k + 1) begin
            for (i = 0; i < 64; i = i + 1) begin
                img[(k ? R_GF : R_GA) + i / 4][32 * (i % 4) +: 32] = gw[64 * k + i];
                img[(k ? R_YF : R_YA) + i / 4][32 * (i % 4) +: 32] = yp[64 * k + i];
            end
            for (i = 0; i < 16; i = i + 1) img[(k ? R_CF : R_CA) + i / 4][32 * (i % 4) +: 32] = comb[16 * k + i];
`ifdef OT_S81SL_TB_MUT_COEF
            img[(k ? R_CF : R_CA)][31:0] = comb[16 * k + 1]; img[(k ? R_CF : R_CA)][63:32] = comb[16 * k + 0];
`endif
            for (i = 0; i < 4; i = i + 1) img[(k ? R_CF : R_CA) + 4][32 * i +: 32] = post[4 * k + i];
            for (r = 0; r < 16; r = r + 1) begin wr_ok[(k ? R_GF : R_GA) + r] = 1; wr_ok[(k ? R_YF : R_YA) + r] = 1; end
            for (r = 0; r < 5; r = r + 1) wr_ok[(k ? R_CF : R_CA) + r] = 1;
        end
        // h0: half row hi = (j = hi >> 1, hf = hi & 1): copy c, lane 4 hf + t at bit (4c + t) * 16 of the 256-b half row
        for (i = 0; i < 16; i = i + 1)
            for (k = 0; k < 4; k = k + 1)
                for (w = 0; w < 4; w = w + 1) begin
                    r = R_H0 + 2 * i + ((4 * k + w) >= 8);
                    img[r][((4 * k + w) % 8) * 16 +: 16] = h0[k * 64 + 8 * (i >> 1) + 4 * (i & 1) + w];
                    wr_ok[r] = 1;
                end
    end

    // checks
    integer cyc = 0, err = 0, ph = 0, blk = 0, np_ = 0, ny = 0, nq = 0, nlo = 0;
    integer t_go = -1, t_p = -1, t_rb = -1, t_y0 = -1, t_ylast = -1, t_q = -1, t_post = -1, t_hw_last = -1, t_hload = -1;
    integer lat_p [0:1], lat_y [0:1], lat_q [0:1], lat_post [0:1];
    task cmd(input [3:0] op, input [9:0] a0, input [9:0] a1, input [7:0] n, input [127:0] imm);
        begin c_v <= 1'b1; c_d <= {imm, n, a1, a0, op}; end
    endtask
    always @(posedge clk) begin
        cyc <= cyc + 1;
        c_v <= 1'b0; sw_v <= 1'b0; rb_v <= 1'b0;
        if (cyc == 3) rst_n <= 1'b1;
        if (cyc >= 10 && cyc < 170 && wr_ok[cyc - 10]) begin sw_v <= 1'b1; sw_a <= cyc - 10; sw_d <= img[cyc - 10]; end
        if (cyc == 180) begin cmd(4'd3, R_H0, 0, 0, 0); t_hload = cyc; end                       // HLOAD
        // per block: GAIN, NORM, rstd, POST, HSTORE, RDOUT
        if (cyc == 220 + 400 * blk && blk < 2) cmd(4'd1, blk ? R_GF : R_GA, 0, 0, 0);            // GAIN
        if (cyc == 240 + 400 * blk && blk < 2) begin
            cmd(4'd5, 0, 0, 0, {pre[4 * blk + 3], pre[4 * blk + 2], pre[4 * blk + 1], pre[4 * blk + 0]}); t_go = cyc;   // NORM
        end
        if (p_v) begin
            np_ = np_ + 1; t_p = cyc; lat_p[blk] = cyc - t_go;
            if (p_d !== bp[1 * blk + 0]) begin err = err + 1; $display("P MISMATCH blk %0d got %h want %h", blk, p_d, bp[1 * blk + 0]); end
        end
        if (t_p >= 0 && cyc == t_p + RB_GAP) begin rb_v <= 1'b1; rb_d <= rstd[1 * blk + 0]; t_rb = cyc; t_y0 = -1; end
        if (y_v) begin
            ny = ny + 1; if (t_y0 < 0) begin t_y0 = cyc; lat_y[blk] = cyc - t_rb; end
            for (i = 0; i < 8; i = i + 1)
                if (y[32 * i +: 32] !== ey[64 * blk + 8 * y_i + i]) begin
                    if (err < 12) $display("Y MISMATCH blk %0d j %0d lane %0d got %h want %h", blk, y_i, i, y[32 * i +: 32], ey[64 * blk + 8 * y_i + i]);
                    err = err + 1;
                end
        end
        if (xq_v) begin
            nq = nq + 1; lat_q[blk] = cyc - t_rb; t_q = cyc;
            if (xq_d[255:0] !== eq[2 * blk + 0] || xq_d[265:256] !== ee[2 * blk + 0] || xq_d[521:266] !== eq[2 * blk + 1] || xq_d[531:522] !== ee[2 * blk + 1]) begin
                err = err + 1; $display("Q MISMATCH blk %0d e0 %h/%h e1 %h/%h", blk, xq_d[265:256], ee[2 * blk + 0], xq_d[531:522], ee[2 * blk + 1]);
            end
            for (i = 0; i < 64; i = i + 1)
                if (xb_d[16 * i +: 16] !== ey[64 * blk + i][31:16]) begin err = err + 1; if (err < 12) $display("B MISMATCH blk %0d lane %0d", blk, i); end
        end
        if (t_q >= 0 && cyc == t_q + 10) begin cmd(4'd2, blk ? R_CF : R_CA, blk ? R_YF : R_YA, 0, 0); t_post = cyc; end   // POST
        if (hw_v && t_post >= 0) begin t_hw_last = cyc; lat_post[blk] = cyc - t_post; end
        if (t_post >= 0 && cyc == t_post + 80) cmd(4'd4, R_HS, 0, 0, 0);                         // HSTORE
        if (t_post >= 0 && cyc == t_post + 110) cmd(4'd6, R_HS, 0, 16, 0);                       // RDOUT 16 row pairs
        if (lo_v) begin
            // half row nlo: copy c lane t
            for (k = 0; k < 4; k = k + 1) for (w = 0; w < 4; w = w + 1)
                if (lo_d[(4 * k + w) * 16 +: 16] !== hn[256 * blk + k * 64 + 8 * (nlo >> 1) + 4 * (nlo & 1) + w]) begin
                    if (err < 12) $display("H MISMATCH blk %0d half %0d copy %0d lane %0d got %h want %h", blk, nlo, k, w,
                                           lo_d[(4 * k + w) * 16 +: 16], hn[256 * blk + k * 64 + 8 * (nlo >> 1) + 4 * (nlo & 1) + w]);
                    err = err + 1;
                end
            nlo = nlo + 1;
            if (nlo == 16) begin nlo = 0; blk = blk + 1; t_p = -1; t_q = -1; t_post = -1; end
        end
        if (cyc == 1200) begin
            $display("SLBEAT partials=%0d ybeats=%0d qbeats=%0d blocks_done=%0d err=%0d fault=vp%b/vn%b/vq%b go_to_partial=%0d/%0d rstd_to_y0=%0d/%0d rstd_to_xq=%0d/%0d post_cmd_to_last_hw=%0d/%0d",
                     np_, ny, nq, blk, err, fp, fn, fq, lat_p[0], lat_p[1], lat_y[0], lat_y[1], lat_q[0], lat_q[1], lat_post[0], lat_post[1]);
            if (err == 0 && np_ == 2 && ny == 16 && nq == 2 && blk == 2 && !fp && !fn && !fq) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
