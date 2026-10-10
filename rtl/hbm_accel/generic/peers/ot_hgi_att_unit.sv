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
    parameter integer MUT_RING = 0          // mutant: ring rows from slot 0
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
    input  wire [255:0]  hr_data
);
    localparam integer S = D / TD, NT = NL * S, DPT = D / NT, G = D / 32, R = TD / H, ROWW = G * 265;
    localparam integer SPR = D * 4 / 32;              // max sectors a row (FP32)
    // ---- record pin flops
    reg [127:0] hdr; reg [255:0] da, db, dc, dout; reg [20:0] nb, nc, pos1; reg raw_v, busy, halt_q;
    always @(posedge clk) begin hdr <= rec_hdr; da <= rec_a; db <= rec_b; dc <= rec_c; dout <= rec_o; nb <= rec_n_b;
                                nc <= rec_n_c; pos1 <= rec_pos1; end
    assign rec_rdy = !raw_v && !busy && !halt_q;
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
    reg qk; reg [4:0] lanes; reg [9:0] hd; reg ring; reg [20:0] tt; reg [1:0] bfmt, cfmt;
    reg [17:0] abase, astr, obase, ostr, oist; reg [39:0] bbase, cbase; reg [31:0] bstr, cstr; reg [19:0] bm;
    // ---- the engine
    reg job_v; reg [15:0] job_t; wire job_ready;
    reg q_v; reg [D*16-1:0] q_w; wire q_ready; reg qload;
    reg kv_v; reg [NL*ROWW-1:0] kv_w; reg [NL-1:0] kv_m; reg [3:0] kl; wire kv_ready;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f; reg sc_cr;
    reg p_v; reg [TD*16-1:0] p_w; wire p_ready;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f; reg pv_cr;
    localparam integer SQ = 16;              // score beats in flight (the engine's credit count)
    ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(BLK), .SC_CRED(SQ)) u_eng (.clk(clk), .rst_n(rst_n),
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
    integer gx, xx;
    always @* begin
        kv_row = {ROWW{1'b0}};
        for (gx = 0; gx < G; gx = gx + 1) begin
            kv_row[gx * 265 + 256 +: 8] = 8'd127;
            for (xx = 0; xx < 32; xx = xx + 1) kv_row[gx * 265 + 8 * xx +: 8] = (gx * 32 + xx < hd) ? c_flat[8 * (gx * 32 + xx) +: 8] : 8'd0;
        end
    end
    // ---- banked writes (each bank: one write an edge)
    wire land_q = (st == S_QRD) && qk && hq < lanes && vr[273] && !vr[256];
    wire land_p = (st == S_PRD) && vr[273] && !vr[256];
    wire land_c = (st == S_KVC) && hr_vq;
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
    generate for (gb = 0; gb < 32; gb = gb + 1) begin : g_cb
        wire [8:0] c16 = e4m3({hr_dq[16 * (gb % 16) +: 16], 16'd0});
        wire [8:0] c32 = e4m3(hr_dq[32 * (gb % 8) +: 32]);
        reg [7:0] m [0:D/32-1];
        always @(posedge clk) begin
            cflt[gb] <= 1'b0;
            if (land_c) begin
                if (es_b == 2'd0) m[hr_tq] <= hr_dq[8*gb +: 8];
                else if (es_b == 2'd1 && hr_tq[0] == gb / 16) begin m[hr_tq >> 1] <= c16[7:0]; cflt[gb] <= c16[8]; end
                else if (es_b == 2'd2 && hr_tq[1:0] == gb / 8) begin m[hr_tq >> 2] <= c32[7:0]; cflt[gb] <= c32[8]; end
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
    always @* for (qe = 0; qe < D; qe = qe + 1) q_w[16 * qe +: 16] = (qload && qe < hd) ? q_flat[16 * qe +: 16] : 16'd0;
    // the ck read: S_OUT walks (hq, dq), the merge (mh, md)
    wire [9:0] ck_d = (st == S_OUT) ? dq : md; wire [4:0] ck_h = (st == S_OUT) ? hq : mh;
    always @* ck_a = ck_d % DPT;
    wire [31:0] ck_q = ck_rd[((ck_d / DPT) * H + ck_h) * 32 +: 32];
    // ---- control
    localparam [4:0] S_IDLE = 0, S_DEC = 1, S_CHK = 2, S_JOB = 3, S_QRD = 4, S_QW = 5, S_KVF = 6, S_KVC = 7,
                     S_KVP = 8, S_SCW = 9, S_PRD = 10, S_PW = 11, S_PVW = 12, S_MRG = 13, S_OUT = 14, S_DONE = 15,
                     S_FAULT = 16, S_NEXT = 17, S_MADD = 18, S_MST = 19;
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
    reg [20:0] blk0, tb; reg [3:0] jb;               // job's first row, rows, job index
    reg [4:0] hq; reg [26:0] sec, sec_end, rsec; reg [2:0] vo_n;   // VM walk
    reg [20:0] row; reg [7:0] nsec, isec; reg [3:0] hout; reg [39:0] rbyte;
    // score beats: NL rows (lane l = row sc_row + l, sc_m mask) x H heads
    reg [20:0] scn; reg [4:0] sch; reg [3:0] scl; reg sc_hold; reg [NL*H*32-1:0] scy; reg [20:0] scrow; reg [NL-1:0] scm;
    reg [NL*H*32-1:0] sfy [0:31]; reg [15:0] sfr_row [0:31]; reg [NL-1:0] sfm [0:31]; reg [4:0] sfw, sfr;
    wire hd_pop = 1'b0;
    function automatic [20:0] pc(input [NL-1:0] m); integer x; pc = 0; for (x = 0; x < NL; x = x + 1) pc = pc + m[x]; endfunction
    reg [20:0] pw_i; reg [9:0] pvn; reg [2:0] ml; reg flt;
    reg [9:0] dq; reg [4:0] hd_o;
    integer k, j, q, e2;
    wire [1:0] es_b = (bfmt == 2'd2) ? 2'd0 : (bfmt == 2'd1) ? 2'd1 : 2'd2;    // log2 bytes an element
    wire [3:0] njobs = (tt + BLK - 1) / BLK;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; raw_v <= 1'b0; busy <= 1'b0; halt_q <= 1'b0; rec_done <= 1'b0; rec_fault <= 1'b0;
            vmq <= 338'd0; hq_v <= 1'b0; job_v <= 1'b0; q_v <= 1'b0; kv_v <= 1'b0; sc_cr <= 1'b0; p_v <= 1'b0;
            pv_cr <= 1'b0; flt <= 1'b0; vo_n <= 3'd0; sc_hold <= 1'b0; scn <= 21'd0; pvn <= 10'd0; ad_v <= 1'b0;
            sfw <= 5'd0; sfr <= 5'd0;
            aw <= 6'd0; ar <= 6'd0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0; vmq[337] <= 1'b0; job_v <= 1'b0; sc_cr <= 1'b0; pv_cr <= 1'b0;
            ad_v <= 1'b0;
            if (|cflt) flt <= 1'b1;
            if (ad_o) begin ar <= ar + 6'd1; if (ad_e != 2'd0) flt <= 1'b1; end
            if (rec_v && rec_rdy) raw_v <= 1'b1;
            if (hq_v && hq_rdy) hq_v <= 1'b0;
            if (q_v && q_ready) q_v <= 1'b0;
            if (kv_v && kv_ready) kv_v <= 1'b0;
            if (p_v && p_ready) p_v <= 1'b0;
            // pv beats: capture (PV) and return the credit
            if (pv_v) begin
                for (k = 0; k < NT; k = k + 1) for (j = 0; j < H; j = j + 1)
                    if (!qk && j < lanes && k * DPT + pv_c < hd && pv_f[k * H + j]) flt <= 1'b1;
                pv_cr <= 1'b1; pvn <= pvn + 10'd1;
            end
            // score beats: QK writes heads < lanes to O (one masked word a VM write), PV discards
            // score FIFO (SQ = the engine's credits): push every beat; the head is written, then its credit returns
            if (sc_v) begin sfy[sfw] <= sc_y; sfr_row[sfw] <= sc_row; sfm[sfw] <= sc_m; sfw <= sfw + 5'd1;
                for (k = 0; k < NL; k = k + 1) for (j = 0; j < H; j = j + 1)
                    if (qk && sc_m[k] && j < lanes && sc_f[k * H + j]) flt <= 1'b1; end
            if (!sc_hold && sfr != sfw && !hd_pop) begin
                sc_hold <= 1'b1; scy <= sfy[sfr]; scrow <= {5'd0, sfr_row[sfr]}; scm <= sfm[sfr]; sch <= 5'd0;
                scl <= 4'd0; sfr <= sfr + 5'd1;
            end
            if (sc_hold) begin
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
            if (st == S_KVF || st == S_KVC || st == S_KVP || st == S_SCW)
                vo_n <= vo_n + ((qk && sc_hold && scl != NL && scm[scl] && vo_n < 3'd4) ? 3'd1 : 3'd0) -
                        (vr[273] ? 3'd1 : 3'd0);
            if (flt && st != S_FAULT && st != S_IDLE) st <= S_FAULT;
            else case (st)
                S_IDLE: if (raw_v) begin raw_v <= 1'b0; busy <= 1'b1; st <= S_DEC; end
                S_DEC: begin
                    qk <= (op == 6'd0); lanes <= (prm[3:0] == 4'd0) ? 5'd16 : {1'b0, prm[3:0]}; ring <= prm[8];
                    hd <= (op == 6'd0) ? mn(da)[9:0] : mn(dout)[9:0];
                    tt <= nb + (hasc ? nc : 21'd0);
                    bfmt <= !db[4] ? db[3:2] : 2'd3; cfmt <= !dc[4] ? dc[3:2] : 2'd3;
                    abase <= mbase(da)[17:0]; astr <= mst(da)[17:0]; obase <= mbase(dout)[17:0]; ostr <= mst(dout)[17:0];
                    oist <= {2'b00, mist(dout)}; bbase <= mbase(db); cbase <= mbase(dc); bstr <= mst(db); cstr <= mst(dc);
                    bm <= mm(db);
                    st <= S_CHK;
                end
                S_CHK: begin
                    if (hdr[127:124] != 4'd5 || op > 6'd1 || !opnd[0] || !opnd[1] || !opnd[4] || da[1:0] != 2'd1 ||
                        dout[1:0] != 2'd1 || db[1:0] != 2'd0 || (hasc && dc[1:0] != 2'd0) || bfmt == 2'd3 ||
                        (hasc && cfmt != bfmt) || hd == 0 || hd > D || hd[4:0] != 0 || tt == 0 ||
                        lanes > H || (ring && (bm == 0 || (bm & (bm - 1)) != 0 || {1'b0, bm} < nb)) ||
                        (!qk && mn(da) != tt[19:0]) || (qk && mn(dout) != tt[19:0]) || bbase[4:0] != 0 ||
                        bstr[4:0] != 0 || (hasc && (cbase[4:0] != 0 || cstr[4:0] != 0)))
                        st <= S_FAULT;
                    else begin blk0 <= 21'd0; jb <= 4'd0; st <= S_JOB; end
                end
                // ---- one engine job: rows blk0 .. blk0 + tb - 1
                S_JOB: begin
                    tb <= (tt - blk0 > BLK) ? BLK : tt - blk0;
                    if (job_ready && !job_v) begin
                        job_v <= 1'b1; job_t <= ((tt - blk0 > BLK) ? BLK : tt - blk0); hq <= 5'd0; scn <= 21'd0; pvn <= 10'd0;
                        st <= S_QRD; 
                        sec <= abase >> 3; sec_end <= ({9'd0, abase} + {17'd0, hd} - 27'd1) >> 3;
                        rsec <= abase >> 3; vo_n <= 3'd0;
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
                        if (hq == H - 1) begin row <= blk0; kl <= 4'd0; st <= S_KVF; vo_n <= 3'd0; end
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
                            b = bbase + slot * bstr;
                        end else b = cbase + (t - nb) * cstr;
                        rbyte <= b;
                    end
                    nsec <= ({8'd0, hd} << es_b) >> 5; isec <= 8'd0; hout <= 4'd0;
                    st <= S_KVC;
                end
                S_KVC: begin
                    if ((!hq_v || hq_rdy) && isec < nsec && hout < NOUT) begin
                        hq_v <= 1'b1; hq_addr <= (rbyte >> 5) + isec; hq_tag <= isec; isec <= isec + 8'd1;
                    end
                    hout <= hout + (((!hq_v || hq_rdy) && isec < nsec && hout < NOUT) ? 4'd1 : 4'd0) - (hr_vq ? 4'd1 : 4'd0);
                    if (isec == nsec && hout == 4'd0 && !hr_vq && (!kv_v || kv_ready)) begin
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
                S_SCW: if (scn == tb && !sc_hold && vo_n == 3'd0) begin  // every score of the job written
                    hq <= 5'd0; pw_i <= 21'd0;
                    if (qk) st <= S_PW;
                    else begin
                        sec <= ({9'd0, abase} + {6'd0, blk0}) >> 3; rsec <= ({9'd0, abase} + {6'd0, blk0}) >> 3;
                        sec_end <= ({9'd0, abase} + {6'd0, blk0} + {6'd0, tb} - 27'd1) >> 3; st <= S_PRD;
                    end
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
                S_NEXT: begin
                    if (blk0 + tb >= tt) begin
                        if (qk) st <= S_DONE;
                        else begin hq <= 5'd0; dq <= 10'd0; vo_n <= 3'd0; st <= S_OUT; end
                    end else begin blk0 <= blk0 + tb; jb <= jb + 4'd1; st <= S_JOB; end
                end
                S_OUT: begin                                        // O[h][d] = the merged root, one word a write
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
                S_DONE: begin rec_done <= 1'b1; busy <= 1'b0; st <= S_IDLE; end
                S_FAULT: begin rec_fault <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; st <= S_IDLE; end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
