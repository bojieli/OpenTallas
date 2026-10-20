`timescale 1ns/1ps
// QW-SUVM8: lockstep of the hardened VM block qfd_dv_s5_vm8 (three regional clock ports tied to one clock here) against
// qfd_dv_s5_vm7 (suvm7's VM, itself lockstep-proven against qfd_dv_s5_suvm) fed with the PRICED delays:
// reads (a/b/c/cr/bs/p) +1, VM writes (vm_we/waddr/wdata, w16, w1) +2, table writes tw +2, and every vm7 output +1.
// Every output compared every cycle outside reset windows; stimulus biased onto few rows (read-after-write, same-cycle
// read/write collisions, multi-lane slot conflicts), random table/program writes, random resets (>= 6 cycles low; fault
// stimulus suppressed while low and 12 cycles after release so both pipelines hold only clean terms at release).
module tb_vm8;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [7:0] a_re, b_re, c_re, cr_re, vm_we; reg [191:0] a_addr, b_addr, c_addr, cr_addr, vm_waddr; reg [255:0] vm_wdata;
    reg bs_re, p_re; reg [23:0] bs_addr; reg [8:0] p_idx;
    reg w16_we, w1_we, tw_we; reg [23:0] w16_addr, w1_addr, tw_addr; reg [511:0] w16_data; reg [31:0] w1_data;
    reg [1:0] tw_kind; reg [1023:0] tw_data;
    // reference input delays
    reg [7:0] d1_a_re, d1_b_re, d1_c_re, d1_cr_re; reg [191:0] d1_a_addr, d1_b_addr, d1_c_addr, d1_cr_addr;
    reg d1_bs_re, d1_p_re; reg [23:0] d1_bs_addr; reg [8:0] d1_p_idx;
    reg [7:0] d1_vm_we, d2_vm_we; reg [191:0] d1_vm_waddr, d2_vm_waddr; reg [255:0] d1_vm_wdata, d2_vm_wdata;
    reg d1_w16_we, d2_w16_we, d1_w1_we, d2_w1_we, d1_tw_we, d2_tw_we;
    reg [23:0] d1_w16_addr, d2_w16_addr, d1_w1_addr, d2_w1_addr, d1_tw_addr, d2_tw_addr;
    reg [511:0] d1_w16_data, d2_w16_data; reg [31:0] d1_w1_data, d2_w1_data; reg [1:0] d1_tw_kind, d2_tw_kind;
    reg [1023:0] d1_tw_data, d2_tw_data;
    always @(posedge ck) begin
        d1_a_re <= a_re; d1_b_re <= b_re; d1_c_re <= c_re; d1_cr_re <= cr_re;
        d1_a_addr <= a_addr; d1_b_addr <= b_addr; d1_c_addr <= c_addr; d1_cr_addr <= cr_addr;
        d1_bs_re <= bs_re; d1_bs_addr <= bs_addr; d1_p_re <= p_re; d1_p_idx <= p_idx;
        d1_vm_we <= vm_we; d2_vm_we <= d1_vm_we; d1_vm_waddr <= vm_waddr; d2_vm_waddr <= d1_vm_waddr;
        d1_vm_wdata <= vm_wdata; d2_vm_wdata <= d1_vm_wdata;
        d1_w16_we <= w16_we; d2_w16_we <= d1_w16_we; d1_w16_addr <= w16_addr; d2_w16_addr <= d1_w16_addr;
        d1_w16_data <= w16_data; d2_w16_data <= d1_w16_data;
        d1_w1_we <= w1_we; d2_w1_we <= d1_w1_we; d1_w1_addr <= w1_addr; d2_w1_addr <= d1_w1_addr;
        d1_w1_data <= w1_data; d2_w1_data <= d1_w1_data;
        d1_tw_we <= tw_we; d2_tw_we <= d1_tw_we; d1_tw_kind <= tw_kind; d2_tw_kind <= d1_tw_kind;
        d1_tw_addr <= tw_addr; d2_tw_addr <= d1_tw_addr; d1_tw_data <= tw_data; d2_tw_data <= d1_tw_data;
    end
    wire [255:0] r_a, r_b, r_c, r_bs, n_a, n_b, n_c, n_bs; wire [511:0] r_cr, n_cr; wire [456:0] r_p, n_p; wire r_f, n_f;
    wire [7:0] r_lvm;
    qfd_dv_s5_vm7 #(.MUT(0)) u_ref (.ck(ck), .rst_n(rst_n),
        .a_re(d1_a_re), .b_re(d1_b_re), .c_re(d1_c_re), .a_addr(d1_a_addr), .b_addr(d1_b_addr), .c_addr(d1_c_addr),
        .a_q(r_a), .b_q(r_b), .c_q(r_c), .cr_re(d1_cr_re), .cr_addr(d1_cr_addr), .cr_q(r_cr),
        .bs_re(d1_bs_re), .bs_addr(d1_bs_addr), .bs_q(r_bs), .p_re(d1_p_re), .p_idx(d1_p_idx), .p_q(r_p),
        .vm_we(d2_vm_we), .su_waddr(d2_vm_waddr), .su_wdata(d2_vm_wdata), .lvm_we(r_lvm),
        .w16_we(d2_w16_we), .w16_addr(d2_w16_addr), .w16_data(d2_w16_data),
        .w1_we(d2_w1_we), .w1_addr(d2_w1_addr), .w1_data(d2_w1_data),
        .tw_we(d2_tw_we), .tw_kind(d2_tw_kind), .tw_addr(d2_tw_addr), .tw_data(d2_tw_data), .fault(r_f));
    qfd_dv_s5_vm8 #(.MUT(0)) u_new (.ck_wr(ck), .ck_rd(ck), .ck_su(ck), .ckm0(ck), .ckm1(ck), .ckm2(ck), .ckm3(ck), .ckm4(ck), .ckm5(ck), .ckm6(ck), .ckm7(ck), .ckm8(ck), .ckm9(ck), .ckm10(ck), .ckm11(ck), .ckm12(ck), .ckm13(ck), .ckm14(ck), .ckm15(ck), .ckm16(ck), .ckm17(ck), .rst_n(rst_n),
        .a_re(a_re), .b_re(b_re), .c_re(c_re), .a_addr(a_addr), .b_addr(b_addr), .c_addr(c_addr),
        .a_q(n_a), .b_q(n_b), .c_q(n_c), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(n_cr),
        .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(n_bs), .p_re(p_re), .p_idx(p_idx), .p_q(n_p),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(n_f));
    // reference outputs +1 (the answer pin registers)
    wire [2047:0] r_now = {r_a, r_b, r_c, r_cr, r_bs, r_p, r_f};
    reg  [2047:0] r_all;
    always @(posedge ck) r_all <= r_now;
    wire [2047:0] n_all = {n_a, n_b, n_c, n_cr, n_bs, n_p, n_f};
    function [23:0] ra(input integer lane, input [23:0] base);
        ra = {base[23:4], base[3], 3'(lane + $urandom % 2)};
    endfunction
    integer cyc, nmis = 0, ncmp = 0, nfault = 0, nrd = 0, ncoll = 0, l, rlow = 0, since = 0;
    reg [23:0] b0, b1, b2, b3, bw;
    reg clean;
    initial begin
        {a_re, b_re, c_re, cr_re, vm_we, a_addr, b_addr, c_addr, cr_addr, vm_waddr, vm_wdata} = 0;
        {bs_re, p_re, bs_addr, p_idx, w16_we, w1_we, tw_we, w16_addr, w1_addr, tw_addr, w16_data, w1_data, tw_kind, tw_data} = 0;
        repeat (8) @(negedge ck); rst_n = 1;
        for (cyc = 0; cyc < 60000; cyc = cyc + 1) begin
            @(negedge ck);
            if (rst_n && $urandom % 3000 == 0) begin rst_n = 0; rlow = 0; end
            else if (!rst_n) begin rlow = rlow + 1; if (rlow >= 6 && $urandom % 4 == 0) begin rst_n = 1; since = 0; end end
            else since = since + 1;
            clean = !rst_n || since < 12;            // no fault / collision stimulus around reset
            b0 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0}; b1 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0};
            b2 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0}; b3 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0};
            bw = {(!clean && $urandom % 8 == 0) ? 2'($urandom) : 2'b00, 8'd0, 10'($urandom % 4), 1'($urandom), 3'd0};
            if (!clean && $urandom % 2500 == 0) b0 = $urandom;
            a_re = ($urandom % 3 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            b_re = ($urandom % 3 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            c_re = ($urandom % 3 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            cr_re = ($urandom % 4 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            vm_we = ($urandom % 3 == 0) ? ((!clean && $urandom % 500 == 0) ? 8'($urandom) : (8'hFF >> ($urandom % 8))) : 8'd0;
            for (l = 0; l < 8; l = l + 1) begin
                a_addr[24*l +: 24] = ra(l, b0); b_addr[24*l +: 24] = ra(l, b1); c_addr[24*l +: 24] = ra(l, b2);
                cr_addr[24*l +: 24] = ra(l, b3); vm_waddr[24*l +: 24] = {bw[23:3], 3'($urandom)};
            end
            vm_wdata = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            bs_re = $urandom % 2; bs_addr = (!clean && $urandom % 2500 == 0) ? 24'($urandom) : {15'd0, 9'($urandom % 16)};
            p_re = ($urandom % 3 == 0); p_idx = 9'($urandom % 16);
            w16_we = ($urandom % 6 == 0);
            w16_addr = (!clean && $urandom % 2500 == 0) ? 24'($urandom) : {10'd0, 10'($urandom % 4), 4'd0};
            w16_data = {16{$urandom}} ^ {$urandom, 480'd0};
            w1_we = ($urandom % 4 == 0);
            w1_addr = (!clean && $urandom % 2500 == 0) ? 24'($urandom) : {10'd0, 10'($urandom % 4), 4'($urandom)};
            w1_data = $urandom;
            tw_we = ($urandom % 5 == 0); tw_kind = (!clean && $urandom % 2500 == 0) ? 2'd0 : 2'(1 + $urandom % 3);
            tw_addr = (!clean && $urandom % 2500 == 0) ? 24'($urandom) : (tw_kind == 2) ? {15'd0, 7'($urandom % 4), 2'd0} : {16'd0, 8'($urandom % 16)};
            for (l = 0; l < 32; l = l + 1) tw_data[32*l +: 32] = $urandom;
            if (clean || $urandom % 500 != 0) begin
                if (w16_we) begin w1_we = 0; vm_we = 0; end
                if (w1_we && vm_we != 0) w1_addr[3] = ~bw[3];
            end
            @(posedge ck); #0.5;
            if (rst_n && since > 12) begin
                ncmp = ncmp + 1;
                if (r_all !== n_all) begin
                    nmis = nmis + 1;
                    if (nmis <= 8) $display("VM8_MISMATCH cycle=%0d diff=%h", cyc, r_all ^ n_all);
                end
                if (r_all[0]) nfault = nfault + 1;
                if (d1_a_re[0] || d1_b_re[0] || d1_c_re[0]) nrd = nrd + 1;
            end
        end
        $display("VM8_STATS compares=%0d mismatches=%0d fault_cycles=%0d read_cycles=%0d", ncmp, nmis, nfault, nrd);
        if (nmis == 0 && nrd > 1000 && ncmp > 40000) $display("VM8_EQ PASS"); else $display("VM8_EQ FAIL");
        $finish;
    end
endmodule
