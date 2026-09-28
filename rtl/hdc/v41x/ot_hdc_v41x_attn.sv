`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION ENGINE of the re-specified DeepSeek-V4.1-Flash decode die
// (docs/ARCH_SPEC_V41.md section 6 item 4, gap-table rows "attention engine
// (q.k, p.v)" and "KV row staging buffer"): per die H heads of head_dim D over
// one shared MQA KV row per position (the row is key and value for every head).
//
// Function (tools/hdc_golden_v41.py Model.attend, R-ARITH chunk8):
//   s[h, t]  = dots(q, kvm)[h, t]              q BF16, csum over the D dims
//   pv[h, d] = dots(to_bf16(e), kvm.T)[h, d]    csum over the T rows, golden row order
// kvm rows: T = min(128, pos+1) window rows then up to 512 selected compressed
// rows, taken in their STORED format (FP8 E4M3 + UE8M0 per 32, or FP4 E2M1 +
// E4M3 per 16) and dequantised exactly in the tiles.  The softmax (max, exp,
// sum, sink, divide) and the attention scale stay on the stream unit; the two
// streams chain at vector granularity: a row's score vector leaves as soon as
// it is done, and p.v starts on each TD-row block of probabilities as soon as
// its last row arrives.
//
// Structure (NT = NL x S tiles of H x TD products, S = D/TD slices):
//   * staging buffer: NL sub-banks (row mod NL), TROWS/NL rows each, a row is
//     G = D/32 group words of 265 bits {fmt, payload}: FP8 {scale, 32 codes},
//     FP4 {2 E4M3 scales, 32 nibbles} (528 B of payload per row at D = 512);
//     each sub-bank reads one row per cycle -> NL rows/cycle.
//   * q.k: tile (l, s) holds q[:, s*TD +: TD] (stationary) and takes row
//     4c + l's slice s each cycle; the S slice partials of a row combine by the
//     golden's pairwise tree (lane tree) -> one H-head score vector per lane per
//     cycle, NL rows per cycle.
//   * p.v: every tile holds the same TD-row probability block (stationary,
//     loaded R = TD/H rows x H heads per word as the probabilities stream in)
//     and takes, per beat, one dim of the block's TD rows from its transposer
//     (tile k owns dims k*DPT +: DPT, DPT = D/NT); DPT beats per block.  A tile's
//     output is the block's TD-row partial of pv[h, d]; blocks combine by a
//     streaming binary-counter merge (MLEV levels, one ring of DPT entries per
//     level), which reproduces the golden's padded pairwise tree over the
//     ceil(T/8) chunk sums exactly: level l adds its stored 2^l-block sum when
//     bit l of the block index is set, the last block flushes from the
//     smallest level upward (x + +0 = x), and IEEE add commutes.
//
// Interfaces (all valid/ready or credit, every boundary registered):
//   job     job_v/job_ready, job_t (T rows).  One job = one layer's attention.
//           job_ready rises when the previous job's p.v has issued.
//   q       q_v/q_ready, q_w = one head's D BF16 (heads 0 .. H-1 in order).
//   kv      kv_v/kv_ready, kv_m (row mask, a prefix), kv_w = NL rows from row 0
//           in order (rows 4c .. 4c+NL-1).  A row may enter while q.k runs.
//   scores  sc_v, sc_row (row of lane 0), sc_m (lane mask), sc_y (NL x H FP32),
//           sc_f (fault per value).  Credit: the engine issues a q.k beat only
//           with a credit (SC_CRED initial); the consumer returns one per sc_cr.
//   probs   p_v/p_ready, p_w = R rows x H heads BF16 (word j*H + h), rows in
//           order from 0; the last word of a job may be partial.
//   pv      pv_v, pv_c (dim offset: tile k's value is dim k*DPT + pv_c), pv_y
//           (NT x H FP32), pv_f.  Credit per final-block beat (PV_CRED).
//
// Stationary banks: NBANK = 3, allocated round robin to the q set and every
// p block.  A bank is reloaded only when the last read of its previous set has
// passed (GUARD_P after a p.v issue: exact for the skewed chunk positions, so
// the p.v stream runs at one block per DPT cycles with 3 banks).
//
// Faults fail closed (see the tile): sc_f / pv_f mark every value whose golden
// value is not finite.
// ---------------------------------------------------------------------------

// Streaming binary-counter merge of one tile's p.v block partials.
module ot_hdc_v41x_attn_merge #(
    parameter integer H = 16,
    parameter integer DPT = 16,
    parameter integer MLEV = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,          // a p.v beat's block partial
    input  wire              ifin,        // of the job's last block
    input  wire [MLEV-1:0]   iblk,        // block index
    input  wire [H*32-1:0]   iy,
    input  wire [H-1:0]      if_,
    output wire              ov,          // a finished pv value (final blocks only)
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      of_
);
    wire [MLEV:0]          lv, lfin, llive;
    wire [(MLEV+1)*MLEV-1:0] lblk;
    wire [(MLEV+1)*H*32-1:0] lx;
    wire [(MLEV+1)*H-1:0]  lf;
    assign lv[0] = iv;
    assign lfin[0] = ifin;
    assign llive[0] = 1'b1;
    assign lblk[0 +: MLEV] = iblk;
    assign lx[0 +: H*32] = iy;
    assign lf[0 +: H] = if_;
    genvar gl, gh;
    generate
        for (gl = 0; gl < MLEV; gl = gl + 1) begin : g_l
            wire v = lv[gl];
            wire fin = lfin[gl];
            wire live = llive[gl];
            wire [MLEV-1:0] blk = lblk[gl*MLEV +: MLEV];
            wire use_ = blk[gl];
            wire store = v && live && !fin && !use_;
            // ring of DPT entries: head = entry of the beat's dim
            reg [H*33-1:0] ring [0:DPT-1];
            wire [H*33-1:0] head = ring[0];
            integer i;
            always @(posedge clk)
                if (v) begin
                    for (i = 0; i < DPT - 1; i = i + 1) ring[i] <= ring[i+1];
                    ring[DPT-1] <= store ? {lf[gl*H +: H], lx[gl*H*32 +: H*32]} : head;
                end
            for (gh = 0; gh < H; gh = gh + 1) begin : g_h
                wire [31:0] a = use_ ? head[gh*32 +: 32] : 32'd0;
                wire [31:0] y;
                wire af;
                ot_hdc_qadd u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(a), .b(lx[(gl*H+gh)*32 +: 32]),
                                 .y(y), .fault(af));
                reg [2:0] fd;
                always @(posedge clk) fd <= {fd[1:0], lf[gl*H+gh] | (use_ & head[H*32+gh])};
                assign lx[((gl+1)*H+gh)*32 +: 32] = y;
                assign lf[(gl+1)*H+gh] = fd[2] | af;
            end
            reg [2:0] dv, dfin, dlive;
            reg [MLEV-1:0] dblk [0:2];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) dv <= 3'd0;
                else dv <= {dv[1:0], v};
            end
            always @(posedge clk) begin
                dfin <= {dfin[1:0], fin};
                dlive <= {dlive[1:0], live && (use_ || fin)};
                dblk[0] <= blk; dblk[1] <= dblk[0]; dblk[2] <= dblk[1];
            end
            assign lv[gl+1] = dv[2];
            assign lfin[gl+1] = dfin[2];
            assign llive[gl+1] = dlive[2];
            assign lblk[(gl+1)*MLEV +: MLEV] = dblk[2];
        end
    endgenerate
    assign ov = lv[MLEV] && lfin[MLEV] && llive[MLEV];
    assign oy = lx[MLEV*H*32 +: H*32];
    assign of_ = lf[MLEV*H +: H];
endmodule

module ot_hdc_v41x_attn #(
    parameter integer H = 16,          // heads per die
    parameter integer D = 512,         // head_dim
    parameter integer TD = 64,         // tile width (dims per q.k beat / rows per p.v block)
    parameter integer NL = 4,          // row lanes (rows per cycle)
    parameter integer TROWS = 640,     // staging buffer rows
    parameter integer SC_CRED = 64,     // score-beat credits
    parameter integer PV_CRED = 64,    // pv-beat credits
    parameter bit SRAM_MACRO = 0       // ASAP7 packed-row staging macro boundary
) (
    input  wire                   clk,
    input  wire                   rst_n,
    // job
    input  wire                   job_v,
    input  wire [15:0]            job_t,
    output wire                   job_ready,
    // q
    input  wire                   q_v,
    input  wire [D*16-1:0]        q_w,
    output wire                   q_ready,
    // kv rows
    input  wire                   kv_v,
    input  wire [NL-1:0]          kv_m,
    input  wire [NL*(D/32)*265-1:0] kv_w,
    output wire                   kv_ready,
    // scores
    output reg                    sc_v,
    output reg  [15:0]            sc_row,
    output reg  [NL-1:0]          sc_m,
    output reg  [NL*H*32-1:0]     sc_y,
    output reg  [NL*H-1:0]        sc_f,
    input  wire                   sc_cr,
    // probabilities
    input  wire                   p_v,
    input  wire [TD*16-1:0]       p_w,
    output wire                   p_ready,
    // pv
    output reg                    pv_v,
    output reg  [7:0]             pv_c,
    output reg  [NL*(D/TD)*H*32-1:0] pv_y,
    output reg  [NL*(D/TD)*H-1:0] pv_f,
    input  wire                   pv_cr,
    // bench visibility
    output wire                   qk_iss,
    output wire                   pv_iss
);
    localparam integer S = D / TD;
    localparam integer NT = NL * S;
    localparam integer G = D / 32;
    localparam integer GW = 265;
    localparam integer ROWW = G * GW;
    localparam integer R = TD / H;
    localparam integer PB = H;                         // p words per full block
    localparam integer DPT = D / NT;
    localparam integer FILLC = TD / NL;                // fill beats per block
    localparam integer DEPTH = (TROWS + NL - 1) / NL;
    localparam integer AW = $clog2(DEPTH);
    localparam integer NBLKMAX = (TROWS + TD - 1) / TD;
    localparam integer MLEV = (NBLKMAX <= 1) ? 1 : $clog2(NBLKMAX);
    localparam integer NBANK = 3;
    localparam integer BW = 2;
    localparam integer LVT = $clog2(TD / 8);
    localparam integer TLAT = 27 + 3 * LVT;            // tile: input -> ov
    localparam integer LS = (S <= 1) ? 0 : $clog2(S);  // lane-tree levels

    // write-after-read guards (cycles from an issue decision to a load of the same bank)
    function automatic integer skew(input integer i);
        skew = (i == 0) ? 0 : 3 * (i - 1);
    endfunction
    function automatic integer guard_p(input integer dummy);
        integer g, j, m, best;
        begin
            best = 0;
            for (g = 0; g < PB; g = g + 1) begin
                m = 0;
                for (j = 0; j < R; j = j + 1)
                    if (skew((R * g + j) % 8) > m) m = skew((R * g + j) % 8);
                if (m - g > best) best = m - g;
            end
            guard_p = best + 1;
        end
    endfunction
    localparam integer GUARD_P = guard_p(0);
    localparam integer GUARD_Q = 20;
    localparam integer CNTW = 5;

    // ================= controller =================
    reg  [15:0]   fill_blk_d;
    reg  [7:0]    fill_cnt_d;
    reg           rd_qk, rd_fill;
    wire          fill_wr = rd_fill;
    reg        act;
    reg [15:0] T;
    reg [15:0] nblk;
    reg        phase_pv;
    reg [15:0] wptr;                  // rows written
    reg [15:0] qk_row;                // next q.k row base
    reg [7:0]  q_cnt;                 // q words loaded
    reg [BW-1:0] q_bank;
    reg [BW-1:0] next_bank;
    reg [NBANK-1:0] held;
    reg [CNTW-1:0] bcnt [0:NBANK-1];
    reg [7:0]  sc_cred;
    reg [7:0]  pv_cred;
    // p loads
    reg [15:0] pl_blk;                // block being loaded
    reg [7:0]  pl_word;               // word within it
    reg [BW-1:0] pl_bank;
    reg [BW-1:0] blk_bank [0:3];      // bank of block (index mod 4)
    // fills
    reg [15:0] fl_blk;
    reg [7:0]  fl_cnt;
    reg [15:0] filled_upto;           // blocks whose transposer fill is complete
    // p.v issue
    reg [15:0] iss_blk;
    reg [7:0]  iss_c;

    wire [15:0] blk_rows0 = pl_blk * TD;                     // first row of the loading block
    wire [15:0] words_blk = ((T - blk_rows0) >= TD) ? PB : ((T - blk_rows0 + R - 1) / R);
    wire q_bank_ok = !held[next_bank] && (bcnt[next_bank] == 0);
    wire p_bank_ok = !held[next_bank] && (bcnt[next_bank] <= (GUARD_Q - GUARD_P + 1));

    assign job_ready = !act;
    wire job_go = job_v && job_ready;
    assign q_ready = act && (q_cnt < H) && ((q_cnt != 0) || q_bank_ok);
    wire q_go = q_v && q_ready;
    assign kv_ready = act && (wptr < T);
    wire kv_go = kv_v && kv_ready;
    // p words: a new block needs a free bank and at most 3 blocks between the issuing and the loading one
    assign p_ready = act && (q_cnt == H) && (pl_blk < nblk) && ((pl_word != 0) || (p_bank_ok && (pl_blk < iss_blk + 3)));
    wire p_go = p_v && p_ready;
    wire p_last_word = p_go && (pl_word + 1 == words_blk);

    // q.k issue
    wire qk_rows_ok = (wptr >= T) || (qk_row + NL <= wptr);
    wire qk_go = act && !phase_pv && (q_cnt == H) && (qk_row < T) && qk_rows_ok && (sc_cred != 0);
    // transposer fill (buffer ports are free once q.k has issued)
    // p.v issue
    wire iss_loaded = (pl_blk > iss_blk) || (p_last_word && (pl_blk == iss_blk));
    wire iss_final = (iss_blk + 1 == nblk);
    wire pv_go_raw = act && phase_pv && (iss_blk < nblk) && iss_loaded && (filled_upto > iss_blk) &&
                 (!iss_final || (pv_cred != 0));
    wire pv_go = pv_go_raw;
    wire fl_half_free = (fl_blk < iss_blk + 2) || ((fl_blk == iss_blk + 2) && pv_go_raw && (iss_c + 1 == DPT));
    wire fl_go = act && phase_pv && (fl_blk < nblk) && fl_half_free;
    wire [BW-1:0] iss_bank = (pl_blk == iss_blk) ? ((pl_word == 0) ? next_bank : pl_bank) : blk_bank[iss_blk[1:0]];
    assign qk_iss = qk_go;
    assign pv_iss = pv_go;

    integer b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            act <= 1'b0; T <= 16'd0; nblk <= 16'd0; phase_pv <= 1'b0; wptr <= 16'd0; qk_row <= 16'd0;
            q_cnt <= 8'd0; q_bank <= {BW{1'b0}}; next_bank <= {BW{1'b0}}; held <= {NBANK{1'b0}};
            for (b = 0; b < NBANK; b = b + 1) bcnt[b] <= {CNTW{1'b0}};
            sc_cred <= SC_CRED; pv_cred <= PV_CRED;
            pl_blk <= 16'd0; pl_word <= 8'd0; pl_bank <= {BW{1'b0}};
            fl_blk <= 16'd0; fl_cnt <= 8'd0; filled_upto <= 16'd0; iss_blk <= 16'd0; iss_c <= 8'd0;
        end else begin
            for (b = 0; b < NBANK; b = b + 1)
                if (bcnt[b] != 0) bcnt[b] <= bcnt[b] - 1'b1;
            if (job_go) begin
                act <= 1'b1; T <= job_t; nblk <= (job_t + TD - 1) / TD; phase_pv <= 1'b0;
                wptr <= 16'd0; qk_row <= 16'd0; q_cnt <= 8'd0;
                pl_blk <= 16'd0; pl_word <= 8'd0; fl_blk <= 16'd0; fl_cnt <= 8'd0; filled_upto <= 16'd0;
                iss_blk <= 16'd0; iss_c <= 8'd0;
            end
            // q set
            if (q_go) begin
                if (q_cnt == 0) begin
                    q_bank <= next_bank;
                    held[next_bank] <= 1'b1;
                    next_bank <= (next_bank == NBANK - 1) ? {BW{1'b0}} : next_bank + 1'b1;
                end
                q_cnt <= q_cnt + 1'b1;
            end
            if (kv_go) wptr <= wptr + ((kv_m == {NL{1'b1}}) ? NL : count_ones(kv_m));
            if (qk_go) begin
                qk_row <= qk_row + NL;
                bcnt[q_bank] <= GUARD_Q + 1;
                if (qk_row + NL >= T) begin
                    phase_pv <= 1'b1;
                    held[q_bank] <= 1'b0;
                end
            end
            if (sc_cr && !qk_go) sc_cred <= sc_cred + 1'b1;
            else if (!sc_cr && qk_go) sc_cred <= sc_cred - 1'b1;
            // p words
            if (p_go) begin
                if (pl_word == 0) begin
                    pl_bank <= next_bank;
                    blk_bank[pl_blk[1:0]] <= next_bank;
                    held[next_bank] <= 1'b1;
                    next_bank <= (next_bank == NBANK - 1) ? {BW{1'b0}} : next_bank + 1'b1;
                end
                if (p_last_word) begin
                    pl_blk <= pl_blk + 1'b1;
                    pl_word <= 8'd0;
                end else begin
                    pl_word <= pl_word + 1'b1;
                end
            end
            // fills
            if (fl_go) begin
                if (fl_cnt + 1 == FILLC) begin
                    fl_cnt <= 8'd0;
                    fl_blk <= fl_blk + 1'b1;
                end else begin
                    fl_cnt <= fl_cnt + 1'b1;
                end
            end
            if (fill_wr && (fill_cnt_d + 1 == FILLC)) filled_upto <= fill_blk_d + 1'b1;
            // p.v issue
            if (pv_go) begin
                bcnt[iss_bank] <= GUARD_Q;
                if (iss_c + 1 == DPT) begin
                    iss_c <= 8'd0;
                    iss_blk <= iss_blk + 1'b1;
                    held[iss_bank] <= 1'b0;
                    if (iss_final) act <= 1'b0;
                end else begin
                    iss_c <= iss_c + 1'b1;
                end
            end
            if (pv_cr && !(pv_go && iss_final)) pv_cred <= pv_cred + 1'b1;
            else if (!pv_cr && pv_go && iss_final) pv_cred <= pv_cred - 1'b1;
        end
    end

    function automatic [15:0] count_ones(input [NL-1:0] m);
        integer i;
        begin
            count_ones = 16'd0;
            for (i = 0; i < NL; i = i + 1) count_ones = count_ones + m[i];
        end
    endfunction

    // ================= staging buffer =================
    genvar gl, gs, gk, gh;
    // one read per sub-bank per cycle: q.k rows or a fill beat
    wire [AW-1:0] rd_addr = qk_go ? AW'(qk_row / NL) : AW'(fl_blk * FILLC + fl_cnt);
    wire [15:0]   rd_row0 = qk_go ? qk_row : (fl_blk * TD + fl_cnt * NL);
    wire [NL*ROWW-1:0] rd_q;
    reg  [15:0]   rd_r0;
    reg  [BW-1:0] rd_bank;
    ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(SRAM_MACRO)) u_stage (
        .clk(clk), .wr_en({NL{kv_go}} & kv_m), .wr_addr(AW'(wptr / NL)), .wr_data(kv_w),
        .rd_addr(rd_addr), .rd_data(rd_q));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rd_qk <= 1'b0; rd_fill <= 1'b0; end
        else begin rd_qk <= qk_go; rd_fill <= fl_go && !qk_go; end
    end
    always @(posedge clk) begin
        rd_r0 <= rd_row0; fill_blk_d <= fl_blk; fill_cnt_d <= fl_cnt; rd_bank <= q_bank;
    end

    // element of dim x (0..31) of a group word, {pad, fmt, code, scale}
    function automatic [17:0] elem(input [GW-1:0] gw, input integer x, input pad);
        begin
            if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};
            else         elem = {pad, 1'b0, gw[8*x +: 8], gw[263:256]};
        end
    endfunction

    // ================= tile inputs (E1 register) =================
    reg              e_ld_v, e_ld_mode;
    reg [BW-1:0]     e_ld_bank;
    reg [7:0]        e_ld_grp;
    reg [TD*16-1:0]  e_p_w;
    reg [D*16-1:0]   e_q_w;
    reg              e_iv, e_pv;
    reg [BW-1:0]     e_ibank;
    reg [NT*TD*18-1:0] e_ib;
    // tags carried to the outputs
    reg [15:0]       e_row0;
    reg [NL-1:0]     e_mask;
    reg              e_fin;
    reg [MLEV-1:0]   e_blk;
    reg [7:0]        e_c;

    // transposers: per tile 2 halves x TD rows x DPT dims of 18-bit elements
    wire [NT*TD*18-1:0] tr_col;
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_tr
            reg [17:0] tr [0:2*TD*DPT-1];
            integer r, x;
            always @(posedge clk)
                if (fill_wr)
                    for (r = 0; r < NL; r = r + 1)
                        for (x = 0; x < DPT; x = x + 1)
                            tr[((fill_blk_d % 2) * TD + fill_cnt_d * NL + r) * DPT + x] <=
                                elem(rd_q[r*ROWW + ((gk*DPT + x) / 32) * GW +: GW], (gk*DPT + x) % 32,
                                     (rd_r0 + r) >= T);
            for (gs = 0; gs < TD; gs = gs + 1) begin : g_c
                assign tr_col[(gk*TD + gs)*18 +: 18] = tr[((iss_blk % 2) * TD + gs) * DPT + iss_c];
            end
        end
    endgenerate

    // q.k beat elements from the buffer read
    wire [NT*TD*18-1:0] qk_ib;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_qkl
            for (gs = 0; gs < S; gs = gs + 1) begin : g_qks
                for (gk = 0; gk < TD; gk = gk + 1) begin : g_qke
                    assign qk_ib[((gl*S + gs)*TD + gk)*18 +: 18] =
                        elem(rd_q[gl*ROWW + ((gs*TD + gk) / 32) * GW +: GW], (gs*TD + gk) % 32, (rd_r0 + gl) >= T);
                end
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin e_ld_v <= 1'b0; e_iv <= 1'b0; e_pv <= 1'b0; end
        else begin
            e_ld_v <= q_go || p_go;
            e_iv <= rd_qk || pv_go;
            e_pv <= pv_go;
        end
    end
    integer li;
    always @(posedge clk) begin
        e_ld_mode <= p_go;
        e_ld_bank <= p_go ? ((pl_word == 0) ? next_bank : pl_bank) : ((q_cnt == 0) ? next_bank : q_bank);
        e_ld_grp <= p_go ? pl_word : q_cnt;
        e_p_w <= p_w;
        e_q_w <= q_w;
        e_ibank <= pv_go ? iss_bank : rd_bank;
        e_ib <= pv_go ? tr_col : qk_ib;
        e_row0 <= rd_r0;
        for (li = 0; li < NL; li = li + 1) e_mask[li] <= (rd_r0 + li) < T;
        e_fin <= iss_final;
        e_blk <= iss_blk[MLEV-1:0];
        e_c <= iss_c;
    end

    // ================= tiles =================
    wire [NT-1:0]      t_ov;
    wire [NT*H*32-1:0] t_y;
    wire [NT*H-1:0]    t_f;
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_t
            localparam integer SL = gk % S;
            wire [TD*16-1:0] ldw = e_ld_mode ? e_p_w : e_q_w[SL*TD*16 +: TD*16];
            ot_hdc_v41x_attn_tile #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW)) u_t (
                .clk(clk), .rst_n(rst_n), .ld_v(e_ld_v), .ld_mode(e_ld_mode), .ld_bank(e_ld_bank),
                .ld_grp(e_ld_grp), .ld_w(ldw), .iv(e_iv), .ibank(e_ibank), .ib(e_ib[gk*TD*18 +: TD*18]),
                .ov(t_ov[gk]), .oy(t_y[gk*H*32 +: H*32]), .oflt(t_f[gk*H +: H]));
        end
    endgenerate

    // tags to the tile outputs
    wire [15:0] t_row0;
    wire [NL-1:0] t_mask;
    wire t_pv, t_fin;
    wire [MLEV-1:0] t_blk;
    wire [7:0] t_c;
    ot_hdc_v41x_dly #(.W(16 + NL + 2 + MLEV + 8), .D(TLAT)) u_tag (.clk(clk),
        .d({e_row0, e_mask, e_pv, e_fin, e_blk, e_c}), .q({t_row0, t_mask, t_pv, t_fin, t_blk, t_c}));

    // ================= q.k lane trees =================
    wire [NL*H*32-1:0] ln_y;
    wire [NL*H-1:0]    ln_f;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_ln
            for (gh = 0; gh < H; gh = gh + 1) begin : g_lh
                wire [(2*S-1)*32-1:0] tn;
                wire [2*S-2:0] tf;
                for (gs = 0; gs < S; gs = gs + 1) begin : g_leaf
                    assign tn[(S-1+gs)*32 +: 32] = t_y[((gl*S + gs)*H + gh)*32 +: 32];
                    assign tf[S-1+gs] = t_f[(gl*S + gs)*H + gh];
                end
                for (gs = 0; gs < S - 1; gs = gs + 1) begin : g_node
                    wire [31:0] y;
                    wire f;
                    ot_hdc_qadd u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(tn[(2*gs+1)*32 +: 32]),
                                     .b(tn[(2*gs+2)*32 +: 32]), .y(y), .fault(f));
                    reg [2:0] fd;
                    always @(posedge clk) fd <= {fd[1:0], tf[2*gs+1] | tf[2*gs+2]};
                    assign tn[gs*32 +: 32] = y;
                    assign tf[gs] = fd[2] | f;
                end
                assign ln_y[(gl*H + gh)*32 +: 32] = tn[31:0];
                assign ln_f[gl*H + gh] = tf[0];
            end
        end
    endgenerate
    wire ln_v, ln_pv;
    wire [15:0] ln_row0;
    wire [NL-1:0] ln_mask;
    ot_hdc_v41x_vdly #(.D(3 * LS + 1)) u_lnv (.clk(clk), .rst_n(rst_n), .d(t_ov[0] && !t_pv), .q(ln_v));
    ot_hdc_v41x_dly #(.W(16 + NL), .D(3 * LS + 1)) u_lnt (.clk(clk), .d({t_row0, t_mask}), .q({ln_row0, ln_mask}));
    // (the +1 above aligns with the register below; ln_y is 3*LS after t_y)
    reg [NL*H*32-1:0] ln_yr;
    reg [NL*H-1:0]    ln_fr;
    always @(posedge clk) begin ln_yr <= ln_y; ln_fr <= ln_f; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sc_v <= 1'b0;
        else sc_v <= ln_v;
    end
    always @(posedge clk) begin
        sc_row <= ln_row0; sc_m <= ln_mask; sc_y <= ln_yr; sc_f <= ln_fr;
    end

    // ================= p.v merges =================
    wire [NT-1:0]      m_ov;
    wire [NT*H*32-1:0] m_y;
    wire [NT*H-1:0]    m_f;
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_m
            ot_hdc_v41x_attn_merge #(.H(H), .DPT(DPT), .MLEV(MLEV)) u_m (
                .clk(clk), .rst_n(rst_n), .iv(t_ov[gk] && t_pv), .ifin(t_fin), .iblk(t_blk),
                .iy(t_y[gk*H*32 +: H*32]), .if_(t_f[gk*H +: H]), .ov(m_ov[gk]), .oy(m_y[gk*H*32 +: H*32]),
                .of_(m_f[gk*H +: H]));
        end
    endgenerate
    wire [7:0] m_c;
    ot_hdc_v41x_dly #(.W(8), .D(3 * MLEV)) u_mc (.clk(clk), .d(t_c), .q(m_c));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv_v <= 1'b0;
        else pv_v <= m_ov[0];
    end
    always @(posedge clk) begin
        pv_c <= m_c; pv_y <= m_y; pv_f <= m_f;
    end
endmodule
