`timescale 1ns/1ps
// tb_dsfd_host_c (s81-die-rtl-bind 2026-10-14, F6): the layer-die host master at its die pins (ck 1.2 GHz, ckv 0.9 GHz).
// The far end (collective) sends, under the host's credits (16 at reset, h_crn returns), a host stream mixing
// sequencer CSR words (program length, NPW program words {a, d28}) and ingest CSR words (class 0 index 0 'share', the
// ingest's own register) in random order.  Checks: the sequencer side (ckv) sees exactly the NPW program words in
// order (t_sseq_pw = {1, a, d}) and t_sseq_plen = the length; every word sent comes back as one credit; the ingest
// received exactly the non-sequencer words (its h_v count); status: a sequencer fault (f_sseq_st[5]) and a WFC fault
// reach t_collective's st, no ingest/decode fault.  PASS line TB_DSFD_HOST_C ... PASS.  MUT 1 / 2 must FAIL.
module tb_dsfd_host_c;
    parameter integer MUT = 0, NPW = 40, NSH = 12;
    reg ck = 0, ckv = 0, rst = 0, rsv = 0;
    always #0.41667 ck = ~ck;
    always #0.55556 ckv = ~ckv;
    reg [515:0] fc = 0; wire [80:0] tc; wire [35:0] pw; wire [7:0] plen; reg [5:0] sst = 6'd0; reg [3:0] wft = 0;
    wire [291:0] hw; reg [8:0] hc = 0;
    dsfd_host_c #(.NS(1), .KVS(1), .ENG(-1), .MUT(MUT)) dut (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_collective(fc),
        .t_collective(tc), .t_sseq_pw(pw), .t_sseq_plen(plen), .f_sseq_st(sst), .f_wfc_ft(wft), .hw(hw), .hc(hc));
    integer cred = 16, sent = 0, sent_pw = 0, sent_sh = 0, ret = 0, cyc = 0, got_pw = 0, bad_pw = 0, ing = 0;
    reg [34:0] expw [0:NPW-1];
    integer i;
    initial begin
        for (i = 0; i < NPW; i = i + 1) expw[i] = {7'(i * 3 + 1), 28'($urandom)};
        repeat (6) @(posedge ckv); rst = 1; rsv = 1;
    end
    // far end: one word a cycle while credits last
    always @(negedge ck) if (rst) begin : snd
        reg [511:0] d;
        cyc = cyc + 1;
        fc <= 516'd0;
        if (cyc > 20 && cred > 0 && (sent_pw < NPW || sent_sh < NSH || sent == 0) && ($urandom % 3) != 0) begin
            d = 512'd0;
            if (sent == 0) begin d[7:0] = 8'h11; d[39:32] = NPW; end
            else if (sent_pw < NPW && (sent_sh >= NSH || ($urandom % 4) != 0)) begin
                d[7:0] = 8'h10; d[102:96] = expw[sent_pw][34:28]; d[59:32] = expw[sent_pw][27:0]; sent_pw = sent_pw + 1;
            end else begin d[7:0] = 8'h00; d[63:32] = 32'd0; sent_sh = sent_sh + 1; end      // ingest CSR 0 (share = 0)
            fc <= {1'b0, 2'd0, d, 1'b1};
            cred = cred - 1; sent = sent + 1;
        end
        if (cyc == 3000) sst <= 6'b100000;
        if (cyc == 3100) wft <= 4'b0010;
    end
    always @(posedge ck) if (rst) begin
        cred = cred + tc[69:65]; ret = ret + tc[69:65];
        if (dut.u_h.h_v) ing = ing + 1;
    end
    always @(posedge ckv) if (rsv && pw[35]) begin
        if (got_pw >= NPW || pw[34:0] !== expw[got_pw]) begin bad_pw = bad_pw + 1; if (bad_pw < 4) $display("ERR program word %0d", got_pw); end
        got_pw = got_pw + 1;
    end
    initial begin
        wait (cyc == 4000);
        $display("TB_DSFD_HOST_C MUT=%0d sent=%0d (program %0d, ingest %0d) credits_back=%0d program_words=%0d bad=%0d plen=%0d ingest_words=%0d st=%b %s",
            MUT, sent, sent_pw, sent_sh, ret, got_pw, bad_pw, plen, ing, tc[80:70],
            (got_pw == NPW && bad_pw == 0 && plen == NPW && ret == sent && ing == sent_sh && tc[80] && tc[79:76] == 4'b0010 && tc[75] && !dut.hf && !dut.sf) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
