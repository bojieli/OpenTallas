`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die (W12, TP4, G = 6,144): the KV memory service of the REAL_MEM runtime on
// NSTK = 4 HBM3E stacks a die behind the near-HBM STREAMING controllers (default-off; selected
// only by the die rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv).  SUCCESSOR of
// ot_qwen_rt_kv_stream_service (one stack, P < 2048; left byte-identical): the core-facing
// boundary, tile slice map, open-tile TAIL, V assembly, token-write checks and readiness rules
// are that module's.  What differs:
//
// (1) FULL BANDWIDTH: NPC = 32 * NSTK landing / write ports (ot_qwen_hbm_stream4_ack).  The KV
//     window is striped across stacks, pseudo-channels and banks in consumption order (stack =
//     r[1:0], PC = r[6:2], PC-local j = {g, r[7]}; the map is in ot_qwen_hbm_stream4_ack), so
//     the window of position P is the prefix of (8 / NSTK) * (P/16 + 1) sectors in EVERY PC of
//     every stack, and P < 8192 (4 MiB a layer a die = one DRAM row in every bank of 4 stacks).
//     The landing adapter takes up to one beat per PC per cycle (NPC beats).  Slice writes are
//     arbitrated PER TILE by the hardened landing merge (rtl/hdc/kv/ot_qwen_kv_land_merge.sv, <= 12
//     sources a tile under this map; one SRAM write per tile a cycle): token writes first; then
//     the first valid beat half in rotating port order claims the write and a later half joins it
//     iff same slice word and its lane quarters overlap no earlier valid half of that word.  The
//     two halves of a V beat are granted independently (no cross-tile handshake); the PC pops the
//     beat when both are written.
// (2) CROSS-LAYER PREFETCH (run-time strap early_go_in): the next layer's descriptor (the
//     notice, posted once this layer retired) is RELEASED (go) as soon as the core is done with
//     this layer's KV slices (kv_free: the layer's next program segment starts, i.e. QK/PV and
//     the O projection with its all-reduce are complete), so the next layer's window streams into
//     the slices during this layer's MLP.  The next layer's start then finds its fill running or
//     done (no refill).  Preconditions, checked: this layer's fill done and every token
//     write-back issued.
// (3) POSTED WRITE-BACK (run-time strap posted_wb_in): kv_write_drained no longer waits for the
//     HBM write-done (the token's K/V are on die: the tiles see them through kv_ok's pipe/tail
//     rules); write-backs issue once this layer's fill is done (the controller's descriptor is
//     then this layer's row) and retire on the tagged, generation-checked write-done, also after
//     the next layer has started (a stale-generation done only retires its entry).  VISIBILITY
//     FENCE: no descriptor of any later layer is posted while a write-back is outstanding (the
//     controller writes on the current descriptor's row, so the fence also orders HBM rows).
//     wb_busy reports outstanding write-backs (the host drains it before reading HBM back).
// With both straps 0 the behaviour is the predecessor's, on 4 stacks.
// The retained description of the predecessor follows.
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die (W12, TP4, G = 6,144): the KV memory service of the REAL_MEM runtime on
// the near-HBM STREAMING controller (HBM_STREAM, default-off; selected only by the die
// rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream.sv).  SUCCESSOR of
// rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv (left byte-identical): the core-facing boundary
// (start/pos/layer, kvd_* + kv_ok, kv_we/kv_waddr/kv_wdata + kv_write_drained), the tile
// slice map, the open-tile TAIL, the V assembly, the token-write checks, the slice-write
// arbitration and network and every readiness rule are that module's, unchanged.  What differs
// is the HBM side (ot_qwen_hbm_stream_ack: ot_hbm_r14_stream_stack + DRAM checker):
//
// FILL = one stream descriptor per layer instead of tagged requests.  The window of position P
// is the stream prefix of 8 * (P/16 + 1) sectors per PC (K tiles 0..P/16 and V positions
// 0..16*(P/16)+15 in position order; the map is in ot_qwen_hbm_stream_ack).  NOTICE: the
// descriptor of the NEXT layer (nx_layer, static in decode) is posted as soon as this layer's
// stream is retired and its token K/V is written back with write-done (the controller then
// protects the first sets from refresh and opens the first rows); `go` at the layer start
// releases the reads.  Without a notice (nx_layer = 255, or the first layer of a run) the
// descriptor is posted at the start.
// LANDING (the row-landing adapter): per PC the controller returns its sectors in stream order;
// each landed beat must carry exactly the next expected (PC, index) sector of this layer's row
// (else a fault); V sectors of positions >= P are taken and dropped; every other beat becomes
// slice writes exactly as a fill response did.
// WRITE-BACK: up to WBW complete token sectors a cycle, each to its own PC's write buffer
// (distinct PCs); retired on the controller's tagged, generation-checked write-done.
// Window limit of the stream map: positions < 2048 (one DRAM row per layer); P >= 2048 faults.
// KV_IDEAL / ideal_in: as the fill service (no HBM traffic; nothing posted).
// ---------------------------------------------------------------------------
module ot_qwen_rt_kv_stream4_service #(
    parameter integer G        = 6144,
    parameter integer TG       = 4,
    parameter integer SW       = 64,
    parameter integer AW       = 24,
    parameter integer NW       = 18,
    parameter integer NSTK     = 4,
    parameter integer NPC      = 32 * NSTK,
    parameter integer HAW      = 24,       // HBM sector address bits
    parameter integer NWR      = 64,       // outstanding writes
    parameter integer FILL_LAT = 8,        // network register stages to the tiles
    parameter integer KV_IDEAL = 0,
    parameter integer WBW      = 1,        // write-backs issued a cycle (distinct PCs)
    parameter integer LPCW     = $clog2(NPC),
    parameter integer IDW      = $clog2(NWR),
    parameter integer TGW      = 1 + 2 + IDW,  // tag: {write, generation[1:0], id}
    parameter integer KV_MAP   = 0             // 1: option-M quadrant-local stripe (ot_qwen_kv_map_m.svh); NSTK 4
) (
    input  wire              clk,
    input  wire              rst_n,
    // layer start
    input  wire              start,
    input  wire              ideal_in,    // A/B reference at run time (as KV_IDEAL = 1)
    input  wire [NW-1:0]     pos,
    input  wire [7:0]        layer,
    input  wire [7:0]        nx_layer,    // the layer that runs next (notice); 255: none
    input  wire [NW-1:0]     pos_hint,    // the token's position (the notice's window size)
    input  wire              kv_free,     // the core is done with this layer's KV slices (pulse)
    input  wire              early_go_in, // strap: release the next layer's stream at kv_free
    input  wire              posted_wb_in,// strap: posted write-back (kv_write_drained not on write-done)
    output wire              wb_busy,     // write-backs outstanding
    // core KV interface (the service boundary)
    input  wire              kvd_v,
    input  wire [NW-1:0]     kvd_pos,
    input  wire              kvd_kindk,
    output wire              kv_ok,
    input  wire [SW-1:0]     kv_we,
    input  wire [SW*AW-1:0]  kv_waddr,
    input  wire [SW*32-1:0]  kv_wdata,
    output wire              kv_write_drained,
    // tile KV slice write ports (registered here; each tile registers again)
    output reg  [G/TG-1:0]     kvw_ce,
    output reg  [G/TG*7-1:0]   kvw_addr,
    output reg  [G/TG*512-1:0] kvw_data,
    output reg  [G/TG*512-1:0] kvw_mask,
    // streaming HBM (ot_qwen_hbm_stream_ack)
    output reg               d_v,
    input  wire              d_rdy,
    output reg  [18:0]       d_row,
    output reg  [10:0]       d_n,
    output reg               go,
    input  wire [NPC-1:0]    l_v,
    input  wire [NPC*17-1:0] l_sec,
    input  wire [NPC*8-1:0]  l_row,
    input  wire [NPC*256-1:0] l_data,
    output reg  [NPC-1:0]    l_pop,
    output reg  [NPC-1:0]    w_v,
    output reg  [NPC*24-1:0] w_sec,
    output reg  [NPC*256-1:0] w_data,
    output reg  [NPC*TGW-1:0] w_tag,
    input  wire [NPC-1:0]    w_room,
    input  wire [NPC-1:0]    wd_v,
    input  wire [NPC*TGW-1:0] wd_tag,
    // status
    output reg               fault,
    output reg  [15:0]       fault_code,
    output reg  [31:0]       st_fill_cycles,     // start to fill retired (last layer)
    output reg  [31:0]       st_fill_sectors,
    output reg  [31:0]       st_wr_sectors,
    output reg  [31:0]       st_rsp_stall,       // port-cycles a landed beat waited on a tile conflict
    output reg  [31:0]       st_kvok_low_desc,   // cycles a KV descriptor waited with kv_ok low
    output reg  [31:0]       st_drain_low,       // cycles kv_write_drained was low
    output reg  [31:0]       st_wr_lat_max,      // longest write request-to-done, cycles
    output reg  [31:0]       st_fill_exposed     // start to fill retired (0 if retired before the start)
);
    localparam integer NT = G / TG;
    wire idl = (KV_IDEAL != 0) || ideal_in;
    localparam integer KVB = 131072;           // first V word
    localparam integer KL = 22;                // K slice words: ceil(512/48) rounds x 2 heads
    localparam integer LAYER_SEC = 131072;     // sectors a layer window occupies
    localparam integer NE = SW + 2 * NPC;      // slice-write entries a cycle
    localparam integer GENW = 2;
    localparam integer SHW = 128;              // half a sector: one word
    localparam integer WINP = 8192;            // window positions (one DRAM row in every bank of 4 stacks)
    localparam integer SPT = 8 / NSTK;         // sectors a PC streams per 16-position tile

    // ---- E4M3 <-> FP32 (exact; the tile's e4m3_f32 inverse) --------------------
    function automatic [8:0] f32_e4m3(input [31:0] b);   // {bad, code}
        reg [7:0] e; reg [22:0] m;
        begin
            e = b[30:23]; m = b[22:0];
            if (e == 0 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd0};
            else if (e >= 8'd121 && e <= 8'd135 && m[19:0] == 0) f32_e4m3 = {1'b0, b[31], e[3:0] - 4'd8, m[22:20]};
            else if (e == 8'd120 && m[20:0] == 0) f32_e4m3 = {1'b0, b[31], 4'd0, 1'b1, m[22:21]};
            else if (e == 8'd119 && m[21:0] == 0) f32_e4m3 = {1'b0, b[31], 5'd0, 1'b1, m[22]};
            else if (e == 8'd118 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd1};
            else f32_e4m3 = {1'b1, 8'd0};
        end
    endfunction

    // ---- layer state ----------------------------------------------------------------
    reg [NW-1:0]  P;
    reg [8:0]     T;                 // open K tile
    reg [3:0]     PL;                // P mod 16
    reg [HAW-1:0] lbase;
    reg [GENW-1:0] gen;
    reg           active;            // a layer is in progress (after start)

    // ---- stream fill state --------------------------------------------------------------------
    // landed beat j of port (stack k, PC q) -> layer-relative logical sector (ot_qwen_hbm_stream4_ack)
`include "ot_qwen_kv_map_m.svh"
    function automatic [16:0] p2l(input integer port, input [9:0] j);
        reg [4:0] q; reg [1:0] k;
        begin q = 5'(port % 32); k = 2'(port / 32);
              p2l = (KV_MAP != 0) ? m_p2l(port, j) : {j[0], q[4], j[9:1], q[3:0], k}; end
    endfunction
    function automatic integer l2port(input [16:0] l);
        l2port = (KV_MAP != 0) ? m_l2port(l) : integer'(l[1:0]) * 32 + integer'({l[15], l[5:2]});
    endfunction
    function automatic [10:0] npc(input integer port, input [10:0] n);   // this PC's sectors of a base-n window
        npc = (KV_MAP != 0) ? m_n(port / 32, n) : n;
    endfunction
    function automatic [10:0] n_of(input [NW-1:0] p);    // sectors a PC streams for position p
        n_of = 11'(({7'd0, p[NW-1:4]} + 1) * SPT);
    endfunction
    reg [7:0]     lyr;               // this layer
    reg [10:0]    nfill;             // sectors per PC this layer
    reg [10:0]    lcnt [0:NPC-1];    // landed sectors per PC
    reg [31:0]    fill_t0;
    reg           fill_done;
    reg [7:0]     posted;            // layer whose descriptor is in the controller and not yet started (255 none)
    reg [NW-1:0]  posted_p;
    reg           go_pend;           // start without notice: go once the descriptor is posted
    reg  [NWR-1:0] w_valid;
    reg  [GENW-1:0] w_gen [0:NWR-1];
    reg  [31:0]   w_t0 [0:NWR-1];
    reg  [31:0]   cyc;
    reg  [7:0]    pre_lyr;           // layer whose fill was released early (before its start); 255 none
    reg  [NW-1:0] pre_p;
    reg           free_seen;         // kv_free seen in this layer
    reg  [31:0]   start_t;           // this layer's start

    // ---- tail (open K tile) and V assembly ---------------------------------------------
    reg [SHW-1:0] tk_data [0:255];   // [h*128 + d]
    reg [255:0]   tk_fill, tk_wr;
    reg [1:0]     tk_st [0:127];     // sector (h, d/2): 0 idle, 1 sent, 2 acked
    reg [SHW-1:0] va_data [0:15];    // [h*8 + q]
    reg [15:0]    va_mask [0:15];
    reg [1:0]     va_st [0:7];       // sector (h, q/2)
    reg [7:0]     w_sec_e [0:NWR-1];   // write entry -> sector (K: h*64 + d/2, V: 128 + h*4 + q/2)
    reg [7:0]     w_pc  [0:NWR-1];   // write entry -> its port (acks must come from it)

    // ---- token (stream-unit) writes: per lane decode ------------------------------------
    // one slice write per lane, merged per tile below
    reg [SW-1:0]   l_v_tok;
    reg [10:0]     l_tile [0:SW-1];
    reg [6:0]      l_loc  [0:SW-1];
    reg [8:0]      l_bit  [0:SW-1];   // bit offset of the lane's code in the slice word
    reg [7:0]      l_code [0:SW-1];
    reg [SW-1:0]   l_bad;
    integer li;
    always @(*) begin
        for (li = 0; li < SW; li = li + 1) begin
            reg [AW-1:0] e; reg [AW-5:0] a; reg [8:0] fc; reg [16:0] w;
            reg [8:0] t; reg [6:0] d; reg h; reg [12:0] pp; reg [2:0] q;
            e = kv_waddr[li*AW +: AW];
            a = e[AW-1:4];
            fc = f32_e4m3(kv_wdata[li*32 +: 32]);
            l_v_tok[li] = kv_we[li];
            l_code[li] = fc[7:0];
            l_bad[li] = 1'b0;
            l_tile[li] = 0; l_loc[li] = 0; l_bit[li] = 0;
            if (kv_we[li]) begin
                if (fc[8]) l_bad[li] = 1'b1;
                if (a < KVB) begin
                    h = a[16]; t = a[15:7]; d = a[6:0];
                    if (a[19:17] != 0 || t != T || e[3:0] != PL) l_bad[li] = 1'b1;
                    l_tile[li] = (t % 48) * 32 + d / 4;
                    l_loc[li]  = (t / 48) * 2 + h;
                    l_bit[li]  = {d[1:0], e[3:0], 3'd0};
                end else begin
                    w = a - KVB;
                    h = w[16]; pp = w[15:3]; q = w[2:0];
                    if (a >= KVB + 131072 || pp != P[12:0]) l_bad[li] = 1'b1;
                    l_tile[li] = q * 128 + (pp % 512) / 4;
                    l_loc[li]  = KL + (pp / 512) * 2 + h;
                    l_bit[li]  = {pp[1:0], e[3:0], 3'd0};
                end
            end
        end
    end

    // ---- landed beats: decode and per-port slice writes ------------------------------------------
    reg [NPC-1:0]  b_rd, b_bad, b_drop;
    reg [16:0]     b_sec [0:NPC-1];
    reg [1:0]      b_n   [0:NPC-1];           // slice writes of the beat (1 K, 2 V, 0 dropped)
    reg [10:0]     b_tile [0:NPC-1][0:1];
    reg [6:0]      b_loc  [0:NPC-1][0:1];
    reg [511:0]    b_data [0:NPC-1][0:1];
    reg [511:0]    b_msk  [0:NPC-1][0:1];
    reg [NPC-1:0]  b_ktail;                   // the beat's words belong to the open K tile
    integer pi;
    always @(*) begin
        for (pi = 0; pi < NPC; pi = pi + 1) begin
            reg [16:0] s; reg [17:0] a; reg [10:0] c;
            reg [8:0] t; reg [6:0] d; reg h; reg [16:0] w; reg [12:0] pp; reg [2:0] q;
            reg [255:0] dat; reg [127:0] lm;
            dat = l_data[pi*256 +: 256];
            c = lcnt[pi];
            b_rd[pi] = 1'b0; b_bad[pi] = 1'b0; b_drop[pi] = 1'b0; b_n[pi] = 0; b_ktail[pi] = 1'b0;
            b_sec[pi] = 0;
            b_tile[pi][0] = 0; b_tile[pi][1] = 0; b_loc[pi][0] = 0; b_loc[pi][1] = 0;
            b_data[pi][0] = 0; b_data[pi][1] = 0; b_msk[pi][0] = 0; b_msk[pi][1] = 0;
            if (l_v[pi]) begin
                b_rd[pi] = 1'b1;
                //: exactly the next sector of this PC's stream, of this layer's row, inside the window
                if (!active || fill_done || c >= npc(pi, nfill) || l_sec[pi*17 +: 17] != p2l(pi, c[9:0]) || l_row[pi*8 +: 8] != lyr)
                    b_bad[pi] = 1'b1;
                s = p2l(pi, c[9:0]);
                b_sec[pi] = s;
                a = {s, 1'b0};
                if (a < KVB) begin
                    h = a[16]; t = a[15:7]; d = a[6:0];       // d even: words d, d+1 share tile and local
                    b_n[pi] = 2'd1;
                    b_tile[pi][0] = (t % 48) * 32 + d / 4;
                    b_loc[pi][0] = (t / 48) * 2 + h;
                    //: the open tile: lanes >= P mod 16 are the token's (or later): never written by the fill
                    lm = (t == T) ? ((128'd1 << (8 * PL)) - 128'd1) : {128{1'b1}};
                    if (t == T) b_ktail[pi] = 1'b1;
                    b_data[pi][0] = {256'd0, dat} << (128 * d[1:0]);
                    b_msk[pi][0]  = {256'd0, lm, lm} << (128 * d[1:0]);
                end else begin
                    w = a - KVB;
                    h = w[16]; pp = w[15:3]; q = w[2:0];      // q even: dim tiles q, q+1
                    if (pp >= P[12:0]) b_drop[pi] = 1'b1;    // V of the token's position or later: not history
                    else begin
                        b_n[pi] = 2'd2;
                        b_tile[pi][0] = q * 128 + (pp % 512) / 4;
                        b_tile[pi][1] = (q + 1) * 128 + (pp % 512) / 4;
                        b_loc[pi][0] = KL + (pp / 512) * 2 + h;
                        b_loc[pi][1] = KL + (pp / 512) * 2 + h;
                        b_data[pi][0] = {384'd0, dat[127:0]} << (128 * pp[1:0]);
                        b_data[pi][1] = {384'd0, dat[255:128]} << (128 * pp[1:0]);
                        b_msk[pi][0]  = {384'd0, {128{1'b1}}} << (128 * pp[1:0]);
                        b_msk[pi][1]  = {384'd0, {128{1'b1}}} << (128 * pp[1:0]);
                    end
                end
            end
        end
    end

    // ---- arbitration: token writes first, then beats in rotating order -------------------
    reg [$clog2(NPC)-1:0] rr;
    reg [NE-1:0]   e_v;
    reg [10:0]     e_tile [0:NE-1];
    reg [6:0]      e_loc  [0:NE-1];
    reg [511:0]    e_data [0:NE-1];
    reg [511:0]    e_msk  [0:NE-1];
    reg            tok_conflict;
    integer ai, aj, ak, pp_i;
    integer tent [0:NT-1];           // the entry that claimed a tile this cycle (-1: none)
    reg [3:0]      seen_q [0:NT-1];  // lane quarters of the valid beat requests of the claimed word so far
    reg [1:0]      hdone [0:NPC-1];  // halves of the presented beat written in earlier cycles
    reg [1:0]      h_got [0:NPC-1];  // halves written by this cycle
    always @(*) begin
        reg ok; integer n;
        for (ai = 0; ai < NE; ai = ai + 1) begin e_v[ai] = 1'b0; e_tile[ai] = 0; e_loc[ai] = 0; e_data[ai] = 0; e_msk[ai] = 0; end
        for (ai = 0; ai < NT; ai = ai + 1) tent[ai] = -1;
        tok_conflict = 1'b0;
        n = 0;
        // token lanes merged per tile (same tile => same local word, else a protocol fault)
        for (ai = 0; ai < SW; ai = ai + 1)
            if (l_v_tok[ai]) begin
                ok = 1'b0;
                for (aj = 0; aj < SW; aj = aj + 1)
                    if (aj < n && e_v[aj] && e_tile[aj] == l_tile[ai]) begin
                        ok = 1'b1;
                        if (e_loc[aj] != l_loc[ai]) tok_conflict = 1'b1;
                        e_data[aj] = e_data[aj] | ({504'd0, l_code[ai]} << l_bit[ai]);
                        e_msk[aj]  = e_msk[aj]  | ({504'd0, 8'hff} << l_bit[ai]);
                    end
                if (!ok) begin
                    tent[l_tile[ai]] = n;
                    e_v[n] = 1'b1; e_tile[n] = l_tile[ai]; e_loc[n] = l_loc[ai];
                    e_data[n] = {504'd0, l_code[ai]} << l_bit[ai];
                    e_msk[n]  = {504'd0, 8'hff} << l_bit[ai];
                    n = n + 1;
                end
            end
        // beats: each beat HALF (slice write) is arbitrated at its own tile by the per-tile landing merge
        // (rtl/hdc/kv/ot_qwen_kv_land_merge.sv, the hardened element; same rule): the first valid request in
        // rotating port order claims the tile's write (unless a token write holds it); a later request joins
        // that write iff it is for the same slice word and its lane quarters overlap no EARLIER valid request
        // of that word.  A V beat's two halves are granted independently; the beat pops when both are written.
        l_pop = 0;
        for (ai = 0; ai < NPC; ai = ai + 1) h_got[ai] = hdone[ai];
        for (ai = 0; ai < NT; ai = ai + 1) seen_q[ai] = 4'd0;
        for (pp_i = 0; pp_i < NPC; pp_i = pp_i + 1) begin
            integer p; reg [1:0] need; reg [3:0] qv; integer tl;
            p = (rr + pp_i) % NPC;
            if (l_v[p]) begin
                if (b_bad[p] || b_drop[p]) l_pop[p] = 1'b1;          // no slice write (a bad beat faults)
                else begin
                    need = (b_n[p] == 2'd2) ? 2'b11 : 2'b01;
                    for (ak = 0; ak < 2; ak = ak + 1)
                        if (need[ak] && !hdone[p][ak]) begin
                            tl = b_tile[p][ak];
                            qv = {|b_msk[p][ak][511:384], |b_msk[p][ak][383:256], |b_msk[p][ak][255:128], |b_msk[p][ak][127:0]};
                            aj = tent[tl];
                            if (aj < 0) begin
                                tent[tl] = SW + 2 * p + ak; seen_q[tl] = qv; h_got[p][ak] = 1'b1;
                                e_v[SW + 2 * p + ak] = 1'b1;
                                e_tile[SW + 2 * p + ak] = b_tile[p][ak]; e_loc[SW + 2 * p + ak] = b_loc[p][ak];
                                e_data[SW + 2 * p + ak] = b_data[p][ak]; e_msk[SW + 2 * p + ak] = b_msk[p][ak];
                            end else if (aj >= SW && e_loc[aj] == b_loc[p][ak]) begin
                                if ((seen_q[tl] & qv) == 4'd0) begin
                                    e_data[aj] = e_data[aj] | b_data[p][ak];
                                    e_msk[aj]  = e_msk[aj]  | b_msk[p][ak];
                                    h_got[p][ak] = 1'b1;
                                end
                                seen_q[tl] = seen_q[tl] | qv;
                            end
                        end
                    if ((h_got[p] & need) == need) l_pop[p] = 1'b1;
                end
            end
        end
    end
    // halves of the presented beat already written (a V beat whose other half waits)
    integer hi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) for (hi = 0; hi < NPC; hi = hi + 1) hdone[hi] <= 2'b00;
        else for (hi = 0; hi < NPC; hi = hi + 1)
            if (l_v[hi]) hdone[hi] <= l_pop[hi] ? 2'b00 : h_got[hi];

    // ---- network pipe to the tiles -------------------------------------------------------
    reg [NE-1:0]   q_v    [0:FILL_LAT-1];
    reg [10:0]     q_tile [0:FILL_LAT-1][0:NE-1];
    reg [6:0]      q_loc  [0:FILL_LAT-1][0:NE-1];
    reg [511:0]    q_data [0:FILL_LAT-1][0:NE-1];
    reg [511:0]    q_msk  [0:FILL_LAT-1][0:NE-1];
    reg [FILL_LAT+2:0] inflight;      // a slice write somewhere between here and its SRAM edge
    integer si, sj;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (si = 0; si < FILL_LAT; si = si + 1) q_v[si] <= 0;
            kvw_ce <= 0; inflight <= 0;
        end else begin
            q_v[0] <= e_v;
            for (si = 1; si < FILL_LAT; si = si + 1) q_v[si] <= q_v[si-1];
            inflight <= {inflight[FILL_LAT+1:0], |e_v};
            kvw_ce <= 0;
            for (sj = 0; sj < NE; sj = sj + 1)
                if (q_v[FILL_LAT-1][sj]) kvw_ce[q_tile[FILL_LAT-1][sj]] <= 1'b1;
        end
    end
    always @(posedge clk) begin
        for (sj = 0; sj < NE; sj = sj + 1) begin
            q_tile[0][sj] <= e_tile[sj]; q_loc[0][sj] <= e_loc[sj]; q_data[0][sj] <= e_data[sj]; q_msk[0][sj] <= e_msk[sj];
        end
        for (si = 1; si < FILL_LAT; si = si + 1)
            for (sj = 0; sj < NE; sj = sj + 1)
                if (q_v[si-1][sj]) begin
                    q_tile[si][sj] <= q_tile[si-1][sj]; q_loc[si][sj] <= q_loc[si-1][sj];
                    q_data[si][sj] <= q_data[si-1][sj]; q_msk[si][sj] <= q_msk[si-1][sj];
                end
        for (sj = 0; sj < NE; sj = sj + 1)
            if (q_v[FILL_LAT-1][sj]) begin
                kvw_addr[q_tile[FILL_LAT-1][sj]*7 +: 7] <= q_loc[FILL_LAT-1][sj];
                kvw_data[q_tile[FILL_LAT-1][sj]*512 +: 512] <= q_data[FILL_LAT-1][sj];
                kvw_mask[q_tile[FILL_LAT-1][sj]*512 +: 512] <= q_msk[FILL_LAT-1][sj];
            end
    end
    wire pipe_empty = (inflight == 0) && (e_v == 0);

    // ---- write-back selection: the lowest complete, unsent sectors (WBW a cycle, distinct PCs)
    function automatic [255:0] wb_data(input [7:0] sc);
        begin
            if (sc < 128) wb_data = {tk_data[2*sc+1], tk_data[2*sc]};
            else wb_data = {va_data[2*(sc-128)+1], va_data[2*(sc-128)]};
        end
    endfunction
    function automatic [16:0] wb_rel(input [7:0] sc);    // layer-relative sector of a write-back
        begin
            if (sc < 128) wb_rel = {sc[6], 16'd0} / 2 + ({8'd0, T} * 17'd64) + sc[5:0];        // K: (h*65536 + T*128 + 2m)/2
            else wb_rel = 17'd65536 + {(sc[2] ? 17'd32768 : 17'd0)} + P[12:0] * 17'd4 + sc[1:0];  // V: (VB + h*65536 + P*8 + 2m)/2
        end
    endfunction
    reg [WBW-1:0] wp_v;
    reg [7:0]     wp_sec [0:WBW-1];
    reg [IDW-1:0] wp_id  [0:WBW-1];
    reg [7:0]     wp_pc  [0:WBW-1];
    integer wi, wk, wj;
    always @(*) begin
        reg [NPC-1:0] used_pc; reg [NWR-1:0] used_id; reg cpl; integer wpo; reg fid_ok; reg [IDW-1:0] fid;
        integer n;
        used_pc = 0; used_id = 0; n = 0;
        for (wk = 0; wk < WBW; wk = wk + 1) begin wp_v[wk] = 1'b0; wp_sec[wk] = 0; wp_id[wk] = 0; wp_pc[wk] = 0; end
        //: write-backs issue once this layer's fill is done: the controllers' descriptor is then this layer's row
        if (!idl && active && fill_done && pre_lyr == 8'hff)
            for (wi = 0; wi < 136; wi = wi + 1) begin
                if (wi < 128) cpl = tk_st[wi] == 2'd0 && tk_wr[2*wi] && tk_wr[2*wi+1] && tk_fill[2*wi] && tk_fill[2*wi+1];
                else cpl = va_st[wi-128] == 2'd0 && va_mask[2*(wi-128)] == 16'hffff && va_mask[2*(wi-128)+1] == 16'hffff;
                wpo = l2port(wb_rel(wi[7:0]));
                if (cpl && n < WBW && !used_pc[wpo] && w_room[wpo]) begin
                    fid_ok = 1'b0; fid = 0;
                    for (wj = NWR - 1; wj >= 0; wj = wj - 1)
                        if (!w_valid[wj] && !used_id[wj]) begin fid_ok = 1'b1; fid = wj[IDW-1:0]; end
                    if (fid_ok) begin
                        for (wk = 0; wk < WBW; wk = wk + 1)
                            if (wk == n) begin wp_v[wk] = 1'b1; wp_sec[wk] = wi[7:0]; wp_id[wk] = fid; wp_pc[wk] = 8'(wpo); end
                        used_pc[wpo] = 1'b1; used_id[fid] = 1'b1;
                        n = n + 1;
                    end
                end
            end
    end
    // pending token data not yet acknowledged
    reg tok_pending, wb_all, tok_unissued, wb_issued_all;
    integer ti;
    always @(*) begin
        tok_pending = 1'b0; wb_all = 1'b1; tok_unissued = 1'b0; wb_issued_all = 1'b1;
        for (ti = 0; ti < 128; ti = ti + 1) begin
            if ((tk_wr[2*ti] || tk_wr[2*ti+1]) && tk_st[ti] != 2'd2) tok_pending = 1'b1;
            if ((tk_wr[2*ti] || tk_wr[2*ti+1]) && tk_st[ti] == 2'd0) tok_unissued = 1'b1;
            if (tk_st[ti] != 2'd2) wb_all = 1'b0;
            if (tk_st[ti] == 2'd0) wb_issued_all = 1'b0;
        end
        for (ti = 0; ti < 8; ti = ti + 1) begin
            if ((va_mask[2*ti] != 0 || va_mask[2*ti+1] != 0) && va_st[ti] != 2'd2) tok_pending = 1'b1;
            if ((va_mask[2*ti] != 0 || va_mask[2*ti+1] != 0) && va_st[ti] == 2'd0) tok_unissued = 1'b1;
            if (va_st[ti] != 2'd2) wb_all = 1'b0;
            if (va_st[ti] == 2'd0) wb_issued_all = 1'b0;
        end
    end
    wire tok_in = |kv_we;

    // ---- landing completion -----------------------------------------------------------------
    reg all_landed;
    integer ci;
    always @(*) begin
        all_landed = 1'b1;
        for (ci = 0; ci < NPC; ci = ci + 1) if (lcnt[ci] != npc(ci, nfill)) all_landed = 1'b0;
    end
    // ---- notice: post the next layer's descriptor once this layer is retired ---------------
    wire layer_retired = !active || (fill_done && wb_all && w_valid == 0 && !tok_in);
    wire want_post = !idl && nx_layer != 8'hff && posted == 8'hff && !go_pend && layer_retired &&
                     !(active && nx_layer == lyr) && pos_hint < WINP && w_valid == 0;
    //: (2) release the posted next layer early: the core is done with this layer's slices, this
    //: layer's fill is done and every token write-back is issued (the tail state is then free)
    wire early_go = early_go_in && !idl && active && pre_lyr == 8'hff && free_seen && posted != 8'hff &&
                    fill_done && wb_issued_all && !tok_in && !go_pend && !start && !d_v;

    // ---- sequential state ------------------------------------------------------------------------
    wire [127:0] tail_lm = (128'd1 << (8 * PL)) - 128'd1;
    reg [1:0] desc_wait;            // a KV descriptor announced, its op not yet allowed
    integer ri, ki;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; gen <= 0; fill_done <= 1'b1; nfill <= 0; lyr <= 8'hff;
            w_valid <= 0; rr <= 0; cyc <= 0;
            fault <= 1'b0; fault_code <= 0;
            tk_fill <= 0; tk_wr <= 0;
            for (ki = 0; ki < 128; ki = ki + 1) tk_st[ki] <= 2'd0;
            for (ki = 0; ki < 16; ki = ki + 1) va_mask[ki] <= 0;
            for (ki = 0; ki < 8; ki = ki + 1) va_st[ki] <= 2'd0;
            for (ki = 0; ki < NPC; ki = ki + 1) lcnt[ki] <= 0;
            st_fill_cycles <= 0; st_fill_sectors <= 0; st_wr_sectors <= 0; st_rsp_stall <= 0;
            st_kvok_low_desc <= 0; st_drain_low <= 0; st_wr_lat_max <= 0; desc_wait <= 0;
            P <= 0; T <= 0; PL <= 0; lbase <= 0; fill_t0 <= 0;
            d_v <= 1'b0; d_row <= 0; d_n <= 0; go <= 1'b0; w_v <= 0; posted <= 8'hff; posted_p <= 0; go_pend <= 1'b0;
            pre_lyr <= 8'hff; pre_p <= 0; free_seen <= 1'b0; start_t <= 0; st_fill_exposed <= 0;
        end else begin
            cyc <= cyc + 1;
            rr <= (rr == NPC - 1) ? 0 : rr + 1'b1;
            d_v <= 1'b0; go <= 1'b0; w_v <= 0;
            // -- notice
            if (want_post && d_rdy && !d_v) begin
                d_v <= 1'b1; d_row <= {11'd0, nx_layer}; d_n <= n_of(pos_hint);
                posted <= nx_layer; posted_p <= pos_hint;
            end
            // -- start without notice: post now, then go (fence: no write-back of an earlier layer outstanding)
            if (go_pend && d_rdy && !d_v && w_valid == 0) begin
                d_v <= 1'b1; d_row <= {11'd0, lyr}; d_n <= nfill; go <= 1'b1; go_pend <= 1'b0;
            end
            // -- kv_free: the core is done with this layer's KV slices
            if (kv_free && active && pre_lyr == 8'hff) free_seen <= 1'b1;
            // -- (2) early release of the next layer's stream: its fill context begins now
            if (early_go) begin
                go <= 1'b1; posted <= 8'hff; pre_lyr <= posted; pre_p <= posted_p; free_seen <= 1'b0;
                gen <= gen + 1'b1; lyr <= posted;
                P <= posted_p; T <= posted_p[NW-1:4]; PL <= posted_p[3:0];
                lbase <= posted * LAYER_SEC;
                nfill <= n_of(posted_p);
                for (ki = 0; ki < NPC; ki = ki + 1) lcnt[ki] <= 0;
                fill_done <= 1'b0; fill_t0 <= cyc;
                tk_fill <= 0; tk_wr <= 0;
                for (ki = 0; ki < 128; ki = ki + 1) tk_st[ki] <= 2'd0;
                for (ki = 0; ki < 16; ki = ki + 1) va_mask[ki] <= 0;
                for (ki = 0; ki < 8; ki = ki + 1) va_st[ki] <= 2'd0;
            end
            if (tok_in && pre_lyr != 8'hff) begin fault <= 1'b1; fault_code[10] <= 1'b1; end   // a token write after the early release
            // -- layer start of a layer whose fill was released early: the context continues
            if (start && pre_lyr != 8'hff) begin
                if (pre_lyr != layer || pre_p != pos) begin fault <= 1'b1; fault_code[11] <= 1'b1; end
                pre_lyr <= 8'hff; free_seen <= 1'b0; start_t <= cyc;
                st_fill_exposed <= fill_done ? 32'd0 : 32'hffffffff;
            end
            // -- layer start
            if (start && pre_lyr == 8'hff) begin
                if (active && (!fill_done || (!idl && (posted_wb_in ? tok_unissued : tok_pending)) ||
                               (!posted_wb_in && w_valid != 0))) begin   // A/B mode writes nothing back
                    fault <= 1'b1; fault_code[0] <= 1'b1;          // previous layer not retired (posted: not issued)
                end
                free_seen <= 1'b0; start_t <= cyc; st_fill_exposed <= 32'hffffffff;
                active <= 1'b1; gen <= gen + 1'b1; lyr <= layer;
                P <= pos; T <= pos[NW-1:4]; PL <= pos[3:0];
                lbase <= layer * LAYER_SEC;
                nfill <= n_of(pos);
                for (ki = 0; ki < NPC; ki = ki + 1) lcnt[ki] <= 0;
                fill_done <= idl; fill_t0 <= cyc;
                tk_fill <= 0; tk_wr <= 0;
                for (ki = 0; ki < 128; ki = ki + 1) tk_st[ki] <= 2'd0;
                for (ki = 0; ki < 16; ki = ki + 1) va_mask[ki] <= 0;
                for (ki = 0; ki < 8; ki = ki + 1) va_st[ki] <= 2'd0;
                if (pos >= WINP) begin fault <= 1'b1; fault_code[1] <= 1'b1; end      // the stream map's window
                if (!idl) begin
                    if (posted == layer && posted_p == pos) begin go <= 1'b1; posted <= 8'hff; end
                    else if (posted == 8'hff && !(want_post && d_rdy && !d_v)) go_pend <= 1'b1;
                    else begin fault <= 1'b1; fault_code[8] <= 1'b1; end          // a notice for another layer/position
                end
            end
            // -- write-back issue
            for (ki = 0; ki < WBW; ki = ki + 1)
                if (wp_v[ki]) begin
                    w_v[wp_pc[ki]] <= 1'b1;
                    w_sec[wp_pc[ki]*24 +: 24] <= lbase + wb_rel(wp_sec[ki]);
                    w_data[wp_pc[ki]*256 +: 256] <= wb_data(wp_sec[ki]);
                    w_tag[wp_pc[ki]*TGW +: TGW] <= {1'b1, gen, wp_id[ki]};
                    w_valid[wp_id[ki]] <= 1'b1; w_gen[wp_id[ki]] <= gen; w_t0[wp_id[ki]] <= cyc;
                    w_sec_e[wp_id[ki]] <= wp_sec[ki]; w_pc[wp_id[ki]] <= wp_pc[ki];
                    if (wp_sec[ki] < 128) tk_st[wp_sec[ki][6:0]] <= 2'd1; else va_st[wp_sec[ki][2:0]] <= 2'd1;
                end
            st_wr_sectors <= st_wr_sectors + $countones(wp_v);
            // -- write-done
            for (ri = 0; ri < NPC; ri = ri + 1)
                if (wd_v[ri]) begin
                    reg [TGW-1:0] tg; reg [IDW-1:0] id;
                    tg = wd_tag[ri*TGW +: TGW]; id = tg[IDW-1:0];
                    if (!tg[TGW-1] || !w_valid[id] || w_gen[id] != tg[IDW +: GENW] || w_pc[id] != 8'(ri)) begin
                        fault <= 1'b1; fault_code[2] <= 1'b1;
                    end else begin
                        w_valid[id] <= 1'b0;
                        //: a write-done of an earlier layer (posted) retires only its entry
                        if (w_gen[id] == gen) begin
                            if (w_sec_e[id] < 128) tk_st[w_sec_e[id][6:0]] <= 2'd2; else va_st[w_sec_e[id][2:0]] <= 2'd2;
                        end
                        if (cyc - w_t0[id] > st_wr_lat_max) st_wr_lat_max <= cyc - w_t0[id];
                    end
                end
            // -- landed beats
            for (ri = 0; ri < NPC; ri = ri + 1)
                if (l_v[ri] && l_pop[ri]) begin
                    if (b_bad[ri]) begin fault <= 1'b1; fault_code[9] <= 1'b1; end
                    else begin
                        lcnt[ri] <= lcnt[ri] + 1'b1;
                        if (b_ktail[ri]) begin
                            reg [16:0] s;
                            s = b_sec[ri];
                            //: lanes < P mod 16 from HBM; the token's lane (and later ones) keep what the
                            //: stream unit wrote (a token write in this same cycle is applied after this)
                            tk_data[{s[15], s[5:0], 1'b0}] <= (l_data[ri*256 +: 128] & tail_lm) |
                                                             (tk_data[{s[15], s[5:0], 1'b0}] & ~tail_lm);
                            tk_data[{s[15], s[5:0], 1'b1}] <= (l_data[ri*256 + 128 +: 128] & tail_lm) |
                                                             (tk_data[{s[15], s[5:0], 1'b1}] & ~tail_lm);
                            tk_fill[{s[15], s[5:0], 1'b0}] <= 1'b1;
                            tk_fill[{s[15], s[5:0], 1'b1}] <= 1'b1;
                        end
                    end
                end else if (l_v[ri]) st_rsp_stall <= st_rsp_stall + 1;
            st_fill_sectors <= st_fill_sectors + $countones(l_v & l_pop & ~b_bad);
            // fill retirement
            if (!fill_done && active && all_landed && !start && !early_go) begin
                fill_done <= 1'b1; st_fill_cycles <= cyc - fill_t0;
                if (pre_lyr == 8'hff) st_fill_exposed <= cyc - start_t;
            end
            // -- token writes: tail / V assembly
            for (li = 0; li < SW; li = li + 1)
                if (l_v_tok[li]) begin
                    reg [AW-5:0] a; reg [16:0] w;
                    a = kv_waddr[li*AW + 4 +: AW-4];
                    if (l_bad[li]) begin fault <= 1'b1; fault_code[3] <= 1'b1; end
                    if (a < KVB) begin
                        tk_data[{a[16], a[6:0]}][8*kv_waddr[li*AW +: 4] +: 8] <= l_code[li];
                        tk_wr[{a[16], a[6:0]}] <= 1'b1;
                        if (tk_st[{a[16], a[6:1]}] != 2'd0) begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                    end else begin
                        w = a - KVB;
                        va_data[{w[16], w[2:0]}][8*kv_waddr[li*AW +: 4] +: 8] <= l_code[li];
                        va_mask[{w[16], w[2:0]}][kv_waddr[li*AW +: 4]] <= 1'b1;
                        if (va_st[{w[16], w[2:1]}] != 2'd0) begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                    end
                end
            if (tok_conflict) begin fault <= 1'b1; fault_code[5] <= 1'b1; end
            if (tok_in && !active) begin fault <= 1'b1; fault_code[6] <= 1'b1; end
            // -- descriptor checks and stall accounting
            if (kvd_v) begin
                desc_wait <= 2'd1;
                if (kvd_pos != P) begin fault <= 1'b1; fault_code[7] <= 1'b1; end
            end else if (kv_ok) desc_wait <= 2'd0;
            if (desc_wait != 0 && !kv_ok) st_kvok_low_desc <= st_kvok_low_desc + 1;
            if (!kv_write_drained) st_drain_low <= st_drain_low + 1;
        end
    end

    assign kv_ok = active && pre_lyr == 8'hff && fill_done && pipe_empty && !tok_in && !fault;
    assign kv_write_drained = (idl || posted_wb_in) ? 1'b1 : (!tok_pending && !tok_in && w_valid == 0);
    assign wb_busy = !idl && (tok_pending || w_valid != 0);
endmodule
