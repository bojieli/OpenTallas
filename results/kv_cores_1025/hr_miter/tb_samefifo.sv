`timescale 1ns/1ps
// KV-CORE-RTL/HR 2026-10-25: lockstep miter on ONE clock: ot_qwen_same_fifo_w (the SAMECLK body of ot_qwen_die_cdc_ch,
// DUT) vs an independent queue reference model with the documented cycle behaviour: a word accepted at edge e is
// readable 2 edges after the accepting edge (one register stage), ready = accepted-not-popped < DEPTH, RSEL2: rd_data = word popped at the
// previous edge (RSEL2=0: the head).  Outputs compared every cycle.
module tb_samefifo;
    parameter integer W = 546, D = 8, RSEL2 = 1, NCYC = 200000;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0, wv = 0, rr = 0; reg [W-1:0] wd = 0;
    wire dr, dv, ddr; wire [W-1:0] dd;
    ot_qwen_same_fifo_w #(.WIDTH(W), .DEPTH(D), .RSEL2(RSEL2)) dut (.clk(clk), .rst_n(rst_n), .wr_valid(wv), .wr_ready(dr),
        .wr_data(wd), .rd_valid(dv), .rd_ready(rr), .rd_data(dd), .drained(ddr));
    reg [W-1:0] qd [$]; integer qv [$]; reg [W-1:0] last; reg popped = 0;
    integer e = 0, bad = 0, cmp = 0, pw = 50, pr = 50, nfull = 0;
    wire ref_ready = (qd.size() < D);
    wire ref_valid = (qd.size() > 0) && (qv[0] <= e);
    always @(posedge clk) if (rst_n) begin
        e <= e + 1;
        if (rr) begin last <= qd[0]; void'(qd.pop_front()); void'(qv.pop_front()); popped <= 1; end
        if (wv) begin qd.push_back(wd); qv.push_back(e + 2); end
    end
    always @(negedge clk) if (rst_n) begin
        cmp = cmp + 1;
        if (dr !== ref_ready || dv !== ref_valid || ddr !== (qd.size() == 0) ||
            (RSEL2 != 0 && popped && dd !== last) || (RSEL2 == 0 && ref_valid && dd !== qd[0])) begin
            if (bad < 5) $display("MISMATCH edge %0d: ready %b/%b valid %b/%b data %0s", e, dr, ref_ready, dv, ref_valid,
                ((RSEL2 != 0) ? (dd === last) : (dd === qd[0])) ? "eq" : "DIFF");
            bad = bad + 1;
        end
        if (!dr) nfull = nfull + 1;
    end
    initial begin
        repeat (3) @(negedge clk); rst_n = 1;
        repeat (NCYC) begin
            @(negedge clk);
            if (($urandom % 4096) == 0) begin pw = $urandom % 101; pr = $urandom % 101; end
            wv = (($urandom % 100) < pw) && dr;
            rr = (($urandom % 100) < pr) && dv;
            wd = {W/32+1{$urandom}};
        end
        $display("%s W=%0d D=%0d RSEL2=%0d cycles_compared=%0d mismatches=%0d full_cycles=%0d",
            (bad == 0) ? "MITER PASS" : "MITER FAIL", W, D, RSEL2, cmp, bad, nfull);
        $finish;
    end
endmodule
