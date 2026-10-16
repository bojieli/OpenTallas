`timescale 1ns/1ps
// Q-TILE-REPACK (2026-10-15, owner 20:35: re-pack the 64-lane compute tile to ~60 % fill, KEEP 64 MAC lanes):
// qfd_tile_nk_rp1 = qfd_tile_nk (rtl/physical/qfd_tile_nk_slot.sv) with the ROM pair pipeline SOFT in the tile parent
// (RPH 1: one ot_qwen_rpair_logic per bank row, the same logic the hardened leaf ot_qwen_tile_rpair holds) and the 10
// ROM macros ot_rom_4096x266_m8 placed directly in the tile (u_tile.u_tile.g_col[p].g_bank[b].u_rom).  The closed rpair
// leaf boxed 2 macros + channels in 311 x 130 um each, capping the tile near 38 % fill; placing the macros directly lets
// two macro columns share channels.  Same die ports, same values on the same edges as qfd_tile_nk (RPH 1 == RPH 2 by
// construction, gated by the r5 rom_pipe exact bench); only the clock structure changes:
//   ck_rp0..4 : was the hard-child entry of rpair leaf b, now the standard-cell CTS root of soft bank row b (~4.4k
//               sinks each; one 22k-sink root on ck would break the 15k sinks/root rule)
//   ck_rom0..9: NEW, one RAW macro clock entry per ROM macro, index p*5 + b = g_col[p].g_bank[b].u_rom (the die delivers
//               phi - R_i at each entry, R_i = the entry wire to the Liberty clock pin)
// The tile glue and the face pin registers stay on the CTS root ck; ck_lsl0..7 / ck_node are unchanged hard-child entries.  On die adoption this body takes
// the die name qfd_tile_nk (no new die master).  Every input bit and every output bit is registered at the pin (owner
// 19:50 rule 1); tie_hi / tie_lo are strap constants (tie cells), not timing paths.
// OT_QFD_TILE_NK_RP1_MUT (bench only): go taken from the top bit of the tap (wrong field order).
module qfd_tile_nk_rp1 #(
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
    input wire ck_rp0,
    input wire ck_rp1,
    input wire ck_rp2,
    input wire ck_rp3,
    input wire ck_rp4,
    input wire ck_rom0,
    input wire ck_rom1,
    input wire ck_rom2,
    input wire ck_rom3,
    input wire ck_rom4,
    input wire ck_rom5,
    input wire ck_rom6,
    input wire ck_rom7,
    input wire ck_rom8,
    input wire ck_rom9,
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
    initial if (1 + IBW + 128 != 508) $fatal(1, "qfd_tile_nk_rp1: tap must be {xl 128, ib %0d, go 1} = 508 b", IBW);
`ifdef OT_QFD_TILE_NK_RP1_MUT
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
        .ck_rpair({ck_rp4,ck_rp3,ck_rp2,ck_rp1,ck_rp0}),   // RPH 1: CTS root of soft bank row b
        .ck_rom({ck_rom9,ck_rom8,ck_rom7,ck_rom6,ck_rom5,ck_rom4,ck_rom3,ck_rom2,ck_rom1,ck_rom0}),
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
