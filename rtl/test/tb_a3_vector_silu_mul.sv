`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Block campaign for the Qwen SwiGLU gate, rtl/abi3/ot_a3_vector_silu_mul.sv.
//
// The expected words come from the independent scalar reference
// ``qwen3_silu_mul_bf16``, which composes one correctly rounded exponential,
// one binary32 add, one correctly rounded division, and two BF16 roundings in
// that order.  A datapath that gets the same answer with fewer roundings is
// wrong here, so the comparison is per word and not per norm.
//
// The refusal cases each poison one element of the same operand run, which is
// how the retired counts prove *where* the block stopped: an infinite gate is
// caught before that element's first multiply, a NaN up value likewise, and a
// gated product outside binary32 is caught after the first multiply of its
// element and before the second.
// ---------------------------------------------------------------------------
module tb_a3_vector_silu_mul;
    localparam integer CASE_COUNT = 5;
    localparam integer CASE_WORDS = 16;
    localparam integer ELEMENTS = 1217;
    localparam [31:0] SENTINEL = 32'hdead_beef;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] case_mem [0:CASE_COUNT*CASE_WORDS-1];
    reg [31:0] gate_mem [0:ELEMENTS-1];
    reg [31:0] up_mem [0:ELEMENTS-1];
    reg [31:0] expected_mem [0:ELEMENTS-1];
    reg [31:0] observed_mem [0:ELEMENTS-1];
    reg [31:0] gate_image [0:ELEMENTS-1];
    reg [31:0] up_image [0:ELEMENTS-1];

    reg [1023:0] cases_path;
    reg [1023:0] gate_path;
    reg [1023:0] up_path;
    reg [1023:0] expected_path;

    reg [31:0] cfg_count;
    wire        a_rd_en;
    wire [31:0] a_rd_addr;
    reg  [31:0] a_rd_data;
    wire        b_rd_en;
    wire [31:0] b_rd_addr;
    reg  [31:0] b_rd_data;
    wire        out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    wire        busy;
    wire        done;
    wire [7:0]  error_code;
    wire [31:0] out_count;
    wire [31:0] saturation_count;
    wire [31:0] activation_saturation_count;
    wire [31:0] work_count;

    integer case_index;
    integer word_index;
    integer checks;
    integer timeout_cycles;
    integer observed_writes;
    reg read_oob;
    reg write_oob;
    reg write_after_done;
    reg completion_seen;

    task automatic check_equal;
        input [1023:0] label;
        input [63:0] actual;
        input [63:0] expected;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                $display(
                    "FAIL case=%0d %0s actual=%0d expected=%0d",
                    case_index, label, actual, expected
                );
                $fatal(1);
            end
        end
    endtask

    ot_a3_vector_silu_mul dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_count(cfg_count),
        .cfg_gate_base(32'd0), .cfg_up_base(32'd0), .cfg_out_base(32'd0),
        .a_rd_en(a_rd_en), .a_rd_addr(a_rd_addr), .a_rd_data(a_rd_data),
        .b_rd_en(b_rd_en), .b_rd_addr(b_rd_addr), .b_rd_data(b_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .saturation_count(saturation_count),
        .activation_saturation_count(activation_saturation_count),
        .work_count(work_count)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_rd_data <= 32'd0;
            b_rd_data <= 32'd0;
            observed_writes <= 0;
            read_oob <= 1'b0;
            write_oob <= 1'b0;
            write_after_done <= 1'b0;
            completion_seen <= 1'b0;
        end else begin
            if (start) begin
                observed_writes <= 0;
                read_oob <= 1'b0;
                write_oob <= 1'b0;
                write_after_done <= 1'b0;
                completion_seen <= 1'b0;
            end
            if (a_rd_en) begin
                if (a_rd_addr < ELEMENTS)
                    a_rd_data <= gate_mem[a_rd_addr];
                else begin
                    a_rd_data <= 32'd0;
                    read_oob <= 1'b1;
                end
            end
            if (b_rd_en) begin
                if (b_rd_addr < ELEMENTS)
                    b_rd_data <= up_mem[b_rd_addr];
                else begin
                    b_rd_data <= 32'd0;
                    read_oob <= 1'b1;
                end
            end
            if (out_we) begin
                observed_writes <= observed_writes + 1;
                if (completion_seen)
                    write_after_done <= 1'b1;
                if (out_addr < ELEMENTS)
                    observed_mem[out_addr] <= out_data;
                else
                    write_oob <= 1'b1;
            end
            if (done)
                completion_seen <= 1'b1;
        end
    end

    initial begin
        checks = 0;
        cfg_count = 32'd0;
        if (!$value$plusargs("SILU_CASES=%s", cases_path) ||
            !$value$plusargs("SILU_GATE=%s", gate_path) ||
            !$value$plusargs("SILU_UP=%s", up_path) ||
            !$value$plusargs("SILU_EXPECTED=%s", expected_path)) begin
            $fatal(1, "missing ABI3 SiLU-multiply vector plusargs");
        end
        $readmemh(cases_path, case_mem);
        $readmemh(gate_path, gate_image);
        $readmemh(up_path, up_image);
        $readmemh(expected_path, expected_mem);
        $display("GEOMETRY cases=%0d elements=%0d", CASE_COUNT, ELEMENTS);

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        for (case_index = 0; case_index < CASE_COUNT;
             case_index = case_index + 1) begin
            for (word_index = 0; word_index < ELEMENTS;
                 word_index = word_index + 1) begin
                gate_mem[word_index] = gate_image[word_index];
                up_mem[word_index] = up_image[word_index];
                observed_mem[word_index] = SENTINEL;
            end
            if (case_mem[case_index*CASE_WORDS + 7] != 0)
                gate_mem[case_mem[case_index*CASE_WORDS + 11]] =
                    case_mem[case_index*CASE_WORDS + 8];
            if (case_mem[case_index*CASE_WORDS + 9] != 0)
                up_mem[case_mem[case_index*CASE_WORDS + 11]] =
                    case_mem[case_index*CASE_WORDS + 10];
            cfg_count = case_mem[case_index*CASE_WORDS + 0];

            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            timeout_cycles = 0;
            while (!done && timeout_cycles < 8000000) begin
                @(posedge clk);
                #1;
                timeout_cycles = timeout_cycles + 1;
            end
            if (!done)
                $fatal(1, "case %0d timed out", case_index);

            check_equal("error_code", error_code,
                        case_mem[case_index*CASE_WORDS + 1]);
            check_equal("out_count", out_count,
                        case_mem[case_index*CASE_WORDS + 2]);
            check_equal("observed_writes", observed_writes,
                        case_mem[case_index*CASE_WORDS + 2]);
            check_equal("work_count", work_count,
                        case_mem[case_index*CASE_WORDS + 3]);
            check_equal("saturations", saturation_count,
                        case_mem[case_index*CASE_WORDS + 4]);
            check_equal("activation_saturations", activation_saturation_count,
                        case_mem[case_index*CASE_WORDS + 5]);
            check_equal("read_oob", read_oob, 0);
            check_equal("write_oob", write_oob, 0);
            check_equal("write_after_done", write_after_done, 0);
            check_equal("busy", busy, 0);
            if (case_mem[case_index*CASE_WORDS + 6] != 0)
                for (word_index = 0; word_index < ELEMENTS;
                     word_index = word_index + 1)
                    check_equal("gated_word", observed_mem[word_index],
                                expected_mem[word_index]);
            $display(
                "CASE_SUMMARY index=%0d error=%0d out=%0d work=%0d saturations=%0d activation_saturations=%0d verification_cycles=%0d",
                case_index, error_code, out_count, work_count,
                saturation_count, activation_saturation_count, timeout_cycles
            );
            repeat (3) @(posedge clk);
        end
        $display(
            "PASS a3_vector_silu_mul cases=%0d elements=%0d checks=%0d",
            CASE_COUNT, ELEMENTS, checks
        );
        $finish;
    end
endmodule
