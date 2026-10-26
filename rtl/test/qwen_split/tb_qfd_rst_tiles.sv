`timescale 1ns/1ps
// Exact production-shape bench of the compute die's reset entry tiles (rtl/qwen_split/qfd_link_slots.sv):
//   qfd_rstsync  (2-flop synchroniser of the forwarded reset + forwarded-release flop), and
//   qfd_rstseq   (die reset sequencer) at its PRODUCTION parameters FLUSH 512 / STEP 256 (no overrides),
// chained exactly as on the die (rstsync.rso_f -> rstseq.rsi).  A cycle-exact reference model of both is compared on
// every edge (and immediately after each asynchronous assertion), plus the order property io <= f <= s <= ctlm <= seq
// and the release distances (FLUSH, STEP).  Scenarios: power-on, two full sequences, a reset glitch in the FLUSH window,
// a reset during each release step, a 1-edge pulse, a long hold.  Prints RST_TILES ... PASS|FAIL.
// Mutants (compile defines in the RTL): OT_QFD_RSTSYNC_MUT (forwarded release early), OT_QFD_RSTSEQ_MUT (seq with ctlm).
module tb_qfd_rst_tiles;
    localparam integer FLUSH = 512, STEP = 256;
    reg ck = 0, arst_n = 0;
    always #0.41667 ck = ~ck;
    wire rso_d, rso_f, io, fld, sp, ctlm, seq;
    qfd_rstsync u_rs (.ck(ck), .arst_n(arst_n), .rso_d(rso_d), .rso_f(rso_f));
    qfd_rstseq u_seq (.ck(ck), .rsi(rso_f), .rso_io(io), .rso_f(fld), .rso_s(sp), .rso_ctlm(ctlm), .rso_seq(seq));
    // reference model
    reg [1:0] m_s; reg m_f; reg [1:0] q_s; integer q_n; reg [4:0] q_o;
    wire m_rsi = m_f;
    always @(posedge ck or negedge arst_n)
        if (!arst_n) begin m_s <= 0; m_f <= 0; end else begin m_s <= {m_s[0], 1'b1}; m_f <= m_s[1]; end
    always @(posedge ck or negedge m_rsi)
        if (!m_rsi) begin q_s <= 0; q_n <= 0; q_o <= 0; end
        else begin
            q_s <= {q_s[0], 1'b1};
            if (q_s[1] && q_n != FLUSH + 4 * STEP) q_n <= q_n + 1;
            q_o <= {q_s[1] && q_n >= FLUSH + 4 * STEP, q_s[1] && q_n >= FLUSH + 3 * STEP, q_s[1] && q_n >= FLUSH + 2 * STEP,
                    q_s[1] && q_n >= FLUSH + STEP, q_s[1] && q_n >= FLUSH};
        end
    integer cyc = 0, checks = 0, errs = 0, ord = 0, rel_seq = 0, last_rel = -1, rise_io = -1, rise_seq = -1, gaps_ok = 0;
    reg [4:0] prev = 0;
    wire [4:0] dut = {seq, ctlm, sp, fld, io};
    task automatic cmp;
        begin
            checks = checks + 1;
            if (rso_d !== m_s[1] || rso_f !== m_f || dut !== q_o) begin
                errs = errs + 1;
                if (errs <= 5) $display("MISMATCH cyc=%0d rso_d %b/%b rso_f %b/%b seq %b/%b", cyc, rso_d, m_s[1], rso_f, m_f, dut, q_o);
            end
            // order property: a later domain is never released before an earlier one
            if ((seq & ~ctlm) | (ctlm & ~sp) | (sp & ~fld) | (fld & ~io)) ord = ord + 1;
        end
    endtask
    always @(negedge ck) begin
        cmp;
        if (io & ~prev[0]) rise_io = cyc;
        if (seq & ~prev[4]) begin
            rise_seq = cyc; rel_seq = rel_seq + 1;
            if (rise_io >= 0 && rise_seq - rise_io == 4 * STEP) gaps_ok = gaps_ok + 1;
        end
        prev = dut;
    end
    // scenario: arst_n schedule (edges), asynchronous assertion mid-cycle
    task automatic hold_rst(input integer n); begin #0.2 arst_n = 0; #0.01 cmp; repeat (n) @(posedge ck); #0.2 arst_n = 1; end endtask
    always @(posedge ck) cyc <= cyc + 1;
    initial begin
        repeat (5) @(posedge ck);
        #0.2 arst_n = 1;                                            // power-on release
        repeat (FLUSH + 4 * STEP + 40) @(posedge ck);               // full sequence
        hold_rst(10); repeat (FLUSH + 4 * STEP + 40) @(posedge ck); // second full sequence
        hold_rst(3);  repeat (FLUSH / 2) @(posedge ck);             // glitch inside FLUSH
        hold_rst(1);  repeat (FLUSH + STEP / 2) @(posedge ck);      // 1-edge pulse, then reset during step 1
        hold_rst(2);  repeat (FLUSH + 2 * STEP + 7) @(posedge ck);  // reset during step 2..3
        hold_rst(5);  repeat (FLUSH + 3 * STEP + 100) @(posedge ck);
        hold_rst(200); repeat (FLUSH + 4 * STEP + 40) @(posedge ck); // long hold then full sequence
        $display("RST_TILES checks=%0d mismatches=%0d order_errors=%0d seq_releases=%0d step_gaps_ok=%0d -> %s",
                 checks, errs, ord, rel_seq, gaps_ok, (errs == 0 && ord == 0 && rel_seq == 3 && gaps_ok == 3) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
