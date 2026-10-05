`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G1f, supporting measurement: WHAT KIND of predicate refuses the reduced
// geometry?
//
// ``rtl/test/tb_a3_g1f_reduced_geometry.sv`` established that
// ``ot_a3_vector_rms_norm`` refuses a 16-wide row and that ``ot_a3_qwen_gqa``
// refuses a context of 4.  Those two refusals are consistent with two
// completely different designs, and the decision G1f's record has to make --
// build the geometry port, or choose a reduced configuration that fits the
// geometry the engines have -- turns on which one is true:
//
//   * a CAPACITY BOUND ("this block holds at most N columns") is a legitimate
//     physical limit.  A reduced configuration must then be chosen inside it,
//     and no RTL owes anything.
//   * an EXACT-SET MEMBERSHIP TEST ("this block serves 4,096 or 128 and
//     nothing else") is a refusal on a ground section 4.9's fail-closed column
//     does not name for this contract, and a configuration chosen to fit it is
//     a configuration chosen to fit a defect.
//
// The two are told apart by SWEEPING, not by reading a constant: a capacity
// bound admits everything below its threshold, an exact-set test admits an
// isolated set and refuses immediately above and below every member.  So this
// bench walks 38 row widths from 1 to 8,192 and 21 context lengths from 1 to
// 128 through the two blocks and prints what each did.  The classification is
// left to the tool that reads this output, so the verdict is computed from the
// sweep rather than asserted here.
//
// The GQA half asks a second question the same way.  ``cfg_context_length`` is
// the ONE geometry field that arrives as a runtime port; the query-head count,
// the KV-head count and the head width do not.  If the block bounds-checks the
// field it can read and generates traffic that scales with it, while its result
// row stays the same width at every admitted context, then the block's own
// behaviour measures both the geometry it is built for and the fact that no
// other geometry can be asked for -- and a field that cannot be read is a field
// that cannot be refused, which is the fail-closed argument rather than a
// convenience argument.
//
// Operands are the constant BF16 code 1.0.  This bench asks which geometries an
// engine ADMITS and what traffic it generates, never what value it computes;
// numeric equivalence is rung G1a's and is established there on real
// checkpoint bytes.
// ---------------------------------------------------------------------------
module tb_a3_g1f_geometry_predicate;
    localparam [31:0] BF16_ONE = 32'h0000_3f80;
    // Qwen3's rms_norm_eps, 1e-6, as the binary32 code the engine requires.
    localparam [31:0] EPSILON  = 32'h3586_37bd;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    integer cycles = 0;
    integer case_start = 0;
    always @(posedge clk) if (rst_n) cycles = cycles + 1;

    // -- RMSNorm ------------------------------------------------------------
    reg         rms_start = 1'b0;
    reg  [31:0] rms_count = 0, rms_rows = 0, rms_cols = 0;
    wire        rms_in_en, rms_w_en, rms_out_we;
    wire [31:0] rms_in_addr, rms_w_addr, rms_out_addr, rms_out_data;
    reg  [31:0] rms_in_data = 0, rms_w_data = 0;
    wire        rms_busy, rms_done;
    wire [7:0]  rms_error;
    wire [31:0] rms_results, rms_saturations, rms_work;
    integer rms_reads = 0;

    always @(posedge clk) begin
        if (!rst_n) begin
            rms_in_data <= 32'd0;
            rms_w_data <= 32'd0;
        end else begin
            rms_in_data <= rms_in_en ? BF16_ONE : 32'd0;
            rms_w_data <= rms_w_en ? BF16_ONE : 32'd0;
            if (rms_in_en) rms_reads = rms_reads + 1;
            if (rms_w_en) rms_reads = rms_reads + 1;
        end
    end

    ot_a3_vector_rms_norm rms (
        .clk(clk), .rst_n(rst_n), .start(rms_start),
        .cfg_count(rms_count), .cfg_rows(rms_rows), .cfg_cols(rms_cols),
        .cfg_epsilon_bits(EPSILON),
        .cfg_input_base(32'd0), .cfg_weight_base(32'd0), .cfg_output_base(32'd0),
        .input_rd_en(rms_in_en), .input_rd_addr(rms_in_addr),
        .input_rd_data(rms_in_data),
        .weight_rd_en(rms_w_en), .weight_rd_addr(rms_w_addr),
        .weight_rd_data(rms_w_data),
        .out_we(rms_out_we), .out_addr(rms_out_addr), .out_data(rms_out_data),
        .busy(rms_busy), .done(rms_done), .error_code(rms_error),
        .result_count(rms_results), .saturation_count(rms_saturations),
        .work_count(rms_work)
    );

    // -- Grouped-query attention -------------------------------------------
    reg         gqa_start = 1'b0;
    reg  [31:0] gqa_context = 0;
    wire        gqa_req_valid, gqa_out_valid;
    wire [31:0] gqa_req_addr, gqa_out_addr, gqa_out_data;
    reg         gqa_rsp_valid = 1'b0;
    reg  [31:0] gqa_rsp_data = 0;
    wire        gqa_busy, gqa_done, gqa_failed;
    wire [7:0]  gqa_error;
    wire [31:0] gqa_reads, gqa_writes, gqa_scores, gqa_exps, gqa_values;
    wire [31:0] gqa_saturations;

    always @(posedge clk) begin
        if (!rst_n) begin
            gqa_rsp_valid <= 1'b0;
            gqa_rsp_data <= 32'd0;
        end else begin
            gqa_rsp_valid <= gqa_req_valid;
            gqa_rsp_data <= BF16_ONE;
        end
    end

    ot_a3_qwen_gqa gqa (
        .clk(clk), .rst_n(rst_n), .start(gqa_start),
        .cfg_context_length(gqa_context),
        .cfg_query_base(32'd0), .cfg_key_base(32'd0),
        .cfg_value_base(32'd0), .cfg_output_base(32'd0),
        .mem_req_valid(gqa_req_valid), .mem_req_ready(1'b1),
        .mem_req_addr(gqa_req_addr),
        .mem_rsp_valid(gqa_rsp_valid), .mem_rsp_data(gqa_rsp_data),
        .out_valid(gqa_out_valid), .out_ready(1'b1),
        .out_addr(gqa_out_addr), .out_data(gqa_out_data),
        .busy(gqa_busy), .done(gqa_done), .failed(gqa_failed),
        .error_code(gqa_error),
        .memory_read_count(gqa_reads), .output_write_count(gqa_writes),
        .score_multiply_count(gqa_scores), .exponential_count(gqa_exps),
        .value_multiply_count(gqa_values), .saturation_count(gqa_saturations)
    );

    integer guard;
    integer cases_run = 0;

    task run_rms;
        input integer rows;
        input integer cols;
        begin
            rms_reads = 0;
            rms_count = rows[31:0] * cols[31:0];
            rms_rows  = rows[31:0];
            rms_cols  = cols[31:0];
            case_start = cycles;
            @(negedge clk);
            rms_start = 1'b1;
            @(negedge clk);
            rms_start = 1'b0;
            guard = 0;
            while (!rms_done && guard < 40000000) begin
                @(posedge clk);
                guard = guard + 1;
            end
            $display("SWEEP engine=rms_norm rows=%0d cols=%0d count=%0d err=%0d results=%0d work=%0d reads=%0d cycles=%0d",
                     rows, cols, rows * cols, rms_error, rms_results, rms_work,
                     rms_reads, cycles - case_start);
            cases_run = cases_run + 1;
            @(negedge clk);
        end
    endtask

    task run_gqa;
        input integer ctx_len;
        begin
            gqa_context = ctx_len[31:0];
            case_start = cycles;
            @(negedge clk);
            gqa_start = 1'b1;
            @(negedge clk);
            gqa_start = 1'b0;
            guard = 0;
            while (!gqa_done && guard < 40000000) begin
                @(posedge clk);
                guard = guard + 1;
            end
            $display("SWEEP engine=gqa context=%0d err=%0d failed=%0d reads=%0d writes=%0d scores=%0d values=%0d cycles=%0d",
                     ctx_len, gqa_error, gqa_failed, gqa_reads, gqa_writes,
                     gqa_scores, gqa_values, cycles - case_start);
            cases_run = cases_run + 1;
            @(negedge clk);
        end
    endtask

    integer i;
    integer widths [0:37];
    integer ctxs   [0:20];

    initial begin
        // Dense around every candidate threshold and around both admitted
        // widths, so a bound and an exact set cannot both survive the sweep.
        widths[0]=1;     widths[1]=2;     widths[2]=3;     widths[3]=4;
        widths[4]=5;     widths[5]=8;     widths[6]=16;    widths[7]=32;
        widths[8]=48;    widths[9]=64;    widths[10]=80;   widths[11]=96;
        widths[12]=112;  widths[13]=120;  widths[14]=126;  widths[15]=127;
        widths[16]=128;  widths[17]=129;  widths[18]=130;  widths[19]=136;
        widths[20]=144;  widths[21]=160;  widths[22]=192;  widths[23]=256;
        widths[24]=320;  widths[25]=512;  widths[26]=640;  widths[27]=1024;
        widths[28]=1280; widths[29]=2048; widths[30]=2560; widths[31]=3072;
        widths[32]=4064; widths[33]=4095; widths[34]=4096; widths[35]=4097;
        widths[36]=6144; widths[37]=8192;

        ctxs[0]=1;   ctxs[1]=2;   ctxs[2]=3;   ctxs[3]=4;   ctxs[4]=5;
        ctxs[5]=6;   ctxs[6]=7;   ctxs[7]=8;   ctxs[8]=9;   ctxs[9]=12;
        ctxs[10]=16; ctxs[11]=17; ctxs[12]=18; ctxs[13]=19; ctxs[14]=24;
        ctxs[15]=31; ctxs[16]=32; ctxs[17]=33; ctxs[18]=48; ctxs[19]=64;
        ctxs[20]=128;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);

        // One row at each width isolates the width predicate from the row count.
        for (i = 0; i < 38; i = i + 1) run_rms(1, widths[i]);

        // The multi-row forms the layer actually issues: 32 head rows of 128 at
        // the full geometry (a positive control) and 8 head rows of 16 at the
        // reduced one.  A width predicate that depended on the row count rather
        // than the width would show up as a disagreement with the one-row sweep.
        run_rms(32, 128);
        run_rms(8, 16);
        run_rms(2, 128);
        run_rms(2, 4096);

        for (i = 0; i < 21; i = i + 1) run_gqa(ctxs[i]);

        $display("MARKER: ABI3 G1F GEOMETRY PREDICATE SWEEP cases=%0d cycles=%0d",
                 cases_run, cycles);
        $finish;
    end
endmodule
