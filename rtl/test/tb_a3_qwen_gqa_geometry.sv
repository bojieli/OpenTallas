`timescale 1ns/1ps
// Numeric proof for ot_a3_qwen_gqa at a declared attention geometry and query
// span.
//
// Rung G1f's third blocker was that this engine "has no geometry input": its
// query-head count, KV-head count, head width and attention scale were
// localparams fixed at Qwen3-8B's 32/8/128, so at the reduced regression
// model's shape it still read a full-model attention row -- 135,168 operand
// words for one query row at context 16, 32x the reduced row.
//
// The geometry is now elaboration parameters, and this drives the engine over
// real operands at whichever geometry it is elaborated for so the caller can
// compare every output word against
// runtime/reference/tensor_accelerator_attention.gqa_causal_attention_bf16.
// Driven by tests/test_a3_qwen_gqa_geometry.py, which elaborates it twice: the
// shipped 32/8/128 as a positive control and the reduced 8/2/16.
//
// SCALE_CODE is passed in rather than derived here because it is part of the
// geometry: bf16(1/sqrt(HEAD_WIDTH)), 0x3db5 at 128 and 0x3e80 at 16.
//
// SPAN is the number of QUERY ROWS one launch retires: 1 is decode, and
// SPAN > 1 is the prefill capability, where query row i may attend only to
// context positions up to CTX-SPAN+i.  The same oracle covers both, because a
// span is a committed KV snapshot of CTX-SPAN rows plus a prepared append of
// SPAN rows, and the oracle masks key_index >= committed.length + i + 1.  The
// operand layout is derived from SPAN so that the query plane, the two KV
// planes and the result never overlap at any span.
module tb_a3_qwen_gqa_geometry #(
    parameter integer QH  = 32,
    parameter integer KVH = 8,
    parameter integer HW  = 128,
    parameter [31:0]  SC  = 32'h3db5_0000,
    parameter integer CTX = 16,
    parameter integer SPAN = 1,
    // Drive a DELIBERATELY wrong span configuration, to show that the new
    // bound and the new alignment rule are enforced rather than decorative:
    //   1  a span past the elaborated MAX_QUERY_SPAN,
    //   2  a first position one above the tail-aligned one,
    //   3  a first position one below it.
    // Each must refuse with ERR_CONFIG and perform no memory read and no write.
    parameter integer BAD = 0
);
    localparam integer KVROW = KVH * HW;
    localparam integer QWORDS = QH * HW;
    localparam integer SPAN_WORDS = SPAN * QWORDS;
    localparam integer KEY_BASE = SPAN_WORDS;
    localparam integer VAL_BASE = KEY_BASE + CTX * KVROW;
    localparam integer OUT_BASE = VAL_BASE + CTX * KVROW;
    localparam integer MEM_WORDS = OUT_BASE + SPAN_WORDS;
    // The absolute sequence position of query row 0: a causal span ends at the
    // end of its KV plane, so the first row sits CTX-SPAN into the sequence.
    localparam integer FIRST_POSITION = CTX - SPAN;
    localparam integer DRIVEN_SPAN = (BAD == 1) ? SPAN + 1 : SPAN;
    localparam integer DRIVEN_FIRST =
          (BAD == 2) ? FIRST_POSITION + 1
        : (BAD == 3) ? FIRST_POSITION - 1
        : FIRST_POSITION;

    reg clk = 1'b0; always #5 clk = ~clk;
    reg rst_n = 1'b0, start = 1'b0;
    reg [31:0] mem [0:MEM_WORDS-1];

    wire req_valid, out_valid;
    wire [31:0] req_addr, out_addr, out_data;
    reg rsp_valid = 1'b0; reg [31:0] rsp_data = 0;
    wire busy, done, failed; wire [7:0] err;
    wire [31:0] reads, writes, smul, expc, vmul, sats;

    always @(posedge clk) begin
        rsp_valid <= req_valid;
        rsp_data  <= req_valid ? mem[req_addr] : 32'd0;
        if (out_valid) mem[out_addr] <= out_data;
    end

    ot_a3_qwen_gqa #(
        .MAX_CONTEXT(64), .MAX_QUERY_SPAN(SPAN), .QUERY_HEADS(QH),
        .KV_HEADS(KVH), .HEAD_WIDTH(HW), .SCALE_CODE(SC)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_context_length(CTX), .cfg_query_span(DRIVEN_SPAN),
        .cfg_first_position(DRIVEN_FIRST), .cfg_query_base(32'd0),
        .cfg_key_base(KEY_BASE), .cfg_value_base(VAL_BASE),
        .cfg_output_base(OUT_BASE),
        .mem_req_valid(req_valid), .mem_req_ready(1'b1), .mem_req_addr(req_addr),
        .mem_rsp_valid(rsp_valid), .mem_rsp_data(rsp_data),
        .out_valid(out_valid), .out_ready(1'b1),
        .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .failed(failed), .error_code(err),
        .memory_read_count(reads), .output_write_count(writes),
        .score_multiply_count(smul), .exponential_count(expc),
        .value_multiply_count(vmul), .saturation_count(sats)
    );

    integer g;
    initial begin
        for (g = 0; g < MEM_WORDS; g = g + 1) mem[g] = 32'h0;
        $readmemh("q.hex", mem, 0, SPAN_WORDS-1);
        $readmemh("k.hex", mem, KEY_BASE, KEY_BASE + CTX*KVROW - 1);
        $readmemh("v.hex", mem, VAL_BASE, VAL_BASE + CTX*KVROW - 1);
        repeat (4) @(negedge clk); rst_n = 1'b1; repeat (4) @(negedge clk);
        start = 1'b1; @(negedge clk); start = 1'b0;
        g = 0;
        while (!done && g < 200000000) begin @(posedge clk); g = g + 1; end
        $display("GQA qh=%0d kvh=%0d hw=%0d ctx=%0d span=%0d first=%0d bad=%0d err=%0d failed=%0d reads=%0d writes=%0d smul=%0d vmul=%0d expc=%0d sats=%0d cycles=%0d",
                 QH, KVH, HW, CTX, DRIVEN_SPAN, DRIVEN_FIRST, BAD, err, failed,
                 reads, writes, smul, vmul, expc, sats, g);
        $writememh("o.hex", mem, OUT_BASE, OUT_BASE + SPAN_WORDS - 1);
        $finish;
    end
endmodule
