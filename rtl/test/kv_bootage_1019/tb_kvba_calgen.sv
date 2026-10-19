`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19: lockstep bench qkd_attn_cal_gen_b (cfg_cal = {F_DLY, D_RL, D_QK}) vs the closed
// qkd_attn_cal_gen #(.G3S2(1), .RX_CMD(2), .STRETCH(1), .D_QK(Q), .D_RL(R), .SERVICE_END(1777)) over T = 1..8192 (go every
// edge, II = 1).  Every output is compared on every edge; with F_DLY = F the calendar's R field must be exactly (F - 1)
// smaller and every other field / output identical; the sticky fault must rise at the first T where the reference
// faults or R - (F - 1) < P0 (the stretched service no longer fits the link slot).  Phase C: invalid words fault on go.
// Prints "KVBA_CALGEN PASS Q=.. R=.. F=.. mut=.. checks=N" or "KVBA_CALGEN FAIL ...".
module tb_kvba_calgen;
    parameter integer Q = 57, R = 87, F = 49, MUT = 0;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg go = 0; reg [13:0] T = 0; reg [15:0] ep = 0; reg [23:0] cfg;
    wire [175:0] a_cal, b_cal; wire [15:0] a_rx, b_rx, a_tx, b_tx, a_en, b_en, a_ce, b_ce; wire a_d, b_d, a_v, b_v, a_f, b_f;
    qkd_attn_cal_gen #(.G3S2(1), .RX_CMD(2), .STRETCH(1), .D_QK(Q), .D_RL(R), .SERVICE_END(1777), .MUT(0)) u_ref (.ck(ck),
        .rst_n(rst_n), .go(go), .ctx_t(T), .epoch(ep), .cal(a_cal), .rx_cmd(a_rx), .tx_first(a_tx), .end_age(a_en),
        .cal_epoch(a_ce), .done(a_d), .valid(a_v), .fault(a_f));
    qkd_attn_cal_gen_b #(.G3S2(1), .RX_CMD(2), .STRETCH(1), .SERVICE_END(1777), .MUT(MUT)) u_dut (.ck(ck), .rst_n(rst_n),
        .cfg_cal(cfg), .go(go), .ctx_t(T), .epoch(ep), .cal(b_cal), .rx_cmd(b_rx), .tx_first(b_tx), .end_age(b_en),
        .cal_epoch(b_ce), .done(b_d), .valid(b_v), .fault(b_f));
    integer checks = 0, errs = 0, t, n, dones = 0, exp_f = 0, fault_errs = 0, bad_ok = 0, k;
    wire [15:0] r_exp = a_cal[175:160] - 16'(F - 1);
    task cmp; begin
        checks = checks + 1;
        if ({a_cal[159:0], a_rx, a_tx, a_en, a_ce, a_d, a_v} !== {b_cal[159:0], b_rx, b_tx, b_en, b_ce, b_d, b_v} ||
            (a_d && b_cal[175:160] !== r_exp)) begin
            errs = errs + 1;
            if (errs < 6) $display("MISMATCH t=%0t done %b/%b R %0d/%0d (want %0d) tx %0d/%0d", $time, a_d, b_d,
                                   a_cal[175:160], b_cal[175:160], r_exp, a_tx, b_tx);
        end
        if (a_d && (a_f || (a_cal[175:160] < 16'(F - 1)) || (r_exp < a_cal[143:128]))) exp_f = 1;
        if (a_d) dones = dones + 1;
    end endtask
    initial begin
        cfg = {8'(F), 8'(R), 8'(Q)};
        repeat (6) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck);
        for (t = 1; t <= 8192 + 12; t = t + 1) begin
            go = t <= 8192; T = 14'(t); ep = 16'(t);
            @(posedge ck); #0.1 cmp; @(negedge ck);
            if (b_f !== 1'(exp_f)) begin
                fault_errs = fault_errs + 1;
                if (fault_errs < 4) $display("FAULT MISMATCH t=%0d dut %b expected %0d (ref %b)", t, b_f, exp_f, a_f);
            end
        end
        go = 0;
        // ---- phase C: invalid words
        for (k = 0; k < 4; k = k + 1) begin
            cfg = (k == 0) ? {8'd0, 8'(R), 8'(Q)} : (k == 1) ? {8'd128, 8'(R), 8'(Q)} : {8'(F), 8'(R), 8'(Q)};
            rst_n = 0; repeat (4) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck);
            if (k >= 2) begin cfg = {8'(F), 8'(R), 8'(Q)}; end
            go = 1; T = 14'd300; @(negedge ck); go = 0; repeat (14) @(negedge ck);
            if (k < 2) begin if (b_f) bad_ok = bad_ok + 1; else $display("PHASE_C k=%0d invalid cfg accepted", k); end
            else if (k == 2) begin if (!b_f) bad_ok = bad_ok + 1; else $display("PHASE_C valid cfg faulted at T=300"); end
        end
        if (errs == 0 && fault_errs == 0 && dones == 8192 && bad_ok == 3)
            $display("KVBA_CALGEN PASS Q=%0d R=%0d F=%0d mut=%0d checks=%0d dones=%0d fault_from_T=%0d", Q, R, F, MUT, checks, dones, exp_f);
        else
            $display("KVBA_CALGEN FAIL Q=%0d R=%0d F=%0d mut=%0d checks=%0d errors=%0d fault_errors=%0d dones=%0d phase_c=%0d/3",
                     Q, R, F, MUT, checks, errs, fault_errs, dones, bad_ok);
        $finish;
    end
endmodule
