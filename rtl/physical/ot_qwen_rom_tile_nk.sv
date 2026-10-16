`timescale 1ns/1ps
// el1011-q-tile 2026-10-11: the r22ko4 Qwen ROM die tile master qfd_tile_nk (die contract results/arch/hier_contract_1011/
// qwen_rom.json, delta D2): the W12 ROM tile (ot_qwen_rom_tile_w12, 10 code-ROM macros) WITHOUT the KV slice and WITHOUT the
// per-tile landing hop li -> lo (attention runs on the KV die's near-HBM row engines).  One hardened replicated cluster
// (x1536): 8 hardened lane-slice leaves (HIER_HARD) + ROM macros + the tile glue (ROM request / capture, engine control,
// tree node) as tile-level logic.  Every output is flop-launched (t_out / t_vout with TOREG, n_y / n_vy from the node's
// output stage, fault_q).
module ot_qwen_rom_tile_nk #(
`ifndef SYNTHESIS
    parameter integer ROM_TILE = -1, // constant die tile identity for released simulation masks
`endif
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer KV_VB = 262144,
    parameter integer KV_NH = 4,
    parameter integer MEM_EXTRA = 0,
    parameter integer ACC_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer ROM_PIPE = 0,       // ot_qwen_rom_tile_w12 ROM_PIPE / ROM_ARELAY / LRST (qwen-blocks 2026-10-07)
    parameter integer ROM_ARELAY = 1,
    parameter integer ROM_CAP2 = 0,       // ot_qwen_rom_tile_w12 ROM_CAP2 (safe-qwen S-A1)
    parameter integer ROM_CAPX = 0,       // ot_qwen_rom_tile_w12 ROM_CAPX (redesign-qwen)
    parameter integer LRST = 0,
    parameter integer ARPB = 0,
    parameter integer MPR = 0,
    parameter integer HIER = 0,
    parameter integer HIER_HARD = 0,
    // el1011-q-tile h3 (2026-10-11; the glue stays tile-level logic, GLUE PLACEMENT): TOREG = tile output pin registers
    // on t_out / t_vout (+1 cycle a tile->node hop), TIDR = registered tile_id strap, LRR = one reset relay flop per
    // hardened leaf
    parameter integer TOREG = 0,
    parameter integer TIDR = 0,
    parameter integer LRR = 0,
    parameter integer RPH = 0,            // q13 r5 leaf 1: 1 = ROM pair pipeline as ot_qwen_rpair_logic per bank (soft), 2 = hardened leaf ot_qwen_tile_rpair (owns its 2 macros)
    parameter integer RQR = 0,            // q14 r5-fp1: ROM return relay: 1 = one register per bank group (south / north) on the rows' relay words before the group OR (+1 cycle on the ROM data), and per-group copies of the rpair address / any seam (needs RPH)
    parameter integer XTX = 0,             // el1011-q-tile r3: registered transmit rungs per hardened leaf (matvec HIER_HARD; +XTX cycles)
    parameter integer ANR = 0,            // ot_qwen_rom_tile_w12 ANR (hardcore-1010 D)           // ot_qwen_rom_tile_w12 ARPB (qwen-1010/c)
    parameter integer BAW = 12,
    parameter integer NDH = 0,            // q13 spec r5 leaf 2: ot_qwen_rom_tile_w12 NDH / BMUT (hardened node leaf)
    parameter integer BMUT = 0,
    parameter integer CHILD_CLOCKS = 0,
    parameter integer NODE = 1            // q14 r9: 0 = node-less tile (ot_qwen_rom_tile_w12 NODE)
) (
    input wire [CODE_BANKS-1:0] ck_rpair,
    input wire [2*CODE_BANKS-1:0] ck_rom,     // Q-TILE-REPACK: raw ROM macro clock entries (CHILD_CLOCKS, RPH 1)
    input wire [7:0] ck_lsl,
    input wire ck_node,
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [3*NW+13*24+13-1:0] ib,
    input  wire [4*32-1:0]   xl,
    output wire [16*32-1:0]  t_out,
    output wire              t_vout,
    input  wire [16*32-1:0]  n_a,
    input  wire [16*32-1:0]  n_b,
    input  wire              n_va,
    output wire [16*32-1:0]  n_y,
    output wire              n_vy,
    output wire              fault
);
    wire tile_fault;
    ot_qwen_rom_tile_w12 #(
`ifndef SYNTHESIS
        .ROM_TILE(ROM_TILE),
`endif
        .CHILD_CLOCKS(CHILD_CLOCKS), .NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_VB(KV_VB), .KV_NH(KV_NH),
        .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .TREE_LAT(TREE_LAT), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX), .LRST(LRST), .ARPB(ARPB), .MPR(MPR), .HIER(HIER), .HIER_HARD(HIER_HARD), .TOREG(TOREG), .TIDR(TIDR), .LRR(LRR), .RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .BAW(BAW), .NDH(NDH), .NODE(NODE), .BMUT(BMUT), .KV_SLICE(0)) u_tile (
        .ck_rpair(ck_rpair), .ck_rom(ck_rom), .ck_lsl(ck_lsl), .ck_node(ck_node),
        .clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl), .t_out(t_out), .t_vout(t_vout),
        .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .fault(tile_fault),
        .kvw_ce(1'b0), .kvw_addr(7'd0), .kvw_data(512'd0), .kvw_mask(512'd0));
    (* keep *) reg fault_q;    // flop-launched output pin
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0; else fault_q <= tile_fault;
    assign fault = fault_q;
endmodule
