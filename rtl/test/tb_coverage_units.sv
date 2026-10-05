`timescale 1ns/1ps

// Deterministic functional/code-coverage bench for inventory blocks that do
// not sit on the stage-control path.  Every check has an independent oracle;
// COVER_BIN lines are consumed by the machine-readable coverage campaign.
module tb_coverage_units;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    integer failures = 0;
    integer checks = 0;
    integer packet_index;
    reg [31:0] rng_state = 32'h4356_554e;

    function automatic [31:0] random32;
        reg [31:0] x;
        begin
            x = rng_state;
            x = x ^ (x << 13);
            x = x ^ (x >> 17);
            x = x ^ (x << 5);
            rng_state = x;
            random32 = x;
        end
    endfunction

    task automatic require_true;
        input condition;
        input [8*96-1:0] message;
        begin
            checks = checks + 1;
            if (!condition) begin
                $display("FAIL check=%0d %0s", checks, message);
                failures = failures + 1;
            end
        end
    endtask

    task automatic pass_bin;
        input [8*96-1:0] bin_id;
        input condition;
        begin
            require_true(condition, bin_id);
            if (condition)
                $display("COVER_BIN %0s PASS", bin_id);
        end
    endtask

    function automatic [15:0] crc16_extend64;
        input [15:0] initial_crc;
        input [63:0] data;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = initial_crc;
            for (byte_i = 0; byte_i < 8; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ data[byte_i*8 + bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_extend64 = c;
        end
    endfunction

    function automatic [31:0] crc32c_extend64;
        input [31:0] initial_crc;
        input [63:0] data;
        integer byte_i;
        integer bit_i;
        reg [31:0] c;
        reg feedback;
        begin
            c = initial_crc;
            for (byte_i = 0; byte_i < 8; byte_i = byte_i + 1)
                for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                    feedback = c[0] ^ data[byte_i*8 + bit_i];
                    c = c >> 1;
                    if (feedback)
                        c = c ^ 32'h82f63b78;
                end
            crc32c_extend64 = c;
        end
    endfunction

    function automatic [15:0] crc16_route;
        input [207:0] data;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 26; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ data[byte_i*8 + bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_route = c;
        end
    endfunction

    // ------------------------------------------------------------------
    // Streaming CRC known answers and beat-boundary invariance.
    reg crc16_valid = 1'b0;
    reg crc16_start = 1'b0;
    reg crc16_last = 1'b0;
    reg [63:0] crc16_data = 64'b0;
    wire crc16_out_valid;
    wire [15:0] crc16_value;
    ot_crc16_ccitt #(.DATA_W(64)) crc16_dut (
        .clk(clk), .rst_n(rst_n), .in_valid(crc16_valid),
        .start(crc16_start), .last(crc16_last), .data(crc16_data),
        .out_valid(crc16_out_valid), .crc(crc16_value));

    reg crc32_valid = 1'b0;
    reg crc32_start = 1'b0;
    reg crc32_last = 1'b0;
    reg [63:0] crc32_data = 64'b0;
    wire crc32_out_valid;
    wire [31:0] crc32_value;
    ot_crc32c #(.DATA_W(64)) crc32_dut (
        .clk(clk), .rst_n(rst_n), .in_valid(crc32_valid),
        .start(crc32_start), .last(crc32_last), .data(crc32_data),
        .out_valid(crc32_out_valid), .crc(crc32_value));

    task automatic crc_beat;
        input use_crc32;
        input start_beat;
        input last_beat;
        input [63:0] data;
        begin
            @(negedge clk);
            if (use_crc32) begin
                crc32_valid = 1'b1;
                crc32_start = start_beat;
                crc32_last = last_beat;
                crc32_data = data;
            end else begin
                crc16_valid = 1'b1;
                crc16_start = start_beat;
                crc16_last = last_beat;
                crc16_data = data;
            end
            @(negedge clk);
            crc16_valid = 1'b0;
            crc32_valid = 1'b0;
            crc16_start = 1'b0;
            crc32_start = 1'b0;
            crc16_last = 1'b0;
            crc32_last = 1'b0;
        end
    endtask

    task automatic test_crc;
        integer sample;
        reg [15:0] expected16;
        reg [31:0] expected32_state;
        reg [63:0] first_data;
        reg [63:0] second_data;
        begin
            first_data = 64'h3736_3534_3332_3130;
            second_data = 64'h6665_6463_6261_3938;
            expected16 = crc16_extend64(16'hffff, first_data);
            crc_beat(1'b0,1'b1,1'b1,first_data);
            pass_bin("COV-UNIT-CRC16-SINGLE",
                     crc16_out_valid && crc16_value == expected16);

            expected16 = crc16_extend64(expected16, second_data);
            crc_beat(1'b0,1'b1,1'b0,first_data);
            require_true(!crc16_out_valid,"CRC16 asserted valid before last beat");
            crc_beat(1'b0,1'b0,1'b1,second_data);
            pass_bin("COV-UNIT-CRC16-MULTIBEAT",
                     crc16_out_valid && crc16_value == expected16);

            expected32_state = crc32c_extend64(32'hffff_ffff,first_data);
            crc_beat(1'b1,1'b1,1'b1,first_data);
            pass_bin("COV-UNIT-CRC32C-SINGLE",
                     crc32_out_valid && crc32_value == (expected32_state ^ 32'hffff_ffff));

            expected32_state = crc32c_extend64(expected32_state,second_data);
            crc_beat(1'b1,1'b1,1'b0,first_data);
            require_true(!crc32_out_valid,"CRC32C asserted valid before last beat");
            crc_beat(1'b1,1'b0,1'b1,second_data);
            pass_bin("COV-UNIT-CRC32C-MULTIBEAT",
                     crc32_out_valid && crc32_value == (expected32_state ^ 32'hffff_ffff));

            // Random single- and multi-beat messages force both transition
            // directions on every datapath bit while retaining an independent
            // software-style recurrence oracle for every result.
            for (sample = 0; sample < 128; sample = sample + 1) begin
                first_data = {random32(),random32()};
                second_data = {random32(),random32()};

                expected16 = crc16_extend64(16'hffff,first_data);
                crc_beat(1'b0,1'b1,1'b1,first_data);
                require_true(crc16_out_valid && crc16_value == expected16,
                             "CRC16 randomized single-beat result");

                expected32_state = crc32c_extend64(32'hffff_ffff,first_data);
                crc_beat(1'b1,1'b1,1'b1,first_data);
                require_true(crc32_out_valid &&
                             crc32_value == (expected32_state ^ 32'hffff_ffff),
                             "CRC32C randomized single-beat result");

                if ((sample % 3) == 0) begin
                    expected16 = crc16_extend64(16'hffff,first_data);
                    expected16 = crc16_extend64(expected16,second_data);
                    crc_beat(1'b0,1'b1,1'b0,first_data);
                    require_true(!crc16_out_valid,
                                 "CRC16 randomized early valid");
                    crc_beat(1'b0,1'b0,1'b1,second_data);
                    require_true(crc16_out_valid && crc16_value == expected16,
                                 "CRC16 randomized multi-beat result");

                    expected32_state =
                        crc32c_extend64(32'hffff_ffff,first_data);
                    expected32_state =
                        crc32c_extend64(expected32_state,second_data);
                    crc_beat(1'b1,1'b1,1'b0,first_data);
                    require_true(!crc32_out_valid,
                                 "CRC32C randomized early valid");
                    crc_beat(1'b1,1'b0,1'b1,second_data);
                    require_true(crc32_out_valid &&
                                 crc32_value ==
                                 (expected32_state ^ 32'hffff_ffff),
                                 "CRC32C randomized multi-beat result");
                end
            end
        end
    endtask

    // ------------------------------------------------------------------
    // Exhaustive public numeric-format classification.
    reg [3:0] format_mode = 4'b0;
    reg [15:0] format_code = 16'b0;
    wire format_finite;
    wire format_zero;
    wire format_nan;
    wire format_infinity;
    wire format_negative;
    wire signed [31:0] format_value;
    wire signed [15:0] format_mantissa;
    wire signed [8:0] format_exponent;
    ot_format_decode format_dut (
        .mode(format_mode), .code(format_code), .finite(format_finite),
        .zero(format_zero), .nan(format_nan), .infinity(format_infinity),
        .negative(format_negative), .value_q16(format_value),
        .mantissa(format_mantissa), .exponent(format_exponent));

    task automatic test_formats;
        integer code_i;
        integer mode_i;
        reg expected_zero;
        reg expected_nan;
        reg expected_inf;
        reg expected_finite;
        reg [31:0] random_word;
        integer format_errors;
        begin
            format_errors = 0;
            format_mode = 4'd0;
            for (code_i = 0; code_i < 256; code_i = code_i + 1) begin
                format_code = {8'b0,code_i[7:0]};
                #1;
                if (!(format_finite && !format_nan && !format_infinity))
                    format_errors = format_errors + 1;
                if (format_zero != (code_i == 0))
                    format_errors = format_errors + 1;
                if (format_mantissa != $signed({{8{code_i[7]}},code_i[7:0]}))
                    format_errors = format_errors + 1;
            end
            checks = checks + 3*256;
            pass_bin("COV-UNIT-FORMAT-INT-EXHAUSTIVE",format_errors == 0);

            format_errors = 0;
            format_mode = 4'd1;
            for (code_i = 0; code_i < 16; code_i = code_i + 1) begin
                format_code = code_i[15:0];
                #1;
                if (!(format_finite && !format_nan && !format_infinity))
                    format_errors = format_errors + 1;
                if (format_zero != ((code_i & 7) == 0))
                    format_errors = format_errors + 1;
                if (format_zero && format_negative)
                    format_errors = format_errors + 1;
            end
            checks = checks + 3*16;
            pass_bin("COV-UNIT-FORMAT-MXFP4-EXHAUSTIVE",format_errors == 0);

            format_errors = 0;
            format_mode = 4'd2;
            for (code_i = 0; code_i < 256; code_i = code_i + 1) begin
                format_code = {8'b0,code_i[7:0]};
                #1;
                expected_zero = ((code_i & 32'h0000_007f) == 0);
                expected_nan = (((code_i >> 3) & 32'h0000_000f) == 32'h0000_000f) &&
                               ((code_i & 32'h0000_0007) == 32'h0000_0007);
                expected_finite = !expected_nan;
                if (format_zero != expected_zero)
                    format_errors = format_errors + 1;
                if (format_nan != expected_nan)
                    format_errors = format_errors + 1;
                if (format_finite != expected_finite)
                    format_errors = format_errors + 1;
                if (format_infinity)
                    format_errors = format_errors + 1;
            end
            checks = checks + 4*256;
            pass_bin("COV-UNIT-FORMAT-FP8-EXHAUSTIVE",format_errors == 0);

            format_mode = 4'd2;
            format_code = 16'h007e;
            #1;
            require_true(format_finite && !format_nan &&
                         format_mantissa == 16'sd14 &&
                         format_exponent == 9'sd5,
                         "E4M3FN positive finite endpoint is +448");
            format_code = 16'h00fe;
            #1;
            require_true(format_finite && !format_nan && format_negative &&
                         format_mantissa == -16'sd14 &&
                         format_exponent == 9'sd5,
                         "E4M3FN negative finite endpoint is -448");

            format_errors = 0;
            format_mode = 4'd3;
            for (code_i = 0; code_i < 65536; code_i = code_i + 1) begin
                format_code = code_i[15:0];
                #1;
                expected_zero = ((code_i & 32'h0000_7fff) == 0);
                expected_inf = ((code_i & 32'h0000_7f80) == 32'h0000_7f80) &&
                               ((code_i & 32'h0000_007f) == 0);
                expected_nan = ((code_i & 32'h0000_7f80) == 32'h0000_7f80) &&
                               ((code_i & 32'h0000_007f) != 0);
                expected_finite = !expected_inf && !expected_nan;
                if (format_zero != expected_zero)
                    format_errors = format_errors + 1;
                if (format_infinity != expected_inf)
                    format_errors = format_errors + 1;
                if (format_nan != expected_nan)
                    format_errors = format_errors + 1;
                if (format_finite != expected_finite)
                    format_errors = format_errors + 1;
                if (format_zero && format_negative)
                    format_errors = format_errors + 1;
            end
            checks = checks + 5*65536;
            pass_bin("COV-UNIT-FORMAT-BF16-EXHAUSTIVE",format_errors == 0);

            format_errors = 0;
            for (mode_i = 4; mode_i < 16; mode_i = mode_i + 1) begin
                format_mode = mode_i[3:0];
                random_word = random32();
                format_code = random_word[15:0];
                #1;
                if (!(format_nan && !format_finite && !format_infinity))
                    format_errors = format_errors + 1;
            end
            checks = checks + 12;
            pass_bin("COV-UNIT-FORMAT-RESERVED",format_errors == 0);
        end
    endtask

    // ------------------------------------------------------------------
    // Combinational reduction and tagged, backpressured collector.
    reg [3:0] tree_valid = 4'b0;
    reg signed [31:0] tree_data = 32'b0;
    wire signed [7:0] tree_sum;
    wire tree_overflow;
    ot_reduction_tree #(.SOURCES(4),.DATA_W(8)) tree_dut (
        .source_valid(tree_valid), .source_data(tree_data),
        .sum(tree_sum), .overflow(tree_overflow));

    reg reduction_in_valid = 1'b0;
    wire reduction_in_ready;
    reg [7:0] reduction_in_tag = 8'b0;
    reg [1:0] reduction_in_source = 2'b0;
    reg signed [15:0] reduction_in_data = 16'sb0;
    reg reduction_in_poison = 1'b0;
    reg reduction_in_last = 1'b0;
    wire reduction_out_valid;
    reg reduction_out_ready = 1'b0;
    wire [7:0] reduction_out_tag;
    wire signed [15:0] reduction_out_data;
    wire reduction_out_poison;
    wire reduction_duplicate;
    wire reduction_unexpected;
    ot_reduction_endpoint #(.SOURCES(3),.DATA_W(16),.GROUPS(2),.TAG_W(8)) reduction_dut (
        .clk(clk), .rst_n(rst_n), .in_valid(reduction_in_valid),
        .in_ready(reduction_in_ready), .in_tag(reduction_in_tag),
        .in_source(reduction_in_source), .in_data(reduction_in_data),
        .in_poison(reduction_in_poison), .in_last(reduction_in_last),
        .out_valid(reduction_out_valid), .out_ready(reduction_out_ready),
        .out_tag(reduction_out_tag), .out_data(reduction_out_data),
        .out_poison(reduction_out_poison), .duplicate_error(reduction_duplicate),
        .unexpected_error(reduction_unexpected));

    task automatic reduction_send;
        input [7:0] tag;
        input [1:0] source_id;
        input signed [15:0] data;
        input poison;
        input last;
        begin
            @(negedge clk);
            reduction_in_valid = 1'b1;
            reduction_in_tag = tag;
            reduction_in_source = source_id;
            reduction_in_data = data;
            reduction_in_poison = poison;
            reduction_in_last = last;
            @(negedge clk);
            reduction_in_valid = 1'b0;
            reduction_in_poison = 1'b0;
            reduction_in_last = 1'b0;
        end
    endtask

    task automatic reduction_expect_pair;
        input [7:0] expected_tag_a;
        input signed [15:0] expected_data_a;
        input expected_poison_a;
        input [7:0] expected_tag_b;
        input signed [15:0] expected_data_b;
        input expected_poison_b;
        integer wait_cycles;
        integer result_index;
        reg saw_a;
        reg saw_b;
        begin
            saw_a = 1'b0;
            saw_b = 1'b0;
            for (result_index = 0; result_index < 2;
                 result_index = result_index + 1) begin
                wait_cycles = 0;
                while (!reduction_out_valid && wait_cycles < 100) begin
                    @(negedge clk);
                    wait_cycles = wait_cycles + 1;
                end
                if (!reduction_out_valid)
                    $display("REDUCTION_TIMEOUT exp_a=%h exp_b=%h gv=%b%b tag=%h/%h seen=%b/%b last=%b%b out=%b:%h",
                             expected_tag_a,expected_tag_b,
                             reduction_dut.group_valid[1],
                             reduction_dut.group_valid[0],
                             reduction_dut.group_tag[0],
                             reduction_dut.group_tag[1],
                             reduction_dut.seen[0],reduction_dut.seen[1],
                             reduction_dut.last_mem[1],
                             reduction_dut.last_mem[0],
                             reduction_out_valid,reduction_out_tag);
                require_true(reduction_out_valid,
                             "randomized reduction output timeout");
                if (reduction_out_valid && reduction_out_tag == expected_tag_a) begin
                    require_true(!saw_a,
                                 "randomized reduction duplicate tag A");
                    require_true(reduction_out_data == expected_data_a,
                                 "randomized reduction sum A");
                    require_true(reduction_out_poison == expected_poison_a,
                                 "randomized reduction poison A");
                    saw_a = 1'b1;
                end else if (reduction_out_valid &&
                             reduction_out_tag == expected_tag_b) begin
                    require_true(!saw_b,
                                 "randomized reduction duplicate tag B");
                    require_true(reduction_out_data == expected_data_b,
                                 "randomized reduction sum B");
                    require_true(reduction_out_poison == expected_poison_b,
                                 "randomized reduction poison B");
                    saw_b = 1'b1;
                end else begin
                    $display("REDUCTION_UNEXPECTED got=%h exp_a=%h exp_b=%h data=%h poison=%b",
                             reduction_out_tag,expected_tag_a,expected_tag_b,
                             reduction_out_data,reduction_out_poison);
                    require_true(1'b0,
                                 "randomized reduction unexpected tag");
                end
                reduction_out_ready = 1'b1;
                @(negedge clk);
                reduction_out_ready = 1'b0;
            end
            require_true(saw_a && saw_b,
                         "randomized reduction pair completion");
        end
    endtask

    task automatic test_reduction;
        integer sample;
        integer total;
        integer value_i;
        integer source_i;
        reg [31:0] random_word;
        reg signed [15:0] held_data;
        reg [7:0] held_tag;
        reg [7:0] tag_a;
        reg [7:0] tag_b;
        reg signed [15:0] data_a0;
        reg signed [15:0] data_a1;
        reg signed [15:0] data_a2;
        reg signed [15:0] data_b0;
        reg signed [15:0] data_b1;
        reg signed [15:0] data_b2;
        reg signed [17:0] sum_a;
        reg signed [17:0] sum_b;
        reg poison_a;
        reg poison_b;
        begin
            for (sample = 0; sample < 2048; sample = sample + 1) begin
                random_word = random32();
                tree_valid = random_word[3:0];
                tree_data = random32();
                #1;
                total = 0;
                for (source_i = 0; source_i < 4; source_i = source_i + 1) begin
                    value_i = $signed({{24{tree_data[source_i*8+7]}},
                                       tree_data[source_i*8 +: 8]});
                    if (tree_valid[source_i])
                        total = total + value_i;
                end
                require_true(tree_sum == total[7:0],"reduction sum ordering");
                require_true(tree_overflow == ((total > 127) || (total < -128)),
                             "reduction overflow classification");
            end
            pass_bin("COV-UNIT-REDUCTION-RANDOM",failures == 0);

            reduction_send(8'h31,2'd2,-16'sd2,1'b0,1'b0);
            reduction_send(8'h31,2'd0,-16'sd5,1'b0,1'b0);
            reduction_send(8'h31,2'd1,16'sd107,1'b0,1'b1);
            wait (reduction_out_valid);
            reduction_out_ready = 1'b0;
            held_data = reduction_out_data;
            held_tag = reduction_out_tag;
            repeat (4) begin
                @(negedge clk);
                require_true(reduction_out_valid && reduction_out_data == held_data &&
                             reduction_out_tag == held_tag,"reduction stall stability");
            end
            pass_bin("COV-UNIT-REDUCTION-OOO-STALL",
                     held_tag == 8'h31 && held_data == 16'sd100 && !reduction_out_poison);
            reduction_out_ready = 1'b1;
            @(negedge clk);
            reduction_out_ready = 1'b0;
            @(negedge clk);
            pass_bin("COV-UNIT-REDUCTION-NO-DUPLICATE",!reduction_out_valid);

            reduction_send(8'h52,2'd0,16'sd3,1'b0,1'b0);
            reduction_send(8'h52,2'd0,16'sd9,1'b0,1'b0);
            reduction_send(8'h52,2'd1,16'sd4,1'b0,1'b0);
            reduction_send(8'h52,2'd2,16'sd5,1'b1,1'b1);
            wait (reduction_out_valid);
            pass_bin("COV-UNIT-REDUCTION-DUPLICATE-POISON",
                     reduction_duplicate && reduction_out_poison);
            reduction_out_ready = 1'b1;
            @(negedge clk);
            reduction_out_ready = 1'b0;

            reduction_send(8'h70,2'd3,16'sd1,1'b0,1'b1);
            pass_bin("COV-UNIT-REDUCTION-ILLEGAL-SOURCE",reduction_unexpected);
            // The preceding poisoned duplicate result is intentionally held
            // until after the illegal-source check.  Retire it across a full
            // active clock edge before allocating both randomized group slots.
            if (reduction_out_valid) begin
                reduction_out_ready = 1'b1;
                @(negedge clk);
                reduction_out_ready = 1'b0;
            end
            @(negedge clk);

            // Repeatedly occupy both architectural group slots, complete them
            // under output backpressure, and check the source-ID-ordered sum.
            // This reaches retained data/tag state on both groups instead of
            // repeatedly recycling only the lowest free slot.
            for (sample = 0; sample < 96; sample = sample + 1) begin
                random_word = random32();
                tag_a = random_word[7:0];
                tag_b = random_word[15:8] ^ 8'ha5;
                if (tag_b == tag_a)
                    tag_b = tag_b ^ 8'hff;
                random_word = random32();
                data_a0 = random_word[15:0];
                data_a1 = random_word[31:16];
                random_word = random32();
                data_a2 = random_word[15:0];
                data_b0 = random_word[31:16];
                random_word = random32();
                data_b1 = random_word[15:0];
                data_b2 = random_word[31:16];
                poison_a = (sample % 11) == 0;
                poison_b = (sample % 13) == 0;
                sum_a = {{2{data_a0[15]}},data_a0} +
                        {{2{data_a1[15]}},data_a1} +
                        {{2{data_a2[15]}},data_a2};
                sum_b = {{2{data_b0[15]}},data_b0} +
                        {{2{data_b1[15]}},data_b1} +
                        {{2{data_b2[15]}},data_b2};

                reduction_send(tag_a,2'd0,data_a0,1'b0,1'b0);
                reduction_send(tag_b,2'd2,data_b2,poison_b,1'b0);
                reduction_send(tag_a,2'd2,data_a2,poison_a,1'b0);
                reduction_send(tag_b,2'd0,data_b0,1'b0,1'b0);
                reduction_send(tag_a,2'd1,data_a1,1'b0,1'b1);
                reduction_send(tag_b,2'd1,data_b1,1'b0,1'b1);
                reduction_expect_pair(tag_a,sum_a[15:0],poison_a,
                                      tag_b,sum_b[15:0],poison_b);
            end
        end
    endtask

    // ------------------------------------------------------------------
    // Compile-time scheduled switch, including explicit idle/illegal source.
    reg [2:0] switch_in_valid = 3'b0;
    reg [47:0] switch_in_flit = 48'b0;
    wire [2:0] switch_out_valid;
    wire [47:0] switch_out_flit;
    static_timeslot_switch #(.PORTS(3),.FLIT_W(16),.SLOTS(4)) switch_dut (
        .clk(clk), .rst_n(rst_n), .in_valid(switch_in_valid),
        .in_flit(switch_in_flit), .out_valid(switch_out_valid),
        .out_flit(switch_out_flit));

    task automatic test_switch;
        integer cycle;
        integer output_port;
        reg [1:0] selected_port;
        reg [1:0] sampled_slot;
        reg [2:0] expected_valid;
        reg [47:0] expected_flit;
        reg saw_illegal;
        reg saw_wrap;
        reg [31:0] random_word;
        begin
            switch_dut.schedule[0][1:0] = 2'd0;
            switch_dut.schedule[0][3:2] = 2'd1;
            switch_dut.schedule[0][5:4] = 2'd2;
            switch_dut.schedule[1][1:0] = 2'd2;
            switch_dut.schedule[1][3:2] = 2'd0;
            switch_dut.schedule[1][5:4] = 2'd1;
            switch_dut.schedule[2][1:0] = 2'd1;
            switch_dut.schedule[2][3:2] = 2'd2;
            switch_dut.schedule[2][5:4] = 2'd0;
            switch_dut.schedule[3][1:0] = 2'd3;
            switch_dut.schedule[3][3:2] = 2'd1;
            switch_dut.schedule[3][5:4] = 2'd0;
            saw_illegal = 1'b0;
            saw_wrap = 1'b0;
            for (cycle = 0; cycle < 256; cycle = cycle + 1) begin
                @(negedge clk);
                random_word = random32();
                switch_in_valid = random_word[2:0];
                random_word = random32();
                switch_in_flit[15:0] = random_word[15:0];
                random_word = random32();
                switch_in_flit[31:16] = random_word[15:0];
                random_word = random32();
                switch_in_flit[47:32] = random_word[15:0];
                sampled_slot = switch_dut.slot;
                expected_valid = 3'b0;
                expected_flit = 48'b0;
                for (output_port = 0; output_port < 3; output_port = output_port + 1) begin
                    selected_port = switch_dut.schedule[sampled_slot][output_port*2 +: 2];
                    if (selected_port < 3) begin
                        expected_valid[output_port] = switch_in_valid[selected_port];
                        expected_flit[output_port*16 +: 16] =
                            switch_in_flit[selected_port*16 +: 16];
                    end else begin
                        saw_illegal = 1'b1;
                    end
                end
                @(posedge clk); #1;
                if (sampled_slot == 3 && switch_dut.slot == 0)
                    saw_wrap = 1'b1;
                require_true(switch_out_valid == expected_valid,"timeslot valid selection");
                require_true(switch_out_flit == expected_flit,"timeslot flit selection");
            end
            pass_bin("COV-UNIT-STATIC-SWITCH-LEGAL",failures == 0);
            pass_bin("COV-UNIT-STATIC-SWITCH-ILLEGAL-IDLE",saw_illegal);
            pass_bin("COV-UNIT-STATIC-SWITCH-WRAP",saw_wrap);
        end
    endtask

    // ------------------------------------------------------------------
    // TX/RX endpoint composition with independent end-to-end queue checks.
    reg link_tx_valid = 1'b0;
    wire link_tx_ready;
    reg [31:0] link_tx_flit = 32'b0;
    reg link_tx_last = 1'b0;
    reg [7:0] link_tx_seq = 8'b0;
    wire link_wire_valid;
    wire link_wire_ready;
    wire [31:0] link_wire_flit;
    wire [31:0] link_wire_flit_crc;
    wire [31:0] link_wire_packet_crc;
    wire link_wire_last;
    wire [7:0] link_wire_seq;
    wire link_rx_valid;
    reg link_rx_ready = 1'b0;
    wire [31:0] link_rx_flit;
    wire link_rx_last;
    wire [7:0] link_rx_seq;
    wire link_rx_poison;
    wire link_ack_valid;
    wire [7:0] link_ack_seq;
    wire link_ack_ok;
    wire link_busy;
    wire [1:0] link_retry_count;
    wire link_credit_consumed;
    wire link_timeout;
    wire link_tx_error;
    wire link_rx_error;
    wire link_rx_duplicate;
    reg [4:0] seen_link_tx_state = 5'b0;
    reg [2:0] seen_link_rx_state = 3'b0;
    ot_stage_link_endpoint #(.FLIT_W(32),.MAX_FLITS(4),.SEQ_W(8),
                             .RETRY_MAX(2),.ACK_TIMEOUT(32)) link_dut (
        .clk(clk), .rst_n(rst_n), .tx_in_valid(link_tx_valid),
        .tx_in_ready(link_tx_ready), .tx_in_flit(link_tx_flit),
        .tx_in_last(link_tx_last), .tx_in_packet_seq(link_tx_seq),
        .tx_remote_credit(1'b1), .tx_link_valid(link_wire_valid),
        .tx_link_ready(link_wire_ready), .tx_link_flit(link_wire_flit),
        .tx_link_flit_crc(link_wire_flit_crc),
        .tx_link_packet_crc(link_wire_packet_crc), .tx_link_last(link_wire_last),
        .tx_link_packet_seq(link_wire_seq), .tx_ack_valid(link_ack_valid),
        .tx_ack_seq(link_ack_seq), .tx_ack_ok(link_ack_ok),
        .rx_link_valid(link_wire_valid), .rx_link_ready(link_wire_ready),
        .rx_link_flit(link_wire_flit), .rx_link_flit_crc(link_wire_flit_crc),
        .rx_link_packet_crc(link_wire_packet_crc), .rx_link_last(link_wire_last),
        .rx_link_packet_seq(link_wire_seq), .rx_out_valid(link_rx_valid),
        .rx_out_ready(link_rx_ready), .rx_out_flit(link_rx_flit),
        .rx_out_last(link_rx_last), .rx_out_packet_seq(link_rx_seq),
        .rx_out_poison(link_rx_poison), .rx_ack_valid(link_ack_valid),
        .rx_ack_seq(link_ack_seq), .rx_ack_ok(link_ack_ok), .tx_busy(link_busy),
        .tx_retry_count(link_retry_count), .tx_credit_consumed(link_credit_consumed),
        .tx_timeout(link_timeout), .tx_error(link_tx_error),
        .rx_protocol_error(link_rx_error), .rx_duplicate_packet(link_rx_duplicate));

    // A second TX instance exposes the architectural abort input that the
    // loopback endpoint intentionally ties low.  It is used only to close the
    // terminal ST_ABORT state; normal packet states remain checked end to end.
    reg abort_tx_in_valid = 1'b0;
    wire abort_tx_in_ready;
    reg [31:0] abort_tx_flit = 32'b0;
    reg abort_tx_abort = 1'b0;
    wire abort_tx_error;
    ot_stage_link_tx #(.FLIT_W(32),.MAX_FLITS(4),.SEQ_W(8),
                       .RETRY_MAX(2),.ACK_TIMEOUT(8)) abort_tx_dut (
        .clk(clk),.rst_n(rst_n),.in_valid(abort_tx_in_valid),
        .in_ready(abort_tx_in_ready),.in_flit(abort_tx_flit),.in_last(1'b0),
        .in_packet_seq(8'hf3),.remote_credit(1'b1),.credit_consumed(),
        .link_valid(),.link_ready(1'b0),.link_flit(),.link_flit_crc(),
        .link_packet_crc(),.link_last(),.link_packet_seq(),.ack_valid(1'b0),
        .ack_seq(8'b0),.ack_ok(1'b0),.abort(abort_tx_abort),.busy(),
        .retry_count(),.timeout(),.error(abort_tx_error));

    always @(posedge clk) begin
        case (link_dut.tx.state)
            3'd0: seen_link_tx_state[0] <= 1'b1;
            3'd1: seen_link_tx_state[1] <= 1'b1;
            3'd2: seen_link_tx_state[2] <= 1'b1;
            3'd3: seen_link_tx_state[3] <= 1'b1;
            3'd4: seen_link_tx_state[4] <= 1'b1;
            default: seen_link_tx_state <= seen_link_tx_state;
        endcase
    end

    always @(posedge clk) begin
        case (abort_tx_dut.state)
            3'd0: seen_link_tx_state[0] <= 1'b1;
            3'd1: seen_link_tx_state[1] <= 1'b1;
            3'd2: seen_link_tx_state[2] <= 1'b1;
            3'd3: seen_link_tx_state[3] <= 1'b1;
            3'd4: seen_link_tx_state[4] <= 1'b1;
            default: seen_link_tx_state <= seen_link_tx_state;
        endcase
    end

    always @(posedge clk) begin
        case (link_dut.rx.state)
            2'd0: seen_link_rx_state[0] <= 1'b1;
            2'd1: seen_link_rx_state[1] <= 1'b1;
            2'd2: seen_link_rx_state[2] <= 1'b1;
            default: seen_link_rx_state <= seen_link_rx_state;
        endcase
    end

    task automatic link_send_flit;
        input [31:0] data;
        input last;
        input [7:0] seq_value;
        integer wait_cycles;
        begin
            @(negedge clk);
            wait_cycles = 0;
            while (!link_tx_ready && wait_cycles < 200) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!link_tx_ready)
                $fatal(1,"link TX ready timeout tx_state=%0d rx_state=%0d",
                       link_dut.tx.state,link_dut.rx.state);
            link_tx_flit = data;
            link_tx_last = last;
            link_tx_seq = seq_value;
            link_tx_valid = 1'b1;
            @(negedge clk);
            link_tx_valid = 1'b0;
            link_tx_last = 1'b0;
        end
    endtask

    task automatic link_expect_flit;
        input [31:0] expected_data;
        input expected_last;
        input [7:0] expected_seq;
        integer wait_cycles;
        begin
            wait_cycles = 0;
            while (!link_rx_valid && wait_cycles < 200) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!link_rx_valid)
                $fatal(1,"link RX valid timeout tx_state=%0d rx_state=%0d tx_seq=%0h expected=%0h retry=%0d tx_error=%0b rx_error=%0b",
                       link_dut.tx.state,link_dut.rx.state,link_dut.tx.packet_seq,
                       expected_seq,link_retry_count,link_tx_error,link_rx_error);
            require_true(link_rx_flit == expected_data,"link endpoint data preservation");
            require_true(link_rx_last == expected_last,"link endpoint last preservation");
            require_true(link_rx_seq == expected_seq,"link endpoint sequence preservation");
            require_true(!link_rx_poison,"clean loopback packet poisoned");
            link_rx_ready = 1'b1;
            @(negedge clk);
            link_rx_ready = 1'b0;
        end
    endtask

    task automatic test_link_endpoint;
        reg [31:0] first_flit;
        reg [31:0] second_flit;
        reg [31:0] held_flit;
        reg [31:0] packet_flits [0:3];
        integer flit_index;
        integer packet_length;
        begin
            first_flit = 32'h0123_4567;
            second_flit = 32'h89ab_cdef;
            link_send_flit(first_flit,1'b0,8'h01);
            link_send_flit(second_flit,1'b1,8'h01);
            wait (link_rx_valid);
            held_flit = link_rx_flit;
            repeat (4) begin
                @(negedge clk);
                require_true(link_rx_valid && link_rx_flit == held_flit,
                             "link endpoint output stall stability");
            end
            link_expect_flit(first_flit,1'b0,8'h01);
            link_expect_flit(second_flit,1'b1,8'h01);
            pass_bin("COV-UNIT-LINK-ENDPOINT-MULTIFLIT",!link_tx_error && !link_rx_error);

            for (packet_index = 0; packet_index < 96; packet_index = packet_index + 1) begin
                packet_length = (packet_index % 4) + 1;
                for (flit_index = 0; flit_index < packet_length;
                     flit_index = flit_index + 1) begin
                    packet_flits[flit_index] = random32();
                    link_send_flit(packet_flits[flit_index],
                                   flit_index == packet_length-1,
                                   packet_index[7:0] + 8'h02);
                end
                if (packet_index[0])
                    repeat (2) @(negedge clk);
                for (flit_index = 0; flit_index < packet_length;
                     flit_index = flit_index + 1)
                    link_expect_flit(packet_flits[flit_index],
                                     flit_index == packet_length-1,
                                     packet_index[7:0] + 8'h02);
                if ((packet_index & 7) == 7)
                    $display("LINK_PROGRESS packets=%0d",packet_index+1);
            end
            pass_bin("COV-UNIT-LINK-ENDPOINT-RANDOM",
                     !link_timeout && !link_tx_error && !link_rx_error &&
                     !link_rx_duplicate && link_retry_count == 0);
        end
    endtask

    task automatic test_link_fsm_states;
        begin
            while (!abort_tx_in_ready)
                @(negedge clk);
            abort_tx_flit = random32();
            abort_tx_in_valid = 1'b1;
            @(negedge clk);
            abort_tx_in_valid = 1'b0;
            while (abort_tx_dut.state != 3'd1)
                @(negedge clk);
            abort_tx_abort = 1'b1;
            @(negedge clk);
            abort_tx_abort = 1'b0;
            while (abort_tx_dut.state != 3'd0)
                @(negedge clk);
            require_true(abort_tx_error,"link TX abort state error indication");
            pass_bin("COV-FSM-LINK-TX-IDLE",seen_link_tx_state[0]);
            pass_bin("COV-FSM-LINK-TX-COLLECT",seen_link_tx_state[1]);
            pass_bin("COV-FSM-LINK-TX-SEND",seen_link_tx_state[2]);
            pass_bin("COV-FSM-LINK-TX-WAIT-ACK",seen_link_tx_state[3]);
            pass_bin("COV-FSM-LINK-TX-ABORT",seen_link_tx_state[4]);
            pass_bin("COV-FSM-LINK-RX-IDLE",seen_link_rx_state[0]);
            pass_bin("COV-FSM-LINK-RX-COLLECT",seen_link_rx_state[1]);
            pass_bin("COV-FSM-LINK-RX-DELIVER",seen_link_rx_state[2]);
        end
    endtask

    // ------------------------------------------------------------------
    // Complete target tile with deterministic behavioral ROM contents.
    reg tile_route_valid = 1'b0;
    wire tile_route_ready;
    reg [223:0] tile_route_record = 224'b0;
    reg tile_act_valid = 1'b0;
    wire tile_act_ready;
    reg [15:0] tile_act_payload = 16'b0;
    reg [1:0] tile_word_index = 2'b0;
    reg [15:0] tile_transaction = 16'b0;
    reg [7:0] tile_sequence = 8'b0;
    reg tile_last = 1'b0;
    reg tile_act_poison = 1'b0;
    wire tile_result_valid;
    reg tile_result_ready = 1'b0;
    wire signed [23:0] tile_result_sum;
    wire [15:0] tile_result_transaction;
    wire [7:0] tile_result_sequence;
    wire tile_result_last;
    wire tile_result_poison;
    wire [3:0] tile_result_status;
    wire tile_route_bad_crc;
    wire tile_route_bad_field;
    reg [7:0] tile_memory [0:15];
    ot_tile #(.NUM_EXPERTS(4),.TOP_K(2),.WORDS_PER_EXPERT(4),.LANES(2),
              .ACT_W(8),.WEIGHT_W(4),.ACC_W(24)) tile_dut (
        .clk(clk), .rst_n(rst_n), .route_valid(tile_route_valid),
        .route_ready(tile_route_ready), .route_record(tile_route_record),
        .act_valid(tile_act_valid), .act_ready(tile_act_ready),
        .act_payload(tile_act_payload), .act_word_index(tile_word_index),
        .act_transaction_id(tile_transaction), .act_sequence(tile_sequence),
        .act_last(tile_last), .act_poison(tile_act_poison),
        .result_valid(tile_result_valid), .result_ready(tile_result_ready),
        .result_sum(tile_result_sum), .result_transaction_id(tile_result_transaction),
        .result_sequence(tile_result_sequence), .result_last(tile_result_last),
        .result_poison(tile_result_poison), .result_status(tile_result_status),
        .route_bad_crc(tile_route_bad_crc), .route_bad_field(tile_route_bad_field));

    function automatic integer signed4;
        input [3:0] value;
        begin
            if (value[3])
                signed4 = -32'sd16 + $signed({28'b0,value});
            else
                signed4 = $signed({28'b0,value});
        end
    endfunction

    task automatic tile_issue;
        input [1:0] expert0;
        input [1:0] expert1;
        input [1:0] word_index;
        input [15:0] transaction;
        input [15:0] activation;
        input mismatch_transaction;
        input inject_poison;
        input stall_result;
        integer expected;
        integer activation0;
        integer activation1;
        reg [207:0] body;
        reg [31:0] random_word;
        reg [3:0] selected_mask;
        integer wait_cycles;
        begin
            body[31:0] = random32();
            body[63:32] = random32();
            body[95:64] = random32();
            body[127:96] = random32();
            body[159:128] = random32();
            body[191:160] = random32();
            random_word = random32();
            body[207:192] = random_word[15:0];
            body[9:0] = {8'b0,expert0};
            body[19:10] = {8'b0,expert1};
            body[175:160] = transaction;
            random_word = random32();
            body[183:176] = random_word[7:0];
            random_word = random32();
            body[190:184] = random_word[6:0];
            body[195:191] = 5'd2;
            body[207:200] = 8'b0;
            tile_route_record = {crc16_route(body),body};
            @(negedge clk);
            wait_cycles = 0;
            while (!tile_route_ready && wait_cycles < 200) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!tile_route_ready)
                $fatal(1,"tile route ready timeout active=%0b ctx_valid=%0b result_valid=%0b",
                       tile_dut.route_active,tile_dut.ctx_valid,tile_result_valid);
            tile_route_valid = 1'b1;
            @(negedge clk);
            tile_route_valid = 1'b0;

            wait_cycles = 0;
            while (!tile_act_ready && wait_cycles < 200) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!tile_act_ready)
                $fatal(1,"tile activation ready timeout active=%0b rom_valid=%0b result_valid=%0b",
                       tile_dut.route_active,tile_dut.rom_valid,tile_result_valid);
            tile_act_payload = activation;
            tile_word_index = word_index;
            tile_transaction = mismatch_transaction ? (transaction ^ 16'h8001) : transaction;
            random_word = random32();
            tile_sequence = random_word[7:0];
            tile_last = 1'b1;
            tile_act_poison = inject_poison;
            tile_act_valid = 1'b1;
            @(negedge clk);
            tile_act_valid = 1'b0;
            tile_last = 1'b0;
            tile_act_poison = 1'b0;

            wait_cycles = 0;
            while (!tile_result_valid && wait_cycles < 200) begin
                @(negedge clk);
                wait_cycles = wait_cycles + 1;
            end
            if (!tile_result_valid)
                $fatal(1,"tile result timeout active=%0b rom_valid=%0b dot_valid=%0b",
                       tile_dut.route_active,tile_dut.rom_valid,tile_dut.dot_valid);
            if (stall_result)
                repeat (3) begin
                    @(negedge clk);
                    require_true(tile_result_valid,"tile result lost under backpressure");
                end
            selected_mask = (4'b0001 << expert0) | (4'b0001 << expert1);
            activation0 = $signed({{24{activation[7]}},activation[7:0]});
            activation1 = $signed({{24{activation[15]}},activation[15:8]});
            expected = 0;
            if (selected_mask[0]) begin
                expected = expected + activation0*signed4(tile_memory[word_index*4+0][3:0]);
                expected = expected + activation1*signed4(tile_memory[word_index*4+0][7:4]);
            end
            if (selected_mask[1]) begin
                expected = expected + activation0*signed4(tile_memory[word_index*4+1][3:0]);
                expected = expected + activation1*signed4(tile_memory[word_index*4+1][7:4]);
            end
            if (selected_mask[2]) begin
                expected = expected + activation0*signed4(tile_memory[word_index*4+2][3:0]);
                expected = expected + activation1*signed4(tile_memory[word_index*4+2][7:4]);
            end
            if (selected_mask[3]) begin
                expected = expected + activation0*signed4(tile_memory[word_index*4+3][3:0]);
                expected = expected + activation1*signed4(tile_memory[word_index*4+3][7:4]);
            end
            require_true(tile_result_transaction == tile_transaction,"tile transaction alignment");
            require_true(tile_result_sequence == tile_sequence,"tile sequence alignment");
            require_true(tile_result_last,"tile terminal marker alignment");
            require_true(tile_result_poison == (inject_poison || mismatch_transaction),
                         "tile poison classification");
            if (inject_poison || mismatch_transaction)
                require_true(tile_result_sum == 0 && tile_result_status[3],"tile poison zeroing");
            else
                require_true(tile_result_sum == $signed(expected[23:0]),"tile numeric result");
            // Align ready to a falling edge so it is held across a complete
            // active clock edge even when result_valid rose just after one.
            @(negedge clk);
            tile_result_ready = 1'b1;
            @(negedge clk);
            tile_result_ready = 1'b0;
        end
    endtask

    task automatic test_tile;
        integer address;
        integer sample;
        reg [31:0] random_word;
        reg [31:0] activation_word;
        begin
            for (address = 0; address < 16; address = address + 1) begin
                random_word = random32();
                tile_memory[address] = random_word[7:0];
                tile_dut.rom.mem[address] = tile_memory[address];
            end
            for (sample = 0; sample < 128; sample = sample + 1) begin
                random_word = random32();
                activation_word = random32();
                tile_issue(random_word[1:0],random_word[3:2],random_word[5:4],
                           random_word[31:16],activation_word[15:0],
                           (sample % 17) == 0,(sample % 19) == 0,(sample % 7) == 0);
                if ((sample & 15) == 15)
                    $display("TILE_PROGRESS samples=%0d",sample+1);
            end
            pass_bin("COV-UNIT-TILE-RANDOM-BACKPRESSURE",failures == 0);
            pass_bin("COV-UNIT-TILE-POISON-BOUNDARY",!tile_route_bad_crc && !tile_route_bad_field);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        test_crc();
        test_formats();
        test_reduction();
        test_switch();
        test_link_endpoint();
        test_link_fsm_states();
        test_tile();

        if (failures == 0) begin
            $display("PASS: coverage units seed=0x4356554e checks=%0d",checks);
            $finish;
        end else begin
            $fatal(1,"coverage units failed: %0d failures in %0d checks",failures,checks);
        end
    end
endmodule
