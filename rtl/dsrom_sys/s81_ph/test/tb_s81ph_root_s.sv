`timescale 1ns/1ps
// tb_s81ph_root_s (s81-gather 2026-10-13): CYCLE-EXACT lockstep of ot_s81ph_ret_root_s (SRAM queue + CAM-free pairing
// store; flop arrays and the two hard-macro models) against ot_s81ph_ret_root_p (the flat gather's root) on one
// partial stream (+STIM, gen_root_stim.py).  Every cycle: r_v equal, and with r_v the row / pos / fp32 / bf16 / e
// equal; fault equal.  The stated latency difference is 0 cycles, so any shift is a mismatch.
//   +EXPECT=0  lockstep, no fault on either side (default)
//   +EXPECT=1  capacity / malformed case: root_s must fault, root_p must not; every row root_s emitted BEFORE its
//              fault rose is a row root_p emitted too, same value (fail closed: nothing wrong leaves unflagged)
//   +EXPECT=2  both roots fault (queue full, duplicate partial); same row criterion
//   +NEED=<mask>  COVERAGE REFUSAL: the bench refuses PASS unless every named event was seen in root_s:
//       1 add with the partial the previous decision inserted (forward)   2 same key, other parent node (forward)
//       4 a freed slot allocated again        8 insert into a slot freed after its look-ahead
//       16 queue read the cycle after the word's write (forward from the write register)
//       32 queue depth >= 64                  64 S slots open at once       128 slot overflow fault
//       256 queue-full fault                  512 add at tree level 4       1024 malformed tag fault
//       2048 duplicate partial fault
module tb_s81ph_root_s;
    parameter integer S = 8;
    reg clk = 0; always #3 clk = ~clk;
    reg rst_n = 0;
    reg i_v = 0; reg [31:0] i_t = 0, i_d = 0; reg i_e = 0;
    wire pv, sv_, mv; wire [15:0] prow, srow, mrow, pbf, sbf, mbf; wire [2:0] ppos, spos, mpos;
    wire [31:0] pfp, sfp, mfp; wire pe, se, me, pf, sf, mf;
    ot_s81ph_ret_root_p #(.D(128), .QD(128)) u_p (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_t(i_t), .i_d(i_d), .i_e(i_e),
        .r_v(pv), .r_row(prow), .r_pos(ppos), .r_fp32(pfp), .r_bf16(pbf), .r_e(pe), .fault(pf));
    ot_s81ph_ret_root_s #(.S(S), .QD(128), .SRAM(0)) u_s (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_t(i_t), .i_d(i_d), .i_e(i_e),
        .r_v(sv_), .r_row(srow), .r_pos(spos), .r_fp32(sfp), .r_bf16(sbf), .r_e(se), .fault(sf));
    ot_s81ph_ret_root_s #(.S(S), .QD(128), .SRAM(1)) u_m (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_t(i_t), .i_d(i_d), .i_e(i_e),
        .r_v(mv), .r_row(mrow), .r_pos(mpos), .r_fp32(mfp), .r_bf16(mbf), .r_e(me), .fault(mf));
    integer cyc = 0, mism = 0, rows_p = 0, rows_s = 0, words = 0, quiet = 0, first_bad = -1, notin = 0, macro_mism = 0;
    integer expect_ = 0, need = 0, cov;
    reg [31:0] prow_d [bit [18:0]];          // root_p rows by {pos, row}
    wire [69:0] po = {pv, prow, ppos, pfp, pbf, pe, pf};
    wire [69:0] so = {sv_, srow, spos, sfp, sbf, se, sf};
    wire [69:0] mo = {mv, mrow, mpos, mfp, mbf, me, mf};
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            if (pv) begin rows_p = rows_p + 1; prow_d[{ppos, prow}] = pfp; end
            if (sv_) rows_s = rows_s + 1;
            // macro build == flop build, always
            if (mv !== sv_ || mf !== sf || (sv_ && mo !== so)) begin macro_mism = macro_mism + 1; if (macro_mism < 4) $display("MACRO MISMATCH cycle %0d: s %h m %h", cyc, so, mo); end
            if (expect_ == 0) begin
                if (pv !== sv_ || pf !== sf || (pv && po !== so)) begin
                    mism = mism + 1; if (first_bad < 0) first_bad = cyc;
                    if (mism < 6) $display("MISMATCH cycle %0d: p v=%b row=%0d pos=%0d fp=%h e=%b f=%b | s v=%b row=%0d pos=%0d fp=%h e=%b f=%b",
                                           cyc, pv, prow, ppos, pfp, pe, pf, sv_, srow, spos, sfp, se, sf);
                end
            end
            quiet = (pv || sv_ || i_v) ? 0 : quiet + 1;
        end
    end
    // fail-closed check for the fault cases: every row root_s emitted must be a root_p row with the same value
    reg [50:0] srows [$];
    always @(posedge clk) if (rst_n && sv_ && !sf) srows.push_back({spos, srow, sfp});   // rows before the fault only
    integer fd, rc, gap, j;
    reg [8*8-1:0] cmd; reg [63:0] a0, a1, a2, a3;
    string stim;
    task automatic idle(input integer n); integer q; begin for (q = 0; q < n; q = q + 1) @(negedge clk); end endtask
    initial begin
        if (!$value$plusargs("STIM=%s", stim)) $fatal(1, "+STIM");
        if (!$value$plusargs("EXPECT=%d", expect_)) expect_ = 0;
        if (!$value$plusargs("NEED=%d", need)) need = 0;
        fd = $fopen(stim, "r");
        if (fd == 0) $fatal(1, "cannot open %s", stim);
        idle(6); rst_n = 1; idle(20);
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%s", cmd);
            if (rc != 1) break;
            if (cmd == "C") begin
                rc = $fscanf(fd, "%h %h %h %h", a0, a1, a2, a3);
                if (a0 > 1) idle(a0 - 1);
                i_v = 1; i_t = a1; i_d = a2; i_e = a3; words = words + 1;
                @(negedge clk); i_v = 0;
            end else if (cmd == "E") begin
                j = 0; while (quiet < 300 && j < 200000) begin @(negedge clk); j = j + 1; end
            end
        end
        idle(400);
        cov = (u_s.cv_fwd_add ? 1 : 0) | (u_s.cv_fwd_oth ? 2 : 0) | (u_s.cv_reuse ? 4 : 0) | (u_s.cv_reval ? 8 : 0)
            | (u_s.cv_qfwd ? 16 : 0) | (u_s.ob_q_pk >= 64 ? 32 : 0) | (u_s.ob_open_pk >= S ? 64 : 0) | (u_s.cv_ovf ? 128 : 0)
            | (u_s.cv_qfull ? 256 : 0) | (u_s.cv_lvl4 ? 512 : 0) | (u_s.cv_bad ? 1024 : 0) | (u_s.cv_dup ? 2048 : 0);
        if (expect_ != 0) begin
            for (j = 0; j < srows.size(); j = j + 1)
                if (!prow_d.exists(srows[j][50:32]) || prow_d[srows[j][50:32]] !== srows[j][31:0]) notin = notin + 1;
        end
        $display("SUMMARY words=%0d rows_p=%0d rows_s=%0d mismatch_cycles=%0d first=%0d macro_mismatch=%0d fault_p=%b fault_s=%b open_peak=%0d q_peak=%0d rows_s_not_in_p=%0d cov=%0d need=%0d latency_delta=0",
                 words, rows_p, rows_s, mism, first_bad, macro_mism, pf, sf, u_s.ob_open_pk, u_s.ob_q_pk, notin, cov, need);
        if ((cov & need) != need) $display("RESULT REFUSED coverage missing %0d", need & ~cov);
        else if (macro_mism != 0) $display("RESULT FAIL macro build differs");
        else if (expect_ == 0 && mism == 0 && !pf && !sf && rows_p == rows_s && rows_p > 0) $display("RESULT PASS");
        else if (expect_ == 1 && sf && !pf && notin == 0) $display("RESULT PASS");
        else if (expect_ == 2 && sf && pf && notin == 0) $display("RESULT PASS");
        else $display("RESULT FAIL");
        $finish;
    end
endmodule
