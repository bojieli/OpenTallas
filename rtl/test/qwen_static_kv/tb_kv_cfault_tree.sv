// KVJ-SMALL (c) bench: qkd_kv_cfault_tree, N 128 radix 4 (4 levels) at STAGES 1 and 2.
//  1. reset: output 0 while in reset and for 3*LAT edges after release with no fault;
//  2. for EVERY leaf i in 0..127: assert the (sticky) fault at a random-phase edge; the output must be 0 for exactly
//     LAT-1 edges and 1 at edge LAT (exact latency), and stay 1 while the source holds; then core reset clears it;
//  3. two simultaneous faults (i, 127-i): same latency;
//  4. no fault for 2000 edges with all leaves 0 -> 0.
// Prints "PASS kv_cfault_tree" / "FAIL kv_cfault_tree ...".  MUT 1 (leaf 20 dropped) and MUT 2 (root unregistered)
// must FAIL.
`timescale 1ns/1ps
module tb_kv_cfault_tree;
    parameter integer MUT = 0;
    parameter integer STAGES = 1;
    localparam integer N = 128, R = 4, LAT = 4 * STAGES;
    reg ck = 0, rst_n = 0;
    reg [N-1:0] f = 0;
    wire y;
    always #0.5 ck = ~ck;
    qkd_kv_cfault_tree #(.N(N), .R(R), .STAGES(STAGES), .MUT(MUT)) dut(.ck(ck), .rst_n(rst_n), .fault_in(f), .fault(y));
    integer errs = 0, i, k, seed = 17;
    task fail(input [8*64-1:0] what, input integer a, input integer b);
        begin errs = errs + 1; if (errs < 10) $display("ERR %0s leaf=%0d edge=%0d", what, a, b); end
    endtask
    task reset_cycle;
        begin
            @(negedge ck) rst_n = 0; f = 0;
            repeat (2) @(negedge ck); if (y !== 1'b0) fail("reset", -1, 0);
            rst_n = 1;
        end
    endtask
    task probe(input integer a, input integer b);
        begin
            repeat ($urandom(seed) % 7) @(negedge ck);
            f[a] = 1'b1; if (b >= 0) f[b] = 1'b1;          // the source flop changes just after an edge
            for (k = 1; k <= LAT + 5; k = k + 1) begin
                @(posedge ck); #0.1;
                if (k < LAT && y !== 1'b0) fail("early", a, k);
                if (k >= LAT && y !== 1'b1) fail("late/missing", a, k);
            end
            reset_cycle;
        end
    endtask
    initial begin
        repeat (3) @(negedge ck);
        if (y !== 1'b0) fail("in reset", -1, 0);
        rst_n = 1;
        for (k = 0; k < 3 * LAT; k = k + 1) begin @(posedge ck); #0.1; if (y !== 1'b0) fail("post-reset", -1, k); end
        for (i = 0; i < N; i = i + 1) probe(i, -1);
        for (i = 0; i < N / 2; i = i + 1) probe(i, N - 1 - i);
        for (k = 0; k < 2000; k = k + 1) begin @(posedge ck); #0.1; if (y !== 1'b0) fail("idle", -1, k); end
        if (errs == 0) $display("PASS kv_cfault_tree N=%0d R=%0d STAGES=%0d latency=%0d edges, 128 single + 64 pair faults exact",
                                N, R, STAGES, LAT);
        else $display("FAIL kv_cfault_tree errors=%0d (MUT=%0d)", errs, MUT);
        $finish;
    end
endmodule
