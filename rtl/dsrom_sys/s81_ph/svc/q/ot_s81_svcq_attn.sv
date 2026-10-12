`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE s81-svcq-1011: ATTENTION compute of one S81 scan-service slab (stack ST of die DIE_ID), behind the svc frame
// protocol v1 (s81-svceng-1011; header [511:508] type, [507] END, [506:503] quadrant mask / source, [502:495] tag,
// [491:480] len, [479:459] pos, [458:449] user, [448:0] type-specific).
//
// One job per layer: rows staged in the golden's order (window rows oldest first, then selected rows in rank order;
// ot_chip_v41x_ckv_stream_merge, unchanged), the UNCHANGED attention engine ot_hdc_v41x_attn_s (H16 D512 TD32 NL4
// TROWS640, the closing 1.2 GHz configuration: PWORDS2 ILV1 REPL2 NSTAGE2 FPL4 FML6 TILE_S NARROW MFAN TRX F12 FPLX5)
// computes q.k for every staged row and p.v for every dim.  Exactness split (ot_s81ph_col.sv DECISION, see
// ot_s81_svcq_rows.sv): this slab EMITS the score rows it holds (window rows with row % 4 == ST, selected rows whose
// owner stack == ST: those are staged whole) and the p.v dims it owns (128 ST .. 128 ST + 127: staged for every row).
// Nothing else derived here leaves the slab, so every emitted value is the engine's full-row / full-T result = the
// golden's.
//
// q frames accepted here (mask bit 0; the slab's other types 3 OWN_ROW, 4 IDX_Q, 12 CFG and other masks are skipped by
// length; an unknown type is a fault):
//   2 WIN_LOAD  job start, len 0. spec [29:0] region base sector (this stack's selected-CKV region), [59:30] its
//               sector count, [80:60] published source count, [88:81] window count (<= 128), [98:89] n_sel (<= 512),
//               [119:99] window first position.  Starts the row assembler, the owned-row fetch, the merger, the
//               window job (wj_* out) and the engine job (T = window count + n_sel).  A WIN_LOAD while a job is
//               active is a fault.
//   7 SEL_IDS   spec [9:0] first rank, [19:10] entries in the frame; payload words of 16 x 32-bit ids, rank order.
//   1 ATTN_Q    spec [448] half (0: heads 0..7, 1: heads 8..15), len 128: word i = head 8 half + i / 16, BF16
//               elements 32 (i % 16) .. +31 (element e at bits 16 (e % 32)).
//   6 ROWS      payload word: [9:0] rank, [30:10] id, [33:31] chunk pair, [321:34] pair data (288 b).
//   5 PV        payload words = the engine's probability words (TD x BF16), in engine order.
// Result frames (tag / pos / user of the job's WIN_LOAD):
//   a0 8 ATTN_OUT  spec [448:447] sub, [446:431] row (scores) / beat pv_c (p.v), [430:427] row mask, flags at [255:0]
//                  sub 0 SCORE: one word per held row of an engine beat (16 heads x FP32, head h at [32 h +: 32]),
//                        flags [63:0] = the beat's sc_f (row l head h at bit 16 l + h)
//                  sub 1 PV: 16 words (dim 128 ST + 8 j + pv_c, 16 heads x FP32), flags [255:0] (word j head h at 16 j + h)
//                  END on the job's last PV frame (source id 0).
//   od 11 ROWX   one frame per locally fetched row, len 8: the row's eight ROWS words (pairs 0..7), for the peers.
// Valid-only q (no back-pressure): every input is absorbed at one word a cycle (q store 16 heads, p FIFO PFIFO words,
// ROWS straight into the assembler); overflow is a fault.  Sticky faults stop every result stream (fail closed).
// ---------------------------------------------------------------------------
module ot_s81_svcq_attn #(
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer P = 8,               // owned-row fetch ports
    parameter integer S = 16,
    parameter integer PFIFO = 512,
    parameter integer SC_CRED = 8,
    parameter integer PV_CRED = 4,
    parameter bit SRAM_MACRO = 0,
    parameter integer ENGINE = 1,          // 0: no engine (row checker benches only)
    parameter integer HAW = 30,
    parameter integer SW = (S > 1) ? $clog2(S) : 1,
    parameter integer TAGW = SW + 4
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 q_v,
    input  wire [511:0]         q_d,
    // window job (to the window source) and its rows (stage4 four-row beats)
    output reg                  wj_v,
    output reg  [9:0]           wj_user,
    output reg  [20:0]          wj_first,
    output reg  [7:0]           wj_count,
    input  wire                 w_v,
    output wire                 w_ready,
    input  wire [3:0]           w_m,
    input  wire [4*4224-1:0]    w_rows,
    // owned-row fetch HBM ports
    output wire [P-1:0]         m_v,
    input  wire [P-1:0]         m_rdy,
    output wire [P*HAW-1:0]     m_addr,
    output wire [P*TAGW-1:0]    m_tag,
    input  wire [P-1:0]         s_v,
    input  wire [P*TAGW-1:0]    s_tag,
    input  wire [P*4-1:0]       s_beat,
    input  wire [P*256-1:0]     s_data,
    // results
    output reg                  a0_v,
    output reg  [511:0]         a0_d,
    input  wire                 a0_r,
    output reg                  od_v,
    output reg  [511:0]         od_d,
    input  wire                 od_r,
    // engine-side visibility (bench) and status
    output wire                 kv_beat,
    output wire                 qk_iss,
    output wire                 pv_iss,
    output reg                  job_active,
    output wire                 fault,
    output wire [15:0]          fault_code
);
    localparam integer H = 16, D = 512, TD = 32, NL = 4, K = 512, KW = 10, POS_W = 21;
    localparam integer G = D / 32, ROWW = G * 265, NT = NL * (D / TD), DPT = D / NT, R = TD / H;
    localparam integer PFW = $clog2(PFIFO);

    // ---------------- frame parser ----------------
    reg in_frame;
    reg [11:0] left;
    reg [3:0] f_type;
    reg f_mine;
    reg [511:0] f_hdr;
    reg [11:0] f_idx;                  // payload word index within the frame
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
            f_hdr <= q_d; f_type <= h_type; f_mine <= h_mask[0]; f_idx <= 0; left <= h_len;
            in_frame <= h_len != 0;
        end else if (is_pay) begin
            f_idx <= f_idx + 1'b1; left <= left - 1'b1;
            if (left == 12'd1) in_frame <= 1'b0;
        end
    end
    wire hdr_mine = is_hdr && h_mask[0];
    wire pay_mine = is_pay && f_mine;

    // ---------------- job ----------------
    reg [7:0] tagj; reg [20:0] posj; reg [9:0] userj;
    reg [7:0] wcount; reg [KW-1:0] nsel;
    reg [29:0] rbase, rcount; reg [20:0] npub;
    reg go;                            // one-cycle job start
    wire start = hdr_mine && h_type == 4'd2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin go <= 0; wj_v <= 0; tagj <= 0; posj <= 0; userj <= 0; wcount <= 0; nsel <= 0; end
        else begin
            go <= start && !job_active && h_len == 0 && q_d[88:81] <= 8'd128 && q_d[98:89] <= 10'd512;
            wj_v <= start && !job_active;
            if (start && !job_active) begin
                tagj <= q_d[502:495]; posj <= q_d[479:459]; userj <= q_d[458:449];
                rbase <= q_d[29:0]; rcount <= q_d[59:30]; npub <= q_d[80:60];
                wcount <= q_d[88:81]; nsel <= q_d[98:89];
                wj_user <= q_d[458:449]; wj_first <= q_d[119:99]; wj_count <= q_d[88:81];
            end
        end
    end
    wire [15:0] tjob = 16'(wcount) + 16'(nsel);   // valid from go (latched with start)

    // ---------------- SEL_IDS -> assembler table ----------------
    reg t_v; reg [KW-1:0] t_rank; reg [4:0] t_n; reg [511:0] t_ids;
    reg [KW-1:0] s_first; reg [9:0] s_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t_v <= 0;
        else begin
            t_v <= 1'b0;
            if (hdr_mine && h_type == 4'd7) begin s_first <= q_d[9:0]; s_cnt <= q_d[19:10]; end
            if (pay_mine && f_type == 4'd7) begin
                t_v <= 1'b1; t_ids <= q_d;
                t_rank <= s_first + KW'(f_idx * 16);
                t_n <= (32'(s_cnt) - 32'(f_idx) * 16 >= 16) ? 5'd16 : 5'(32'(s_cnt) - 32'(f_idx) * 16);
            end
        end
    end

    // ---------------- ROWS -> assembler remote port ----------------
    reg r_v; reg [KW-1:0] r_rank; reg [POS_W-1:0] r_gid; reg [2:0] r_pair; reg [287:0] r_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_v <= 0;
        else begin
            r_v <= pay_mine && f_type == 4'd6;
            r_rank <= q_d[9:0]; r_gid <= q_d[30:10]; r_pair <= q_d[33:31]; r_data <= q_d[321:34];
        end
    end

    // ---------------- assembler + owned-row fetch ----------------
    wire [KW-1:0] own_count, own_idx, own_rank; wire own_done; wire [POS_W-1:0] own_gid;
    wire f_ov, f_or; wire [KW-1:0] f_rank; wire [POS_W-1:0] f_gid; wire [2303:0] f_row;
    wire f_run, f_done, f_fault; wire [3:0] f_fc;
    wire [K-1:0] held; wire [2:0] c_n, c_take; wire [KW-1:0] c_rank; wire [4*2304-1:0] c_rows;
    wire a_done, a_fault; wire [5:0] a_fc;
    ot_s81_svcq_rows #(.DIE_ID(DIE_ID), .ST(ST), .K(K), .POS_W(POS_W)) u_rows (
        .clk(clk), .rst_n(rst_n), .clr(go), .exp_n(nsel),
        .t_v(t_v), .t_rank(t_rank), .t_n(t_n), .t_ids(t_ids),
        .own_count(own_count), .own_done(own_done), .own_idx(own_idx), .own_rank(own_rank), .own_gid(own_gid),
        .l_v(f_ov && f_or), .l_rank(f_rank), .l_gid(f_gid), .l_row(f_row),
        .r_v(r_v), .r_rank(r_rank), .r_gid(r_gid), .r_pair(r_pair), .r_data(r_data),
        .held(held), .o_n(c_n), .o_take(c_take), .o_rank(c_rank), .o_row(c_rows),
        .done(a_done), .fault(a_fault), .fault_code(a_fc));
    ot_s81_svcq_selfetch #(.DIE_ID(DIE_ID), .ST(ST), .P(P), .S(S), .HAW(HAW), .SRAM_MACRO(SRAM_MACRO)) u_fetch (
        .clk(clk), .rst_n(rst_n), .job_v(go), .published_source_count(npub),
        .region_base_sector(rbase), .region_sector_count(rcount),
        .id_count(own_count), .id_done(own_done), .id_idx(own_idx), .id_rank_in(own_rank), .id_gid(own_gid),
        .o_v(f_ov), .o_ready(f_or), .o_rank(f_rank), .o_gid(f_gid), .o_row(f_row),
        .run(f_run), .done(f_done), .fault(f_fault), .fault_code(f_fc),
        .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_tag(m_tag),
        .s_v(s_v), .s_tag(s_tag), .s_beat(s_beat), .s_data(s_data));

    // ---------------- merger ----------------
    wire kv_v, kv_ready; wire [3:0] kv_m; wire [NL*ROWW-1:0] kv_w;
    wire m_jready, m_done, m_fault; wire [1:0] m_fc;
    ot_chip_v41x_ckv_stream_merge u_mrg (
        .clk(clk), .rst_n(rst_n), .job_v(go), .job_ready(m_jready),
        .window_count(wcount), .n_sel(nsel),
        .w_v(w_v), .w_ready(w_ready), .w_m(w_m), .w_rows(w_rows),
        .c_n(c_n), .c_take(c_take), .c_rank(c_rank), .c_rows(c_rows),
        .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w),
        .done(m_done), .fault(m_fault), .fault_code(m_fc));
    assign kv_beat = kv_v && kv_ready;

    // ---------------- q store (16 heads) ----------------
    reg [D*16-1:0] qmem [0:H-1];
    reg [4:0] q_have, q_rd;            // heads complete / heads handed to the engine
    always @(posedge clk) if (pay_mine && f_type == 4'd1)
        qmem[{f_hdr[448], f_idx[6:4]}][512*f_idx[3:0] +: 512] <= q_d;
    wire eq_v = q_rd < q_have;
    wire eq_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin q_have <= 0; q_rd <= 0; end
        else if (go) begin q_have <= 0; q_rd <= 0; end
        else begin
            // heads complete in order: half 0 heads 0..7, then half 1 heads 8..15
            if (pay_mine && f_type == 4'd1 && f_idx[3:0] == 4'hf) q_have <= q_have + 1'b1;
            if (eq_v && eq_ready) q_rd <= q_rd + 1'b1;
        end
    end

    // ---------------- p FIFO ----------------
    reg [TD*16-1:0] pmem [0:PFIFO-1];
    reg [PFW:0] pw, pr;
    wire [PFW:0] pcnt = pw - pr;
    reg [15:0] p_left;                 // p words of the job not yet handed to the engine
    always @(posedge clk) if (pay_mine && f_type == 4'd5) pmem[pw[PFW-1:0]] <= q_d;
    wire [1:0] pstep = (p_left >= 16'd2) ? 2'd2 : 2'(p_left);
    wire ep_v = job_active && p_left != 0 && pcnt >= (PFW+1)'(pstep);
    wire ep_ready;
    wire [2*TD*16-1:0] ep_w = {(pstep == 2'd2) ? pmem[pr[PFW-1:0] + 1'b1] : {TD*16{1'b1}}, pmem[pr[PFW-1:0]]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pw <= 0; pr <= 0; p_left <= 0; end
        else begin
            if (pay_mine && f_type == 4'd5) pw <= pw + 1'b1;
            if (go) p_left <= (tjob + 16'(R) - 1) / 16'(R);
            else if (ep_v && ep_ready) begin pr <= pr + (PFW+1)'(pstep); p_left <= p_left - 16'(pstep); end
        end
    end

    // ---------------- engine ----------------
    reg ej_pend;
    wire ej_ready;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ej_pend <= 0; else if (go) ej_pend <= 1'b1; else if (ej_ready) ej_pend <= 1'b0;
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    reg sc_cr, pv_cr;
    generate if (ENGINE != 0) begin : g_eng
        // Engine configuration: the closing 1.2 GHz configuration by default.  SVCQ_ENG_FG3 selects the as-built
        // latencies (FPL 3 / FML 3, tile _l: results/rtl/hbm_accel_fmax_inventory_20261004/attn/full_geometry_fpl3_ilv1),
        // the only full-geometry (D512) configuration whose Verilator model fits a 50 GB build; values are identical
        // (latency parameters only: the closing configuration is lockstep-verified against it by the attention
        // owners' gates, gates/verify6_final.json + equiv_*.json), cycles differ.
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
            .qk_iss(qk_iss), .pv_iss(pv_iss));
    end else begin : g_noeng
        assign ej_ready = 1'b1; assign eq_ready = 1'b1; assign kv_ready = 1'b1; assign ep_ready = 1'b1;
        assign sc_v = 0; assign sc_row = 0; assign sc_m = 0; assign sc_y = 0; assign sc_f = 0;
        assign pv_v = 0; assign pv_c = 0; assign pv_y = 0; assign pv_f = 0; assign qk_iss = 0; assign pv_iss = 0;
    end endgenerate

    // ---------------- score beats: held filter, FIFO of SC_CRED beats ----------------
    localparam integer SCB = 16 + 4 + NL*H*32 + NL*H;
    reg [SCB-1:0] scq [0:SC_CRED-1];
    reg [$clog2(SC_CRED):0] scw, scr;
    reg [3:0] hm;
    integer l;
    always @(*) begin
        hm = 0;
        for (l = 0; l < NL; l = l + 1) begin
            if (32'(sc_row) + l < 32'(wcount)) hm[l] = sc_m[l] && ((32'(sc_row) + l) % 4 == ST);
            else hm[l] = sc_m[l] && held[KW'(32'(sc_row) + l - 32'(wcount))];
        end
    end
    always @(posedge clk) if (sc_v) scq[scw[$clog2(SC_CRED)-1:0]] <= {sc_row, hm, sc_y, sc_f};
    // ---------------- p.v beats: the owned dims, FIFO of PV_CRED beats ----------------
    localparam integer PVB = 8 + 16*H*32 + 16*H;
    reg [PVB-1:0] pvq [0:PV_CRED-1];
    reg [$clog2(PV_CRED):0] pvw, pvr;
    always @(posedge clk) if (pv_v)
        pvq[pvw[$clog2(PV_CRED)-1:0]] <= {pv_c, pv_y[16*ST*H*32 +: 16*H*32], pv_f[16*ST*H +: 16*H]};

    // ---------------- od export FIFO (fetched rows) ----------------
    localparam integer XQ = 8;
    reg [KW+POS_W+2304-1:0] xq [0:XQ-1];
    reg [3:0] xw, xr;
    assign f_or = (xw - xr) < 4'(XQ);
    always @(posedge clk) if (f_ov && f_or) xq[xw[2:0]] <= {f_rank, f_gid, f_row};

    // ---------------- result emitters ----------------
    wire [3:0] sv_n = 4'(scw - scr);
    wire [3:0] pv_n = 4'(pvw - pvr);
    reg [SCB-1:0] sb; reg [PVB-1:0] pb;
    reg [2:0] a_state;                 // 0 idle, 1 score words, 2 pv words
    reg [4:0] a_i;
    reg [3:0] a_mask;
    reg [3:0] pv_frames;               // pv frames emitted this job
    reg x_busy; reg [3:0] x_i; reg [KW+POS_W+2304-1:0] xb;
    wire live = !fault;
    function automatic [511:0] hdr(input [3:0] typ, input endb, input [11:0] len, input [448:0] spec);
        hdr = {typ, endb, 4'd0, tagj, 3'd0, len, posj, userj, spec};
    endfunction
    function automatic integer pop4(input [3:0] m);
        pop4 = m[0] + m[1] + m[2] + m[3];
    endfunction
    integer b, nh;
    reg [448:0] sp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a0_v <= 0; od_v <= 0; a_state <= 0; a_i <= 0; scw <= 0; scr <= 0; pvw <= 0; pvr <= 0; sc_cr <= 0; pv_cr <= 0;
            xw <= 0; xr <= 0; x_busy <= 0; x_i <= 0; job_active <= 0; pv_frames <= 0; fc <= 0;
        end else begin
            sc_cr <= 1'b0; pv_cr <= 1'b0;
            if (sc_v) scw <= scw + 1'b1;
            if (pv_v) pvw <= pvw + 1'b1;
            if (f_ov && f_or) xw <= xw + 1'b1;
            if (go) begin job_active <= 1'b1; pv_frames <= 0; end
            // faults
            if (start && job_active) fc[0] <= 1'b1;
            if (start && (h_len != 0 || q_d[88:81] > 8'd128 || q_d[98:89] > 10'd512)) fc[1] <= 1'b1;
            if (hdr_mine && !(h_type inside {4'd1, 4'd2, 4'd3, 4'd4, 4'd5, 4'd6, 4'd7, 4'd12})) fc[2] <= 1'b1;
            if (hdr_mine && h_type == 4'd1 && h_len != 12'd128) fc[2] <= 1'b1;
            if (hdr_mine && (h_type inside {4'd1, 4'd5, 4'd6, 4'd7}) && !job_active) fc[3] <= 1'b1;
            if (pay_mine && f_type == 4'd5 && pcnt >= (PFW+1)'(PFIFO)) fc[4] <= 1'b1;
            if (hdr_mine && h_type == 4'd1 && (q_d[448] != q_have[3] || q_have[2:0] != 3'd0)) fc[5] <= 1'b1;
            if (sc_v && sv_n >= 4'(SC_CRED)) fc[6] <= 1'b1;
            if (pv_v && pv_n >= 4'(PV_CRED)) fc[6] <= 1'b1;
            if (a_fault) fc[7] <= 1'b1;
            if (f_fault) fc[8] <= 1'b1;
            if (m_fault) fc[9] <= 1'b1;
            // a0 emitter (frame-atomic)
            if (a0_v && a0_r) a0_v <= 1'b0;
            if (!a0_v || a0_r) begin
                case (a_state)
                    0: if (live && sv_n != 0) begin
                           sb = scq[scr[$clog2(SC_CRED)-1:0]];
                           a_mask <= sb[SCB-17 -: 4];
                           if (sb[SCB-17 -: 4] == 0) begin scr <= scr + 1'b1; sc_cr <= 1'b1; end
                           else begin
                               sp = 0; sp[448:447] = 2'd0; sp[446:431] = sb[SCB-1 -: 16]; sp[430:427] = sb[SCB-17 -: 4];
                               sp[63:0] = sb[NL*H-1:0];
                               a0_v <= 1'b1; a0_d <= hdr(4'd8, 1'b0, 12'(pop4(sb[SCB-17 -: 4])), sp);
                               a_state <= 1; a_i <= 0;
                           end
                       end else if (live && pv_n != 0 && (pv_frames != 4'd7 || (x_busy == 0 && xw == xr && f_done && sv_n == 0))) begin
                           pb = pvq[pvr[$clog2(PV_CRED)-1:0]];
                           sp = 0; sp[448:447] = 2'd1; sp[446:431] = 16'(pb[PVB-1 -: 8]); sp[255:0] = pb[16*H-1:0];
                           a0_v <= 1'b1; a0_d <= hdr(4'd8, pv_frames == 4'd7, 12'd16, sp);
                           a_state <= 2; a_i <= 0;
                       end
                    1: begin
                           sb = scq[scr[$clog2(SC_CRED)-1:0]];
                           // next held row of the beat
                           nh = -1;
                           for (b = NL - 1; b >= 0; b = b - 1) if (a_mask[b]) nh = b;
                           a0_v <= 1'b1; a0_d <= sb[16*H + nh*H*32 +: H*32];
                           a_mask[nh] <= 1'b0;
                           if (pop4(a_mask) == 1) begin a_state <= 0; scr <= scr + 1'b1; sc_cr <= 1'b1; end
                       end
                    2: begin
                           pb = pvq[pvr[$clog2(PV_CRED)-1:0]];
                           a0_v <= 1'b1; a0_d <= pb[16*H + a_i*H*32 +: H*32];
                           a_i <= a_i + 1'b1;
                           if (a_i == 5'd15) begin
                               a_state <= 0; pvr <= pvr + 1'b1; pv_cr <= 1'b1; pv_frames <= pv_frames + 1'b1;
                               if (pv_frames == 4'd7) job_active <= 1'b0;
                           end
                       end
                    default: a_state <= 0;
                endcase
            end
            // od emitter: one ROWX frame per fetched row
            if (od_v && od_r) od_v <= 1'b0;
            if (!od_v || od_r) begin
                if (!x_busy) begin
                    if (live && xw != xr) begin
                        xb = xq[xr[2:0]];
                        sp = 0; sp[9:0] = xb[KW+POS_W+2304-1 -: KW]; sp[30:10] = xb[POS_W+2304-1 -: POS_W];
                        od_v <= 1'b1; od_d <= hdr(4'd11, 1'b0, 12'd8, sp); x_busy <= 1'b1; x_i <= 0;
                    end
                end else begin
                    xb = xq[xr[2:0]];
                    od_v <= 1'b1;
                    od_d <= {190'd0, xb[2048 + 32*x_i +: 32], xb[256*x_i +: 256], x_i[2:0],
                             xb[POS_W+2304-1 -: POS_W], xb[KW+POS_W+2304-1 -: KW]};
                    x_i <= x_i + 1'b1;
                    if (x_i == 4'd7) begin x_busy <= 1'b0; xr <= xr + 1'b1; end
                end
            end
        end
    end
endmodule
