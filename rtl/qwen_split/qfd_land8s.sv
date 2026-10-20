`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// QW-LANDW (2026-10-19, LEAD3-QW; Q.STA.LAND600.3 wide lanes): D8 hop-0 landing with SRAM RECORD storage.
// Same frame, ports, release landing, counters, meta / fault and mutant defines as ot_qfd_land8 (qfd_land8.sv); the
// data slots live in dual-clock 1R1W SRAM macros (ot_sram_1r1w2c_32x64_m1: write port on the ring write clock wck,
// registered read port on the receiving root ck) instead of flop banks (SAFE checklist 5: a slot set > ~2 kb goes to
// SRAM; the wide lanes 453 / 520 / 548 b are 3.6..4.4 kb per lane at D = 8 and are built as 3 slice tiles of <= 192 b,
// each slice tile = 3 macros on the 43.2-um lattice, so no tile needs a fill exception).
//
// Per 64-bit bank (ot_qfd_land8s_bank, kept hierarchy, one macro, NOT parameterised: no paramod rename can merge the
// replicated control flops back):
//   write: i -> a_q (pin register, wck) ; wp (binary slot pointer, its own en copy) -> wa_q ; wce_q (en copy)
//          macro write on the NEXT wck edge: word w(e) launched on source edge e is in a_q after edge e + 1 and in the
//          macro after edge e + 2, slot (e - G - 2) mod 8 (the ot_qfd_land8 slot map; the pointer copies clear and
//          release on the same edge as the meta region's one-hot select).
//   read : ra_q = (rc + 1 - K) mod 8 registered one edge early (= the meta region's rdsel) -> macro read (registered
//          read port) -> rd_out ; use_q = warm & |(rdsel & vld) (the land8 bubble / warm mask, two kept copies) ;
//          o <= use_q ? rd_out : 0 (output pin register).
//   No wclk -> rd_out arc exists in the macro: the write -> read age is guaranteed by the calendar (strap K), not by
//   STA, exactly as for the CDC FIFO class the macro was built for.  The masked bubble / valid path (vld on wck ->
//   use_q on ck) is the only timed crossing, under physical/qwen_fwd_lane/land8_clocks.tcl.
// CALENDAR (die strap; checked by tools/qwen_split/bench_land8w.sh --sram):
//   o after receiver edge t = w(t - L) for K = (L + G - R0 - 2) mod 16 (one more than the flop D8: the output register),
//   with the write -> read age at the macro (L - 3) T + phi in the D8 window [1.25 T, 4.125 T]; i.e. the SRAM record
//   costs +2 receiver edges against the flop D8 ring (+1 pin register before the macro write, +1 registered macro read
//   before the output register).  Output 0 until warm (K read edges after release, then one more edge), 0 for words of
//   no current source epoch.  Fault: the ot_qfd_land8 meta epoch check, unchanged.
// ICG = 0: no clock gate (fallback); calendar identical.
// ---------------------------------------------------------------------------------------------------------------------

(* keep_hierarchy = "yes" *)
module ot_qfd_land8s_bank (
    input  wire        wck,         // ring write clock (gated ck_s, or ck_s for ICG = 0)
    input  wire        ckw,         // ungated ck_s
    input  wire        en_s0,       // source-side first en stage
    input  wire [63:0] i,
    input  wire        ck,          // receiving root
    input  wire        rs0,         // receiver-side first reset stage
    input  wire [2:0]  rnext,       // (rc + 1 - K) mod 8
    input  wire [2:0]  rseed,       // (0 - K) mod 8
    input  wire        warm,        // top warm (state before the edge)
    input  wire [7:0]  rds,         // meta region registered one-hot read select
    input  wire [7:0]  vld,         // meta region slot valid (wck domain)
    output reg  [63:0] o
);
    // ---------------------------------------------------------------- write half (wck)
    (* keep = "true", dont_touch = "true" *) reg en_q;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_q = en_s0;
`else
    always @(posedge ckw or negedge en_s0)
        if (!en_s0) en_q <= 1'b0; else en_q <= 1'b1;
`endif
    (* keep = "true", dont_touch = "true" *) reg [2:0] wp;
    always @(posedge wck or negedge en_q)
        if (!en_q) wp <= 3'd0;
`ifdef OT_QFD_LAND8_MUT_WSEL
        else wp <= wp + 3'd2;                               // mutant: pointer skips a slot
`else
        else wp <= wp + 3'd1;
`endif
    (* keep = "true", dont_touch = "true" *) reg wce_q;
    always @(posedge wck or negedge en_q)
        if (!en_q) wce_q <= 1'b0; else wce_q <= 1'b1;
    reg [63:0] a_q;
    reg [2:0]  wa_q;
    always @(posedge wck) begin
        a_q  <= i;
        wa_q <= wp;
    end
    // ---------------------------------------------------------------- read half (ck)
    (* keep = "true", dont_touch = "true" *) reg rs1;
    always @(posedge ck or negedge rs0)
        if (!rs0) rs1 <= 1'b0; else rs1 <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg rce_q;
    always @(posedge ck or negedge rs0)
        if (!rs0) rce_q <= 1'b0; else rce_q <= rs1;
    (* keep = "true", dont_touch = "true" *) reg [2:0] ra_q;
    wire [2:0] ridx = rs1 ? rnext : rseed;
`ifdef OT_QFD_LAND8_MUT_RSEL
    always @(posedge ck) ra_q <= ridx + 3'd2;                  // mutant: read slot two late
`else
    always @(posedge ck) ra_q <= ridx;
