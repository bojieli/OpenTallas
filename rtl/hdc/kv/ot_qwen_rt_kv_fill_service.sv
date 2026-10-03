`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die (W12, TP4, G = 6,144): the KV memory service of the
// REAL_MEM runtime (default-off; selected only by the REAL_MEM die
// rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_rm.sv).
//
// It drives the core's KV readiness from real memory, replacing the tied-high
// kv_ok / kv_write_drained of the retained runtime:
//
//   HBM (ot_qwen_hbm_model_ack: per-pseudo-channel queues, bank/row timing,
//        refresh, reordering, finite return queues, WR_ACK write-done)
//     |  32-byte sectors, tagged requests {kind, generation, id}
//   this service: per-layer FILL of the layer's KV window into the tiles' KV
//     |  slices, write-through of the token's new K/V with exact completion
//   tile KV slices (ot_qwen_rom_tile_w12: 2 x ot_sram_1r1w_128x256 per tile,
//        E4M3 codes, written through the tile's registered kvw_* port) -- the
//        hardened element's own memories; the engine reads them in place.
//
// SERVICE BOUNDARY (the swap point for a near-HBM attention path): the core's
// KV interface only -- kvd_* descriptor + kv_ok, the stream unit's element
// writes kv_we/kv_waddr/kv_wdata + kv_write_drained, start/pos/layer.  A
// near-HBM unit replaces this module and the tiles' KV slices; ROM, scale,
// embedding and vector memories are wired independently of it.
//
// LAYOUT (tools/hdc_qwen_fullshape_program_w12.py LayerZero, KV = 2 heads/die):
//   K word a = h*2^16 + t*128 + d   (16 position lanes of position tile t)
//   V word a = VB + h*2^16 + p*8 + q (16 dims of position p, dim tile q)
// HBM: layer n's window at sector n * 2^17; sector s holds words 2s (bits
// 127:0) and 2s+1 (255:128), each 16 E4M3 codes, lane l at bits 8l.
// SLICE MAP (rtl/hdc/ot_qwen_rom_tile_w12.sv, KV_LOCAL = 1, proven one-to-one
// by tools/qwen_o4_kv_slice_map_w12.py):
//   K (h,t,d):  tile (t mod 48)*32 + d/4, group d mod 4, local (t/48)*2 + h
//   V (h,p,q):  tile q*128 + (p mod 512)/4, group p mod 4, local 22 + (p/512)*2 + h
//
// FILL: at each layer start (start pulse: pos P, layer n) the window's K tiles
// 0..P/16 and V positions 0..P-1 are read (requests of up to RLEN sectors),
// every response beat identified by its tag (table entry, generation, beat
// bitmap: duplicate, stale or unknown beats fault) and written to its slice
// word.  The open K tile (P/16) is also captured whole into the TAIL buffer
// and its slice write masks out lanes >= P mod 16 (the token's own lane comes
// from the stream unit, so fill and token writes are disjoint).
// TOKEN WRITES: each K/V element the stream unit writes (must be position P,
// an exact E4M3 value) goes to its slice lane and to the tail (K) or the V
// assembly buffer; a sector whose words are complete (and, for K, filled) is
// written to HBM with a tagged write and retired only on its write-done.
// kv_ok           = fill retired and every slice write (fill and token) landed
// kv_write_drained = no token K/V data that HBM has not acknowledged
// Network: up to NPC beats a cycle; one slice write per tile per cycle (a beat
// whose tile is taken waits: back-pressure on its pseudo-channel port), token
// writes first; FILL_LAT register stages to the tiles, + the tile's own
// input register, then the SRAM write edge.
//
// KV_IDEAL = 1 or ideal_in (A/B reference only): no HBM; kv_write_drained = 1 and
// kv_ok = token writes landed; the host preloads the slices directly.
// ---------------------------------------------------------------------------
module ot_qwen_rt_kv_fill_service #(
    parameter integer G        = 6144,
    parameter integer TG       = 4,
    parameter integer SW       = 64,
    parameter integer AW       = 24,
    parameter integer NW       = 18,
    parameter integer NPC      = 32,
    parameter integer HAW      = 24,       // HBM sector address bits
    parameter integer RLEN     = 16,       // fill request length, sectors (power of 2)
    parameter integer NRD      = 64,       // outstanding fill reads (table entries, a power of 2)
    parameter integer NWR      = 64,       // outstanding writes
    parameter integer FILL_LAT = 8,        // network register stages to the tiles
    parameter integer KV_IDEAL = 0,
    parameter integer LKA      = 8,        // fill lookahead window, request units
    parameter integer LPCW     = $clog2(NPC),
    parameter integer IDW      = $clog2(NRD > NWR ? NRD : NWR),
    parameter integer TGW      = 1 + 2 + IDW   // tag: {write, generation[1:0], id}
) (
    input  wire              clk,
    input  wire              rst_n,
    // layer start
    input  wire              start,
    input  wire              ideal_in,    // A/B reference at run time (as KV_IDEAL = 1)
    input  wire [NW-1:0]     pos,
    input  wire [7:0]        layer,
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
    // HBM request / response (ot_qwen_hbm_model_ack)
    output reg               h_req_v,
    input  wire              h_req_rdy,
    input  wire [NPC-1:0]    h_pc_room,   // per pseudo-channel queue room (controller, one cycle stale)
    output reg               h_req_we,
    output reg  [HAW-1:0]    h_req_addr,
    output reg  [$clog2(RLEN):0] h_req_len,
    output reg  [TGW-1:0]    h_req_tag,
    output reg  [255:0]      h_req_wdata,
    input  wire [NPC-1:0]    h_rsp_v,
    output reg  [NPC-1:0]    h_rsp_rdy,
    input  wire [NPC*TGW-1:0] h_rsp_tag,
    input  wire [NPC*$clog2(RLEN)-1:0] h_rsp_beat,
    input  wire [NPC*256-1:0] h_rsp_data,
    input  wire [NPC-1:0]    h_rsp_wr,
    // status
    output reg               fault,
    output reg  [15:0]       fault_code,
    output reg  [31:0]       st_fill_cycles,     // start to fill retired (last layer)
    output reg  [31:0]       st_fill_sectors,
    output reg  [31:0]       st_wr_sectors,
    output reg  [31:0]       st_rsp_stall,       // port-cycles a beat waited on a tile conflict
    output reg  [31:0]       st_kvok_low_desc,   // cycles a KV descriptor waited with kv_ok low
    output reg  [31:0]       st_drain_low,       // cycles kv_write_drained was low
    output reg  [31:0]       st_wr_lat_max       // longest write request-to-done, cycles
);
    localparam integer NT = G / TG;
    wire idl = (KV_IDEAL != 0) || ideal_in;
    localparam integer LBK = $clog2(RLEN);
    localparam integer KVB = 131072;           // first V word
    localparam integer KL = 22;                // K slice words: ceil(512/48) rounds x 2 heads
    localparam integer LAYER_SEC = 131072;     // sectors a layer window occupies
    localparam integer NE = SW + 2 * NPC;      // slice-write entries a cycle
    localparam integer GENW = 2;
    localparam integer SHW = 128;              // half a sector: one word

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

    // ---- fill walker: 4 segments (K h0, K h1, V h0, V h1) ------------------------------
    reg [1:0]     seg;
    reg           walk_v;            // requests remain
    reg [17:0]    w_next;            // next sector (layer-relative)
    reg [17:0]    w_end;             // segment end (exclusive)
    reg [31:0]    fill_t0;
    reg           fill_done;
    reg  [NRD-1:0] r_valid;
    reg  [GENW-1:0] r_gen [0:NRD-1];
    reg  [16:0]   r_base [0:NRD-1];
    reg  [LBK:0]  r_len  [0:NRD-1];
    reg  [RLEN-1:0] r_got [0:NRD-1];
    reg  [NWR-1:0] w_valid;
    reg  [GENW-1:0] w_gen [0:NWR-1];
    reg  [31:0]   w_t0 [0:NWR-1];
    reg  [31:0]   cyc;

    // segment bounds for P: K tiles 0..T (T+1)*64 sectors a head; V positions 0..P-1: P*4 sectors a head
    function automatic [35:0] seg_bounds(input [1:0] sg, input [NW-1:0] p);   // {start, end} layer-relative sectors
        reg [17:0] s0, n;
        begin
            case (sg)
                2'd0: begin s0 = 18'd0;                n = ({9'd0, p[NW-1:4]} + 18'd1) * 18'd64; end
                2'd1: begin s0 = 18'd32768;            n = ({9'd0, p[NW-1:4]} + 18'd1) * 18'd64; end
                2'd2: begin s0 = 18'd65536;            n = p[13:0] * 18'd4; end
                default: begin s0 = 18'd98304;         n = p[13:0] * 18'd4; end
            endcase
            seg_bounds = {s0, s0 + n};
        end
    endfunction

    // free table entries
    reg [IDW-1:0] r_free_id, w_free_id;
    reg           r_free_any, w_free_any;
    integer fi;
    always @(*) begin
        r_free_any = 1'b0; r_free_id = 0;
        for (fi = NRD - 1; fi >= 0; fi = fi - 1) if (!r_valid[fi]) begin r_free_any = 1'b1; r_free_id = fi[IDW-1:0]; end
        w_free_any = 1'b0; w_free_id = 0;
        for (fi = NWR - 1; fi >= 0; fi = fi - 1) if (!w_valid[fi]) begin w_free_any = 1'b1; w_free_id = fi[IDW-1:0]; end
    end

    // ---- tail (open K tile) and V assembly ---------------------------------------------
    reg [SHW-1:0] tk_data [0:255];   // [h*128 + d]
    reg [255:0]   tk_fill, tk_wr;
    reg [1:0]     tk_st [0:127];     // sector (h, d/2): 0 idle, 1 sent, 2 acked
    reg [SHW-1:0] va_data [0:15];    // [h*8 + q]
    reg [15:0]    va_mask [0:15];
    reg [1:0]     va_st [0:7];       // sector (h, q/2)
    reg [7:0]     w_sec [0:NWR-1];   // write entry -> sector (K: h*64 + d/2, V: 128 + h*4 + q/2)

    // ---- token (stream-unit) writes: per lane decode ------------------------------------
    // one slice write per lane, merged per tile below
    reg [SW-1:0]   l_v;
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
            l_v[li] = kv_we[li];
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

    // ---- response beats: decode and per-port slice writes --------------------------------
    reg [NPC-1:0]  b_rd, b_wrack, b_bad;
    reg [16:0]     b_sec [0:NPC-1];
    reg [1:0]      b_n   [0:NPC-1];           // slice writes of the beat (1 K, 2 V)
    reg [10:0]     b_tile [0:NPC-1][0:1];
    reg [6:0]      b_loc  [0:NPC-1][0:1];
    reg [511:0]    b_data [0:NPC-1][0:1];
    reg [511:0]    b_msk  [0:NPC-1][0:1];
    reg [NPC-1:0]  b_ktail;                   // the beat's words belong to the open K tile
    integer pi;
    always @(*) begin
        for (pi = 0; pi < NPC; pi = pi + 1) begin
            reg [TGW-1:0] tg; reg [LBK-1:0] bt; reg [IDW-1:0] id; reg [16:0] s; reg [17:0] a;
            reg [8:0] t; reg [6:0] d; reg h; reg [16:0] w; reg [12:0] pp; reg [2:0] q;
            reg [255:0] dat; reg [127:0] lm;
            tg = h_rsp_tag[pi*TGW +: TGW]; bt = h_rsp_beat[pi*LBK +: LBK]; id = tg[IDW-1:0];
            dat = h_rsp_data[pi*256 +: 256];
            b_rd[pi] = 1'b0; b_wrack[pi] = 1'b0; b_bad[pi] = 1'b0; b_n[pi] = 0; b_ktail[pi] = 1'b0;
            b_sec[pi] = 0;
            b_tile[pi][0] = 0; b_tile[pi][1] = 0; b_loc[pi][0] = 0; b_loc[pi][1] = 0;
            b_data[pi][0] = 0; b_data[pi][1] = 0; b_msk[pi][0] = 0; b_msk[pi][1] = 0;
            if (h_rsp_v[pi]) begin
                if (h_rsp_wr[pi]) begin
                    b_wrack[pi] = 1'b1;
                    if (!tg[TGW-1] || !w_valid[id] || w_gen[id] != tg[IDW +: GENW] || bt != 0) b_bad[pi] = 1'b1;
                end else begin
                    b_rd[pi] = 1'b1;
                    if (tg[TGW-1] || !r_valid[id] || r_gen[id] != tg[IDW +: GENW] || {1'b0, bt} >= r_len[id] || r_got[id][bt])
                        b_bad[pi] = 1'b1;
                    s = r_base[id] + bt;
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
    always @(*) begin
        reg ok; integer n; integer mj [0:1];
        for (ai = 0; ai < NE; ai = ai + 1) begin e_v[ai] = 1'b0; e_tile[ai] = 0; e_loc[ai] = 0; e_data[ai] = 0; e_msk[ai] = 0; end
        tok_conflict = 1'b0;
        n = 0;
        // token lanes merged per tile (same tile => same local word, else a protocol fault)
        for (ai = 0; ai < SW; ai = ai + 1)
            if (l_v[ai]) begin
                ok = 1'b0;
                for (aj = 0; aj < SW; aj = aj + 1)
                    if (aj < n && e_v[aj] && e_tile[aj] == l_tile[ai]) begin
                        ok = 1'b1;
                        if (e_loc[aj] != l_loc[ai]) tok_conflict = 1'b1;
                        e_data[aj] = e_data[aj] | ({504'd0, l_code[ai]} << l_bit[ai]);
                        e_msk[aj]  = e_msk[aj]  | ({504'd0, 8'hff} << l_bit[ai]);
                    end
                if (!ok) begin
                    e_v[n] = 1'b1; e_tile[n] = l_tile[ai]; e_loc[n] = l_loc[ai];
                    e_data[n] = {504'd0, l_code[ai]} << l_bit[ai];
                    e_msk[n]  = {504'd0, 8'hff} << l_bit[ai];
                    n = n + 1;
                end
            end
        // beats
        h_rsp_rdy = 0;
        for (pp_i = 0; pp_i < NPC; pp_i = pp_i + 1) begin
            integer p;
            p = (rr + pp_i) % NPC;
            if (h_rsp_v[p]) begin
                if (b_wrack[p] || b_bad[p]) h_rsp_rdy[p] = 1'b1;     // no slice write (a bad beat faults)
                else begin
                    //: a tile takes one SRAM write a cycle: a beat may join an entry for the SAME slice
                    //: word with disjoint lanes (write combining), else it waits (back-pressure)
                    ok = 1'b1;
                    for (ak = 0; ak < 2; ak = ak + 1) begin
                        mj[ak] = -1;
                        if (ak < b_n[p])
                            for (aj = 0; aj < NE; aj = aj + 1)
                                if (e_v[aj] && e_tile[aj] == b_tile[p][ak]) begin
                                    if (aj >= SW && e_loc[aj] == b_loc[p][ak] && (e_msk[aj] & b_msk[p][ak]) == 0) mj[ak] = aj;
                                    else ok = 1'b0;
                                end
                    end
                    if (ok) begin
                        h_rsp_rdy[p] = 1'b1;
                        for (ak = 0; ak < 2; ak = ak + 1)
                            if (ak < b_n[p]) begin
                                if (mj[ak] >= 0) begin
                                    e_data[mj[ak]] = e_data[mj[ak]] | b_data[p][ak];
                                    e_msk[mj[ak]]  = e_msk[mj[ak]]  | b_msk[p][ak];
                                end else begin
                                    e_v[SW + 2 * p + ak] = 1'b1;
                                    e_tile[SW + 2 * p + ak] = b_tile[p][ak]; e_loc[SW + 2 * p + ak] = b_loc[p][ak];
                                    e_data[SW + 2 * p + ak] = b_data[p][ak]; e_msk[SW + 2 * p + ak] = b_msk[p][ak];
                                end
                            end
                    end
                end
            end
        end
    end

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

    // ---- write-back selection: the lowest complete, unsent sector ------------------------
    reg        wb_any;
    reg [7:0]  wb_sec;               // 0..127 K (h*64 + d/2), 128..135 V (128 + h*4 + q/2)
    integer wi;
    always @(*) begin
        wb_any = 1'b0; wb_sec = 0;
        for (wi = 135; wi >= 0; wi = wi - 1) begin
            if (wi < 128) begin
                if (tk_st[wi] == 2'd0 && tk_wr[2*wi] && tk_wr[2*wi+1] && tk_fill[2*wi] && tk_fill[2*wi+1]) begin
                    wb_any = 1'b1; wb_sec = wi[7:0];
                end
            end else if (va_st[wi-128] == 2'd0 && va_mask[2*(wi-128)] == 16'hffff && va_mask[2*(wi-128)+1] == 16'hffff) begin
                wb_any = 1'b1; wb_sec = wi[7:0];
            end
        end
    end
    // pending token data not yet acknowledged
    reg tok_pending;
    integer ti;
    always @(*) begin
        tok_pending = 1'b0;
        for (ti = 0; ti < 128; ti = ti + 1)
            if ((tk_wr[2*ti] || tk_wr[2*ti+1]) && tk_st[ti] != 2'd2) tok_pending = 1'b1;
        for (ti = 0; ti < 8; ti = ti + 1)
            if ((va_mask[2*ti] != 0 || va_mask[2*ti+1] != 0) && va_st[ti] != 2'd2) tok_pending = 1'b1;
    end
    wire tok_in = |kv_we;

    // ---- request port -------------------------------------------------------------------------
    wire req_free = !h_req_v || h_req_rdy;
    wire do_wb   = (!idl) && active && req_free && wb_any && w_free_any;
    // Fill lookahead: the next LKA request units (RLEN sectors each) of the segment; the first whose
    // pseudo-channels all report room (h_pc_room, the controller's per-channel queue state) is issued,
    // so a channel held by a refresh backs up only its own requests (an in-order walker stalls the
    // whole fill behind it: measured 3.4x slower).  The window slides past issued leading units.
    function automatic integer pc_of(input [HAW-1:0] sa);
        pc_of = ((sa >> 2) ^ (sa >> (2 + LPCW)) ^ (sa >> (2 + 2 * LPCW))) & (NPC - 1);
    endfunction
    reg [LKA-1:0] u_done;
    reg           f_pick_v;
    reg [$clog2(LKA)-1:0] f_pick;
    reg [17:0]    f_addr;
    reg [LBK:0]   f_len;
    integer ui, uj;
    always @(*) begin
        f_pick_v = 1'b0; f_pick = 0; f_addr = w_next; f_len = 0;
        for (ui = LKA - 1; ui >= 0; ui = ui - 1) begin
            reg [17:0] a; reg [17:0] rem; reg [LBK:0] ln; reg ok;
            a = w_next + ui * RLEN;
            rem = w_end - a;
            ln = (rem > RLEN) ? RLEN[LBK:0] : rem[LBK:0];
            ok = (a < w_end) && !u_done[ui];
            for (uj = 0; uj < RLEN / 4; uj = uj + 1)
                if (uj * 4 < ln && !h_pc_room[pc_of(lbase + a + uj * 4)]) ok = 1'b0;
            if (ok) begin f_pick_v = 1'b1; f_pick = ui[$clog2(LKA)-1:0]; f_addr = a; f_len = ln; end
        end
    end
    wire do_fill = (!idl) && active && req_free && !do_wb && walk_v && r_free_any && f_pick_v;
    wire [LKA-1:0] u_now = u_done | (do_fill ? (LKA'(1) << f_pick) : {LKA{1'b0}});
    reg [$clog2(LKA):0] u_lead;
    integer uk;
    always @(*) begin
        u_lead = 0;
        for (uk = LKA - 1; uk >= 0; uk = uk - 1) if (!u_now[uk]) u_lead = uk;
        if (&u_now) u_lead = LKA;
    end
    wire [17:0] w_slid = w_next + u_lead * RLEN;
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

    // beats accepted this cycle, per read entry (several pseudo-channels can complete one request together)
    reg [RLEN-1:0] got_add [0:NRD-1];
    integer gi2;
    always @(*) begin
        for (gi2 = 0; gi2 < NRD; gi2 = gi2 + 1) got_add[gi2] = 0;
        for (gi2 = 0; gi2 < NPC; gi2 = gi2 + 1)
            if (h_rsp_v[gi2] && h_rsp_rdy[gi2] && b_rd[gi2] && !b_bad[gi2])
                got_add[h_rsp_tag[gi2*TGW +: IDW]] = got_add[h_rsp_tag[gi2*TGW +: IDW]] |
                                                   (RLEN'(1) << h_rsp_beat[gi2*LBK +: LBK]);
    end

    // ---- sequential state ------------------------------------------------------------------------
    wire [127:0] tail_lm = (128'd1 << (8 * PL)) - 128'd1;
    reg [1:0] desc_wait;            // a KV descriptor announced, its op not yet allowed
    integer ri, ki;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; gen <= 0; walk_v <= 1'b0; fill_done <= 1'b1; seg <= 0; u_done <= 0;
            r_valid <= 0; w_valid <= 0; h_req_v <= 1'b0; rr <= 0; cyc <= 0;
            fault <= 1'b0; fault_code <= 0;
            tk_fill <= 0; tk_wr <= 0;
            for (ki = 0; ki < 128; ki = ki + 1) tk_st[ki] <= 2'd0;
            for (ki = 0; ki < 16; ki = ki + 1) va_mask[ki] <= 0;
            for (ki = 0; ki < 8; ki = ki + 1) va_st[ki] <= 2'd0;
            st_fill_cycles <= 0; st_fill_sectors <= 0; st_wr_sectors <= 0; st_rsp_stall <= 0;
            st_kvok_low_desc <= 0; st_drain_low <= 0; st_wr_lat_max <= 0; desc_wait <= 0;
            P <= 0; T <= 0; PL <= 0; lbase <= 0; fill_t0 <= 0;
        end else begin
            cyc <= cyc + 1;
            rr <= (rr == NPC - 1) ? 0 : rr + 1'b1;
            // -- layer start
            if (start) begin
                if (active && (!fill_done || (!idl && tok_pending) || w_valid != 0 || r_valid != 0)) begin   // A/B mode writes nothing back
                    fault <= 1'b1; fault_code[0] <= 1'b1;          // previous layer not retired
                end
                active <= 1'b1; gen <= gen + 1'b1;
                P <= pos; T <= pos[NW-1:4]; PL <= pos[3:0];
                lbase <= layer * LAYER_SEC;
                seg <= 0; {w_next, w_end} <= seg_bounds(2'd0, pos); u_done <= 0;
                walk_v <= (!idl); fill_done <= idl; fill_t0 <= cyc;
                tk_fill <= 0; tk_wr <= 0;
                for (ki = 0; ki < 128; ki = ki + 1) tk_st[ki] <= 2'd0;
                for (ki = 0; ki < 16; ki = ki + 1) va_mask[ki] <= 0;
                for (ki = 0; ki < 8; ki = ki + 1) va_st[ki] <= 2'd0;
                if (pos >= 8192) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            end
            // -- request issue
            if (req_free) h_req_v <= 1'b0;
            if (do_wb) begin
                h_req_v <= 1'b1; h_req_we <= 1'b1; h_req_len <= 1;
                h_req_addr <= lbase + wb_rel(wb_sec);
                h_req_tag <= {1'b1, gen, w_free_id};
                h_req_wdata <= wb_data(wb_sec);
                w_valid[w_free_id] <= 1'b1; w_gen[w_free_id] <= gen; w_t0[w_free_id] <= cyc; w_sec[w_free_id] <= wb_sec;
                if (wb_sec < 128) tk_st[wb_sec[6:0]] <= 2'd1; else va_st[wb_sec[2:0]] <= 2'd1;
                st_wr_sectors <= st_wr_sectors + 1;
            end else if (do_fill) begin
                h_req_v <= 1'b1; h_req_we <= 1'b0; h_req_len <= f_len;
                h_req_addr <= lbase + f_addr;
                h_req_tag <= {1'b0, gen, r_free_id};
                r_valid[r_free_id] <= 1'b1; r_gen[r_free_id] <= gen; r_base[r_free_id] <= f_addr[16:0];
                r_len[r_free_id] <= f_len; r_got[r_free_id] <= 0;
                st_fill_sectors <= st_fill_sectors + f_len;
            end
            // window slide / next segment
            if (walk_v && !start) begin
                if (w_slid >= w_end) begin
                    u_done <= 0;
                    if (seg == 2'd3) walk_v <= 1'b0;
                    else begin seg <= seg + 1'b1; {w_next, w_end} <= seg_bounds(seg + 1'b1, P); end
                end else begin
                    w_next <= w_slid;
                    u_done <= u_now >> u_lead;
                end
            end
            // -- responses
            for (ri = 0; ri < NPC; ri = ri + 1)
                if (h_rsp_v[ri] && h_rsp_rdy[ri]) begin
                    reg [IDW-1:0] id; reg [LBK-1:0] bt;
                    id = h_rsp_tag[ri*TGW +: IDW]; bt = h_rsp_beat[ri*LBK +: LBK];
                    if (b_bad[ri]) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
                    else if (b_wrack[ri]) begin
                        w_valid[id] <= 1'b0;
                        if (w_sec[id] < 128) tk_st[w_sec[id][6:0]] <= 2'd2; else va_st[w_sec[id][2:0]] <= 2'd2;
                        if (cyc - w_t0[id] > st_wr_lat_max) st_wr_lat_max <= cyc - w_t0[id];
                    end else begin
                        r_got[id] <= r_got[id] | got_add[id];
                        if ((r_got[id] | got_add[id]) == RLEN'((32'd1 << r_len[id]) - 32'd1)) r_valid[id] <= 1'b0;
                        if (b_ktail[ri]) begin
                            reg [16:0] s;
                            s = b_sec[ri];
                            //: lanes < P mod 16 from HBM; the token's lane (and later ones) keep what the
                            //: stream unit wrote (a token write in this same cycle is applied after this)
                            tk_data[{s[15], s[5:0], 1'b0}] <= (h_rsp_data[ri*256 +: 128] & tail_lm) |
                                                             (tk_data[{s[15], s[5:0], 1'b0}] & ~tail_lm);
                            tk_data[{s[15], s[5:0], 1'b1}] <= (h_rsp_data[ri*256 + 128 +: 128] & tail_lm) |
                                                             (tk_data[{s[15], s[5:0], 1'b1}] & ~tail_lm);
                            tk_fill[{s[15], s[5:0], 1'b0}] <= 1'b1;
                            tk_fill[{s[15], s[5:0], 1'b1}] <= 1'b1;
                        end
                    end
                end else if (h_rsp_v[ri]) st_rsp_stall <= st_rsp_stall + 1;
            // fill retirement
            if (!fill_done && !walk_v && r_valid == 0 && active) begin
                fill_done <= 1'b1; st_fill_cycles <= cyc - fill_t0;
            end
            // -- token writes: tail / V assembly
            for (li = 0; li < SW; li = li + 1)
                if (l_v[li]) begin
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

    assign kv_ok = active && fill_done && pipe_empty && !tok_in && !fault;
    assign kv_write_drained = idl ? 1'b1 : (!tok_pending && !tok_in && w_valid == 0);
endmodule
