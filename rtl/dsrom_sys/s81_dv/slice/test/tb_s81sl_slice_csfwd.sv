`timescale 1ns/1ps
// PATH-S81 X2 (10-25): exact lockstep miter for the per-leaf CS forwarding of ot_s81sl_slice.  u_a = the slice of the
// base commit (origin/main, every module renamed O_*: no R3 station mechanism, module-scope vp loop integers), u_b = this
// branch's slice (R3 station chains + LF_CS_* forwarding + block-local vp integers).  Random ring / V / band / return
// inputs every cycle (tb_s81sl_slice_x stimulus), every output compared every cycle after reset.
//   MUT 0: u_b at its defaults                           -> must PASS (byte / cycle identical)
//   MUT 1: u_b leaf 2 LF_CS_U_D = 1 (vs -> vq station)    -> must FAIL (forwarding reaches the leaf)
//   MUT 2: u_b leaf 0 LF_CS_HI_D = 2 (vp lane inputs)     -> must FAIL
//   MUT 3: u_b every leaf the named normal-leaf CS set    -> must FAIL (public behaviour moves; latencies: leaf benches)
// +define+OT_S81SL_CST_MUT_UV with MUT 0 (u_v one station off its interface) is the R3 station mutant.
module tb_s81sl_slice_csfwd;
    parameter integer HB = 0;
    parameter integer MUT = 0;
    parameter integer CYC = 4000;
    parameter integer SEED = 1;
    localparam [19:0] N1 = 20'h11111, N2 = 20'h22222, N4 = 20'h44444;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [1103:0] ri_w, ri_e, bi; reg [275:0] vi; reg [559:0] rt;
    wire [1103:0] ro_e_a, ro_w_a, ro_e_b, ro_w_b; wire [512:0] bo_a, bo_b; wire [275:0] vo_a, vo_b; wire [4415:0] xc_a, xc_b;
    wire [15:0] cl_a, cl_b, cx_a, cx_b; wire [1:0] cv_a, cv_b; wire [7:0] cr_a, cr_b; wire f_a, f_b;
    O_ot_s81sl_slice #(.HB(HB)) u_a (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_a),
        .ro_w(ro_w_a), .vi(vi), .vo(vo_a), .bi(bi), .bo(bo_a), .xc(xc_a), .rt(rt), .ck_line(cl_a), .ck_v(cv_a), .ck_xc(cx_a),
        .ck_rt(cr_a), .fault(f_a));
    generate if (MUT == 0) begin : g_m0
        ot_s81sl_slice #(.HB(HB)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_b),
            .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b), .ck_v(cv_b),
            .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else if (MUT == 1) begin : g_m1
        ot_s81sl_slice #(.HB(HB), .LF_CS_U_D(20'h00100)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e),
            .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b),
            .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else if (MUT == 2) begin : g_m2
        ot_s81sl_slice #(.HB(HB), .LF_CS_HI_D(20'h00002)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e),
            .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b),
            .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else begin : g_m3
        ot_s81sl_slice #(.HB(HB), .LF_CS_HI_D(N2), .LF_CS_HO_D(N2), .LF_CS_H_G(N4), .LF_CS_PVS_D(N1), .LF_CS_SWR_D(N1),
            .LF_CS_U_D(N1), .LF_CS_VNI_D(N1), .LF_CS_VSP_D(N1), .LF_CS_Y_D(N1)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3),
            .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt),
            .ck_line(cl_b), .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end endgenerate
    wire [11041:0] oa = {ro_e_a, ro_w_a, bo_a, vo_a, xc_a, f_a};
    wire [11041:0] ob = {ro_e_b, ro_w_b, bo_b, vo_b, xc_b, f_b};
    wire [41:0] ka = {cl_a, cx_a, cv_a, cr_a}, kb = {cl_b, cx_b, cv_b, cr_b};
    integer cyc, bad, nc, j, act, first, fcyc; reg [11041:0] prev;
    task rnd; begin
        for (j = 0; j < 35; j = j + 1) begin ri_w[32*j +: 32] = $urandom; ri_e[32*j +: 32] = $urandom; bi[32*j +: 32] = $urandom; end
        for (j = 0; j < 9; j = j + 1) vi[32*j +: 32] = $urandom;
        for (j = 0; j < 18; j = j + 1) rt[32*j +: 32] = $urandom;
    end endtask
    initial begin
        j = $urandom(SEED);
        bad = 0; nc = 0; act = 0; prev = 0; first = -1; fcyc = -1; ri_w = 0; ri_e = 0; bi = 0; vi = 0; rt = 0;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 8) rst_n = 1'b1;
            rnd;
            if (cyc > 10) begin
                nc = nc + 1; if (oa[11041:1] !== prev[11041:1]) act = act + 1; prev = oa;
                if (f_a && fcyc < 0) fcyc = cyc;
                if (oa !== ob || ka !== kb) begin
                    bad = bad + 1; if (first < 0) first = cyc;
                    if (bad <= 5) $display("CSF_MISMATCH cycle=%0d ro_e %0d ro_w %0d bo %0d vo %0d xc %0d f %0d ck %0d", cyc,
                        ro_e_a !== ro_e_b, ro_w_a !== ro_w_b, bo_a !== bo_b, vo_a !== vo_b, xc_a !== xc_b, f_a !== f_b, ka !== kb);
                end
            end
        end
        if (bad == 0) $display("CSF PASS HB=%0d MUT=%0d SEED=%0d compared=%0d cycles output_changes=%0d first_fault=%0d", HB, MUT,
            SEED, nc, act, fcyc);
        else $display("CSF FAIL HB=%0d MUT=%0d SEED=%0d mismatches=%0d of %0d first=%0d output_changes=%0d", HB, MUT, SEED, bad,
            nc, first, act);
        $finish;
    end
endmodule