`endif
    (* keep = "true", dont_touch = "true" *) reg use_lo, use_hi;
    wire use_n = warm & |(rds & vld);
    always @(posedge ck) begin use_lo <= use_n; use_hi <= use_n; end
    wire [63:0] rd;
    ot_sram_1r1w2c_32x64_m1 u_mem (
        .wclk(wck), .rclk(ck),
        .r_ce_in(rce_q), .r_addr_in({2'b00, ra_q}), .rd_out(rd),
        .w_ce_in(wce_q), .w_addr_in({2'b00, wa_q}), .wd_in(a_q), .w_mask_in({64{1'b1}}));
`ifdef OT_QFD_LAND8_MUT_NAIVE
    reg [63:0] i_d;
    always @(posedge ck) begin i_d <= i; o <= use_lo ? i_d : 64'd0; end   // mutant: retime only, no record store
`else
    always @(posedge ck) o <= {({32{use_hi}} & rd[63:32]), ({32{use_lo}} & rd[31:0])};
`endif
endmodule

module ot_qfd_land8s #(
    parameter integer W    = 192,    // 1 .. 192 (three 64-bit banks per slice tile)
    parameter integer ICG  = 1
) (
    input  wire         ck_s,
    input  wire         en,
    input  wire [W-1:0] i,
    input  wire         ck,
    input  wire         rs,
    input  wire [3:0]   k,
    output wire [W-1:0] o,
    output reg          fault
);
    localparam integer NB = (W + 63) / 64;
    // ---------------------------------------------------------------- source-side en landing (as ot_qfd_land8)
    (* keep = "true", dont_touch = "true" *) reg en_s0;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_s0 = en;
`else
    always @(posedge ck_s or negedge en)
        if (!en) en_s0 <= 1'b0; else en_s0 <= 1'b1;
`endif
    (* keep = "true", dont_touch = "true" *) reg en_icg;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_icg = en_s0;
`else
    always @(posedge ck_s or negedge en_s0)
        if (!en_s0) en_icg <= 1'b0; else en_icg <= 1'b1;
`endif
    wire wck;
    generate if (ICG != 0) begin : g_icg
        ot_qfd_land8_gate u_fwd0 (.ck(ck_s), .en(en_icg), .gclk(wck));
    end else begin : g_nogate
        assign wck = ck_s;
    end endgenerate
    (* keep = "true", dont_touch = "true" *) reg en_qm;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_qm = en_s0;
`else
    always @(posedge ck_s or negedge en_s0)
        if (!en_s0) en_qm <= 1'b0; else en_qm <= 1'b1;
`endif
    reg [3:0] wc;
    always @(posedge wck or negedge en_qm)
        if (!en_qm) wc <= 4'b0; else wc <= wc + 1'b1;
    // ---------------------------------------------------------------- receiver-side reset landing, counters
    (* keep = "true", dont_touch = "true" *) reg rs0, rs1;
    always @(posedge ck or negedge rs)
        if (!rs) rs0 <= 1'b0; else rs0 <= 1'b1;
    always @(posedge ck or negedge rs0)
        if (!rs0) rs1 <= 1'b0; else rs1 <= 1'b1;
    reg [3:0] k_q;
`ifdef OT_QFD_LAND8_MUT_K3
    always @(posedge ck) k_q <= {1'b0, k[2:0]};
`else
    always @(posedge ck) k_q <= k;
`endif
    reg [3:0] rc;
    reg warm;
    wire warm_next = warm | (rc == k_q - 1'b1);
    always @(posedge ck or negedge rs1)
        if (!rs1) begin rc <= 4'b0; warm <= 1'b0; end
        else begin rc <= rc + 1'b1; warm <= warm_next; end
`ifdef OT_QFD_LAND8_MUT_SEL
    wire [3:0] nxt = rc + 4'd2 - k_q;
    wire [3:0] seed = 4'd1 - k_q;
`else
    wire [3:0] nxt = rc + 4'd1 - k_q;
    wire [3:0] seed = 4'd0 - k_q;
`endif
    // ---------------------------------------------------------------- meta region (epochs, valid, read select)
    wire [7:0] vld_m, rds_m;
    wire [3:0] ep_o;
    ot_qfd_land8_region #(.W(4)) u_meta (
        .wck(wck), .ckw(ck_s), .en_s0(en_s0), .i(wc), .ck(ck), .rs0(rs0),
        .rnext(nxt[2:0]), .rseed(seed[2:0]), .warm_next(warm_next),
        .vld_o(vld_m), .rdsel_o(rds_m), .o(ep_o));
    reg [3:0] exp_d;
    reg chk_d;
    always @(posedge ck) begin exp_d <= rc - k_q; chk_d <= warm && |(rds_m & vld_m); end
    always @(posedge ck or negedge rs1)
        if (!rs1) fault <= 1'b0;
        else if (chk_d && ep_o != exp_d) fault <= 1'b1;
    // ---------------------------------------------------------------- SRAM record banks
    wire [NB*64-1:0] i_p = {{(NB*64-W){1'b0}}, i};
    wire [NB*64-1:0] o_p;
    assign o = o_p[W-1:0];
    genvar b;
    generate for (b = 0; b < NB; b = b + 1) begin : g_bank
        ot_qfd_land8s_bank u_bank (
            .wck(wck), .ckw(ck_s), .en_s0(en_s0), .i(i_p[b*64 +: 64]), .ck(ck), .rs0(rs0),
            .rnext(nxt[2:0]), .rseed(seed[2:0]), .warm(warm), .rds(rds_m), .vld(vld_m), .o(o_p[b*64 +: 64]));
    end endgenerate
`ifndef SYNTHESIS
    initial if (W < 1 || W > 192) $fatal(1, "ot_qfd_land8s: 1 <= W <= 192 per slice tile (3 x 64-bit SRAM banks)");
`endif
endmodule
`default_nettype wire
