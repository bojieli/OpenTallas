`timescale 1ns/1ps
// tb_dsfd_host_c_static (S-BIND r6 2026-10-15): dsfd_host_c +DSFD_HOST_C_STATIC at its die pins (ck 1.2 GHz, ckv 0.9 GHz).
// The far end (the static collective's host channel) sends NO-CREDIT host-stream words on fixed slots (every 3rd edge,
// the compiler's host slots): program length, NPW sequencer program words and NSH ingest CSR words.  There is no credit
// return to wait for (t_collective has no h_crn field).  Checks: the sequencer side (ckv) sees exactly the NPW program
// words in order and t_sseq_plen = NPW; the ingest received exactly the non-sequencer words; alive = 1 after reset; no
// fault before edge 2500; a forwarded-lane fault injected on f_lf at 2500 (an hc-end {fault, live} pair) reaches
// t_collective's status fault by 2800; the sequencer fault (3000) and a WFC fault (3100) reach st.  PASS line
// TB_DSFD_HOST_C_STATIC ... PASS.  MUT 1 (program words dropped) and MUT 4 (lane faults not folded) must FAIL.
module tb_dsfd_host_c_static;
    parameter integer MUT = 0, NPW = 40, NSH = 12;
    reg ck = 0, ckv = 0, rst = 0, rsv = 0;
    always #0.41667 ck = ~ck;
    always #0.55556 ckv = ~ckv;
    reg [514:0] fc = 0; wire [76:0] tc; wire [35:0] pw; wire [7:0] plen; reg [5:0] sst = 6'd0; reg [3:0] wft = 0;
    wire [291:0] hw; reg [8:0] hc = 0; reg [3:0] lf = 4'b0101;
    dsfd_host_c #(.NS(1), .KVS(1), .ENG(-1), .MUT(MUT)) dut (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_collective(fc),
        .t_collective(tc), .f_lf(lf), .t_sseq_pw(pw), .t_sseq_plen(plen), .f_sseq_st(sst), .f_wfc_ft(wft), .hw(hw), .hc(hc));
    integer sent = 0, sent_pw = 0, sent_sh = 0, cyc = 0, got_pw = 0, bad_pw = 0, ing = 0, early_fault = 0, lane_fault_seen = 0;
    reg [34:0] expw [0:NPW-1];
    integer i;
    initial begin
        for (i = 0; i < NPW; i = i + 1) expw[i] = {7'(i * 3 + 1), 28'($urandom)};
        repeat (6) @(posedge ckv); rst = 1; rsv = 1;
    end
    // far end: one word on every 3rd edge (a fixed host-slot cadence), no credits
    always @(negedge ck) if (rst) begin : snd
        reg [511:0] d;
        cyc = cyc + 1;
        fc <= 515'd0;
        if (cyc > 20 && cyc % 3 == 0 && (sent_pw < NPW || sent_sh < NSH || sent == 0)) begin
            d = 512'd0;
            if (sent == 0) begin d[7:0] = 8'h11; d[39:32] = NPW; end
            else if (sent_pw < NPW && (sent_sh >= NSH || ($urandom % 4) != 0)) begin
                d[7:0] = 8'h10; d[102:96] = expw[sent_pw][34:28]; d[59:32] = expw[sent_pw][27:0]; sent_pw = sent_pw + 1;
            end else begin d[7:0] = 8'h00; d[63:32] = 32'd0; sent_sh = sent_sh + 1; end      // ingest CSR 0 (share = 0)
            fc <= {2'd0, d, 1'b1};
            sent = sent + 1;
        end
        if (cyc == 2500) lf <= 4'b0111;      // hc-end pair {fault 1, live 1}
        if (cyc == 3000) sst <= 6'b100000;
        if (cyc == 3100) wft <= 4'b0010;
    end
    always @(posedge ck) if (rst) begin
        if (dut.u_h.h_v) ing = ing + 1;
        if (cyc > 100 && cyc < 2500 && tc[75]) early_fault = early_fault + 1;
        if (cyc == 2800 && tc[75] && tc[76]) lane_fault_seen = 1;
    end
    always @(posedge ckv) if (rsv && pw[35]) begin
        if (got_pw >= NPW || pw[34:0] !== expw[got_pw]) begin bad_pw = bad_pw + 1; if (bad_pw < 4) $display("ERR program word %0d", got_pw); end
        got_pw = got_pw + 1;
    end
    initial begin
        wait (cyc == 4000);
        $display("TB_DSFD_HOST_C_STATIC MUT=%0d sent=%0d (program %0d, ingest %0d) program_words=%0d bad=%0d plen=%0d ingest_words=%0d early_fault=%0d lane_fault=%0d st=%b alive=%b %s",
            MUT, sent, sent_pw, sent_sh, got_pw, bad_pw, plen, ing, early_fault, lane_fault_seen, tc[75:65], tc[76],
            (got_pw == NPW && bad_pw == 0 && plen == NPW && ing == sent_sh && early_fault == 0 && lane_fault_seen && tc[76]
             && tc[75] && tc[74:71] == 4'b0010 && tc[70] && !dut.hf && !dut.sf) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
