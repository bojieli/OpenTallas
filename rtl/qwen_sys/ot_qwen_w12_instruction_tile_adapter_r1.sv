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
`ifndef SYNTHESIS
    parameter integer ROM_TILE = -1, // constant die tile identity for released simulation masks
`endif
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
    // ROM_PIPE = 1 (needs MEM_EXTRA = 1; default 0 = byte-identical original): the 1.2 GHz macro read pipeline
    // (qwen-blocks 2026-10-07).  ROM clk->q is 739-834 ps SS, so the single-cycle ROM->capture path closes only with
    // the ROM clock pin landed EARLY by CTS (useful skew from the CTS-only view ot_rom_4096x266_m8_skew250); that costs
    // the request path the same, so
    //   ROM_ARELAY register stages of the request (ce decode + address; one kept copy per bank group: banks
    //     [0, SB) south, [SB, CODE_BANKS) north) feed the macros from beside them,
    //   the capture register sits at the macro pins with no enable (the macro holds its output when not read),
    //   + 1 stage: INT8 -> BF16 expansion and the group OR (masked by the held bank select) at the group,
    //   + 1 stage: a relay register, then the two-group OR into the engine's mq capture.
    // The KV slice request and its write port take the same ROM_ARELAY stages (read/write order unchanged) and its
    // captured word 2 more; x waits the same.  The engine sees MEM_EXTRA + ROM_ARELAY + 2 memory cycles.
    parameter integer ROM_PIPE = 0,
    parameter integer ROM_ARELAY = 1,
    parameter integer ROM_MUT = 0,        // bench negative control: 1 = the capture register's bank select one edge early
    // ROM_CAP2 = 1 (safe-qwen S-A1, 2026-10-08; needs ROM_PIPE; 0 = unchanged): one more register stage between the pin
    // capture (cap, placed at the macro pins by rom_cap_at_pins.tcl) and the INT8 -> BF16 expansion / group OR (cap2,
    // with its bank select sel_c2), so the cap -> BF16 / group-OR -> gs stage (the predicted next limiter) is a
    // register-to-register hop.  +1 memory cycle per matvec fill (RX = ROM_ARELAY + 2 + ROM_CAP2; KV and x follow RX).
    parameter integer ROM_CAP2 = 0,
    // ROM_CAPX = 1 (redesign-qwen 2026-10-09; needs ROM_CAP2 = 1; 0 = unchanged): cap2 registers the bank-select-masked
    // INT8 -> BF16 expansion of cap instead of a copy of cap, so cap -> cap2 carries the expansion logic (no zero-logic
    // flop-to-flop hop beside the macro cluster: the rp1pc CTS hold stall sat on cap -> cap2) and cap2 -> gs is only the
    // 5:1 group OR.  Same edge, same word, same latency as ROM_CAP2 = 1 (cap2 is 2x wider: BF16).
    parameter integer ROM_CAPX = 0,
    // ROM_CAPX = 2 (el1011-q-tile 2026-10-11; needs ROM_CAP2 = 1): the INT8 -> BF16 expansion in TWO register rungs
    // (fba TT -51: cap -> cap2x was 20 levels: negate + leading-one + shift + mask in one stage).  Rung A (cx1, beside
    // cap): sign, magnitude, leading-one position, masked nonzero; rung B (cap2x): normalising shift + exponent.
    // +1 memory cycle per matvec fill (RX + 1; KV and x follow RX).
    // BAW: bank address width (12: ot_rom_4096x266_m8 banks; 11: ot_rom_2048x266_m8 half-depth banks, SS clk->q
    // 604 ps, twice CODE_BANKS for the same words -- the single-cycle capture then closes with a balanced clock)
    parameter integer BAW = 12,
    // LRST = 1: lane / tree-level reset copies inside the engine (ot_qwen_w12_matvec_part LRST)
    parameter integer LRST = 0,
    // ARPB = 1 (qwen-1010/c 2026-10-10; needs ROM_PIPE; 0 = unchanged): the LAST request-relay stage keeps ONE address
    // register per bank (a kept leaf beside the bank's two macros, rom_addr_b) instead of one per bank group: the group
    // copy rq_ad_s drove 6 macro address pins across the macro cluster (rp1pcl-hm0 TT -84: 9 levels of buffers).  Same
    // edge, same value: 0 cycles.  rom_addr / rom_addr_n then come from banks 0 / SB.
    parameter integer ARPB = 0,
    // TMUT (bench mutants, 0 = none): 1 = bank 0's address copy one edge stale; 2 = one tree adder's reset copy never
    // released (LRST 3)
    // ANR = 1 (hardcore-1010 D, 2026-10-10; 0 = unchanged): every lane / tree / node FP32 adder as ot_hdc_fp32_add_lat_nr
    // (cut bundles reset only their valid bit; HSPLIT kept copy for the B2a pass-through).  Bit-identical, 0 cycles.
    parameter integer ANR = 0,
    // MPR = 1 (el1011-q-tile 2026-10-11; needs ROM_PIPE and ARPB; 0 = unchanged): the last request-relay stage as ONE kept
    // {ce, address} register PER MACRO (rom_req_m, 2 columns x CODE_BANKS), placed at that macro's pins (rom_cap_at_pins.tcl
    // OT_PREQ=1).  The per-bank copy drove its bank's macro in BOTH columns across the frame (fba TT -59: rom_ce -> ce_in
    // 10 levels).  rom_ce / rom_addr_b keep the same stream (bench ROM model); same edge, same value: 0 cycles.
    parameter integer MPR = 0,
    // HIER = NPL > 0 (el1011-q-tile): the engine's lanes + tree as hardened lane-slice leaves (ot_qwen_w12_matvec_part HIER)
    parameter integer HIER = 0,
    parameter integer HIER_HARD = 0,      // the slices as the hardened leaf ot_qwen_tile_lsl (round 2)
    // el1011-q-tile h3 (2026-10-11; the glue stays tile-level logic, GLUE PLACEMENT): TOREG = tile output pin registers
    // on t_out / t_vout (+1 cycle a tile->node hop), TIDR = registered tile_id strap, LRR = one reset relay flop per
    // hardened leaf
    parameter integer TOREG = 0,
    parameter integer TIDR = 0,
    parameter integer LRR = 0,
    parameter integer RPH = 0,            // q13 r5 leaf 1: 1 = ROM pair pipeline as ot_qwen_rpair_logic per bank (soft), 2 = hardened leaf ot_qwen_tile_rpair (owns its 2 macros)
    parameter integer RQR = 0,            // q14 r5-fp1: ROM return relay: 1 = one register per bank group (south / north) on the rows' relay words before the group OR (+1 cycle on the ROM data), and per-group copies of the rpair address / any seam (needs RPH)
    parameter integer XTX = 0,             // el1011-q-tile r3: registered transmit rungs per hardened leaf (matvec HIER_HARD; +XTX cycles)
    // TMUT 3 = column 1 / bank 0's MPR copy one edge stale
    parameter integer TMUT = 0,
    // q13 spec r5 leaf 2 (2026-10-13), pure re-hierarchy (same registers, same edges):
    //   NDH 1 = the upper tree node as the hardened leaf ot_qwen_tile_node (W 16, NREG 1, TREE_LAT 7, ANR 1); its fault
    //           pin is registered in the leaf (+1 cycle on the node fault flag only; data/valid unchanged).
    //   BMUT  = bench boundary mutants: 2 = the node leaf's a input with lanes 0 / 1 swapped; 3 = the leaf's t_d
    //           (t_out feed-through) input with lanes 0 / 1 swapped.
    //   q14: with NDH 1 the TOREG t_out / t_vout pin registers are the leaf's feed-through registers (needs TOREG 1).
    parameter integer NDH = 0,
    // q14 r9 (2026-10-14): NODE 0 = node-less tile (the block-last tile of a 16-leaf tree has no node role): no node
    //   logic at all, n_a / n_b / n_va unread, n_y / n_vy / node fault constant 0; t_out via the TOREG pin registers.
    parameter integer NODE = 1,
    parameter integer BMUT = 0,
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
    parameter integer TREE_LAT = 3,       // split-tree pair adder latency (ot_qwen_w12_matvec_part TREE_LAT)
    parameter integer GLUE_HARD = 0, // opt-in consumer hard operand and column RQR registers
    parameter integer LOCAL_ROOTS = 0, // opt-in localized soft roots, no data latency change
    parameter integer REGROOT = 0,     // Q-ROMPARENT 10-16 (RPH 3 only): ck_reg = {data E, data W, gn W, gs W} regional roots; 0 = ck_reg unused
    parameter integer CHILD_CLOCKS = 0
) (

    input wire warm_request, warm_release, all_copy_drained,
    input wire tile_launch_ready, instruction_retire, transport_beat_ready,
    output wire ib_ready, warm_fence_done, instruction_debt,
    input wire [CODE_BANKS-1:0] ck_rpair,
    input wire [CODE_BANKS-1:0] ck_pair1,
    input wire [1:0] ck_rqr,
    input wire [1:0] ck_rqre,
    input wire [7:0] ck_tx,
    input wire [3:0] ck_reg,

    input wire [7:0] ck_lsl,
    input wire ck_node,
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    // instruction broadcast (the i_* fields of ot_qwen_w12_matvec, packed as in ot_qwen_me_array_w12)
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
    output wire [11:0]       rom_addr_n,          // north banks' address (ROM_PIPE; else == rom_addr)
    output wire [CODE_BANKS*12-1:0] rom_addr_b,   // per-bank address (ARPB; else each bank's group address)
    output wire [2*CODE_BANKS*13-1:0] rom_req_m,  // MPR: per-macro {ce, addr[11:0]}, macro (column p, bank b) at p*CODE_BANKS+b
    input  wire [2*CODE_BANKS*266-1:0] rom_rd,
    // KV slice macro pins (KV_LOCAL = 1)
    output wire              kvs_r_ce,
    output wire [KV_AW-1:0]  kvs_r_addr,
    input  wire [TG*W*8-1:0] kvs_rd,
    // global KV port (KV_LOCAL = 0)
    output wire              kv_re,
    output wire [TG*AW-1:0]  kv_addr,
    input  wire [TG*W*32-1:0] kv_q,
    // QC-PG-5 ICG: the engine drained flag (u_me.idle, registered, 1 in reset) for the A0 tile-root clock-gate enable
    output wire              idle
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
`ifndef SYNTHESIS
      .ROM_TILE(ROM_TILE),
`endif
      .NW(NW),
      .GT(GT),
      .TG(TG),
      .SMIN(SMIN),
      .CODE_BANKS(CODE_BANKS),
      .IREG(IREG),
      .MEM_EXTRA(MEM_EXTRA),
      .ROM_PIPE(ROM_PIPE),
      .ROM_ARELAY(ROM_ARELAY),
      .ROM_MUT(ROM_MUT),
      .ROM_CAP2(ROM_CAP2),
      .ROM_CAPX(ROM_CAPX),
      .BAW(BAW),
      .LRST(LRST),
      .ARPB(ARPB),
      .ANR(ANR),
      .MPR(MPR),
      .HIER(HIER),
      .HIER_HARD(HIER_HARD),
      .TOREG(TOREG),
      .TIDR(TIDR),
      .LRR(LRR),
      .RPH(RPH),
      .RQR(RQR),
      .XTX(XTX),
      .TMUT(TMUT),
      .NDH(NDH),
      .NODE(NODE),
      .BMUT(BMUT),
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
      .TREE_LAT(TREE_LAT),
      .GLUE_HARD(GLUE_HARD),
      .LOCAL_ROOTS(LOCAL_ROOTS),
      .REGROOT(REGROOT),
      .CHILD_CLOCKS(CHILD_CLOCKS)) u_original_tile (
      .ck_rpair(ck_rpair),
      .ck_pair1(ck_pair1),
      .ck_rqr(ck_rqr),
      .ck_rqre(ck_rqre),
      .ck_tx(ck_tx),
      .ck_reg(ck_reg),
      .ck_lsl(ck_lsl),
      .ck_node(ck_node),
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
      .rom_addr_n(rom_addr_n),
      .rom_addr_b(rom_addr_b),
      .rom_req_m(rom_req_m),
      .rom_rd(rom_rd),
      .kvs_r_ce(kvs_r_ce),
      .kvs_r_addr(kvs_r_addr),
      .kvs_rd(kvs_rd),
      .kv_re(kv_re),
      .kv_addr(kv_addr),
      .kv_q(kv_q),
      .idle(idle));
endmodule
