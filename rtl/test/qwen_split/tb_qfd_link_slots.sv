`timescale 1ns/1ps
// Bench of rtl/qwen_split/qfd_link_slots.sv (compute-die lead r3, 2026-10-14).
// (1) qfd_d2d_rom is the reference composition of the link bench (tb_qwen_split_link.sv LLR=1: ot_qfd_split_romlink ->
//     ot_qkvd_d2d_llr): both get the same random stimulus on every input every cycle (SU / VM / sequencer / tree / PHY
//     FDI sides) and every output is compared every cycle.  MUT=1 (crossed x3 tag bits) must FAIL.
// (2) qfd_rstsync + qfd_rstseq: every domain stays in reset >= FLUSH edges after the forwarded reset releases and the
//     domains release in order io -> field -> spine -> tree top -> sequencer; a reset re-assertion re-asserts all.
module tb_qfd_link_slots;
    parameter integer MUT = 0;
    parameter integer N   = 20000;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    localparam integer FW = 548, PW = FW + 35;
    reg x3_v, ea_v, ea_kind, ar_cr, tx_up, rx_v;
    reg [511:0] x3_d; reg [10:0] x3_tag; reg [23:0] ea_addr; reg [55:0] dc; reg [43:0] kvd; reg [PW-1:0] rx_f;
    wire        d_x3cr, d_eacr, d_eqv, d_arv, d_txv, d_f; wire [511:0] d_eq; wire [518:0] d_ar; wire [186:0] d_dh;
    wire [74:0] d_pw; wire [PW-1:0] d_txf; wire [10:0] d_fc;
    wire        r_x3cr, r_eacr, r_eqv, r_arv, r_txv, r_f1, r_f2; wire [511:0] r_eq; wire [518:0] r_ar; wire [186:0] r_dh;
    wire [74:0] r_pw; wire [PW-1:0] r_txf; wire [7:0] r_fc1; wire [2:0] r_fc2;
    qfd_d2d_rom #(.MUT(MUT)) dut (.ck(clk), .rst_n(rst_n), .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(d_x3cr),
        .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(d_eacr), .eq_v(d_eqv), .eq_d(d_eq), .ar_v(d_arv), .ar_d(d_ar),
        .ar_cr(ar_cr), .dc(dc), .dh(d_dh), .pw(d_pw), .kvd(kvd), .fdi_tx_up(tx_up), .fdi_tx_v(d_txv), .fdi_tx_flit(d_txf),
        .fdi_rx_v(rx_v), .fdi_rx_flit(rx_f), .fault(d_f), .fault_cause(d_fc));
    wire a_up, a_txv, a_rxv; wire [FW-1:0] a_txf, a_rxf;
    ot_qfd_split_romlink ref_rl (.clk(clk), .rst_n(rst_n), .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(r_x3cr),
        .ar_v(r_arv), .ar_d(r_ar), .ar_cr(ar_cr), .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(r_eacr),
        .eq_v(r_eqv), .eq_d(r_eq), .sd(dc), .kvd(kvd), .ds(r_dh), .pw(r_pw),
        .tx_up(a_up), .tx_v(a_txv), .tx_flit(a_txf), .rx_v(a_rxv), .rx_flit(a_rxf), .fault(r_f1), .fault_cause(r_fc1));
    ot_qkvd_d2d_llr #(.FW(FW)) ref_llr (.clk(clk), .rst_n(rst_n), .a_tx_up(a_up), .a_tx_v(a_txv), .a_tx_flit(a_txf),
        .a_rx_v(a_rxv), .a_rx_flit(a_rxf), .p_tx_up(tx_up), .p_tx_v(r_txv), .p_tx_flit(r_txf), .p_rx_v(rx_v),
        .p_rx_flit(rx_f), .fault(r_f2), .fault_cause(r_fc2));
    wire [2000:0] dv = {d_x3cr, d_eacr, d_eqv, d_arv, d_txv, d_f, d_eq, d_ar, d_dh, d_pw, d_txf, d_fc};
    wire [2000:0] rv = {r_x3cr, r_eacr, r_eqv, r_arv, r_txv, r_f1 | r_f2, r_eq, r_ar, r_dh, r_pw, r_txf, r_fc2, r_fc1};
    // reset sequencer
    reg arst = 0;
    wire rso_d, rso_f, io, fld, sp, ctlm, seq;
    qfd_rstsync u_rs (.ck(clk), .arst_n(arst), .rso_d(rso_d), .rso_f(rso_f));
    qfd_rstseq #(.FLUSH(64), .STEP(4)) u_seq (.ck(clk), .rsi(rso_f), .rso_io(io), .rso_f(fld), .rso_s(sp), .rso_ctlm(ctlm), .rso_seq(seq));
    integer cyc = 0, errs = 0, checks = 0, t_rel = -1, t_io = -1, t_f = -1, t_s = -1, t_c = -1, t_q = -1, rerr = 0, i;
    integer seed = 1;
    function [511:0] r512; input integer s; integer k; begin for (k = 0; k < 16; k = k + 1) r512[k*32 +: 32] = $random(seed); end endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1;
        // stimulus: mostly-quiet valid strobes so the credit / retry logic runs in all states
        x3_v <= ($random(seed) & 7) == 0; x3_d <= r512(0); x3_tag <= $random(seed);
        ea_v <= ($random(seed) & 31) == 0; ea_kind <= $random(seed); ea_addr <= $random(seed);
        ar_cr <= ($random(seed) & 3) == 0; dc <= {$random(seed), $random(seed)}; kvd <= {$random(seed), $random(seed)};
        tx_up <= cyc > 40; rx_v <= ($random(seed) & 15) == 0;
        for (i = 0; i < PW; i = i + 32) rx_f[i +: 32] <= $random(seed);
        if (rst_n) begin
            checks <= checks + 1;
            if (dv !== rv) begin errs <= errs + 1; if (errs < 3) $display("MISMATCH cyc %0d", cyc); end
        end
        // reset sequencer: release at 100, re-assert at 400 for 3 edges, release again
        arst <= !(cyc < 100 || (cyc >= 400 && cyc < 403));
        if (cyc == 100) t_rel = cyc;
        if (cyc == 403) begin t_rel = cyc; t_io = -1; t_f = -1; t_s = -1; t_c = -1; t_q = -1; end
        if (cyc >= 401 && cyc < 404 && (io | fld | sp | ctlm | seq)) rerr = rerr + 1;   // re-assertion is immediate
        if (io   && t_io < 0) t_io = cyc;  if (fld && t_f < 0) t_f = cyc;  if (sp && t_s < 0) t_s = cyc;
        if (ctlm && t_c  < 0) t_c  = cyc;  if (seq && t_q < 0) t_q = cyc;
        if (cyc == 300 || cyc == N) begin
            if (!(t_io - t_rel >= 64 && t_io < t_f && t_f < t_s && t_s < t_c && t_c < t_q)) begin
                rerr = rerr + 1; $display("RESET ORDER FAIL rel %0d io %0d f %0d s %0d c %0d q %0d", t_rel, t_io, t_f, t_s, t_c, t_q);
            end
        end
        if (cyc == N) begin
            $display("LINK_SLOTS checks=%0d mismatches=%0d reset_errors=%0d MUT=%0d -> %s", checks, errs, rerr, MUT,
                     (errs == 0 && rerr == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
