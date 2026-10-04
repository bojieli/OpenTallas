`timescale 1ns/1ps
// Additive actual W12 tile wrapper; arithmetic/memory logic instantiated unchanged.
// Caller must delay x issue/top tags consistently with accepted transport latency.
// rst_n is cold POR ONLY in selected mode. Warm reset uses the explicit fence.
// instruction_retire is the identity-qualified real result/ACK owner retirement.
// This is source-ready, not a declaration that the full-system caller is installed.
module ot_qwen_w12_instruction_tile_adapter_r1 #(
    parameter integer ENABLE_TWO_BEAT = 0,
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer TG = 4,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer IREG = 1,
    // MEM_EXTRA = 1: every memory operand is captured at its source before use -- each ROM bank's
    // output at the macro pins (SS clk->q 739 ps leaves no room for the bank OR at 0.833 ns), the KV
    // slice word and the x line -- one cycle the engine's tags wait (ot_qwen_w12_matvec_part MEM_EXTRA)
    parameter integer MEM_EXTRA = 0,
    parameter integer NREG = 1,
    parameter integer KV_LOCAL = 1,
    parameter integer KV_AW = 7,          // local KV words: 2^KV_AW
    parameter integer KV_VB = 262144,     // first V word (4 heads x 65,536)
    parameter integer KV_HB = 16,         // words per head: 2^KV_HB
    parameter integer KV_NH = 4,          // KV heads per die
    parameter integer KV_SK = 7,          // scores split (log2)
    parameter integer KV_SV = 9,          // weighted-sum split (log2)
    parameter integer ACC_LAT = 5,        // lane accumulator FP32 add latency (ot_qwen_w12_matvec_part ACC_LAT)
    parameter integer FAST_ISSUE = 0,     // 1.2 GHz issue loop (ot_qwen_w12_matvec_part FAST_ISSUE)
    parameter integer KV_PREP = 0,        // KV-op offset pipeline cycles (ot_qwen_w12_matvec_part KV_PREP)
    parameter integer MUL_LAT = 5,        // lane BF16 product latency (ot_qwen_w12_matvec_part MUL_LAT)
    parameter integer TREE_LAT = 3        // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    // instruction broadcast (the i_* fields of ot_qwen_w12_matvec, packed as in ot_qwen_me_array_w12)
    input wire warm_request, warm_release, all_copy_drained,
    input wire tile_launch_ready, instruction_retire, transport_beat_ready,
    output wire ib_ready, warm_fence_done, instruction_debt,
    // Existing packed W12 caller interface.
    input  wire              ib_go,
    input  wire [3*NW+13*AW+13-1:0] ib,
    // x line: this tile's TG chunk elements
    input  wire [TG*32-1:0]  xl,
    // split tree
    output wire [W*32-1:0]   t_out,
    output wire              t_vout,
    input  wire [W*32-1:0]   n_a,
    input  wire [W*32-1:0]   n_b,
    input  wire              n_va,
    output wire [W*32-1:0]   n_y,
    output wire              n_vy,
    output wire              fault,
    // code ROM macro pins
    output wire [CODE_BANKS-1:0] rom_ce,
    output wire [11:0]       rom_addr,
    input  wire [2*CODE_BANKS*266-1:0] rom_rd,
    // KV slice macro pins (KV_LOCAL = 1)
    output wire              kvs_r_ce,
    output wire [KV_AW-1:0]  kvs_r_addr,
    input  wire [TG*W*8-1:0] kvs_rd,
    // global KV port (KV_LOCAL = 0)
    output wire              kv_re,
    output wire [TG*AW-1:0]  kv_addr,
    input  wire [TG*W*32-1:0] kv_q
);
    localparam integer IBW=3*NW+13*AW+13;
    wire local_valid,local_ready,transport_fault;
    wire [378:0] reconstructed;
    wire tile_fault;
    generate if(ENABLE_TWO_BEAT != 0) begin : g_selected
        initial if(NW!=18 || AW!=24) $fatal(1,"selected W12 transport requires NW18/AW24");
        ot_qwen_w12_instruction_transport_r1 #(.ENABLE_TWO_BEAT(1)) u_transport (
          .clk(clk),.cold_por_n(rst_n),.warm_request(warm_request),.warm_release(warm_release),
          .all_copy_drained(all_copy_drained),.in_valid(ib_go),.in_ready(ib_ready),.in_word(ib),
          .beat_ready(transport_beat_ready),.beat_valid(),.beat_last(),.beat_data(),
          .consumer_valid(local_valid),.consumer_ready(tile_launch_ready),.consumer_word(reconstructed),
          .consumer_retire(instruction_retire),.warm_fence_done(warm_fence_done),.fault(transport_fault),
          .accepted_debt(instruction_debt));
    end else begin : g_original
        assign local_valid=ib_go;assign reconstructed=379'(ib);assign ib_ready=1'b1;
        assign warm_fence_done=0;assign transport_fault=0;assign instruction_debt=0;
    end endgenerate
    wire launch_go=ENABLE_TWO_BEAT != 0 ? local_valid && tile_launch_ready:ib_go;
    wire [IBW-1:0] packed_ib=ENABLE_TWO_BEAT != 0 ? IBW'(reconstructed):ib;
    assign fault=tile_fault || transport_fault;
    ot_qwen_rom_tile_logic_w12 #(
      .W(W),
      .IL(IL),
      .AW(AW),
      .NW(NW),
      .GT(GT),
      .TG(TG),
      .SMIN(SMIN),
      .CODE_BANKS(CODE_BANKS),
      .IREG(IREG),
      .MEM_EXTRA(MEM_EXTRA),
      .NREG(NREG),
      .KV_LOCAL(KV_LOCAL),
      .KV_AW(KV_AW),
      .KV_VB(KV_VB),
      .KV_HB(KV_HB),
      .KV_NH(KV_NH),
      .KV_SK(KV_SK),
      .KV_SV(KV_SV),
      .ACC_LAT(ACC_LAT),
      .FAST_ISSUE(FAST_ISSUE),
      .KV_PREP(KV_PREP),
      .MUL_LAT(MUL_LAT),
      .TREE_LAT(TREE_LAT)) u_original_tile (
      .clk(clk),
      .rst_n(rst_n),
      .tile_id(tile_id),
      .ib_go(launch_go),
      .ib(packed_ib),
      .xl(xl),
      .t_out(t_out),
      .t_vout(t_vout),
      .n_a(n_a),
      .n_b(n_b),
      .n_va(n_va),
      .n_y(n_y),
      .n_vy(n_vy),
      .fault(tile_fault),
      .rom_ce(rom_ce),
      .rom_addr(rom_addr),
      .rom_rd(rom_rd),
      .kvs_r_ce(kvs_r_ce),
      .kvs_r_addr(kvs_r_addr),
      .kvs_rd(kvs_rd),
      .kv_re(kv_re),
      .kv_addr(kv_addr),
      .kv_q(kv_q));
endmodule
