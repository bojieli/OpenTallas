`timescale 1ns/1ps
// el1011-q-tile 2026-10-13 (spec r5 item 3): the hardened KV + landing leaf of the W12 ROM tile (qfd_tile; absent in the
// NK tile variant).  A pure re-hierarchy of registers that sat in three modules of the flat tile, at the tile-die
// production parameters; no arithmetic and no latency differs from the KVH = 0 path:
//   ot_qwen_rom_tile_die        li -> li_q (W pin register) -> lo_q (E pin register) -> lo, the slot decode against the
//                               tile column strap, ot_qwen_kv_land_merge u_merge, the sticky land_fault register
//   ot_qwen_rom_tile_w12        kvw_*_q, g_kwv.u_kwv / u_kwd (the write port's ROM_ARELAY relay stages), the two
//                               g_kv[p].u_kv slice macros (ot_sram_1r1w_128x256_m1_r2c2)
//   ot_qwen_rom_tile_logic_w12  g_kv_local: the slice address map, g_kvrl (u_kvce / u_kvad), g_kvcap (kv_rd_q, cap,
//                               u_kvd)
// Seam (every pin a flop on the leaf side except kv_a, see below):
//   li        -> li_q                        lo       <- lo_q
//   kv_re     -> u_kvce stage 1              kv_q     <- u_kvd last stage (kvs_rd_m; the e4m3 -> f32 expansion to
//   kv_a      -> address map -> u_kvad 1        me_kv_q is combinational wiring and stays in the parent)
//   tile_id6  -> tid_q (static strap)        land_fault <- its register
// kv_a (= me_kv_addr[AW-1:0], a flop output of the parent's matvec) crosses the seam in front of the address map: the
// map is the logic between the parent's flop and u_kvad's first stage, exactly as in the flat tile.  The strap register
// tid_q is the leaf's copy of the TIDR idea (a strap is constant from power-up: one more register changes no data
// cycle); it removes the pin -> compare -> merge path.
// The parameter-free top carries the fixed name the parent instantiates (Yosys 0.68 re-derivation assert, see
// ot_qwen_tile_lsl).  MUT (bench only): 1 = the slice read address enters u_kvad one edge late.
module ot_qwen_tile_kvl_core #(
    parameter integer GT = 6144,
    parameter integer KV_VB = 131072,
    parameter integer KV_NH = 2,
    parameter integer KV_AW = 7,
    parameter integer KV_HB = 16,
    parameter integer KV_SK = 7,
    parameter integer KV_SV = 9,
    parameter integer AW = 24,
    parameter integer TG = 4,
    parameter integer W = 16,
    parameter integer ROM_ARELAY = 2,
    parameter integer RX = 6,
    parameter integer KVL = 984,
    parameter integer LSLOTS = 3,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [5:0]        tile_id6,
    input  wire [KVL-1:0]    li,
    output wire [KVL-1:0]    lo,
    input  wire              kv_re,
    input  wire [AW-1:0]     kv_a,
    output wire [TG*W*8-1:0] kv_q,
    output wire              land_fault
);
    localparam integer SLW = 281;
    (* keep *) reg [5:0] tid_q;
    always @(posedge clk) tid_q <= tile_id6;
    // ---- landing hop: W pin register, E pin register (ot_qwen_rom_tile_die) ----------------------------------------
    (* keep *) reg [KVL-1:0] li_q;
    (* keep *) reg [KVL-1:0] lo_q;
    always @(posedge clk) begin li_q <= li; lo_q <= li_q; end
    assign lo = lo_q;
    // ---- slot decode -----------------------------------------------------------------------------------------------
    wire [LSLOTS-1:0]     s_v;
    wire [LSLOTS*7-1:0]   s_port, s_loc;
    wire [LSLOTS-1:0]     s_isk, s_ktail;
    wire [LSLOTS*2-1:0]   s_sel;
    wire [LSLOTS*256-1:0] s_beat;
    genvar k;
    generate for (k = 0; k < LSLOTS; k = k + 1) begin : g_slot
        wire [SLW-1:0] w = li_q[k*SLW +: SLW];
        assign s_beat[k*256 +: 256] = w[255:0];
        assign s_sel[k*2 +: 2]      = w[257:256];
        assign s_ktail[k]           = w[258];
        assign s_isk[k]             = w[259];
        assign s_loc[k*7 +: 7]      = w[266:260];
        assign s_port[k*7 +: 7]     = w[273:267];
        assign s_v[k]               = w[274] && (w[280:275] == tid_q);
    end endgenerate
    wire [6:0]   rr_n    = li_q[LSLOTS*SLW +: 7];
    wire [127:0] tail_lm = li_q[LSLOTS*SLW + 7 +: 128];
    wire [LSLOTS-1:0] s_grant;
    wire         kvw_ce;
    wire [6:0]   kvw_addr;
    wire [511:0] kvw_data, kvw_mask;
    ot_qwen_kv_land_merge #(.NSRC(LSLOTS), .PW(7), .LW(7), .DW(512)) u_merge (
        .clk(clk), .rst_n(rst_n), .rr_n(rr_n), .s_v(s_v), .s_port(s_port), .s_loc(s_loc), .s_isk(s_isk),
        .s_ktail(s_ktail), .s_sel(s_sel), .s_beat(s_beat), .tail_lm(tail_lm), .s_grant(s_grant),
        .tok_v(1'b0), .tok_loc(7'd0), .tok_data(512'd0), .tok_mask(512'd0),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask));
    reg land_fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) land_fault_q <= 1'b0;
        else land_fault_q <= land_fault_q | (|(s_v & ~s_grant));
    assign land_fault = land_fault_q;
    // ---- slice write port (ot_qwen_rom_tile_w12) -------------------------------------------------------------------
    reg        kvw_ce_q;
    reg [6:0]  kvw_addr_q;
    reg [511:0] kvw_data_q, kvw_mask_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kvw_ce_q <= 1'b0;
        else kvw_ce_q <= kvw_ce;
    end
    always @(posedge clk) begin kvw_addr_q <= kvw_addr; kvw_data_q <= kvw_data; kvw_mask_q <= kvw_mask; end
    localparam integer KWD = ROM_ARELAY;
    wire        kvw_ce_r;
    wire [KWD+1:0] kvw_l;
    ot_hdc_vline #(.D(KWD + 1)) u_kwv (.clk(clk), .rst_n(rst_n), .v(kvw_ce_q), .vd(kvw_l));
    assign kvw_ce_r = kvw_l[KWD];
    wire [6:0]  kvw_addr_r;
    wire [511:0] kvw_data_r, kvw_mask_r;
    ot_hdc_delay #(.W(7 + 1024), .D(KWD)) u_kwd (.clk(clk), .rst_n(rst_n), .d({kvw_addr_q, kvw_data_q, kvw_mask_q}),
        .q({kvw_addr_r, kvw_data_r, kvw_mask_r}));
    wire              kvs_r_ce;
    wire [KV_AW-1:0]  kvs_r_addr;
    wire [511:0]      kvs_rd;
    genvar p;
    generate
        for (p = 0; p < 2; p = p + 1) begin : g_kv
            ot_sram_1r1w_128x256_m1_r2c2 u_kv (
                .clk(clk), .r_ce_in(kvs_r_ce), .r_addr_in(kvs_r_addr), .rd_out(kvs_rd[256*p +: 256]),
                .w_ce_in(kvw_ce_r), .w_addr_in(kvw_addr_r), .wd_in(kvw_data_r[256*p +: 256]),
                .w_mask_in(kvw_mask_r[256*p +: 256]),
                .rr_en(2'b0), .rr_addr(14'd0), .cr_en(2'b0), .cr_sel(16'd0));
        end
    endgenerate
    // ---- slice read port (ot_qwen_rom_tile_logic_w12 g_kv_local) ---------------------------------------------------
    localparam [KV_AW-1:0] PRK = GT >> KV_SK;
    localparam integer KV_PT = 1 << (KV_HB - 7);
    localparam integer KV_KL = ((KV_PT + (GT >> KV_SK) - 1) / (GT >> KV_SK)) * KV_NH;
    wire [AW-1:0] a = kv_a;
    wire          is_v = (a >= KV_VB);
    wire [AW-1:0] wo = a - KV_VB;
    wire [KV_HB-8:0] tk = a[KV_HB-1:7];
    wire [KV_HB-4:0] pv = wo[KV_HB-1:3];
    wire [KV_AW-1:0] lk = (tk / PRK) * KV_NH + a[KV_HB+1:KV_HB];
    wire [KV_AW-1:0] lv = KV_KL + (pv >> KV_SV) * KV_NH + wo[KV_HB+1:KV_HB];
    wire [TG*W*8-1:0] kvs_rd_m;
    wire          kv_ce_r;
    wire [KV_AW-1:0] kv_ad_r;
    wire [ROM_ARELAY+1:0] kvce_l;
    ot_hdc_vline #(.D(ROM_ARELAY + 1)) u_kvce (.clk(clk), .rst_n(rst_n), .v(kv_re), .vd(kvce_l));
    wire [KV_AW-1:0] kv_ad_d;
    generate if (MUT == 1) begin : g_mut_ad
        reg [KV_AW-1:0] late;
        always @(posedge clk) late <= is_v ? lv : lk;
        assign kv_ad_d = late;
    end else begin : g_ad
        assign kv_ad_d = is_v ? lv : lk;
    end endgenerate
    ot_hdc_delay #(.W(KV_AW), .D(ROM_ARELAY)) u_kvad (.clk(clk), .rst_n(rst_n), .d(kv_ad_d), .q(kv_ad_r));
    assign kv_ce_r = kvce_l[ROM_ARELAY];
    reg kv_rd_q;
    reg [TG*W*8-1:0] cap;
    always @(posedge clk or negedge rst_n) if (!rst_n) kv_rd_q <= 1'b0; else kv_rd_q <= kv_ce_r;
    always @(posedge clk) if (kv_rd_q) cap <= kvs_rd;
    ot_hdc_delay #(.W(TG*W*8), .D(RX - ROM_ARELAY)) u_kvd (.clk(clk), .rst_n(rst_n),
        .d(cap), .q(kvs_rd_m));
    assign kvs_r_ce = kv_ce_r;
    assign kvs_r_addr = kv_ad_r;
    assign kv_q = kvs_rd_m;
endmodule

module ot_qwen_tile_kvl (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    tile_id6,
    input  wire [983:0]  li,
    output wire [983:0]  lo,
    input  wire          kv_re,
    input  wire [23:0]   kv_a,
    output wire [511:0]  kv_q,
    output wire          land_fault
);
    ot_qwen_tile_kvl_core #(.GT(6144), .KV_VB(131072), .KV_NH(2), .KV_AW(7), .KV_HB(16), .KV_SK(7), .KV_SV(9), .AW(24),
        .TG(4), .W(16), .ROM_ARELAY(2), .RX(6), .KVL(984), .LSLOTS(3), .MUT(0)) u_c (
        .clk(clk), .rst_n(rst_n), .tile_id6(tile_id6), .li(li), .lo(lo), .kv_re(kv_re), .kv_a(kv_a), .kv_q(kv_q),
        .land_fault(land_fault));
endmodule
