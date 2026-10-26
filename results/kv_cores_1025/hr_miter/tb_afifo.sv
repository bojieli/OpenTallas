`timescale 1ns/1ps
// KV-CORE-RTL/HR 2026-10-25: lockstep miter on ONE clock: ot_link_afifo SAMECLK=1 (plain register stage, DUT) vs
// ot_link_afifo SYNC=1 SAMECLK=0 (reference: the unchanged Gray/synchroniser construction with one stage, same cycle
// behaviour by construction).  Every output compared every cycle.  OLD = SYNC=2 (the shipped path) for latency only.
module tb_afifo;
    parameter integer W = 64, AW = 4, NCYC = 200000;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0, wr = 0, rd = 0; reg [W-1:0] wd = 0;
    wire df, rf, dov, rov, de, re; wire [AW:0] dfr, rfr, dc, rc; wire [W-1:0] dd, rdd;
    ot_link_afifo #(.W(W), .AW(AW), .SYNC(2), .SAMECLK(1)) dut (.wclk(clk), .wrst_n(rst_n), .wr(wr), .wdata(wd), .wfull(df),
        .wfreed(dfr), .ovf(dov), .rclk(clk), .rrst_n(rst_n), .rd(rd), .rempty(de), .rdata(dd), .rcount(dc));
    ot_link_afifo #(.W(W), .AW(AW), .SYNC(1), .SAMECLK(0)) ref_ (.wclk(clk), .wrst_n(rst_n), .wr(wr), .wdata(wd), .wfull(rf),
        .wfreed(rfr), .ovf(rov), .rclk(clk), .rrst_n(rst_n), .rd(rd), .rempty(re), .rdata(rdd), .rcount(rc));
    // latency probes: old path (SYNC=2) and DUT in a directed single-word run (separate instances, own stimulus)
    reg lwr = 0, lrd = 0; wire oe, ne, of_, nf; wire [AW:0] ofr, nfr, oc, nc; wire [W-1:0] od, nd; wire oov, nov;
    ot_link_afifo #(.W(W), .AW(AW), .SYNC(2), .SAMECLK(0)) old_ (.wclk(clk), .wrst_n(rst_n), .wr(lwr), .wdata(wd), .wfull(of_),
        .wfreed(ofr), .ovf(oov), .rclk(clk), .rrst_n(rst_n), .rd(lrd), .rempty(oe), .rdata(od), .rcount(oc));
    ot_link_afifo #(.W(W), .AW(AW), .SYNC(2), .SAMECLK(1)) new_ (.wclk(clk), .wrst_n(rst_n), .wr(lwr), .wdata(wd), .wfull(nf),
        .wfreed(nfr), .ovf(nov), .rclk(clk), .rrst_n(rst_n), .rd(lrd), .rempty(ne), .rdata(nd), .rcount(nc));
    integer cyc = 0, bad = 0, cmp = 0, pw = 50, pr = 50, nfull = 0, novf = 0, t0 = -1, lo = -1, ln = -1, fo = -1, fn = -1;
    always @(negedge clk) if (rst_n) begin
        cmp = cmp + 1;
        if (df !== rf || dfr !== rfr || dov !== rov || de !== re || dc !== rc || (!re && dd !== rdd)) begin
            if (bad < 5) $display("MISMATCH cyc %0d: full %b/%b freed %0d/%0d ovf %b/%b empty %b/%b cnt %0d/%0d data %0s",
                cyc, df, rf, dfr, rfr, dov, rov, de, re, dc, rc, (dd === rdd) ? "eq" : "DIFF");
            bad = bad + 1;
        end
        if (df) nfull = nfull + 1;
        if (dov) novf = novf + 1;
    end
    always @(posedge clk) cyc <= cyc + 1;
    initial begin
        repeat (3) @(negedge clk); rst_n = 1;
        // directed latency: one word written at edge t0, popped as soon as visible
        @(negedge clk); lwr = 1; t0 = cyc; @(negedge clk); lwr = 0;
        repeat (8) begin
            if (lo < 0 && !oe) lo = cyc - t0;
            if (ln < 0 && !ne) ln = cyc - t0;
            @(negedge clk);
        end
        lrd = 1; @(negedge clk); lrd = 0; t0 = cyc;
        repeat (8) begin
            if (fo < 0 && ofr != 0) fo = cyc - t0;
            if (fn < 0 && nfr != 0) fn = cyc - t0;
            @(negedge clk);
        end
        // random lockstep (wr also while full -> ovf exercised once late)
        repeat (NCYC) begin
            if (($urandom % 4096) == 0) begin pw = $urandom % 101; pr = $urandom % 101; end
            wr = (($urandom % 100) < pw) && (!df || cyc > NCYC - 2000);
            rd = (($urandom % 100) < pr);
            wd = {W/32+1{$urandom}};
            @(negedge clk);
        end
        $display("LATENCY write->visible edges: SYNC2(old)=%0d SAMECLK(new)=%0d ; pop->wfreed edges: old=%0d new=%0d", lo, ln, fo, fn);
        $display("%s W=%0d AW=%0d cycles_compared=%0d mismatches=%0d full_cycles=%0d ovf_cycles=%0d",
            (bad == 0) ? "MITER PASS" : "MITER FAIL", W, AW, cmp, bad, nfull, novf);
        $finish;
    end
endmodule
