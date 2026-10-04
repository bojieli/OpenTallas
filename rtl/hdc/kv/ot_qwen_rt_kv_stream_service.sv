`timescale 1ns/1ps
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
module ot_qwen_rt_kv_stream_service #(
    parameter integer G        = 6144,
    parameter integer TG       = 4,
    parameter integer SW       = 64,
    parameter integer AW       = 24,
    parameter integer NW       = 18,
    parameter integer NPC      = 32,
    parameter integer HAW      = 24,       // HBM sector address bits
    parameter integer NWR      = 64,       // outstanding writes
    parameter integer FILL_LAT = 8,        // network register stages to the tiles
    parameter integer KV_IDEAL = 0,
    parameter integer WBW      = 1,        // write-backs issued a cycle (distinct PCs)
    parameter integer LPCW     = $clog2(NPC),
    parameter integer IDW      = $clog2(NWR),
    parameter integer TGW      = 1 + 2 + IDW   // tag: {write, generation[1:0], id}
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
    output reg  [31:0]       st_wr_lat_max       // longest write request-to-done, cycles
);
    localparam integer NT = G / TG;
    wire idl = (KV_IDEAL != 0) || ideal_in;
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

    // ---- stream fill state --------------------------------------------------------------------
    function automatic [16:0] s2l(input [14:0] sx);     // stream sector -> layer-relative sector
        s2l = {sx[7], sx[6], 2'b00, sx[14:8], sx[5:0]};
    endfunction
    function automatic [14:0] l2s(input [16:0] lx);
        l2s = {lx[12:6], lx[16], lx[15], lx[5:0]};
    endfunction
    function automatic [10:0] n_of(input [NW-1:0] p);    // sectors a PC streams for position p
        n_of = 11'(({7'd0, p[NW-1:4]} + 1) * 8);
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

    // ---- tail (open K tile) and V assembly ---------------------------------------------
    reg [SHW-1:0] tk_data [0:255];   // [h*128 + d]
    reg [255:0]   tk_fill, tk_wr;
    reg [1:0]     tk_st [0:127];     // sector (h, d/2): 0 idle, 1 sent, 2 acked
    reg [SHW-1:0] va_data [0:15];    // [h*8 + q]
    reg [15:0]    va_mask [0:15];
    reg [1:0]     va_st [0:7];       // sector (h, q/2)
    reg [7:0]     w_sec_e [0:NWR-1];   // write entry -> sector (K: h*64 + d/2, V: 128 + h*4 + q/2)
    reg [5:0]     w_pc  [0:NWR-1];   // write entry -> its PC (acks must come from it)

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
            reg [16:0] s; reg [17:0] a; reg [10:0] c; reg [14:0] sx;
            reg [8:0] t; reg [6:0] d; reg h; reg [16:0] w; reg [12:0] pp; reg [2:0] q;
            reg [255:0] dat; reg [127:0] lm;
            dat = l_data[pi*256 +: 256];
            c = lcnt[pi];
            sx = {c[9:2], 5'(pi), c[1:0]};
            b_rd[pi] = 1'b0; b_bad[pi] = 1'b0; b_drop[pi] = 1'b0; b_n[pi] = 0; b_ktail[pi] = 1'b0;
            b_sec[pi] = 0;
            b_tile[pi][0] = 0; b_tile[pi][1] = 0; b_loc[pi][0] = 0; b_loc[pi][1] = 0;
            b_data[pi][0] = 0; b_data[pi][1] = 0; b_msk[pi][0] = 0; b_msk[pi][1] = 0;
            if (l_v[pi]) begin
                b_rd[pi] = 1'b1;
                //: exactly the next sector of this PC's stream, of this layer's row, inside the window
                if (!active || fill_done || c >= nfill || l_sec[pi*17 +: 17] != s2l(sx) || l_row[pi*8 +: 8] != lyr)
                    b_bad[pi] = 1'b1;
                s = s2l(sx);
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
    always @(*) begin
        reg ok; integer n; integer mj [0:1];
        for (ai = 0; ai < NE; ai = ai + 1) begin e_v[ai] = 1'b0; e_tile[ai] = 0; e_loc[ai] = 0; e_data[ai] = 0; e_msk[ai] = 0; end
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
                    e_v[n] = 1'b1; e_tile[n] = l_tile[ai]; e_loc[n] = l_loc[ai];
                    e_data[n] = {504'd0, l_code[ai]} << l_bit[ai];
                    e_msk[n]  = {504'd0, 8'hff} << l_bit[ai];
                    n = n + 1;
                end
            end
        // beats
        l_pop = 0;
        for (pp_i = 0; pp_i < NPC; pp_i = pp_i + 1) begin
            integer p;
            p = (rr + pp_i) % NPC;
            if (l_v[p]) begin
                if (b_bad[p] || b_drop[p]) l_pop[p] = 1'b1;          // no slice write (a bad beat faults)
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
                        l_pop[p] = 1'b1;
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
    reg [4:0]     wp_pc  [0:WBW-1];
    integer wi, wk, wj;
    always @(*) begin
        reg [NPC-1:0] used_pc; reg [NWR-1:0] used_id; reg cpl; reg [14:0] sx; reg fid_ok; reg [IDW-1:0] fid;
        integer n;
        used_pc = 0; used_id = 0; n = 0;
        for (wk = 0; wk < WBW; wk = wk + 1) begin wp_v[wk] = 1'b0; wp_sec[wk] = 0; wp_id[wk] = 0; wp_pc[wk] = 0; end
        if (!idl && active)
            for (wi = 0; wi < 136; wi = wi + 1) begin
                if (wi < 128) cpl = tk_st[wi] == 2'd0 && tk_wr[2*wi] && tk_wr[2*wi+1] && tk_fill[2*wi] && tk_fill[2*wi+1];
                else cpl = va_st[wi-128] == 2'd0 && va_mask[2*(wi-128)] == 16'hffff && va_mask[2*(wi-128)+1] == 16'hffff;
                sx = l2s(wb_rel(wi[7:0]));
                if (cpl && n < WBW && !used_pc[sx[6:2]] && w_room[sx[6:2]]) begin
                    fid_ok = 1'b0; fid = 0;
                    for (wj = NWR - 1; wj >= 0; wj = wj - 1)
                        if (!w_valid[wj] && !used_id[wj]) begin fid_ok = 1'b1; fid = wj[IDW-1:0]; end
                    if (fid_ok) begin
                        for (wk = 0; wk < WBW; wk = wk + 1)
                            if (wk == n) begin wp_v[wk] = 1'b1; wp_sec[wk] = wi[7:0]; wp_id[wk] = fid; wp_pc[wk] = sx[6:2]; end
                        used_pc[sx[6:2]] = 1'b1; used_id[fid] = 1'b1;
                        n = n + 1;
                    end
                end
            end
    end
    // pending token data not yet acknowledged
    reg tok_pending, wb_all;
    integer ti;
    always @(*) begin
        tok_pending = 1'b0; wb_all = 1'b1;
        for (ti = 0; ti < 128; ti = ti + 1) begin
            if ((tk_wr[2*ti] || tk_wr[2*ti+1]) && tk_st[ti] != 2'd2) tok_pending = 1'b1;
            if (tk_st[ti] != 2'd2) wb_all = 1'b0;
        end
        for (ti = 0; ti < 8; ti = ti + 1) begin
            if ((va_mask[2*ti] != 0 || va_mask[2*ti+1] != 0) && va_st[ti] != 2'd2) tok_pending = 1'b1;
            if (va_st[ti] != 2'd2) wb_all = 1'b0;
        end
    end
    wire tok_in = |kv_we;

    // ---- landing completion -----------------------------------------------------------------
    reg all_landed;
    integer ci;
    always @(*) begin
        all_landed = 1'b1;
        for (ci = 0; ci < NPC; ci = ci + 1) if (lcnt[ci] != nfill) all_landed = 1'b0;
    end
    // ---- notice: post the next layer's descriptor once this layer is retired ---------------
    wire layer_retired = !active || (fill_done && wb_all && w_valid == 0 && !tok_in);
    wire want_post = !idl && nx_layer != 8'hff && posted == 8'hff && !go_pend && layer_retired &&
                     !(active && nx_layer == lyr) && pos_hint < 2048;

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
        end else begin
            cyc <= cyc + 1;
            rr <= (rr == NPC - 1) ? 0 : rr + 1'b1;
            d_v <= 1'b0; go <= 1'b0; w_v <= 0;
            // -- notice
            if (want_post && d_rdy && !d_v) begin
                d_v <= 1'b1; d_row <= {11'd0, nx_layer}; d_n <= n_of(pos_hint);
                posted <= nx_layer; posted_p <= pos_hint;
            end
            // -- start without notice: post now, then go
            if (go_pend && d_rdy && !d_v) begin
                d_v <= 1'b1; d_row <= {11'd0, lyr}; d_n <= nfill; go <= 1'b1; go_pend <= 1'b0;
            end
            // -- layer start
            if (start) begin
                if (active && (!fill_done || (!idl && tok_pending) || w_valid != 0)) begin   // A/B mode writes nothing back
                    fault <= 1'b1; fault_code[0] <= 1'b1;          // previous layer not retired
                end
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
                if (pos >= 2048) begin fault <= 1'b1; fault_code[1] <= 1'b1; end      // the stream map's window
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
                    w_sec_e[wp_id[ki]] <= wp_sec[ki]; w_pc[wp_id[ki]] <= {1'b0, wp_pc[ki]};
                    if (wp_sec[ki] < 128) tk_st[wp_sec[ki][6:0]] <= 2'd1; else va_st[wp_sec[ki][2:0]] <= 2'd1;
                end
            st_wr_sectors <= st_wr_sectors + $countones(wp_v);
            // -- write-done
            for (ri = 0; ri < NPC; ri = ri + 1)
                if (wd_v[ri]) begin
                    reg [TGW-1:0] tg; reg [IDW-1:0] id;
                    tg = wd_tag[ri*TGW +: TGW]; id = tg[IDW-1:0];
                    if (!tg[TGW-1] || !w_valid[id] || w_gen[id] != tg[IDW +: GENW] || w_pc[id] != ri) begin
                        fault <= 1'b1; fault_code[2] <= 1'b1;
                    end else begin
                        w_valid[id] <= 1'b0;
                        if (w_sec_e[id] < 128) tk_st[w_sec_e[id][6:0]] <= 2'd2; else va_st[w_sec_e[id][2:0]] <= 2'd2;
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
            if (!fill_done && active && all_landed && !start) begin
                fill_done <= 1'b1; st_fill_cycles <= cyc - fill_t0;
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

    assign kv_ok = active && fill_done && pipe_empty && !tok_in && !fault;
    assign kv_write_drained = idl ? 1'b1 : (!tok_pending && !tok_in && w_valid == 0);
endmodule
