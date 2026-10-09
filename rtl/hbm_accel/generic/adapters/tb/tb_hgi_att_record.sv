`timescale 1ns/1ps
// hgi-adapters (2026-10-09): bench of ot_hgi_att_issue (the att consumer of the G12 record adapter).
// Vectors: tools/hgi_adapters/att_bench.py (+DIR=).  RUN cases: every job word at issue == the reference, each record
// retires once, in order, only after the stub controller's done (random ready / latency).  NEGATIVE: att_fault, no job.
// Prints HGI_ATT PASS / FAIL.
module tb_hgi_att_record;
`ifdef MUT_LANES
    localparam integer ML = 1;
`else
    localparam integer ML = 0;
`endif
    `include "att_sizes.svh"
    reg clk = 0;
    always #1 clk = ~clk;
    reg [1172:0] recm [0:NREC-1];
    reg [162:0]  refm [0:NREC-1];
    reg [95:0]   casem [0:NCASE-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/att_rec.mem"}, recm); $readmemh({dir, "/att_ref.mem"}, refm); $readmemh({dir, "/att_case.mem"}, casem);
    end
    integer errors = 0, seed = 3;
    reg rst_n = 0; reg [1172:0] cur; reg v = 0;
    wire r, done, fault, job_v; wire [160:0] job; reg job_rdy = 0, job_done = 0;
    ot_hgi_att_issue #(.MUT_LANES(ML)) u (.clk(clk), .rst_n(rst_n), .att_v(v), .att_r(r), .att_hdr(cur[127:0]),
        .att_desc({cur[1151:896], cur[895:640], cur[639:384], cur[383:128]}), .att_pos1(cur[1172:1152]),
        .att_done(done), .att_fault(fault), .job_v(job_v), .job_rdy(job_rdy), .job(job), .job_done(job_done), .job_fault(1'b0));
    integer k = 0, base = 0, issued = 0, lat = -1, nfault = 0;
    reg [162:0] rw;
    always @(posedge clk) begin
        rw = refm[base + k];
        job_rdy <= $random(seed) & 1; job_done <= 0;
        if (rst_n && job_v && job_rdy) begin
            issued = issued + 1; lat = 2 + ($random(seed) & 31);
            if (rw[162:161] != 2'd0 || job !== rw[160:0]) begin
                $display("ERR job mismatch at record %0d: %h vs %h", base + k, job, rw[160:0]); errors = errors + 1; end
        end else if (lat > 0) lat = lat - 1;
        else if (lat == 0) begin job_done <= 1; lat = -1; end
        if (rst_n && done) begin
            if (lat != -1 || job_done) begin $display("ERR record %0d retired early", base + k); errors = errors + 1; end
            k = k + 1;
        end
        if (rst_n && fault) begin nfault = nfault + 1; k = k + 1; end
    end
    integer c, j, kind, r0, nr, t, runs = 0, negs = 0;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][95:64]; r0 = casem[c][63:32]; nr = casem[c][31:0];
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
            base = r0; k = 0; issued = 0; nfault = 0; lat = -1;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; v = 1;
                t = 0; while (!r && t < 20000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 v = 0;
            end
            t = 0; while (k < nr && t < 20000) begin @(posedge clk); t = t + 1; end
            repeat (10) @(posedge clk);
            if (kind == 0) begin
                if (k != nr || nfault != 0 || issued != nr) begin
                    $display("ERR run case %0d: retired %0d issued %0d of %0d faults %0d", c, k, issued, nr, nfault); errors = errors + 1; end
                runs = runs + nr;
            end else if (nfault != 1 || issued != 0) begin $display("ERR negative case %0d", c); errors = errors + 1; end
            else negs = negs + 1;
        end
        $display("summary: %0d ATT records run (CF-ATT 43 + Qwen 144), %0d negatives refused", runs, negs);
        if (errors == 0) $display("HGI_ATT PASS"); else $display("HGI_ATT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
