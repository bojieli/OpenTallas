`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Does the five-stage pipeline compute what the combinational adder computes?
//
// The ARITHMETIC is already settled: ot_bf16_add_flat is proven bit-identical to
// ot_bf16_add_rne over all 2**32 input pairs by SAT miter
// (tools/prove_bf16_add_equivalence.sh), and ot_bf16_add_pipe implements that
// same function. Registers do not change a function. What a proof of the
// combinational function cannot check is the STAGING: whether every value a
// later stage reads was carried forward, or whether one of them is read a cycle
// stale. That is the only bug class left here, and it is what this bench targets.
//
// HOW IT CHECKS, and why it is built this way.
//
// The contract is not "the answer appears N cycles later", it is "one answer per
// accepted operand, in order". So operands are queued on in_valid and popped on
// out_valid, and the bench never encodes a latency. A fixed-depth shadow instead
// reported all 67 idle cycles of the gap pattern as failures while the
// arithmetic was fine.
//
// The monitor samples on the FALLING edge. Reading the DUT's outputs off
// @(posedge clk) returns pre-edge values for some signals and post-edge for
// others, so out_valid came back updated while result_code came back stale --
// which reads exactly like a one-cycle pipeline bug and is not one. At the
// negedge every non-blocking update from the rising edge has settled.
//
// The reference is driven CONTINUOUSLY from the queue head rather than assigned
// inside the monitor followed by `#0`. A `#0` does not reliably settle a
// combinational module instance, and when it does not the comparison silently
// uses the previous pop's reference.
//
// Each of those three was a real wrong answer out of this bench before it was a
// comment. None of them was a bug in the pipeline.
// ---------------------------------------------------------------------------
module tb_bf16_add_pipe;
    reg clk = 0, rst_n = 0, iv = 0;
    reg [15:0] l = 0, r = 0;
    always #0.5 clk = ~clk;

    wire        ov;
    wire [15:0] q_pipe;  wire sat_pipe;  wire [1:0] err_pipe;
    ot_bf16_add_pipe dut (.clk(clk), .rst_n(rst_n), .in_valid(iv),
        .left_code(l), .right_code(r), .out_valid(ov),
        .result_code(q_pipe), .result_saturated(sat_pipe), .result_error(err_pipe));

    // ---- operands in flight, queued on in_valid, popped on out_valid -------
    localparam integer QMAX = 64;
    reg [15:0] ql [0:QMAX-1];
    reg [15:0] qr [0:QMAX-1];
    integer qhead = 0, qtail = 0, issued = 0, retired = 0;
    integer checked = 0, bad = 0, i;

    // the qualified combinational adder as the authority, always settled
    wire [15:0] ref_l = ql[qhead];
    wire [15:0] ref_r = qr[qhead];
    wire [15:0] q_ref; wire sat_ref; wire [1:0] err_ref;
    ot_bf16_add_rne gold (.left_code(ref_l), .right_code(ref_r),
        .result_code(q_ref), .result_saturated(sat_ref), .result_error(err_ref));

    always @(negedge clk) if (rst_n) begin
        if (ov) begin
            retired = retired + 1;
            if (qhead == qtail) begin
                bad = bad + 1;
                if (bad < 6) $display("FAIL: a result with no operand in flight");
            end else begin
                checked = checked + 1;
                if (q_pipe !== q_ref || sat_pipe !== sat_ref || err_pipe !== err_ref) begin
                    bad = bad + 1;
                    if (bad < 12)
                        $display("FAIL %h + %h : pipe %h/%b/%0d  ref %h/%b/%0d",
                                 ref_l, ref_r, q_pipe, sat_pipe, err_pipe,
                                 q_ref, sat_ref, err_ref);
                end
                qhead = (qhead + 1) % QMAX;
            end
        end
    end

    task step(input [15:0] la, input [15:0] rb, input v);
        begin
            l = la; r = rb; iv = v;
            if (v) begin
                ql[qtail] = la; qr[qtail] = rb;
                qtail = (qtail + 1) % QMAX;
                issued = issued + 1;
            end
            @(posedge clk);
        end
    endtask

    // boundary codes: zero, both signed zeros, subnormals, one, largest finite,
    // the 0xff nonfinite row, and the saturation neighbourhood
    localparam integer NDIR = 14;
    reg [15:0] dir [0:NDIR-1];

    reg [15:0] a_code, b_code;
    reg [31:0] rnd;

    initial begin
        dir[0]=16'h0000; dir[1]=16'h8000; dir[2]=16'h0001; dir[3]=16'h007f;
        dir[4]=16'h3f80; dir[5]=16'hbf80; dir[6]=16'h7f7f; dir[7]=16'hff7f;
        dir[8]=16'h7f80; dir[9]=16'hff80; dir[10]=16'h7fc0; dir[11]=16'h0080;
        dir[12]=16'h7f00; dir[13]=16'h0100;

        repeat (4) @(posedge clk);
        rst_n = 1;
        repeat (2) @(posedge clk);

        // every directed pair, back to back
        for (i = 0; i < NDIR*NDIR; i = i + 1)
            step(dir[i/NDIR], dir[i%NDIR], 1'b1);

        // gaps: one result per accepted operand, and none for an idle cycle
        for (i = 0; i < 300; i = i + 1)
            step(dir[i%NDIR], dir[(i*7)%NDIR], (i % 3) != 0);

        // random, changing every cycle. Half the pairs are forced to near-equal
        // exponents, where cancellation drives the normalising shift to its
        // extremes -- the part of the path this redesign replaced.
        rnd = 32'h1234_5678;
        for (i = 0; i < 400000; i = i + 1) begin
            rnd = rnd * 32'd1664525 + 32'd1013904223;
            a_code = rnd[31:16];
            rnd = rnd * 32'd1664525 + 32'd1013904223;
            b_code = (i % 2) ? rnd[31:16]
                             : {rnd[31], a_code[14:7] + rnd[18:16] - 3'd3, rnd[6:0]};
            step(a_code, b_code, 1'b1);
        end

        // drain, then require that every operand issued came back out exactly once
        for (i = 0; i < 16; i = i + 1) step(16'h0, 16'h0, 1'b0);
        if (issued != retired) begin
            bad = bad + 1;
            $display("FAIL: issued %0d operands, retired %0d results", issued, retired);
        end

        if (bad == 0)
            $display("PASS bf16_add_pipe: %0d results bit-identical to ot_bf16_add_rne, %0d issued = %0d retired",
                     checked, issued, retired);
        else
            $display("FAIL bf16_add_pipe: %0d bad of %0d checked", bad, checked);
        $finish;
    end
endmodule
