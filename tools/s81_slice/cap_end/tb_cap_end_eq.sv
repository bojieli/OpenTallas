`timescale 1ns/1ps
// S81/PORTFIX-DEAD D-CAPEND: the end-slice capture roots vs ot_s81sl_cap #(EDLY 24, WL3DLY 16) (the capc2 / capc5r core)
// with the dropped lanes tied 0 as on the as-built die.  Lanes come from the real die return chain (dsfd_node_NNfu ->
// dsfd_rstg -> dsfd_cfifo_crs, as tb_s81sl_cap) driven by a cap_model.py vector stream; lanes >= NL carry nothing.
// Every output (cw_*, fault) compared every edge, and the root's fcause.  +DIR +T (as tb_s81sl_cap).  -GNL=3 | 6.
module tb_cap_end_eq #(parameter integer NL = 3);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg [65:0] lw [0:7];
    reg cfg_v; reg [159:0] cfg_d;
    wire [559:0] rtf, rt;
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_col
        wire [65:0] no, so; wire fo; wire [69:0] rd; wire [14:0] cc; wire [282:0] xa; wire [265:0] xb; wire [535:0] x2;
        wire rs;
        dsfd_node_NNfu u_node (.a(lw[gl]), .b(66'd0), .clk(clk), .fi(1'b0), .fo(fo), .o(no), .rst_n(rst_n));
        dsfd_rstg u_stg (.ck(clk), .i(no), .o(so), .rs(rst_n));
        dsfd_cfifo_crs u_cf (.cc(cc), .cr(clk), .cr_s(clk), .rd(rd), .ri(so), .rs(rs), .rst(rst_n), .st(2'b00),
            .xa(xa), .xb(xb), .xd(566'd0), .xf(clk), .x2(x2), .xd2(538'd0), .xf2(clk));
        assign rtf[70 * gl +: 70] = rd;
        assign rt[70 * gl +: 70] = gl < NL ? rd : 70'd0;     // the as-built die's tie
    end endgenerate
    wire [9:0] rv, vv; wire [119:0] ra, va; wire [319:0] rdd, vd; wire rf, vf;
    ot_s81sl_cap #(.EDLY(24), .WL3DLY(16)) u_ref (.clk(clk), .rst_n(rst_n), .rt_w(rt[279:0]), .rt_e(rt[559:280]),
        .cfg_v(cfg_v), .cfg_d(cfg_d), .cw_s_v(rv[5:0]), .cw_s_a(ra[71:0]), .cw_s_d(rdd[191:0]),
        .cw_n_v(rv[9:6]), .cw_n_a(ra[119:72]), .cw_n_d(rdd[319:192]), .fault(rf));
    wire [15:0] rfc = u_ref.g_hard.u_rt.fcause, vfc;
    generate if (NL == 3) begin : g_w3
        ot_s81sl_cap_w3 u_var (.clk(clk), .rst_n(rst_n), .rt_w(rt[209:0]),
            .cfg_v(cfg_v), .cfg_d(cfg_d), .cw_s_v(vv[5:0]), .cw_s_a(va[71:0]), .cw_s_d(vd[191:0]),
            .cw_n_v(vv[9:6]), .cw_n_a(va[119:72]), .cw_n_d(vd[319:192]), .fault(vf));
        assign vfc = u_var.u_rt.fcause;
    end else begin : g_e6
        ot_s81sl_cap_e6 u_var (.clk(clk), .rst_n(rst_n), .rt_w(rt[279:0]), .rt_e(rt[419:280]),
            .cfg_v(cfg_v), .cfg_d(cfg_d), .cw_s_v(vv[5:0]), .cw_s_a(va[71:0]), .cw_s_d(vd[191:0]),
            .cw_n_v(vv[9:6]), .cw_n_a(va[119:72]), .cw_n_d(vd[319:192]), .fault(vf));
        assign vfc = u_var.u_rt.fcause;
    end endgenerate
    integer T, fs, r, n, k, cv, mism = 0, nv = 0, lw_n = 0;
    reg [1023:0] dir;
    reg [159:0] sc_d [0:65535]; reg sc_v [0:65535];
    reg [65:0] sl [0:65535][0:7];
    reg [159:0] c160; reg [67:0] l0, l1, l2, l3, l4, l5, l6, l7;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("T=%d", T)) $fatal(1, "+T");
        fs = $fopen($sformatf("%0s/stim.hex", dir), "r");
        if (fs == 0) $fatal(1, "stim");
        for (n = 0; n < T; n = n + 1) begin
            r = $fscanf(fs, "%d %h %h %h %h %h %h %h %h %h", cv, c160, l0, l1, l2, l3, l4, l5, l6, l7);
            sc_v[n] = cv[0]; sc_d[n] = c160;
            sl[n][0] = l0[65:0]; sl[n][1] = l1[65:0]; sl[n][2] = l2[65:0]; sl[n][3] = l3[65:0];
            sl[n][4] = l4[65:0]; sl[n][5] = l5[65:0]; sl[n][6] = l6[65:0]; sl[n][7] = l7[65:0];
        end
        for (k = 0; k < 8; k = k + 1) lw[k] = 66'd0;
        cfg_v = 0; cfg_d = 0;
        repeat (6) @(posedge clk);
        @(negedge clk); rst_n = 1;
        repeat (T + 400) @(posedge clk);
        $display("CAP_END_EQ NL=%0d %s edges %0d lane_words %0d cw_valid_edges %0d fault %b/%b fcause %h/%h mismatches %0d",
                 NL, (mism == 0 && nv > 0) ? "PASS" : "FAIL", T + 400, lw_n, nv, rf, vf, rfc, vfc, mism);
        $finish;
    end
    always @(negedge clk) if (rst_n) begin
        if (cyc + 1 < T) begin
            for (k = 0; k < 8; k = k + 1) lw[k] <= sl[cyc + 1][k];
            cfg_v <= sc_v[cyc + 1]; cfg_d <= sc_d[cyc + 1];
        end else begin
            for (k = 0; k < 8; k = k + 1) lw[k] <= 66'd0;
            cfg_v <= 1'b0;
        end
    end
    always @(negedge clk) if (rst_n) begin
        for (k = 0; k < NL; k = k + 1) if (rt[70 * k + 1]) lw_n = lw_n + 1;
        if (|rv) nv = nv + 1;
        if (rv !== vv || ra !== va || rdd !== vd || rf !== vf || rfc !== vfc) begin
            mism = mism + 1;
            if (mism < 8) $display("MISMATCH edge %0d v %h/%h f %b/%b fc %h/%h", cyc, rv, vv, rf, vf, rfc, vfc);
        end
    end
endmodule
