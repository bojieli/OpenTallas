`timescale 1ns/1ps
// ot_a3_vector_mhc_pre_tile_scheduler, narrowed work product against the one it
// replaced, on the committed cases.
//
// The module's own campaign (tools/run_a3_mhc_pre_tile_rtl_campaign.py) regenerates
// its vectors from a deployment and is red at HEAD for an unrelated reason -- its
// builder refuses with "current descriptor 546 is not the qualified semantics of
// prior descriptor 545" -- so it cannot gate a change today.  The committed cases
// themselves are still there, and they are what a miter needs: 22 configurations,
// admitting and refusing, driven into BOTH modules at once with every output
// compared on every cycle.
//
// This is equivalence over those cases and the arithmetic bound is proved
// separately in tb_a3_tile_work_product_equiv.sv.
module tb_a3_mhc_pre_tile_equiv;
    parameter integer CASES = 22;
    parameter integer CONFIG_WORDS = 128;
    parameter integer CASE_WORDS = 144;

    reg [31:0] case_mem [0:CASES*CASE_WORDS-1];
    reg [1023:0] cases_path;
    reg clk = 0, rst_n = 0, start = 0, tile_ready = 1;
    reg [CONFIG_WORDS*32-1:0] config_words = 0;

    wire a_tile_valid, b_tile_valid, a_busy, b_busy, a_done, b_done;
    wire a_tile_last, b_tile_last;
    wire [1:0]  a_kind, b_kind;
    wire [31:0] a_tb, b_tb, a_fb, b_fb, a_kb, b_kb;
    wire [31:0] a_at, b_at, a_af, b_af, a_ak, b_ak, a_ors, b_ors;
    wire [63:0] a_work, b_work, a_ob, b_ob;
    wire [7:0]  a_err, b_err;
    wire [63:0] a_ptc, b_ptc, a_ctc, b_ctc, a_fma, b_fma, a_loc, b_loc;

    integer errors = 0, checks = 0, c, wi, base, cycles, tiles, admitted;

    ot_a3_vector_mhc_pre_tile_scheduler_ref #(.CONFIG_WORDS(CONFIG_WORDS)) ref_i (
        .clk(clk), .rst_n(rst_n), .start(start), .config_words(config_words),
        .tile_valid(a_tile_valid), .tile_ready(tile_ready), .tile_kind(a_kind),
        .tile_token_base(a_tb), .tile_field_base(a_fb), .tile_k_base(a_kb),
        .tile_active_tokens(a_at), .tile_active_fields(a_af), .tile_active_k(a_ak),
        .tile_logical_work(a_work), .tile_output_base(a_ob),
        .tile_output_row_stride(a_ors), .tile_last(a_tile_last),
        .busy(a_busy), .done(a_done), .error_code(a_err),
        .projection_tile_count(a_ptc), .commit_tile_count(a_ctc),
        .logical_fma_count(a_fma), .logical_output_count(a_loc));

    ot_a3_vector_mhc_pre_tile_scheduler #(.CONFIG_WORDS(CONFIG_WORDS)) new_i (
        .clk(clk), .rst_n(rst_n), .start(start), .config_words(config_words),
        .tile_valid(b_tile_valid), .tile_ready(tile_ready), .tile_kind(b_kind),
        .tile_token_base(b_tb), .tile_field_base(b_fb), .tile_k_base(b_kb),
        .tile_active_tokens(b_at), .tile_active_fields(b_af), .tile_active_k(b_ak),
        .tile_logical_work(b_work), .tile_output_base(b_ob),
        .tile_output_row_stride(b_ors), .tile_last(b_tile_last),
        .busy(b_busy), .done(b_done), .error_code(b_err),
        .projection_tile_count(b_ptc), .commit_tile_count(b_ctc),
        .logical_fma_count(b_fma), .logical_output_count(b_loc));

    always #1 clk = ~clk;

    task compare(input integer case_index); begin
        checks = checks + 1;
        if (a_tile_valid !== b_tile_valid || a_kind !== b_kind
            || a_tb !== b_tb || a_fb !== b_fb || a_kb !== b_kb
            || a_at !== b_at || a_af !== b_af || a_ak !== b_ak
            || a_work !== b_work || a_ob !== b_ob || a_ors !== b_ors
            || a_tile_last !== b_tile_last || a_busy !== b_busy || a_done !== b_done
            || a_err !== b_err || a_ptc !== b_ptc || a_ctc !== b_ctc
            || a_fma !== b_fma || a_loc !== b_loc) begin
            errors = errors + 1;
            if (errors <= 6)
                $display("FAIL case %0d cycle %0d: work %0d/%0d fma %0d/%0d loc %0d/%0d valid %b/%b err %0h/%0h",
                         case_index, cycles, a_work, b_work, a_fma, b_fma,
                         a_loc, b_loc, a_tile_valid, b_tile_valid, a_err, b_err);
        end
    end endtask

    initial begin
        if (!$value$plusargs("CASES=%s", cases_path))
            cases_path = "testdata/rtl/a3_mhc_pre_tiles/cases.hex";
        $readmemh(cases_path, case_mem);
        $display("  loaded: case_mem[0]=%h [1]=%h [55]=%h [128]=%h",
                 case_mem[0], case_mem[1], case_mem[55], case_mem[128]);

        for (c = 0; c < CASES; c = c + 1) begin
            rst_n = 0; start = 0;
            @(negedge clk); @(negedge clk); rst_n = 1; @(negedge clk);
            base = c * CASE_WORDS;
            for (wi = 0; wi < CONFIG_WORDS; wi = wi + 1)
                config_words[wi*32 +: 32] = case_mem[base + wi];
            @(negedge clk); start = 1; @(negedge clk); start = 0;
            cycles = 0; tiles = 0;
            while (!(a_done && b_done) && cycles < 200000) begin
                @(negedge clk);
                compare(c);
                if (a_tile_valid) tiles = tiles + 1;
                cycles = cycles + 1;
            end
            if (cycles >= 200000) begin
                $display("FAIL case %0d did not finish in %0d cycles (a_done=%b b_done=%b)",
                         c, cycles, a_done, b_done);
                errors = errors + 1;
            end
            compare(c);
            $display("  case %0d: %0d cycles, %0d tile beats, err %0h, fma %0d, out %0d",
                     c, cycles, tiles, a_err, a_fma, a_loc);
        end

        if (errors == 0)
            $display("PASS a3_mhc_pre_tile_equiv: %0d cycle comparisons over %0d committed cases, the narrowed work product and the 64-bit one agree on every output",
                     checks, CASES);
        else
            $display("FAIL a3_mhc_pre_tile_equiv: %0d of %0d comparisons differ", errors, checks);
        $finish;
    end
endmodule
