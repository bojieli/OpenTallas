`timescale 1ns/1ps
// Qualify ot_fp32_add_rne_pipe against ot_fp32_rne_pkg::fp32_add_rne.
//
// The combinational function is the project's scalar authority; this bench
// asserts the pipeline is BIT-IDENTICAL to it -- result code and error code --
// on every case, and that it sustains one result per cycle while doing so.
//
// The corpus is directed boundaries crossed against each other plus a long
// pseudo-random tail. The boundaries are where an adder actually breaks:
// signed zeros (whose sum the authority canonicalizes to +0, not IEEE's -0),
// the subnormal edge in both operands, exact cancellation, a one-ulp difference
// at every exponent, ties-to-even at the round bit, and the overflow boundary
// that must FAIL CLOSED rather than encode an infinity.
module tb_fp32_add_rne_pipe_qualify;
    reg clk = 0, rst_n = 0;
    reg valid_in = 0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] y; wire [1:0] err; wire valid_out;

    ot_fp32_add_rne_pipe dut (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .a(a), .b(b), .y(y), .err(err), .valid_out(valid_out)
    );

    localparam integer LATENCY = 5;
    localparam integer QUEUE = 64;
    //: The expected answer travels alongside, so a latency change shows up as a
    //: mismatch rather than silently comparing the wrong pair.
    reg [31:0] q_a [0:QUEUE-1];
    reg [31:0] q_b [0:QUEUE-1];
    reg [33:0] q_e [0:QUEUE-1];
    reg [QUEUE-1:0] q_v;
    integer wptr = 0, rptr = 0;
    integer checked = 0, errors = 0, issued = 0;
    integer i, j, n_directed;
    reg [31:0] seed;
    reg [31:0] next_a;

    //: 41 directed codes: zeros, the smallest and largest subnormals, the
    //: subnormal/normal boundary, one and its neighbours, powers that force a
    //: 24-bit alignment, the largest finite, and near-overflow.
    reg [31:0] directed [0:40];
    initial begin
        directed[0]  = 32'h0000_0000; directed[1]  = 32'h8000_0000;
        directed[2]  = 32'h0000_0001; directed[3]  = 32'h8000_0001;
        directed[4]  = 32'h007f_ffff; directed[5]  = 32'h807f_ffff;
        directed[6]  = 32'h0080_0000; directed[7]  = 32'h8080_0000;
        directed[8]  = 32'h0080_0001; directed[9]  = 32'h3f80_0000;
        directed[10] = 32'hbf80_0000; directed[11] = 32'h3f80_0001;
        directed[12] = 32'hbf80_0001; directed[13] = 32'h3f7f_ffff;
        directed[14] = 32'h4000_0000; directed[15] = 32'hc000_0000;
        directed[16] = 32'h4b80_0000; directed[17] = 32'hcb80_0000;
        directed[18] = 32'h4c00_0000; directed[19] = 32'h3400_0000;
        directed[20] = 32'hb400_0000; directed[21] = 32'h7f7f_ffff;
        directed[22] = 32'hff7f_ffff; directed[23] = 32'h7f7f_fffe;
        directed[24] = 32'h7f00_0000; directed[25] = 32'hff00_0000;
        directed[26] = 32'h0000_0002; directed[27] = 32'h0040_0000;
        directed[28] = 32'h8040_0000; directed[29] = 32'h3f00_0000;
        directed[30] = 32'hbf00_0000; directed[31] = 32'h3e80_0000;
        directed[32] = 32'h4180_0000; directed[33] = 32'hc180_0000;
        directed[34] = 32'h3fff_ffff; directed[35] = 32'h4b7f_ffff;
        directed[36] = 32'h3380_0000; directed[37] = 32'hb380_0000;
        directed[38] = 32'h0000_0003; directed[39] = 32'h7f7f_fffd;
        directed[40] = 32'h4b00_0001;
        n_directed = 41;
    end

    always #1 clk = ~clk;

    //: A fresh pseudo-random 32-bit code, biased toward the exponents where two
    //: operands actually interact rather than one swamping the other.
    function automatic [31:0] pick;
        input integer which;
        reg [31:0] v;
        reg [7:0] e;
        begin
            seed = seed * 32'd1664525 + 32'd1013904223;
            v = seed;
            seed = seed * 32'd1664525 + 32'd1013904223;
            //: Exponents 100..154 keep both operands in a range where alignment
            //: distances of 0..30 are common, which is where rounding decides.
            e = 8'd100 + (seed[15:8] % 8'd55);
            if (seed[3:0] == 4'd0) e = 8'd0;          //: subnormal sometimes
            else if (seed[3:0] == 4'd1) e = 8'd254;   //: near overflow sometimes
            pick = {v[31], e, v[22:0]};
            if (which != 0) pick = {~v[31], e, v[22:0]};
        end
    endfunction

    task push;
        input [31:0] ca;
        input [31:0] cb;
        begin
            @(negedge clk);
            a = ca; b = cb; valid_in = 1'b1;
            q_a[wptr % QUEUE] = ca;
            q_b[wptr % QUEUE] = cb;
            q_e[wptr % QUEUE] = ot_fp32_rne_pkg::fp32_add_rne(ca, cb);
            wptr = wptr + 1;
            issued = issued + 1;
        end
    endtask

    //: Checked in the clock process so back-to-back results are all seen; a
    //: gap here would let the II=1 claim pass on a design that stalls.
    always @(posedge clk) begin
        if (rst_n && valid_out) begin
            checked = checked + 1;
            if ({err, y} !== q_e[rptr % QUEUE]) begin
                if (errors < 12)
                    $display("FAIL a=%08h b=%08h got err=%0d y=%08h expected err=%0d y=%08h",
                             q_a[rptr % QUEUE], q_b[rptr % QUEUE], err, y,
                             q_e[rptr % QUEUE][33:32], q_e[rptr % QUEUE][31:0]);
                errors = errors + 1;
            end
            rptr = rptr + 1;
        end
    end

    initial begin
        seed = 32'h1234_5678;
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        //: Every directed pair, both orders -- 41*41 = 1,681 cases.
        for (i = 0; i < n_directed; i = i + 1)
            for (j = 0; j < n_directed; j = j + 1)
                push(directed[i], directed[j]);

        //: Directed against random, so a boundary meets an arbitrary partner.
        for (i = 0; i < n_directed; i = i + 1)
            for (j = 0; j < 200; j = j + 1) begin
                push(directed[i], pick(0));
                push(pick(0), directed[i]);
            end

        //: A random tail, and a self-cancelling pair every 16th case so exact
        //: cancellation keeps arriving at every exponent.
        //: THROUGH A LOCAL, never through the DUT's own input register. Writing
        //: ``a`` here lands between the previous push's negedge and the posedge
        //: that samples it, so the DUT sees this case's a against the PREVIOUS
        //: case's b while the queue expects the matched pair -- which reads as a
        //: catastrophic arithmetic failure and is a bench defect.
        for (i = 0; i < 880000; i = i + 1) begin
            next_a = pick(0);
            if (i[3:0] == 4'd0) push(next_a, {~next_a[31], next_a[30:0]});
            else push(next_a, pick(0));
        end

        @(negedge clk); valid_in = 1'b0;
        for (i = 0; i < LATENCY + 4; i = i + 1) @(negedge clk);

        if (checked !== issued) begin
            $display("FAIL issued %0d but only %0d results emerged -- the pipe does not sustain II=1",
                     issued, checked);
            errors = errors + 1;
        end
        if (errors == 0)
            $display("PASS fp32_add_rne_pipe: bit-identical to fp32_add_rne over %0d cases at one result per cycle", checked);
        else
            $display("FAIL fp32_add_rne_pipe: %0d of %0d cases differ", errors, checked);
        $finish;
    end
endmodule
