`timescale 1ns/1ps
// Qualification campaign for ot_mac_bf16_fp32_pipe against the scalar reference.
//
// The pipe carries "NOT numerically qualified ... must not be wired into any
// consumer until it does". This is that campaign. The authority is
// ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne, which computes the same
// operation through a 524-bit exact intermediate and rounds once -- the contract
// ot_a3_mac_lane implements.
//
// The comparison is legal because a BF16 x BF16 product is EXACT in binary32: two
// 8-bit significands make at most 16 significant bits and binary32 carries 24. So
// round(a*b) == a*b, and the separate round-multiply-then-round-add the legacy lane
// performs is identical to the fused product-add the reference computes. The pipe
// may therefore be compared against either.
//
// This bench REPORTS rather than merely passing or failing, because the first
// question is how big the gap is and where it lives: alignment sticky bits,
// subnormal results, and out-of-range exponents are three different defects with
// three different fixes, and a single pass/fail count cannot tell them apart.
module tb_mac_fp32_pipe_qualify;
    reg clk = 0, rst_n = 0, iv = 0;
    reg [15:0] a = 0, b = 0;
    reg [31:0] c = 0;
    always #0.5 clk = ~clk;

    wire        ov;
    wire [31:0] y;
    wire [1:0]  ey;
    ot_mac_bf16_fp32_pipe dut (.clk(clk), .rst_n(rst_n), .valid_in(iv),
                               .a(a), .b(b), .c(c), .y(y), .err(ey), .valid_out(ov));

    // operands in flight, popped on valid_out
    localparam integer QMAX = 64;
    reg [15:0] qa [0:QMAX-1];
    reg [15:0] qb [0:QMAX-1];
    reg [31:0] qc [0:QMAX-1];
    integer qh = 0, qt = 0, issued = 0, retired = 0;

    integer checked = 0, bad = 0, i;
    // failure taxonomy
    integer n_ref_err = 0, n_sub = 0, n_zero = 0, n_align = 0, n_other = 0;

    reg [33:0] ref_packed;
    reg [31:0] ref_val;
    reg [1:0]  ref_err;
    reg [7:0]  ref_exp;

    always @(posedge clk) if (rst_n) begin
        if (ov) begin
            retired = retired + 1;
            if (qh != qt) begin
                ref_packed = ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(
                                 qc[qh], qa[qh], qb[qh]);
                ref_err = ref_packed[33:32];
                ref_val = ref_packed[31:0];
                ref_exp = ref_val[30:23];
                checked = checked + 1;
                if ((ey !== ref_err) || ((ref_err == 2'd0) && (y !== ref_val))) begin
                    bad = bad + 1;
                    //: classify, because these need different fixes
                    if (ref_err != 2'd0)              n_ref_err = n_ref_err + 1;
                    else if (ref_exp == 8'd0 && ref_val[22:0] != 23'b0)
                                                       n_sub = n_sub + 1;
                    else if (y == 32'b0)               n_zero = n_zero + 1;
                    else if ((y[31:23] == ref_val[31:23]) &&
                             ((y[22:0] ^ ref_val[22:0]) <= 23'd2))
                                                       n_align = n_align + 1;
                    else                               n_other = n_other + 1;
                    if (bad < 8)
                        $display("  DIFF a=%h b=%h c=%h : pipe %h  ref %h (err %0d)",
                                 qa[qh], qb[qh], qc[qh], y, ref_val, ref_err);
                end
                qh = (qh + 1) % QMAX;
            end
        end
        if (iv) begin
            qa[qt] = a; qb[qt] = b; qc[qt] = c;
            qt = (qt + 1) % QMAX; issued = issued + 1;
        end
    end

    task step(input [15:0] la, input [15:0] lb, input [31:0] lc, input v);
        begin a = la; b = lb; c = lc; iv = v; @(negedge clk); end
    endtask

    reg [31:0] rnd = 32'h0bad_f00d;
    function [31:0] nxt; input [31:0] s; nxt = s*32'd1664525 + 32'd1013904223; endfunction
    reg [7:0] ea, eb, ec;
    localparam integer NDB = 12, NDC = 10;
    reg [15:0] db [0:NDB-1];
    reg [31:0] dc [0:NDC-1];

    initial begin
        db[0]=16'h0000; db[1]=16'h8000; db[2]=16'h0001; db[3]=16'h8001;
        db[4]=16'h007f; db[5]=16'h3f80; db[6]=16'hbf80; db[7]=16'h7f7f;
        db[8]=16'hff7f; db[9]=16'h7f80; db[10]=16'h0080; db[11]=16'h00ff;
        dc[0]=32'h00000000; dc[1]=32'h80000000; dc[2]=32'h00000001;
        dc[3]=32'h007fffff; dc[4]=32'h3f800000; dc[5]=32'hbf800000;
        dc[6]=32'h7f7fffff; dc[7]=32'h7f800000; dc[8]=32'h00800000;
        dc[9]=32'h80000001;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        // 1. exponents near each other: the common case, no large alignment
        for (i = 0; i < 300000; i = i + 1) begin
            rnd = nxt(rnd); ea = rnd[30:23];
            if (ea == 8'd0 || ea == 8'hff) ea = 8'd127;
            rnd = nxt(rnd); eb = ea + rnd[18:16] - 8'd3;
            rnd = nxt(rnd); ec = ea + eb - 8'd127 + rnd[18:16] - 8'd3;
            rnd = nxt(rnd);
            step({rnd[31], ea, rnd[6:0]},
                 {rnd[30], eb, rnd[14:8]},
                 {rnd[29], ec, rnd[22:0]}, 1'b1);
        end
        // 2. widely separated exponents: exercises the alignment shift and sticky
        for (i = 0; i < 300000; i = i + 1) begin
            rnd = nxt(rnd); ea = 8'd100 + rnd[20:16] ;
            rnd = nxt(rnd); eb = 8'd100 + rnd[20:16];
            rnd = nxt(rnd); ec = 8'd170 + rnd[19:16];
            rnd = nxt(rnd);
            step({rnd[31], ea, rnd[6:0]},
                 {rnd[30], eb, rnd[14:8]},
                 {rnd[29], ec, rnd[22:0]}, 1'b1);
        end
        // 3. fully random, including zeros, nonfinites and the whole range
        for (i = 0; i < 300000; i = i + 1) begin
            rnd = nxt(rnd); a = rnd[31:16]; b = rnd[15:0];
            rnd = nxt(rnd); step(a, b, rnd, 1'b1);
        end
        //: directed boundary sweep: zeros, both signed zeros, the smallest and
        //: largest subnormals, one, the largest finite, and the nonfinite row,
        //: crossed against subnormal / normal / huge accumulators
        for (i = 0; i < NDB*NDB*NDC; i = i + 1)
            step(db[(i/NDC) % NDB], db[(i/(NDC*NDB)) % NDB], dc[i % NDC], 1'b1);
        for (i = 0; i < 16; i = i + 1) step(0, 0, 0, 1'b0);

        $display("");
        $display("  issued %0d  retired %0d  checked %0d  disagreeing %0d (%0.4f%%)",
                 issued, retired, checked, bad, 100.0*bad/checked);
        $display("  taxonomy: reference-error %0d, subnormal result %0d, pipe-flushed-to-zero %0d,",
                 n_ref_err, n_sub, n_zero);
        $display("            near-miss (<=2 ulp, alignment/sticky) %0d, other %0d",
                 n_align, n_other);
        if (bad == 0)
            $display("PASS mac_fp32_pipe: bit-identical to bf16_bf16_fp32_product_add_rne over %0d cases", checked);
        else
            $display("FAIL mac_fp32_pipe: %0d of %0d disagree -- NOT qualified", bad, checked);
        $finish;
    end
endmodule
