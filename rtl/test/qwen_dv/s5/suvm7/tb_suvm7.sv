`timescale 1ns/1ps
// QW-SLICE7-LEAVES/SUVM: lockstep of the safe master qfd_dv_s5_suvm7 against the reference qfd_dv_s5_suvm (HARD 1)
// fed with the VM write bundle {vm_we, vm_waddr, vm_wdata, w16_*, w1_*} ONE cycle later (= the priced +1 write landing).
// Every output compared every cycle (after the first reset), random stimulus biased onto few rows (read-after-write,
// collisions, multi-lane slot conflicts), random program words via table writes, random mid-run resets.
module tb_suvm7;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [9:0] su_cmd; reg [7:0] va_re, vb_re, vc_re, cr_re, vm_we, kv_we, l_retire, l_last, l_fault, l_wrom_re;
    reg [191:0] va_addr, vb_addr, vc_addr, cr_addr, vm_waddr, l_wrom_addr; reg [255:0] vm_wdata;
    reg rd_v, red_busy, red_fault, w16_we, w1_we, tw_we; reg [23:0] w16_addr, w1_addr, tw_addr; reg [511:0] w16_data;
    reg [31:0] w1_data; reg [1:0] tw_kind; reg [1023:0] tw_data;
    // reference write bundle, one cycle late
    reg [7:0] d_vm_we; reg [191:0] d_vm_waddr; reg [255:0] d_vm_wdata; reg d_w16_we, d_w1_we; reg [23:0] d_w16_addr, d_w1_addr;
    reg [511:0] d_w16_data; reg [31:0] d_w1_data;
    always @(posedge ck) begin
        d_vm_we <= vm_we; d_vm_waddr <= vm_waddr; d_vm_wdata <= vm_wdata; d_w16_we <= w16_we; d_w1_we <= w1_we;
        d_w16_addr <= w16_addr; d_w1_addr <= w1_addr; d_w16_data <= w16_data; d_w1_data <= w1_data;
    end
`define OUTS(P) wire [499:0] P``gb; wire [2:0] P``gv; wire [7:0] P``lv1; wire [767:0] P``pd1; wire [255:0] P``va_q, P``vb_q, P``vc_q; \
    wire [511:0] P``cr_q; wire P``su_nr, P``su_idle, P``su_fault, P``vm_fault; wire [15:0] P``su_prog, P``su_rows;
    `OUTS(r_) `OUTS(n_)
