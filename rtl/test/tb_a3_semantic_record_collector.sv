`timescale 1ns/1ps
// The collector assembles the same 128 words the decoded path assembles.
//
// Driven with the REAL raw descriptors of both shipped programs' HC_PRE dispatches
// and compared against config_words, the function tests/abi3/test_semantic_record.py
// proves equal to the raw reading. So a disagreement here is the collector's, not a
// dispute about where a field lives.
//
// The descriptors are presented in a SHUFFLED order -- not role order and not the
// sequencer's walk -- because the design claim is that roles are matched by
// identity. A bench presenting them in the order the operator names them would
// pass for a collector that merely counted arrivals.
module tb_a3_semantic_record_collector;
    localparam integer WORDS = 128;
    localparam integer DWORDS = 48;
    localparam integer ROLES = 11;

    reg clk = 0, rst_n = 0;
    reg        begin_valid = 0;
    reg [31:0] cfg_profile, cfg_active_tokens, instruction_pc, instruction_flags;
    reg [31:0] instruction_operator_id, instruction_wait_set_id;
    reg [31:0] instruction_signal_event_id, instruction_control_id;
    reg [31:0] instruction_source_operation_id;
    reg        desc_valid = 0;
    reg [31:0] desc_id = 0;
    reg [1535:0] desc_data = 0;
    wire record_valid;
    wire [WORDS*32-1:0] record_words;
    wire [7:0] error_code;
    wire [10:0] collected_mask;

    ot_a3_semantic_record_collector dut (
        .clk(clk), .rst_n(rst_n),
        .begin_valid(begin_valid),
        .cfg_profile(cfg_profile), .cfg_active_tokens(cfg_active_tokens),
        .instruction_pc(instruction_pc), .instruction_flags(instruction_flags),
        .instruction_operator_id(instruction_operator_id),
        .instruction_wait_set_id(instruction_wait_set_id),
        .instruction_signal_event_id(instruction_signal_event_id),
        .instruction_control_id(instruction_control_id),
        .instruction_source_operation_id(instruction_source_operation_id),
        .desc_valid(desc_valid), .desc_id(desc_id), .desc_data(desc_data),
        //: One stream here: these vectors present all eleven descriptors on it, so
        //: the auxiliary port is tied to the same signals. On a live tap the two
        //: differ -- the sequencer's port carries nine of the eleven roles and the
        //: bridge's carries NUMERIC and COUNTER_CLASS, measured on the four shipped
        //: programs -- and the primary is preferred when both match, so this wiring
        //: reproduces the single-stream behaviour exactly.
        .aux_desc_valid(desc_valid), .aux_desc_id(desc_id), .aux_desc_data(desc_data),
        .record_valid(record_valid), .record_words(record_words),
        .error_code(error_code), .collected_mask(collected_mask));

    always #1 clk = ~clk;

    reg [31:0] meta [0:ROLES+8];
    reg [31:0] stream [0:ROLES*DWORDS-1];
    reg [31:0] expect_words [0:WORDS-1];
    integer errors = 0, checks = 0;
    integer store, role, w, guard;
    reg [1023:0] meta_path, desc_path, exp_path;
    reg [1535:0] packed_desc;

    task automatic load_store;
        input integer which;
        begin
            if (which == 0) begin
                if (!$value$plusargs("ROM_META=%s", meta_path)) meta_path = "rom_meta.hex";
                if (!$value$plusargs("ROM_DESC=%s", desc_path)) desc_path = "rom_descriptors.hex";
                if (!$value$plusargs("ROM_EXPECT=%s", exp_path)) exp_path = "rom_expected.hex";
            end else begin
                if (!$value$plusargs("HBM_META=%s", meta_path)) meta_path = "hbm_meta.hex";
                if (!$value$plusargs("HBM_DESC=%s", desc_path)) desc_path = "hbm_descriptors.hex";
                if (!$value$plusargs("HBM_EXPECT=%s", exp_path)) exp_path = "hbm_expected.hex";
            end
            $readmemh(meta_path, meta);
            $readmemh(desc_path, stream);
            $readmemh(exp_path, expect_words);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        for (store = 0; store < 2; store = store + 1) begin
            load_store(store);
            @(negedge clk);
            cfg_profile                     = meta[0];
            cfg_active_tokens               = meta[1];
            instruction_pc                  = meta[2];
            instruction_flags               = meta[3];
            instruction_operator_id         = meta[4];
            instruction_wait_set_id         = meta[5];
            instruction_signal_event_id     = meta[6];
            instruction_control_id          = meta[7];
            instruction_source_operation_id = meta[8];
            begin_valid = 1;
            @(negedge clk);
            begin_valid = 0;

            // Present every descriptor once, in the shuffled order the vectors use.
            for (role = 0; role < ROLES; role = role + 1) begin
                packed_desc = {1536{1'b0}};
                for (w = 0; w < DWORDS; w = w + 1)
                    packed_desc[w*32 +: 32] = stream[role*DWORDS + w];
                desc_data = packed_desc;
                desc_id = meta[9 + role];
                desc_valid = 1;
                @(negedge clk);
                desc_valid = 0;
                @(negedge clk);
            end

            guard = 0;
            while (!record_valid && guard < 64) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!record_valid) begin
                errors = errors + 1;
                $display("FAIL store=%0d record never completed mask=%b error=%0d",
                         store, collected_mask, error_code);
            end else begin
                if (error_code != 0) begin
                    errors = errors + 1;
                    $display("FAIL store=%0d error_code=%0d", store, error_code);
                end
                for (w = 0; w < WORDS; w = w + 1) begin
                    checks = checks + 1;
                    if (record_words[w*32 +: 32] !== expect_words[w]) begin
                        errors = errors + 1;
                        if (errors < 12)
                            $display("FAIL store=%0d word %0d got=%08x want=%08x",
                                     store, w, record_words[w*32 +: 32], expect_words[w]);
                    end
                end
            end
        end

        $display("A3_SEMANTIC_RECORD_SUMMARY stores=2 words_checked=%0d errors=%0d",
                 checks, errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
