`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_a3_vector_scale_pipe must be the combinational engine's equal.
//
// The pipelined engine reschedules the arithmetic; it does not change it.  That
// is only worth anything if it is checked, so this drives BOTH engines from the
// same configuration over the same operand memory contents and requires them to
// agree on EVERY architectural output: the committed address/data sequence, the
// error code, the retired count and the saturation count.
//
// The two engines have different latencies by construction, so each gets its
// own memory model and its own collector and they are compared on their results
// rather than cycle by cycle.  The cycle counts ARE recorded, because the whole
// point of the rewrite is that the pipelined one takes fewer.
//
// Coverage is directed as well as random: nonfinite operands, products that
// overflow binary32, values that saturate the BF16 narrowing, the constant and
// elementwise forms, count 1, and counts that exercise the pipe's fill and
// drain against a short operand.
// ---------------------------------------------------------------------------
module tb_vector_scale_pipe_equivalence;
    localparam integer MAX_ELEMENTS = 512;
    localparam integer AW = 32;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #0.5 clk = ~clk;

    reg  [31:0] cfg_count, cfg_scale_bits, cfg_a_base, cfg_b_base, cfg_out_base;
    reg  [7:0]  cfg_dtype_a, cfg_dtype_b;
    reg  [15:0] cfg_aux0;
    reg         start_a, start_b;

    // --- two identical operand memories ------------------------------------
    reg [31:0] mem_a [0:2047];
    reg [31:0] mem_b [0:2047];

    wire        a_en_r, b_en_r, a_en_p, b_en_p;
    wire [31:0] a_ad_r, b_ad_r, a_ad_p, b_ad_p;
    reg  [31:0] a_dt_r, b_dt_r, a_dt_p, b_dt_p;

    always @(posedge clk) begin
        if (a_en_r) a_dt_r <= mem_a[a_ad_r[10:0]];
        if (b_en_r) b_dt_r <= mem_b[b_ad_r[10:0]];
        if (a_en_p) a_dt_p <= mem_a[a_ad_p[10:0]];
        if (b_en_p) b_dt_p <= mem_b[b_ad_p[10:0]];
    end

    wire        we_r, we_p, busy_r, busy_p, done_r, done_p;
    wire [31:0] oa_r, od_r, oa_p, od_p;
    wire [7:0]  ec_r, ec_p;
    wire [31:0] oc_r, oc_p, sc_r, sc_p;

    ot_a3_vector_scale #(.MAX_ELEMENTS(MAX_ELEMENTS)) reference (
        .clk(clk), .rst_n(rst_n), .start(start_a),
        .cfg_count(cfg_count), .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_aux0(cfg_aux0), .cfg_scale_bits(cfg_scale_bits),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base), .cfg_out_base(cfg_out_base),
        .a_rd_en(a_en_r), .a_rd_addr(a_ad_r), .a_rd_data(a_dt_r),
        .b_rd_en(b_en_r), .b_rd_addr(b_ad_r), .b_rd_data(b_dt_r),
        .out_we(we_r), .out_addr(oa_r), .out_data(od_r),
        .busy(busy_r), .done(done_r), .error_code(ec_r),
        .out_count(oc_r), .saturation_count(sc_r));

    ot_a3_vector_scale_pipe #(.MAX_ELEMENTS(MAX_ELEMENTS)) pipelined (
        .clk(clk), .rst_n(rst_n), .start(start_b),
        .cfg_count(cfg_count), .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_aux0(cfg_aux0), .cfg_scale_bits(cfg_scale_bits),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base), .cfg_out_base(cfg_out_base),
        .a_rd_en(a_en_p), .a_rd_addr(a_ad_p), .a_rd_data(a_dt_p),
        .b_rd_en(b_en_p), .b_rd_addr(b_ad_p), .b_rd_data(b_dt_p),
        .out_we(we_p), .out_addr(oa_p), .out_data(od_p),
        .busy(busy_p), .done(done_p), .error_code(ec_p),
        .out_count(oc_p), .saturation_count(sc_p));

    // --- collectors ---------------------------------------------------------
    reg [31:0] seen_a_addr [0:MAX_ELEMENTS-1];
    reg [31:0] seen_a_data [0:MAX_ELEMENTS-1];
    reg [31:0] seen_p_addr [0:MAX_ELEMENTS-1];
    reg [31:0] seen_p_data [0:MAX_ELEMENTS-1];
    integer n_a, n_p, cyc_a, cyc_p;
    reg run_a, run_p;

    // ``done`` is a one-cycle pulse and the pipelined engine can finish FIRST,
    // so waiting for one and then the other misses the earlier pulse and hangs.
    // Both are latched and cleared at the start of each case instead.
    reg saw_done_a, saw_done_p;

    always @(posedge clk) begin
        if (run_a) cyc_a <= cyc_a + 1;
        if (run_p) cyc_p <= cyc_p + 1;
        if (done_r) saw_done_a <= 1'b1;
        if (done_p) saw_done_p <= 1'b1;
        if (we_r) begin seen_a_addr[n_a] <= oa_r; seen_a_data[n_a] <= od_r; n_a <= n_a + 1; end
        if (we_p) begin seen_p_addr[n_p] <= oa_p; seen_p_data[n_p] <= od_p; n_p <= n_p + 1; end
    end

    integer errors, cases, i, guard;
    integer total_cyc_a, total_cyc_p;

    task automatic run_case(input [31:0] count, input [15:0] aux0,
                            input [31:0] scale, input [7:0] dt_b);
        begin
            cases = cases + 1;
            cfg_count = count; cfg_aux0 = aux0; cfg_scale_bits = scale;
            cfg_dtype_a = 8'h10; cfg_dtype_b = dt_b;
            cfg_a_base = 0; cfg_b_base = 0; cfg_out_base = 32'd1024;
            n_a = 0; n_p = 0; cyc_a = 0; cyc_p = 0;
            saw_done_a = 1'b0; saw_done_p = 1'b0;
            @(negedge clk); start_a = 1'b1; start_b = 1'b1; run_a = 1'b1; run_p = 1'b1;
            @(negedge clk); start_a = 1'b0; start_b = 1'b0;
            guard = 0;
            while ((!saw_done_a || !saw_done_p) && guard < 100000) begin
                if (saw_done_a) run_a = 1'b0;
                if (saw_done_p) run_p = 1'b0;
                @(negedge clk);
                guard = guard + 1;
            end
            run_a = 1'b0; run_p = 1'b0;
            if (guard >= 100000) begin
                $display("TIMEOUT count=%0d aux0=%0d: reference done=%0d pipelined done=%0d",
                         count, aux0, saw_done_a, saw_done_p);
                errors = errors + 1;
            end
            total_cyc_a = total_cyc_a + cyc_a;
            total_cyc_p = total_cyc_p + cyc_p;
            if (ec_r !== ec_p) begin
                $display("MISMATCH error_code count=%0d aux0=%0d: reference %0d pipelined %0d",
                         count, aux0, ec_r, ec_p); errors = errors + 1;
            end
            if (oc_r !== oc_p) begin
                $display("MISMATCH out_count count=%0d: reference %0d pipelined %0d",
                         count, oc_r, oc_p); errors = errors + 1;
            end
            if (sc_r !== sc_p) begin
                $display("MISMATCH saturation_count count=%0d: reference %0d pipelined %0d",
                         count, sc_r, sc_p); errors = errors + 1;
            end
            if (n_a !== n_p) begin
                $display("MISMATCH committed words count=%0d: reference %0d pipelined %0d",
                         count, n_a, n_p); errors = errors + 1;
            end else begin
                for (i = 0; i < n_a; i = i + 1) begin
                    if (seen_a_addr[i] !== seen_p_addr[i] ||
                        seen_a_data[i] !== seen_p_data[i]) begin
                        $display("MISMATCH word %0d count=%0d: reference %h@%h pipelined %h@%h",
                                 i, count, seen_a_data[i], seen_a_addr[i],
                                 seen_p_data[i], seen_p_addr[i]);
                        errors = errors + 1;
                    end
                end
            end
            @(negedge clk);
        end
    endtask

    integer seed, j;
    initial begin
        errors = 0; cases = 0; total_cyc_a = 0; total_cyc_p = 0;
        n_a = 0; n_p = 0; cyc_a = 0; cyc_p = 0; run_a = 0; run_p = 0;
        start_a = 0; start_b = 0; seed = 32'h5EED_1234;
        for (j = 0; j < 2048; j = j + 1) begin mem_a[j] = 0; mem_b[j] = 0; end
        rst_n = 1'b0; repeat (6) @(negedge clk); rst_n = 1'b1;
        repeat (3) @(negedge clk);

        // ---- random BF16 operands, constant scale --------------------------
        for (j = 0; j < 512; j = j + 1) begin
            mem_a[j] = {16'b0, $random(seed) & 16'h7F7F};
            mem_b[j] = {16'b0, $random(seed) & 16'h7F7F};
        end
        run_case(32'd1,   16'd0, 32'h3F800000, 8'h10);
        run_case(32'd2,   16'd0, 32'h3F800000, 8'h10);
        run_case(32'd7,   16'd0, 32'h40490FDB, 8'h10);
        run_case(32'd8,   16'd0, 32'h3E4CCCCD, 8'h10);
        run_case(32'd64,  16'd0, 32'h3F000000, 8'h10);
        run_case(32'd512, 16'd0, 32'h3FC00000, 8'h10);
        // ---- elementwise ---------------------------------------------------
        run_case(32'd1,   16'd1, 32'h0, 8'h10);
        run_case(32'd9,   16'd1, 32'h0, 8'h10);
        run_case(32'd512, 16'd1, 32'h0, 8'h10);
        // ---- a nonfinite operand, at the front and deep in the operand -----
        mem_a[0] = {16'b0, 16'h7F80};
        run_case(32'd64, 16'd0, 32'h3F800000, 8'h10);
        mem_a[0] = {16'b0, 16'h3F80};
        mem_a[40] = {16'b0, 16'h7FC0};
        run_case(32'd64, 16'd0, 32'h3F800000, 8'h10);
        mem_a[40] = {16'b0, 16'h3F80};
        // ---- a product that overflows --------------------------------------
        for (j = 0; j < 64; j = j + 1) mem_a[j] = {16'b0, 16'h7F00};
        run_case(32'd64, 16'd0, 32'h7F000000, 8'h10);
        // ---- refusals that never reach the datapath ------------------------
        run_case(32'd0,   16'd0, 32'h3F800000, 8'h10);
        run_case(32'd513, 16'd0, 32'h3F800000, 8'h10);
        run_case(32'd8,   16'd0, 32'h7F800000, 8'h10);
        run_case(32'd8,   16'd2, 32'h3F800000, 8'h10);
        // ---- a REFUSAL immediately followed by a good operation ------------
        // This is the case the engine campaign caught and this bench did not.
        // A refusal abandons the operand with elements still in the multiplier,
        // and if the engine returns to S_IDLE and is restarted before they
        // emerge, they retire as the NEXT operation's results: the campaign saw
        // six words committed and the wrong fault code on two refusal cases.
        // Back-to-back with no idle gap is what exposes it.
        for (j = 0; j < 512; j = j + 1) begin
            mem_a[j] = {16'b0, 16'h3F80};
            mem_b[j] = {16'b0, 16'h3F80};
        end
        mem_a[3] = {16'b0, 16'h7F80};          // nonfinite deep in the operand
        run_case(32'd64, 16'd0, 32'h3F800000, 8'h10);   // refuses at element 3
        mem_a[3] = {16'b0, 16'h3F80};
        run_case(32'd6,  16'd0, 32'h3F800000, 8'h10);   // must be clean
        run_case(32'd6,  16'd0, 32'h3F800000, 8'h10);
        mem_a[1] = {16'b0, 16'hFF80};
        run_case(32'd8,  16'd1, 32'h0, 8'h10);          // refuses at element 1
        mem_a[1] = {16'b0, 16'h3F80};
        run_case(32'd8,  16'd1, 32'h0, 8'h10);          // must be clean
        run_case(32'd64, 16'd0, 32'h3F800000, 8'h10);

        // ---- back to ordinary values, several random sweeps ----------------
        for (j = 0; j < 512; j = j + 1) begin
            mem_a[j] = {16'b0, $random(seed) & 16'h3FFF};
            mem_b[j] = {16'b0, $random(seed) & 16'h3FFF};
        end
        run_case(32'd128, 16'd0, 32'h3F800000, 8'h10);
        run_case(32'd128, 16'd1, 32'h0, 8'h10);
        run_case(32'd511, 16'd1, 32'h0, 8'h10);

        $display("CASES: %0d", cases);
        $display("CYCLES: reference %0d, pipelined %0d", total_cyc_a, total_cyc_p);
        if (total_cyc_a > 0)
            $display("SPEEDUP_CYCLES: %0d.%02d",
                     total_cyc_a / total_cyc_p,
                     ((total_cyc_a * 100) / total_cyc_p) % 100);
        if (errors == 0) $display("VECTOR_SCALE_PIPE_EQUIVALENCE: PASS");
        else $display("VECTOR_SCALE_PIPE_EQUIVALENCE: FAIL (%0d mismatches)", errors);
        $finish;
    end
endmodule
