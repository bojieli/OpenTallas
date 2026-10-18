`timescale 1ns/1ps
// S81-DV 16-slice norm exchange bench (deliverable 3, step 1).  16 x ot_s81dv_norm_slice on the slice ring (logical
// order = the plan's snake: S row c = 0..7, then N row c = 7..0; street links LS registered stages, the two end-column
// links LE stages, both directions), the DS1M golden hc_pre + RMSNorm row (results/rtl/hbm_norm_engine_view_20261006/
// gold: x.mem = 4 copies x 5120, w.mem gains, cfg.mem = pre[0..3], n_f, eps; ey.mem = golden y).
// Slice g gets the global beats 5g .. 5g+4 (element e = beat*64 + lane).  Checks: every y word of every slice equals
// the golden ey; all 16 slices produce the same rstd; no slice faults; exactly 16 x 5 y vectors.
// Prints DVNORM16 ... then PASS or FAIL at line start.  Negative controls: +define+OT_S81DV_MUT_BASE (slice 3 tags its
// partials as slice 4's), +define+OT_S81DV_MUT_LEAF (finish leaves 0/1 swapped) -- each must FAIL.
module tb_s81dv_norm16 #(parameter integer LS = 9, parameter integer LE = 29);
    localparam integer NS = 16, NVL = 5, D = 5120, N = 64, KW = 1 + 4 + 8 + NVL * 32;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] xm [0:4*D-1]; reg [31:0] wm [0:D-1]; reg [31:0] cfg [0:5]; reg [31:0] ey [0:D-1];
    initial begin $readmemh("x.mem", xm); $readmemh("w.mem", wm); $readmemh("cfg.mem", cfg); $readmemh("ey.mem", ey); end
    reg rst_n = 1'b0, go = 1'b0, in_v = 1'b0, wl_v = 1'b0;
    reg [7:0] wl_i = 0;
    reg [2:0] beat = 0;
    // ring wires: eo[k] -> link -> wi[k+1]; wo[k+1] -> link -> ei[k]
    wire [KW-1:0] eo [0:NS-1], wo [0:NS-1], wi [0:NS-1], ei [0:NS-1];
    wire [NS-1:0] y_v, r_v, flt;
    wire [7:0] y_i [0:NS-1];
    wire [N*32-1:0] y [0:NS-1];
    wire [31:0] r [0:NS-1];
    genvar g;
    generate
        for (g = 0; g < NS; g = g + 1) begin : s
            reg [4*N*32-1:0] in_x; reg [N*32-1:0] wl_d;
            integer j, k;
            always @(*) begin
                for (k = 0; k < 4; k = k + 1)
                    for (j = 0; j < N; j = j + 1) in_x[(k * N + j) * 32 +: 32] = xm[k * D + (g * NVL + beat) * N + j];
                for (j = 0; j < N; j = j + 1) wl_d[j * 32 +: 32] = wm[(g * NVL + wl_i) * N + j];
            end
            ot_s81dv_norm_slice #(.SID(g), .NS(NS), .NVL(NVL)) u (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v),
                .in_x(in_x), .pre({cfg[3], cfg[2], cfg[1], cfg[0]}), .eps(cfg[5]), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d),
                .wi_v(wi[g][KW-1]), .wi_h(wi[g][KW-2 -: 4]), .wi_b(wi[g][KW-6 -: 8]), .wi_d(wi[g][NVL*32-1:0]),
                .ei_v(ei[g][KW-1]), .ei_h(ei[g][KW-2 -: 4]), .ei_b(ei[g][KW-6 -: 8]), .ei_d(ei[g][NVL*32-1:0]),
                .eo_v(eo[g][KW-1]), .eo_h(eo[g][KW-2 -: 4]), .eo_b(eo[g][KW-6 -: 8]), .eo_d(eo[g][NVL*32-1:0]),
                .wo_v(wo[g][KW-1]), .wo_h(wo[g][KW-2 -: 4]), .wo_b(wo[g][KW-6 -: 8]), .wo_d(wo[g][NVL*32-1:0]),
                .y_v(y_v[g]), .y_i(y_i[g]), .y(y[g]), .r_v(r_v[g]), .r(r[g]), .fault(flt[g]));
            // link g -> g+1 (both directions): the end-column links are 7 -> 8 and 15 -> 0
            localparam integer L = (g == 7 || g == NS - 1) ? LE : LS;
            ot_hdc_delay #(.W(KW), .D(L), .RESET(1)) u_le (.clk(clk), .rst_n(rst_n), .d(eo[g]), .q(wi[(g + 1) % NS]));
            ot_hdc_delay #(.W(KW), .D(L), .RESET(1)) u_lw (.clk(clk), .rst_n(rst_n), .d(wo[(g + 1) % NS]), .q(ei[g]));
        end
    endgenerate
    integer cyc = 0, i, j, err = 0, ny = 0, nr = 0, rdiff = 0, t_go = -1, t_r = -1, t_r_last = -1;
    reg [31:0] r0; reg r0_set = 1'b0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        wl_v <= 1'b0; go <= 1'b0; in_v <= 1'b0;
        if (cyc >= 10 && cyc < 10 + NVL) begin wl_v <= 1'b1; wl_i <= cyc - 10; end
        if (cyc == 30) begin go <= 1'b1; t_go = cyc; end
        if (cyc >= 32 && cyc < 32 + NVL) begin in_v <= 1'b1; beat <= cyc - 32; end
        for (i = 0; i < NS; i = i + 1) begin
            if (y_v[i]) begin
                ny = ny + 1;
                for (j = 0; j < N; j = j + 1)
                    if (y[i][j * 32 +: 32] !== ey[(i * NVL + y_i[i]) * N + j]) begin
                        if (err < 8) $display("Y MISMATCH slice %0d beat %0d lane %0d got %h want %h", i, y_i[i], j,
                                              y[i][j * 32 +: 32], ey[(i * NVL + y_i[i]) * N + j]);
                        err = err + 1;
                    end
            end
            if (r_v[i]) begin
                nr = nr + 1;
                if (t_r < 0) t_r = cyc;
                t_r_last = cyc;
                if (!r0_set) begin r0 = r[i]; r0_set = 1'b1; end
                else if (r[i] !== r0) rdiff = rdiff + 1;
            end
        end
        if (cyc == 3000) begin
            $display("DVNORM16 slices=%0d y_vecs=%0d y_err=%0d rstd=%0d rstd_distinct=%0d rstd=%h fault=%b go_to_first_rstd=%0d rstd_spread=%0d LS=%0d LE=%0d",
                     NS, ny, err, nr, rdiff, r0, flt, t_r - t_go, t_r_last - t_r, LS, LE);
            if (err == 0 && ny == NS * NVL && nr == NS && rdiff == 0 && flt == {NS{1'b0}}) $display("PASS");
            else $display("FAIL");
            $finish;
        end
    end
endmodule
