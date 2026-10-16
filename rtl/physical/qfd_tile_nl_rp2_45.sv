// Q-TILE45 node-less twin (2026-10-15): qfd_tile_nl_rp2_45 = qfd_tile_nl (rtl/physical/qfd_tile_nk_slot.sv, NODE 0)
// with the qfd_tile_nk_rp2_45 re-pack: ROM macros in the tile parent (RPH 1), 41 independent compensated clock entries
// = the 45-entry nk treatment minus ck_node (no node leaf) and minus ck_fa0/ck_fa1/ck_fa3 (no n_a/n_b/n_y faces:
// a node-less tile has no tree-node ports, so those roots would have no sinks).  Same 457.92 x 820.8 a2 outline,
// same W/E t_out/tap/tie/tile_id/rst_n windows and the same clock entry pins as qfd_tile_nk_rp2_45_a2.
// Values and edges equal qfd_tile_nl / qfd_tile_nk t_out (TOREG register on ck instead of the node leaf's t_d
// feed-through: same edge and value), every input bit and output bit registered at its pin (face roots ck_fa2/ck_fa4).
// OT_QFD_TILE_NL_RP2_MUT (bench only): go taken from the top bit of the tap (wrong field order).
`timescale 1ns/1ps
module qfd_tile_nl_rp2_45 #(
`ifndef SYNTHESIS
    parameter integer ROM_TILE = -1, // constant die tile identity for released simulation masks
`endif
    parameter integer NW = 18,
    parameter integer GT = 3072,
    parameter integer SMIN = 7,
    parameter integer CODE_BANKS = 5,
    parameter integer KV_VB = 131072,
    parameter integer KV_NH = 2,
    parameter integer MEM_EXTRA = 1,
    parameter integer ACC_LAT = 7,
    parameter integer FAST_ISSUE = 1,
    parameter integer KV_PREP = 4,
    parameter integer MUL_LAT = 8,
    parameter integer TREE_LAT = 7,
    parameter integer ROM_PIPE = 1,
    parameter integer ROM_ARELAY = 2,
    parameter integer ROM_CAP2 = 1,
    parameter integer ROM_CAPX = 2,
    parameter integer LRST = 3,
    parameter integer ARPB = 1,
    parameter integer MPR = 1,
    parameter integer HIER = 2,
    parameter integer HIER_HARD = 1,
    parameter integer TOREG = 1,
    parameter integer TIDR = 1,
    parameter integer LRR = 1,
    parameter integer RPH = 1,
    parameter integer RQR = 1,
    parameter integer XTX = 2,
    parameter integer ANR = 1,
    parameter integer NDH = 1
) (
    input  wire          ck,
    input wire ck_rp0, input wire ck_rp1, input wire ck_rp2, input wire ck_rp3, input wire ck_rp4,
    input wire ck_rp5, input wire ck_rp6, input wire ck_rp7, input wire ck_rp8, input wire ck_rp9,
    input wire ck_rom0, input wire ck_rom1, input wire ck_rom2, input wire ck_rom3, input wire ck_rom4,
    input wire ck_rom5, input wire ck_rom6, input wire ck_rom7, input wire ck_rom8, input wire ck_rom9,
    input wire ck_lsl0, input wire ck_lsl1, input wire ck_lsl2, input wire ck_lsl3,
    input wire ck_lsl4, input wire ck_lsl5, input wire ck_lsl6, input wire ck_lsl7,
    input wire ck_tx0, input wire ck_tx1, input wire ck_tx2, input wire ck_tx3,
    input wire ck_tx4, input wire ck_tx5, input wire ck_tx6, input wire ck_tx7,
    input wire ck_rqr0, input wire ck_rqr1,
    input wire ck_fa2, input wire ck_fa4,
    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    output wire          tie_hi,
    output wire          tie_lo,
    input  wire [507:0]  tap,
    output wire [513:0]  t_out
);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
`ifndef SYNTHESIS
    always @(posedge ck) if(rst_n && ROM_TILE>=0 && tile_id!==16'(ROM_TILE))
        $fatal(1,"native tile mask identity differs from real tile_id strap");
`endif
    (* keep *) reg [507:0] tap_q;
    (* keep *) reg [15:0] tile_id_q;
    (* keep *) reg reset_q;
    always @(posedge ck_fa4) begin
        tap_q <= tap; tile_id_q <= tile_id; reset_q <= rst_n;
    end
    localparam integer IBW = 3 * NW + 13 * 24 + 13;               // 379
    initial if (1 + IBW + 128 != 508) $fatal(1, "qfd_tile_nl_rp2_45: tap must be {xl 128, ib %0d, go 1} = 508 b", IBW);
`ifdef OT_QFD_TILE_NL_RP2_MUT
    wire           go = tap_q[507];
`else
    wire           go = tap_q[0];
`endif
    wire [IBW-1:0] ib = tap_q[IBW:1];
    wire [127:0]   xl = tap_q[507 -: 128];
    wire [511:0]   to;
    wire           tv, tf;
    ot_qwen_rom_tile_nk #(
`ifndef SYNTHESIS
        .ROM_TILE(ROM_TILE),
`endif
        .LOCAL_ROOTS(1), .CHILD_CLOCKS(1), .NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_VB(KV_VB), .KV_NH(KV_NH),
        .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .TREE_LAT(TREE_LAT), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX),
        .LRST(LRST), .ARPB(ARPB), .MPR(MPR), .HIER(HIER), .HIER_HARD(HIER_HARD), .TOREG(TOREG), .TIDR(TIDR), .LRR(LRR),
        .RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .NDH(NDH), .NODE(0)) u_tile (
        .ck_pair1({ck_rp9,ck_rp8,ck_rp7,ck_rp6,ck_rp5}), .ck_rqr({ck_rqr1,ck_rqr0}),
        .ck_tx({ck_tx7,ck_tx6,ck_tx5,ck_tx4,ck_tx3,ck_tx2,ck_tx1,ck_tx0}),
        .ck_rpair({ck_rp4,ck_rp3,ck_rp2,ck_rp1,ck_rp0}),
        .ck_rom({ck_rom9,ck_rom8,ck_rom7,ck_rom6,ck_rom5,ck_rom4,ck_rom3,ck_rom2,ck_rom1,ck_rom0}),
        .ck_lsl({ck_lsl7,ck_lsl6,ck_lsl5,ck_lsl4,ck_lsl3,ck_lsl2,ck_lsl1,ck_lsl0}),
        .ck_node(ck),                                  // NODE 0: no node leaf, the entry has no sink
        .clk(ck), .rst_n(reset_q), .tile_id(tile_id_q), .ib_go(go), .ib(ib), .xl(xl), .t_out(to), .t_vout(tv),
        .n_a(512'd0), .n_b(512'd0), .n_va(1'b0), .n_y(), .n_vy(), .fault(tf));   // NODE 0: n_* not read / not driven
    (* keep *) reg [513:0] t_out_q;
    always @(posedge ck_fa2) begin
        t_out_q[511:0]<=to;
        t_out_q[513:512]<=reset_q ? {tf,tv} : 2'd0;
    end
    assign t_out=t_out_q;
endmodule
