`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G1f: does the integrated RTL admit the reduced regression geometry?
//
// G1f runs the whole workload at a structurally identical, dimensionally
// reduced configuration.  Whether that is expressible is a property of the
// engines the integrated vehicle instantiates, and it is a question that must
// be MEASURED rather than read off the source: a gate field decided by
// grepping a module for a constant is exactly the defect
// docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7 records inside the G1a tool.
//
// So this checker drives the three geometry-bearing engines the vehicle
// instantiates -- ot_a3_vector_rms_norm, ot_a3_qwen_gqa and ot_a3_mac_lane --
// at both the full Qwen3-8B geometry and the reduced one, and prints what each
// engine did: its error code, its result count, its work count, the words it
// read, and the cycles it took.  Every full-geometry case is a positive
// control: a checker in which nothing is admitted measures nothing.
//
// Operands are the constant BF16 code 1.0.  This checker asks what geometry an
// engine ADMITS and what traffic it generates, not what value it computes;
// numeric equivalence is G1a's rung and is established there on real
// checkpoint bytes.
// ---------------------------------------------------------------------------
module tb_a3_g1f_reduced_geometry;
    localparam [31:0] BF16_ONE = 32'h0000_3f80;
    localparam [7:0]  FMT_BF16 = 8'h10;
    // Qwen3's rms_norm_eps, 1e-6, as the binary32 code the engines require.
    localparam [31:0] EPSILON = 32'h3586_37bd;

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

    // -- One contraction lane ----------------------------------------------
    reg         mac_start = 1'b0;
    reg  [15:0] mac_rows = 0, mac_cols = 0, mac_depth = 0;
    wire        mac_a_en, mac_b_en, mac_s_en, mac_t_en, mac_out_we;
    wire [31:0] mac_a_addr, mac_b_addr, mac_s_addr, mac_t_addr;
    wire [31:0] mac_out_addr, mac_out_data;
    reg  [31:0] mac_a_data = 0, mac_b_data = 0;
    wire        mac_busy, mac_done;
    wire [7:0]  mac_error;
    wire [31:0] mac_out_count, mac_saturations, mac_macs;

    always @(posedge clk) begin
        if (!rst_n) begin
            mac_a_data <= 32'd0;
            mac_b_data <= 32'd0;
        end else begin
            mac_a_data <= mac_a_en ? BF16_ONE : 32'd0;
            mac_b_data <= mac_b_en ? BF16_ONE : 32'd0;
        end
    end

    ot_a3_mac_lane lane (
        .clk(clk), .rst_n(rst_n), .start(mac_start),
        .cfg_rows(mac_rows), .cfg_cols(mac_cols), .cfg_depth(mac_depth),
        .cfg_dtype_a(FMT_BF16), .cfg_dtype_b(FMT_BF16),
        .cfg_a_base(32'd0), .cfg_b_base(32'd0),
        .cfg_scale_a(1'b0), .cfg_scale_b(1'b0),
        .cfg_block_a(16'd0), .cfg_block_b(16'd0),
        .cfg_block_rows_a(16'd0), .cfg_block_rows_b(16'd0),
        .cfg_scale_a_base(32'd0), .cfg_scale_b_base(32'd0),
        .cfg_out_base(32'd0),
        .a_rd_en(mac_a_en), .a_rd_addr(mac_a_addr), .a_rd_data(mac_a_data),
        .b_rd_en(mac_b_en), .b_rd_addr(mac_b_addr), .b_rd_data(mac_b_data),
        .s_rd_en(mac_s_en), .s_rd_addr(mac_s_addr), .s_rd_data(32'd0),
        .t_rd_en(mac_t_en), .t_rd_addr(mac_t_addr), .t_rd_data(32'd0),
        .out_we(mac_out_we), .out_addr(mac_out_addr), .out_data(mac_out_data),
        .busy(mac_busy), .done(mac_done), .error_code(mac_error),
        .out_count(mac_out_count), .saturation_count(mac_saturations),
        .mac_count(mac_macs)
    );

    integer guard;
    integer cases_run = 0;

    task run_rms;
        input [1023:0] label;
        input integer count;
        input integer rows;
        input integer cols;
        begin
            rms_reads = 0;
            rms_count = count[31:0];
            rms_rows = rows[31:0];
            rms_cols = cols[31:0];
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
            $display("CASE %0s engine=rms_norm rows=%0d cols=%0d count=%0d err=%0d results=%0d work=%0d reads=%0d cycles=%0d",
                     label, rows, cols, count, rms_error, rms_results, rms_work,
                     rms_reads, cycles - case_start);
            cases_run = cases_run + 1;
            @(negedge clk);
        end
    endtask

    task run_gqa;
        input [1023:0] label;
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
            $display("CASE %0s engine=gqa context=%0d err=%0d failed=%0d reads=%0d writes=%0d scores=%0d values=%0d cycles=%0d",
                     label, ctx_len, gqa_error, gqa_failed, gqa_reads,
                     gqa_writes, gqa_scores, gqa_values, cycles - case_start);
            cases_run = cases_run + 1;
            @(negedge clk);
        end
    endtask

    task run_mac;
        input [1023:0] label;
        input integer rows;
        input integer cols;
        input integer depth;
        begin
            mac_rows = rows[15:0];
            mac_cols = cols[15:0];
            mac_depth = depth[15:0];
            case_start = cycles;
            @(negedge clk);
            mac_start = 1'b1;
            @(negedge clk);
            mac_start = 1'b0;
            guard = 0;
            while (!mac_done && guard < 40000000) begin
                @(posedge clk);
                guard = guard + 1;
            end
            $display("CASE %0s engine=mac_lane rows=%0d cols=%0d depth=%0d err=%0d results=%0d macs=%0d cycles=%0d",
                     label, rows, cols, depth, mac_error, mac_out_count,
                     mac_macs, cycles - case_start);
            cases_run = cases_run + 1;
            @(negedge clk);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);

        // Positive controls: the geometry the shipped deployment issues.
        run_rms("full_model_row", 4096, 1, 4096);
        run_rms("full_head_rows", 4096, 32, 128);
        // The reduced configuration: hidden 128, 8 heads of 16.
        run_rms("reduced_model_row", 128, 1, 128);
        run_rms("reduced_head_rows", 128, 8, 16);

        // Attention.  The engine takes no geometry at all beyond context, so
        // the measurement is the traffic it generates: how many operand words
        // it reads and how many result words it writes for one query row.
        run_gqa("gqa_context_16", 16);
        run_gqa("gqa_context_below_minimum", 4);

        // The contraction lane is shape-driven, so both the reduced and the
        // full projection depths are asked for directly.
        run_mac("reduced_q_proj_row", 1, 128, 128);
        run_mac("full_depth_row", 1, 1, 4096);

        // Token ids this vehicle emitted.  It instantiates no selection
        // engine, so it emits none and prints no TOKEN line; the rung's
        // record_token_ids field is whatever TOKEN lines appear here, which
        // is how an empty list stays a measurement rather than a belief.
        $display("TOKENS: none emitted -- no selection engine is instantiated");
        $display("MARKER: ABI3 G1F REDUCED GEOMETRY PROBE cases=%0d cycles=%0d",
                 cases_run, cycles);
        $finish;
    end
endmodule