`define CONN(P) .ck(ck), .rst_n(rst_n), .su_cmd(su_cmd), .gb(P``gb), .gv(P``gv), .lv1(P``lv1), .pd1(P``pd1), \
    .va_re(va_re), .vb_re(vb_re), .vc_re(vc_re), .cr_re(cr_re), .kv_we(kv_we), .l_retire(l_retire), .l_last(l_last), \
    .l_fault(l_fault), .l_wrom_re(l_wrom_re), .va_addr(va_addr), .vb_addr(vb_addr), .vc_addr(vc_addr), .cr_addr(cr_addr), \
    .l_wrom_addr(l_wrom_addr), .va_q(P``va_q), .vb_q(P``vb_q), .vc_q(P``vc_q), .cr_q(P``cr_q), .rd_v(rd_v), \
    .red_busy(red_busy), .red_fault(red_fault), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), \
    .su_nr(P``su_nr), .su_idle(P``su_idle), .su_fault(P``su_fault), .su_prog(P``su_prog), .su_rows(P``su_rows), .vm_fault(P``vm_fault)
    qfd_dv_s5_suvm #(.HARD(1)) u_ref (`CONN(r_), .vm_we(d_vm_we), .vm_waddr(d_vm_waddr), .vm_wdata(d_vm_wdata),
        .w16_we(d_w16_we), .w16_addr(d_w16_addr), .w16_data(d_w16_data), .w1_we(d_w1_we), .w1_addr(d_w1_addr), .w1_data(d_w1_data));
    qfd_dv_s5_suvm7 #(.HARD(1)) u_new (`CONN(n_), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data));
    wire [4095:0] r_all = {r_gb, r_gv, r_lv1, r_pd1, r_va_q, r_vb_q, r_vc_q, r_cr_q, r_su_nr, r_su_idle, r_su_fault, r_vm_fault, r_su_prog, r_su_rows};
    wire [4095:0] n_all = {n_gb, n_gv, n_lv1, n_pd1, n_va_q, n_vb_q, n_vc_q, n_cr_q, n_su_nr, n_su_idle, n_su_fault, n_vm_fault, n_su_prog, n_su_rows};
    function [23:0] ra(input integer lane, input [23:0] base);     // few rows, lane-consistent word, random element
        ra = {base[23:4], base[3], 3'(lane + $urandom % 2)};
    endfunction
    integer cyc, nmis = 0, ncmp = 0, nfault = 0, nact = 0, l;
    reg [23:0] b0, b1, b2, b3, bw;
    initial begin
        {su_cmd, va_re, vb_re, vc_re, cr_re, vm_we, kv_we, l_retire, l_last, l_fault, l_wrom_re} = 0;
        {va_addr, vb_addr, vc_addr, cr_addr, vm_waddr, l_wrom_addr, vm_wdata} = 0;
        {rd_v, red_busy, red_fault, w16_we, w1_we, tw_we, w16_addr, w1_addr, tw_addr, w16_data, w1_data, tw_kind, tw_data} = 0;
        repeat (4) @(negedge ck); rst_n = 1;
        for (cyc = 0; cyc < 40000; cyc = cyc + 1) begin
            @(negedge ck);
            if ($urandom % 3000 == 0) rst_n = 0; else if (!rst_n && $urandom % 4 == 0) rst_n = 1;
            b0 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0}; b1 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0};
            b2 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0}; b3 = {10'd0, 10'($urandom % 4), 1'($urandom), 3'd0};
            bw = {($urandom % 8 == 0) ? 2'($urandom) : 2'b00, 8'd0, 10'($urandom % 4), 1'($urandom), 3'd0};
            if ($urandom % 2500 == 0) b0 = $urandom;       // out-of-window / misaligned (fault paths)
            va_re = ($urandom % 3 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            vb_re = ($urandom % 3 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            vc_re = ($urandom % 3 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            cr_re = ($urandom % 4 == 0) ? (8'hFF >> ($urandom % 8)) : 8'd0;
            vm_we = ($urandom % 3 == 0) ? (($urandom % 500 == 0) ? 8'($urandom) : (8'hFF >> ($urandom % 8))) : 8'd0;
            for (l = 0; l < 8; l = l + 1) begin
                va_addr[24*l +: 24] = ra(l, b0); vb_addr[24*l +: 24] = ra(l, b1); vc_addr[24*l +: 24] = ra(l, b2);
                cr_addr[24*l +: 24] = ra(l, b3); vm_waddr[24*l +: 24] = {bw[23:3], 3'($urandom)};
                l_wrom_addr[24*l +: 24] = {15'd0, 9'($urandom % 16)};
            end
            vm_wdata = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            w16_we = ($urandom % 6 == 0); w16_addr = ($urandom % 2500 == 0) ? 24'($urandom) : {10'd0, 10'($urandom % 4), 4'd0};
            w16_data = {16{$urandom}} ^ {$urandom, 480'd0};
            w1_we = ($urandom % 4 == 0); w1_addr = ($urandom % 2500 == 0) ? 24'($urandom) : {10'd0, 10'($urandom % 4), 4'($urandom)};
            w1_data = $urandom;
            tw_we = ($urandom % 5 == 0); tw_kind = ($urandom % 2500 == 0) ? 2'd0 : 2'(1 + $urandom % 3);
            tw_addr = ($urandom % 2500 == 0) ? 24'($urandom) : (tw_kind == 2) ? {15'd0, 7'($urandom), 2'd0} : {16'd0, 8'($urandom)};
            tw_data = {32{$urandom}};
            for (l = 0; l < 32; l = l + 1) tw_data[32*l +: 32] = $urandom;
            if (tw_kind == 3) begin            // program words: small counts so instructions finish
                tw_data[18:1] = 18'($urandom % 3 + 1); tw_data[36:19] = 18'($urandom % 20 + 1); tw_data[265:263] = 3'($urandom % 2);
                tw_data[512 + 18:512 + 1] = 18'($urandom % 3 + 1); tw_data[512 + 36:512 + 19] = 18'($urandom % 20 + 1);
            end
            if ($urandom % 500 != 0) begin     // write sources mostly exclusive (collision fault paths kept rare)
                if (w16_we) begin w1_we = 0; vm_we = 0; end
                if (w1_we && vm_we != 0) w1_addr[3] = ~bw[3];
            end
            su_cmd = {($urandom % 25 == 0), 9'($urandom % 8)};
            kv_we = ($urandom % 10 == 0) ? 8'd1 : 8'd0; l_retire = 8'($urandom % 2); l_last = 8'($urandom % 2);
            l_fault = ($urandom % 4000 == 0) ? 8'd1 : 8'd0; l_wrom_re = 8'($urandom % 2);
            rd_v = ($urandom % 8 == 0); red_busy = ($urandom % 8 == 0); red_fault = ($urandom % 5000 == 0);
            @(posedge ck); #0.5;
            if (rst_n && cyc > 2) begin
                ncmp = ncmp + 1;
                if (r_all !== n_all) begin
                    nmis = nmis + 1;
                    if (nmis <= 8) $display("SUVM7_MISMATCH cycle=%0d diff=%h", cyc, r_all ^ n_all);
                end
                if (r_vm_fault) nfault = nfault + 1;
                if (r_gv[2]) nact = nact + 1;
            end
        end
        $display("SUVM7_STATS compares=%0d mismatches=%0d fault_cycles=%0d emit_cycles=%0d", ncmp, nmis, nfault, nact);
        if (nmis == 0 && nact > 100) $display("SUVM7_EQ PASS"); else $display("SUVM7_EQ FAIL");
        $finish;
    end
endmodule
