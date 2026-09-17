`timescale 1ns/1ps
// HC_PRE executing on a record the COLLECTOR assembled, not one a bench wrote.
//
// tb_a3_hc_pre_t1 drives ot_a3_hc_pre_t1_descriptor_rne from config_words read out
// of a vector file, which proves the engine's arithmetic and says nothing about
// where such a record would come from in a device.  This drives the same engine
// from ot_a3_semantic_record_collector, fed the raw descriptors of the shipped ROM
// program, so the chain under test is
//
//     raw descriptors -> collector -> 128-word record -> HC_PRE -> coefficients
//
// and the coefficients are compared against the same expected vector the engine's
// own campaign uses.  That is the whole path from what the microsequencer carries on
// its descriptor port to what the operator produces, with nothing hand-assembled in
// between.
//
// Still not a token: the sequencer is not here, the collector is fed by this bench
// rather than tapped off a live fetch port, and one operator of one layer is not a
// model.  What it removes is the possibility that the collector and the engine agree
// with a golden separately but not with each other.
module tb_a3_hc_pre_collected;
    localparam integer WIDTH = 16384;
    localparam integer FIELDS = 24;
    localparam integer CONFIG_WORDS = 128;
    localparam integer EXPECTED_WORDS = 74;
    localparam integer DWORDS = 48;
    localparam integer ROLES = 11;

    reg clk = 0, rst_n = 0;

    // -- the collector ---------------------------------------------------
    reg        begin_valid = 0;
    reg [31:0] cfg_profile, cfg_active_tokens, instruction_pc, instruction_flags;
    reg [31:0] instruction_operator_id, instruction_wait_set_id;
    reg [31:0] instruction_signal_event_id, instruction_control_id;
    reg [31:0] instruction_source_operation_id;
    reg        desc_valid = 0;
    reg [31:0] desc_id = 0;
    reg [1535:0] desc_data = 0;
    wire record_valid;
    wire [CONFIG_WORDS*32-1:0] record_words;
    wire [7:0]  collector_error;
    wire [10:0] collected_mask;

    ot_a3_semantic_record_collector collector (
        .clk(clk), .rst_n(rst_n), .begin_valid(begin_valid),
        .cfg_profile(cfg_profile), .cfg_active_tokens(cfg_active_tokens),
        .instruction_pc(instruction_pc), .instruction_flags(instruction_flags),
        .instruction_operator_id(instruction_operator_id),
        .instruction_wait_set_id(instruction_wait_set_id),
        .instruction_signal_event_id(instruction_signal_event_id),
        .instruction_control_id(instruction_control_id),
        .instruction_source_operation_id(instruction_source_operation_id),
        .desc_valid(desc_valid), .desc_id(desc_id), .desc_data(desc_data),
        .record_valid(record_valid), .record_words(record_words),
        .error_code(collector_error), .collected_mask(collected_mask));

    // -- the engine, fed by the collector --------------------------------
    reg         in_valid = 0;
    wire        in_ready;
    reg  [767:0] base_codes;
    reg  [95:0]  scale_codes;
    wire         hidden_rd_en;
    wire [13:0]  hidden_rd_k;
    reg  [15:0]  hidden_rd_data;
    wire         weight_rd_en;
    wire [4:0]   weight_rd_field_base;
    wire [13:0]  weight_rd_k;
    reg  [255:0] weight_rd_data;
    wire         out_valid;
    reg          out_ready = 1;
    wire [255:0] result_weight_codes;
    wire [511:0] result_combination_codes;
    wire [7:0]   result_error;
    wire [63:0]  sched_proj, sched_commit, sched_fmas, sched_outputs;
    wire [31:0]  arith_square, arith_add, arith_fma;

    ot_a3_hc_pre_t1_descriptor_rne engine (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_ready(in_ready),
        //: THE RECORD THE COLLECTOR BUILT, wired straight through.
        .config_words(record_words),
        .base_codes(base_codes), .scale_codes(scale_codes),
        .hidden_rd_en(hidden_rd_en), .hidden_rd_k(hidden_rd_k),
        .hidden_rd_data(hidden_rd_data),
        .weight_rd_en(weight_rd_en), .weight_rd_field_base(weight_rd_field_base),
        .weight_rd_k(weight_rd_k), .weight_rd_data(weight_rd_data),
        .out_valid(out_valid), .out_ready(out_ready),
        .result_weight_codes(result_weight_codes),
        .result_combination_codes(result_combination_codes),
        .result_error(result_error),
        .scheduler_projection_tiles(sched_proj),
        .scheduler_commit_tiles(sched_commit),
        .scheduler_logical_fmas(sched_fmas),
        .scheduler_logical_outputs(sched_outputs),
        .arithmetic_square_count(arith_square),
        .arithmetic_reduction_add_count(arith_add),
        .arithmetic_fma_count(arith_fma));

    always #5 clk = ~clk;

    reg [15:0] hidden_mem [0:WIDTH-1];
    reg [31:0] projection_mem [0:FIELDS*WIDTH-1];
    reg [31:0] base_mem [0:FIELDS-1];
    reg [31:0] scale_mem [0:2];
    reg [31:0] expected_mem [0:EXPECTED_WORDS-1];
    reg [31:0] meta [0:ROLES+8];
    reg [31:0] stream [0:ROLES*DWORDS-1];

    integer lane, address;
    always @(posedge clk) begin
        if (hidden_rd_en)
            hidden_rd_data <= hidden_mem[hidden_rd_k];
        if (weight_rd_en)
            for (lane = 0; lane < 8; lane = lane + 1) begin
                address = (weight_rd_field_base + lane) * WIDTH + weight_rd_k;
                weight_rd_data[32*lane +: 32] <= projection_mem[address];
            end
    end

    integer errors = 0, checks = 0, role, w, guard;
    reg [1023:0] path;
    reg [1535:0] packed_desc;

    task automatic expect32;
        input [1023:0] label;
        input [31:0] got, want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                errors = errors + 1;
                if (errors < 10)
                    $display("FAIL %0s got=%08x want=%08x", label, got, want);
            end
        end
    endtask

    initial begin
        if ($value$plusargs("HIDDEN=%s", path)) $readmemh(path, hidden_mem);
        if ($value$plusargs("PROJECTION=%s", path)) $readmemh(path, projection_mem);
        if ($value$plusargs("BASE=%s", path)) $readmemh(path, base_mem);
        if ($value$plusargs("SCALE=%s", path)) $readmemh(path, scale_mem);
        if ($value$plusargs("EXPECTED=%s", path)) $readmemh(path, expected_mem);
        if ($value$plusargs("ROM_META=%s", path)) $readmemh(path, meta);
        if ($value$plusargs("ROM_DESC=%s", path)) $readmemh(path, stream);
        for (w = 0; w < FIELDS; w = w + 1)
            base_codes[32*w +: 32] = base_mem[w];
        for (w = 0; w < 3; w = w + 1)
            scale_codes[32*w +: 32] = scale_mem[w];

        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        cfg_profile                     = meta[0];
        cfg_active_tokens               = meta[1];
        instruction_pc                  = meta[2];
        instruction_flags               = meta[3];
        instruction_operator_id         = meta[4];
        instruction_wait_set_id         = meta[5];
        instruction_signal_event_id     = meta[6];
        instruction_control_id          = meta[7];
        instruction_source_operation_id = meta[8];
        @(negedge clk); begin_valid = 1; @(negedge clk); begin_valid = 0;

        for (role = 0; role < ROLES; role = role + 1) begin
            packed_desc = {1536{1'b0}};
            for (w = 0; w < DWORDS; w = w + 1)
                packed_desc[w*32 +: 32] = stream[role*DWORDS + w];
            desc_data = packed_desc;
            desc_id = meta[9 + role];
            desc_valid = 1; @(negedge clk);
            desc_valid = 0; @(negedge clk);
        end

        guard = 0;
        while (!record_valid && guard < 64) begin @(negedge clk); guard = guard + 1; end
        if (!record_valid) begin
            errors = errors + 1;
            $display("FAIL collector never completed mask=%b error=%0d",
                     collected_mask, collector_error);
        end else begin
            //: Hand the collected record to the engine and let it run.
            in_valid = 1;
            guard = 0;
            while (!(in_valid && in_ready) && guard < 64) begin
                @(negedge clk); guard = guard + 1;
            end
            @(negedge clk); in_valid = 0;

            guard = 0;
            while (!out_valid && guard < 400000) begin @(negedge clk); guard = guard + 1; end
            if (!out_valid) begin
                errors = errors + 1;
                $display("FAIL engine produced no result in %0d cycles", guard);
            end else begin
                expect32("engine error", {24'd0, result_error}, 32'd0);
                for (w = 0; w < 8; w = w + 1)
                    expect32("weight coefficient",
                             result_weight_codes[32*w +: 32], expected_mem[50 + w]);
                for (w = 0; w < 16; w = w + 1)
                    expect32("combination coefficient",
                             result_combination_codes[32*w +: 32],
                             expected_mem[58 + w]);
                expect32("fused accumulations", arith_fma, 32'd393216);
                expect32("balanced reduction adds", arith_add, 32'd16383);
            end
        end

        $display("A3_HC_PRE_COLLECTED_SUMMARY checks=%0d errors=%0d", checks, errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
