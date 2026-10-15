`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE s81die-1011/ctrl svch: the ATTENTION QUARTER of one dsfd_svc_quad (quadrant QID of slab ST, die DIE_ID).
// Decomposition = head_dim split (exact, no cross-quadrant row traffic): quadrant g owns dims 128 g .. 128 g + 127 =
// the D = 512 engine's q.k tiles / CKV groups 4 g .. 4 g + 3 of every lane, and runs the UNCHANGED engine
// ot_hdc_v41x_attn_s with D = 128 (S = 4 tiles a lane; H 16, TD 32, NL 4, TROWS 640 and every latency parameter as
// ot_s81_svcq_attn).  Its lane-tree root (heap nodes 0 = 1 + 2, 1 = leaves 0 + 1, 2 = leaves 2 + 3) is exactly the
// D = 512 tree's level-2 node 3 + g; the levels above ((Q0 + Q1) + (Q2 + Q3), same ot_hdc_v41x_qaddf FX / F12, fault
// OR) are ot_s81_svch_comb on the registered seams.  p.v tile t of the D = 128 engine is dims 8 t + pv_c of the
// quarter (DPT 8 as in D = 512, where tile t is dims 8 t + pv_c), so the slab's owned dims 128 ST .. are quadrant
// ST's whole p.v: only quadrant ST stores probabilities and emits p.v; the others feed the engine counted all-zero
// p words (their p.v is dropped; the engine's q.k is independent of p).
// Per-quadrant controller copy (lockstep by data, not by cycle): the q frame parser, job, SEL_IDS table, ROWS port,
// the row assembler ot_s81_svcq_rows and the merger ot_chip_v41x_ckv_stream_merge, both UNCHANGED and fed with the
// rows' other quarters as zero (their presence bits still follow every word, so completion order = the flat slab's;
// synthesis drops the constant storage).  Row sources: window beats (dim slice, from the home's window source over a
// credit lane), locally fetched rows (dim slice, valid-only broadcast from the home's fetch), ROWS q words.
// q frames as ot_s81_svcq_attn (types 1 ATTN_Q, 2 WIN_LOAD, 5 PV, 6 ROWS, 7 SEL_IDS; 3 / 4 / 12 skipped by length).
// Outputs: score beats {row 16, mask 4, y 4 x 16 x FP32, flags 64} (valid/ready, SC_CRED FIFO, engine credits on pop);
// p.v as 17-word beats on the PV lane (word 0 {1, pv_c, 256 flags}, words 1..16 = tile j's 16 heads x FP32).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svch_attq #(
    parameter integer QID = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer PFIFO = 512,
    parameter integer SC_CRED = 8,
    parameter integer PV_CRED = 4,
    parameter bit SRAM_MACRO = 0,
    parameter integer ENGINE = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 q_v,
    input  wire [511:0]         q_d,
    // window beats (dim slice: row l at [1056 l +: 1056] = {scales 32, codes 1024})
    input  wire                 w_v,
    output wire                 w_ready,
    input  wire [3:0]           w_m,
    input  wire [4*1056-1:0]    w_sl,
    // locally fetched rows (dim slice {scales 64, codes 512}), valid-only
    input  wire                 l_v,
    input  wire [9:0]           l_rank,
    input  wire [20:0]          l_gid,
    input  wire [575:0]         l_sl,
    // score beats
    output wire                 s_v,
    input  wire                 s_r,
    output wire [2131:0]        s_d,
    // p.v lane words {hdr, data 512}
    output reg                  p_ov,
    input  wire                 p_or,
    output reg  [512:0]         p_od,
    // job / assembler state for the home (quadrant 2)
    output reg                  go,
    output reg  [7:0]           tagj,
    output reg  [20:0]          posj,
    output reg  [9:0]           userj,
    output reg  [7:0]           wcount,
    output reg  [9:0]           nsel,
    output reg  [29:0]          rbase,
    output reg  [29:0]          rcount,
    output reg  [20:0]          npub,
    output reg                  wj_v,
    output reg  [9:0]           wj_user,
    output reg  [20:0]          wj_first,
    output reg  [7:0]           wj_count,
    output wire [511:0]         held,
    output wire [9:0]           own_count,
    output wire                 own_done,
    input  wire [9:0]           own_idx,
    output wire [9:0]           own_rank,
    output wire [20:0]          own_gid,
    output wire                 fault,
    output wire [15:0]          fault_code
);
    localparam integer H = 16, D = 128, TD = 32, NL = 4, K = 512, KW = 10, POS_W = 21;
    localparam integer G = D / 32, ROWW = G * 265, NT = NL * (D / TD), R = TD / H;
    localparam integer PFW = $clog2(PFIFO);
    localparam bit PVOWN = (QID == ST);

    // ---------------- frame parser ----------------
    reg in_frame; reg [11:0] left; reg [3:0] f_type; reg f_mine; reg [511:0] f_hdr; reg [11:0] f_idx;
    wire [3:0]  h_type = q_d[511:508];
    wire [3:0]  h_mask = q_d[506:503];
    wire [11:0] h_len  = q_d[491:480];
    wire is_hdr = q_v && !in_frame;
    wire is_pay = q_v && in_frame;
    reg [15:0] fc;
    assign fault_code = fc;
    assign fault = |fc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin in_frame <= 0; left <= 0; f_type <= 0; f_mine <= 0; f_idx <= 0; end
        else if (is_hdr) begin
            f_type <= h_type; f_mine <= h_mask[0]; f_idx <= 0; left <= h_len; in_frame <= h_len != 0;
        end else if (is_pay) begin
            f_idx <= f_idx + 1'b1; left <= left - 1'b1; if (left == 12'd1) in_frame <= 1'b0;
        end
    end
    always @(posedge clk) if (is_hdr) f_hdr <= q_d;
    wire hdr_mine = is_hdr && h_mask[0];
    wire pay_mine = is_pay && f_mine;

    // ---------------- job ----------------
    reg job_active;
    wire start = hdr_mine && h_type == 4'd2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin go <= 0; wj_v <= 0; tagj <= 0; posj <= 0; userj <= 0; wcount <= 0; nsel <= 0; end
        else begin
            go <= start && !job_active && h_len == 0 && q_d[88:81] <= 8'd128 && q_d[98:89] <= 10'd512;
            wj_v <= start && !job_active;
            if (start && !job_active) begin
                tagj <= q_d[502:495]; posj <= q_d[479:459]; userj <= q_d[458:449];
                wcount <= q_d[88:81]; nsel <= q_d[98:89];
            end
        end
    end
    always @(posedge clk) if (start && !job_active) begin
        rbase <= q_d[29:0]; rcount <= q_d[59:30]; npub <= q_d[80:60];
        wj_user <= q_d[458:449]; wj_first <= q_d[119:99]; wj_count <= q_d[88:81];
    end
    wire [15:0] tjob = 16'(wcount) + 16'(nsel);

    // ---------------- SEL_IDS -> assembler table ----------------
    reg t_v; reg [KW-1:0] t_rank; reg [4:0] t_n; reg [511:0] t_ids; reg [KW-1:0] s_first; reg [9:0] s_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t_v <= 0;
        else begin
            t_v <= pay_mine && f_type == 4'd7;
        end
    end
    always @(posedge clk) begin
        if (hdr_mine && h_type == 4'd7) begin s_first <= q_d[9:0]; s_cnt <= q_d[19:10]; end
        if (pay_mine && f_type == 4'd7) begin
            t_ids <= q_d;
            t_rank <= s_first + KW'(f_idx * 16);
            t_n <= (32'(s_cnt) - 32'(f_idx) * 16 >= 16) ? 5'd16 : 5'(32'(s_cnt) - 32'(f_idx) * 16);
        end
    end

    // ---------------- ROWS -> assembler (other quarters' pairs as zero) ----------------
    reg r_v; reg [KW-1:0] r_rank; reg [POS_W-1:0] r_gid; reg [2:0] r_pair; reg [287:0] r_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_v <= 0;
        else begin
            r_v <= pay_mine && f_type == 4'd6;
        end
    end
    always @(posedge clk) begin
        r_rank <= q_d[9:0]; r_gid <= q_d[30:10]; r_pair <= q_d[33:31];
        r_data <= (q_d[33:32] == 2'(QID)) ? q_d[321:34] : 288'd0;
    end
    // locally fetched row slice -> a 2,304-bit row with the other quarters zero
    reg [2303:0] l_row;
    always @(*) begin
        l_row = 2304'd0;
        l_row[512*QID +: 512] = l_sl[511:0];
        l_row[2048 + 64*QID +: 64] = l_sl[575:512];
    end

    // ---------------- assembler (unchanged) ----------------
    wire [2:0] c_n, c_take; wire [KW-1:0] c_rank; wire [4*2304-1:0] c_rows;
    wire a_done, a_fault; wire [5:0] a_fc;
    ot_s81_svcq_rows #(.DIE_ID(DIE_ID), .ST(ST), .K(K), .POS_W(POS_W)) u_rows (
        .clk(clk), .rst_n(rst_n), .clr(go), .exp_n(nsel),
        .t_v(t_v), .t_rank(t_rank), .t_n(t_n), .t_ids(t_ids),
        .own_count(own_count), .own_done(own_done), .own_idx(own_idx), .own_rank(own_rank), .own_gid(own_gid),
        .l_v(l_v), .l_rank(l_rank), .l_gid(l_gid), .l_row(l_row),
        .r_v(r_v), .r_rank(r_rank), .r_gid(r_gid), .r_pair(r_pair), .r_data(r_data),
        .held(held), .o_n(c_n), .o_take(c_take), .o_rank(c_rank), .o_row(c_rows),
        .done(a_done), .fault(a_fault), .fault_code(a_fc));

    // ---------------- merger (unchanged; window rows' other quarters zero) ----------------
    reg [4*4224-1:0] w_rows;
    integer wl;
    always @(*) begin
        w_rows = '0;
        for (wl = 0; wl < 4; wl = wl + 1) begin
            w_rows[wl*4224 + 1024*QID +: 1024] = w_sl[wl*1056 +: 1024];
            w_rows[wl*4224 + 4096 + 32*QID +: 32] = w_sl[wl*1056 + 1024 +: 32];
        end
    end
    wire kv_v, kv_ready; wire [3:0] kv_m; wire [NL*16*265-1:0] kv_full;
    wire m_jready, m_done, m_fault; wire [1:0] m_fc;
    ot_chip_v41x_ckv_stream_merge u_mrg (
        .clk(clk), .rst_n(rst_n), .job_v(go), .job_ready(m_jready),
        .window_count(wcount), .n_sel(nsel),
        .w_v(w_v), .w_ready(w_ready), .w_m(w_m), .w_rows(w_rows),
        .c_n(c_n), .c_take(c_take), .c_rank(c_rank), .c_rows(c_rows),
        .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_full),
        .done(m_done), .fault(m_fault), .fault_code(m_fc));
    wire [NL*ROWW-1:0] kv_w;
    genvar gl, gg;
    generate for (gl = 0; gl < NL; gl = gl + 1) begin : g_kl
        for (gg = 0; gg < G; gg = gg + 1) begin : g_kg
            assign kv_w[(gl*G + gg)*265 +: 265] = kv_full[(gl*16 + G*QID + gg)*265 +: 265];
        end
    end endgenerate

    // ---------------- q store (16 heads, this quarter's 128 dims) ----------------
    reg [D*16-1:0] qmem [0:H-1];
    reg [4:0] q_have, q_rd;
    always @(posedge clk) if (pay_mine && f_type == 4'd1 && f_idx[3:2] == 2'(QID))
        qmem[{f_hdr[448], f_idx[6:4]}][512*f_idx[1:0] +: 512] <= q_d;
    wire eq_v = q_rd < q_have;
    wire eq_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin q_have <= 0; q_rd <= 0; end
        else if (go) begin q_have <= 0; q_rd <= 0; end
        else begin
            if (pay_mine && f_type == 4'd1 && f_idx[3:0] == 4'hf) q_have <= q_have + 1'b1;
            if (eq_v && eq_ready) q_rd <= q_rd + 1'b1;
        end
    end

    // ---------------- p FIFO (stored only in the p.v-owning quadrant) ----------------
    reg [PFW:0] pw, pr;
    wire [PFW:0] pcnt = pw - pr;
    reg [15:0] p_left;
    wire [1:0] pstep = (p_left >= 16'd2) ? 2'd2 : 2'(p_left);
    wire ep_v = job_active && p_left != 0 && pcnt >= (PFW+1)'(pstep);
    wire ep_ready;
    wire [2*TD*16-1:0] ep_w;
    generate if (PVOWN) begin : g_pm
        reg [TD*16-1:0] pmem [0:PFIFO-1];
        always @(posedge clk) if (pay_mine && f_type == 4'd5) pmem[pw[PFW-1:0]] <= q_d;
        assign ep_w = {(pstep == 2'd2) ? pmem[pr[PFW-1:0] + 1'b1] : {TD*16{1'b1}}, pmem[pr[PFW-1:0]]};
    end else begin : g_pz
        assign ep_w = '0;          // p.v of this quarter is never emitted
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pw <= 0; pr <= 0; p_left <= 0; end
        else begin
            if (pay_mine && f_type == 4'd5) pw <= pw + 1'b1;
            if (go) p_left <= (tjob + 16'(R) - 1) / 16'(R);
            else if (ep_v && ep_ready) begin pr <= pr + (PFW+1)'(pstep); p_left <= p_left - 16'(pstep); end
        end
    end

    // ---------------- engine (unchanged, D = 128) ----------------
    reg ej_pend;
    wire ej_ready;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ej_pend <= 0; else if (go) ej_pend <= 1'b1; else if (ej_ready) ej_pend <= 1'b0;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    reg sc_cr, pv_cr;
    generate if (ENGINE != 0) begin : g_eng
`ifdef SVCQ_ENG_FG3
        localparam integer E_FPL = 3, E_FML = 3, E_TS = 0, E_NAR = 0, E_MF = 0, E_TRX = 0, E_F12 = 0, E_FX = 0;
