`timescale 1ns/1ps
// S81-SLICERTL (10-20): the parameter-free native32 MU LEP tops (ot_s81sl_lep_mu_n32.sv) elaborate EXACTLY the n32 kit
// configuration: lockstep of ot_s81sl_lep_mu_{a,h}_n32 vs ot_s81sl_lep_mu_{a,h} #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1))
// (the kit top + kit params of s81sl_lepmu{a,h}_n32) under random inputs on every pin every cycle (reset released at 16),
// every output compared every cycle from cycle 24.  H = 0: copy-A top, H = 1: host-plane top.
// MUT 1 (negative control): the reference is the DEFAULT-parameter top (RX_SRAM 0 / IN_PIPE 0 / NATIVE32 0, what the die
// source bound before) -> must FAIL.
module tb_s81sl_lep_mu_n32_eq;
    parameter integer H = 0;
    parameter integer MUT = 0;
    parameter integer CYC = 4000;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [1103:0] ro, ml_rd; reg lo0_r, lo1_r, li0_v, li1_v, sl_f, ml_rv, ml_f; reg [552:0] li0_d, li1_d;
    reg [2:0] l0_f, l1_f; reg [33:0] mu_c; reg [1:0] l0_st, l1_st; reg [76:0] t_host; reg [53:0] t_kd;
    wire [1103:0] ri_a, ri_b, wd_a, wd_b; wire [552:0] lo0d_a, lo0d_b, lo1d_a, lo1d_b;
    wire lo0v_a, lo0v_b, lo1v_a, lo1v_b, li0r_a, li0r_b, li1r_a, li1r_b, wv_a, wv_b, f_a, f_b;
    wire [1:0] rxv_a, rxv_b; wire [31:0] rt_a, rt_b; wire [514:0] fh_a, fh_b; wire [3:0] fl_a, fl_b; wire [52:0] fk_a, fk_b;
`define LEPA_PINS(S) .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri_``S), .lo0_v(lo0v_``S), .lo0_r(lo0_r), .lo0_d(lo0d_``S), \
        .lo1_v(lo1v_``S), .lo1_r(lo1_r), .lo1_d(lo1d_``S), .li0_v(li0_v), .li0_r(li0r_``S), .li0_d(li0_d), .li1_v(li1_v), \
        .li1_r(li1r_``S), .li1_d(li1_d), .rxv(rxv_``S), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .mu_c(mu_c), .mu_rt(rt_``S), \
        .ml_wv(wv_``S), .ml_wd(wd_``S), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(f_``S)
`define LEPH_PINS(S) `LEPA_PINS(S), .l0_st(l0_st), .l1_st(l1_st), .t_host(t_host), .t_kd(t_kd), .f_host(fh_``S), \
        .f_lf(fl_``S), .f_ks(fk_``S)
    generate if (H == 0) begin : g_a
        ot_s81sl_lep_mu_a_n32 u_w (`LEPA_PINS(a));
        if (MUT == 0) begin : g_r ot_s81sl_lep_mu_a #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_r (`LEPA_PINS(b)); end
        else begin : g_m ot_s81sl_lep_mu_a u_r (`LEPA_PINS(b)); end
        assign fh_a = 0; assign fh_b = 0; assign fl_a = 0; assign fl_b = 0; assign fk_a = 0; assign fk_b = 0;
    end else begin : g_h
        ot_s81sl_lep_mu_h_n32 u_w (`LEPH_PINS(a));
        if (MUT == 0) begin : g_r ot_s81sl_lep_mu_h #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_r (`LEPH_PINS(b)); end
        else begin : g_m ot_s81sl_lep_mu_h u_r (`LEPH_PINS(b)); end
    end endgenerate
    wire [5000:0] oa = {ri_a, wd_a, lo0d_a, lo1d_a, lo0v_a, lo1v_a, li0r_a, li1r_a, wv_a, f_a, rxv_a, rt_a, fh_a, fl_a, fk_a};
    wire [5000:0] ob = {ri_b, wd_b, lo0d_b, lo1d_b, lo0v_b, lo1v_b, li0r_b, li1r_b, wv_b, f_b, rxv_b, rt_b, fh_b, fl_b, fk_b};
    integer cyc, j, bad, nc, act; reg [5000:0] prev;
    task rnd; begin
        for (j = 0; j < 35; j = j + 1) begin ro[32*j +: 32] = $urandom; ml_rd[32*j +: 32] = $urandom; end
        for (j = 0; j < 18; j = j + 1) begin li0_d[32*j +: 32] = $urandom; li1_d[32*j +: 32] = $urandom; end
        {lo0_r, lo1_r, li0_v, li1_v, ml_rv} = $urandom; sl_f = ($urandom % 64) == 0; ml_f = ($urandom % 64) == 0;
        l0_f = (($urandom % 16) == 0) ? $urandom : 3'd0; l1_f = (($urandom % 16) == 0) ? $urandom : 3'd0;
        mu_c = {$urandom, $urandom}; l0_st = $urandom; l1_st = $urandom;
        t_host = {$urandom, $urandom, $urandom}; t_kd = {$urandom, $urandom};
    end endtask
    initial begin
        bad = 0; nc = 0; act = 0; prev = 0; rnd;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk); if (cyc == 16) rst_n = 1'b1;
            if (cyc >= 24) begin
                nc = nc + 1;
                if (oa !== ob) begin bad = bad + 1; if (bad <= 4) $display("MISMATCH cyc %0d", cyc); end
                if (oa !== prev) act = act + 1; prev = oa;
            end
            rnd;
        end
        if (bad == 0 && nc > 0) $display("N32EQ PASS H=%0d MUT=%0d compared=%0d active=%0d", H, MUT, nc, act);
        else $display("N32EQ FAIL H=%0d MUT=%0d mismatches=%0d of %0d", H, MUT, bad, nc);
        $finish;
    end
endmodule
