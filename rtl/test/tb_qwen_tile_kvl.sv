// ot_qwen_tile_kvl leaf equivalence bench (el1011-q-tile spec r5 item 3).  The leaf is a pure re-hierarchy, so the
// reference is the ORIGINAL logic: the statements of the KVH = 0 path frozen verbatim in three reference modules that
// mirror the three modules they came from (ot_qwen_rom_tile_die, ot_qwen_rom_tile_w12, ot_qwen_rom_tile_logic_w12
// g_kv_local), at the tile-die production parameters, with the same behavioural slice macro model
// (physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v).
// Stimulus: random landing words (slots addressed to this tile and to other columns, a few same-word collisions so
// land_fault is exercised), random slice reads over the K and V address ranges, random asynchronous resets.
// Check: lo, kv_q and land_fault equal the reference on every cycle; the run must also see slice writes, reads that
// return written (non-zero) words and at least one land_fault.
// MUT = 1 (must FAIL): the leaf's read address enters its relay one edge late (ot_qwen_tile_kvl_core MUT).
`timescale 1ns/1ps
module kvl_ref_die #(parameter integer KVL = 984, parameter integer LSLOTS = 3) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire [KVL-1:0]    li,
    output wire [KVL-1:0]    lo,
    output wire              kvw_ce,
    output wire [6:0]        kvw_addr,
    output wire [511:0]      kvw_data, kvw_mask,
    output reg               land_fault
);
    localparam integer SLW = 281;
    (* keep *) reg [KVL-1:0] li_q;
    (* keep *) reg [KVL-1:0] lo_q;
    always @(posedge clk) begin li_q <= li; lo_q <= li_q; end
    assign lo = lo_q;
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
        assign s_v[k]               = w[274] && (w[280:275] == tile_id[5:0]);
    end endgenerate
    wire [6:0]   rr_n    = li_q[LSLOTS*SLW +: 7];
    wire [127:0] tail_lm = li_q[LSLOTS*SLW + 7 +: 128];
    wire [LSLOTS-1:0] s_grant;
    ot_qwen_kv_land_merge #(.NSRC(LSLOTS), .PW(7), .LW(7), .DW(512)) u_merge (
        .clk(clk), .rst_n(rst_n), .rr_n(rr_n), .s_v(s_v), .s_port(s_port), .s_loc(s_loc), .s_isk(s_isk),
        .s_ktail(s_ktail), .s_sel(s_sel), .s_beat(s_beat), .tail_lm(tail_lm), .s_grant(s_grant),
        .tok_v(1'b0), .tok_loc(7'd0), .tok_data(512'd0), .tok_mask(512'd0),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) land_fault <= 1'b0;
        else land_fault <= land_fault | (|(s_v & ~s_grant));
endmodule

module kvl_ref_w12 #(parameter integer ROM_PIPE = 1, parameter integer ROM_ARELAY = 2, parameter integer KV_SLICE = 1) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              kvs_r_ce,
    input  wire [6:0]        kvs_r_addr,
    output wire [511:0]      kvs_rd,
    input  wire              kvw_ce,
    input  wire [6:0]        kvw_addr,
    input  wire [511:0]      kvw_data,
    input  wire [511:0]      kvw_mask
);
    genvar p;
    reg        kvw_ce_q;
    reg [6:0]  kvw_addr_q;
    reg [511:0] kvw_data_q, kvw_mask_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kvw_ce_q <= 1'b0;
        else kvw_ce_q <= kvw_ce;
    end
    always @(posedge clk) begin kvw_addr_q <= kvw_addr; kvw_data_q <= kvw_data; kvw_mask_q <= kvw_mask; end
    localparam integer KWD = (ROM_PIPE != 0) ? ROM_ARELAY : 0;
    wire        kvw_ce_r;
    generate if (KWD != 0) begin : g_kwv
        wire [KWD+1:0] kvw_l;
        ot_hdc_vline #(.D(KWD + 1)) u_kwv (.clk(clk), .rst_n(rst_n), .v(kvw_ce_q), .vd(kvw_l));
        assign kvw_ce_r = kvw_l[KWD];
    end else begin : g_kwn
        assign kvw_ce_r = kvw_ce_q;
    end endgenerate
    wire [6:0]  kvw_addr_r;
    wire [511:0] kvw_data_r, kvw_mask_r;
    ot_hdc_delay #(.W(7 + 1024), .D(KWD)) u_kwd (.clk(clk), .rst_n(rst_n), .d({kvw_addr_q, kvw_data_q, kvw_mask_q}),
        .q({kvw_addr_r, kvw_data_r, kvw_mask_r}));
    generate
        for (p = 0; p < ((KV_SLICE != 0) ? 2 : 0); p = p + 1) begin : g_kv
            ot_sram_1r1w_128x256_m1_r2c2 u_kv (
                .clk(clk), .r_ce_in(kvs_r_ce), .r_addr_in(kvs_r_addr), .rd_out(kvs_rd[256*p +: 256]),
                .w_ce_in(kvw_ce_r), .w_addr_in(kvw_addr_r), .wd_in(kvw_data_r[256*p +: 256]),
                .w_mask_in(kvw_mask_r[256*p +: 256]),
                .rr_en(2'b0), .rr_addr(14'd0), .cr_en(2'b0), .cr_sel(16'd0));
        end
    endgenerate
endmodule

module kvl_ref_logic #(
    parameter integer GT = 6144,
    parameter integer KV_VB = 131072,
    parameter integer KV_NH = 2,
    parameter integer MEM_EXTRA = 1,
    parameter integer ROM_PIPE = 1,
    parameter integer ROM_ARELAY = 2,
    parameter integer ROM_CAP2 = 1,
    parameter integer ROM_CAPX = 2,
    parameter integer KV_AW = 7,
    parameter integer KV_HB = 16,
    parameter integer KV_SK = 7,
    parameter integer KV_SV = 9,
    parameter integer TG = 4,
    parameter integer W = 16,
    parameter integer AW = 24
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              me_kv_re,
    input  wire [TG*AW-1:0]  me_kv_addr,
    output wire [TG*W*8-1:0] kvs_rd_m,
    output wire              kvs_r_ce,
    output wire [KV_AW-1:0]  kvs_r_addr,
    input  wire [TG*W*8-1:0] kvs_rd
);
    localparam integer RX = (ROM_PIPE != 0) ? (ROM_ARELAY + 2 + ROM_CAP2 + ((ROM_CAPX == 2) ? 1 : 0)) : 0;   // extra memory cycles of the ROM pipeline
    generate begin : g_kv_local
        localparam [KV_AW-1:0] PRK = GT >> KV_SK;
        localparam integer KV_PT = 1 << (KV_HB - 7);
        localparam integer KV_KL = ((KV_PT + (GT >> KV_SK) - 1) / (GT >> KV_SK)) * KV_NH;
        wire [AW-1:0] a = me_kv_addr[AW-1:0];            // every group of the tile maps to the same word
        wire          is_v = (a >= KV_VB);
        wire [AW-1:0] w = a - KV_VB;
        wire [KV_HB-8:0] tk = a[KV_HB-1:7];
        wire [KV_HB-4:0] pv = w[KV_HB-1:3];
        wire [KV_AW-1:0] lk = (tk / PRK) * KV_NH + a[KV_HB+1:KV_HB];
        wire [KV_AW-1:0] lv = KV_KL + (pv >> KV_SV) * KV_NH + w[KV_HB+1:KV_HB];
        wire          kv_ce_r;
        wire [KV_AW-1:0] kv_ad_r;
        if (ROM_PIPE != 0) begin : g_kvrl
            wire [ROM_ARELAY+1:0] kvce_l;
            ot_hdc_vline #(.D(ROM_ARELAY + 1)) u_kvce (.clk(clk), .rst_n(rst_n), .v(me_kv_re), .vd(kvce_l));
            ot_hdc_delay #(.W(KV_AW), .D(ROM_ARELAY)) u_kvad (.clk(clk), .rst_n(rst_n), .d(is_v ? lv : lk), .q(kv_ad_r));
            assign kv_ce_r = kvce_l[ROM_ARELAY];
        end else begin : g_kvnorl
            assign kv_ce_r = me_kv_re;
            assign kv_ad_r = is_v ? lv : lk;
        end
        if (MEM_EXTRA != 0) begin : g_kvcap
            reg kv_rd_q;
            reg [TG*W*8-1:0] cap;
            always @(posedge clk or negedge rst_n) if (!rst_n) kv_rd_q <= 1'b0; else kv_rd_q <= kv_ce_r;
            always @(posedge clk) if (kv_rd_q) cap <= kvs_rd;
            ot_hdc_delay #(.W(TG*W*8), .D(RX - ((ROM_PIPE != 0) ? ROM_ARELAY : 0))) u_kvd (.clk(clk), .rst_n(rst_n),
                .d(cap), .q(kvs_rd_m));
        end else begin : g_kvnocap
            assign kvs_rd_m = kvs_rd;
        end
        assign kvs_r_ce = kv_ce_r;
        assign kvs_r_addr = kv_ad_r;
    end endgenerate
endmodule

module tb_qwen_tile_kvl;
    parameter integer N = 40000, MUT = 0;
    reg clk = 0, rst_n = 0;
    reg [983:0] li = 0;
    reg         kv_re = 0;
    reg [23:0]  kv_a = 0;
    localparam [15:0] TID = 16'h0a2b;   // column 0x2b
    // ---- reference: the original three-module structure ----
    wire [983:0] r_lo; wire r_fault;
    wire r_wce; wire [6:0] r_waddr; wire [511:0] r_wdata, r_wmask;
    wire r_rce; wire [6:0] r_raddr; wire [511:0] r_rd, r_q;
    kvl_ref_die r_die (.clk(clk), .rst_n(rst_n), .tile_id(TID), .li(li), .lo(r_lo), .kvw_ce(r_wce), .kvw_addr(r_waddr),
        .kvw_data(r_wdata), .kvw_mask(r_wmask), .land_fault(r_fault));
    kvl_ref_w12 r_w12 (.clk(clk), .rst_n(rst_n), .kvs_r_ce(r_rce), .kvs_r_addr(r_raddr), .kvs_rd(r_rd),
        .kvw_ce(r_wce), .kvw_addr(r_waddr), .kvw_data(r_wdata), .kvw_mask(r_wmask));
    kvl_ref_logic r_log (.clk(clk), .rst_n(rst_n), .me_kv_re(kv_re), .me_kv_addr({72'd0, kv_a}), .kvs_rd_m(r_q),
        .kvs_r_ce(r_rce), .kvs_r_addr(r_raddr), .kvs_rd(r_rd));
    // ---- the leaf ----
    wire [983:0] lo; wire [511:0] kv_q; wire land_fault;
    generate if (MUT == 0) begin : g_dut
        ot_qwen_tile_kvl u (.clk(clk), .rst_n(rst_n), .tile_id6(TID[5:0]), .li(li), .lo(lo), .kv_re(kv_re), .kv_a(kv_a),
            .kv_q(kv_q), .land_fault(land_fault));
    end else begin : g_mut
        ot_qwen_tile_kvl_core #(.MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .tile_id6(TID[5:0]), .li(li), .lo(lo),
            .kv_re(kv_re), .kv_a(kv_a), .kv_q(kv_q), .land_fault(land_fault));
    end endgenerate
    always #1 clk = ~clk;
    integer i, k, bad = 0, checks = 0, writes = 0, reads = 0, nzq = 0, faults = 0, resets = 0, seed = 7, r;
    reg pf;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 7; $display("SEED=%0d", seed); end
    initial begin
        repeat (3) @(posedge clk); rst_n = 1; pf = 0;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            if (i > 12) begin
                if (lo !== r_lo) bad = bad + 1;
                if (kv_q !== r_q) bad = bad + 1;
                if (land_fault !== r_fault) bad = bad + 1;
                checks = checks + 1; writes = writes + r_wce; reads = reads + r_rce;
                if (r_q != 512'd0) nzq = nzq + 1;
                if (r_fault && !pf) faults = faults + 1;
                pf = r_fault;
            end
            for (k = 0; k < 984; k = k + 8) li[k +: 8] = $random(seed);
            for (k = 0; k < 3; k = k + 1) begin
                if (($random(seed) & 3) != 0) li[k*281 + 275 +: 6] = TID[5:0];
                // slice words: mostly distinct per slot (always granted), a same-word collision about 1 in 512 cycles
                r = $random(seed);
                li[k*281 + 260 +: 7] = ((r & 511) == 0) ? 7'd5 : ((r >> 9) & 7'h78) | k;
            end
            kv_re = $random(seed);
            r = $random(seed);
            // K range (below KV_VB = 131072), V range above it, and now and then any 24-bit address
            if ((r & 15) == 0) kv_a = $random(seed);
            else if (r & 16) kv_a = (r >> 5) & 24'h03ffff;
            else kv_a = 24'd131072 + ((r >> 5) & 24'h03ffff);
            // asynchronous reset, about every 4000 cycles, 1..4 cycles long
            r = $random(seed);
            if ((r & 4095) == 0 && i > 100) begin
                #0.3 rst_n = 0; repeat (1 + ((r >> 12) & 3)) @(negedge clk); #0.3 rst_n = 1; resets = resets + 1;
            end
        end
        if (bad == 0 && writes > 0 && reads > 0 && nzq > 0 && faults > 0)
            $display("PASS %0d cycles writes=%0d reads=%0d nonzero_q=%0d land_faults=%0d resets=%0d", checks, writes, reads, nzq, faults, resets);
        else $display("FAIL tile_kvl MUT=%0d: %0d mismatches of %0d cycles (writes %0d reads %0d nonzero_q %0d land_faults %0d)",
                      MUT, bad, checks, writes, reads, nzq, faults);
        $finish;
    end
endmodule
