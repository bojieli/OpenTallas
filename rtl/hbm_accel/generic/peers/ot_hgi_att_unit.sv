`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 ATT unit die body (hgi-adapters, 2026-10-09; D4 = the ATT load protocol, owned here by hgi-takeover's call).
// Unit 5 records ATT.QK (op 0) / ATT.PV (op 1) exactly as hgi_sim machine.u_att_qk / u_att_pv (spec 6.7, G12):
//   rows    the row list: B's n_B rows (param[8] ring: slot (POS1 - n_B + i) mod B.m, B.m a power of two >= n_B), then
//           C's n_C rows; T = n_B + n_C; a row is hd elements in B / C's format (FP8 E4M3 bytes, FP32 or BF16 on the
//           E4M3 grid), at byte address base + slot x stride (32-byte aligned).
//   QK      q[h] = A row h (VM, hd FP32 words holding BF16 values), h < lanes (param[3:0], 0 = 16);
//           O[h x O.stride + t] = att_qk(q[h], row t): chunk8 per 64-slice, slices by the pairwise tree.
//   PV      p[h] = A row h (T BF16-valued words); O[h x O.stride + d] = att_pv(p[h], V)[d] = csum8 over the T rows.
// Engine: the r25 attention engine ot_hdc_v41x_attn (H heads, head_dim D, TD 64, NL lanes; exact against
// hdc_golden_v41 attend).  LOAD PROTOCOL (this file is its definition):
//   * a record runs as ceil(T / BLK) engine jobs of <= BLK (512) rows, rows in list order;
//   * every job loads all H q words (QK: q[h] zero-padded from hd to D, heads >= lanes zero; PV: all zero) and its rows
//     as engine staging rows: D / 32 group words {fmt 0, scale 127, 32 E4M3 codes}, groups past hd zero;
//   * QK: the job's scores (lane 0 = row) go to O, heads < lanes; the job's p.v is fed zero probabilities, discarded;
//   * PV: the job's scores are discarded; its probabilities are p[h][rows of the job] (R = TD / H rows x H heads a
//     word, heads >= lanes zero) sent after the job's last score; its pv (H x D) is merged ACROSS jobs by the binary
//     counter of the golden's padded pairwise tree (BLK rows = BLK / 8 chunks, a power of two, so each job's sum is
//     one node of the tree; job j: at level l, bit l of j set -> add(stored[l], cur) and climb, clear -> store and stop;
//     the last job climbs every level, a clear bit passing cur up unchanged = cur + +0); O = the root, h < lanes, d < hd.
//   * an element not on the E4M3 grid (|x| > 448, finer than its binade's quantum, or NaN / inf) faults (fail closed).
// Ports: the record (header, A, B, C, O, n_B, n_C, POS1; SUT unused), ONE VM packet client (q / p reads, score and
// output writes), ONE HBM read lane {sector address, tag} -> {tag, 256 b} with NOUT outstanding, any response order.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_att_unit #(
    parameter integer H = 16,
    parameter integer D = 512,
    parameter integer TD = 64,
    parameter integer NL = 2,               // row lanes (D / (NL x S) <= 32: a tile's dims in one 32-dim group)
    parameter integer BLK = 512,
    parameter integer NOUT = 8,
    parameter integer MUT_RING = 0,         // mutant: ring rows from slot 0
    parameter integer MUT_ROW = 0,          // mutant (hgi-1010/g): B row t read from slot t + MUT_ROW (0 = exact)
    // PIPE (hgi-1010/g, opt-in, default 0 = the as-built unit): (1) rows STREAM: one sector request a cycle across
    // rows (up to RBD sectors in flight, tag = reorder slot, any response order), the converter lands one sector a
    // cycle in row order and a row leaves for the engine as soon as its last sector lands (no per-row round trip);
    // (2) QK scores with O.istride 1 leave as SECTOR writes (a head's consecutive rows of a beat, up to 8 words a
    // write) instead of one word a write.  Same records, same golden values, same fault rules.
    parameter integer PIPE = 0,
    parameter integer RBD = 128,            // PIPE: reorder slots (sectors in flight), <= 256 (the 8-bit tag)
    // PIPE = 2 (hgi-1010/g, opt-in): STRIPED KV ROW LANES.  The row stream leaves the single 32 B sector lane: one
    // engine beat (NL rows) is requested a cycle on the row-lane port {wq_sv[s] = row slot s of the beat valid,
    // wq_row[s] = its row byte address}; the HBM side (svc, PC-striped) returns sector l of slot s's row on lane
    // (s, l) (l < sectors a row), IN ORDER per lane.  A beat lands when every lane of its rows has its head: the whole
    // rows convert to E4M3 codes in one edge (same grid rules / faults) and leave as one kv beat -- up to NL rows a
    // cycle, bounded by the HBM bandwidth, never by a lane.  RIF rows in flight a slot (the landing FIFO depth).
    // MUT_LANE (bench): lane 1's data taken from lane 0 -> must FAIL.
    parameter integer RIF = 64,
    parameter integer MUT_LANE = 0,
    // KV8 (fe-push-hgi-1010/kv8, opt-in, default 0 = the as-built unit): B / C fmt 7 = the FP8 KV ROW of the DS packed
    // window contract (docs/V41X_PACKED_WINDOW_KV_INTERFACE.md, hdc_golden_v41 quant_fp8): hd E4M3 code bytes (hd / 32
    // sectors) then hd / 32 UE8M0 block scales in byte order in ONE trailing sector (row = hd / 32 + 1 sectors, B/C
    // stride >= that).  Element t of a row = E4M3[code] x 2^(scale(t / 32) - 127), carried to the engine as the group
    // word's scale byte (the as-built rows pin it at 127) -- the engine dequantises exactly as the golden's qdq_fp8.
    // Scale 0xFF (E8M0 NaN) faults (fail closed); codes keep the engine's own rules.  B and C must agree (7 or not).
    // KV8 = 1 also lands the PIPE = 0 sector path through ot_hgi_att_sector_codec (registered conversion + bank
    // address, the closed codec element) instead of the inline e4m3 at the bank write.  fmt 7 with KV8 = 0 faults.
    // MUT_KV8 (bench): group g takes group g+1's scale -> must FAIL.
    parameter integer KV8 = 0,
    parameter integer MUT_KV8 = 0,
    // PIPE = 3 (hbm-attn-tput 2026-10-12, opt-in; B2 local-slice client): the PIPE = 2 row lanes plus
    //   * the engine's job modes (MODES = 1): a QK record runs QK-ONLY jobs (no zero-probability p.v pass), a PV record
    //     PV-ONLY jobs (no discarded q.k pass); ONE job when T <= TROWS1 (every DS record), else BLK-row jobs + merge;
    //   * rows issue from the job's first cycle (overlapping the q / p load); KVL lanes a slot (rows wider fault);
    //   * the LOCAL VM SLICE WIDE CLIENT (ot_hgi_vm_unit RP / W2 group form, provisional B2 port): xr = 32 read lanes
    //     {v, sector 15} (lane b = slice bank b = sector[4:0], LQW credits a lane, xr_cr returns one, xr_d {v, 256}
    //     in request order a lane), xw = 32 write lanes {v, sector 15, wdata 256, word mask 8} (LQW credits,
    //     xw_cr / xw_done).  q heads and p rows load as wide reads; QK scores leave as 8-row sectors a head DURING the
    //     row stream; PV's O leaves as up to 32 sectors a cycle.  The packet port (vmq) is unused.
    //   MUT_W3 (bench): 1 = the score sector of a beat's closing row drops its last word -> must FAIL.
    parameter integer TROWS1 = 640,
    parameter integer KVL = D * 4 / 32,     // row lanes a slot (PIPE >= 2); PIPE 3 production KV8 rows: D / 32 + 1
    parameter integer LQW = 8,
    parameter integer MUT_W3 = 0,
    // PIPE = 3 RECORD OVERLAP (hbm-attn-tput2 2026-10-12): the unit is a FRONT (decode / check, wide q / p loads, KV
    // row stream, engine job, q / p words) and two BACK paths, each holding a SNAPSHOT of its job's tail context
    // (op fields, O base / strides, rows, lanes) taken at the job's start:
    //   * the SCORE path (QK): every beat writes the score buffer on its sc_v edge (one beat a cycle), the next edge
    //     closes its 8-row sectors into the write FIFO wf; the engine's SQ3 score credits are returned against a
    //     RESERVATION of wf space (H closes a beat in flight, 2 H for the beat being closed), so wf never overflows;
    //   * the PV path: pv beats land in the O buffer; the O burst leaves when the job's last beat has landed.
    // The FRONT takes the next record as soon as its own job's rows / q / p words are in the engine; the next
    // record's wide loads and KV row requests run during the current record's tail, and its engine job starts
    // when the engine is free AND its op's back path is free (one job a path: the buffers need no second bank).
    // Records retire in order (a 4-deep op FIFO); a path's writes are counted per lane by a tag FIFO.
    // Multi-job records (T > TROWS1) keep the serial merge in the FRONT.  MUT_OVL (bench): the back paths use the
    // FRONT's live O base instead of the snapshot -> must FAIL.
    parameter integer SQ3 = 64,
    parameter integer MUT_OVL = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_o,
    input  wire [20:0]   rec_n_b, rec_n_c, rec_pos1,
    output reg           rec_done,
    output reg           rec_fault,
    output wire          halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    output reg           hq_v,
    input  wire          hq_rdy,
    output reg  [34:0]   hq_addr,
    output reg  [7:0]    hq_tag,
    input  wire          hr_v,
    input  wire [7:0]    hr_tag,
    input  wire [255:0]  hr_data,
    // PIPE = 2 row lanes (tie off otherwise): request {wq_sv, wq_row} when wq_rdy; lane (s, l) = s * (D*4/32) + l
    output reg           wq_v,
    input  wire          wq_rdy,
    output reg  [NL-1:0] wq_sv,
    output reg  [NL*40-1:0] wq_row,
    output reg  [7:0]    wq_nsec,
    input  wire [NL*KVL-1:0]     wl_v,
    input  wire [NL*KVL*256-1:0] wl_d,
    // PIPE = 3 local-slice wide client (tie off otherwise)
    output reg  [32*16-1:0]  xr_q,
    input  wire [31:0]       xr_cr,
    input  wire [32*257-1:0] xr_d,
    output reg  [32*280-1:0] xw_q,
    input  wire [31:0]       xw_cr,
    input  wire [31:0]       xw_done
);
    localparam integer S = D / TD, NT = NL * S, DPT = D / NT, G = D / 32, R = TD / H, ROWW = G * 265;
    localparam integer SPR = D * 4 / 32;              // max sectors a row (FP32)
    initial if (PIPE != 0 && (RBD < 2 || RBD > 256 || (RBD & (RBD - 1)) != 0)) $fatal(1, "ot_hgi_att_unit: RBD a power of two <= 256");
    // ---- record pin flops
    reg [127:0] hdr; reg [255:0] da, db, dc, dout; reg [20:0] nb, nc, pos1; reg raw_v, busy, halt_q;
    // PIPE = 3: the pin flops load on the handshake only (the record stays put while the next one waits)
    always @(posedge clk) if (PIPE != 3 || (rec_v && rec_rdy)) begin hdr <= rec_hdr; da <= rec_a; db <= rec_b;
                                dc <= rec_c; dout <= rec_o; nb <= rec_n_b; nc <= rec_n_c; pos1 <= rec_pos1; end
    reg [2:0] rf_n; reg [1:0] rf_h; reg [3:0] rf_k;             // PIPE = 3: records accepted, not retired (op bit)
    assign rec_rdy = !raw_v && !busy && !halt_q && (PIPE != 3 || rf_n < 3'd4);
    assign halted = halt_q;
    function automatic [39:0] mbase(input [255:0] d); mbase = d[47:8]; endfunction
    function automatic [19:0] mn(input [255:0] d); mn = d[67:48]; endfunction
    function automatic [19:0] mm(input [255:0] d); mm = d[87:68]; endfunction
    function automatic [31:0] mst(input [255:0] d); mst = d[119:88]; endfunction
    function automatic [15:0] mist(input [255:0] d); mist = (d[135:120] == 16'd0) ? 16'd1 : d[135:120]; endfunction
    wire [5:0] op = hdr[123:118];
    wire [6:0] opnd = hdr[99:93];
    wire [24:0] prm = hdr[88:64];
    wire hasc = opnd[2];
    // ---- decoded record
    reg qk; reg [4:0] lanes; reg [9:0] hd; reg ring; reg [20:0] tt; reg [1:0] bfmt, cfmt; reg bk8, ck8;
    reg [17:0] abase, astr, obase, ostr, oist; reg [39:0] bbase, cbase; reg [31:0] bstr, cstr; reg [19:0] bm;
    // ---- the engine
    reg job_v; reg [15:0] job_t; wire job_ready;
    reg q_v; reg [D*16-1:0] q_w; wire q_ready; reg qload;
    reg kv_v; reg [NL*ROWW-1:0] kv_w; reg [NL-1:0] kv_m; reg [3:0] kl; wire kv_ready;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f; reg sc_cr;
    reg p_v; reg [TD*16-1:0] p_w; wire p_ready;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f; reg pv_cr;
    localparam integer SQ = (PIPE == 3) ? SQ3 : 16;     // score beats in flight (the engine's credit count)
    localparam integer JB = (PIPE == 3 && TROWS1 > BLK) ? TROWS1 : BLK;     // rows a job (buffers)
    ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(JB), .SC_CRED(SQ), .MODES(PIPE == 3 ? 1 : 0)) u_eng (.clk(clk), .rst_n(rst_n),
        .job_v(job_v), .job_t(job_t), .job_ready(job_ready), .q_v(q_v), .q_w(q_w), .q_ready(q_ready),
        .kv_v(kv_v), .kv_m(kv_m), .kv_w(kv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
        .p_v(p_v), .p_w(p_w), .p_ready(p_ready), .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f), .pv_cr(pv_cr),
        .qk_iss(), .pv_iss());
    // ---- local buffers
    // STORAGE, banked so no array takes more than one write (and the reads it needs) an edge:
    //   qb[e mod 8][e / 8]            q of the head being loaded (a VM sector lands 8 consecutive elements)
    //   pbk[h][row mod 8][row / 8]    the job's probabilities (a sector lands 8 rows; a p word reads 4 rows)
    //   cb[i mod 32][i / 32]          the row's E4M3 codes (a sector lands 32 / 16 / 8 codes)
    //   ck[k H + h][c]                the job's pv: tile k's head-h value of dim k DPT + c (one pv beat writes every bank)
    // (each bank is a memory local to its generate scope: one writer; reads leave through the flat wires below)
    wire [D*16-1:0] q_flat;                  // qb, element e at [16 e]
    wire [D*8-1:0]  c_flat;                  // cb, code i at [8 i]
    wire [R*H*16-1:0] p_word;                // the p word of pw_i: row j, head h at [(j H + h) 16]
    wire [NT*H*32-1:0] ck_rd;                // every ck bank's word at ck_a
    reg  [5:0] ck_a;
    reg [31:0] lvl [0:4*H*D-1];              // merge levels [l][h][d]
    // ---- E4M3 encode of an FP32 value on the E4M3 grid (fault otherwise)
    function automatic [8:0] e4m3(input [31:0] x);     // {bad, code}
        reg [7:0] e; reg [22:0] m; integer E; reg [3:0] sig;
        begin
            e = x[30:23]; m = x[22:0]; E = e - 127; sig = {1'b1, m[22:20]};
            if (x[30:0] == 31'd0) e4m3 = {1'b0, x[31], 7'd0};
            else if (e == 8'd0 || e == 8'hFF || m[19:0] != 20'd0) e4m3 = 9'h100;
            else if (E >= -6 && E <= 8) begin
                if (E == 8 && m[22:20] == 3'd7) e4m3 = 9'h100;
                else e4m3 = {1'b0, x[31], 4'(E + 7), m[22:20]};
            end
            else if (E == -7) e4m3 = sig[0] ? 9'h100 : {1'b0, x[31], 4'd0, sig[3:1]};
            else if (E == -8) e4m3 = (sig[1:0] != 0) ? 9'h100 : {1'b0, x[31], 4'd0, 1'b0, sig[3:2]};
            else if (E == -9) e4m3 = (sig[2:0] != 0) ? 9'h100 : {1'b0, x[31], 4'd0, 2'b00, sig[3]};
            else e4m3 = 9'h100;
        end
    endfunction
    // the staging row: D / 32 groups {fmt 0, scale 127, 32 codes}, codes past hd zero (static wiring)
    reg [ROWW-1:0] kv_row;
    reg [255:0] s8r;                         // KV8: the row's scale sector (byte g = group g's UE8M0)
    integer gx, xx;
    always @* begin
        kv_row = {ROWW{1'b0}};
        for (gx = 0; gx < G; gx = gx + 1) begin
            kv_row[gx * 265 + 256 +: 8] = (bk8 && gx < hd[9:5]) ? s8r[8 * ((gx + MUT_KV8) % G) +: 8] : 8'd127;
            for (xx = 0; xx < 32; xx = xx + 1) kv_row[gx * 265 + 8 * xx +: 8] = (gx * 32 + xx < hd) ? c_flat[8 * (gx * 32 + xx) +: 8] : 8'd0;
        end
    end
    // ---- banked writes (each bank: one write an edge)
    wire land_q = (st == S_QRD) && qk && hq < lanes && vr[273] && !vr[256];
    wire land_p = (st == S_PRD) && vr[273] && !vr[256];
    wire land_c;                             // a sector lands in cb: index c_tq of the row, data c_dq
    wire [7:0] c_tq; wire [255:0] c_dq;
    wire [26:0] qbase = {9'd0, abase} + hq * {9'd0, astr};
    wire [26:0] pbase = qbase + {6'd0, blk0};
    genvar gb, gh;
    generate for (gb = 0; gb < 8; gb = gb + 1) begin : g_qb
        wire [2:0] qq = gb[2:0] + qbase[2:0];                    // the sector word that lands in bank gb
        wire [26:0] e = {rsec, qq} - qbase;
        reg [15:0] m [0:D/8-1];
        always @(posedge clk) if (land_q && e < hd) m[e >> 3] <= vr[32*qq + 16 +: 16];
        genvar gi;
        for (gi = 0; gi < D / 8; gi = gi + 1) begin : g_o
            assign q_flat[16 * (gi * 8 + gb) +: 16] = m[gi];
        end
    end endgenerate
    // p banks: head h, bank b = row mod PB (PB = max(8, R): a sector's 8 rows and a word's R rows hit distinct banks)
    localparam integer PB = (R > 8) ? R : 8;
    wire [H*PB*16-1:0] pb_val; wire [H*PB*5-1:0] pb_jj; wire [H*PB-1:0] pb_ok;
    generate for (gh = 0; gh < H; gh = gh + 1) begin : g_ph
        for (gb = 0; gb < PB; gb = gb + 1) begin : g_pb
            reg [15:0] m [0:BLK/PB-1];
            integer x;
            always @(posedge clk) if (land_p && hq == gh)
                for (x = 0; x < 8; x = x + 1)                  // the (one) word of this sector that maps to bank gb
                    if ((({rsec, x[2:0]} - pbase) % PB) == gb && ({rsec, x[2:0]} - pbase) < tb)
                        m[({rsec, x[2:0]} - pbase) / PB] <= vr[32*x + 16 +: 16];
            wire [20:0] r0 = pw_i * R;
            wire [20:0] jj = (gb + PB - (r0 % PB)) % PB;
            assign pb_jj[(gh * PB + gb) * 5 +: 5] = jj[4:0];
            assign pb_ok[gh * PB + gb] = jj < R;
            assign pb_val[(gh * PB + gb) * 16 +: 16] = m[(r0 + jj) / PB];
        end
    end endgenerate
    integer pbx;
    reg [R*H*16-1:0] p_word_r;
    always @* begin
        p_word_r = {(R*H*16){1'b0}};
        for (pbx = 0; pbx < H * PB; pbx = pbx + 1)
            if (pb_ok[pbx]) p_word_r[(pb_jj[pbx*5 +: 5] * H + pbx / PB) * 16 +: 16] = pb_val[pbx*16 +: 16];
    end
    assign p_word = p_word_r;
    reg [31:0] cflt;
    // KV8: the PIPE = 0 landing goes through the registered sector codec; a fmt 7 row's trailing sector (index
    // hd / 32) is the scale sector: it loads s8r, never the code banks.
    wire codec_v; wire [255:0] codec_codes; wire [31:0] codec_mask, codec_bad; wire [7:0] codec_addr;
    wire use_codec = (KV8 != 0) && (PIPE == 0);
    wire [7:0] k8_tq; wire k8_ssec, k8_land; reg s8f;
    generate for (gb = 0; gb < 32; gb = gb + 1) begin : g_cb
        wire [8:0] c16 = e4m3({c_dq[16 * (gb % 16) +: 16], 16'd0});
        wire [8:0] c32 = e4m3(c_dq[32 * (gb % 8) +: 32]);
        reg [7:0] m [0:D/32-1];
        always @(posedge clk) begin
            cflt[gb] <= 1'b0;
            if (use_codec) begin
                if (codec_v && st == S_KVC && codec_mask[gb] && !k8_ssec) begin
                    m[codec_addr] <= codec_codes[8*gb +: 8]; cflt[gb] <= codec_bad[gb];
                end
            end else if (land_c && !(KV8 != 0 && k8_ssec)) begin
                if (es_b == 2'd0) m[c_tq] <= c_dq[8*gb +: 8];
                else if (es_b == 2'd1 && c_tq[0] == gb / 16) begin m[c_tq >> 1] <= c16[7:0]; cflt[gb] <= c16[8]; end
                else if (es_b == 2'd2 && c_tq[1:0] == gb / 8) begin m[c_tq >> 2] <= c32[7:0]; cflt[gb] <= c32[8]; end
            end
        end
        genvar gi;
        for (gi = 0; gi < D / 32; gi = gi + 1) begin : g_o
            assign c_flat[8 * (gi * 32 + gb) +: 8] = m[gi];
        end
    end endgenerate
    generate for (gb = 0; gb < NT * H; gb = gb + 1) begin : g_ck
        reg [31:0] m [0:DPT-1];
        always @(posedge clk)
            if (pv_v) m[pv_c] <= pv_y[gb * 32 +: 32];
            else if (ad_o && aq[ar][12:6] == gb) m[aq[ar][5:0]] <= ad_y;
        assign ck_rd[gb * 32 +: 32] = m[ck_a];
    end endgenerate
    integer qe;
    reg [D*16-1:0] q3w;                      // PIPE = 3: the head's q word, registered with q_v
    always @* for (qe = 0; qe < D; qe = qe + 1) q_w[16 * qe +: 16] = (PIPE == 3) ? q3w[16 * qe +: 16] :
                                                                   (qload && qe < hd) ? q_flat[16 * qe +: 16] : 16'd0;
    // the ck read: S_OUT walks (hq, dq), the merge (mh, md)
    wire [9:0] ck_d = (st == S_OUT) ? dq : md; wire [4:0] ck_h = (st == S_OUT) ? hq : mh;
    always @* ck_a = ck_d % DPT;
    wire [31:0] ck_q = ck_rd[((ck_d / DPT) * H + ck_h) * 32 +: 32];
    // ---- control
    localparam [4:0] S_IDLE = 0, S_DEC = 1, S_CHK = 2, S_JOB = 3, S_QRD = 4, S_QW = 5, S_KVF = 6, S_KVC = 7,
                     S_KVP = 8, S_SCW = 9, S_PRD = 10, S_PW = 11, S_PVW = 12, S_MRG = 13, S_OUT = 14, S_DONE = 15,
                     S_FAULT = 16, S_NEXT = 17, S_MADD = 18, S_MST = 19, S_KVS = 20, S_SCO = 21, S_W3 = 22;
    // the merge adder (the golden's binary32 add) and its in-order destination FIFO
    reg ad_v; reg [31:0] ad_a, ad_b; wire ad_o; wire [31:0] ad_y; wire [1:0] ad_e;
    ot_hdc_fp32_add_fast u_add (.clk(clk), .rst_n(rst_n), .valid_in(ad_v), .a(ad_a), .b(ad_b), .y(ad_y), .err(ad_e),
        .valid_out(ad_o));
    reg [13:0] aq [0:63]; reg [5:0] aw, ar; reg [4:0] mh; reg [9:0] md; reg [11:0] mout; reg miss;
    reg [4:0] st;
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg hr_vq; reg [7:0] hr_tq; reg [255:0] hr_dq;
    always @(posedge clk) begin hr_tq <= hr_tag; hr_dq <= hr_data; end
    always @(posedge clk or negedge rst_n) if (!rst_n) hr_vq <= 1'b0; else hr_vq <= hr_v;
    generate if (KV8 != 0 && PIPE == 0) begin : g_codec
        ot_hgi_att_sector_codec u_codec (.clk(clk), .rst_n(rst_n), .in_v(hr_vq && st == S_KVC), .in_data(hr_dq),
            .in_tag(hr_tq), .in_es(es_b), .out_v(codec_v), .out_codes(codec_codes), .out_mask(codec_mask),
            .out_bad(codec_bad), .out_addr(codec_addr));
    end else begin : g_no_codec
        assign codec_v = 1'b0; assign codec_codes = 256'd0; assign codec_mask = 32'd0; assign codec_bad = 32'd0;
        assign codec_addr = 8'd0;
    end endgenerate
    assign k8_tq = use_codec ? codec_addr : c_tq;                  // the landing sector's index in the row
    assign k8_ssec = bk8 && k8_tq == hd[9:5];                            // fmt 7: the scale sector
    assign k8_land = use_codec ? (codec_v && st == S_KVC) : land_c;
    always @(posedge clk) if (KV8 != 0 && k8_land && k8_ssec) s8r <= s8d;
    // s8f: a used group's scale is 0xFF
    wire [255:0] s8d = use_codec ? codec_codes : c_dq;
    integer s8i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s8f <= 1'b0;
        else begin
            s8f <= 1'b0;
            if (KV8 != 0 && k8_land && k8_ssec)
                for (s8i = 0; s8i < 32; s8i = s8i + 1)
                    if (s8i < hd[9:5] && s8d[8 * s8i +: 8] == 8'hFF) s8f <= 1'b1;
        end
    // ---- PIPE row stream: issuer (fi_*) -> reorder slots (rob) -> in-order converter (co_*)
    reg [255:0] rob [0:RBD-1]; reg [RBD-1:0] rv; reg [7:0] fi_t, co_h; reg [8:0] occ;
    reg [20:0] fi_row, co_row; reg [7:0] fi_sec, co_sec; reg pend_row;
    wire [7:0] nsec_w = (({8'd0, hd} << es_b) >> 5) + ((KV8 != 0 && bk8) ? 8'd1 : 8'd0);
    function automatic [39:0] rowbyte(input [20:0] t);
        reg [20:0] slot;
        begin
            if (t < nb) begin
                slot = ring ? (MUT_RING ? t : ((pos1 - nb + t) & (bm - 1))) : t;
                rowbyte = bbase + (slot + MUT_ROW) * bstr;
            end else rowbyte = cbase + (t - nb) * cstr;
        end
    endfunction
    wire [7:0] co_hm = (co_h % RBD);
    wire co_copy = pend_row && (!kv_v || kv_ready);                    // the landed row leaves for the staging word
    wire co_land = (PIPE == 1) && (st == S_KVS) && rv[co_hm] && co_row < blk0 + tb && (!pend_row || co_copy);
    wire fi_go = (PIPE == 1) && (st == S_KVS) && fi_row < blk0 + tb && occ < RBD && (!hq_v || hq_rdy);
    assign land_c = (PIPE == 1) ? co_land : ((st == S_KVC) && hr_vq);
    assign c_tq = (PIPE == 1) ? co_sec : hr_tq;
    assign c_dq = (PIPE == 1) ? rob[co_hm] : hr_dq;
    always @(posedge clk) if (PIPE == 1 && hr_vq) rob[hr_tq % RBD] <= hr_dq;
    wire sc_pk = (PIPE != 0) && qk && oist == 18'd1;                    // packed sector score writes
    wire sc_kvst = st == S_KVF || st == S_KVC || st == S_KVP || st == S_SCW || st == S_KVS;
    wire [20:0] sc_nv = pc(scm);
    wire [31:0] sc_wa0 = {14'd0, obase} + sch * {14'd0, ostr} + (blk0 + scrow + scl);
    wire [20:0] sc_cnt = ((21'd8 - sc_wa0[2:0]) < (sc_nv - scl)) ? (21'd8 - sc_wa0[2:0]) : (sc_nv - scl);
    // PIPE = 2 job-buffer scores issue no VM write here (S_SCO does): never count them as outstanding (vo_n)
    wire sc_iss = sc_hold && qk && vo_n < 3'd4 && sc_kvst && !(PIPE >= 2 && sc_pk) && (sc_pk ? (sch != lanes) : (scl != NL && scm[scl]));
    reg [20:0] blk0, tb; reg [3:0] jb;               // job's first row, rows, job index
    reg [4:0] hq; reg [26:0] sec, sec_end, rsec; reg [2:0] vo_n;   // VM walk
    reg [20:0] row; reg [7:0] nsec, isec; reg [3:0] hout; reg [39:0] rbyte;
    // score beats: NL rows (lane l = row sc_row + l, sc_m mask) x H heads
    // PIPE = 2: the job's QK scores land in a per-head job buffer (one beat an edge, every head) and leave as whole
    // 8-word sector writes after the job (S_SCO) -- lanes x tb / 8 VM writes instead of one per head per beat
    wire scb = (PIPE >= 2) && sc_pk;
    reg [31:0] sbuf [0:H*JB-1]; reg [4:0] so_h; reg [20:0] so_r;
    wire [31:0] so_wa = {14'd0, obase} + so_h * {14'd0, ostr} + (blk0 + so_r);
    wire [20:0] so_cnt = ((21'd8 - so_wa[2:0]) < (tb - so_r)) ? (21'd8 - so_wa[2:0]) : (tb - so_r);
    reg [20:0] scn; reg [4:0] sch; reg [3:0] scl; reg sc_hold; reg [NL*H*32-1:0] scy; reg [20:0] scrow; reg [NL-1:0] scm;
    reg [NL*H*32-1:0] sfy [0:31]; reg [15:0] sfr_row [0:31]; reg [NL-1:0] sfm [0:31]; reg [4:0] sfw, sfr;
    // PIPE = 3 score-sector write FIFO: H (SQ + 4) entries cover every beat the engine may hold a credit for
    localparam integer WFA = (PIPE == 3) ? $clog2(H * (SQ + 4)) : 6;
    localparam integer WFD = 1 << WFA;
    reg [WFA:0] wf_n;
    wire hd_pop = (PIPE == 3) && (wf_n > WFD - 2 * H - 4);
    function automatic [20:0] pc(input [NL-1:0] m); integer x; pc = 0; for (x = 0; x < NL; x = x + 1) pc = pc + m[x]; endfunction
    reg [20:0] pw_i; reg [9:0] pvn; reg [2:0] ml; reg flt;
    reg [9:0] dq; reg [4:0] hd_o;
    integer k, j, q, e2;
    wire [1:0] es_b = (bfmt == 2'd2) ? 2'd0 : (bfmt == 2'd1) ? 2'd1 : 2'd2;    // log2 bytes an element
    wire s_land = use_codec ? codec_v : hr_vq;                         // PIPE 0: a sector has landed in cb
    wire [3:0] njobs = (tt + BLK - 1) / BLK;
    // ---- PIPE = 2: striped row lanes
    localparam integer SPRL = KVL;
    wire [20:0] l2_end = blk0 + tb;
    wire [NL-1:0] l2_imask, l2_pmask; wire [20:0] l2_pn;
    genvar ls, ll;
    for (ls = 0; ls < NL; ls = ls + 1) begin : g_l2m
        assign l2_imask[ls] = fi_row + ls < l2_end;
        assign l2_pmask[ls] = co_row + ls < l2_end;
    end
    function automatic [20:0] popc(input [NL-1:0] m); integer x; popc = 0; for (x = 0; x < NL; x = x + 1) popc = popc + m[x]; endfunction
    assign l2_pn = popc(l2_pmask);
    reg [7:0] l2_inf [0:NL-1];                          // rows in flight a slot (issued, not popped)
    wire [NL-1:0] l2_room, l2_rdy;
    wire [NL*SPRL*256-1:0] l2_head;
    reg rows_on;                                        // PIPE = 3: the job's row stream is live
    wire l2_run = (PIPE == 2) ? (st == S_KVS) : (PIPE == 3) && rows_on;
    wire l2_iss = (PIPE >= 2) && l2_run && fi_row < l2_end && (!wq_v || wq_rdy) && (&l2_room);
    wire l2_pop = (PIPE >= 2) && l2_run && co_row < l2_end && (&(l2_rdy | ~l2_pmask)) && (!kv_v || kv_ready);
    if (PIPE >= 2) begin : g_l2                          // the lanes exist only in the PIPE = 2 build
    for (ls = 0; ls < NL; ls = ls + 1) begin : g_l2s
        assign l2_room[ls] = l2_inf[ls] < RIF;
        reg [7:0] hp;                                   // head pointer (shared by the slot's lanes: rows land in order)
        wire [SPRL-1:0] lane_ok;
        for (ll = 0; ll < SPRL; ll = ll + 1) begin : g_l2l
            reg [255:0] m [0:RIF-1]; reg [7:0] tp, n;
            wire push = wl_v[ls * SPRL + ll], pop = l2_pop && l2_pmask[ls] && ll < nsec_w;
            always @(posedge clk) if (push) m[tp % RIF] <= wl_d[(ls * SPRL + ll) * 256 +: 256];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin tp <= 8'd0; n <= 8'd0; end
                else begin
                    if (push) tp <= tp + 8'd1;
                    n <= n + (push ? 8'd1 : 8'd0) - (pop ? 8'd1 : 8'd0);
                    if (push && n == RIF && !pop) $display("ot_hgi_att_unit: lane overflow");
                end
            assign lane_ok[ll] = (ll >= nsec_w) || n != 8'd0;
            assign l2_head[(ls * SPRL + ll) * 256 +: 256] = m[hp % RIF];
        end
        assign l2_rdy[ls] = &lane_ok;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin hp <= 8'd0; l2_inf[ls] <= 8'd0; end
            else begin
                if (l2_pop && l2_pmask[ls]) hp <= hp + 8'd1;
                l2_inf[ls] <= l2_inf[ls] + ((l2_iss && l2_imask[ls]) ? 8'd1 : 8'd0) - ((l2_pop && l2_pmask[ls]) ? 8'd1 : 8'd0);
            end
    end
    end else begin : g_l2n
        assign l2_room = {NL{1'b1}}; assign l2_rdy = {NL{1'b0}}; assign l2_head = {NL*SPRL*256{1'b0}};
    end
    // whole-row conversion: slot s's lanes -> D E4M3 codes -> the staging row
    // Static wiring, one generate instance per element / scale byte (continuous assigns, no wide procedural
    // part-selects): byte offsets ce, 2ce, 4ce are elaboration constants; only the per-slot scale sector
    // (lane hd/32) is a runtime select, done once per slot as a <= SPRL : 1 sector mux.
    wire [NL*ROWW-1:0] l2_row; wire [NL-1:0] l2_bad;
    genvar cs, ce, cg;
    for (cs = 0; cs < NL; cs = cs + 1) begin : g_cv
        wire [4:0] scl = hd[9:5];
        wire scl_ok = scl < SPRL;
        wire [255:0] sc_sec = scl_ok ? l2_head[(cs * SPRL + (scl_ok ? scl : 0)) * 256 +: 256] : 256'd0;
        wire [G-1:0] sbad;
        wire [D-1:0] ebad;
        for (cg = 0; cg < G; cg = cg + 1) begin : g_sc
            wire on = KV8 != 0 && bk8 && cg < scl;
            assign l2_row[cs * ROWW + cg * 265 + 256 +: 9] = {1'b0, on ? sc_sec[8 * ((cg + MUT_KV8) % G) +: 8] : 8'd127};
            assign sbad[cg] = on && l2_pmask[cs] && sc_sec[8 * cg +: 8] == 8'hFF;
        end
        for (ce = 0; ce < D; ce = ce + 1) begin : g_el
            localparam integer L1 = ((MUT_LANE != 0 && ((ce) >> 5) == 1) ? 0 : ((ce) >> 5)) % SPRL;
            localparam integer L2 = ((MUT_LANE != 0 && ((2 * ce) >> 5) == 1) ? 0 : ((2 * ce) >> 5)) % SPRL;
            localparam integer L4 = ((MUT_LANE != 0 && ((4 * ce) >> 5) == 1) ? 0 : ((4 * ce) >> 5)) % SPRL;
            wire [31:0] x_ = (es_b == 2'd1) ? {l2_head[(cs * SPRL + L2) * 256 + 8 * ((2 * ce) % 32) +: 16], 16'd0}
                                            : l2_head[(cs * SPRL + L4) * 256 + 8 * ((4 * ce) % 32) +: 32];
            wire [8:0] c = (es_b == 2'd0) ? {1'b0, l2_head[(cs * SPRL + L1) * 256 + 8 * ((ce) % 32) +: 8]} : e4m3(x_);
            wire on = ce < hd;
            assign l2_row[cs * ROWW + (ce / 32) * 265 + 8 * (ce % 32) +: 8] = on ? c[7:0] : 8'd0;
            assign ebad[ce] = on && l2_pmask[cs] && c[8];
        end
        assign l2_bad[cs] = (|sbad) || (|ebad);
    end

    // ================= PIPE = 3: the local VM slice wide client =================
    localparam integer NW = 32;
    function automatic [26:0] w3base(input [4:0] h);    // word address of element / row 0 of head h's A operand
        w3base = {9'd0, abase} + h * {9'd0, astr} + (qk ? 27'd0 : {6'd0, blk0});
    endfunction
    wire [20:0] w3n = qk ? {11'd0, hd} : tb;            // elements a head
    function automatic [26:0] w3last(input [4:0] h); w3last = (w3base(h) + {6'd0, w3n} - 27'd1) >> 3; endfunction
    // ---- wide READ loader: heads in order, up to 32 consecutive sectors a cycle (a prefix of lanes with credit)
    reg ld_on; reg [4:0] ld_h; reg [26:0] ld_s; reg [3:0] xr_c [0:NW-1];
    reg [31:0] xr_f [0:NW-1][0:15]; reg [3:0] xr_fh [0:NW-1]; reg [3:0] xr_ft [0:NW-1];
    reg [7:0] ld_cnt [0:H-1];                           // sectors landed a head
    reg [15:0] qbuf [0:H*D-1]; reg [15:0] pbuf [0:H*JB-1]; reg [31:0] obuf [0:H*D-1];
    reg [NW-1:0] ri_v; reg [26:0] ri_s [0:NW-1]; reg [5:0] ri_n;
    integer ix3, b3x, w3x, h3x, k3x;
    always @* begin : w3ri
        reg [26:0] s_; reg stop;
        ri_v = {NW{1'b0}}; ri_n = 6'd0; stop = 1'b0;
        for (ix3 = 0; ix3 < NW; ix3 = ix3 + 1) begin
            s_ = ld_s + ix3; ri_s[ix3] = 27'd0;
            if (!stop && ld_on && s_ <= w3last(ld_h) && xr_c[s_[4:0]] != 4'd0) begin ri_v[s_[4:0]] = 1'b1; ri_n = ix3 + 1; end
            else stop = 1'b1;
        end
        for (ix3 = 0; ix3 < NW; ix3 = ix3 + 1) ri_s[(ld_s[4:0] + ix3) % NW] = ld_s + ix3;
    end
    wire [26:0] ld_nx = ld_s + {21'd0, ri_n};
    wire [7:0] w3need [0:H-1];
    for (genvar g3 = 0; g3 < H; g3 = g3 + 1) begin : g_w3n
        assign w3need[g3] = 8'(w3last(g3[4:0]) - (w3base(g3[4:0]) >> 3) + 27'd1);
    end
    reg [4:0] q3_h;                                     // QK: next q head to the engine
    wire q3_rdy = q3_h >= lanes || ld_cnt[q3_h] == w3need[q3_h];
    reg p3_all;                                         // PV: every head's p landed
    integer pa3;
    always @* begin p3_all = !ld_on; for (pa3 = 0; pa3 < H; pa3 = pa3 + 1) if (pa3 < lanes && ld_cnt[pa3] != w3need[pa3]) p3_all = 1'b0; end
    // ---- wide WRITE side: score sectors (FIFO, <= 4 distinct-bank sectors a cycle) or the O burst (32 a cycle)
    reg [290:0] wf [0:WFD-1]; reg [WFA-1:0] wf_h, wf_t;    // {sector 27, data 256, mask 8}
    reg [3:0] xw_c [0:NW-1]; reg [12:0] xw_out;
    // ---- back-path snapshots (PIPE = 3): taken at the job's start, read only by the back paths
    reg sc_busy, scx_last; reg [17:0] scx_ob, scx_os; reg [20:0] scx_b0, scx_tb; reg [4:0] scx_ln;
    reg pv_busy, pvx_last, pvx_multi, pvx_og; reg [17:0] pvx_ob, pvx_os; reg [9:0] pvx_hd; reg [4:0] pvx_ln;
    wire [17:0] scx_obu = (MUT_OVL != 0) ? obase : scx_ob;   // MUT_OVL: the FRONT's live O base
    wire [17:0] pvx_obu = (MUT_OVL != 0) ? obase : pvx_ob;
    reg o3_on; reg [4:0] o3_h; reg [26:0] o3_s;         // O burst: head, next sector
    wire [26:0] o3_b = {9'd0, pvx_obu} + o3_h * {9'd0, pvx_os};
    wire [26:0] o3_e = (o3_b + {17'd0, pvx_hd} - 27'd1) >> 3;
    reg [NW-1:0] wi_v; reg [279:0] wi_q [0:NW-1]; reg [5:0] wi_n, wi_f;
    always @* begin : w3wi
        reg [26:0] s_; reg stop; reg [NW-1:0] seen; reg [290:0] e_; reg [255:0] d_; reg [7:0] m_; integer w_; reg [31:0] a_;
        wi_v = {NW{1'b0}}; wi_n = 6'd0; wi_f = 6'd0; stop = 1'b0; seen = {NW{1'b0}};
        for (ix3 = 0; ix3 < NW; ix3 = ix3 + 1) wi_q[ix3] = 280'd0;
        if (o3_on) begin
            for (ix3 = 0; ix3 < NW; ix3 = ix3 + 1) begin
                s_ = o3_s + ix3;
                if (!stop && s_ <= o3_e && xw_c[s_[4:0]] != 4'd0) begin
                    d_ = 256'd0; m_ = 8'd0;
                    for (w_ = 0; w_ < 8; w_ = w_ + 1) begin
                        a_ = {s_, 3'(w_)} - o3_b;
                        if ({s_, 3'(w_)} >= o3_b && a_ < pvx_hd) begin d_[32 * w_ +: 32] = obuf[o3_h * D + a_]; m_[w_] = 1'b1; end
                    end
                    wi_v[s_[4:0]] = 1'b1; wi_q[s_[4:0]] = {1'b1, s_[14:0], d_, m_}; wi_n = ix3 + 1;
                end else stop = 1'b1;
            end
        end else begin
            for (ix3 = 0; ix3 < 4; ix3 = ix3 + 1) begin
                e_ = wf[(wf_h + ix3) % WFD];
                if (!stop && ix3 < wf_n && !seen[e_[268:264]] && xw_c[e_[268:264]] != 4'd0) begin
                    seen[e_[268:264]] = 1'b1; wi_v[e_[268:264]] = 1'b1; wi_q[e_[268:264]] = {1'b1, e_[278:264], e_[263:0]};
                    wi_f = ix3 + 1;
                end else stop = 1'b1;
            end
        end
    end
    // ---- score sector closes: the beat written to sbuf last edge (rows b3_r0 .. b3_r1 of the job)
    reg b3_v; reg [20:0] b3_r0, b3_r1;
    reg [290:0] cl_e [0:2*H-1]; reg [5:0] cl_n;
    always @* begin : w3cl
        reg [31:0] base_, a_, s0_; integer r_, c_, w_; reg [255:0] d_; reg [7:0] m_; reg [20:0] lo_;
        cl_n = 6'd0;
        for (c_ = 0; c_ < 2 * H; c_ = c_ + 1) cl_e[c_] = 291'd0;
        if (b3_v)
            for (h3x = 0; h3x < H; h3x = h3x + 1) if (h3x < scx_ln) begin
                base_ = {14'd0, scx_obu} + h3x * {14'd0, scx_os} + {11'd0, scx_b0};
                for (r_ = 0; r_ < NL; r_ = r_ + 1)
                    if (b3_r0 + r_ <= b3_r1 && (((base_ + b3_r0 + r_) % 8) == 7 || b3_r0 + r_ == scx_tb - 1)) begin
                        a_ = base_ + b3_r0 + r_; s0_ = a_ & ~32'd7;     // the sector's first word
                        d_ = 256'd0; m_ = 8'd0;
                        for (w_ = 0; w_ < 8; w_ = w_ + 1)
                            if (s0_ + w_ >= base_ && s0_ + w_ <= a_) begin
                                d_[32 * w_ +: 32] = sbuf[h3x * JB + (s0_ + w_ - base_)];
                                m_[w_] = !(MUT_W3 != 0 && s0_ + w_ == a_);
                            end
                        cl_e[cl_n] = {s0_[29:3], d_, m_}; cl_n = cl_n + 1;
                    end
            end
    end
    always @(posedge clk) if (PIPE == 3) begin
        for (b3x = 0; b3x < NW; b3x = b3x + 1) begin
            xr_q[b3x * 16 +: 16] <= {ri_v[b3x], ri_s[b3x][14:0]};
            xw_q[b3x * 280 +: 280] <= wi_v[b3x] ? wi_q[b3x] : 280'd0;
        end
        for (b3x = 0; b3x < NW; b3x = b3x + 1) if (ri_v[b3x]) xr_f[b3x][xr_ft[b3x]] <= {ld_h, ri_s[b3x]};
        for (b3x = 0; b3x < NW; b3x = b3x + 1) if (wi_v[b3x]) xt_m[b3x][xt_w[b3x]] <= o3_on;   // write tag: 1 = O burst
        for (b3x = 0; b3x < NW; b3x = b3x + 1) if (xr_d[b3x * 257 + 256]) begin : land
            reg [31:0] f_; reg [26:0] bs_; reg [26:0] e_;
            f_ = xr_f[b3x][xr_fh[b3x]]; bs_ = w3base(f_[31:27]);
            for (w3x = 0; w3x < 8; w3x = w3x + 1) begin
                e_ = {f_[26:0], 3'(w3x)} - bs_;
                if ({f_[26:0], 3'(w3x)} >= bs_ && e_ < w3n) begin
                    if (qk) qbuf[f_[31:27] * D + e_] <= xr_d[b3x * 257 + 32 * w3x + 16 +: 16];
                    else pbuf[f_[31:27] * JB + e_] <= xr_d[b3x * 257 + 32 * w3x + 16 +: 16];
                end
            end
        end
        for (k3x = 0; k3x < cl_n; k3x = k3x + 1) wf[(wf_t + k3x) % WFD] <= cl_e[k3x];
        if (pv_v) for (k3x = 0; k3x < NT; k3x = k3x + 1) for (h3x = 0; h3x < H; h3x = h3x + 1)
            obuf[h3x * D + k3x * DPT + pv_c] <= pv_y[(k3x * H + h3x) * 32 +: 32];
        else if (ad_o) obuf[(aq[ar][12:6] % H) * D + (aq[ar][12:6] / H) * DPT + aq[ar][5:0]] <= ad_y;
    end
    // q / p BF16 check on landing (fault), credits, FIFO pointers, landed counts
    reg w3f;
    // per-lane write tag FIFOs (a lane's writes complete in order): xo0 score-path / xo1 O-burst writes outstanding
    reg xt_m [0:NW-1][0:LQW-1]; reg [3:0] xt_w [0:NW-1], xt_r [0:NW-1]; reg [12:0] xo0, xo1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (b3x = 0; b3x < NW; b3x = b3x + 1) begin xr_c[b3x] <= LQW; xw_c[b3x] <= LQW; xr_fh[b3x] <= 4'd0; xr_ft[b3x] <= 4'd0;
                xt_w[b3x] <= 4'd0; xt_r[b3x] <= 4'd0; end
            wf_h <= '0; wf_t <= '0; wf_n <= '0; xw_out <= 13'd0; w3f <= 1'b0; xo0 <= 13'd0; xo1 <= 13'd0;
        end else if (PIPE == 3) begin : cr3
            integer i0_, i1_, d0_, d1_;
            i0_ = 0; i1_ = 0; d0_ = 0; d1_ = 0;
            for (b3x = 0; b3x < NW; b3x = b3x + 1) begin
                if (wi_v[b3x]) begin xt_w[b3x] <= (xt_w[b3x] + 4'd1) % LQW; if (o3_on) i1_ = i1_ + 1; else i0_ = i0_ + 1; end
                if (xw_done[b3x]) begin xt_r[b3x] <= (xt_r[b3x] + 4'd1) % LQW; if (xt_m[b3x][xt_r[b3x]]) d1_ = d1_ + 1; else d0_ = d0_ + 1; end
            end
            xo0 <= xo0 + 13'(i0_) - 13'(d0_); xo1 <= xo1 + 13'(i1_) - 13'(d1_);
            w3f <= 1'b0;
            for (b3x = 0; b3x < NW; b3x = b3x + 1) begin
                xr_c[b3x] <= xr_c[b3x] - (ri_v[b3x] ? 4'd1 : 4'd0) + (xr_cr[b3x] ? 4'd1 : 4'd0);
                xw_c[b3x] <= xw_c[b3x] - (wi_v[b3x] ? 4'd1 : 4'd0) + (xw_cr[b3x] ? 4'd1 : 4'd0);
                if (ri_v[b3x]) xr_ft[b3x] <= xr_ft[b3x] + 4'd1;
                if (xr_d[b3x * 257 + 256]) begin : chk
                    reg [31:0] f_; reg [26:0] bs_; reg [26:0] e_;
                    f_ = xr_f[b3x][xr_fh[b3x]]; bs_ = w3base(f_[31:27]);
                    xr_fh[b3x] <= xr_fh[b3x] + 4'd1;
                    for (w3x = 0; w3x < 8; w3x = w3x + 1) begin
                        e_ = {f_[26:0], 3'(w3x)} - bs_;
                        if ({f_[26:0], 3'(w3x)} >= bs_ && e_ < w3n && xr_d[b3x * 257 + 32 * w3x +: 16] != 16'd0) w3f <= 1'b1;
                    end
                end
            end
            wf_t <= (wf_t + cl_n) % WFD; wf_h <= (wf_h + wi_f) % WFD; wf_n <= wf_n + {1'b0, cl_n} - {1'b0, wi_f};
            if (wf_n + cl_n > WFD) $display("ot_hgi_att_unit: score FIFO overflow");
            xw_out <= xw_out + 13'($countones(wi_v)) - 13'($countones(xw_done));
        end
    // landed sectors a head (reset at each job start, S_JOB -> S_W3)
    always @(posedge clk) if (PIPE == 3) begin
        if (st == S_JOB && j3_go) for (h3x = 0; h3x < H; h3x = h3x + 1) ld_cnt[h3x] <= 8'd0;
        else for (h3x = 0; h3x < H; h3x = h3x + 1) begin : lc
            integer n_; n_ = 0;
            for (b3x = 0; b3x < NW; b3x = b3x + 1) if (xr_d[b3x * 257 + 256] && xr_f[b3x][xr_fh[b3x]][31:27] == h3x) n_ = n_ + 1;
            ld_cnt[h3x] <= ld_cnt[h3x] + 8'(n_);
        end
    end
    // ---- PIPE = 3 back-path control: credit return against the wf reservation, completion, in-order retire
    reg [8:0] cw;                                       // score beats received whose credit is still held
    reg j3_go;                                          // FRONT: first cycle of a job (start the loads / rows)
    wire [31:0] sc_rsv = 32'(wf_n) + (b3_v ? 32'(2 * H) : 32'd0) + 32'(H) * (32'(SQ) + 32'd2 - 32'(cw));
    wire sc_ret = (PIPE == 3) && cw != 9'd0 && sc_rsv <= 32'(WFD);
    wire sc_cpl = sc_busy && scn == scx_tb && !b3_v && wf_n == 0 && xo0 == 13'd0;
    wire pv_cpl = pv_busy && pvx_og && !o3_on && xo1 == 13'd0;
    wire ret_sc = (PIPE == 3) && sc_cpl && scx_last && rf_n != 3'd0 && !rf_k[rf_h];
    wire ret_pv = (PIPE == 3) && pv_cpl && pvx_last && rf_n != 3'd0 && rf_k[rf_h];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; raw_v <= 1'b0; busy <= 1'b0; halt_q <= 1'b0; rec_done <= 1'b0; rec_fault <= 1'b0;
            vmq <= 338'd0; hq_v <= 1'b0; wq_v <= 1'b0; wq_sv <= {NL{1'b0}}; wq_row <= {NL*40{1'b0}}; wq_nsec <= 8'd0; job_v <= 1'b0; q_v <= 1'b0; kv_v <= 1'b0; sc_cr <= 1'b0; p_v <= 1'b0;
            pv_cr <= 1'b0; flt <= 1'b0; vo_n <= 3'd0; sc_hold <= 1'b0; scn <= 21'd0; pvn <= 10'd0; ad_v <= 1'b0;
            rows_on <= 1'b0; ld_on <= 1'b0; o3_on <= 1'b0; b3_v <= 1'b0; q3_h <= 5'd0;
            sc_busy <= 1'b0; pv_busy <= 1'b0; pvx_og <= 1'b0; rf_n <= 3'd0; rf_h <= 2'd0; cw <= 9'd0; j3_go <= 1'b0;
            sfw <= 5'd0; sfr <= 5'd0;
            aw <= 6'd0; ar <= 6'd0;
            rv <= {RBD{1'b0}}; occ <= 9'd0; fi_t <= 8'd0; co_h <= 8'd0; pend_row <= 1'b0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0; vmq[337] <= 1'b0; job_v <= 1'b0; sc_cr <= 1'b0; pv_cr <= 1'b0;
            ad_v <= 1'b0;
            if (|cflt || s8f || w3f) flt <= 1'b1;
            b3_v <= 1'b0;
            if (PIPE == 3 && ld_on) begin                           // wide read loader: next sectors / head
                ld_s <= ld_nx;
                if (ld_nx > w3last(ld_h)) begin
                    if (ld_h + 5'd1 >= lanes) ld_on <= 1'b0;
                    else begin ld_h <= ld_h + 5'd1; ld_s <= w3base(ld_h + 5'd1) >> 3; end
                end
            end
            if (PIPE == 3 && o3_on) begin                           // O burst: next sectors / head
                o3_s <= o3_s + {21'd0, wi_n};
                if (o3_s + {21'd0, wi_n} > o3_e) begin
                    if (o3_h + 5'd1 >= pvx_ln) o3_on <= 1'b0;
                    else begin o3_h <= o3_h + 5'd1; o3_s <= ({9'd0, pvx_obu} + (o3_h + 5'd1) * {9'd0, pvx_os}) >> 3; end
                end
            end
            if (ad_o) begin ar <= ar + 6'd1; if (ad_e != 2'd0) flt <= 1'b1; end
            if (rec_v && rec_rdy) raw_v <= 1'b1;
            if (hq_v && hq_rdy) hq_v <= 1'b0;
            if (q_v && q_ready) q_v <= 1'b0;
            if (kv_v && kv_ready) kv_v <= 1'b0;
            if (p_v && p_ready) p_v <= 1'b0;
            // pv beats: capture (PV) and return the credit
            if (pv_v) begin
                for (k = 0; k < NT; k = k + 1) for (j = 0; j < H; j = j + 1)
                    if ((PIPE == 3) ? (j < pvx_ln && k * DPT + pv_c < pvx_hd && pv_f[k * H + j])
                                    : (!qk && j < lanes && k * DPT + pv_c < hd && pv_f[k * H + j])) flt <= 1'b1;
                pv_cr <= 1'b1; pvn <= pvn + 10'd1;
            end
            if (PIPE == 3) begin                                    // ---- BACK: score path, one beat a cycle
                if (sc_v) begin
                    for (k = 0; k < NL; k = k + 1) for (j = 0; j < H; j = j + 1)
                        if (sc_m[k] && j < scx_ln) begin
                            sbuf[j * JB + sc_row + k] <= sc_y[32 * (k * H + j) +: 32];
                            if (sc_f[k * H + j]) flt <= 1'b1;
                        end
                    b3_v <= 1'b1; b3_r0 <= {5'd0, sc_row}; b3_r1 <= {5'd0, sc_row} + pc(sc_m) - 21'd1; scn <= scn + pc(sc_m);
                end
                cw <= cw + (sc_v ? 9'd1 : 9'd0) - (sc_ret ? 9'd1 : 9'd0); sc_cr <= sc_ret;
                // path completion: the last job of a record retires in order (rf), an earlier job frees the path
                if (sc_cpl && (!scx_last || ret_sc)) sc_busy <= 1'b0;
                if (pv_busy && !pvx_multi && !pvx_og && pvn == DPT) begin
                    o3_on <= 1'b1; o3_h <= 5'd0; o3_s <= {9'd0, pvx_obu} >> 3; pvx_og <= 1'b1;
                end
                if (pv_cpl && ret_pv) pv_busy <= 1'b0;
                if (ret_sc || ret_pv) begin rec_done <= 1'b1; rf_h <= rf_h + 2'd1; end
                rf_n <= rf_n + ((st == S_DEC) ? 3'd1 : 3'd0) - ((ret_sc || ret_pv) ? 3'd1 : 3'd0);
                if (st == S_DEC) rf_k[rf_h + rf_n[1:0]] <= (op != 6'd0);
            end
            // score beats: QK writes heads < lanes to O (one masked word a VM write), PV discards
            // score FIFO (SQ = the engine's credits): push every beat; the head is written, then its credit returns
            if (PIPE != 3) begin
            if (sc_v) begin sfy[sfw] <= sc_y; sfr_row[sfw] <= sc_row; sfm[sfw] <= sc_m; sfw <= sfw + 5'd1;
                for (k = 0; k < NL; k = k + 1) for (j = 0; j < H; j = j + 1)
                    if (qk && sc_m[k] && j < lanes && sc_f[k * H + j]) flt <= 1'b1; end
            if (!sc_hold && sfr != sfw && !hd_pop) begin
                sc_hold <= 1'b1; scy <= sfy[sfr]; scrow <= {5'd0, sfr_row[sfr]}; scm <= sfm[sfr]; sch <= 5'd0;
                scl <= 4'd0; sfr <= sfr + 5'd1;
            end
            if (sc_hold && scb) begin
                for (k = 0; k < NL; k = k + 1) for (j = 0; j < H; j = j + 1)
                    if (scm[k] && j < lanes) sbuf[j * JB + scrow + k] <= scy[32 * (k * H + j) +: 32];
                sc_hold <= 1'b0; sc_cr <= 1'b1; scn <= scn + pc(scm);
                b3_v <= (PIPE == 3); b3_r0 <= scrow; b3_r1 <= scrow + pc(scm) - 21'd1;
            end else if (sc_hold && sc_pk) begin
                if (sch == lanes) begin
                    sc_hold <= 1'b0; sc_cr <= 1'b1;
                    scn <= scn + pc(scm);
                end else if (sc_iss) begin : scwp
                    reg [255:0] wd; reg [31:0] wm; integer w, ix;
                    wd = 256'd0; wm = 32'd0;
                    for (w = 0; w < 8; w = w + 1) begin
                        ix = w - sc_wa0[2:0];
                        if (ix >= 0 && ix < sc_cnt) begin
                            wd[32 * w +: 32] = scy[32 * ((scl + ix) * H + sch) +: 32]; wm[4 * w +: 4] = 4'hF;
                        end
                    end
                    vmq <= {1'b1, 1'b1, sc_wa0[29:3], 5'd0, wd, wm, 16'h4157};
                    if (scl + sc_cnt >= sc_nv) begin scl <= 4'd0; sch <= sch + 5'd1; end else scl <= scl + sc_cnt[3:0];
                end
            end else if (sc_hold) begin
                if (!qk || scl == NL || !scm[scl]) begin
                    sc_hold <= 1'b0; sc_cr <= 1'b1;
                    scn <= scn + pc(scm);
                end
                else if (st == S_KVF || st == S_KVC || st == S_KVP || st == S_SCW) begin
                    if (vo_n < 3'd4) begin : scw
                        reg [31:0] wa;
                        wa = {14'd0, obase} + sch * {14'd0, ostr} + (blk0 + scrow + scl) * {14'd0, oist};
                        vmq <= {1'b1, 1'b1, wa[29:3], 5'd0, {8{scy[32 * (scl * H + sch) +: 32]}}, 32'hF << (4 * wa[2:0]),
                                16'h4157};
                        if (sch == lanes - 1) begin sch <= 5'd0; scl <= scl + 4'd1; end else sch <= sch + 5'd1;
                    end
                end
            end
            if (sc_kvst)
                vo_n <= vo_n + (sc_iss ? 3'd1 : 3'd0) - (vr[273] ? 3'd1 : 3'd0);
            end
            if (PIPE >= 2) begin                                    // striped row lanes (S_KVS / PIPE 3 rows_on)
                if (wq_v && wq_rdy) wq_v <= 1'b0;
                if (l2_iss) begin
                    wq_v <= 1'b1; wq_sv <= l2_imask; wq_nsec <= nsec_w;
                    for (k = 0; k < NL; k = k + 1) wq_row[k * 40 +: 40] <= rowbyte(fi_row + k);
                    fi_row <= fi_row + NL;
                end
                if (l2_pop) begin
                    for (k = 0; k < NL; k = k + 1) kv_w[k * ROWW +: ROWW] <= l2_row[k * ROWW +: ROWW];
                    kv_v <= 1'b1; kv_m <= l2_pmask; co_row <= co_row + l2_pn;
                    if (|l2_bad) flt <= 1'b1;
                end
            end
            if (PIPE == 1) begin                                    // the row stream (S_KVS)
                if (fi_go) begin
                    hq_v <= 1'b1; hq_addr <= (rowbyte(fi_row) >> 5) + fi_sec; hq_tag <= fi_t;
                    fi_t <= fi_t + 8'd1;
                    if (fi_sec == nsec_w - 8'd1) begin fi_sec <= 8'd0; fi_row <= fi_row + 21'd1; end else fi_sec <= fi_sec + 8'd1;
                end
                occ <= occ + (fi_go ? 9'd1 : 9'd0) - (co_land ? 9'd1 : 9'd0);
                if (hr_vq) rv[hr_tq % RBD] <= 1'b1;
                if (co_land) begin
                    rv[co_hm] <= 1'b0; co_h <= co_h + 8'd1;
                    if (co_sec == nsec_w - 8'd1) begin co_sec <= 8'd0; end else co_sec <= co_sec + 8'd1;
                end
                if (co_copy) begin
                    kv_w[kl * ROWW +: ROWW] <= kv_row;
                    if (kl == NL - 1 || co_row == blk0 + tb - 21'd1) begin
                        kv_v <= 1'b1; kv_m <= (({{(NL-1){1'b0}}, 1'b1} << (kl + 1)) - 1); kl <= 4'd0;
                    end else kl <= kl + 4'd1;
                    co_row <= co_row + 21'd1;
                end
                pend_row <= (co_land && co_sec == nsec_w - 8'd1) ? 1'b1 : (co_copy ? 1'b0 : pend_row);
            end
            if (flt && st != S_FAULT && (st != S_IDLE || (PIPE == 3 && !halt_q))) st <= S_FAULT;
            else case (st)
                S_IDLE: if (raw_v) begin raw_v <= 1'b0; busy <= 1'b1; st <= S_DEC; end
                S_DEC: begin
                    qk <= (op == 6'd0); lanes <= (prm[3:0] == 4'd0) ? 5'd16 : {1'b0, prm[3:0]}; ring <= prm[8];
                    hd <= (op == 6'd0) ? mn(da)[9:0] : mn(dout)[9:0];
                    tt <= nb + (hasc ? nc : 21'd0);
                    bfmt <= (KV8 != 0 && db[4:2] == 3'd7) ? 2'd2 : (!db[4] ? db[3:2] : 2'd3);
                    cfmt <= (KV8 != 0 && dc[4:2] == 3'd7) ? 2'd2 : (!dc[4] ? dc[3:2] : 2'd3);
                    bk8 <= (KV8 != 0) && db[4:2] == 3'd7; ck8 <= (KV8 != 0) && dc[4:2] == 3'd7;
                    abase <= mbase(da)[17:0]; astr <= mst(da)[17:0]; obase <= mbase(dout)[17:0]; ostr <= mst(dout)[17:0];
                    oist <= {2'b00, mist(dout)}; bbase <= mbase(db); cbase <= mbase(dc); bstr <= mst(db); cstr <= mst(dc);
                    bm <= mm(db);
                    st <= S_CHK;
                end
                S_CHK: begin
                    if (hdr[127:124] != 4'd5 || op > 6'd1 || !opnd[0] || !opnd[1] || !opnd[4] || da[1:0] != 2'd1 ||
                        dout[1:0] != 2'd1 || db[1:0] != 2'd0 || (hasc && dc[1:0] != 2'd0) || bfmt == 2'd3 ||
                        (hasc && (cfmt != bfmt || ck8 != bk8)) || hd == 0 || hd > D || hd[4:0] != 0 || tt == 0 ||
                        lanes > H || (ring && (bm == 0 || (bm & (bm - 1)) != 0 || {1'b0, bm} < nb)) ||
                        (!qk && mn(da) != tt[19:0]) || (qk && mn(dout) != tt[19:0]) || bbase[4:0] != 0 ||
                        bstr[4:0] != 0 || (hasc && (cbase[4:0] != 0 || cstr[4:0] != 0)) ||
                        (PIPE >= 2 && nsec_w > KVL) || (PIPE == 3 && qk && oist != 18'd1))
                        st <= S_FAULT;
                    else begin blk0 <= 21'd0; jb <= 4'd0; st <= S_JOB; j3_go <= (PIPE == 3); end
                end
                // ---- one engine job: rows blk0 .. blk0 + tb - 1
                S_JOB: if (PIPE == 3) begin : j3
                    reg [20:0] tj;                                  // one job when T <= TROWS1, else BLK-row jobs
                    tj = (tt <= TROWS1) ? tt : ((tt - blk0 > BLK) ? BLK : tt - blk0);
                    if (j3_go) begin                                // the loads and the row stream start now,
                        tb <= tj; j3_go <= 1'b0;                    // during the previous record's tail
                        fi_row <= blk0; co_row <= blk0; rows_on <= 1'b1; q3_h <= 5'd0; pw_i <= 21'd0;
                        ld_on <= 1'b1; ld_h <= 5'd0; ld_s <= ({9'd0, abase} + (qk ? 27'd0 : {6'd0, blk0})) >> 3;
                    end else if (job_ready && !job_v && (qk ? !sc_busy : !pv_busy)) begin
                        // the engine job, once the engine and this op's back path are free: snapshot the tail context
                        job_v <= 1'b1; job_t <= tb[15:0] | (qk ? 16'h2000 : 16'h4000);
                        if (qk) begin
                            scn <= 21'd0; sc_busy <= 1'b1; scx_last <= blk0 + tb >= tt; scx_ob <= obase; scx_os <= ostr;
                            scx_b0 <= blk0; scx_tb <= tb; scx_ln <= lanes;
                        end else begin
                            pvn <= 10'd0; pv_busy <= 1'b1; pvx_last <= blk0 + tb >= tt; pvx_multi <= tt > TROWS1;
                            pvx_og <= 1'b0; pvx_ob <= obase; pvx_os <= ostr; pvx_hd <= hd; pvx_ln <= lanes;
                        end
                        st <= S_W3;
                    end
                end else begin
                    tb <= (tt - blk0 > BLK) ? BLK : tt - blk0;
                    if (job_ready && !job_v) begin
                        job_v <= 1'b1; job_t <= ((tt - blk0 > BLK) ? BLK : tt - blk0); hq <= 5'd0; scn <= 21'd0; pvn <= 10'd0;
                        st <= S_QRD; 
                        sec <= abase >> 3; sec_end <= ({9'd0, abase} + {17'd0, hd} - 27'd1) >> 3;
                        rsec <= abase >> 3; vo_n <= 3'd0;
                    end
                end
                // ---- PIPE = 3 job body: rows, q / p loads, q / p words, scores / pv all overlap
                S_W3: begin
                    if (qk && q3_h < H && q3_rdy && (!q_v || q_ready)) begin : q3s
                        integer e_;
                        for (e_ = 0; e_ < D; e_ = e_ + 1)
                            q3w[16 * e_ +: 16] <= (q3_h < lanes && e_ < hd) ? qbuf[q3_h * D + e_] : 16'd0;
                        q_v <= 1'b1; q3_h <= q3_h + 5'd1;
                    end
                    if (!qk && p3_all && (!p_v || p_ready) && pw_i * R < tb) begin : p3s
                        reg [TD*16-1:0] w; integer jj, hh;
                        w = {(TD*16){1'b0}};
                        for (jj = 0; jj < R; jj = jj + 1) for (hh = 0; hh < H; hh = hh + 1)
                            if (hh < lanes && pw_i * R + jj < tb) w[(jj * H + hh) * 16 +: 16] = pbuf[hh * JB + pw_i * R + jj];
                        p_w <= w; p_v <= 1'b1; pw_i <= pw_i + 21'd1;
                    end
                    // the FRONT is done with the job once its rows and q / p words are in the engine; the tail runs
                    // on the back path (next record / job accepted now)
                    if (co_row == blk0 + tb && !kv_v && !ld_on) begin
                        if (qk && q3_h == H && !q_v) begin
                            rows_on <= 1'b0;
                            if (blk0 + tb >= tt) begin busy <= 1'b0; st <= S_IDLE; end
                            else begin blk0 <= blk0 + tb; jb <= jb + 4'd1; j3_go <= 1'b1; st <= S_JOB; end
                        end
                        if (!qk && pw_i * R >= tb && !p_v) begin
                            rows_on <= 1'b0;
                            if (tt <= TROWS1) begin busy <= 1'b0; st <= S_IDLE; end
                            else st <= S_PVW;                       // multi-job: the FRONT merges (serial)
                        end
                    end
                end
                S_QRD: begin                                        // q[hq]: hd words of A row hq (QK, hq < lanes)
                    if (!qk || hq >= lanes) begin
                        if (!q_v || q_ready) begin q_v <= 1'b1; qload <= 1'b0; st <= S_QW; end
                    end else begin
                        if (vo_n < 3'd4 && sec <= sec_end) begin
                            vmq <= {1'b1, 1'b0, sec, 5'd0, 256'd0, 32'd0, 16'h4151}; sec <= sec + 27'd1;
                        end
                        if (vr[273] && !vr[256]) begin
                            for (q = 0; q < 8; q = q + 1) begin
                                e2 = {rsec, q[2:0]} - ({9'd0, abase} + hq * {9'd0, astr});
                                if (e2 >= 0 && e2 < hd && vr[32*q +: 16] != 16'd0) flt <= 1'b1;   // q is BF16
                            end
                            rsec <= rsec + 27'd1;
                        end
                        vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                        if (rsec > sec_end && vo_n == 3'd0 && (!q_v || q_ready)) begin q_v <= 1'b1; qload <= 1'b1; st <= S_QW; end
                    end
                end
                S_QW: if (!q_v || q_ready) begin
                    if (q_v && q_ready || !q_v) begin
                        if (hq == H - 1) begin
                            row <= blk0; kl <= 4'd0; vo_n <= 3'd0;
                            st <= (PIPE != 0) ? S_KVS : S_KVF;
                            fi_row <= blk0; fi_sec <= 8'd0; co_row <= blk0; co_sec <= 8'd0; pend_row <= 1'b0;
                        end
                        else begin
                            hq <= hq + 5'd1; 
                            sec <= ({9'd0, abase} + (hq + 1) * {9'd0, astr}) >> 3;
                            rsec <= ({9'd0, abase} + (hq + 1) * {9'd0, astr}) >> 3;
                            sec_end <= ({9'd0, abase} + (hq + 1) * {9'd0, astr} + {17'd0, hd} - 27'd1) >> 3;
                            st <= S_QRD;
                        end
                    end
                end
                // ---- rows: fetch row `row` (all sectors, NOUT outstanding, any order), convert, push
                S_KVF: begin
                    begin : ra
                        reg [20:0] t; reg [39:0] b; reg [31:0] s; reg [20:0] slot;
                        t = row;
                        if (t < nb) begin
                            slot = ring ? (MUT_RING ? t : ((pos1 - nb + t) & (bm - 1))) : t;
                            b = bbase + (slot + MUT_ROW) * bstr;
                        end else b = cbase + (t - nb) * cstr;
                        rbyte <= b;
                    end
                    nsec <= nsec_w; isec <= 8'd0; hout <= 4'd0;
                    st <= S_KVC;
                end
                S_KVC: begin
                    if ((!hq_v || hq_rdy) && isec < nsec && hout < NOUT) begin
                        hq_v <= 1'b1; hq_addr <= (rbyte >> 5) + isec; hq_tag <= isec; isec <= isec + 8'd1;
                    end
                    hout <= hout + (((!hq_v || hq_rdy) && isec < nsec && hout < NOUT) ? 4'd1 : 4'd0) - (s_land ? 4'd1 : 4'd0);
                    if (isec == nsec && hout == 4'd0 && !s_land && (!kv_v || kv_ready)) begin
                        // the row -> staging slot kl; a beat leaves with NL rows (or the job's last rows)
                        kv_w[kl * ROWW +: ROWW] <= kv_row;
                        if (kl == NL - 1 || row == blk0 + tb - 21'd1) begin
                            kv_v <= 1'b1; kv_m <= (({{(NL-1){1'b0}}, 1'b1} << (kl + 1)) - 1); st <= S_KVP;
                        end else begin kl <= kl + 4'd1; row <= row + 21'd1; st <= S_KVF; end
                    end
                end
                S_KVP: if (kv_v && kv_ready || !kv_v) begin
                    kl <= 4'd0;
                    if (row == blk0 + tb - 21'd1) st <= S_SCW;
                    else begin row <= row + 21'd1; st <= S_KVF; end
                end
                S_KVS: if (co_row == blk0 + tb && !pend_row && (!kv_v || kv_ready)) st <= S_SCW;   // every row pushed
                S_SCW: if (scb && qk && scn == tb && !sc_hold) begin so_h <= 5'd0; so_r <= 21'd0; st <= S_SCO; end
                else if (scn == tb && !sc_hold && vo_n == 3'd0) begin  // every score of the job written
                    hq <= 5'd0; pw_i <= 21'd0;
                    if (qk) st <= S_PW;
                    else begin
                        sec <= ({9'd0, abase} + {6'd0, blk0}) >> 3; rsec <= ({9'd0, abase} + {6'd0, blk0}) >> 3;
                        sec_end <= ({9'd0, abase} + {6'd0, blk0} + {6'd0, tb} - 27'd1) >> 3; st <= S_PRD;
                    end
                end
                S_SCO: begin                                        // PIPE = 2: the job's scores, sector writes
                    if (so_h != lanes && vo_n < 3'd4) begin : sco
                        reg [255:0] wd; reg [31:0] wm; integer w, ix;
                        wd = 256'd0; wm = 32'd0;
                        for (w = 0; w < 8; w = w + 1) begin
                            ix = w - so_wa[2:0];
                            if (ix >= 0 && ix < so_cnt) begin wd[32 * w +: 32] = sbuf[so_h * JB + so_r + ix]; wm[4 * w +: 4] = 4'hF; end
                        end
                        vmq <= {1'b1, 1'b1, so_wa[29:3], 5'd0, wd, wm, 16'h4157};
                        if (so_r + so_cnt >= tb) begin so_r <= 21'd0; so_h <= so_h + 5'd1; end else so_r <= so_r + so_cnt;
                    end
                    vo_n <= vo_n + ((so_h != lanes && vo_n < 3'd4) ? 3'd1 : 3'd0) - (vr[273] ? 3'd1 : 3'd0);
                    if (so_h == lanes && vo_n == 3'd0) begin hq <= 5'd0; pw_i <= 21'd0; st <= S_PW; end
                end
                S_PRD: begin                                        // p[hq][job rows] -> pb (PV)
                    if (vo_n < 3'd4 && sec <= sec_end) begin
                        vmq <= {1'b1, 1'b0, sec, 5'd0, 256'd0, 32'd0, 16'h4150}; sec <= sec + 27'd1;
                    end
                    if (vr[273] && !vr[256]) begin
                        for (q = 0; q < 8; q = q + 1) begin
                            e2 = {rsec, q[2:0]} - ({9'd0, abase} + hq * {9'd0, astr} + {6'd0, blk0});
                            if (e2 >= 0 && e2 < tb && vr[32*q +: 16] != 16'd0) flt <= 1'b1;   // p is BF16
                        end
                        rsec <= rsec + 27'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                    if (rsec > sec_end && vo_n == 3'd0) begin
                        if (hq == lanes - 1) st <= S_PW;
                        else begin
                            hq <= hq + 5'd1;
                            sec <= ({9'd0, abase} + (hq + 1) * {9'd0, astr} + {6'd0, blk0}) >> 3;
                            rsec <= ({9'd0, abase} + (hq + 1) * {9'd0, astr} + {6'd0, blk0}) >> 3;
                            sec_end <= ({9'd0, abase} + (hq + 1) * {9'd0, astr} + {6'd0, blk0} + {6'd0, tb} - 27'd1) >> 3;
                        end
                    end
                end
                S_PW: begin                                         // probability words: R rows x H heads
                    if ((!p_v || p_ready) && pw_i * R < tb) begin
                        begin : pwd
                            reg [TD*16-1:0] w; integer jj, hh;
                            w = {(TD*16){1'b0}};
                            for (jj = 0; jj < R; jj = jj + 1) for (hh = 0; hh < H; hh = hh + 1)
                                if (!qk && hh < lanes && pw_i * R + jj < tb) w[(jj * H + hh) * 16 +: 16] = p_word[(jj * H + hh) * 16 +: 16];
                            p_w <= w;
                        end
                        p_v <= 1'b1; pw_i <= pw_i + 21'd1;
                    end
                    if (pw_i * R >= tb && (!p_v || p_ready)) st <= S_PVW;
                end
                S_PVW: if (pvn == DPT) begin                        // the job's pv is in cur
                    if (qk) st <= S_NEXT;
                    else begin ml <= 3'd0; st <= S_MRG; end
                end
                S_MRG: begin                                        // binary-counter merge over jobs, level ml
                    if (ml == 3'd4) st <= S_NEXT;
                    else if (jb[ml]) begin mh <= 5'd0; md <= 10'd0; mout <= 12'd0; miss <= 1'b0; st <= S_MADD; end
                    else if (blk0 + tb >= tt) ml <= ml + 3'd1;      // last job: the padding sibling, cur + +0 = cur
                    else begin mh <= 5'd0; md <= 10'd0; st <= S_MST; end
                end
                S_MADD: begin                                       // cur = add(lvl[ml], cur), one value an edge
                    if (!miss) begin
                        ad_v <= 1'b1; ad_a <= lvl[ml * H * D + mh * D + md]; ad_b <= ck_q;
                        aq[aw] <= {7'((md / DPT) * H + mh), 6'(md % DPT)}; aw <= aw + 6'd1; mout <= mout + 12'd1;
                        if (md == hd - 1) begin
                            md <= 10'd0;
                            if (mh == lanes - 1) miss <= 1'b1; else mh <= mh + 5'd1;
                        end else md <= md + 10'd1;
                    end else if (ar == aw && !ad_o) begin ml <= ml + 3'd1; st <= S_MRG; end
                end
                S_MST: begin                                        // lvl[ml] = cur; this job stops here
                    lvl[ml * H * D + mh * D + md] <= ck_q;
                    if (md == hd - 1) begin
                        md <= 10'd0;
                        if (mh == lanes - 1) st <= S_NEXT; else mh <= mh + 5'd1;
                    end else md <= md + 10'd1;
                end
                S_NEXT: if (PIPE == 3) begin                        // multi-job PV after its merge
                    if (blk0 + tb >= tt) begin
                        o3_on <= 1'b1; o3_h <= 5'd0; o3_s <= {9'd0, pvx_obu} >> 3; pvx_og <= 1'b1;
                        busy <= 1'b0; st <= S_IDLE;
                    end else begin pv_busy <= 1'b0; blk0 <= blk0 + tb; jb <= jb + 4'd1; j3_go <= 1'b1; st <= S_JOB; end
                end else begin
                    if (blk0 + tb >= tt) begin
                        if (qk) st <= S_DONE;
                        else begin
                            hq <= 5'd0; dq <= 10'd0; vo_n <= 3'd0; st <= S_OUT;
                            if (PIPE == 3) begin o3_on <= 1'b1; o3_h <= 5'd0; o3_s <= {9'd0, obase} >> 3; end
                        end
                    end else begin blk0 <= blk0 + tb; jb <= jb + 4'd1; st <= S_JOB; end
                end
                S_OUT: if (PIPE == 3) begin                         // the O burst runs above; retire when written
                    if (!o3_on && wf_n == 7'd0 && xw_out == 13'd0) st <= S_DONE;
                end else begin                                      // O[h][d] = the merged root, one word a write
                    if (vo_n < 3'd4 && hq < lanes) begin : ow
                        reg [31:0] wa;
                        wa = {14'd0, obase} + hq * {14'd0, ostr} + dq;
                        vmq <= {1'b1, 1'b1, wa[29:3], 5'd0, {8{ck_q}}, 32'hF << (4 * wa[2:0]),
                                16'h414F};
                        if (dq == hd - 1) begin dq <= 10'd0; hq <= hq + 5'd1; end else dq <= dq + 10'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && hq < lanes) ? 3'd1 : 3'd0) - (vr[273] ? 3'd1 : 3'd0);
                    if (hq >= lanes && vo_n == 3'd0) st <= S_DONE;
                end
                S_DONE: if (PIPE != 3 || (wf_n == 7'd0 && xw_out == 13'd0 && !b3_v)) begin rec_done <= 1'b1; busy <= 1'b0; st <= S_IDLE; end
                S_FAULT: begin rec_fault <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; st <= S_IDLE; end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
