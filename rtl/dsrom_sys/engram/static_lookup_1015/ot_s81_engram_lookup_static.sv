`timescale 1ns/1ps
// Real source-derived 14-root static lookup successor. The compiler supplies
// RETURN_AGE from its proved external service bound; this parameter is not a
// memory model or performance qualification. All six rows are reserved at
// launch. Every on-chip request/output slot is unconditional. Missing, stale,
// duplicate or late external atoms poison the fixed return instead of retrying.
// No normal ready/credit signals or dynamically shifted output slots exist.
// 2026-10-16 (S-ENGRAM, static14 gate re-time): the hash is ot_s81_engram_hash_static (residues selected
// directly, no row-minus-offset subtract across the column->core roots); accepted response atoms are
// registered in the core root as one-hot (bank, atom) write enables + data and written one cycle later by
// the row-root leaf (flop-to-flop root crossing), so emission starts at RETURN_AGE+1 (+1 cycle on every
// output beat and status; the HBM response window age < RETURN_AGE is unchanged).
// 2026-10-16 (STATIC14 cross-root hold; st3-main0600-b64134583 EARLY_FAIL_HOLD at CTS, -164 ps hash->core,
// 23,324 hold endpoints): every clock-root crossing except the row read is a flop-to-flop HALF-CYCLE hop, a
// negative-edge register of the launching root feeding a positive-edge register of the capturing root (hold margin
// ~T/2 against the 100 ps inter-entry reserve, no hold buffers):
//   core -> seed : the core forms the hash window from ids (win_n, ck negedge) -> hash w (ck_seed posedge);
//   seed -> hash : roll_s -> roll_n (ck_seed negedge) -> roll_h (column posedge), inside the hash;
//   hash -> core : res_n (column negedge) -> res_c (ck posedge) -> the 8:1 strap select -> res[];
//   seed -> core : removed (hdone = lastl[12]; the hash valid pipe was redundant with it);
//   rows -> core : (st6) core negedge {hit, ek} per bank -> row posedge h_b -> row posedge atom select b* (full cycle in
//                  the row root) -> core negedge c* -> OR of six banks into e1 on the core posedge; +1 read cycle;
//   core -> rows : (st8) wen_q/wdata_q -> per-bank wx_en/wx_d (ck POSEDGE, a full-cycle registered copy per bank) ->
//                  leaf we_q/wd_q (row posedge, full-cycle root crossing) -> payload: no half-cycle on the write path
//                  (st7 gate: core->rows was the binding class, -53.4 TT placement / -91.1 related, two tile-wide
//                  half-cycles).  +1 write cycle: payload visible at age <= RETURN_AGE+3, emission from RETURN_AGE+2
//                  (+1 on every output beat and status; the Engram lookup is lookahead, priced 0 like st6).
// Requests keep their cycles; st6 adds +1 cycle to every row beat and status (row read hop).
import ot_hdc_engram_tables_shipped_pkg::*;

module ot_s81_engram_lookup_static #(
    parameter integer RETURN_AGE = 0,
    parameter integer ROWSTRIPE = 0, // opt-in nine contiguous atoms per PC row
    parameter integer NR    = 4,           // TP ranks
    parameter integer CPR   = 6,           // columns per rank (ENG_COLS / NR)
    parameter integer NSLOT = 2,           // prefetch slots in every sink
    parameter integer ABW   = 36,          // HBM byte address bits (2 stacks, 45 GB)
    parameter [ABW-1:0] BASE = {ABW{1'b0}},// region base (32-B aligned)
    parameter integer PIPE  = 0,           // 1: one-hot replicated atom select (+1 stage), linear-split CRC
    // CRCMAT (sys-takeover 2026-10-09, opt-in; define OT_ENGRAM_CRCMAT or the parameter): every CRC term as an explicit
    // GF(2) matrix (per output bit a reduction XOR of a constant-masked vector -> balanced XOR trees, depth log2 256 = 8)
    // instead of 32 chained crc_byte calls (engram-lkp-B/C PREROUTE -2144 ps: e2_d -> g_crc1.ga, a ~100-level XOR chain).
    // crc_beat(c, d) = crc_beat(c, 0) ^ crc_beat(0, d) and crc_byte(c, b) = crc_byte(c, 0) ^ crc_byte(0, b) (linear,
    // no constant term): identical values, 0 cycles.
`ifdef OT_ENGRAM_CRCMAT
    parameter integer CRCMAT = 1,
