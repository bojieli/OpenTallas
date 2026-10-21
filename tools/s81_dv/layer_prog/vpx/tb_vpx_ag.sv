`timescale 1ns/1ps
// LB2-S81/CC fork VPX (10-18): end-slice collective vehicle for the compiled all-gather legs (lower_vpx.py).
// Die A = ot_s81sl_slice_lepw (u_s_0S master, sid strap SA = die.v 0), die B = ot_s81sl_slice_lepe_nh (u_s_7S master of the
// W peer die, sid strap SB = die.v 14), the 2 x 2 link lanes cross-wired through ot_pdie_ucie (as tb_s81sl_slice_lep).
// Stimulus = the compiler's CTL beats (and the bench's preload / read-back beats) on the slices' INWARD line pins at their
// compiled cycles: file STIM, lines "<cycle> <port 0 = A ri_e, 1 = B ri_w> <1104-b beat hex>".  The bench only drives
// pins and prints what the real RTL does; check_vpx_ag.py compares it with the compiler's expectations.
// Log records (cycle = bench edge count, a value printed at edge c is the value the flops sample at edge c):
//   SEND <die> <cyc> <beat>     beat leaving the slice's outward port into the lep (u.lro)
//   LRI  <die> <cyc> <beat>     beat from the lep into the slice's outward input (u.lri)
//   CTL  <die> <cyc> <tgt>      xr CTL decode (cvld) for this slice
//   LO   <die> <cyc> <mask>     xr lo pair input valid (RDOUT pairs at the centre)
//   WR   <die> <cyc> <leaf> <row> <mask> <data256>   xr row-pair write to a beat leaf (RD unpack / CTL row write)
//   OUT  <die> <cyc> <beat>     beat on the bench-facing inward output (A ro_e / B ro_w)
//   FAULT <die> <cyc>           first cycle a slice fault is high
module tb_vpx_ag #(parameter integer SA = 0, parameter integer SB = 14, parameter integer NMAX = 4096);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] a_in = 0, b_in = 0; wire [1103:0] a_out, b_out;
    wire a_f, b_f;
    wire [511:0] atx0, atx1, btx0, btx1, arx0, arx1, brx0, brx1; wire [1:0] ast0, ast1, bst0, bst1;
    wire [512:0] pa0, pa1, pb0, pb1; wire ta0, ta1, tb0, tb1;
    ot_s81sl_slice_lepw A (.clk(clk), .rst_n(rst_n), .sid(SA[3:0]), .ri_e(a_in), .ro_e(a_out), .vi(276'd0), .vo(), .bi(1104'd0),
        .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(1'b0), .tx0(atx0), .tx1(atx1),
        .rx0({ast0, arx0}), .rx1({ast1, arx1}), .tf(), .fault(a_f));
    ot_s81sl_slice_lepe_nh B (.clk(clk), .rst_n(rst_n), .sid(SB[3:0]), .ri_w(b_in), .ro_w(b_out), .vi(276'd0), .vo(), .bi(1104'd0),
        .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(1'b0), .tx0(btx0), .tx1(btx1),
        .rx0({bst0, brx0}), .rx1({bst1, brx1}), .tf(), .fault(b_f));
    ot_pdie_ucie #(.PMA_LAT(2)) ua0 (.clk(clk), .rst(rst_n), .tx(atx0), .rx(arx0), .st(ast0), .pma_tx(pa0), .pma_tck(ta0), .pma_rx(pb0), .pma_rck(tb0));
    ot_pdie_ucie #(.PMA_LAT(2)) ub0 (.clk(clk), .rst(rst_n), .tx(btx0), .rx(brx0), .st(bst0), .pma_tx(pb0), .pma_tck(tb0), .pma_rx(pa0), .pma_rck(ta0));
    ot_pdie_ucie #(.PMA_LAT(5)) ua1 (.clk(clk), .rst(rst_n), .tx(atx1), .rx(arx1), .st(ast1), .pma_tx(pa1), .pma_tck(ta1), .pma_rx(pb1), .pma_rck(tb1));
    ot_pdie_ucie #(.PMA_LAT(5)) ub1 (.clk(clk), .rst(rst_n), .tx(btx1), .rx(brx1), .st(bst1), .pma_tx(pb1), .pma_tck(tb1), .pma_rx(pa1), .pma_rck(ta1));

    // ---------------------------------------------------------------- stimulus
    integer st_c [0:NMAX-1]; integer st_p [0:NMAX-1]; reg [1103:0] st_b [0:NMAX-1];
    integer ns = 0, si = 0, cyc = 0, endc = 0, fd, r, c, p, af = 0, bf = 0;
    reg [1103:0] bb;
    reg [8*256-1:0] fn;
    initial begin
        if (!$value$plusargs("STIM=%s", fn)) begin $display("FAIL no +STIM"); $finish; end
        fd = $fopen(fn, "r");
        if (fd == 0) begin $display("FAIL cannot open STIM"); $finish; end
        r = $fscanf(fd, "END %d\n", endc);
        while (!$feof(fd) && ns < NMAX) begin
            r = $fscanf(fd, "%d %d %h\n", c, p, bb);
            if (r == 3) begin st_c[ns] = c; st_p[ns] = p; st_b[ns] = bb; ns = ns + 1; end
        end
        $fclose(fd);
        $display("STIM %0d beats, end %0d", ns, endc);
    end
    always @(posedge clk) cyc <= cyc + 1;
    always @(negedge clk) begin
        a_in <= 1104'd0; b_in <= 1104'd0;
        while (si < ns && st_c[si] == cyc) begin
            if (st_p[si] == 0) a_in <= st_b[si]; else b_in <= st_b[si];
            si = si + 1;
        end
        if (si < ns && st_c[si] < cyc) begin $display("FAIL stimulus out of order at %0d", si); $finish; end
    end
    initial begin
        repeat (8) @(posedge clk); rst_n = 1;
    end

    // ---------------------------------------------------------------- monitors
    integer k;
    always @(posedge clk) if (rst_n) begin
        if (A.u.lro[0]) $display("SEND A %0d %h", cyc, A.u.lro);
        if (B.u.lro[0]) $display("SEND B %0d %h", cyc, B.u.lro);
        if (A.u.lri[0]) $display("LRI A %0d %h", cyc, A.u.lri);
        if (B.u.lri[0]) $display("LRI B %0d %h", cyc, B.u.lri);
        if (A.u.g_w.u_sl.g_c1.u_xr.u.cvld) $display("CTL A %0d %0d", cyc, A.u.g_w.u_sl.g_c1.u_xr.u.tg[4] ? 4 : A.u.g_w.u_sl.g_c1.u_xr.u.tg[0] ? 0 : A.u.g_w.u_sl.g_c1.u_xr.u.tg[2] ? 2 : A.u.g_w.u_sl.g_c1.u_xr.u.tg[3] ? 3 : A.u.g_w.u_sl.g_c1.u_xr.u.tg[1] ? 1 : 5);  // TOK2: post-XR2 stage-1 (tg one-hot)
        if (B.u.g_e.u_sl.g_c1.u_xr.u.cvld) $display("CTL B %0d %0d", cyc, B.u.g_e.u_sl.g_c1.u_xr.u.tg[4] ? 4 : B.u.g_e.u_sl.g_c1.u_xr.u.tg[0] ? 0 : B.u.g_e.u_sl.g_c1.u_xr.u.tg[2] ? 2 : B.u.g_e.u_sl.g_c1.u_xr.u.tg[3] ? 3 : B.u.g_e.u_sl.g_c1.u_xr.u.tg[1] ? 1 : 5);  // TOK2: post-XR2 stage-1 (tg one-hot)
        if (|A.u.g_w.u_sl.g_c1.u_xr.u.lov1) $display("LO A %0d %b", cyc, A.u.g_w.u_sl.g_c1.u_xr.u.lov1);  // TOK2: post-XR2 packer-side lo (lov1)
        if (|B.u.g_e.u_sl.g_c1.u_xr.u.lov1) $display("LO B %0d %b", cyc, B.u.g_e.u_sl.g_c1.u_xr.u.lov1);  // TOK2: post-XR2 packer-side lo (lov1)
        for (k = 0; k < 5; k = k + 1) begin
            if (A.u.g_w.u_sl.sw_v_x[k]) $display("WR A %0d %0d %0d %h %h", cyc, k, A.u.g_w.u_sl.sw_a_x[10 * k +: 10],
                                                 A.u.g_w.u_sl.sw_m_x[8 * k +: 8], A.u.g_w.u_sl.sw_d_x[256 * k +: 256]);
            if (B.u.g_e.u_sl.sw_v_x[k]) $display("WR B %0d %0d %0d %h %h", cyc, k, B.u.g_e.u_sl.sw_a_x[10 * k +: 10],
                                                 B.u.g_e.u_sl.sw_m_x[8 * k +: 8], B.u.g_e.u_sl.sw_d_x[256 * k +: 256]);
        end
        if (a_out[0]) $display("OUT A %0d %h", cyc, a_out);
        if (b_out[0]) $display("OUT B %0d %h", cyc, b_out);
        if (a_f && !af) begin af = 1; $display("FAULT A %0d", cyc); end
        if (b_f && !bf) begin bf = 1; $display("FAULT B %0d", cyc); end
        if (endc > 0 && cyc == endc) begin $display("DONE %0d faultA %0d faultB %0d", cyc, a_f, b_f); $finish; end
    end
endmodule
