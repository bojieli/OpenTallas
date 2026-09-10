`timescale 1ns/1ps
// Numeric proof for ot_a3_qwen_gqa at a declared attention geometry.
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
module tb_a3_qwen_gqa_geometry #(
    parameter integer QH  = 32,
    parameter integer KVH = 8,
    parameter integer HW  = 128,
    parameter [31:0]  SC  = 32'h3db5_0000,
    parameter integer CTX = 16
);
    localparam integer KVROW = KVH * HW;
    localparam integer QWORDS = QH * HW;
    localparam integer KEY_BASE = 32768;
    localparam integer VAL_BASE = 65536;
    localparam integer OUT_BASE = 98304;

    reg clk = 1'b0; always #5 clk = ~clk;
    reg rst_n = 1'b0, start = 1'b0;
    reg [31:0] mem [0:262143];

    wire req_valid, out_valid;
    wire [31:0] req_addr, out_addr, out_data;
    reg rsp_valid = 1'b0; reg [31:0] rsp_data = 0;
    wire busy, done, failed; wire [7:0] err;
    wire [31:0] reads, writes, smul, expc, vmul, sats;

    always @(posedge clk) begin
        rsp_valid <= req_valid;
        rsp_data  <= req_valid ? mem[req_addr[17:0]] : 32'd0;
        if (out_valid) mem[out_addr[17:0]] <= out_data;
    end

    ot_a3_qwen_gqa #(
        .MAX_CONTEXT(64), .QUERY_HEADS(QH), .KV_HEADS(KVH),
        .HEAD_WIDTH(HW), .SCALE_CODE(SC)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_context_length(CTX), .cfg_query_base(32'd0),
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
        for (g = 0; g < 262144; g = g + 1) mem[g] = 32'h0;
        $readmemh("q.hex", mem, 0, QWORDS-1);
        $readmemh("k.hex", mem, KEY_BASE, KEY_BASE + CTX*KVROW - 1);
        $readmemh("v.hex", mem, VAL_BASE, VAL_BASE + CTX*KVROW - 1);
        repeat (4) @(negedge clk); rst_n = 1'b1; repeat (4) @(negedge clk);
        start = 1'b1; @(negedge clk); start = 1'b0;
        g = 0;
        while (!done && g < 200000000) begin @(posedge clk); g = g + 1; end
        $display("GQA qh=%0d kvh=%0d hw=%0d ctx=%0d err=%0d failed=%0d reads=%0d writes=%0d smul=%0d vmul=%0d",
                 QH, KVH, HW, CTX, err, failed, reads, writes, smul, vmul);
        $writememh("o.hex", mem, OUT_BASE, OUT_BASE + QWORDS - 1);
        $finish;
    end
endmodule
