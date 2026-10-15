`timescale 1ns/1ps
// q14 r8 (2026-10-14): Qwen split COMPUTE die master qfd_tile_nk (x768) as real RTL under its die name (owner no-stub
// rule 10-14 08:05: every die instance binds to real RTL under its die name, every die net lands on a real RTL port of
// the right width).  Die ports per the compute-die lead (el1014-qwen-split-compute.log 11:51, C6/C7 die-bus audit):
//   tap[507:0]      in   corridor station tap (ot_qfd_xcst tap_d = {xo[127:0], t_q[IBW:0]}): [0] go, [379:1] ib (the
//                        379-b ME issue word), [507:380] xl (the tile's x window, 4 x 32 b)
//   tile_id[15:0]   in   strap = 16 * block + morton(c % 4, r % 4) (the reference ot_qwen_me_array_w12 tile index)
//   t_out[513:0]    out  {fault, valid, data[511:0]}  = {tile fault, t_vout, t_out}
//   n_a / n_b[513:0] in  tree legs {fault, valid, data}; the node takes valid from leg a (reference n_va = leg a valid)
//   n_y[513:0]      out  {fault, valid, data} = {registered OR of the leg faults + sticky leg-valid mismatch, n_vy, n_y}
//   ck, rst_n
// NO KV port (the split compute tile runs no attention: KV_SLICE 0, wsrc ops fault) and no tap ready (the die ties the
// station tap_r high).  The die pads every node's early leg, so legs arrive aligned: va != vb is an alignment FAULT
// (a misaligned leg faults instead of summing wrong data), held until reset.
// Body = ot_qwen_rom_tile_nk with the TP8 production configuration (GT 3072) of the r5 hardened tile (5 rpair leaves
// RPH 2 + node leaf NDH 1 + 8 lane-slice leaves HIER_HARD, ROM return relay RQR 1, TOREG / TIDR / LRR pin registers):
// the die instantiates masters without parameter overrides, so the defaults ARE the production configuration.
// OT_QFD_TILE_NK_MUT (bench only): go taken from the top bit of the tap (wrong field order).
module qfd_tile_nk #(
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
    parameter integer RPH = 2,
    parameter integer RQR = 1,
    parameter integer XTX = 2,
    parameter integer ANR = 1,
    parameter integer NDH = 1
) (
    input  wire          ck,
    input wire ck_rp0,
    input wire ck_rp1,
    input wire ck_rp2,
    input wire ck_rp3,
    input wire ck_rp4,
    input wire ck_lsl0,
    input wire ck_lsl1,
    input wire ck_lsl2,
    input wire ck_lsl3,
    input wire ck_lsl4,
    input wire ck_lsl5,
    input wire ck_lsl6,
    input wire ck_lsl7,
    input wire ck_node,

    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    // die contract v1.2 (compute lead 21:23 10-14): strap ties.  The die wires every tile_id strap bit to this
    // instance's own tie_hi / tie_lo (E face, adjacent to tile_id): no die-netlist literal (one_/zero_ POWER nets).
    output wire          tie_hi,
    output wire          tie_lo,
    input  wire [507:0]  tap,
    output wire [513:0]  t_out,
    input  wire [513:0]  n_a,
    input  wire [513:0]  n_b,
    output wire [513:0]  n_y
);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
`ifndef SYNTHESIS
    // Rehosting the tree must preserve both the constant mask identity and
    // the real static die strap. A wrong binding is a simulation error.
    always @(posedge ck) if(rst_n && ROM_TILE>=0 && tile_id!==16'(ROM_TILE))
        $fatal(1,"native tile mask identity differs from real tile_id strap");
`endif
    // One kept native-face register per input bit; reset only controls
    // metadata. The child clocks remain independent compensated entries.
    (* keep *) reg [507:0] tap_q;
    (* keep *) reg [15:0] tile_id_q;
    (* keep *) reg reset_q;
    always @(posedge ck) begin
        tap_q <= tap; tile_id_q <= tile_id; reset_q <= rst_n;
    end
    (* keep *) reg [513:0] n_a_q,n_b_q;
    always @(posedge ck) begin n_a_q<=n_a;n_b_q<=n_b;end
    localparam integer IBW = 3 * NW + 13 * 24 + 13;               // 379
    initial if (1 + IBW + 128 != 508) $fatal(1, "qfd_tile_nk: tap must be {xl 128, ib %0d, go 1} = 508 b", IBW);
`ifdef OT_QFD_TILE_NK_MUT
    wire           go = tap_q[507];
`else
    wire           go = tap_q[0];
`endif
    wire [IBW-1:0] ib = tap_q[IBW:1];
    wire [127:0]   xl = tap_q[507 -: 128];
    wire [511:0]   to, ny;
    wire           tv, nvy, tf;
    ot_qwen_rom_tile_nk #(
`ifndef SYNTHESIS
        .ROM_TILE(ROM_TILE),
`endif
        .CHILD_CLOCKS(1), .NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_VB(KV_VB), .KV_NH(KV_NH),
        .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .TREE_LAT(TREE_LAT), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX),
        .LRST(LRST), .ARPB(ARPB), .MPR(MPR), .HIER(HIER), .HIER_HARD(HIER_HARD), .TOREG(TOREG), .TIDR(TIDR), .LRR(LRR),
        .RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .NDH(NDH)) u_tile (
        .ck_rpair({ck_rp4,ck_rp3,ck_rp2,ck_rp1,ck_rp0}),
        .ck_lsl({ck_lsl7,ck_lsl6,ck_lsl5,ck_lsl4,ck_lsl3,ck_lsl2,ck_lsl1,ck_lsl0}),
        .ck_node(ck_node),
        .clk(ck), .rst_n(reset_q), .tile_id(tile_id_q), .ib_go(go), .ib(ib), .xl(xl), .t_out(to), .t_vout(tv),
        .n_a(n_a_q[511:0]), .n_b(n_b_q[511:0]), .n_va(n_a_q[512]), .n_y(ny), .n_vy(nvy), .fault(tf));
    (* keep *) reg [513:0] t_out_q;
    always @(posedge ck) begin
        t_out_q[511:0]<=to;
        t_out_q[513:512]<=reset_q ? {tf,tv} : 2'd0;
    end
    assign t_out=t_out_q;
    // tree fault: the legs' faults ORed up one register per node (the reference fab_fault = OR of every tile fault,
    // registered at the top), plus a sticky leg-alignment fault
    (* keep *) reg fy_q;
    reg mis_q;
    always @(posedge ck)
        if (!reset_q) begin fy_q <= 1'b0; mis_q <= 1'b0; end
        else begin
            mis_q <= mis_q | (n_a_q[512] ^ n_b_q[512]);
            fy_q  <= n_a_q[513] | n_b_q[513] | mis_q;
        end
    (* keep *) reg [513:0] n_y_q;
    always @(posedge ck) begin
        n_y_q[511:0]<=ny;
        n_y_q[513:512]<=reset_q ? {fy_q,nvy} : 2'd0;
    end
    assign n_y=n_y_q;
