`timescale 1ns/1ps
// tb_s81sl_cap: bench of the S81-SLICE capture root ot_s81sl_cap (2026-10-17).
// Stimulus and expectation: tools/s81_slice/cap_model.py gen (the compiler model + return-slot legaliser; expected VALUES
// are the golden tree sums of every row's segments, computed independently of the arrival path).
// Each of the 8 lanes is the REAL die return chain of one frame column, so the rt bit order is the RTL's, not assumed:
//   column root word (stim) -> dsfd_node_NNfu (ot_s81_retn_static WIN 2: the column root node, forwards the word and
//   packs o = {oe, od, ot_, ov}) -> dsfd_rstg (column return stage) -> dsfd_cfifo_crs.ri -> rd -> cap rt[70 l +: 70].
// P1: independent golden A arrivals +1, writes +2, no value/order change.
// Checks, per edge: every lane word reaches the cap pin flop at the model's ARR edge (A lines); every leaf write
// (edge, leaf, port, word address, data) equals an expected W line exactly once; no extra write; final fault 0.
// Reports the latency from a row's last lane-word arrival (cap pin) to its leaf write.
// +DIR=<vector dir> +T=<edges> +NW=<rows>
module tb_s81sl_cap_p1;
    parameter integer MUT = 0;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg [65:0] lw [0:7];
    reg cfg_v; reg [159:0] cfg_d;
    wire [559:0] rt;
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_col
        wire [65:0] no, so; wire fo; wire [69:0] rd; wire [14:0] cc; wire [282:0] xa; wire [265:0] xb; wire [535:0] x2;
        wire rs;
        dsfd_node_NNfu u_node (.a(lw[gl]), .b(66'd0), .clk(clk), .fi(1'b0), .fo(fo), .o(no), .rst_n(rst_n));
        dsfd_rstg u_stg (.ck(clk), .i(no), .o(so), .rs(rst_n));
        dsfd_cfifo_crs u_cf (.cc(cc), .cr(clk), .cr_s(clk), .rd(rd), .ri(so), .rs(rs), .rst(rst_n), .st(2'b00),
            .xa(xa), .xb(xb), .xd(566'd0), .xf(clk), .x2(x2), .xd2(538'd0), .xf2(clk));
        assign rt[70 * gl +: 70] = rd;
    end endgenerate
    wire [9:0] cw_v; wire [119:0] cw_a; wire [319:0] cw_d; wire fault;
    ot_s81sl_cap_p1 #(.PINPIPE(1),.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .rt_w(rt[279:0]), .rt_e(rt[559:280]), .cfg_v(cfg_v),
        .cfg_d(cfg_d), .cw_s_v(cw_v[5:0]), .cw_s_a(cw_a[71:0]), .cw_s_d(cw_d[191:0]),
        .cw_n_v(cw_v[9:6]), .cw_n_a(cw_a[119:72]), .cw_n_d(cw_d[319:192]), .fault(fault));

    // ---------------------------------------------------------------- vectors
    localparam integer MAXW = 8192, MAXA = 32768;
    integer T, NW, fs, fe, r, n, i, k, p;
    reg [1023:0] dir;
    reg [159:0] sc_d [0:65535]; reg sc_v [0:65535];
    reg [65:0] sl [0:65535][0:7];
    integer ew_e [0:MAXW-1], ew_l [0:MAXW-1], ew_p [0:MAXW-1], ew_a [0:MAXW-1], ew_la [0:MAXW-1];
    reg [31:0] ew_d [0:MAXW-1]; reg ew_hit [0:MAXW-1];
    integer ea_e [0:MAXA-1], ea_l [0:MAXA-1]; integer nA = 0, nE = 0;
    reg [8*2-1:0] kind;
    integer i0, i1, i2, i3, i4, i5, i6, i7; reg [31:0] x0, x1;
    reg [159:0] c160; integer cv;
    reg [67:0] l0, l1, l2, l3, l4, l5, l6, l7;
    integer bad = 0, extra = 0, hits = 0, abad = 0, aidx = 0;
    integer lat_min = 1 << 30, lat_max = 0; real lat_sum = 0;
    reg [1:0] dummy;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("T=%d", T)) $fatal(1, "+T");
        if (!$value$plusargs("NW=%d", NW)) $fatal(1, "+NW");
        fs = $fopen($sformatf("%0s/stim.hex", dir), "r");
        fe = $fopen($sformatf("%0s/expect.txt", dir), "r");
        if (fs == 0 || fe == 0) $fatal(1, "vector files");
        for (n = 0; n < T; n = n + 1) begin
            r = $fscanf(fs, "%d %h %h %h %h %h %h %h %h %h", cv, c160, l0, l1, l2, l3, l4, l5, l6, l7);
            sc_v[n] = cv[0]; sc_d[n] = c160;
            sl[n][0] = l0[65:0]; sl[n][1] = l1[65:0]; sl[n][2] = l2[65:0]; sl[n][3] = l3[65:0];
            sl[n][4] = l4[65:0]; sl[n][5] = l5[65:0]; sl[n][6] = l6[65:0]; sl[n][7] = l7[65:0];
        end
        while (!$feof(fe)) begin
            r = $fscanf(fe, "%s", kind);
            if (r != 1) break;
            if (kind[7:0] == "A") begin
                r = $fscanf(fe, "%d %d %h %h", i0, i1, x0, x1);
                ea_e[nA] = i0 + 1; ea_l[nA] = i1; nA = nA + 1;
            end else begin
                r = $fscanf(fe, "%d %d %d %d %h %d %d %d", i0, i1, i2, i3, x0, i4, i5, i6);
                ew_e[nE] = i0 + 2; ew_l[nE] = i1; ew_p[nE] = i2; ew_a[nE] = i3; ew_d[nE] = x0; ew_la[nE] = i6 + 1;
                ew_hit[nE] = 0; nE = nE + 1;
            end
        end
        if (nE != NW) $fatal(1, "expect rows %0d != NW %0d", nE, NW);
        for (k = 0; k < 8; k = k + 1) lw[k] = 66'd0;
        cfg_v = 0; cfg_d = 0;
        repeat (6) @(posedge clk);
        @(negedge clk); rst_n = 1;
    end
    // stimulus line n is sampled at posedge n (cyc == n after it): drive it at the negedge before
    always @(negedge clk) if (rst_n) begin
        if (cyc + 1 < T) begin
            for (k = 0; k < 8; k = k + 1) lw[k] <= sl[cyc + 1][k];
            cfg_v <= sc_v[cyc + 1]; cfg_d <= sc_d[cyc + 1];
        end else begin
            for (k = 0; k < 8; k = k + 1) lw[k] <= 66'd0;
            cfg_v <= 1'b0;
        end
    end
    // split form (S81U-CAP2): the lane pin flops live in the tree leaves, fcause in the root leaf
    wire [7:0] rvq; wire [15:0] fcause;
    generate if (MUT == 0) begin : g_h
        assign rvq = {dut.u_core.g_hard.u_te.rv_q, dut.u_core.g_hard.u_tw.rv_q}; assign fcause = dut.u_core.g_hard.u_rt.fcause;
    end else begin : g_m
        assign rvq = {dut.u_core.g_hard.u_te.rv_q, dut.u_core.g_hard.u_tw.rv_q}; assign fcause = dut.u_core.g_hard.u_rt.fcause;
    end endgenerate
    // checks: the value registered at posedge cyc is visible at the following negedge
    integer j, found;
    always @(negedge clk) if (rst_n && cyc > 0) begin
        for (k = 0; k < 8; k = k + 1)
            if (rvq[k]) begin
                if (aidx >= nA || ea_e[aidx] != cyc || ea_l[aidx] != k) begin
                    if (abad < 8) $display("ARR_MISMATCH edge %0d lane %0d (expect %0d lane %0d)", cyc, k,
                                           aidx < nA ? ea_e[aidx] : -1, aidx < nA ? ea_l[aidx] : -1);
                    abad = abad + 1;
                end
                aidx = aidx + 1;
            end
        for (k = 0; k < 5; k = k + 1)
            for (p = 0; p < 2; p = p + 1)
                if (cw_v[2 * k + p]) begin
                    found = -1;
                    for (j = 0; j < nE; j = j + 1)
                        if (found < 0 && !ew_hit[j] && ew_e[j] == cyc && ew_l[j] == k && ew_p[j] == p &&
                            ew_a[j] == cw_a[24 * k + 12 * p +: 12] && ew_d[j] == cw_d[64 * k + 32 * p +: 32]) found = j;
                    if (found < 0) begin
                        if (bad < 10) $display("WRITE_MISMATCH edge %0d leaf %0d port %0d addr %0d data %08h", cyc, k, p,
                                               cw_a[24 * k + 12 * p +: 12], cw_d[64 * k + 32 * p +: 32]);
                        bad = bad + 1;
                    end else begin
                        ew_hit[found] = 1; hits = hits + 1;
                        if (cyc - ew_la[found] < lat_min) lat_min = cyc - ew_la[found];
                        if (cyc - ew_la[found] > lat_max) lat_max = cyc - ew_la[found];
                        lat_sum = lat_sum + (cyc - ew_la[found]);
                    end
                end
        if (cyc == T + 60) begin
            for (j = 0; j < nE; j = j + 1) if (!ew_hit[j]) begin
                if (extra < 10) $display("MISSING row write edge %0d leaf %0d port %0d addr %0d", ew_e[j], ew_l[j], ew_p[j], ew_a[j]);
                extra = extra + 1;
            end
            $display("SLCAP rows %0d written_ok %0d bad_writes %0d missing %0d arrivals %0d/%0d arr_mismatch %0d fault %0d fcause %04h",
                     nE, hits, bad, extra, aidx, nA, abad, fault, fcause);
            if (hits > 0) $display("SLCAP_LATENCY last_lane_arrival_to_leaf_write edges min %0d max %0d mean %0.2f",
                                   lat_min, lat_max, lat_sum / hits);
            if (bad == 0 && extra == 0 && abad == 0 && aidx == nA && hits == nE && fault == 0) $display("PASS");
            else $display("FAIL");
            $finish;
        end
    end
endmodule
