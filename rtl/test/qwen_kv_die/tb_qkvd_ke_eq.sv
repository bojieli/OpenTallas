`timescale 1ns/1ps
// q13-kvleaves 2026-10-13: the thin-cluster KV end (ot_qkvd_kv_end SPL=1: ot_qkvd_ke_cluster over the hard tiles of
// ot_qkvd_ke_tiles.sv and the pin-registered link buffers) against the flat ot_qkvd_kv_end (HT=1, PQ=2, PF=1) it was
// cut from.
//   A  = SPL=1, in a closed link with a matched far end B (flop FIFOs) under random die-face traffic both ways, random
//        die credit return and random tx_up drops: every word must arrive once, in order, per class, with no fault
//        (the tb_qkvd_d2d_pair scoreboard);
//   R  = SPL=0, fed the SAME inputs as A with r_cr and tx_up one cycle late (the two seams where the cluster spends a
//        register): t_cr, r_v, r_d, tx_v, tx_flit must equal A's on EVERY cycle, and A's fault / fault_cause must equal
//        R's one cycle later;
//   then a die-face overrun is forced on TX class 6 (words without credit, link down): both must raise fault with
//        cause 00001, again in step.
// Prints "KE_EQ PASS words <n> cycles <c> compares <m> fault_ok 1" or "KE_EQ FAIL ...".  Mutants (must FAIL):
// +define+KVD_KE_MUT_TI / _RQ / _TM / _TF / _RO / _CTL / _WF (one per hard tile) and +define+KVD_PQ2MUT (the shadows).
module tb_qkvd_ke_eq;
    parameter integer QD = 48, UCX = 48, FCR_RES = 32, NCYC = 40000, SEED = 12345;
    localparam integer W = 528, FW = 548;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg  [2:0] a_tv; reg [3*W-1:0] a_td; wire [2:0] a_tcr; wire [3:0] a_rv; wire [4*W-1:0] a_rd; reg [3:0] a_rcr;
    reg  [3:0] b_tv; reg [4*W-1:0] b_td; wire [3:0] b_tcr; wire [2:0] b_rv; wire [3*W-1:0] b_rd; reg [2:0] b_rcr;
    reg a_up, b_up; wire a_txv, b_txv; wire [FW-1:0] a_txf, b_txf; wire a_f, b_f; wire [4:0] a_fc, b_fc;
    ot_qkvd_kv_end #(.QD(QD), .UCX(UCX), .FCR_RES(FCR_RES), .SPL(1)) u_a (.clk(clk), .rst_n(rst_n), .t_v(a_tv), .t_d(a_td),
        .t_cr(a_tcr), .r_v(a_rv), .r_d(a_rd), .r_cr(a_rcr), .tx_up(a_up), .tx_v(a_txv), .tx_flit(a_txf), .rx_v(b_txv),
        .rx_flit(b_txf), .fault(a_f), .fault_cause(a_fc));
    // reference: the flat KV end, r_cr / tx_up one cycle late
    reg [3:0] r_rcr; reg r_up;
    always @(posedge clk) begin r_rcr <= a_rcr; r_up <= a_up; end
    wire [2:0] r_tcr; wire [3:0] r_rv; wire [4*W-1:0] r_rd; wire r_txv; wire [FW-1:0] r_txf; wire r_f; wire [4:0] r_fc;
    ot_qkvd_kv_end #(.QD(QD), .UCX(UCX), .FCR_RES(FCR_RES), .HT(1), .PQ(2), .PF(1)) u_r (.clk(clk), .rst_n(rst_n), .t_v(a_tv),
        .t_d(a_td), .t_cr(r_tcr), .r_v(r_rv), .r_d(r_rd), .r_cr(r_rcr), .tx_up(r_up), .tx_v(r_txv), .tx_flit(r_txf),
        .rx_v(b_txv), .rx_flit(b_txf), .fault(r_f), .fault_cause(r_fc));
    reg r_f_q; reg [4:0] r_fc_q;
    always @(posedge clk) begin r_f_q <= r_f; r_fc_q <= r_fc; end
    // far end (ROM-end configuration of ot_qkvd_d2d, flop FIFOs)
    ot_qkvd_d2d #(.NT(4), .NR(3), .TXB(0), .RXB(4), .W(W), .IBD({8'd8, 8'd8, 8'd8, 8'd8}),
        .FCR({8'd32, 8'd8, 8'd32, 8'd4}), .RBD({8'd8, 8'd4, 8'd32, 8'd32}), .OCR({8'd8, 8'd8, 8'd8, 8'd8})) u_b (
        .clk(clk), .rst_n(rst_n), .t_v(b_tv), .t_d(b_td), .t_cr(b_tcr), .r_v(b_rv), .r_d(b_rd), .r_cr(b_rcr),
        .tx_up(b_up), .tx_v(b_txv), .tx_flit(b_txf), .rx_v(a_txv), .rx_flit(a_txf), .fault(b_f), .fault_cause(b_fc));
    integer a_cr [0:2], b_cr [0:3], a_ow [0:3], b_ow [0:2];
    integer a_sent [0:2], b_sent [0:3], a_got [0:3], b_got [0:2];
    integer k, cyc, errs, total, cmps, eqerr, fault_ok;
    integer seed = SEED;
    function [W-1:0] word(input integer cls, input integer n);
        word = {16'(cls * 4096 + n), {16{32'(n * 2654435761 + cls)}}};
    endfunction
    // lockstep compare (outputs settled after the edge)
    task cmp;
        begin
            cmps = cmps + 1;
            if (a_tcr !== r_tcr || a_rv !== r_rv || a_rd !== r_rd || a_txv !== r_txv || a_txf !== r_txf ||
                a_f !== r_f_q || a_fc !== r_fc_q) begin
                eqerr = eqerr + 1;
                if (eqerr < 6) $display("LOCKSTEP mismatch cyc %0d: t_cr %b/%b r_v %b/%b r_d %s tx_v %b/%b tx_flit %s fault %b/%b cause %b/%b",
                    cyc, a_tcr, r_tcr, a_rv, r_rv, a_rd === r_rd ? "eq" : "NE", a_txv, r_txv, a_txf === r_txf ? "eq" : "NE",
                    a_f, r_f_q, a_fc, r_fc_q);
            end
        end
    endtask
    initial begin
        errs = 0; total = 0; cmps = 0; eqerr = 0; fault_ok = 0;
        for (k = 0; k < 3; k = k + 1) begin a_cr[k] = (k == 2) ? 4 : UCX; a_sent[k] = 0; b_got[k] = 0; b_ow[k] = 0; end
        for (k = 0; k < 4; k = k + 1) begin b_cr[k] = 8; b_sent[k] = 0; a_got[k] = 0; a_ow[k] = 0; end
        a_tv = 0; b_tv = 0; a_td = 0; b_td = 0; a_rcr = 0; b_rcr = 0; a_up = 0; b_up = 0;
        repeat (5) @(posedge clk);
        rst_n = 1;
        repeat (16) @(posedge clk);
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            a_up = ($urandom(seed) % 16) != 0 || cyc < 100; b_up = ($urandom % 16) != 0;
            a_tv = 0; b_tv = 0; a_rcr = 0; b_rcr = 0;
            for (k = 0; k < 3; k = k + 1) if (a_cr[k] > 0 && cyc < NCYC - 2000 && ($urandom % 100) < ((cyc / 3000) % 2 ? 95 : 40)) begin
                a_tv[k] = 1; a_td[W*k +: W] = word(4 + k, a_sent[k]); a_sent[k] = a_sent[k] + 1; a_cr[k] = a_cr[k] - 1; end
            for (k = 0; k < 4; k = k + 1) if (b_cr[k] > 0 && cyc < NCYC - 2000 && ($urandom % 100) < 60) begin
                b_tv[k] = 1; b_td[W*k +: W] = word(k, b_sent[k]); b_sent[k] = b_sent[k] + 1; b_cr[k] = b_cr[k] - 1; end
            for (k = 0; k < 4; k = k + 1) if (a_ow[k] > 0 && ($urandom % 100) < ((cyc / 5000) % 2 ? 90 : 30)) begin a_rcr[k] = 1; a_ow[k] = a_ow[k] - 1; end
            for (k = 0; k < 3; k = k + 1) if (b_ow[k] > 0 && ($urandom % 100) < 70) begin b_rcr[k] = 1; b_ow[k] = b_ow[k] - 1; end
            @(posedge clk); #0.1;
            cmp;
            for (k = 0; k < 3; k = k + 1) if (a_tcr[k]) a_cr[k] = a_cr[k] + 1;
            for (k = 0; k < 4; k = k + 1) if (b_tcr[k]) b_cr[k] = b_cr[k] + 1;
            for (k = 0; k < 4; k = k + 1) if (a_rv[k]) begin
                if (a_rd[W*k +: W] !== word(k, a_got[k])) begin errs = errs + 1; if (errs < 5) $display("A rx class %0d word %0d mismatch", k, a_got[k]); end
                a_got[k] = a_got[k] + 1; a_ow[k] = a_ow[k] + 1; total = total + 1; end
            for (k = 0; k < 3; k = k + 1) if (b_rv[k]) begin
                if (b_rd[W*k +: W] !== word(4 + k, b_got[k])) begin errs = errs + 1; if (errs < 5) $display("B rx class %0d word %0d mismatch", 4 + k, b_got[k]); end
                b_got[k] = b_got[k] + 1; b_ow[k] = b_ow[k] + 1; total = total + 1; end
            if (a_f || b_f || r_f) begin $display("KE_EQ FAIL fault a %b (%b) ref %b (%b) b %b (%b) at cycle %0d", a_f, a_fc, r_f, r_fc, b_f, b_fc, cyc); $finish; end
        end
        for (k = 0; k < 3; k = k + 1) if (b_got[k] != a_sent[k]) begin errs = errs + 1; $display("class %0d: sent %0d got %0d", 4 + k, a_sent[k], b_got[k]); end
        for (k = 0; k < 4; k = k + 1) if (a_got[k] != b_sent[k]) begin errs = errs + 1; $display("class %0d: sent %0d got %0d", k, b_sent[k], a_got[k]); end
        // forced die-face overrun on TX class 6 (buffer of 4, link down): fault, cause f_die, in step with the reference
        for (cyc = NCYC; cyc < NCYC + 40; cyc = cyc + 1) begin
            @(negedge clk);
            a_up = 0; b_up = 0; a_tv = 0; b_tv = 0; a_rcr = 0; b_rcr = 0;
            if (cyc < NCYC + 12) begin a_tv[2] = 1; a_td[W*2 +: W] = word(6, cyc); end
            @(posedge clk); #0.1;
            cmp;
        end
        fault_ok = (a_f === 1'b1 && a_fc === 5'b00001 && r_f === 1'b1);
        if (errs == 0 && eqerr == 0 && fault_ok == 1)
            $display("KE_EQ PASS words %0d cycles %0d compares %0d fault_ok 1 (QD %0d UCX %0d FCR_RES %0d; A->B %0d %0d %0d)",
                     total, NCYC, cmps, QD, UCX, FCR_RES, b_got[0], b_got[1], b_got[2]);
        else $display("KE_EQ FAIL errors %0d lockstep %0d fault_ok %0d (a_f %b cause %b)", errs, eqerr, fault_ok, a_f, a_fc);
        $finish;
    end
endmodule
