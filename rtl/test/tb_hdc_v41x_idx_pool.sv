`timescale 1ns/1ps
// Pooled lightning indexer (spec R-U2), end to end against the golden:
//   the pooled block-dot tile (ot_hdc_v41x_wgt_tile, KIND 0, POOL 1) runs each
//   token's index op in split mode with the keys on the stream port rd_k
//   (dots_q4 per (key, head)), ot_hdc_v41x_idx_pcol gathers each key's IH
//   head scores, ot_hdc_v41x_idx_hsum does to_bf16 / ReLU x weight / the head
//   sum / mask / the UE8M0 >= 253 refusal; every key's BF16 score is checked.
// The read network (rd_k key words, rd_x q blocks) is the behavioural model of
// tb_hdc_v41x_wgt.sv: lane j answers its chain position's request RL cycles
// later; split lane j carries block j mod 4 of row rg * 2G + 2 (j / 8) +
// (j mod 8 >= 4); row r = (key r / (IH/M), head group r mod (IH/M)).
// Files: pt.mem per token {xbase, wbase, nkeys} (3 words); pw.mem per token IH
// lines {q scales[31:0], w[15:0]}; pk.mem key words {we, codes} (264 b); px.mem
// q words {xe, E4M3 codes} (264 b); pm.mem per key {ref, keep}; pe.mem per key
// {fault, score}.  Reports keys, errors, faults, the mode counters, the
// refusal counter and the last key's latency (its last block request to its
// score).
module tb_hdc_v41x_idx_pool #(
    parameter integer G = 1,
    parameter integer M = 1,
    parameter integer IH = 32,
    parameter integer RL = 2,
    parameter integer MAXT = 1024,
    parameter integer KD = 1 << 20,
    parameter integer XD = 1 << 16,
    parameter integer MAXK = 1 << 18
) (input wire clk);
    localparam integer L = 8 * G;
    localparam integer WW = 264, XW = 264, AW = 20, RWW = 16, NBW = 14, TGW = 4;
    reg [31:0]   tm [0:3*MAXT-1];
    reg [47:0]   wm [0:MAXT*IH-1];
    reg [WW-1:0] kmem [0:KD-1];
    reg [XW-1:0] xmem [0:XD-1];
    reg [1:0]    mm [0:MAXK-1];
    reg [16:0]   em [0:MAXK-1];
    integer ntok = 0, nkey = 0;
    initial begin
        if (!$value$plusargs("NTOK=%d", ntok)) ntok = 0;
        if (!$value$plusargs("NKEY=%d", nkey)) nkey = 0;
        $readmemh("pt.mem", tm, 0, 3 * ntok - 1);
        $readmemh("pw.mem", wm, 0, ntok * IH - 1);
        $readmemh("pk.mem", kmem);
        $readmemh("px.mem", xmem);
        $readmemh("pm.mem", mm, 0, nkey - 1);
        $readmemh("pe.mem", em, 0, nkey - 1);
    end

    reg rst_n = 1'b0;
    integer cyc = 0;
    reg                 d_v = 1'b0;
    wire                d_rdy;
    reg  [NBW-1:0]      d_nb = 4;
    reg  [RWW-1:0]      d_nrows = 0;
    reg  [AW-1:0]       d_wbase = 0;
    reg  [TGW-1:0]      d_tag = 0;
    wire [7:0]          rq_v, rq_src, rq_split;
    wire [8*AW-1:0]     rq_a;
    wire [8*NBW-1:0]    rq_q;
    wire [8*4-1:0]      rq_plg;
    wire [8*TGW-1:0]    rq_tag;
    wire [8*RWW-1:0]    rq_rg;
    reg  [L*WW-1:0]     rd_k;
    reg  [L*M*XW-1:0]   rd_x;
    wire                o_v;
    wire [RWW-1:0]      o_rg;
    wire [TGW-1:0]      o_tag;
    wire [G-1:0]        o_mask, o_smask;
    wire [G*M*32-1:0]   o_y, o_ys;
    wire [G*M*16-1:0]   o_bf, o_bfs;
    wire [G*M-1:0]      o_f, o_fs;
    wire [31:0]         cnt_rom, cnt_stream, cnt_split;
    wire                idle;
    ot_hdc_v41x_wgt_tile #(.KIND(0), .G(G), .M(M), .LB(5), .PMIN_LG(0), .AW(AW), .NBW(NBW), .RWW(RWW),
                           .EIW(9), .TGW(TGW), .RL(RL), .OCRED(128), .POOL(1)) pool (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(4'd0), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(1'b0), .d_eid(9'd0), .d_estride({AW{1'b0}}), .d_fp4(1'b1), .d_tag(d_tag),
        .d_src(1'b1), .d_split(1'b1),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(rq_src),
        .rq_split(rq_split), .rq_rg(rq_rg), .rd_w({L*WW{1'b0}}), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(o_v), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(o_smask), .o_ys(o_ys), .o_bfs(o_bfs), .o_fs(o_fs), .o_cnt_rom(cnt_rom),
        .o_cnt_stream(cnt_stream), .o_cnt_split(cnt_split), .idle(idle));

    // read network model (RL stages), split mapping
    reg [L*WW-1:0]   pk [0:RL-1];
    reg [L*M*XW-1:0] px [0:RL-1];
    reg [31:0] xb_tag [0:15];
    integer j, c, p, st, row, blk, tg, last_rq = 0;
    always @(posedge clk) begin
        for (j = 0; j < L; j = j + 1) begin
            c = j % 8;
            if (rq_v[c]) begin
                pk[0][j*WW +: WW] <= kmem[rq_a[c*AW +: AW] * L + j];
                tg = rq_tag[c*TGW +: TGW];
                row = rq_rg[c*RWW +: RWW] * 2 * G + 2 * (j / 8) + (((j % 8) >= 4) ? 1 : 0);
                blk = j % 4;
                for (p = 0; p < M; p = p + 1)
                    px[0][(j*M + p)*XW +: XW] <= xmem[xb_tag[tg] + ((row % (IH / M)) * 4 + blk) * M + p];
                last_rq = cyc;
            end else begin
                pk[0][j*WW +: WW] <= {WW{1'bx}};
                for (p = 0; p < M; p = p + 1) px[0][(j*M + p)*XW +: XW] <= {XW{1'bx}};
            end
        end
        for (st = 1; st < RL; st = st + 1) begin
            pk[st] <= pk[st-1];
            px[st] <= px[st-1];
        end
    end
    always @(*) begin
        rd_k = pk[RL-1];
        rd_x = px[RL-1];
    end

    // collector and head-sum stage
    wire             k_v;
    wire [IH*32-1:0] k_score;
    wire [IH-1:0]    k_fault;
    ot_hdc_v41x_idx_pcol #(.G(G), .M(M), .IH(IH)) col (.clk(clk), .rst_n(rst_n), .i_v(o_v), .i_smask(o_smask),
        .i_ys(o_ys), .i_fs(o_fs), .i_mask(o_mask), .i_y(o_y), .i_f(o_f), .k_v(k_v), .k_score(k_score),
        .k_fault(k_fault));
    reg        w_v = 1'b0;
    reg [7:0]  w_head = 0;
    reg [15:0] w_w = 0;
    reg [31:0] w_qsc = 0;
    integer kin = 0;
    wire [1:0] meta = mm[kin];
    wire        h_v;
    wire [0:0]  h_kv, h_fault;
    wire [15:0] h_score;
    wire [47:0] cnt_ref;
    ot_hdc_v41x_idx_hsum #(.IH(IH), .NKT(1), .NBQ(4)) hs (.clk(clk), .rst_n(rst_n), .w_v(w_v), .w_head(w_head),
        .w_w(w_w), .w_qsc(w_qsc), .i_v(k_v), .i_kv(1'b1), .i_ref(meta[1]), .i_keep(meta[0]), .i_score(k_score),
        .i_fault(k_fault), .o_v(h_v), .o_kv(h_kv), .o_score(h_score), .o_fault(h_fault), .cnt_refused(cnt_ref));
    always @(posedge clk) if (k_v) kin <= kin + 1;

    integer stt = 0, tok = 0, h = 0, kend = 0, kout = 0, errors = 0, faults = 0, wait_c = 0;
    integer lat_last = -1, beats_exp = 0, first_out = -1, t_desc = -1, lat_first = -1;
    reg [16:0] e;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (h_v) begin
            e = em[kout];
            if (e[16] ? !h_fault[0] : (h_fault[0] || h_score != e[15:0])) begin
                errors = errors + 1;
                if (errors <= 10) $display("MISMATCH key %0d got %h f%0d exp %h", kout, h_score, h_fault[0], e);
            end else if (e[16]) faults = faults + 1;
            if (lat_first < 0) lat_first = cyc - t_desc;
            kout = kout + 1;
            if (kout == kend) lat_last = cyc - last_rq;
        end
        w_v <= 1'b0;
        if (d_v && d_rdy) d_v <= 1'b0;
        if (rst_n) case (stt)
            0: if (tok >= ntok) stt = 9;
               else begin
                   w_v <= 1'b1; w_head <= h[7:0]; {w_qsc, w_w} <= wm[tok * IH + h];
                   if (h == IH - 1) begin h = 0; stt = 1; wait_c = 0; end
                   else h = h + 1;
               end
            1: begin
                   wait_c = wait_c + 1;
                   if (wait_c >= 3) begin
                       xb_tag[tok % 16] = tm[3 * tok];
                       d_wbase <= tm[3 * tok + 1];
                       d_nrows <= tm[3 * tok + 2] * (IH / M);
                       d_tag <= tok % 16;
                       d_v <= 1'b1;
                       t_desc = cyc + 1;
                       kend = kend + tm[3 * tok + 2];
                       beats_exp = beats_exp + tm[3 * tok + 2] * (IH / M) / (2 * G);
                       stt = 2;
                   end
               end
            2: if (!d_v && kout >= kend) begin tok = tok + 1; stt = 0; end
            default: begin
                $display("V41XPOOLCNT stream_beats=%0d split_beats=%0d rom_beats=%0d expected_beats=%0d refused=%0d",
                         cnt_stream, cnt_split, cnt_rom, beats_exp, cnt_ref);
                $display("V41XPOOL keys=%0d checked=%0d errors=%0d faults_expected_and_raised=%0d lat_first=%0d lat_last=%0d cycles=%0d",
                         nkey, kout, errors, faults, lat_first, lat_last, cyc);
                $finish;
            end
        endcase
        if (cyc > 50000000) begin $display("V41XPOOL TIMEOUT"); $finish; end
    end
endmodule
