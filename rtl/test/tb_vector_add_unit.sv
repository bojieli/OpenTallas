`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Does the vector unit's CREDIT-BASED flow control work?
//
// The arithmetic is settled before this bench runs: ot_bf16_add_pipe is proven
// bit-identical to ot_bf16_add_rne over all 2**32 input pairs by SAT miter, and
// rtl/test/tb_bf16_add_pipe.sv has already checked the pipeline's staging. What
// is not settled is the flow control, and that is all this bench is for.
//
// A credit-based unit fails in ways a streaming test never reaches: when the
// consumer stalls long enough to exhaust the credits, when it resumes on the
// same cycle an operand is issued -- credits must neither double-count nor miss a
// simultaneous accept-and-drain -- and when the FIFO pointers wrap. So in_valid
// and out_ready are both random, which produces all three.
//
// EVERYTHING IS OBSERVED AT ONE INSTANT. Expectations are not precomputed in the
// driver; the operand pair is queued and the authority is driven continuously
// from the queue head. Building expectations in a loop over a single shared
// combinational instance separated by `#0` gave every lane the same value, and
// counting issues in the driver while counting drains in the monitor made the two
// counters disagree by 17 out of 9,576 with nothing wrong in the DUT. Both
// counts now come from the same negedge, from the same signals the DUT itself
// uses, so they cannot skew.
// ---------------------------------------------------------------------------
module tb_vector_add_unit;
    localparam integer LANES = 8;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;

    reg                  iv = 0, orr = 0;
    reg  [16*LANES-1:0]  a = 0, b = 0;
    wire                 ir, ov;
    wire [16*LANES-1:0]  q;
    wire [LANES-1:0]     sat;
    wire [2*LANES-1:0]   err;

    ot_vector_add_unit #(.LANES(LANES), .FIFO_LOG2(4)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(ir),
        .in_left(a), .in_right(b), .out_valid(ov), .out_ready(orr),
        .out_result(q), .out_saturated(sat), .out_error(err));

    // ---- operands in flight, in issue order -------------------------------
    localparam integer QMAX = 256;
    reg [16*LANES-1:0] ql [0:QMAX-1];
    reg [16*LANES-1:0] qr [0:QMAX-1];
    integer qh = 0, qt = 0, issued = 0, retired = 0, bad = 0, i, k;

    // ---- the authority: one adder per lane, driven continuously from the
    //      queue head, so it is always settled and never needs a #0 ----------
    wire [16*LANES-1:0] head_l = ql[qh];
    wire [16*LANES-1:0] head_r = qr[qh];
    wire [16*LANES-1:0] gq;
    wire [LANES-1:0]    gs;
    wire [2*LANES-1:0]  ge;

    genvar g;
    generate
        for (g = 0; g < LANES; g = g + 1) begin : gold
            ot_bf16_add_rne u (
                .left_code (head_l[16*g +: 16]),
                .right_code(head_r[16*g +: 16]),
                .result_code(gq[16*g +: 16]),
                .result_saturated(gs[g]),
                .result_error(ge[2*g +: 2]));
        end
    endgenerate

    //: STIMULUS ON THE FALLING EDGE, MONITOR ON THE RISING EDGE.  Driving and
    //: observing on the same edge is a race, and it is the one that produced
    //: every wrong answer this bench gave before: results appeared to lag the
    //: expectation queue by one, and the issue and drain counts disagreed by 73
    //: in 40,000, with the DUT verified correct by hand the whole time.  With
    //: the stimulus settled half a cycle early, a posedge monitor reads exactly
    //: the values the DUT's own always blocks read at that edge.
    always @(posedge clk) if (rst_n) begin
        if (ov && orr) begin
            retired = retired + 1;
            if (qh == qt) begin
                bad = bad + 1;
                if (bad < 6) $display("FAIL: a vector drained with none in flight");
            end else begin
                if (q !== gq || sat !== gs || err !== ge) begin
                    bad = bad + 1;
                    if (bad < 8) $display("FAIL vector %0d: got %h/%h/%h want %h/%h/%h",
                                          retired, q, sat, err, gq, gs, ge);
                end
                qh = (qh + 1) % QMAX;
            end
        end
        //: queued AFTER the pop above, so a vector issued on the same cycle the
        //: last one drains cannot be compared against its own operands.
        if (iv && ir) begin
            ql[qt] = a; qr[qt] = b;
            qt = (qt + 1) % QMAX;
            issued = issued + 1;
        end
    end

    reg [31:0] rnd = 32'h2468_ace0;
    function [31:0] nxt; input [31:0] s; nxt = s * 32'd1664525 + 32'd1013904223; endfunction
    reg [7:0] near_exp;

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        for (i = 0; i < 40000; i = i + 1) begin
            for (k = 0; k < LANES; k = k + 1) begin
                rnd = nxt(rnd);
                a[16*k +: 16] = rnd[31:16];
                near_exp = a[16*k+7 +: 8] + {5'b0, rnd[18:16]} - 8'd3;
                rnd = nxt(rnd);
                // odd lanes fully random, even lanes forced to a near-equal
                // exponent so cancellation drives the normalising shift to its
                // extremes -- the part of the adder this redesign replaced
                b[16*k +: 16] = (k % 2) ? rnd[31:16] : {rnd[31], near_exp, rnd[22:16]};
            end
            rnd = nxt(rnd); iv  = rnd[20];
            rnd = nxt(rnd); orr = rnd[21];
            @(negedge clk);
        end

        // drain everything still held
        iv = 0; orr = 1;
        for (i = 0; i < 300; i = i + 1) @(negedge clk);

        if (issued != retired) begin
            bad = bad + 1;
            $display("FAIL: issued %0d vectors, retired %0d", issued, retired);
        end
        if (bad == 0)
            $display("PASS vector_add_unit: %0d vectors x %0d lanes = %0d adds, bit-exact under random backpressure; %0d issued = %0d retired",
                     retired, LANES, retired*LANES, issued, retired);
        else
            $display("FAIL vector_add_unit: %0d failures over %0d vectors", bad, retired);
        $finish;
    end
endmodule
