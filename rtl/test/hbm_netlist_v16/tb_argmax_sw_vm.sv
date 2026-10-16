`timescale 1ns/1ps
`default_nettype none
// Bench: ot_hbm_argmax_static_sw_vm vs the gated ot_hbm_argmax_static_sw (am_stream idle) on the SAME random inputs:
// every VM-mode record (legal and illegal, random vm_rr / cr responses, random go spacing) must give identical outputs
// on every edge; every STREAM-mode record must end busy with fault (never hang) within 8 edges and write nothing.
module tb_argmax_sw_vm;
`ifndef NREC
`define NREC 400
`endif
`ifndef MUT
`define MUT 0
`endif
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg go = 0, mode = 0, a_mirror = 0; reg [17:0] imm_a = 0, a_base = 0, n = 0, o_base = 0; reg [15:0] o_is = 0;
    reg [2055:0] vm_rr = 0; reg [273:0] cr = 0;
    wire [135:0] rq0, rq1; wire [337:0] cq0, cq1; wire [1:0] s0, s1; wire b0, b1, d0, d1, f0, f1, n0, n1;
    ot_hbm_argmax_static_sw ref_(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(go && !mode), .mode(1'b0), .imm_a(imm_a),
        .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq0), .vm_rr(vm_rr),
        .am_stream(523'd0), .cq(cq0), .cq_seq(s0), .cr(cr), .busy(b0), .done(d0), .fault(f0), .nan_flag(n0));
    ot_hbm_argmax_static_sw_vm #(.MUT(`MUT)) dut(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(go), .mode(mode),
        .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq1),
        .vm_rr(vm_rr), .cq(cq1), .cq_seq(s1), .cr(cr), .busy(b1), .done(d1), .fault(f1), .nan_flag(n1));
    integer cyc = 0, mism = 0, vm_recs = 0, st_recs = 0, st_ok = 0, st_bad = 0, vm_done = 0, k, w;
    reg in_stream = 0; integer st_age = 0;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (!in_stream && {rq0, cq0, s0, b0, d0, f0, n0} !== {rq1, cq1, s1, b1, d1, f1, n1}) begin
            mism = mism + 1; if (mism < 5) $display("MISMATCH cyc %0d busy %b/%b done %b/%b fault %b/%b", cyc, b0, b1, d0, d1, f0, f1);
        end
        if (d1) vm_done = vm_done + 1;
    end
    task automatic rec(input m);
        begin
            @(negedge clk);
            mode = m; imm_a = $urandom % 40000; a_mirror = $urandom % 2; n = 1 + $urandom % 200;
            a_base = {(($urandom % 8) == 0) ? 2'd1 : 2'd0, 16'($urandom)}; o_base = {2'd0, 16'($urandom % 60000)};
            o_is = $urandom % 64; go = 1;
            @(negedge clk) go = 0;
        end
    endtask
    // Fixed-latency VM read group / record-client model (the slice's measured edges): a lane request answers RD edges
    // later with random data (random NaN-free FP32 most of the time) and its valid bit; a client write is acknowledged
    // ACKD edges later with its tag.  Every ERR-th record gets a garbage response (exercises the fault paths).
    `ifndef RD
    `define RD 7
    `endif
    `ifndef ACKD
    `define ACKD 12
    `endif
    reg [7:0] rqv [0:31]; reg [16:0] cqv [0:31]; integer t; reg garble = 0;
    always @(posedge clk) begin
        for (t = 31; t > 0; t = t - 1) begin rqv[t] <= rqv[t-1]; cqv[t] <= cqv[t-1]; end
        for (t = 0; t < 8; t = t + 1) rqv[0][t] <= rq0[17*t+16];
        cqv[0] <= {cq0[337], cq0[15:0]};
    end
    initial for (t = 0; t < 32; t = t + 1) begin rqv[t] = 0; cqv[t] = 0; end
    always @(negedge clk) begin
        for (k = 0; k < 8; k = k + 1) begin
            vm_rr[257*k +: 256] = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom} & {8{32'hBFFF_FFFF}};
            vm_rr[257*k+256] = garble ? $urandom : rqv[`RD-1][k];
        end
        cr = 0; cr[273] = cqv[`ACKD-1][16]; cr[272:257] = cqv[`ACKD-1][15:0]; cr[256] = cqv[`ACKD-1][16];
        if (garble) cr[273] = $urandom;
    end
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);
        for (w = 0; w < `NREC; w = w + 1) begin
            if (($urandom % 4) == 0) begin
                in_stream = 1; st_recs = st_recs + 1; rec(1); st_age = 0;
                while (b1 && st_age < 64) begin @(negedge clk); st_age = st_age + 1; if (f1) st_ok = st_ok + 1; end
                if (b1 || st_age > 8) st_bad = st_bad + 1;
                repeat (200) begin if (b1) @(negedge clk); end
                if (b1) begin $display("STREAM record hangs busy (no fault) at cyc %0d", cyc); $display("ARGMAX_SW_VM FAIL"); $finish; end
                @(negedge clk); while (b0 || b1) @(negedge clk);
                in_stream = 0;
            end else begin
                vm_recs = vm_recs + 1; garble = ($urandom % 8) == 0; rec(0);
                repeat ($urandom % 6) @(negedge clk);
                while (b0 || b1) @(negedge clk);
                repeat ($urandom % 4) @(negedge clk);
            end
        end
        $display("vm records %0d (done %0d) stream records %0d (fault %0d, bad %0d) mismatching edges %0d",
                 vm_recs, vm_done, st_recs, st_ok, st_bad, mism);
        if (mism == 0 && st_bad == 0 && st_ok == st_recs && vm_done > vm_recs / 2) $display("ARGMAX_SW_VM PASS"); else $display("ARGMAX_SW_VM FAIL");
        $finish;
    end
endmodule
`default_nettype wire
