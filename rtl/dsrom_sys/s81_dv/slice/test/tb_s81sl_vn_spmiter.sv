`timescale 1ns/1ps
// S81/RTLSPLIT miter bench (2026-10-24): the two-core split ot_s81sl_vn_sp (u_a = ot_s81sl_vn_a + u_b = ot_s81sl_vn_b,
// DUT) against the unsplit ot_s81sl_vn (reference, same file) on the same random static-schedule stimulus:
//   h half-row writes / reads (any density, reads also inside a norm: the shared-port fault), norm go (n_pre) never
//   while the previous norm still issues (the compiler's slot rule; >= 9 edges apart, else 9..GOMAX), gain row loads,
//   rstd broadcasts (any spacing).  Data: BF16 h / FP32 coefficients, gains, rstd in a finite range (no FP faults, so
//   the fault pin compares exactly).
// Checks every released edge: hq_v, hq_d, y_v, y_i, y, fault == the reference on the SAME edge; p_v, p_d == the
// reference 2 edges earlier (the split's cost: chain partial through c_s output flop + pin flop).
// Prints "MITER PASS|FAIL vn split cycles N mismatches M" + activity.  +define+OT_S81SL_SPMUT_C1 / _HQ = DUT mutants.
module tb_s81sl_vn_spmiter #(parameter integer CYC = 40000, GOMAX = 90);
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg hw_v = 0, hw_hf = 0, hr_v = 0, hr_hf = 0, n_go = 0, wl_v = 0, rb_v = 0;
    reg [2:0] hw_j = 0, hr_j = 0, wl_i = 0; reg [255:0] hw_d = 0, wl_d = 0; reg [127:0] n_pre = 0; reg [31:0] rb_d = 0;
    wire hq_v, p_v, y_v, fault; wire [255:0] hq_d; wire [31:0] p_d; wire [2:0] y_i; wire [127:0] y;
    wire r_hq_v, r_p_v, r_y_v, r_fault; wire [255:0] r_hq_d; wire [31:0] r_p_d; wire [2:0] r_y_i; wire [127:0] r_y;
    ot_s81sl_vn_sp dut (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d), .hr_v(hr_v),
        .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hq_v), .hq_d(hq_d), .n_go(n_go), .n_pre(n_pre), .wl_v(wl_v), .wl_i(wl_i),
        .wl_d(wl_d), .rb_v(rb_v), .rb_d(rb_d), .p_v(p_v), .p_d(p_d), .y_v(y_v), .y_i(y_i), .y(y), .fault(fault));
    ot_s81sl_vn ref_vn (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d), .hr_v(hr_v),
        .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(r_hq_v), .hq_d(r_hq_d), .n_go(n_go), .n_pre(n_pre), .wl_v(wl_v), .wl_i(wl_i),
        .wl_d(wl_d), .rb_v(rb_v), .rb_d(rb_d), .p_v(r_p_v), .p_d(r_p_d), .y_v(r_y_v), .y_i(r_y_i), .y(r_y), .fault(r_fault));
    reg [32:0] pd1, pd2;
    always @(posedge clk) begin pd1 <= {r_p_v, r_p_d}; pd2 <= pd1; end
    function automatic [15:0] bf(input integer dummy);
        reg [31:0] r; begin r = $urandom; bf = {r[15], 8'd120 + {4'd0, r[11:8]} % 8'd14, r[6:0]}; end
    endfunction
    function automatic [31:0] f32(input integer lo, input integer span);
        reg [31:0] r; begin r = $urandom; f32 = {r[31], 8'd0 + lo[7:0] + (r[30:23] % span[7:0]), r[22:0]}; end
    endfunction
    integer cyc = 0, mm = 0, k, gap = 0, gnext = 9;
    integer a_p = 0, a_y = 0, a_hq = 0, a_go = 0, a_f = 0, a_rb = 0, a_wl = 0, a_hw = 0;
    integer dh, dr, dw, db;
    always @(posedge clk) begin
        #0.01;
        if (rst_n && cyc > 12) begin
            if ({hq_v, y_v, fault, y_i} !== {r_hq_v, r_y_v, r_fault, r_y_i} || hq_d !== r_hq_d || y !== r_y) begin
                mm = mm + 1; if (mm < 6) $display("MITER DIFF same-edge cyc=%0d hq_v %b/%b y_v %b/%b fault %b/%b", cyc,
                    hq_v, r_hq_v, y_v, r_y_v, fault, r_fault);
            end
            if ({p_v, p_d} !== pd2) begin
                mm = mm + 1; if (mm < 6) $display("MITER DIFF p cyc=%0d split %b %h ref(-2) %b %h", cyc, p_v, p_d, pd2[32], pd2[31:0]);
            end
            a_p = a_p + p_v; a_y = a_y + y_v; a_hq = a_hq + hq_v; a_f = a_f + fault;
        end
    end
    initial begin
        void'($urandom(32'd20261024));
        repeat (8) @(negedge clk); rst_n = 1;
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            // per-2000-edge phase densities (1/2 .. 1/32)
            if (cyc % 2000 == 0) begin dh = 2 + $urandom % 30; dr = 2 + $urandom % 30; dw = 2 + $urandom % 30; db = 9 + $urandom % 60; end
            hw_v = ($urandom % dh) == 0; hw_j = $urandom; hw_hf = $urandom;
            for (k = 0; k < 16; k = k + 1) hw_d[16 * k +: 16] = bf(0);
            hr_v = ($urandom % dr) == 0; hr_j = $urandom; hr_hf = $urandom;
            wl_v = ($urandom % dw) == 0; wl_i = $urandom;
            for (k = 0; k < 8; k = k + 1) wl_d[32 * k +: 32] = f32(118, 16);
            rb_v = ($urandom % db) == 0; rb_d = f32(118, 14);
            gap = gap + 1;
            n_go = (gap >= gnext);
            if (n_go) begin gap = 0; gnext = 9 + $urandom % (GOMAX - 8); end
            for (k = 0; k < 4; k = k + 1) n_pre[32 * k +: 32] = f32(119, 10);
            a_go = a_go + n_go; a_rb = a_rb + rb_v; a_wl = a_wl + wl_v; a_hw = a_hw + hw_v;
            @(negedge clk);
        end
        $display("MITER_ACT go %0d hw %0d wl %0d rb %0d | p_v %0d y_v %0d hq_v %0d fault-edges %0d", a_go, a_hw, a_wl, a_rb,
                 a_p, a_y, a_hq, a_f);
        $display("MITER %s vn split cycles %0d mismatches %0d", (mm == 0 && a_p > 0 && a_y > 0) ? "PASS" : "FAIL", CYC, mm);
        $finish;
    end
endmodule
