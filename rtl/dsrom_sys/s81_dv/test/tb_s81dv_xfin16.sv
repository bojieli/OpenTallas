`timescale 1ns/1ps
// S81-DV exchange + replicated-finish bench, minimum vehicle (deliverable 3, step 1b).  One real ot_hbm_norm_grp
// (G = 64, D = 5120: a beat's partial does not depend on how many beats the group holds, so beat 5g+i's partial is
// exactly what slice g's G64 / D320 group emits) feeds 16 real ot_s81dv_xfin leaves (collector + ring stop + finish) on
// the plan's snake ring (street links LS stages, end-column links LE stages, both directions).  Slice g receives the
// partials of beats 5g .. 5g+4 as its local s_i 0..4.  The group's scale takes slice 0's rstd.
// Checks: all 16 slices produce the SAME rstd, no fault, the 80 y vectors equal the DS1M golden ey bit for bit.
// Prints DVXFIN16 ... then PASS / FAIL.  Negative controls: +define+OT_S81DV_MUT_BASE / +define+OT_S81DV_MUT_LEAF (leaves 1/2 swapped: association change).
module tb_s81dv_xfin16 #(parameter integer LS = 9, parameter integer LE = 29);
    localparam integer NS = 16, NVL = 5, D = 5120, N = 64, NV = D / N, KW = 1 + 4 + 8 + NVL * 32;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] xm [0:4*D-1]; reg [31:0] wm [0:D-1]; reg [31:0] cfg [0:5]; reg [31:0] ey [0:D-1];
    initial begin $readmemh("x.mem", xm); $readmemh("w.mem", wm); $readmemh("cfg.mem", cfg); $readmemh("ey.mem", ey); end
    reg rst_n = 1'b0, go = 1'b0, in_v = 1'b0, wl_v = 1'b0;
    reg [7:0] wl_i = 0, beat = 0;
    reg [4*N*32-1:0] in_x; reg [N*32-1:0] wl_d;
    integer j, k;
    always @(*) begin
        for (k = 0; k < 4; k = k + 1) for (j = 0; j < N; j = j + 1) in_x[(k * N + j) * 32 +: 32] = xm[k * D + beat * N + j];
        for (j = 0; j < N; j = j + 1) wl_d[j * 32 +: 32] = wm[wl_i * N + j];
    end
    wire s_v, y_v, gf; wire [7:0] s_i, y_i; wire [31:0] s; wire [N*32-1:0] y;
    wire [NS-1:0] rb_v, flt; wire [31:0] rb_d [0:NS-1];
    reg rbg_v; reg [31:0] rbg_d;
    always @(posedge clk) begin rbg_v <= rb_v[0]; rbg_d <= rb_d[0]; end
    ot_hbm_norm_grp #(.G(64), .D(D), .N(64)) u_g (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x),
        .pre({cfg[3], cfg[2], cfg[1], cfg[0]}), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .rb_v(rbg_v), .rb_d(rbg_d),
        .s_v(s_v), .s_i(s_i), .s(s), .y_v(y_v), .y_i(y_i), .y(y), .gf(gf));
    wire [KW-1:0] eo [0:NS-1], wo [0:NS-1], wi [0:NS-1], ei [0:NS-1];
    genvar g;
    generate
        for (g = 0; g < NS; g = g + 1) begin : sl
            wire mine = s_v && s_i >= g * NVL && s_i < (g + 1) * NVL;
            wire [7:0] li = s_i - g * NVL;
            ot_s81dv_xfin #(.NS(NS), .NVL(NVL), .SIW(8)) u (.clk(clk), .rst_n(rst_n), .go(go), .mode(1'b0), .sid(g[3:0]), .eps(cfg[5]),
                .s_v(mine), .s_i(li), .s(s),
                .wi_v(wi[g][KW-1]), .wi_h(wi[g][KW-2 -: 4]), .wi_b(wi[g][KW-6 -: 8]), .wi_d(wi[g][NVL*32-1:0]),
                .ei_v(ei[g][KW-1]), .ei_h(ei[g][KW-2 -: 4]), .ei_b(ei[g][KW-6 -: 8]), .ei_d(ei[g][NVL*32-1:0]),
                .eo_v(eo[g][KW-1]), .eo_h(eo[g][KW-2 -: 4]), .eo_b(eo[g][KW-6 -: 8]), .eo_d(eo[g][NVL*32-1:0]),
                .wo_v(wo[g][KW-1]), .wo_h(wo[g][KW-2 -: 4]), .wo_b(wo[g][KW-6 -: 8]), .wo_d(wo[g][NVL*32-1:0]),
                .rb_v(rb_v[g]), .rb_d(rb_d[g]), .e_v(), .e_c(), .e_hh(), .e_kk(), .e_dd(), .fault(flt[g]));
            localparam integer L = (g == 7 || g == NS - 1) ? LE : LS;
            ot_hdc_delay #(.W(KW), .D(L), .RESET(1)) u_le (.clk(clk), .rst_n(rst_n), .d(eo[g]), .q(wi[(g + 1) % NS]));
            ot_hdc_delay #(.W(KW), .D(L), .RESET(1)) u_lw (.clk(clk), .rst_n(rst_n), .d(wo[(g + 1) % NS]), .q(ei[g]));
        end
    endgenerate
    integer cyc = 0, i, err = 0, ny = 0, nr = 0, rdiff = 0, t_go = -1, t_r = -1, t_r_last = -1, t_s_last = -1;
    reg [31:0] r0; reg r0_set = 1'b0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        wl_v <= 1'b0; go <= 1'b0; in_v <= 1'b0;
        if (cyc >= 10 && cyc < 10 + NV) begin wl_v <= 1'b1; wl_i <= cyc - 10; end
        if (cyc == 100) begin go <= 1'b1; t_go = cyc; end
        if (cyc >= 102 && cyc < 102 + NV) begin in_v <= 1'b1; beat <= cyc - 102; end
        if (s_v) t_s_last = cyc;
        if (y_v) begin
            ny = ny + 1;
            for (j = 0; j < N; j = j + 1)
                if (y[j * 32 +: 32] !== ey[y_i * N + j]) begin
                    if (err < 8) $display("Y MISMATCH beat %0d lane %0d got %h want %h", y_i, j, y[j * 32 +: 32], ey[y_i * N + j]);
                    err = err + 1;
                end
        end
        for (i = 0; i < NS; i = i + 1)
            if (rb_v[i]) begin
                nr = nr + 1;
                if (t_r < 0) t_r = cyc;
                t_r_last = cyc;
                if (!r0_set) begin r0 = rb_d[i]; r0_set = 1'b1; end
                else if (rb_d[i] !== r0) rdiff = rdiff + 1;
            end
        if (cyc == 4000) begin
            $display("DVXFIN16 slices=%0d y_vecs=%0d y_err=%0d rstd=%0d rstd_distinct=%0d rstd=%h fault=%b gf=%b last_partial_to_first_rstd=%0d rstd_spread=%0d LS=%0d LE=%0d",
                     NS, ny, err, nr, rdiff, r0, flt, gf, t_r - t_s_last, t_r_last - t_r, LS, LE);
            if (err == 0 && ny == NV && nr == NS && rdiff == 0 && flt == {NS{1'b0}} && !gf) $display("PASS");
            else $display("FAIL");
            $finish;
        end
    end
endmodule
