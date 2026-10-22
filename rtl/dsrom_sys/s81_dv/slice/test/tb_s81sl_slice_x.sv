`timescale 1ns/1ps
// PL-SLICE (10-18): the wires-only flat slice ot_s81sl_slice_c{1,3}x (tools/s81_slice/slice_flat_gen.py) is cycle-identical
// to the original ot_s81sl_slice #(.HB(HB)) -- random ring / V / band / return inputs every cycle, every output compared
// every cycle after reset.  MUT 1 (negative control): leaf 0 relay depth DLK0 = 5 must FAIL.
module tb_s81sl_slice_x;
    parameter integer HB = 0;
    parameter integer MUT = 0;
    parameter integer CYC = 3000;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [1103:0] ri_w, ri_e, bi; reg [275:0] vi; reg [559:0] rt;
    wire [1103:0] ro_e_a, ro_w_a, ro_e_b, ro_w_b; wire [512:0] bo_a, bo_b; wire [275:0] vo_a, vo_b; wire [4415:0] xc_a, xc_b;
    wire [15:0] cl_a, cl_b, cx_a, cx_b; wire [1:0] cv_a, cv_b; wire [7:0] cr_a, cr_b; wire f_a, f_b;
    ot_s81sl_slice #(.HB(HB)) u_a (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_a), .ro_w(ro_w_a),
        .vi(vi), .vo(vo_a), .bi(bi), .bo(bo_a), .xc(xc_a), .rt(rt), .ck_line(cl_a), .ck_v(cv_a), .ck_xc(cx_a), .ck_rt(cr_a),
        .fault(f_a));
    generate if (HB != 0) begin : g3
        ot_s81sl_slice_c3x #(.DLK0(MUT == 1 ? 5 : 4)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e),
            .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b),
            .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else begin : g1
        ot_s81sl_slice_c1x #(.DLK0(MUT == 1 ? 5 : 4)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e),
            .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b),
            .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end endgenerate
    wire [11041:0] oa = {ro_e_a, ro_w_a, bo_a, vo_a, xc_a, f_a};
    wire [11041:0] ob = {ro_e_b, ro_w_b, bo_b, vo_b, xc_b, f_b};
    integer cyc, bad, nc, j, act; reg [11041:0] prev;
    task rnd; begin
        for (j = 0; j < 35; j = j + 1) begin ri_w[32*j +: 32] = $urandom; ri_e[32*j +: 32] = $urandom; bi[32*j +: 32] = $urandom; end
        for (j = 0; j < 9; j = j + 1) vi[32*j +: 32] = $urandom;
        for (j = 0; j < 18; j = j + 1) rt[32*j +: 32] = $urandom;
    end endtask
    initial begin
        bad = 0; nc = 0; act = 0; prev = 0; ri_w = 0; ri_e = 0; bi = 0; vi = 0; rt = 0;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 8) rst_n = 1'b1;
            rnd;
            if (cyc > 10) begin
                nc = nc + 1; if (oa[11041:1] !== prev[11041:1]) act = act + 1; prev = oa;
                if (oa !== ob) begin bad = bad + 1; if (bad <= 5) $display("SLX_MISMATCH cycle=%0d ro_e %0d ro_w %0d bo %0d vo %0d xc %0d f %0d", cyc,
                    ro_e_a !== ro_e_b, ro_w_a !== ro_w_b, bo_a !== bo_b, vo_a !== vo_b, xc_a !== xc_b, f_a !== f_b); end
            end
        end
        if (bad == 0) $display("SLX PASS HB=%0d MUT=%0d compared=%0d cycles output_changes=%0d fault_seen=%0d", HB, MUT, nc, act, f_a);
        else $display("SLX FAIL HB=%0d MUT=%0d mismatches=%0d of %0d", HB, MUT, bad, nc);
        $finish;
    end
endmodule
