`timescale 1ns/1ps
`default_nettype none
// tb_hnx_fused_tree (LH-P3UNITS/FUSHUB 2026-10-19): tb_hnx_fused on ot_hnx_fused_tree_top (die neighbour-hop csum tree +
// hub, E = landing handoff).  One N-row FUSED record against 32 fixed-latency
// VM bank lanes (bank L serves only lane L: a request on another bank is an error), vectors from
// tools/hbm_next/hnx_fused_vec.py (golden hdc_golden_v41 chunk8).  Run in the case dir: +NVMI= +NVME= (plus.txt).
// Prints HNX_FUSED_CYCLES (job launch edge -> done edge) and HNX_FUSED PASS / FAIL (exact words, no fault, every
// output sector written once, no bank violation).
module tb_hnx_fused_tree #(parameter integer KX = 4, RR = 10, RL = 4, MUT = 0, NMAX = 8, E = 2);
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    reg job_v = 1'b0; reg [216:0] job;
    wire done, fault, busy;
    wire [31:0] rq_v, wq_v; wire [32*16-1:0] rq_s, wq_s; wire [32*256-1:0] wq_d;
    reg [31:0] rr_v; reg [32*256-1:0] rr_d;
    ot_hnx_fused_tree_top #(.KX(KX), .RR(RR), .NMAX(NMAX), .MUT(MUT), .E(E)) dut (.clk(clk), .rst_n(rst_n), .job_v(job_v),
        .job(job), .done(done), .fault(fault), .busy(busy), .rq_v(rq_v), .rq_s(rq_s), .rr_v(rr_v), .rr_d(rr_d),
        .wq_v(wq_v), .wq_s(wq_s), .wq_d(wq_d));
    reg [255:0] vm [0:65535];
    reg [256:0] dl [0:31][0:RR-1];
    integer bankerr = 0, nwr = 0, nrd = 0;
    always @(posedge clk) begin
        for (integer L = 0; L < 32; L = L + 1) begin
            dl[L][0] <= {rq_v[L], vm[rq_s[L*16 +: 16]]};
            for (integer i = 1; i < RR; i = i + 1) dl[L][i] <= dl[L][i - 1];
            if (rq_v[L]) begin nrd = nrd + 1; if (rq_s[L*16 +: 5] != 5'(L)) bankerr = bankerr + 1; end
            if (wq_v[L]) begin
                vm[wq_s[L*16 +: 16]] <= wq_d[L*256 +: 256]; nwr = nwr + 1;
                if (wq_s[L*16 +: 5] != 5'(L)) bankerr = bankerr + 1;
            end
        end
    end
    always @* for (integer L = 0; L < 32; L = L + 1) begin rr_v[L] = dl[L][RR-1][256]; rr_d[L*256 +: 256] = dl[L][RR-1][255:0]; end

    localparam integer MAXE = 262144;
    reg [51:0] vmi [0:MAXE-1]; reg [51:0] vme [0:MAXE-1]; reg [219:0] jm [0:0];
    integer nvmi, nvme, cyc, mism, nflt = 0, ndone = 0, rgap, nrow, cc = 0, t0c = 0, t1c = 0;
    reg seen = 1'b0;
    always @(posedge clk) begin
        cc <= cc + 1;
        if (job_v) t0c <= cc;
        if ((done || fault) && !seen) begin seen <= 1'b1; t1c <= cc; if (fault) nflt <= 1; else ndone <= 1; end
    end
    reg [8*8-1:0] opn;
    initial begin
        if (!$value$plusargs("NVMI=%d", nvmi)) nvmi = 0;
        if (!$value$plusargs("NVME=%d", nvme)) nvme = 0;
        if (!$value$plusargs("RGAP=%d", rgap)) rgap = 0;
        if (!$value$plusargs("N=%d", nrow)) nrow = 0;
        if (!$value$plusargs("OP=%s", opn)) opn = "?";
        for (integer s = 0; s < 65536; s = s + 1) vm[s] = '0;
        $readmemh("vmi.mem", vmi, 0, nvmi - 1);
        $readmemh("vme.mem", vme, 0, nvme - 1);
        $readmemh("job.mem", jm);
        for (integer i = 0; i < nvmi; i = i + 1) vm[vmi[i][50:35]][32*vmi[i][34:32] +: 32] = vmi[i][31:0];
        job = jm[0][216:0];
        repeat (6) @(posedge clk);
        rst_n = 1'b1;
        repeat (8) @(posedge clk);
        #0.1 job_v = 1'b1;
        @(posedge clk); #0.1 job_v = 1'b0;
        while (!seen && cc < 90000) @(posedge clk);
        repeat (4 * RR + 8) @(posedge clk);
        cyc = t1c - 1 - t0c;
        mism = 0;
        for (integer i = 0; i < nvme; i = i + 1)
            if (vm[vme[i][50:35]][32*vme[i][34:32] +: 32] !== vme[i][31:0]) begin
                if (mism < 5) $display("MISMATCH word %0d: got %08h exp %08h", vme[i][50:32],
                                       vm[vme[i][50:35]][32*vme[i][34:32] +: 32], vme[i][31:0]);
                mism = mism + 1;
            end
        $display("HNX_FUSED_CYCLES op=%0s N=%0d rgap=%0d KX=%0d MUT=%0d cycles=%0d done=%0d fault=%0d reads=%0d writes=%0d",
                 opn, nrow, rgap, KX, MUT, cyc, ndone, nflt, nrd, nwr);
        if (ndone == 1 && nflt == 0 && mism == 0 && bankerr == 0 && nwr * 8 == nvme && nvme > 0)
            $display("HNX_FUSED PASS op=%0s N=%0d words=%0d", opn, nrow, nvme);
        else
            $display("HNX_FUSED FAIL op=%0s N=%0d mism=%0d fault=%0d done=%0d bankerr=%0d writes=%0d expect_sectors=%0d",
                     opn, nrow, mism, nflt, ndone, bankerr, nwr, nvme / 8);
        $finish;
    end
endmodule
`default_nettype wire