`else
        localparam integer E_FPL = 4, E_FML = 6, E_TS = 1, E_NAR = 1, E_MF = 1, E_TRX = 1, E_F12 = 1, E_FX = 5;
`endif
        ot_hdc_v41x_attn_s #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(640), .SRAM_MACRO(SRAM_MACRO), .PWORDS(2),
                             .ILV(1), .REPL(2), .NSTAGE(2), .FPL(E_FPL), .FML(E_FML), .NBANKP(0), .TILE_S(E_TS),
                             .NARROW(E_NAR), .MFAN(E_MF), .TRX(E_TRX), .F12(E_F12), .FPLX(E_FX),
                             .SC_CRED(SC_CRED), .PV_CRED(PV_CRED)) u_eng (
            .clk(clk), .rst_n(rst_n), .job_v(ej_pend), .job_t({1'b0, tjob[14:0]}), .job_ready(ej_ready),
            .q_v(eq_v), .q_w(qmem[q_rd[3:0]]), .q_ready(eq_ready),
            .kv_v(kv_v), .kv_m(kv_m), .kv_w(kv_w), .kv_ready(kv_ready),
            .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(sc_cr),
            .p_v(ep_v), .p_w(ep_w), .p_ready(ep_ready),
            .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f), .pv_cr(pv_cr),
            .qk_iss(), .pv_iss());
    end else begin : g_noeng
        assign ej_ready = 1'b1; assign eq_ready = 1'b1; assign kv_ready = 1'b1; assign ep_ready = 1'b1;
        assign sc_v = 0; assign sc_row = 0; assign sc_m = 0; assign sc_y = 0; assign sc_f = 0;
        assign pv_v = 0; assign pv_c = 0; assign pv_y = 0; assign pv_f = 0;
    end endgenerate

    // ---------------- score beats: FIFO of SC_CRED beats, a credit per pop ----------------
    localparam integer SCB = 16 + 4 + NL*H*32 + NL*H;      // 2,132
    localparam integer SA = $clog2(SC_CRED);
    reg [SCB-1:0] scq [0:SC_CRED-1];
    reg [SA:0] scw, scr;
    always @(posedge clk) if (sc_v) scq[scw[SA-1:0]] <= {sc_row, sc_m, sc_y, sc_f};
    assign s_v = scw != scr;
    assign s_d = scq[scr[SA-1:0]];

    // ---------------- p.v beats: FIFO of PV_CRED beats -> 17-word lane beats (owner only) ----------------
    localparam integer PVB = 8 + NT*H*32 + NT*H;
    localparam integer PA = $clog2(PV_CRED);
    reg [PVB-1:0] pvq [0:PV_CRED-1];
    reg [PA:0] pvw, pvr;
    reg [4:0] p_i;
    reg [3:0] pv_n;                    // engine p.v beats of the job
    always @(posedge clk) if (pv_v) pvq[pvw[PA-1:0]] <= {pv_c, pv_y, pv_f};
    wire [PVB-1:0] pb = pvq[pvr[PA-1:0]];
    always @(posedge clk) if (PVOWN && (!p_ov || p_or) && pvw != pvr)
        p_od <= (p_i == 0) ? {1'b1, 248'd0, pb[PVB-1 -: 8], pb[NT*H-1:0]} : {1'b0, pb[NT*H + 32'(p_i - 1)*H*32 +: H*32]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scw <= 0; scr <= 0; pvw <= 0; pvr <= 0; sc_cr <= 0; pv_cr <= 0; p_ov <= 0; p_i <= 0; job_active <= 0;
            pv_n <= 0; fc <= 0;
        end else begin
            sc_cr <= 1'b0; pv_cr <= 1'b0;
            if (sc_v) scw <= scw + 1'b1;
            if (s_v && s_r) begin scr <= scr + 1'b1; sc_cr <= 1'b1; end
            if (go) begin job_active <= 1'b1; pv_n <= 0; end
            else if (pv_v) begin pv_n <= pv_n + 1'b1; if (pv_n == 4'd7) job_active <= 1'b0; end
            if (PVOWN) begin
                if (pv_v) pvw <= pvw + 1'b1;
                if (p_ov && p_or) p_ov <= 1'b0;
                if ((!p_ov || p_or) && pvw != pvr) begin
                    p_ov <= 1'b1;
                    p_i <= (p_i == 5'd16) ? 5'd0 : p_i + 1'b1;
                    if (p_i == 5'd16) begin pvr <= pvr + 1'b1; pv_cr <= 1'b1; end
                end
            end else pv_cr <= pv_v;           // p.v of this quarter is dropped
            // faults (as ot_s81_svcq_attn)
            if (start && job_active) fc[0] <= 1'b1;
            if (start && (h_len != 0 || q_d[88:81] > 8'd128 || q_d[98:89] > 10'd512)) fc[1] <= 1'b1;
            if (hdr_mine && !(h_type inside {4'd1, 4'd2, 4'd3, 4'd4, 4'd5, 4'd6, 4'd7, 4'd12})) fc[2] <= 1'b1;
            if (hdr_mine && h_type == 4'd1 && h_len != 12'd128) fc[2] <= 1'b1;
            if (hdr_mine && (h_type inside {4'd1, 4'd5, 4'd6, 4'd7}) && !job_active) fc[3] <= 1'b1;
            if (pay_mine && f_type == 4'd5 && pcnt >= (PFW+1)'(PFIFO)) fc[4] <= 1'b1;
            if (hdr_mine && h_type == 4'd1 && (q_d[448] != q_have[3] || q_have[2:0] != 3'd0)) fc[5] <= 1'b1;
            if (sc_v && 32'(scw - scr) >= SC_CRED) fc[6] <= 1'b1;
            if (pv_v && PVOWN && 32'(pvw - pvr) >= PV_CRED) fc[6] <= 1'b1;
            if (a_fault) fc[7] <= 1'b1;
            if (m_fault) fc[9] <= 1'b1;
        end
    end
endmodule
