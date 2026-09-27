`timescale 1ns/1ps
// Correctness-rate bridge from a four-stack idx_kmerge beat to one pooled
// block-dot tile.  It holds 64 keys, presents their four FP4 blocks on the
// tile's rd_k port at RL=2, and tags each score with its original quarter
// position for the core's vector-memory writer.  Query FP8 words on rd_x and
// head weights are supplied by the core's query loader; this block does not
// implement that loader.  One G=4,M=2 tile takes two dot-result events per
// key, so this bridge back-pressures kmerge and is a correctness stage, not
// the 64-key/cycle full-rate die implementation (which needs replicated tiles).
module ot_hdc_v41x_idx_pool_batch #(
    parameter integer G = 4,
    parameter integer M = 2,
    parameter integer IH = 32,
    parameter integer AW = 20,
    parameter integer RL = 2
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    cmd_v,
    input  wire [29:0]             cmd_nkeys,
    input  wire                    b_valid,
    output wire                    b_ready,
    input  wire [63:0]             b_kv,
    input  wire [63:0]             b_ref,
    input  wire [63:0]             b_keep,
    input  wire [64*544-1:0]       b_key,
    input  wire                    w_v,
    input  wire [7:0]              w_head,
    input  wire [15:0]             w_w,
    input  wire [31:0]             w_qsc,
    output wire [7:0]              rq_v,
    output wire [8*AW-1:0]         rq_a,
    output wire [8*14-1:0]         rq_q,
    output wire [8*4-1:0]          rq_plg,
    output wire [8*4-1:0]          rq_tag,
    output wire [7:0]              rq_src,
    output wire [7:0]              rq_split,
    output wire [8*16-1:0]         rq_rg,
    input  wire [8*G*M*264-1:0]    rd_x,
    output wire                    o_valid,
    output wire                    o_write,
    output wire [29:0]             o_index,
    output wire [15:0]             o_score,
    output wire                    o_fault,
    output wire                    protocol_fault
);
    localparam integer L = 8*G;
    localparam integer HK = IH/M;
    localparam [1:0] IDLE=0, META=1, DESC=2, RUN=3;
    reg [1:0] state;
    reg [64*544-1:0] keys;
    reg [63:0] valid_key, ref_key, keep_key;
    reg [6:0] sent, scored;
    reg [29:0] quarter_size, beat_no, this_beat;
    wire d_rdy, p_v, p_idle, m_ready;
    wire [15:0] p_rg;
    wire [3:0] p_tag;
    wire [G-1:0] p_mask, p_smask;
    wire [G*M*32-1:0] p_y, p_ys;
    wire [G*M*16-1:0] p_bf, p_bfs;
    wire [G*M-1:0] p_f, p_fs;
    wire [31:0] cnt_rom, cnt_stream, cnt_split;
    wire [47:0] cnt_refused;

    assign b_ready = state == IDLE;
    wire m_v = state == META && sent < 64;
    wire [5:0] m_slot = sent[5:0];
    ot_hdc_v41x_idx_pool_finish #(.G(G), .M(M), .IH(IH), .MD(128)) finish (
        .clk(clk), .rst_n(rst_n), .m_v(m_v), .m_ready(m_ready),
        .m_keep(valid_key[m_slot] && keep_key[m_slot]), .m_ref(ref_key[m_slot]),
        .w_v(w_v), .w_head(w_head), .w_w(w_w), .w_qsc(w_qsc),
        .p_v(p_v), .p_smask(p_smask), .p_ys(p_ys), .p_fs(p_fs),
        .p_mask(p_mask), .p_y(p_y), .p_f(p_f),
        .o_v(o_valid), .o_score(o_score), .o_fault(o_fault),
        .cnt_refused(cnt_refused), .protocol_fault(protocol_fault));

    ot_hdc_v41x_wgt_tile #(.KIND(0), .G(G), .M(M), .LB(5), .PMIN_LG(0),
        .AW(AW), .NBW(14), .RWW(16), .EIW(9), .TGW(4), .RL(RL), .OCRED(128), .POOL(1)) tile (
        .clk(clk), .rst_n(rst_n), .d_v(state == DESC), .d_rdy(d_rdy),
        .d_plg(4'd0), .d_nb(14'd4), .d_nrows(16'(64*HK)), .d_wbase({AW{1'b0}}),
        .d_ind(1'b0), .d_eid(9'd0), .d_estride({AW{1'b0}}), .d_fp4(1'b1),
        .d_tag(4'd0), .d_src(1'b1), .d_split(1'b1),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag),
        .rq_src(rq_src), .rq_split(rq_split), .rq_rg(rq_rg),
        .rd_w({L*264{1'b0}}), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(p_v), .o_v(p_v), .o_rg(p_rg), .o_tag(p_tag),
        .o_mask(p_mask), .o_y(p_y), .o_bf(p_bf), .o_f(p_f),
        .o_smask(p_smask), .o_ys(p_ys), .o_bfs(p_bfs), .o_fs(p_fs),
        .o_cnt_rom(cnt_rom), .o_cnt_stream(cnt_stream), .o_cnt_split(cnt_split), .idle(p_idle));

    // One key contributes HK rows.  A split event contributes 2*G rows;
    // chain lane j names the row and block exactly as tb_hdc_v41x_idx_pool.
    reg [L*264-1:0] kp [0:RL-1];
    wire [L*264-1:0] rd_k = kp[RL-1];
    integer j, s, row, keyno, blk, c;
    reg [543:0] keyword;
    always @(posedge clk) begin
        for (j=0; j<L; j=j+1) begin
            c = j % 8;
            row = rq_a[c*AW +: AW] * (2*G) + 2*(j/8) + ((j%8)>=4);
            keyno = row/HK;
            blk = j%4;
            keyword = keys[544*keyno +: 544];
            kp[0][264*j +: 264] <= rq_v[c] ?
                {keyword[512+8*blk +: 8], 128'd0, keyword[128*blk +: 128]} : 264'd0;
        end
        for (s=1; s<RL; s=s+1) kp[s] <= kp[s-1];
    end

    wire [1:0] out_quarter = scored[5:4];
    wire [29:0] index_now = out_quarter*quarter_size + this_beat*30'd16 + {26'd0,scored[3:0]};
    assign o_index = index_now;
    assign o_write = o_valid && valid_key[scored[5:0]] && index_now < cmd_nkeys;

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE; sent <= 0; scored <= 0;
            quarter_size <= 0; beat_no <= 0; this_beat <= 0;
        end else begin
            if (cmd_v) begin
                quarter_size <= {cmd_nkeys[29:5],3'b000};
                beat_no <= 0;
            end
            case (state)
                IDLE: if (b_valid) begin
                    keys <= b_key; valid_key <= b_kv; ref_key <= b_ref; keep_key <= b_keep;
                    sent <= 0; scored <= 0; this_beat <= beat_no;
                    beat_no <= beat_no + 1'b1;
                    state <= META;
                end
                META: if (m_v && m_ready) begin
                    sent <= sent + 1'b1;
                    if (sent == 63) state <= DESC;
                end
                DESC: if (d_rdy) state <= RUN;
                RUN: if (o_valid) begin
                    scored <= scored + 1'b1;
                    if (scored == 63) state <= IDLE;
                end
            endcase
        end
    end
endmodule
