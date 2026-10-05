`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Block campaign for rtl/abi3/ot_a3_selection_token_append.sv.
//
// This engine decides whether a generation continues, so its interesting
// behaviour is entirely in its refusals and in one precedence.  Each row of
// the matrix is a different refusal -- a sampling policy, a request outside
// the immutable policy's ceiling, an EOS set larger than the frozen ABI bound,
// a token outside the vocabulary -- and "both stopped" is not the claim; the
// claim is that each stopped for the reason the golden model gives.
//
// The precedence case is the one that matters in a real session: a final token
// that is *also* the policy's EOS must report OFFICIAL_EOS, because the golden
// model returns on the EOS branch before it ever tests the length bound.
//
// Every refusal is also checked for silence: no ring write, and for a policy
// refusal not even a read of the token object.
// ---------------------------------------------------------------------------
module tb_a3_selection_token_append;
    localparam integer CASE_COUNT = 13;
    localparam integer CASE_WORDS = 32;
    localparam integer MAX_EOS_TOKENS = 8;
    localparam [31:0] SENTINEL = 32'hdead_beef;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] case_mem [0:CASE_COUNT*CASE_WORDS-1];
    // 512 characters, not 128: a 128-character register silently keeps
    // only the TAIL of a longer path, so $readmemh fails on a truncated
    // name and the run then reports a case mismatch or a timeout instead
    // of a load failure. The same fix ot_a3 operator-admission carries.
    reg [4095:0] cases_path;

    reg [31:0] token_word;
    reg [31:0] ring_word;

    reg        cfg_ring_bound;
    reg [7:0]  cfg_selection_mode;
    reg [15:0] cfg_eos_count;
    reg [31:0] cfg_policy_max_new_tokens;
    reg [31:0] cfg_vocabulary;
    reg [31:0] cfg_eos_token [0:MAX_EOS_TOKENS-1];
    reg [31:0] cfg_request_max_new_tokens;
    reg [31:0] cfg_generated_before;

    wire        a_rd_en;
    wire [31:0] a_rd_addr;
    reg  [31:0] a_rd_data;
    wire        out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    wire        busy;
    wire        done;
    wire [7:0]  error_code;
    wire        refusal_capability;
    wire [31:0] token;
    wire [7:0]  eos_reason;
    wire [31:0] appended_count;
    wire [31:0] out_count;

    integer case_index;
    integer slot_index;
    integer checks;
    integer timeout_cycles;
    integer observed_writes;
    integer observed_reads;

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

    ot_a3_selection_token_append dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_token_base(32'd0),
        .cfg_ring_bound(cfg_ring_bound),
        .cfg_out_base(32'd0),
        .cfg_selection_mode(cfg_selection_mode),
        .cfg_eos_count(cfg_eos_count),
        .cfg_policy_max_new_tokens(cfg_policy_max_new_tokens),
        .cfg_vocabulary(cfg_vocabulary),
        .cfg_eos_token_0(cfg_eos_token[0]),
        .cfg_eos_token_1(cfg_eos_token[1]),
        .cfg_eos_token_2(cfg_eos_token[2]),
        .cfg_eos_token_3(cfg_eos_token[3]),
        .cfg_eos_token_4(cfg_eos_token[4]),
        .cfg_eos_token_5(cfg_eos_token[5]),
        .cfg_eos_token_6(cfg_eos_token[6]),
        .cfg_eos_token_7(cfg_eos_token[7]),
        .cfg_request_max_new_tokens(cfg_request_max_new_tokens),
        .cfg_generated_before(cfg_generated_before),
        .a_rd_en(a_rd_en), .a_rd_addr(a_rd_addr), .a_rd_data(a_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .refusal_capability(refusal_capability),
        .token(token), .eos_reason(eos_reason),
        .appended_count(appended_count), .out_count(out_count)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_rd_data <= 32'd0;
            observed_writes <= 0;
            observed_reads <= 0;
        end else begin
            if (start) begin
                observed_writes <= 0;
                observed_reads <= 0;
            end
            if (a_rd_en) begin
                a_rd_data <= token_word;
                observed_reads <= observed_reads + 1;
            end
            if (out_we) begin
                observed_writes <= observed_writes + 1;
                ring_word <= out_data;
            end
        end
    end

    initial begin
        checks = 0;
        cfg_ring_bound = 1'b0;
        cfg_selection_mode = 8'd0;
        cfg_eos_count = 16'd0;
        cfg_policy_max_new_tokens = 32'd0;
        cfg_vocabulary = 32'd0;
        cfg_request_max_new_tokens = 32'd0;
        cfg_generated_before = 32'd0;
        token_word = 32'd0;
        ring_word = SENTINEL;
        for (slot_index = 0; slot_index < MAX_EOS_TOKENS;
             slot_index = slot_index + 1)
            cfg_eos_token[slot_index] = 32'hffff_ffff;

        if (!$value$plusargs("APPEND_CASES=%s", cases_path))
            $fatal(1, "missing ABI3 token-append vector plusarg");
        $readmemh(cases_path, case_mem);
        $display("GEOMETRY cases=%0d", CASE_COUNT);

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        for (case_index = 0; case_index < CASE_COUNT;
             case_index = case_index + 1) begin
            token_word = case_mem[case_index*CASE_WORDS + 0];
            cfg_ring_bound = case_mem[case_index*CASE_WORDS + 1][0];
            cfg_selection_mode = case_mem[case_index*CASE_WORDS + 2][7:0];
            cfg_eos_count = case_mem[case_index*CASE_WORDS + 3][15:0];
            cfg_policy_max_new_tokens = case_mem[case_index*CASE_WORDS + 4];
            cfg_vocabulary = case_mem[case_index*CASE_WORDS + 5];
            cfg_request_max_new_tokens = case_mem[case_index*CASE_WORDS + 6];
            cfg_generated_before = case_mem[case_index*CASE_WORDS + 7];
            for (slot_index = 0; slot_index < MAX_EOS_TOKENS;
                 slot_index = slot_index + 1)
                cfg_eos_token[slot_index] =
                    case_mem[case_index*CASE_WORDS + 16 + slot_index];
            ring_word = SENTINEL;

            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            timeout_cycles = 0;
            while (!done && timeout_cycles < 1000) begin
                @(posedge clk);
                #1;
                timeout_cycles = timeout_cycles + 1;
            end
            if (!done)
                $fatal(1, "case %0d timed out", case_index);

            check_equal("error_code", error_code,
                        case_mem[case_index*CASE_WORDS + 8]);
            check_equal("refusal_capability", refusal_capability,
                        case_mem[case_index*CASE_WORDS + 9]);
            check_equal("token", token, case_mem[case_index*CASE_WORDS + 10]);
            check_equal("eos_reason", eos_reason,
                        case_mem[case_index*CASE_WORDS + 11]);
            check_equal("out_count", out_count,
                        case_mem[case_index*CASE_WORDS + 12]);
            check_equal("observed_writes", observed_writes,
                        case_mem[case_index*CASE_WORDS + 12]);
            check_equal("appended_count", appended_count,
                        case_mem[case_index*CASE_WORDS + 13]);
            check_equal("busy", busy, 0);
            // A policy this device cannot honour must not cause a read of the
            // token object at all.  The vector states the expected read count
            // per case rather than deriving it from the trap class, because
            // this engine deliberately validates the whole policy record
            // before the read while the golden model validates the EOS-count
            // field after the append -- see the module header.
            check_equal("token_reads", observed_reads,
                        case_mem[case_index*CASE_WORDS + 14]);
            if (case_mem[case_index*CASE_WORDS + 12] != 0)
                check_equal("ring_word", ring_word,
                            case_mem[case_index*CASE_WORDS + 10]);
            else
                check_equal("ring_untouched", ring_word, SENTINEL);

            $display(
                "CASE_SUMMARY index=%0d error=%0d capability=%0d token=%0d eos=%0d out=%0d appended=%0d reads=%0d verification_cycles=%0d",
                case_index, error_code, refusal_capability, token, eos_reason,
                out_count, appended_count, observed_reads, timeout_cycles
            );
            repeat (3) @(posedge clk);
        end
        $display(
            "PASS a3_selection_token_append cases=%0d checks=%0d",
            CASE_COUNT, checks
        );
        $finish;
    end
endmodule
