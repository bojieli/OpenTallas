`timescale 1ns/1ps
`default_nettype none
// FAN32 static IDX.TOPK (HBM-IDX6 2026-10-20). Same function, same edges as ot_hbm_idx_topk_static at RSPLIT 1 (every
// port identical every edge; bench tb_idx_rootctl_am_f32_eq + the g2d banklat set on FAN32 1). Why: the mandatory
// native32 census of the d4g IDX root g2d/g2df (claude/l2h-idx-g2d-1019 ad0dad443) FAILED 296 drivers > 32 loads,
// max 2,057, almost all in this engine. Each class and its structural fix (safe-design checklist items 3/4):
//   di[] 2,057 (the 8:1 x 256 b VM capture mux select)  -> one registered ONE-HOT bank select per 32-bit word
//        (8 kept copies x 8 b, loaded from the read pipeline one edge before di; each copy bit gates 32 AND inputs);
//   r_rb/o_rb 544/349 (the 8:1 word barrel rotate select) -> registered one-hot rotate per output word (8 kept
//        copies each for O and R, two stages after o_rb/r_rb, which settle >= 10 edges before E_PKO);
//   st[] decodes 560/381/96/74, tk_busy/go 205 (wide enables)  -> every wide enable is a kept registered copy of the
//        decode of the NEXT state (st is registered from one st_nx, so copy == decode every edge), <= 29 bits a copy:
//        descriptor (6 copies of go & !busy), row/sector registers, capture slots, lane clear/shift, cq payload;
//   pipeline registers whose enable never matters at their consumer (cm, rank->placement, O/R words, rotated sector,
//        write list, lane C stage) are FREE-RUNNING: their consumers sample them on the same edges as before and they
//        are stable then (operands change only at E_CHK / E_NEXT / E_SEL), so no enable net exists at all;
//   t1/t2 55/56 (tournament mux selects) -> two kept comparator copies per mux (ot_hbm_idx_kbetter), 27 b each;
//   lane c_b/c_v/ins_v/ed/ev 107-123 -> ot_hbm_idx_topk_lane_f32 (registered insert enables / selects, two kept
//        copies per entry, free-running C stage, shift as 17 kept copies per lane);
//   k_q/rk/fk/fz 33-66 (rank and placement) -> placement is a registered one-hot matrix (2 kept copies: ids /
//        values); the R value is formed at capture (fv) from the tournament winner, the sign half-split over a kept copy;
//   cap_d/cap_v/cap_first 40-56 -> XOR-form key (one invert net a word), kept copies of cap_v / cap_first.
// Added cycles: NONE (every copy is a look-ahead register on the edge its original decode used). Compiler schedule
// and latency ledger unchanged (TOPK go +1 / row +1 / writes +1 / done +1 of rootctl_am stay as they are).
// Storage: the sorted lists (8 x 8 x 53 b) and the 8 winners are a systolic sort network read at fixed positions, not
// runtime-indexed storage (checklist item 5: no address decode into a flop array; nothing to put in SRAM).
// Ports = ot_hbm_idx_topk_static + go_c (NGO kept copies of go made beside the caller's go pin register: same D, same
// reset). MUT as ot_hbm_idx_topk_static (1 ascending ranks by score, 2 ties high, 3 select skips lanes 3/7, 4 capture
// one edge early, 5 second split O sector not written, 6 write acknowledgement one edge early).
module ot_hbm_idx_topk_lane_f32 #(
    parameter integer IDW = 20,
    parameter integer TIEHI = 0
) (
    input  wire            clk,
    input  wire            rn,
    input  wire            clr,
    input  wire [32:0]     sh_c,         // kept copies of the shift: entry e quarter q = 4e+q, ev = 32
    input  wire            ins_v,
    input  wire [31:0]     ins_key,
    input  wire            ins_nz,
    input  wire [IDW-1:0]  ins_id,
    output wire [IDW+33:0] head
);
    localparam integer EW = IDW + 34, DW = EW - 1;
    // entry bit quarters (each mapped mux bit loads its controls ~2x): [0,12) [12,26) [26,40) [40,DW)
    reg [7:0] ev; reg [DW-1:0] ed [0:7];
    reg [DW-1:0] c_d;                                          // free-running C-stage word (used only with an insert)
    always @(posedge clk) c_d <= {ins_key, ins_nz, ins_id};
    reg [7:0] beats;
    integer i;
    always @* for (i = 0; i < 8; i = i + 1)
        beats[i] = !ev[i] || ins_key > ed[i][IDW+32:IDW+1] || (TIEHI != 0 && ins_key == ed[i][IDW+32:IDW+1]);
    // insert enable ie = (registered ins_v && !clr) && (registered beats) of the closed lane; sel = beats[i-1].
    // Reset-free kept copies: their D is 0 while the lane is held in reset (ins_v = s1_v is reset), one edge settles them.
    wire [7:0] ie_d = {8{ins_v && !clr}} & beats;
    wire [7:0] ie [0:3]; wire [6:0] sl [0:3];
    genvar e, q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_c
        ot_hbm_idx_kreg #(.W(8)) u_ie (.clk(clk), .rst_n(rn), .d(ie_d), .q(ie[q]));
        ot_hbm_idx_kreg #(.W(7)) u_sl (.clk(clk), .rst_n(rn), .d(beats[6:0]), .q(sl[q]));
    end endgenerate
    wire [7:0] ie0 = ie[0]; wire [6:0] sl0 = sl[0];
    assign head = {ev[0], ed[0]};
    always @(posedge clk or negedge rn)
        if (!rn) ev <= 8'd0;
        else if (clr) ev <= 8'd0;
        else if (sh_c[32]) ev <= {1'b0, ev[7:1]};
        else for (i = 0; i < 8; i = i + 1) if (ie0[i]) ev[i] <= (i != 0 && sl0[i == 0 ? 0 : i - 1]) ? ev[i == 0 ? 0 : i - 1] : 1'b1;
    generate for (e = 0; e < 8; e = e + 1) begin : g_e
        for (q = 0; q < 4; q = q + 1) begin : g_q
            localparam integer LO = (q == 0) ? 0 : (q == 1) ? 12 : (q == 2) ? 26 : 40;
            localparam integer HI = (q == 0) ? 12 : (q == 1) ? 26 : (q == 2) ? 40 : DW;
            always @(posedge clk) begin
                if (sh_c[4*e+q]) begin if (e < 7) ed[e][HI-1:LO] <= ed[(e < 7) ? e + 1 : e][HI-1:LO]; end
                else if (ie[q][e]) ed[e][HI-1:LO] <= (e != 0 && sl[q][(e == 0) ? 0 : e - 1]) ? ed[(e == 0) ? 0 : e - 1][HI-1:LO] : c_d[HI-1:LO];
            end
        end
    end endgenerate
endmodule


module ot_hbm_idx_topk_static_f32 #(
    parameter integer MUT = 0,
    parameter integer IDW = 20,
    parameter integer PIN_IN = 0,
    parameter integer ACK = 12 + PIN_IN,
    parameter integer RT_EXTRA = 0,
    parameter integer NGO = 12           // kept go copies = descriptor enable groups of DG bits
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    sid,
    input  wire          go,
    input  wire [NGO-1:0] go_c,
    input  wire [3:0]    k,
    input  wire          order,
    input  wire [19:0]   n,
    input  wire [19:0]   m,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   a_str,
    input  wire          o_mirror,
    input  wire [17:0]   o_base,
    input  wire [17:0]   o_str,
    input  wire          has_r,
    input  wire [17:0]   r_base,
    input  wire [17:0]   r_str,
    output reg  [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output reg  [337:0]  cq,
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output reg           busy,
    output reg           done,
    output reg           fault
);
    localparam integer EW = IDW + 34;
    localparam [4:0] E_IDLE=0, E_CHK=1, E_ROW=2, E_RD=3, E_DR=4, E_FL1=5, E_FL2=6, E_FL3=7, E_SEL=8, E_RK1=9,
                     E_RK2=10, E_PK1=11, E_PKO=12, E_WR=13, E_NEXT=14, E_END=15;
    localparam integer XRT = PIN_IN + RT_EXTRA;
    localparam integer CW = (8 + PIN_IN + RT_EXTRA < 16 && ACK - 1 < 16) ? 4 : 8;
    // descriptor: 157 bits + kept duplicates of k (2 x 4) and order (2), each duplicate in a DIFFERENT enable group than
    // its original (a flop with the same D and the same enable net would be merged back): DSW 167 in NGO groups of DG 14
    localparam integer DSW = 167, DG = 14;
    integer l, a, b;
    genvar g, c;
    // reset-free kept copies (ot_hbm_idx_kreg RST 0): every copy's D is a function of reset-held state while rst_n is
    // low, so one clock edge inside reset settles it (the die reset is landed: 2 registered stages, clock running);
    // only copies the kit reset splitter cannot see (inside keep_hierarchy) are reset-free, the originals keep resets.
    // ------------------------------------------------------------ descriptor
    wire legal = k >= 4'd1 && k <= 4'd8 && n >= {16'd0, k} && m != 20'd0 &&
                 (a_mirror ? a_base[17:16] == 2'd0 : a_base[17:16] == sid) &&
                 !o_mirror && o_base[17:16] == sid && (!has_r || r_base[17:16] == sid);
    wire [DSW-1:0] dsc_in = {legal, k, order, has_r, a_mirror, o_mirror, n, m, a_base, a_str, o_base, o_str, r_base,
                             k, r_str[17:9], order, r_str[8:0], k, order};
    reg  [DSW-1:0] dsc;
    wire [NGO-1:0] busy_c;
    wire [NGO-1:0] den = go_c & ~busy_c;
    generate for (g = 0; g < DSW; g = g + 1) begin : g_dsc
        always @(posedge clk) if (den[g / DG]) dsc[g] <= dsc_in[g];
    end endgenerate
    wire legal_q; wire [3:0] k_q, k_d, k_m; wire order_q, order_d1, order_d2, has_r_q, am_q, om_q; wire [19:0] n_q, m_q;
    wire [17:0] a_base_q, a_str_q, o_base_q, o_str_q, r_base_q, r_str_q;
    assign {legal_q, k_q, order_q, has_r_q, am_q, om_q, n_q, m_q, a_base_q, a_str_q, o_base_q, o_str_q, r_base_q,
            k_m, r_str_q[17:9], order_d2, r_str_q[8:0], k_d, order_d1} = dsc;
    // ------------------------------------------------------------ sequencer state (st registered from st_nx)
    reg [4:0] st, st_nx; reg [CW-1:0] cnt; reg flt, f_nan, s_inv;
    reg [19:0] c_row; reg [17:0] c_rb, c_le, o_rb, r_rb; reg [2:0] ol3, rl3;
    reg [14:0] i_sec, i_left; reg i_tgl, i_first;
    reg i_tgl_nx, busy_nx;
    reg [1:0] s_ph; reg [3:0] s_cnt;
    reg [2:0] nw, wi; reg [3:0] woh;
    reg [EW-1:0] t1 [0:3]; reg [3:0] t1_s; reg [EW-1:0] t2 [0:1]; reg [3:0] t2_l; reg [EW-1:0] t3; reg [2:0] t3_l;
    wire rd_now;
    wire [11:0] di;
    wire rd_last = rd_now && i_left == 15'd0;
    wire last_row = c_row + 20'd1 == m_q;
    always @* begin
        st_nx = st; busy_nx = busy; i_tgl_nx = i_tgl;
        case (st)
            E_IDLE: if (go) begin st_nx = E_CHK; busy_nx = 1'b1; end
            E_CHK:  if (!legal_q) begin st_nx = E_IDLE; busy_nx = 1'b0; end else st_nx = E_ROW;
            E_ROW:  begin st_nx = E_RD; i_tgl_nx = 1'b0; end
            E_RD:   begin i_tgl_nx = !i_tgl; if (rd_now && rd_last) st_nx = E_DR; end
            E_DR:   if (cnt == CW'(0)) st_nx = E_FL1;
            E_FL1:  st_nx = E_FL2;
            E_FL2:  st_nx = E_FL3;
            E_FL3:  st_nx = E_SEL;
            E_SEL:  if (s_ph == 2'd3 && s_cnt + 4'd1 == k_q) st_nx = E_RK1;
            E_RK1:  st_nx = E_RK2;
            E_RK2:  st_nx = E_PK1;
            E_PK1:  st_nx = E_PKO;
            E_PKO:  st_nx = E_WR;
            E_WR:   if (wi + 3'd1 == nw) st_nx = E_NEXT;
            E_NEXT: st_nx = last_row ? E_END : E_ROW;
            E_END:  if (cnt == CW'(0)) begin st_nx = E_IDLE; busy_nx = 1'b0; end
            default: st_nx = E_IDLE;
        endcase
    end
    // ------------------------------------------------------------ kept registered copies of the wide decodes
    localparam integer NWR = (337 + 13) / 14;            // cq payload enable groups of <= 14 bits
    wire [11:0] chk_c, upd_c; wire [3:0] row_c; wire [3:0] rdn_c; wire [7:0] lclr_c; wire [NWR-1:0] wr_c;
    generate
        for (c = 0; c < NGO; c = c + 1) begin : g_busy
            ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(busy_nx), .q(busy_c[c]));
        end
        for (c = 0; c < 12; c = c + 1) begin : g_chk
            ot_hbm_idx_kreg #(.W(2)) u (.clk(clk), .rst_n(rst_n),
                .d({st_nx == E_NEXT && !last_row, st_nx == E_CHK}), .q({upd_c[c], chk_c[c]}));
        end
        for (c = 0; c < 4; c = c + 1) begin : g_row      // [2]/[3]: i_left halves (census v5: one copy 35)
            ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(st_nx == E_ROW), .q(row_c[c]));
        end
        for (c = 0; c < 4; c = c + 1) begin : g_rdn
            ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(st_nx == E_RD && !i_tgl_nx), .q(rdn_c[c]));
        end
        for (c = 0; c < 8; c = c + 1) begin : g_lclr
            ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(st_nx == E_RK1 || st_nx == E_CHK), .q(lclr_c[c]));
        end
        for (c = 0; c < NWR; c = c + 1) begin : g_wr
            ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(st_nx == E_WR), .q(wr_c[c]));
        end
    endgenerate
    assign rd_now = rdn_c[3];
    // ------------------------------------------------------------ row / sector registers (no reset; RSPLIT form), halves
    always @(posedge clk) begin
        if (chk_c[0]) c_row[9:0] <= 10'd0; else if (upd_c[0]) c_row[9:0] <= c_row[9:0] + 10'd1;
        if (chk_c[1]) c_row[19:10] <= 10'd0; else if (upd_c[1]) c_row[19:10] <= c_row[19:10] + {9'd0, &c_row[9:0]};
        if (chk_c[2]) c_rb[8:0] <= a_base_q[8:0]; else if (upd_c[2]) c_rb[8:0] <= c_rb[8:0] + a_str_q[8:0];
        if (chk_c[3]) c_rb[17:9] <= a_base_q[17:9]; else if (upd_c[3]) c_rb[17:9] <= c_rb_n[17:9];
        if (chk_c[4]) c_le[8:0] <= le0[8:0]; else if (upd_c[4]) c_le[8:0] <= c_le[8:0] + a_str_q[8:0];
        if (chk_c[5]) c_le[17:9] <= le0[17:9]; else if (upd_c[5]) c_le[17:9] <= c_le_n[17:9];
        if (chk_c[6]) o_rb[8:0] <= o_base_q[8:0]; else if (upd_c[6]) o_rb[8:0] <= o_rb[8:0] + o_str_q[8:0];
        if (chk_c[7]) o_rb[17:9] <= o_base_q[17:9]; else if (upd_c[7]) o_rb[17:9] <= o_rb_n[17:9];
        if (chk_c[8]) r_rb[8:0] <= r_base_q[8:0]; else if (upd_c[8]) r_rb[8:0] <= r_rb[8:0] + r_str_q[8:0];
        if (chk_c[9]) r_rb[17:9] <= r_base_q[17:9]; else if (upd_c[9]) r_rb[17:9] <= r_rb_n[17:9];
        if (chk_c[10]) ol3 <= o_base_q[2:0]; else if (upd_c[10]) ol3 <= ol3 + o_str_q[2:0];     // kept low-bit copies
        if (chk_c[11]) rl3 <= r_base_q[2:0]; else if (upd_c[11]) rl3 <= rl3 + r_str_q[2:0];     // (rotate decode)
        if (row_c[0]) begin i_sec[7:0] <= c_rb[10:3]; i_first <= 1'b1; end
        else if (rdn_c[0]) begin i_sec[7:0] <= i_sec[7:0] + 8'd1; i_first <= 1'b0; end
        if (row_c[1]) i_sec[14:8] <= c_rb[17:11]; else if (rdn_c[1]) i_sec[14:8] <= i_sec[14:8] + {6'd0, &i_sec[7:0]};
        if (row_c[2]) i_left[7:0] <= i_lt0[7:0]; else if (rdn_c[2]) i_left[7:0] <= i_ldec[7:0];
        if (row_c[3]) i_left[14:8] <= i_lt0[14:8]; else if (rdn_c[2]) i_left[14:8] <= i_ldec[14:8];
    end
    wire [17:0] c_rb_n = c_rb + a_str_q, c_le_n = c_le + a_str_q, o_rb_n = o_rb + o_str_q, r_rb_n = r_rb + r_str_q;
    wire [17:0] le0 = a_base_q + n_q[17:0] - 18'd1;
    wire [14:0] i_lt0 = c_le[17:3] - c_rb[17:3], i_ldec = i_left - 15'd1;
    // ------------------------------------------------------------ fixed read pipeline (as ot_hbm_idx_topk_static)
    localparam integer TAP = ((MUT == 4) ? 6 : 7) + XRT;
    reg [11:0] dp [0:8+XRT];
    assign di = dp[TAP];
    reg cap_v, cap_first, cap_last; reg [2:0] cap_off, cap_lastw; reg [255:0] cap_d;
    wire [2:0] i_off = i_first ? c_rb[2:0] : 3'd0;
    wire [2:0] i_lw  = c_le[2:0];
    wire rsid_bad = !am_q && i_sec[14:13] != sid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vm_rq <= 136'd0; cap_v <= 1'b0;
            for (integer d = 0; d < 9 + XRT; d = d + 1) dp[d] <= 12'd0;
        end else begin
            vm_rq <= 136'd0;
            for (integer d = 1; d < 9 + XRT; d = d + 1) dp[d] <= dp[d-1];
            dp[0] <= 12'd0;
            if (rd_now && !rsid_bad) begin
                vm_rq[17*i_sec[2:0] +: 17] <= {1'b1, am_q, i_sec};
                dp[0] <= {1'b1, i_sec[2:0], i_first, rd_last, i_off, i_lw};
            end
            cap_v <= di[11];
        end
    end
    // capture: one-hot bank select per 32-bit word (copy w gates word w of all 8 banks), loaded from dp[TAP-1]
    wire [7:0] csel [0:7];
    wire [7:0] cs_d = 8'd1 << dp[TAP-1][10:8];
    wire [3:0] cv_c; wire [6:0] cf_c;   // cf_c: 7-bit col_now / col_nowb select slices (census v5: 36 / 48)
    generate
        for (c = 0; c < 8; c = c + 1) begin : g_cs
            ot_hbm_idx_kreg #(.W(8)) u (.clk(clk), .rst_n(rst_n), .d(cs_d), .q(csel[c]));
        end
        for (c = 0; c < 4; c = c + 1) begin : g_cv
            ot_hbm_idx_kreg #(.W(1)) uv (.clk(clk), .rst_n(rst_n), .d(di[11]), .q(cv_c[c]));
        end
        for (c = 0; c < 7; c = c + 1) begin : g_cf
            ot_hbm_idx_kreg #(.W(1)) uf (.clk(clk), .rst_n(rst_n), .d(di[7]), .q(cf_c[c]));
        end
        for (g = 0; g < 8; g = g + 1) begin : g_cap
            reg [31:0] wv;
            always @* begin
                wv = 32'd0;
                for (integer bk = 0; bk < 8; bk = bk + 1) wv = wv | ({32{csel[g][bk]}} & vm_rr[257*bk + 32*g +: 32]);
            end
            always @(posedge clk) cap_d[32*g +: 32] <= wv;
        end
    endgenerate
    always @(posedge clk) {cap_first, cap_last, cap_off, cap_lastw} <= di[7:0];
    reg rd_bad;
    always @* begin
        rd_bad = 1'b0;
        for (l = 0; l < 8; l = l + 1)
            if (vm_rr[257*l+256] != (di[11] && di[10:8] == 3'(l))) rd_bad = 1'b1;
    end
    // ------------------------------------------------------------ S1 feed (XOR-form key: one invert net a word)
    reg [IDW:0] col0;
    wire [IDW:0] cneg = {(IDW+1){1'b0}} - {{(IDW-2){1'b0}}, cap_off};
    wire [IDW:0] col_now = {cf_c[1] ? cneg[IDW:14] : col0[IDW:14], cf_c[4] ? cneg[13:7] : col0[13:7],
                            cf_c[0] ? cneg[6:0] : col0[6:0]};
    wire [IDW:0] col_nowb = {cf_c[5] ? cneg[IDW:14] : col0[IDW:14], cf_c[6] ? cneg[13:7] : col0[13:7],
                             cf_c[3] ? cneg[6:0] : col0[6:0]};    // second copy: the id adders of lanes 4..7
    reg [7:0] s1_v; reg [31:0] s1_key [0:7]; reg [7:0] s1_nz; reg [IDW-1:0] s1_id [0:7]; reg s1_nan;
    reg [7:0] f_v; reg [31:0] f_w [0:7]; reg [7:0] f_isnan; reg [IDW:0] f_idx [0:7];
    reg [7:0] f_sg, f_z;
    always @* for (l = 0; l < 8; l = l + 1) begin
        f_w[l] = cap_d[32*l +: 32];
        f_v[l] = cv_c[2] && (!cf_c[2] || l[2:0] >= cap_off) && (!cap_last || l[2:0] <= cap_lastw);
        f_isnan[l] = f_w[l][30:23] == 8'hff && f_w[l][22:0] != 23'd0;
        f_idx[l] = ((l < 4) ? col_now : col_nowb) + {{(IDW-2){1'b0}}, l[2:0]};
        f_sg[l] = f_w[l][31];
        f_z[l] = f_w[l][30:0] == 31'd0;
    end
    always @(posedge clk) begin
        if (cv_c[0]) col0[10:0] <= col_now[10:0] + 11'd8;
        if (cv_c[1]) col0[IDW:11] <= col_now[IDW:11] + {{(IDW-11){1'b0}}, &col_now[10:3]};
        for (l = 0; l < 8; l = l + 1) begin
            s1_key[l] <= {!f_sg[l] || f_z[l], f_w[l][30:0] ^ {31{f_sg[l] && !f_z[l]}}};
            s1_nz[l]  <= f_sg[l] && f_z[l];
            s1_id[l]  <= f_idx[l][IDW-1:0];
        end
    end
    // ------------------------------------------------------------ lanes
    wire [EW-1:0] lh [0:7];
    wire [7:0] shk [0:32];
    generate for (g = 0; g < 8; g = g + 1) begin : g_lane
        wire [32:0] sh_l;
        for (c = 0; c < 33; c = c + 1) begin : g_shl
            assign sh_l[c] = shk[c][g];
        end
        ot_hbm_idx_topk_lane_f32 #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u_l (.clk(clk), .rn(rst_n), .clr(lclr_c[g]),
            .sh_c(sh_l), .ins_v(s1_v[g]), .ins_key(s1_key[g]), .ins_nz(s1_nz[g]), .ins_id(s1_id[g]), .head(lh[g]));
    end endgenerate
    // ------------------------------------------------------------ tournament: four kept comparator copies per mux
    reg [EW-1:0] hx [0:7];
    always @* for (l = 0; l < 8; l = l + 1) hx[l] = (MUT == 3 && (l % 4) == 3) ? {EW{1'b0}} : lh[l];
    // mux quarters [0,14) [14,27) [27,41) [41,EW); comparator copy q selects quarter q (copy 3 also the lane index)
    function automatic [EW-1:0] qmux(input [3:0] bq, input [EW-1:0] x, input [EW-1:0] y);
        qmux = {bq[3] ? x[EW-1:41] : y[EW-1:41], bq[2] ? x[40:27] : y[40:27], bq[1] ? x[26:14] : y[26:14],
                bq[0] ? x[13:0] : y[13:0]};
    endfunction
    wire [15:0] b1f; wire [7:0] b2f; wire [3:0] b3; wire b3c;
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_t1
            for (c = 0; c < 4; c = c + 1) begin : g_c
                ot_hbm_idx_kbetter #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u (.x(hx[2*g]), .y(hx[2*g+1]), .b(b1f[4*g+c]));
            end
        end
        for (g = 0; g < 2; g = g + 1) begin : g_t2
            for (c = 0; c < 4; c = c + 1) begin : g_c
                ot_hbm_idx_kbetter #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u (.x(t1[2*g]), .y(t1[2*g+1]), .b(b2f[4*g+c]));
            end
        end
        for (c = 0; c < 4; c = c + 1) begin : g_t3
            ot_hbm_idx_kbetter #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u (.x(t2[0]), .y(t2[1]), .b(b3[c]));
        end
    endgenerate
    ot_hbm_idx_kbetter #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u_b3c (.x(t2[0]), .y(t2[1]), .b(b3c));
    wire b3d;   // second look-ahead comparator: the 33 shift copies are fed from two distinct decode nets
    ot_hbm_idx_kbetter #(.IDW(IDW), .TIEHI(MUT == 2 ? 1 : 0)) u_b3d (.x(t2[0]), .y(t2[1]), .b(b3d));
    wire [EW-1:0] t3_nx = qmux(b3, t2[0], t2[1]);
    always @(posedge clk) begin
        for (l = 0; l < 4; l = l + 1) begin
            t1_s[l] <= !b1f[4*l+3];
            t1[l]   <= qmux(b1f[4*l +: 4], hx[2*l], hx[2*l+1]);
        end
        for (l = 0; l < 2; l = l + 1) begin
            t2_l[2*l +: 2] <= b2f[4*l+3] ? {1'b0, t1_s[2*l]} : {1'b1, t1_s[2*l+1]};
            t2[l]          <= qmux(b2f[4*l +: 4], t1[2*l], t1[2*l+1]);
        end
        t3_l <= b3[3] ? {1'b0, t2_l[1:0]} : {1'b1, t2_l[3:2]};
        t3   <= t3_nx;
    end
    // lane shift copies: registered at SEL phase 2 from the phase-3 winner look-ahead (= l_sh of the closed engine)
    wire t3v_nx = b3c ? t2[0][EW-1] : t2[1][EW-1];
    wire [2:0] t3l_nx = b3c ? {1'b0, t2_l[1:0]} : {1'b1, t2_l[3:2]};
    wire t3v_ny = b3d ? t2[0][EW-1] : t2[1][EW-1];
    wire [2:0] t3l_ny = b3d ? {1'b0, t2_l[1:0]} : {1'b1, t2_l[3:2]};
    wire sel2 = st == E_SEL && s_ph == 2'd2;
    wire [7:0] sh_d, sh_e;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_shd
            assign sh_d[g] = sel2 && t3v_nx && t3l_nx == g[2:0];
            assign sh_e[g] = sel2 && t3v_ny && t3l_ny == g[2:0];
        end
        for (c = 0; c < 33; c = c + 1) begin : g_shk
            ot_hbm_idx_kreg #(.W(8)) u (.clk(clk), .rst_n(rst_n), .d((c < 17) ? sh_d : sh_e), .q(shk[c]));
        end
    endgenerate
    // ------------------------------------------------------------ winner capture (slot copies), R value at capture
    wire [7:0] cpe [0:5];                           // 0/1: fi halves, 2..5: fv quarters
    wire [7:0] cpe_d = {8{sel2}} & (8'd1 << s_cnt[2:0]);
    generate for (c = 0; c < 6; c = c + 1) begin : g_cpe
        ot_hbm_idx_kreg #(.W(8)) u (.clk(clk), .rst_n(rst_n), .d(cpe_d), .q(cpe[c]));
    end endgenerate
    wire k31c;
    ot_hbm_idx_kreg #(.W(1)) u_k31 (.clk(clk), .rst_n(rst_n), .d(t3_nx[IDW+32]), .q(k31c));
    wire [31:0] rv = {t3[IDW] || !t3[IDW+32], t3[IDW+31:IDW+17] ^ {15{!k31c}}, t3[IDW+16:IDW+1] ^ {16{!t3[IDW+32]}}};
    reg [31:0] fv [0:7]; reg [IDW-1:0] fi [0:7]; reg [31:0] fk [0:7];
    always @(posedge clk)
        for (l = 0; l < 8; l = l + 1) begin
            if (cpe[0][l]) fi[l][9:0] <= t3[9:0];
            if (cpe[1][l]) fi[l][IDW-1:10] <= t3[IDW-1:10];
            if (cpe[2][l]) fv[l][7:0] <= rv[7:0];
            if (cpe[3][l]) fv[l][15:8] <= rv[15:8];
            if (cpe[4][l]) fv[l][23:16] <= rv[23:16];
            if (cpe[5][l]) fv[l][31:24] <= rv[31:24];
            if (MUT == 1 && cpe[0][l]) fk[l] <= t3[IDW+32:IDW+1];
        end
    // ------------------------------------------------------------ rank and placement (free-running; one-hot matrix)
    wire [7:0] kgt;
    generate for (g = 0; g < 8; g = g + 1) begin : g_kgt
        assign kgt[g] = k_d > g[3:0];
    end endgenerate
    reg [7:0] cm [0:7]; reg [2:0] rk_c [0:7]; reg [63:0] pm_d; reg [2:0] rsl [0:7];
    always @* begin
        for (a = 0; a < 8; a = a + 1) begin
            rk_c[a] = 3'd0;
            for (b = 0; b < 8; b = b + 1) rk_c[a] = rk_c[a] + {2'd0, cm[a][b]};
        end
        for (b = 0; b < 8; b = b + 1)
            rsl[b] = ((b < 3) ? order_q : (b < 6) ? order_d1 : order_d2) ? rk_c[b] : 3'(b);
        for (a = 0; a < 8; a = a + 1)
            for (b = 0; b < 8; b = b + 1)
                pm_d[8*a+b] = kgt[b] && rsl[b] == 3'(a);
    end
    wire [63:0] pmi, pmv;
    ot_hbm_idx_kreg #(.W(64)) u_pmi (.clk(clk), .rst_n(rst_n), .d(pm_d), .q(pmi));
    ot_hbm_idx_kreg #(.W(64)) u_pmv (.clk(clk), .rst_n(rst_n), .d(pm_d), .q(pmv));
    reg [IDW-1:0] o_w [0:7]; reg [31:0] r_w [0:7];
    reg [IDW-1:0] pk_id [0:7]; reg [31:0] pk_val [0:7];
    always @* for (a = 0; a < 8; a = a + 1) begin
        pk_id[a] = {IDW{1'b0}}; pk_val[a] = 32'd0;
        for (b = 0; b < 8; b = b + 1) begin
            pk_id[a]  = pk_id[a]  | ({IDW{pmi[8*a+b]}} & fi[b]);
            pk_val[a] = pk_val[a] | ({32{pmv[8*a+b]}} & fv[b]);
        end
    end
    always @(posedge clk) begin
        for (a = 0; a < 8; a = a + 1)
            for (b = 0; b < 8; b = b + 1)
                cm[a][b] <= b != a && kgt[b] &&
                            ((MUT == 1) ? (fk[b] < fk[a] || (fk[b] == fk[a] && b > a)) : (fi[b] < fi[a]));
        for (a = 0; a < 8; a = a + 1) begin o_w[a] <= pk_id[a]; r_w[a] <= pk_val[a]; end
    end
    // ------------------------------------------------------------ static writer (free-running sector words, one-hot rotate)
    wire [7:0] kmask = 8'hff >> (4'd8 - k_m);      // the second kept k duplicate (k_d: kgt; k_q: sequencer only)
    wire [255:0] o_flat, r_flat;
    generate for (g = 0; g < 8; g = g + 1) begin : g_flat
        assign o_flat[g*32 +: 32] = {{(32-IDW){1'b0}}, o_w[g]};
        assign r_flat[g*32 +: 32] = r_w[g];
    end endgenerate
    reg [7:0] ooh, roh;
    always @(posedge clk) begin ooh <= 8'd1 << ol3; roh <= 8'd1 << rl3; end
    wire [7:0] osel [0:7]; wire [7:0] rsel [0:7];
    reg [255:0] w_o, w_r;
    generate for (g = 0; g < 8; g = g + 1) begin : g_rot
        wire [7:0] od, rd;
        for (c = 0; c < 8; c = c + 1) begin : g_s
            assign od[c] = ooh[(g - c + 8) % 8];
            assign rd[c] = roh[(g - c + 8) % 8];
        end
        ot_hbm_idx_kreg #(.W(8)) uo (.clk(clk), .rst_n(rst_n), .d(od), .q(osel[g]));
        ot_hbm_idx_kreg #(.W(8)) ur (.clk(clk), .rst_n(rst_n), .d(rd), .q(rsel[g]));
        reg [31:0] wo, wr;
        always @* begin
            wo = 32'd0; wr = 32'd0;
            for (integer s = 0; s < 8; s = s + 1) begin
                wo = wo | ({32{osel[g][s]}} & o_flat[32*s +: 32]);
                wr = wr | ({32{rsel[g][s]}} & r_flat[32*s +: 32]);
            end
        end
        always @(posedge clk) begin w_o[32*g +: 32] <= wo; w_r[32*g +: 32] <= wr; end
    end endgenerate
    // word masks: low byte from the kept low-bit copy, high byte from the register (halves the shift-select load)
    wire [15:0] o_wma = {8'd0, kmask} << ol3, o_wmb = {8'd0, kmask} << o_rb[2:0];
    wire [15:0] r_wma = {8'd0, kmask} << rl3, r_wmb = {8'd0, kmask} << r_rb[2:0];
    wire [15:0] o_wm = {o_wmb[15:8], o_wma[7:0]};
    wire [15:0] r_wm = {r_wmb[15:8], r_wma[7:0]};
    // O split flag: 5 kept registered copies (o_rb / k_q settle >= 10 edges before E_PKO; wl_* two edges after)
    wire [4:0] osp; reg rsp;
    generate for (c = 0; c < 5; c = c + 1) begin : g_osp
        ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(o_wm[15:8] != 8'd0), .q(osp[c]));
    end endgenerate
    reg [14:0] wl_sec [0:3]; reg [7:0] wl_wm [0:3]; reg [3:0] wl_isr;
    always @(posedge clk) begin
        rsp <= r_wm[15:8] != 8'd0;
        wl_sec[0] <= o_rb[17:3]; wl_wm[0] <= o_wm[7:0]; wl_isr[0] <= 1'b0;
        wl_sec[1] <= osp[0] ? o_rb[17:3] + 15'd1 : r_rb[17:3];
        wl_sec[2] <= osp[1] ? r_rb[17:3] : r_rb[17:3] + 15'd1;
        if (osp[2]) wl_sec[3] <= r_rb[17:3] + 15'd1;
        wl_wm[1] <= osp[3] ? o_wm[15:8] : r_wm[7:0];
        wl_wm[2] <= osp[3] ? r_wm[7:0] : r_wm[15:8];
        if (osp[4]) wl_wm[3] <= r_wm[15:8];
        wl_isr[1] <= !osp[4]; wl_isr[2] <= 1'b1;
        if (osp[4]) wl_isr[3] <= 1'b1;
        nw <= 3'd1 + (osp[4] ? 3'd1 : 3'd0) + (has_r_q ? 3'd1 + (rsp ? 3'd1 : 3'd0) : 3'd0);
    end
    function automatic [31:0] bmask(input [7:0] wm);
        for (integer w = 0; w < 8; w = w + 1) bmask[4*w +: 4] = {4{wm[w]}};
    endfunction
    // write-slot select: one-hot woh (= wi), data O/R select as 16 kept look-ahead copies (wl_isr of the next slot)
    reg [14:0] w_sec; reg [7:0] w_wm;
    always @* begin
        w_sec = 15'd0; w_wm = 8'd0;
        for (l = 0; l < 4; l = l + 1) begin
            w_sec = w_sec | ({15{woh[l]}} & wl_sec[l]);
            w_wm  = w_wm  | ({8{woh[l]}} & wl_wm[l]);
        end
    end
    wire [3:0] woh_n = {woh[2:0], 1'b0};
    wire wsel_d = (st == E_PKO) ? 1'b0 : |(woh_n & wl_isr);
    wire [15:0] wsel_c;
    generate for (c = 0; c < 16; c = c + 1) begin : g_wsel
        ot_hbm_idx_kreg #(.W(1)) u (.clk(clk), .rst_n(rst_n), .d(wsel_d), .q(wsel_c[c]));
    end endgenerate
    reg [255:0] wdata;
    always @* for (l = 0; l < 16; l = l + 1) wdata[16*l +: 16] = wsel_c[l] ? w_r[16*l +: 16] : w_o[16*l +: 16];
    wire wkill = flt || f_nan || s_inv || (MUT == 5 && wi == 3'd1 && nw == 3'd2);
    wire w_bad_sid = !om_q && w_sec[14:13] != sid;
    wire [336:0] cq_d = {1'b1, 11'd0, om_q, w_sec, 5'd0, wdata, (wkill || w_bad_sid) ? 32'd0 : bmask(w_wm), {14'h0244, wi[1:0]}};
    generate for (g = 0; g < 337; g = g + 1) begin : g_cq
        always @(posedge clk or negedge rst_n)
            if (!rst_n) cq[g] <= 1'b0;
            else if (wr_c[g / 14]) cq[g] <= cq_d[g];
    end endgenerate
    // ------------------------------------------------------------ write acknowledgement check (as built)
    reg [2:0] ap [0:ACK];
    reg cr_v; reg [15:0] cr_tag; reg cr_we;
    wire [2:0] ax = ap[(MUT == 6) ? ACK-2 : ACK-1];
    wire ack_bad = cr_v != ax[2] || (ax[2] && (cr_tag != {14'h0244, ax[1:0]} || !cr_we));
    reg wr_now;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cr_v <= 1'b0;
            for (integer d = 0; d <= ACK; d = d + 1) ap[d] <= 3'd0;
        end else begin
            cr_v <= cr[273];
            for (integer d = 1; d <= ACK; d = d + 1) ap[d] <= ap[d-1];
            ap[0] <= {wr_now, cq_seq};
        end
    always @(posedge clk) begin cr_tag <= cr[272:257]; cr_we <= cr[256]; end
    // ------------------------------------------------------------ control (narrow registers only)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= E_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; flt <= 1'b0; f_nan <= 1'b0; s_inv <= 1'b0;
            cq[337] <= 1'b0; cq_seq <= 2'd0; s1_v <= 8'd0; s1_nan <= 1'b0; wr_now <= 1'b0; wi <= 3'd0; woh <= 4'd0;
            cnt <= CW'(0); i_tgl <= 1'b0; s_ph <= 2'd0; s_cnt <= 4'd0;
        end else begin
            st <= st_nx; busy <= busy_nx; i_tgl <= i_tgl_nx;
            done <= 1'b0; fault <= 1'b0; cq[337] <= 1'b0; wr_now <= 1'b0;
            s1_v <= f_v; s1_nan <= |(f_v & f_isnan);
            if (s1_nan) f_nan <= 1'b1;
            if (busy && (rd_bad || ack_bad) && st != E_CHK) flt <= 1'b1;
            if (rd_now && rsid_bad) flt <= 1'b1;
            case (st)
                E_CHK: begin flt <= 1'b0; f_nan <= 1'b0; s_inv <= 1'b0; if (!legal_q) fault <= 1'b1; end
                E_RD: if (rd_now && rd_last) cnt <= CW'(8 + XRT);
                E_DR: if (cnt != CW'(0)) cnt <= cnt - CW'(1);
                E_FL3: begin s_ph <= 2'd0; s_cnt <= 4'd0; end
                E_SEL: begin
                    s_ph <= s_ph + 2'd1;
                    if (s_ph == 2'd3) begin
                        if (!t3[EW-1]) s_inv <= 1'b1;
                        s_cnt <= s_cnt + 4'd1;
                    end
                end
                E_PKO: begin wi <= 3'd0; woh <= 4'd1; end
                E_WR: begin
                    wr_now <= 1'b1; cq[337] <= 1'b1;
                    if (w_bad_sid) flt <= 1'b1;
                    cq_seq <= wi[1:0];
                    wi <= wi + 3'd1; woh <= woh_n;
                end
                E_NEXT: if (last_row) cnt <= CW'(ACK - 1);
                E_END: if (cnt == CW'(0)) begin
                    done <= !(flt || f_nan || s_inv || ack_bad); fault <= flt || f_nan || s_inv || ack_bad;
                end else cnt <= cnt - CW'(1);
                default: ;
            endcase
        end
    end
`ifndef SYNTHESIS
    // simulation-only: every kept copy equals the decode / register it replaces, every edge after reset release
    integer f32_copy_err = 0;
    reg [7:0] l_sh_ref; reg rst_q = 1'b0;
    always @(posedge clk) rst_q <= rst_n;
    always @* for (l = 0; l < 8; l = l + 1) l_sh_ref[l] = st == E_SEL && s_ph == 2'd3 && t3[EW-1] && t3_l == l[2:0];
    always @(negedge clk) if (rst_n && rst_q) begin : chk
        reg bad; bad = 1'b0;
        if (chk_c != {12{st == E_CHK}} || upd_c != {12{st == E_NEXT && !last_row}}) bad = 1'b1;
        if (row_c != {4{st == E_ROW}} || rdn_c != {4{st == E_RD && !i_tgl}} || wr_c != {NWR{st == E_WR}}) bad = 1'b1;
        if (lclr_c != {8{st == E_RK1 || st == E_CHK}} || busy_c != {NGO{busy}} || go_c != {NGO{go}}) bad = 1'b1;
        if (k_d !== k_q || k_m !== k_q || order_d1 !== order_q || order_d2 !== order_q) bad = 1'b1;
        if (busy && (ol3 !== o_rb[2:0] || rl3 !== r_rb[2:0])) bad = 1'b1;
        for (l = 0; l < 33; l = l + 1) if (shk[l] != l_sh_ref) bad = 1'b1;
        for (l = 0; l < 6; l = l + 1) if (cpe[l] != ({8{st == E_SEL && s_ph == 2'd3}} & (8'd1 << s_cnt[2:0]))) bad = 1'b1;
        for (l = 0; l < 8; l = l + 1) if (csel[l] != (8'd1 << di[10:8])) bad = 1'b1;
        if (cv_c != {4{cap_v}} || cf_c !== {7{cap_first}}) bad = 1'b1;
        if (st == E_WR && (woh != (4'd1 << wi[1:0]) || wsel_c != {16{wl_isr[wi[1:0]]}})) bad = 1'b1;
        if (bad) begin f32_copy_err = f32_copy_err + 1; if (f32_copy_err < 5) $display("F32_COPY_MISMATCH t=%0t st=%0d", $time, st); end
    end
`endif
endmodule
`default_nettype wire
