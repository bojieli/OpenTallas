`timescale 1ns/1ps
// tb_s81sl_xrt_land_eq (S81-KITS-RTLB 10-24): the FACE_LAND landing stage of ot_s81sl_xrt is a pure +1-edge delay of the
// beat-leaf / Engram inputs lo_v lo_d p_v p_d e_v e_c e_d.  DUT = ot_s81sl_xrt1 / xrt3 (HB) with FACE_LAND = LAND; REF =
// the pre-fix module (origin/main text, renamed ref_s81sl_xrt*) fed those 7 inputs through bench delay registers when
// LAND = 1 (undelayed when LAND = 0).  Every other input is shared.  Random stimulus (beats of every kind with the own
// slice mask half the time, sparse leaf / partial / Engram valids, warm resets every RP cycles); EVERY output bit is
// compared every cycle after the first reset release.  Prints LANDEQ ... and PASS / FAIL.
module tb_s81sl_xrt_land_eq #(parameter integer HB = 0, parameter integer LAND = 1, parameter integer SEED = 1,
                              parameter integer NC = 20000, parameter integer RP = 997,
                              parameter integer SPARSE = 0);   // SPARSE = 1: rare full-set valids, few faults
    localparam integer W = 1104, V = 276;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0; reg [3:0] sid = 4'd0;
    reg dl_ev = 0, dl_wv = 0, dl_vv = 0; reg [W-1:0] dl_e = 0, dl_w = 0, bi = 0; reg [V-1:0] dl_vb = 0;
    reg [4:0] lo_v = 0, p_v = 0, e_v = 0; reg [1279:0] lo_d = 0; reg [159:0] p_d = 0; reg [9:0] e_c = 0; reg [479:0] e_d = 0;
    reg x_rbv = 0; reg [31:0] x_rbd = 0; reg eg_v = 0; reg [1:0] eg_c = 0; reg [31:0] eg_d = 0;
    // reference inputs: one edge later when LAND = 1
    reg [4:0] r_lo_v = 0, r_p_v = 0, r_e_v = 0; reg [1279:0] r_lo_d = 0; reg [159:0] r_p_d = 0; reg [9:0] r_e_c = 0;
    reg [479:0] r_e_d = 0;
    always @(posedge clk) begin r_lo_v <= lo_v; r_p_v <= p_v; r_e_v <= e_v; r_lo_d <= lo_d; r_p_d <= p_d; r_e_c <= e_c; r_e_d <= e_d; end
    wire [4:0] f_lo_v = LAND ? r_lo_v : lo_v, f_p_v = LAND ? r_p_v : p_v, f_e_v = LAND ? r_e_v : e_v;
    wire [1279:0] f_lo_d = LAND ? r_lo_d : lo_d; wire [159:0] f_p_d = LAND ? r_p_d : p_d;
    wire [9:0] f_e_c = LAND ? r_e_c : e_c; wire [479:0] f_e_d = LAND ? r_e_d : e_d;
    // all outputs packed: {ci_dir, ci_b, bo, c_v, c_d, sw_v, sw_a, sw_m, sw_d, rb_v, rb_d, g_v, g_c, g_d, x_go, x_mode,
    //                      x_eps, x_scale, x_sv, x_si, x_s, is_v, is_d, cfg_v, cfg_d, fault}
    localparam integer OW = 3 + W + 513 + 5 + 160 + 5 + 50 + 40 + 1280 + 1 + 32 + 1 + 2 + 32 + 1 + 1 + 32 + 32 + 1 + 8 + 32
                            + 1 + 160 + 1 + 160 + 1;
    wire [OW-1:0] od, orf;
    `define XRT_PORTS(P, LV, LD, PV, PD, EV, EC, ED) \
        .clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w), .dl_vv(dl_vv), \
        .dl_vb(dl_vb), .ci_dir(P[OW-1 -: 3]), .ci_b(P[OW-4 -: W]), .c_v(P[OW-4-W-513 -: 5]), \
        .c_d(P[OW-9-W-513 -: 160]), .sw_v(P[OW-169-W-513 -: 5]), .sw_a(P[OW-174-W-513 -: 50]), .sw_m(P[OW-224-W-513 -: 40]), \
        .sw_d(P[OW-264-W-513 -: 1280]), .lo_v(LV), .lo_d(LD), .p_v(PV), .p_d(PD), .rb_v(P[OW-1544-W-513]), \
        .rb_d(P[OW-1545-W-513 -: 32]), .e_v(EV), .e_c(EC), .e_d(ED), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), \
        .g_v(P[OW-1577-W-513]), .g_c(P[OW-1578-W-513 -: 2]), .g_d(P[OW-1580-W-513 -: 32]), .x_go(P[OW-1612-W-513]), \
        .x_mode(P[OW-1613-W-513]), .x_eps(P[OW-1614-W-513 -: 32]), .x_scale(P[OW-1646-W-513 -: 32]), \
        .x_sv(P[OW-1678-W-513]), .x_si(P[OW-1679-W-513 -: 8]), .x_s(P[OW-1687-W-513 -: 32]), .x_rbv(x_rbv), .x_rbd(x_rbd), \
        .is_v(P[OW-1719-W-513]), .is_d(P[OW-1720-W-513 -: 160]), .cfg_v(P[OW-1880-W-513]), .cfg_d(P[OW-1881-W-513 -: 160]), \
        .fault(P[0])
    generate if (HB != 0) begin : g3
        ot_s81sl_xrt3 #(.FACE_LAND(LAND)) dut (`XRT_PORTS(od, lo_v, lo_d, p_v, p_d, e_v, e_c, e_d), .bi(bi), .bo(od[OW-4-W -: 513]));
        ref_s81sl_xrt3 rf (`XRT_PORTS(orf, f_lo_v, f_lo_d, f_p_v, f_p_d, f_e_v, f_e_c, f_e_d), .bi(bi), .bo(orf[OW-4-W -: 513]));
    end else begin : g1
        ot_s81sl_xrt1 #(.FACE_LAND(LAND)) dut (`XRT_PORTS(od, lo_v, lo_d, p_v, p_d, e_v, e_c, e_d));
        ref_s81sl_xrt1 rf (`XRT_PORTS(orf, f_lo_v, f_lo_d, f_p_v, f_p_d, f_e_v, f_e_c, f_e_d));
        assign od[OW-4-W -: 513] = 513'd0; assign orf[OW-4-W -: 513] = 513'd0;
    end endgenerate
    reg [63:0] rs;
    function automatic [31:0] r32(); rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); r32 = rs[31:0]; endfunction
    function automatic [1279:0] rw(); integer q; for (q = 0; q < 40; q = q + 1) rw[32 * q +: 32] = r32(); endfunction
    function automatic [W-1:0] beat(input integer pmine);
        reg [1279:0] t; begin
            t = rw(); beat = t[W-1:0]; beat[0] = 1'b1;
            if (r32() % 100 < pmine) beat[21 + sid] = 1'b1;
            if (r32() % 4 == 0) beat[37 +: 5] = r32() % 6;          // legal CTL targets most of the time
        end
    endfunction
    integer n, err = 0, ncmp = 0, nlo = 0, np = 0, ne = 0, nflt = 0, nxs = 0, nsend = 0;
    reg [1279:0] t;
    initial begin
        rs = 64'h9e3779b97f4a7c15 ^ SEED; for (n = 0; n < 8; n = n + 1) t = r32();
        sid = r32() % 16;
        repeat (6) @(negedge clk);
        rst_n = 1'b1;
        for (n = 0; n < NC; n = n + 1) begin
            if (n % RP == RP - 1) rst_n = 1'b0; else if (n % RP == 2) rst_n = 1'b1;
            dl_ev = r32() % 100 < (SPARSE ? 3 : 20); dl_e = beat(SPARSE ? 10 : 60); dl_wv = r32() % 100 < (SPARSE ? 3 : 15);
            dl_w = beat(SPARSE ? 10 : 60);
            dl_vv = r32() % 100 < (SPARSE ? 2 : 12); t = rw(); dl_vb = beat(50); bi = beat(50); bi[0] = r32() % 100 < (SPARSE ? 1 : 10);
            lo_v = (r32() % 100 < (SPARSE ? 4 : 25)) ? (5'd1 << (r32() % 5)) : ((!SPARSE && r32() % 100 < 3) ? r32() : 5'd0);
            lo_d = rw();
            p_v = (r32() % 100 < (SPARSE ? 1 : 6)) ? 5'b11111 : ((!SPARSE && r32() % 100 < 2) ? r32() : 5'd0); t = rw(); p_d = t[159:0];
            e_v = (r32() % 100 < (SPARSE ? 1 : 6)) ? 5'b11111 : ((!SPARSE && r32() % 100 < 2) ? r32() : 5'd0); t = rw(); e_d = t[479:0];
            e_c = (r32() % 2) ? {5{t[481:480]}} : t[491:482];
            eg_v = r32() % 100 < 8; eg_c = r32(); eg_d = r32();
            x_rbv = r32() % 100 < 10; x_rbd = r32();
            nlo = nlo + (lo_v != 0); np = np + (p_v != 0); ne = ne + (e_v != 0);
            @(negedge clk);
            ncmp = ncmp + 1; nflt = nflt + od[0]; nxs = nxs + od[OW-1678-W-513]; nsend = nsend + od[OW-3-W];
            if (od !== orf) begin
                err = err + 1;
                if (err < 6) $display("LANDEQ MISMATCH cycle %0d diff bits %0d (fault dut %b ref %b, x_sv %b %b)", n,
                                      $countones(od ^ orf), od[0], orf[0], od[OW-1678-W-513], orf[OW-1678-W-513]);
            end
        end
        $display("LANDEQ hb=%0d land=%0d seed=%0d cycles=%0d lo=%0d p=%0d e=%0d fault_cycles=%0d xs_cycles=%0d ci_cycles=%0d err=%0d",
                 HB, LAND, SEED, ncmp, nlo, np, ne, nflt, nxs, nsend, err);
        if (err == 0 && nxs > 100 && nsend > (SPARSE ? 20 : 100) && nflt < ncmp) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
