`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM (DeepSeek-V4.1-Flash, S81 array) Engram lookup engine, one per TP rank
// die of an Engram HOME stage (the 4 rank dies of the stage that runs layer L's
// Engram; design record results/arch/engram_20261008/design.json).
//
// ONE HARDENED ELEMENT for all 8 home dies: the layer and rank are static
// strap inputs (cfg_layer, cfg_rank) that select the column constants (row
// offsets, region column bases) and the 6 columns of the hash output.
//
// PLACEMENT OF THE TABLES (why HBM, why by column).  Layer L's table is 24 hash
// columns of ~16.0 M rows of 264 B (256 E4M3 codes, 1 UE8M0 scale, 7 bytes we
// own).  Rank r of the home stage holds columns r*CPR .. r*CPR+CPR-1 (CPR = 6,
// 25.35 GB) in a load-once region of its own HBM3E stacks.  Every token reads
// exactly ONE row of every column, so each rank reads exactly CPR rows a token:
// the column split is perfectly balanced by construction and needs no hashing
// of the placement.  The other ranks' rows arrive over the TP4 all-gather; the
// row sink (ot_dsrom_engram_rowsink) merges the 24 rows on every rank.
//
// FLOW.  win_* takes one token's n-gram window (4 compressed ids, newest at
// [ID_W-1:0]; pad / dead substitution already applied by ot_dsrom_engram_idwin).
//   1. HASH: the shipped hash unit (ot_hdc_engram_hash_shipped, II 1, latency
//      12) is fed the window oldest first, in_first on the oldest, so its 4th
//      output is the window's hash -- no per-user state on this die.
//   2. ADDRESS: residue = row - offset[c]; byte = BASE + colbase[j] + residue*264
//      (two registered adds); atom = byte >> 5.  Column bases are 32-B aligned
//      and 264 = 8 mod 32, so a row starts at byte 0/8/16/24 of an atom and
//      always spans exactly 9 atoms.
//   3. REQUEST: CPR requests (atom, len 9, tag j) to the HBM controller port,
//      valid/ready.  Responses are 32-B atoms tagged {row j, atom index}; they
//      may arrive in any order and interleaved.  hr_ready is constant 1: a
//      request is only issued into a row buffer that is reserved for it.
//   4. EMIT: rows are emitted in column order once complete, 8 beats each:
//      beat k = codes 32k..32k+31 at [255:0], the row's scale byte at [263:256]
//      on EVERY beat (the sink keeps no per-row state).  Two register stages
//      (atom select, byte shift) feed a 4-entry output FIFO; a beat is only
//      started when the FIFO has room for everything in flight (no stall path
//      through the select / shift registers).
//   5. INTEGRITY: bytes 257..260 of a stored row hold CRC-32/MPEG-2 (poly
//      04C11DB7, init FFFFFFFF, MSB first, no reflection, no xorout) over the
//      256 codes and the scale byte, written at table load.  The engine checks
//      it on emission and sends one status per row (st_valid, st_bad) after
//      the row's last beat; the sink counts 24 statuses before a slot is ready
//      and poisons it on any bad one; fault is sticky.  A wrong address, a bad alignment and a
//      DRAM upset that ECC let through all show up here, never silently.
//
// CREDITS.  Window n lands in prefetch slot n mod NSLOT on every rank (all
// ranks see the same window order).  A window is accepted only when every
// rank's sink has released slot n - NSLOT: rel_valid[r] pulses once per slot
// release of rank r, in slot order (carried back over the TP4 control lane).
//
// Timing (1.2 GHz design rule): every output is a flop; the hash, the 36-bit
// address adds, the 54:1 atom select and the 4:1 byte shift each sit between
// registers; the output head is a register; the CRC update (XOR network over 256 data + 32 state bits) has its
// own stage.  PIPE = 1 (route variant B/C): the atom select reads registered one-hot row/atom selects replicated
// per 64-bit lane group (no index decode and at most 64 x 54 loads per select copy, +1 cycle per beat latency), and
// the CRC is split by linearity, crc(c, d) = crc(c, 0) ^ crc(0, d): the data term (256-bit XOR network) in one
// stage and the 32-bit state term in the next (+1 cycle on the row status only).
// ---------------------------------------------------------------------------
import ot_hdc_engram_tables_shipped_pkg::*;

module ot_dsrom_engram_lookup #(
    parameter integer ROWSTRIPE = 0, // opt-in nine contiguous atoms per PC row
    parameter integer NR    = 4,           // TP ranks
    parameter integer CPR   = 6,           // columns per rank (ENG_COLS / NR)
    parameter integer NSLOT = 2,           // prefetch slots in every sink
    parameter integer ABW   = 36,          // HBM byte address bits (2 stacks, 45 GB)
    parameter [ABW-1:0] BASE = {ABW{1'b0}},// region base (32-B aligned)
    parameter integer PIPE  = 0,           // 1: one-hot replicated atom select (+1 stage), linear-split CRC
    parameter integer SLW   = (NSLOT > 1) ? $clog2(NSLOT) : 1
) (
    input  wire                     clk,
    input  wire                     rst_n,
    // static straps (die-level ties): one hardened element serves all 8 home dies
    input  wire                     cfg_layer,       // Engram layer index (0: layer 1, 1: layer 14)
    input  wire [1:0]               cfg_rank,        // TP rank of this die
    // window (lead flit)
    input  wire                     win_valid,
    output wire                     win_ready,
    input  wire [4*ENG_ID_W-1:0]    win_ids,
    // sink slot releases, one pulse per release, per rank
    input  wire [NR-1:0]            rel_valid,
    // HBM controller request port
    output reg                      hq_valid,
    input  wire                     hq_ready,
    output reg  [ABW-6:0]           hq_atom,
    output wire [3:0]               hq_len,
    output reg  [2:0]               hq_tag,
    // HBM controller response port (32-B atoms)
    input  wire                     hr_valid,
    output wire                     hr_ready,
    input  wire [2:0]               hr_tag,
    input  wire [3:0]               hr_idx,
    input  wire [255:0]             hr_data,
    // row beats to the all-gather and the local sink
    output wire                     o_valid,
    input  wire                     o_ready,
    output wire [4:0]               o_col,
    output wire [2:0]               o_beat,
    output wire [SLW-1:0]           o_slot,
    output wire [263:0]             o_data,
    // integrity
    output reg                      st_valid,        // one status per emitted row
    output reg  [SLW-1:0]           st_slot,
    output reg                      st_bad,          // CRC mismatch on that row
    output reg                      fault
);
    localparam integer RW = ENG_ROW_W, QW = ENG_RES_W;
    localparam integer ATOMS = 9;
    localparam [31:0] POLY = 32'h04C11DB7;
    assign hq_len = ATOMS[3:0];
    assign hr_ready = 1'b1;

    // ---- column constants -----------------------------------------------------------
    function automatic [63:0] col_base(input integer l, input integer rk, input integer j);
        integer i;
        reg [63:0] acc, sz;
        begin
            acc = 64'd0;
            for (i = 0; i < j; i = i + 1) begin
                sz = ENG_PRIME[QW*(l*ENG_COLS + rk*CPR + i) +: QW] * (ROWSTRIPE ? 64'd288 : 64'd264);
                acc = acc + ((sz + 64'd31) & ~64'd31);
            end
            col_base = acc;
        end
    endfunction

    // ---- credits ----------------------------------------------------------------------
    localparam integer CW = 8;
    reg [CW-1:0] acc_n;
    reg [CW-1:0] rel_n [0:NR-1];
    reg          credit_ok;
    integer r;
    always @(*) begin
        credit_ok = 1'b1;
        for (r = 0; r < NR; r = r + 1)
            if ((acc_n - rel_n[r]) >= NSLOT[CW-1:0]) credit_ok = 1'b0;
    end

    // ---- state ------------------------------------------------------------------------
    localparam [2:0] S_IDLE = 3'd0, S_FEED = 3'd1, S_HASH = 3'd2, S_ADDR = 3'd3, S_ISSUE = 3'd4, S_EMIT = 3'd5;
    reg [2:0] st;
    reg [1:0] fcnt;
    reg [4*ENG_ID_W-1:0] ids;
    reg [SLW-1:0] slot;
    reg rdy_q;                               // registered ready: credits only grow between accepts
    assign win_ready = rdy_q;
    wire win_acc = win_valid && rdy_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rdy_q <= 1'b0;
        else rdy_q <= (st == S_IDLE) && !win_acc && credit_ok;
    end
    always @(posedge clk) if (win_acc) ids <= win_ids;

    // ---- hash -------------------------------------------------------------------------
    wire hfeed = (st == S_FEED);
    wire [ENG_ID_W-1:0] hcid = ids[ENG_ID_W*(3 - fcnt) +: ENG_ID_W];
    wire hov;
    wire [RW*ENG_LAYERS*ENG_COLS-1:0] hrow;
    ot_hdc_engram_hash_shipped u_hash (.clk(clk), .rst_n(rst_n), .in_valid(hfeed), .in_first(hfeed && fcnt == 2'd0),
                                       .in_cid(hcid), .out_valid(hov), .out_row(hrow));
    reg [12:1] lastl;                        // marks the 4th feed through the hash latency
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) lastl <= 12'd0;
        else lastl <= {lastl[11:1], hfeed && fcnt == 2'd3};
    end
    wire hdone = hov && lastl[12];

    // ---- address ----------------------------------------------------------------------
    reg [QW-1:0]  res  [0:CPR-1];
    reg [ABW-1:0] r256 [0:CPR-1];
    reg [ABW-1:0] r8   [0:CPR-1];
    reg [ABW-1:0] baddr[0:CPR-1];
    reg [1:0]     acnt;                      // address pipeline step
    // straps registered (static after reset); one-hot of {layer, rank} selects the column constants
    reg [7:0] csel;
    reg [1:0] crank;
    always @(posedge clk) begin
        csel <= 8'd1 << {cfg_layer, cfg_rank};
        crank <= cfg_rank;
    end
    genvar gj, gc;
    generate
        for (gj = 0; gj < CPR; gj = gj + 1) begin : g_col
            reg [RW-1:0]  row_m, off_m;
            reg [ABW-1:0] cb_m;
            reg [RW-1:0]  off_q;
            reg [ABW-1:0] cb_q;
            wire [8*RW-1:0]  rows_c, offs_c;
            wire [8*ABW-1:0] cbs_c;
            for (gc = 0; gc < 8; gc = gc + 1) begin : g_cand          // gc = {layer, rank}
                localparam integer C = (gc / 4) * ENG_COLS + (gc % 4) * CPR + gj;
                localparam [63:0] CB = col_base(gc / 4, gc % 4, gj);
                assign rows_c[RW*gc +: RW]  = hrow[RW*C +: RW];
                assign offs_c[RW*gc +: RW]  = ENG_OFFSET[RW*C +: RW];
                assign cbs_c[ABW*gc +: ABW] = CB[ABW-1:0];
            end
            integer m;
            always @(*) begin
                row_m = {RW{1'b0}}; off_m = {RW{1'b0}}; cb_m = {ABW{1'b0}};
                for (m = 0; m < 8; m = m + 1) begin
                    row_m = row_m | ({RW{csel[m]}} & rows_c[RW*m +: RW]);
                    off_m = off_m | ({RW{csel[m]}} & offs_c[RW*m +: RW]);
                    cb_m  = cb_m  | ({ABW{csel[m]}} & cbs_c[ABW*m +: ABW]);
                end
            end
            always @(posedge clk) begin
                off_q <= off_m;
                cb_q <= BASE + cb_m;
            end
            wire [RW-1:0] lr = row_m - off_q;
            always @(posedge clk) begin
                if (hdone) res[gj] <= lr[QW-1:0];
                if (st == S_ADDR && acnt == 2'd0) begin
                    r256[gj] <= {{(ABW-QW-8){1'b0}}, res[gj], 8'd0};
                    r8[gj]   <= (ROWSTRIPE ? {{(ABW-QW-5){1'b0}},res[gj],5'd0} : {{(ABW-QW-3){1'b0}},res[gj],3'd0}) + cb_q;
                end
                if (st == S_ADDR && acnt == 2'd1) baddr[gj] <= r256[gj] + r8[gj];
            end
        end
    endgenerate

    // ---- row buffers ------------------------------------------------------------------
    reg [255:0] rb [0:CPR-1][0:ATOMS-1];
    reg [3:0]   rcnt [0:CPR-1];
    reg [1:0]   roff [0:CPR-1];             // row start within its first atom, in 8-byte units
    integer j;
    always @(posedge clk) if (hr_valid) rb[hr_tag][hr_idx] <= hr_data;

    // ---- issue ------------------------------------------------------------------------
    reg [2:0] icnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; fcnt <= 2'd0; acnt <= 2'd0; icnt <= 3'd0; hq_valid <= 1'b0;
            acc_n <= {CW{1'b0}}; slot <= {SLW{1'b0}};
            for (r = 0; r < NR; r = r + 1) rel_n[r] <= {CW{1'b0}};
            for (j = 0; j < CPR; j = j + 1) rcnt[j] <= 4'd0;
        end else begin
            for (r = 0; r < NR; r = r + 1) if (rel_valid[r]) rel_n[r] <= rel_n[r] + 1'b1;
            for (j = 0; j < CPR; j = j + 1) if (hr_valid && hr_tag == j[2:0]) rcnt[j] <= rcnt[j] + 1'b1;
            case (st)
                S_IDLE: if (win_acc) begin
                    st <= S_FEED; fcnt <= 2'd0; acc_n <= acc_n + 1'b1;
                end
                S_FEED: begin
                    fcnt <= fcnt + 1'b1;
                    if (fcnt == 2'd3) st <= S_HASH;
                end
                S_HASH: if (hdone) begin st <= S_ADDR; acnt <= 2'd0; end
                S_ADDR: begin
                    acnt <= acnt + 1'b1;
                    if (acnt == 2'd1) begin st <= S_ISSUE; icnt <= 3'd0; end
                end
                S_ISSUE: begin
                    if (!hq_valid || hq_ready) begin
                        if (icnt < CPR[2:0]) begin
                            hq_valid <= 1'b1;
                            hq_atom <= baddr[icnt][ABW-1:5];
                            hq_tag <= icnt;
                            icnt <= icnt + 1'b1;
                        end else begin
                            hq_valid <= 1'b0;
                            st <= S_EMIT;
                        end
                    end
                end
                S_EMIT: if (emit_done) begin
                    st <= S_IDLE;
                    slot <= (slot == NSLOT[SLW-1:0] - 1'b1) ? {SLW{1'b0}} : slot + 1'b1;
                    for (j = 0; j < CPR; j = j + 1) rcnt[j] <= 4'd0;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
    always @(posedge clk) if (st == S_ADDR && acnt == 2'd1)
        for (j = 0; j < CPR; j = j + 1) roff[j] <= r8[j][4:3];   // byte address mod 32 / 8 (r256 is 0 mod 256)

    // ---- emit -------------------------------------------------------------------------
    // E0 issues beat (ej, ek); E1 registers the three atoms; E2 shifts into the FIFO; E3 updates the CRC.
    reg [2:0] ej;
    reg [3:0] ek;                            // 0..7 beats, 8 = row finished
    reg       emit_done_r;
    wire      emit_done = emit_done_r;
    reg [2:0] fifo_n;
    reg       e1_v, e2_v, e0q_v;
    wire      fifo_pop;
    wire      row_ok = (ej < CPR[2:0]) && (rcnt[ej] == ATOMS[3:0]);
    wire      room = ({1'b0, fifo_n} + e1_v + e2_v + e0q_v) < 4'd4;
    wire      e0_go = (st == S_EMIT) && !emit_done_r && row_ok && ek < 4'd8 && room;
    reg [255:0] e1_lo, e1_hi, e1_a8;
    reg [1:0]   e1_off;
    reg [2:0]   e1_j, e1_k;
    reg [SLW-1:0] e1_s, e2_s, e3_s;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ej <= 3'd0; ek <= 4'd0; emit_done_r <= 1'b0; e1_v <= 1'b0; e0q_v <= 1'b0;
        end else begin
            e0q_v <= (PIPE != 0) && e0_go;
            e1_v <= (PIPE != 0) ? e0q_v : e0_go;
            if (st != S_EMIT) begin
                ej <= 3'd0; ek <= 4'd0; emit_done_r <= 1'b0;
            end else if (e0_go) begin
                if (ek == 4'd7) begin
                    ek <= 4'd0;
                    if (ej == CPR[2:0] - 1'b1) emit_done_r <= 1'b1;
                    ej <= ej + 1'b1;
                end else ek <= ek + 1'b1;
            end
        end
    end
    generate
        if (PIPE == 0) begin : g_sel0
            always @(posedge clk) if (e0_go) begin
                e1_lo <= rb[ej][ek];
                e1_hi <= rb[ej][ek + 1'b1];
                e1_a8 <= rb[ej][8];
                e1_off <= roff[ej];
                e1_j <= ej; e1_k <= ek[2:0]; e1_s <= slot;
            end
        end else begin : g_sel1
            // E0q: one-hot selects, one copy per 64-bit lane group
            localparam integer NS = CPR * ATOMS;
            reg [4*NS-1:0] slo, shi, sa8;        // copy g at [NS*g +: NS], bit jj*ATOMS + kk
            reg [4*NS-1:0] nlo, nhi, na8;
            reg [1:0]  q_off;
            reg [2:0]  q_j, q_k;
            reg [SLW-1:0] q_s;
            integer g, jj, kk;
            always @(*) begin
                for (g = 0; g < 4; g = g + 1)
                    for (jj = 0; jj < CPR; jj = jj + 1)
                        for (kk = 0; kk < ATOMS; kk = kk + 1) begin
                            nlo[NS*g + jj*ATOMS + kk] = (ej == jj) && (ek == kk);
                            nhi[NS*g + jj*ATOMS + kk] = (ej == jj) && (ek + 1 == kk);
                            na8[NS*g + jj*ATOMS + kk] = (ej == jj) && (kk == ATOMS - 1);
                        end
            end
            always @(posedge clk) if (e0_go) begin
                slo <= nlo; shi <= nhi; sa8 <= na8;
                q_off <= roff[ej]; q_j <= ej; q_k <= ek[2:0]; q_s <= slot;
            end
            reg [255:0] vlo, vhi, va8;
            always @(*) begin
                vlo = 256'd0; vhi = 256'd0; va8 = 256'd0;
                for (g = 0; g < 4; g = g + 1)
                    for (jj = 0; jj < CPR; jj = jj + 1)
                        for (kk = 0; kk < ATOMS; kk = kk + 1) begin
                            vlo[64*g +: 64] = vlo[64*g +: 64] | ({64{slo[NS*g + jj*ATOMS + kk]}} & rb[jj][kk][64*g +: 64]);
                            vhi[64*g +: 64] = vhi[64*g +: 64] | ({64{shi[NS*g + jj*ATOMS + kk]}} & rb[jj][kk][64*g +: 64]);
                            va8[64*g +: 64] = va8[64*g +: 64] | ({64{sa8[NS*g + jj*ATOMS + kk]}} & rb[jj][kk][64*g +: 64]);
                        end
            end
            always @(posedge clk) if (e0q_v) begin
                e1_lo <= vlo; e1_hi <= vhi; e1_a8 <= va8;
                e1_off <= q_off; e1_j <= q_j; e1_k <= q_k; e1_s <= q_s;
            end
        end
    endgenerate
    // E2: byte shift
    reg [255:0] e2_d;
    reg [7:0]   e2_scale;
    reg [31:0]  e2_crc;
    reg [2:0]   e2_j, e2_k;
    wire [511:0] e1_cat = {e1_hi, e1_lo};
    wire [255:0] e1_a8s = e1_a8 >> {e1_off, 6'd0};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e2_v <= 1'b0;
        else e2_v <= e1_v;
    end
    always @(posedge clk) if (e1_v) begin
        e2_d <= e1_cat[{e1_off, 6'd0} +: 256];
        e2_scale <= e1_a8s[7:0];
        e2_crc <= e1_a8s[39:8];             // bytes 257..260, byte 257 = crc[7:0]
        e2_j <= e1_j; e2_k <= e1_k; e2_s <= e1_s;
    end

    // ---- output FIFO (4 entries) ------------------------------------------------------
    localparam integer FW = 5 + 3 + SLW + 264;
    reg [FW-1:0] fq [0:3];
    reg [1:0] fh, ft;
    wire [4:0] e2_col = crank * CPR + e2_j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fh <= 2'd0; ft <= 2'd0; fifo_n <= 3'd0;
        end else begin
            if (e2_v) ft <= ft + 1'b1;
            if (fifo_pop) fh <= fh + 1'b1;
            fifo_n <= fifo_n + e2_v - fifo_pop;
        end
    end
    always @(posedge clk) if (e2_v) fq[ft] <= {e2_col, e2_k, e2_s, e2_scale, e2_d};
    // registered output head: loaded from the FIFO when empty or taken
    reg          ov;
    reg [FW-1:0] od;
    wire         head_ld = (fifo_n != 3'd0) && (!ov || o_ready);
    assign fifo_pop = head_ld;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else if (!ov || o_ready) ov <= (fifo_n != 3'd0);
    end
    always @(posedge clk) if (head_ld) od <= fq[fh];
    assign o_valid = ov;
    assign {o_col, o_beat, o_slot, o_data} = od;

    // ---- CRC-32/MPEG-2 over the 256 codes and the scale byte --------------------------
    function automatic [31:0] crc_byte(input [31:0] c, input [7:0] b);
        integer i;
        reg [31:0] x;
        begin
            x = c;
            for (i = 7; i >= 0; i = i - 1)
                x = {x[30:0], 1'b0} ^ ((x[31] ^ b[i]) ? POLY : 32'd0);
            crc_byte = x;
        end
    endfunction
    function automatic [31:0] crc_beat(input [31:0] c, input [255:0] d);
        integer i;
        reg [31:0] x;
        begin
            x = c;
            for (i = 0; i < 32; i = i + 1) x = crc_byte(x, d[8*i +: 8]);
            crc_beat = x;
        end
    endfunction
    reg [31:0] crc;
    reg        e3_last;
    reg [7:0]  e3_scale;
    reg [31:0] e3_exp;
    generate
        if (PIPE == 0) begin : g_crc0
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    crc <= 32'hFFFFFFFF; e3_last <= 1'b0;
                end else begin
                    e3_last <= e2_v && e2_k == 3'd7;
                    if (e2_v) crc <= crc_beat((e2_k == 3'd0) ? 32'hFFFFFFFF : crc, e2_d);
                end
            end
            always @(posedge clk) if (e2_v && e2_k == 3'd7) begin e3_scale <= e2_scale; e3_exp <= e2_crc; e3_s <= e2_s; end
        end else begin : g_crc1
            // stage a: data term; stage b: state term ^ data term
            reg [31:0] ga;
            reg        a_v, a_first, a_last;
            reg [7:0]  a_scale;
            reg [31:0] a_exp;
            reg [SLW-1:0] a_s;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin a_v <= 1'b0; a_last <= 1'b0; crc <= 32'hFFFFFFFF; e3_last <= 1'b0; end
                else begin
                    a_v <= e2_v;
                    a_last <= e2_v && e2_k == 3'd7;
                    e3_last <= a_last;
                    if (a_v) crc <= crc_beat(a_first ? 32'hFFFFFFFF : crc, 256'd0) ^ ga;
                end
            end
            always @(posedge clk) if (e2_v) begin
                ga <= crc_beat(32'd0, e2_d);
                a_first <= (e2_k == 3'd0);
                a_scale <= e2_scale; a_exp <= e2_crc; a_s <= e2_s;
            end
            always @(posedge clk) if (a_last) begin e3_scale <= a_scale; e3_exp <= a_exp; e3_s <= a_s; end
        end
    endgenerate
    // final: fold the scale byte and compare
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st_valid <= 1'b0; st_slot <= {SLW{1'b0}}; st_bad <= 1'b0; fault <= 1'b0;
        end else begin
            st_valid <= e3_last;
            if (e3_last) begin
                st_slot <= e3_s;
                st_bad <= (crc_byte(crc, e3_scale) != e3_exp);
                if (crc_byte(crc, e3_scale) != e3_exp) fault <= 1'b1;
            end
        end
    end
endmodule
