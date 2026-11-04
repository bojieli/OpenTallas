`timescale 1ns/1ps
// tb_s81sl_xrt_rland_eq (DIE-S81-51/RF-B RE-FORM 11-03): RING_LAND of ot_s81sl_xrt is a pure +1-edge delay of the ring /
// band inputs dl_ev dl_e dl_wv dl_w dl_vv dl_vb bi.  DUT = ot_s81sl_xrt1 / xrt3 (HB) with RING_LAND = RL (FACE_LAND 1, and
// the XR8 pin predecode OT_S81SL_XR_PDC when the build defines it: it then reads the landing flops); REF = origin/main
// text (renamed ref_s81sl_xrt*, its OT_S81SL_XR_PDC renamed away so the REF is the plain non-predecode module) fed those
// 7 inputs through bench delay registers when RL = 1 (both FACE_LAND 1: LAND must be 0 here, the lo / p / e inputs are shared).  Every output bit compared every cycle (same stimulus as
// tb_s81sl_xrt_land_eq, from which this is derived; OL = 1: DUT out-face lockup latches, ports compared in the low
// phase and required to hold that value through the next high phase; the REF gets the same narrowed RTLC ports as the DUT).  Prints LANDEQ ... and PASS / FAIL.
module tb_s81sl_xrt_rland_eq #(parameter integer HB = 0, parameter integer LAND = 1, parameter integer RL = 1, parameter integer OL = 1, parameter integer SEED = 1,
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
    reg r_ev = 0, r_wv = 0, r_vv = 0; reg [W-1:0] r_e = 0, r_w = 0, r_bi = 0; reg [V-1:0] r_vb = 0;
    always @(posedge clk) begin r_ev <= dl_ev; r_wv <= dl_wv; r_vv <= dl_vv; r_e <= dl_e; r_w <= dl_w; r_bi <= bi; r_vb <= dl_vb; end
    wire g_ev = RL ? r_ev : dl_ev, g_wv = RL ? r_wv : dl_wv, g_vv = RL ? r_vv : dl_vv;
    wire [W-1:0] g_e = RL ? r_e : dl_e, g_w = RL ? r_w : dl_w, g_bi = RL ? r_bi : bi; wire [V-1:0] g_vb = RL ? r_vb : dl_vb;
    // all outputs packed: {ci_dir, ci_b, bo, c_v, c_d, sw_v, sw_a, sw_m, sw_d, rb_v, rb_d, g_v, g_c, g_d, x_go, x_mode,
    //                      x_eps, x_scale, x_sv, x_si, x_s, is_v, is_d, cfg_v, cfg_d, fault}
    localparam integer OW = 3 + W + 513 + 5 + 160 + 5 + 50 + 40 + 1280 + 1 + 32 + 1 + 2 + 32 + 1 + 1 + 32 + 32 + 1 + 8 + 32
                            + 1 + 160 + 1 + 160 + 1;
    wire [OW-1:0] od, orf;
    `define XRT_PORTS(P, LV, LD, PV, PD, EV, EC, ED, DE, DW, DV, CB, XS, EVV, WVV, VVV) \
        .clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(EVV), .dl_e(DE), .dl_wv(WVV), .dl_w(DW), .dl_vv(VVV), \
        .dl_vb(DV), .ci_dir(P[OW-1 -: 3]), .ci_b(CB), .c_v(P[OW-4-W-513 -: 5]), \
        .c_d(P[OW-9-W-513 -: 160]), .sw_v(P[OW-169-W-513 -: 5]), .sw_a(P[OW-174-W-513 -: 50]), .sw_m(P[OW-224-W-513 -: 40]), \
        .sw_d(P[OW-264-W-513 -: 1280]), .lo_v(LV), .lo_d(LD), .p_v(PV), .p_d(PD), .rb_v(P[OW-1544-W-513]), \
        .rb_d(P[OW-1545-W-513 -: 32]), .e_v(EV), .e_c(EC), .e_d(ED), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), \
        .g_v(P[OW-1577-W-513]), .g_c(P[OW-1578-W-513 -: 2]), .g_d(P[OW-1580-W-513 -: 32]), .x_go(P[OW-1612-W-513]), \
        .x_mode(P[OW-1613-W-513]), .x_eps(P[OW-1614-W-513 -: 32]), .x_scale(P[OW-1646-W-513 -: 32]), \
        .x_sv(P[OW-1678-W-513]), .x_si(XS), .x_s(P[OW-1687-W-513 -: 32]), .x_rbv(x_rbv), .x_rbd(x_rbd), \
        .is_v(P[OW-1719-W-513]), .is_d(P[OW-1720-W-513 -: 160]), .cfg_v(P[OW-1880-W-513]), .cfg_d(P[OW-1881-W-513 -: 160]), \
        .fault(P[0])
    generate if (HB != 0) begin : g3
        ot_s81sl_xrt3 #(.FACE_LAND(1), .RING_LAND(RL), .OLAT(OL)) dut (`XRT_PORTS(od, lo_v, lo_d, p_v, p_d, e_v, e_c, e_d, dl_e[1075:1], dl_w[1075:1],
            dl_vb[275:1], od[OW-4-28 -: W-28], od[OW-1680-W-513 -: 7], dl_ev, dl_wv, dl_vv), .bi({bi[1075:37], bi[6:0]}), .bo(od[OW-4-W -: 513]));
        ref_s81sl_xrt3 rf (`XRT_PORTS(orf, f_lo_v, f_lo_d, f_p_v, f_p_d, f_e_v, f_e_c, f_e_d, g_e[1075:1], g_w[1075:1],
            g_vb[275:1], orf[OW-4-28 -: W-28], orf[OW-1680-W-513 -: 7], g_ev, g_wv, g_vv), .bi({g_bi[1075:37], g_bi[6:0]}), .bo(orf[OW-4-W -: 513]));
    end else begin : g1
        ot_s81sl_xrt1 #(.FACE_LAND(1), .RING_LAND(RL), .OLAT(OL)) dut (`XRT_PORTS(od, lo_v, lo_d, p_v, p_d, e_v, e_c, e_d, dl_e[1075:1], dl_w[1075:1],
            dl_vb[275:1], od[OW-4-28 -: W-28], od[OW-1680-W-513 -: 7], dl_ev, dl_wv, dl_vv));
        ref_s81sl_xrt1 rf (`XRT_PORTS(orf, f_lo_v, f_lo_d, f_p_v, f_p_d, f_e_v, f_e_c, f_e_d, g_e[1075:1], g_w[1075:1],
            g_vb[275:1], orf[OW-4-28 -: W-28], orf[OW-1680-W-513 -: 7], g_ev, g_wv, g_vv));
        assign od[OW-4-W -: 513] = 513'd0; assign orf[OW-4-W -: 513] = 513'd0;
    end endgenerate
    assign od[OW-4 -: 28] = 28'd0; assign od[OW-1679-W-513] = 1'b0;
    assign orf[OW-4 -: 28] = 28'd0; assign orf[OW-1679-W-513] = 1'b0;   // RF-B: REF has the same narrowed ports   // dropped constant pins (ci_b[1103:1076], x_si[7])
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
    // OL = 1: in the high phase the ports must HOLD the low-phase value (negative-level latch), checked 0.1 after posedge
    reg [OW-1:0] orf_h; reg armed = 1'b0; integer herr = 0;
    // orf_h = the REF ports just before the rising edge (after any mid-cycle async reset change in the low phase)
    always @(negedge clk) begin #0.45; orf_h = orf; end
    always @(posedge clk) if (OL != 0 && armed) begin #0.1; if (od !== orf_h) herr = herr + 1; end
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
            @(negedge clk); #0.1;   // OL: out-face latches are transparent in the low phase
            ncmp = ncmp + 1; nflt = nflt + od[0]; nxs = nxs + od[OW-1678-W-513]; nsend = nsend + od[OW-3-W];
            armed = 1'b1;
            if (od !== orf) begin
                err = err + 1;
                if (err < 6) $display("LANDEQ MISMATCH cycle %0d diff bits %0d (fault dut %b ref %b, x_sv %b %b)", n,
                                      $countones(od ^ orf), od[0], orf[0], od[OW-1678-W-513], orf[OW-1678-W-513]);
            end
        end
        $display("LANDEQ ol=%0d herr=%0d rl=%0d hb=%0d land=%0d seed=%0d cycles=%0d lo=%0d p=%0d e=%0d fault_cycles=%0d xs_cycles=%0d ci_cycles=%0d err=%0d",
                 OL, herr, RL, HB, LAND, SEED, ncmp, nlo, np, ne, nflt, nxs, nsend, err);
        if (err == 0 && herr == 0 && nxs > 100 && nsend > (SPARSE ? 20 : 100) && nflt < ncmp) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