endmodule

// q14 r9 (2026-10-14): qfd_tile_nl = the NODE-LESS compute tile (die lead 17:19 port-bind table: the 48 block-last tiles,
// tile_id 16k+15, have no node role in the 16-leaf block tree, so qfd_tile_nk's n_a / n_b would be die ties and n_y
// unread).  Same body, outline, ROM leaves and tap / t_out faces as qfd_tile_nk; the node leaf is not instantiated
// (ot_qwen_rom_tile_w12 NODE 0: t_out via the TOREG pin registers instead of the node leaf's feed-through registers,
// same edge and value).  No n_* ports, so nothing is tied on the die.  OT_QFD_TILE_NL_MUT (bench only): go from tap[507].
module qfd_tile_nl #(
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
    parameter integer RPH = 2,
    parameter integer RQR = 1,
    parameter integer XTX = 2,
    parameter integer ANR = 1,
    parameter integer NDH = 1
) (
    input  wire          ck,
    input wire ck_rp0,
    input wire ck_rp1,
    input wire ck_rp2,
    input wire ck_rp3,
    input wire ck_rp4,
    input wire ck_lsl0,
    input wire ck_lsl1,
    input wire ck_lsl2,
    input wire ck_lsl3,
    input wire ck_lsl4,
    input wire ck_lsl5,
    input wire ck_lsl6,
    input wire ck_lsl7,

    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    // die contract v1.2 (compute lead 21:23 10-14): strap ties.  The die wires every tile_id strap bit to this
    // instance's own tie_hi / tie_lo (E face, adjacent to tile_id): no die-netlist literal (one_/zero_ POWER nets).
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
    // Rehosting the tree must preserve both the constant mask identity and
    // the real static die strap. A wrong binding is a simulation error.
    always @(posedge ck) if(rst_n && ROM_TILE>=0 && tile_id!==16'(ROM_TILE))
        $fatal(1,"native tile mask identity differs from real tile_id strap");
`endif
    // One kept native-face register per input bit; reset only controls
    // metadata. The child clocks remain independent compensated entries.
    (* keep *) reg [507:0] tap_q;
    (* keep *) reg [15:0] tile_id_q;
    (* keep *) reg reset_q;
    always @(posedge ck) begin
        tap_q <= tap; tile_id_q <= tile_id; reset_q <= rst_n;
    end
    localparam integer IBW = 3 * NW + 13 * 24 + 13;               // 379
    initial if (1 + IBW + 128 != 508) $fatal(1, "qfd_tile_nl: tap must be {xl 128, ib %0d, go 1} = 508 b", IBW);
`ifdef OT_QFD_TILE_NL_MUT
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
        .CHILD_CLOCKS(1), .NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_VB(KV_VB), .KV_NH(KV_NH),
        .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .TREE_LAT(TREE_LAT), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX),
        .LRST(LRST), .ARPB(ARPB), .MPR(MPR), .HIER(HIER), .HIER_HARD(HIER_HARD), .TOREG(TOREG), .TIDR(TIDR), .LRR(LRR),
        .RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .NDH(NDH), .NODE(0)) u_tile (
        .ck_rpair({ck_rp4,ck_rp3,ck_rp2,ck_rp1,ck_rp0}),
        .ck_lsl({ck_lsl7,ck_lsl6,ck_lsl5,ck_lsl4,ck_lsl3,ck_lsl2,ck_lsl1,ck_lsl0}),
        .ck_node(ck),
        .clk(ck), .rst_n(reset_q), .tile_id(tile_id_q), .ib_go(go), .ib(ib), .xl(xl), .t_out(to), .t_vout(tv),
        .n_a(512'd0), .n_b(512'd0), .n_va(1'b0), .n_y(), .n_vy(), .fault(tf));   // NODE 0: n_* not read / not driven
    (* keep *) reg [513:0] t_out_q;
    always @(posedge ck) begin
        t_out_q[511:0]<=to;
        t_out_q[513:512]<=reset_q ? {tf,tv} : 2'd0;
    end
    assign t_out=t_out_q;
endmodule