`else
    parameter integer CRCMAT = 0,
`endif
    parameter integer SLW   = (NSLOT > 1) ? $clog2(NSLOT) : 1
) (
    input  wire                     clk,        // front root: window ids / win_n, hash capture res_c, straps
    // st10 (S81-TILES2 10-17): three more phase-0 1:1 regional roots of the same source as clk (each only re-roots
    // registers; no logic, cycle or edge changes; in simulation all four carry the same clock):
    input  wire                     clk_ctl,    // control: FSM / issue / address / age-seen / write path / emit control / qn
    input  wire                     clk_rd,     // read select: c* bank captures (negedge), r_* and E1
    input  wire                     clk_em,     // emit tail: E2, CRC, E3, transport / od, status
    input  wire                     clk_seed,
    input  wire [5:0]               clk_hash,
    input  wire [CPR-1:0]           clk_rows,
    input  wire                     rst_n,
    // static straps (die-level ties): one hardened element serves all 8 home dies
    input  wire                     cfg_layer,       // Engram layer index (0: layer 1, 1: layer 14)
    input  wire [1:0]               cfg_rank,        // TP rank of this die
    // window (lead flit)
    input  wire                     win_valid,
    input  wire [SLW-1:0]           win_slot,
    input  wire [4*ENG_ID_W-1:0]    win_ids,
    // sink slot releases, one pulse per release, per rank

    // HBM controller request port
    output reg                      hq_valid,

    output reg  [ABW-6:0]           hq_atom,
    output wire [3:0]               hq_len,
    output reg  [2:0]               hq_tag,
    // HBM controller response port (32-B atoms)
    input  wire                     hr_valid,
    input  wire [SLW-1:0]           hr_slot,
    input  wire [2:0]               hr_tag,
    input  wire [3:0]               hr_idx,
    input  wire [255:0]             hr_data,
    // row beats to the all-gather and the local sink
    output wire                     o_valid,

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
    initial begin
        if (RETURN_AGE < 32 || RETURN_AGE > 65000 || CPR != 6 || PIPE != 1)
            $fatal(1,"static lookup requires explicit service age32..65000, six columns, PIPE1");
    end

    // ---- column constants -----------------------------------------------------------
    function automatic [63:0] col_base(input integer l, input integer rk, input integer j);
        integer i;
        reg [63:0] acc, sz;
        begin
            acc = 64'd0;
            for (i = 0; i < j; i = i + 1) begin
                sz = ENG_PRIME[QW*(l*ENG_COLS + rk*CPR + i) +: QW] * (ROWSTRIPE ? 64'd288 : 64'd272);
                acc = acc + ((sz + 64'd31) & ~64'd31);
            end
            col_base = acc;
        end
    endfunction

    // ---- state ------------------------------------------------------------------------
    localparam [2:0] S_IDLE = 3'd0, S_FEED = 3'd1, S_HASH = 3'd2, S_ADDR = 3'd3, S_ISSUE = 3'd4, S_EMIT = 3'd5;
    reg [2:0] st;
    reg [1:0] fcnt;
    reg [4*ENG_ID_W-1:0] ids;
    reg [SLW-1:0] slot;
    reg active;
    reg [15:0] age;
    reg protocol_bad;
    reg [8:0] seen [0:CPR-1];
    wire win_acc = win_valid && !active;
    wire response_ok = hr_valid && active && age < RETURN_AGE &&
        hr_slot == slot && hr_tag < CPR && hr_idx < 9 && !seen[hr_tag][hr_idx];
    integer sr;
    always @(posedge clk_ctl or negedge rst_n) begin
        if (!rst_n) begin
            active<=0; age<=0; protocol_bad<=0;
            for(sr=0;sr<CPR;sr=sr+1) seen[sr]<=0;
        end else begin
            if(active) age<=age+1'b1;
            if(win_valid && active) protocol_bad<=1;
            if(hr_valid && !response_ok) protocol_bad<=1;
            if(response_ok) seen[hr_tag][hr_idx]<=1'b1;
            if(active && age == RETURN_AGE) begin
                if(st != S_EMIT) protocol_bad<=1;
                for(sr=0;sr<CPR;sr=sr+1) if(seen[sr]!=9'h1ff) protocol_bad<=1;
            end
            // Fixed drainage includes all select/FIFO/CRC output registers.
            if(active && age==RETURN_AGE+63) active<=0;
            if(win_acc) begin
                active<=1;age<=0;
                for(sr=0;sr<CPR;sr=sr+1) seen[sr]<=0;
            end
        end
    end
    always @(posedge clk) if (win_acc) ids <= win_ids;

    // ---- hash -------------------------------------------------------------------------
    // The 4th feed (fcnt 3) of a window hashes ids[0] newest .. ids[3] oldest with no pad (sequence start at feed 0),
    // i.e. exactly the window {ids[3], ids[2], ids[1], ids[0]} (w[k] = ids slot k); ids is stable from the cycle after
    // win_acc until the next window, so the window register win_n carries ids every cycle (only the 4th feed's result
    // is captured, at hdone).  win_n is the core -> seed hop: ck negedge -> hash w on ck_seed posedge.
    wire hfeed = (st == S_FEED);
    reg [4*ENG_ID_W-1:0] win_n;
    always @(negedge clk) win_n <= ids;
    wire [QW*ENG_LAYERS*ENG_COLS-1:0] hres;
    ot_s81_engram_hash_static u_hash (.clk(clk_seed), .clk_columns(clk_hash), .in_w(win_n), .out_res(hres));
    reg [12:1] lastl;                        // marks the 4th feed through the hash latency
    always @(posedge clk_ctl or negedge rst_n) begin
        if (!rst_n) lastl <= 12'd0;
        else lastl <= {lastl[11:1], hfeed && fcnt == 2'd3};
    end
    wire hdone = lastl[12];
    // hash -> core hop: column negedge res_n -> core posedge res_c (no logic between them)
    reg [QW*ENG_LAYERS*ENG_COLS-1:0] res_c;
    always @(posedge clk) res_c <= hres;

    // ---- address ----------------------------------------------------------------------
    reg [QW-1:0]  res  [0:CPR-1];
    reg [ABW-1:0] r256 [0:CPR-1];
    reg [ABW-1:0] r8   [0:CPR-1];            // residue*16 (272-B rows) / residue*32 (ROWSTRIPE 288-B rows) + column base
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
            reg [QW-1:0]  res_m;
            reg [ABW-1:0] cb_m;
            reg [ABW-1:0] cb_q;
            wire [8*QW-1:0]  res_c8;
            wire [8*ABW-1:0] cbs_c;
            for (gc = 0; gc < 8; gc = gc + 1) begin : g_cand          // gc = {layer, rank}
                localparam integer C = (gc / 4) * ENG_COLS + (gc % 4) * CPR + gj;
                localparam [63:0] CB = col_base(gc / 4, gc % 4, gj);
                assign res_c8[QW*gc +: QW]  = res_c[QW*C +: QW];    // = row - offset, exactly
                assign cbs_c[ABW*gc +: ABW] = CB[ABW-1:0];
            end
            integer m;
            always @(*) begin
                res_m = {QW{1'b0}}; cb_m = {ABW{1'b0}};
                for (m = 0; m < 8; m = m + 1) begin
                    res_m = res_m | ({QW{csel[m]}} & res_c8[QW*m +: QW]);
                    cb_m  = cb_m  | ({ABW{csel[m]}} & cbs_c[ABW*m +: ABW]);
                end
            end
            always @(posedge clk_ctl) begin
                cb_q <= BASE + cb_m;
            end
            always @(posedge clk_ctl) begin
                if (hdone) res[gj] <= res_m;
                if (st == S_ADDR && acnt == 2'd0) begin
                    r256[gj] <= {{(ABW-QW-8){1'b0}}, res[gj], 8'd0};
                    r8[gj]   <= (ROWSTRIPE ? {{(ABW-QW-5){1'b0}},res[gj],5'd0} : {{(ABW-QW-4){1'b0}},res[gj],4'd0}) + cb_q;
                end
                if (st == S_ADDR && acnt == 2'd1) baddr[gj] <= r256[gj] + r8[gj];
            end
        end
    endgenerate

    // ---- row buffers ------------------------------------------------------------------
    wire [255:0] rb [0:CPR-1][0:ATOMS-1];
    reg [3:0]   rcnt [0:CPR-1];
    reg [1:0]   roff [0:CPR-1];             // row start within its first atom, in 8-byte units (0 / 2)
    integer j;
    genvar bank, atom;
    // accepted atom -> core-root registers (one-hot bank x atom enables + data); the row-root leaf writes them
    // one cycle later, so the core->row root crossing is flop to flop (enable fanout lives in the row root)
    reg [255:0] wdata_q;
    always @(posedge clk_ctl) wdata_q <= hr_data;
    generate for (bank=0; bank<CPR; bank=bank+1) begin : g_clocked_row
        wire [256*ATOMS-1:0] stored;
        reg  [ATOMS-1:0] wen_q;
        always @(posedge clk_ctl or negedge rst_n)
            if (!rst_n) wen_q <= {ATOMS{1'b0}};
            else        wen_q <= (response_ok && hr_tag == bank) ? ({{(ATOMS-1){1'b0}}, 1'b1} << hr_idx) : {ATOMS{1'b0}};
        // core -> row hop (st8): this bank's ck-POSEDGE copy (full core cycle from the shared wdata_q, so its tile-wide
        // fanout wire has a whole cycle), captured by the leaf on the row posedge one cycle later (full-cycle crossing)
        reg  [ATOMS-1:0] wx_en;
        reg  [255:0]     wx_d;
        always @(posedge clk_ctl) begin wx_en <= wen_q; wx_d <= wdata_q; end
        ot_s81_engram_rowbank_static_leaf #(.ATOMS(ATOMS)) storage (
            .ck(clk_rows[bank]), .write_en(wx_en), .write_data(wx_d), .rows(stored));
        for (atom=0; atom<ATOMS; atom=atom+1) begin : g_read
            assign rb[bank][atom]=stored[256*atom+:256];
        end
    end endgenerate

    // ---- issue ------------------------------------------------------------------------
    reg [2:0] icnt;
    always @(posedge clk_ctl or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; fcnt <= 2'd0; acnt <= 2'd0; icnt <= 3'd0; hq_valid <= 1'b0;
            slot <= {SLW{1'b0}};
            for (j = 0; j < CPR; j = j + 1) rcnt[j] <= 4'd0;
        end else begin
            for (j = 0; j < CPR; j = j + 1) if (response_ok && hr_tag == j[2:0]) rcnt[j] <= rcnt[j] + 1'b1;
            case (st)
                S_IDLE: if (win_acc) begin
                    st <= S_FEED; fcnt <= 2'd0; slot <= win_slot;
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
                    begin
                        if (icnt < CPR[2:0]) begin
                            hq_valid <= 1'b1;
                            icnt <= icnt + 1'b1;
                        end else begin
                            hq_valid <= 1'b0;
                            st <= S_EMIT;
                        end
                    end
                end
                S_EMIT: if (emit_done) begin
                    st <= S_IDLE;

                    for (j = 0; j < CPR; j = j + 1) rcnt[j] <= 4'd0;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
    // st10b: the unreset request payload lives in a plain clocked block (it sat in the async-reset block, so yosys put
    // rst_n on its enable: OT_MULTI_ROOT 'rst_n wrong domain' once clk_ctl became ck_s).  Same enable, same cycle:
    // while rst_n is low st is S_IDLE, so the payload holds exactly as before.
    always @(posedge clk_ctl) if (st == S_ISSUE && icnt < CPR[2:0]) begin
        hq_atom <= baddr[icnt][ABW-1:5];
        hq_tag  <= icnt;
    end
    always @(posedge clk_ctl) if (st == S_ADDR && acnt == 2'd1)
        for (j = 0; j < CPR; j = j + 1) roff[j] <= r8[j][4:3];   // byte address mod 32 / 8 (r256 is 0 mod 256)

    // ---- emit -------------------------------------------------------------------------
    // E0 issues beat (ej, ek); E1 registers the three atoms; E2 shifts into the FIFO; E3 updates the CRC.
    reg [2:0] ej;
    reg [3:0] ek;                            // 0..7 beats, 8 = row finished
    reg       emit_done_r;
    wire      emit_done = emit_done_r;

    reg       e1_v, e2_v, e0q_v, e0r_v;
    wire      e1_vn = e0r_v;                // PIPE 1 (st6): E1 captures the read two cycles after E0q

    wire      row_ok = (ej < CPR[2:0]);
    wire      room = 1'b1;
    wire      e0_go = (st == S_EMIT) && active && age >= RETURN_AGE + 2 && !emit_done_r && row_ok && ek < 4'd8 && room;
    reg [255:0] e1_lo, e1_hi, e1_a8;
    reg [1:0]   e1_off;
    reg [2:0]   e1_j, e1_k;
    reg [SLW-1:0] e1_s, e2_s, e3_s;
    always @(posedge clk_ctl or negedge rst_n) begin
        if (!rst_n) begin
            ej <= 3'd0; ek <= 4'd0; emit_done_r <= 1'b0; e1_v <= 1'b0; e0q_v <= 1'b0; e0r_v <= 1'b0;
        end else begin
            e0q_v <= (PIPE != 0) && e0_go;
            e0r_v <= e0q_v;
            e1_v <= (PIPE != 0) ? e0r_v : e0_go;
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
            always @(posedge clk_rd) if (e0_go) begin
                e1_lo <= rb[ej][ek];
                e1_hi <= rb[ej][ek + 1'b1];
                e1_a8 <= rb[ej][8];
                e1_off <= roff[ej];
                e1_j <= ej; e1_k <= ek[2:0]; e1_s <= slot;
            end
        end else begin : g_sel1
            // STATIC14 st6 (S-ELEM 10-16): the row read crosses the core <-> row roots only flop to flop, every crossing
            // a HALF-CYCLE hop, all logic inside one root on a full cycle (st5 put the one-hot AND-OR and the six-bank OR
            // inside its half-cycle hops: gate TT core->rows -95..-107 ps, rows->core -50..-92 ps). +1 cycle on the
            // read (E0q -> E1 two cycles; every output beat and status one cycle later):
            //   core NEGEDGE  qn[b]  = {e0_go && ej == b, ek}         (E0 decode, half cycle inside the core)
            //   row  posedge  h_b    <= qn[b]                          (core -> row hop, 5 flops per bank)
            //   row  posedge  b*     <= hit ? atoms ek / ek+1 / 8 : 0  (full cycle, payload and decode local to the row root)
            //   core NEGEDGE  c*[b]  <= b*                              (row -> core hop)
            //   core posedge  e1     <= OR of the six banks             (half cycle inside the core)
            reg [1:0]  q_off, r_off;
            reg [2:0]  q_j, q_k, r_j, r_k;
            reg [SLW-1:0] q_s, r_s;
            integer jj;
            always @(posedge clk_ctl) begin
                if (e0_go) begin q_off <= roff[ej]; q_j <= ej; q_k <= ek[2:0]; q_s <= slot; end
            end
            always @(posedge clk_rd) begin
                r_off <= q_off; r_j <= q_j; r_k <= q_k; r_s <= q_s;
            end
            reg [255:0] clo [0:CPR-1], chi [0:CPR-1], ca8 [0:CPR-1];
            genvar gb;
            for (gb = 0; gb < CPR; gb = gb + 1) begin : g_rdhop
                reg       qn_h;
                reg [3:0] qn_k;
                always @(negedge clk_ctl) begin qn_h <= e0_go && (ej == gb); qn_k <= ek; end
                reg       h_b;
                reg [3:0] k_b;
                always @(posedge clk_rows[gb]) begin h_b <= qn_h; k_b <= qn_k; end
                reg [ATOMS-1:0] dlo, dhi;
                reg [255:0] lo_b, hi_b;
                integer k2;
                always @(*) begin
                    for (k2 = 0; k2 < ATOMS; k2 = k2 + 1) begin
                        dlo[k2] = h_b && (k_b == k2);
                        dhi[k2] = h_b && (k_b + 4'd1 == k2);
                    end
                    lo_b = 256'd0; hi_b = 256'd0;
                    for (k2 = 0; k2 < ATOMS; k2 = k2 + 1) begin
                        lo_b = lo_b | ({256{dlo[k2]}} & rb[gb][k2]);
                        hi_b = hi_b | ({256{dhi[k2]}} & rb[gb][k2]);
                    end
                end
                reg [255:0] blo, bhi, ba8;
                always @(posedge clk_rows[gb]) begin blo <= lo_b; bhi <= hi_b; ba8 <= {256{h_b}} & rb[gb][ATOMS-1]; end
                always @(negedge clk_rd) begin clo[gb] <= blo; chi[gb] <= bhi; ca8[gb] <= ba8; end
            end
            reg [255:0] vlo, vhi, va8;
            always @(*) begin
                vlo = 256'd0; vhi = 256'd0; va8 = 256'd0;
                for (jj = 0; jj < CPR; jj = jj + 1) begin
                    vlo = vlo | clo[jj]; vhi = vhi | chi[jj]; va8 = va8 | ca8[jj];
                end
            end
            always @(posedge clk_rd) if (e1_vn) begin
                e1_lo <= vlo; e1_hi <= vhi; e1_a8 <= va8;
                e1_off <= r_off; e1_j <= r_j; e1_k <= r_k; e1_s <= r_s;
            end
        end
    endgenerate
    // E2: byte shift
    reg [255:0] e2_d;
    reg [7:0]   e2_scale;                   // this beat's block exponent (row byte 256 + k)
    reg [63:0]  e2_sc8;                     // all 8 block exponents (row bytes 256..263, byte 256 at [7:0]) for the CRC
    reg [31:0]  e2_crc;
    reg [2:0]   e2_j, e2_k;
    wire [511:0] e1_cat = {e1_hi, e1_lo};
    wire [255:0] e1_a8s = e1_a8 >> {e1_off, 6'd0};
    always @(posedge clk_em or negedge rst_n) begin
        if (!rst_n) e2_v <= 1'b0;
        else e2_v <= e1_v;
    end
    always @(posedge clk_em) if (e1_v) begin
        e2_d <= e1_cat[{e1_off, 6'd0} +: 256];
`ifdef OT_ENGRAM_MUT_ONESCALE
        e2_scale <= e1_a8s[7:0];            // NEGATIVE CONTROL ONLY: the pre-F13 one-exponent decode (block 0's on every beat)
`else
        e2_scale <= e1_a8s[{e1_k, 3'd0} +: 8];
`endif
        e2_sc8 <= e1_a8s[63:0];
        e2_crc <= e1_a8s[95:64];            // bytes 264..267, byte 264 = crc[7:0]
        e2_j <= e1_j; e2_k <= e1_k; e2_s <= e1_s;
    end

    // Fixed two-stage registered output transport. There is no FIFO
    // occupancy or readiness term capable of moving a compiler output slot.
    localparam integer FW = 5 + 3 + SLW + 264;
    reg transport_v, ov;
    reg [FW-1:0] transport_d, od;
    wire [4:0] e2_col = crank * CPR + e2_j;
    always @(posedge clk_em or negedge rst_n) begin
        if(!rst_n) begin transport_v<=0;ov<=0;end
        else begin transport_v<=e2_v;ov<=transport_v;end
    end
    always @(posedge clk_em) begin
        transport_d<={e2_col,e2_k,e2_s,e2_scale,e2_d};
        od<=transport_d;
    end
    assign o_valid=ov;
    assign {o_col,o_beat,o_slot,o_data}=od;

    // ---- CRC-32/MPEG-2 over the 256 codes and the 8 exponent bytes ----------------------
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
    function automatic [31:0] crc_sc8(input [31:0] c, input [63:0] s);   // the 8 exponent bytes, byte 256 first
        integer i;
        reg [31:0] x;
        begin
            x = c;
            for (i = 0; i < 8; i = i + 1) x = crc_byte(x, s[8*i +: 8]);
            crc_sc8 = x;
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
    // ---- CRCMAT: constant GF(2) columns and the per-output-bit masks ------------------------
    wire [31:0] m_dcol [0:255];              // crc_beat(0, e_i)
    wire [31:0] m_scol [0:31];               // crc_beat(e_k, 0)
    wire [31:0] m_bcol [0:63];               // crc_sc8(0, e_i)
    wire [31:0] m_fcol [0:31];               // crc_sc8(e_k, 0)
    wire [255:0] m_dmask [0:31];
    wire [31:0]  m_smask [0:31], m_fmask [0:31];
    wire [63:0]  m_bmask [0:31];
    genvar gmi, gmj;
    generate
        for (gmi = 0; gmi < 256; gmi = gmi + 1) begin : g_mdc
            localparam [31:0] C = crc_beat(32'd0, 256'd1 << gmi);
            assign m_dcol[gmi] = C;
        end
        for (gmi = 0; gmi < 32; gmi = gmi + 1) begin : g_msc
            localparam [31:0] C = crc_beat(32'd1 << gmi, 256'd0);
            localparam [31:0] F = crc_sc8(32'd1 << gmi, 64'd0);
            assign m_scol[gmi] = C; assign m_fcol[gmi] = F;
        end
        for (gmi = 0; gmi < 64; gmi = gmi + 1) begin : g_mbc
            localparam [31:0] C = crc_sc8(32'd0, 64'd1 << gmi);
            assign m_bcol[gmi] = C;
        end
        for (gmj = 0; gmj < 32; gmj = gmj + 1) begin : g_mm
            for (gmi = 0; gmi < 256; gmi = gmi + 1) begin : g_d
                assign m_dmask[gmj][gmi] = m_dcol[gmi][gmj];
            end
            for (gmi = 0; gmi < 32; gmi = gmi + 1) begin : g_s
                assign m_smask[gmj][gmi] = m_scol[gmi][gmj];
                assign m_fmask[gmj][gmi] = m_fcol[gmi][gmj];
            end
            for (gmi = 0; gmi < 64; gmi = gmi + 1) begin : g_b
                assign m_bmask[gmj][gmi] = m_bcol[gmi][gmj];
            end
        end
    endgenerate
    reg [31:0] crc;
    reg        e3_last;
    wire [31:0] mx_d, mx_s, mx_f;            // crc_beat(0, e2_d), crc_beat(crc, 0), crc_sc8(crc, e3_sc8)
    reg  [63:0] e3_sc8;
    generate
        for (gmj = 0; gmj < 32; gmj = gmj + 1) begin : g_mx
            assign mx_d[gmj] = ^(e2_d & m_dmask[gmj]);
            assign mx_s[gmj] = ^(crc & m_smask[gmj]);
            assign mx_f[gmj] = (^(crc & m_fmask[gmj])) ^ (^(e3_sc8 & m_bmask[gmj]));
        end
    endgenerate
    wire [31:0] beat_d = (CRCMAT != 0) ? mx_d : crc_beat(32'd0, e2_d);
    wire [31:0] beat_s = (CRCMAT != 0) ? mx_s : crc_beat(crc, 256'd0);
    wire [31:0] fold   = (CRCMAT != 0) ? mx_f : crc_sc8(crc, e3_sc8);
    reg [31:0] e3_exp;
    generate
        if (PIPE == 0) begin : g_crc0
            always @(posedge clk_em or negedge rst_n) begin
                if (!rst_n) begin
                    crc <= 32'hFFFFFFFF; e3_last <= 1'b0;
                end else begin
                    e3_last <= e2_v && e2_k == 3'd7;
                    if (e2_v) crc <= (CRCMAT != 0) ? (((e2_k == 3'd0) ? crc_beat(32'hFFFFFFFF, 256'd0) : beat_s) ^ beat_d)
                                                   : crc_beat((e2_k == 3'd0) ? 32'hFFFFFFFF : crc, e2_d);
                end
            end
            always @(posedge clk_em) if (e2_v && e2_k == 3'd7) begin e3_sc8 <= e2_sc8; e3_exp <= e2_crc; e3_s <= e2_s; end
        end else begin : g_crc1
            // stage a: data term; stage b: state term ^ data term
            reg [31:0] ga;
            reg        a_v, a_first, a_last;
            reg [63:0] a_sc8;
            reg [31:0] a_exp;
            reg [SLW-1:0] a_s;
            always @(posedge clk_em or negedge rst_n) begin
                if (!rst_n) begin a_v <= 1'b0; a_last <= 1'b0; crc <= 32'hFFFFFFFF; e3_last <= 1'b0; end
                else begin
                    a_v <= e2_v;
                    a_last <= e2_v && e2_k == 3'd7;
                    e3_last <= a_last;
                    if (a_v) crc <= ((CRCMAT != 0) ? (a_first ? crc_beat(32'hFFFFFFFF, 256'd0) : beat_s)
                                                   : crc_beat(a_first ? 32'hFFFFFFFF : crc, 256'd0)) ^ ga;
                end
            end
            always @(posedge clk_em) if (e2_v) begin
                ga <= beat_d;
                a_first <= (e2_k == 3'd0);
                a_sc8 <= e2_sc8; a_exp <= e2_crc; a_s <= e2_s;
            end
            always @(posedge clk_em) if (a_last) begin e3_sc8 <= a_sc8; e3_exp <= a_exp; e3_s <= a_s; end
        end
    endgenerate
    // final: fold the 8 exponent bytes and compare
    always @(posedge clk_em or negedge rst_n) begin
        if (!rst_n) begin
            st_valid <= 1'b0; st_slot <= {SLW{1'b0}}; st_bad <= 1'b0; fault <= 1'b0;
        end else begin
            if (protocol_bad) fault <= 1;
            st_valid <= e3_last;
            if (e3_last) begin
                st_slot <= e3_s;
                st_bad <= (fold != e3_exp) || protocol_bad;
                if (fold != e3_exp) fault <= 1'b1;
            end
        end
    end
endmodule
