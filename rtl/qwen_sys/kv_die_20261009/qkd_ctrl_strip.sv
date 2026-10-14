`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B ROM TP8 die (track B: KV merged into the one die type), HBM controller strip qkd_ctrl / qkd_ctrl_n
// (el1013-qwen-kvstrips 2026-10-13, coordinator-accepted slot change): the 247.512 x 12,141.336 strip slot becomes
//   32 x qkd_ctrl_pc  (one hardened master, 246.24 x 172.8 beside its CDC, 378 um pitch: PC k at strip y = 378 k + 190.08)
//    1 x qkd_ctrl_kc  (the kc stream-command crossing, 64.8 x 43.2, N end of the strip, y = 12,096)
// and nothing else: the strip parent holds no logic and no routed wire longer than one abutment.
//
// qkd_ctrl_pc = ONE HBM3E pseudo-channel of the stack, HBM controller clock pll_hbm (1,024 ps), every block a closed
// or benched module, left byte-identical:
//   ot_qkvd_kcmd_tap        one station of the stream-command chain (ki -> ko, registered) + this PC's DESC / GO
//   ot_qwen_ctrl_pc_emb     the JEDEC stream scheduler behind its 8-credit command FIFO, with the static-row port
//                           (ot_hbm_r14_stream_pc_srow).  PC IDENTITY IS A STRAP: the scheduler is built for PC 0 and its
//                           reset is released dly(pc) cycles late (dly = RPH of ot_qwen_ctrl_pc_head: the refresh phase
//                           (pc * 118 / 32) rounded up to the PC's row-slot parity).  The scheduler's only uses of PC are
//                           the reset value of the refresh counter (RPH + PERIOD) and the row-slot parity, both of which
//                           are a pure time shift of the PC 0 machine, so the leaf is cycle-exact against
//                           ot_qwen_ctrl_pc_emb #(.PC(pc)) (bench: every command pin compared every cycle).
//   ot_qfd_emb_pcport KVW 2 read class (KV / embedding), embedding SECDED, the PHY write data (288 b, side-band encoded)
//   ot_qfd_kv_landing_ecc   SECDED of the KV return before the landing crossing
//   ot_qfd_emb_cdc          the embedding static port's core <-> HBM crossing (strip engine side on the core clock ck)
// New in this leaf (glue only):
//   * command arbiter: the tap's DESC / GO have priority; a KV write hand-off (CDC head h_wv / h_wsec) becomes
//     cmd 2 {column, bank} when its layer row (ROW0 + sec[16:11]) is the row of the LATEST descriptor sent to the
//     scheduler (command order = the row a queued write lands on), two of the 8 command credits stay reserved for the
//     tap.  A write of another layer is HELD (never written to a wrong row); held LATE cycles -> fault.
//   * write timing: h_wcon = the WR column (registered); the CDC returns the completion entry CVL edges after h_wcon at
//     its pin; the column the pcport sees is delayed CVL + 1 edges, so kw_v is exactly one edge after it (the pcport's
//     own check) and the PHY write data po.wd is valid CVL + 3 = 5 edges after the WR column on po.  The completion
//     sector is checked against the column (bank, column): fault on a mismatch.  Write-done h_av / h_atag WDONE edges
//     after the column (CWL + BL8 + response, the timed model's figure).
//   * read tags: the PHY returns data only, in RD order.  Every KV RD pushes {open row of the bank [7:0], j} (j = the
//     PC-local sector {bank[4:2], column, bank[1:0]}); the returned beat pops it:
//     h_lsec = {layer[5:0] = row - ROW0, j[9:7], 1'b0, j[6:0]} (= w_sec[16:0] of ot_qkvd_kv_wq: {layer, v, g, t[6],
//     t[13:9], t[5:3]}), h_lrow = row[7:0].
//   * registers at every pin: h_wv / h_wsec / h_cv / h_c* / h_fault, pi (PHY return), es (core clock), hrst / rsi are
//     captured by a flop with no logic in front; h_cred and the kc word are captured by the pin flops the closed
//     modules already own (read_credit_q, o_d); every output is a flop.
// Die ports (LSB first; tools/qwen_kv_die/kv_die.py CTRL_PC_BUS / BINDINGS):
//   W  ci[318:0] in  = CDC ho {h_cred 3, h_wv, h_wsec 24, h_cv, h_csec 24, h_cdata 256, h_ctag 9, h_fault}
//   W  co[293:0] out = CDC hi {h_lv, h_lsec 17, h_lrow 8, h_ldata 256, h_hand, h_wcon, h_av, h_atag 9}
//   W  es[287:0] in  (ck)  = {s_d 287 = {w_v, s_we, bank 5, col 5, row 19, w_d 256}, s_v}   strip engine static command
//   W  er[260:0] out (ck)  = {fault_core, s_credit, e_d 258 = {ue, ce, data 256}, e_v}
//   E  po[327:0] out = {wd 288, col_col 5, col_bank 5, col_we, col_v, row_row 19, row_bank 5, row_op 3, row_v}
//   E  pi[288:0] in  = {r_d 288, r_v}
//   N  ki[32:0] in / S ko[32:0] out   kc chain {d 32, v}, N -> S;   S fi in / N fo out  sticky fault chain, S -> N
//   pc[4:0] strap (die-top tie cells), pll_hbm (hclk), hrst (active low, hclk-synchronous, the same cycle at every
//   leaf: the row-slot TDM of a channel's two PCs counts from it), ck (core clock), rsi (core reset, active low).
// Contract: no command and no static word within 128 hclk of the hrst release (the strap delay; a command inside it
// faults); controller CRED 32 = the CDC landing depth; the PHY samples po.wd 5 edges after a WR column.
// MUT (bench mutants, never synthesized != 0): 1 strap delay + 1; 2 pcport MUT 4 (KV write check bit); 3 landing tag
// j low bits swapped; 4 write issued on a layer mismatch (guard off).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ctrl_pc #(
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = 17,          // write-done edges after the WR column (>= CVL + 4)
    parameter integer LATE  = 4096,        // a held (layer-mismatch) write faults after this many cycles
    parameter integer MUT   = 0
) (
    input  wire         pll_hbm,
    input  wire         hrst,
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    input  wire [318:0] ci,
    output wire [293:0] co,
    input  wire [287:0] es,
    output wire [260:0] er,
    output wire [327:0] po,
    input  wire [288:0] pi,
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output reg          fo
);
    localparam integer LW  = CVL + 1;              // column delay in front of the pcport
    localparam integer WDS = WDONE - (CVL + 3);    // write-done stages after the completion pin flop
    wire hclk = pll_hbm;

    // ---- resets: pin flops; hrst is hclk-synchronous, rsi core-synchronous -------------------------------------------
    (* keep *) reg hr_q;
    (* keep *) reg rs_q;
    always @(posedge hclk) hr_q <= hrst;
    always @(posedge ck)   rs_q <= rsi;
    wire h_rn = hr_q;

    // ---- strap: the scheduler's reset release, dly(pc) cycles after the leaf's ---------------------------------------
    wire [6:0] dtab [0:31];
    genvar gi;
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_dly
        localparam integer RP = ((gi * 118) / 32) % 118;
        assign dtab[gi] = 7'(RP + ((RP + gi) % 2) + (MUT == 1 ? 1 : 0));
    end endgenerate
    reg [6:0] dsel, dcnt;
    reg       hgo;
    (* keep *) reg [4:0] pc_q;
    always @(posedge hclk) begin pc_q <= pc; dsel <= dtab[pc_q]; end
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin dcnt <= 7'd0; hgo <= 1'b0; end
        else if (dcnt == dsel) hgo <= 1'b1;
        else dcnt <= dcnt + 7'd1;

    // ---- kc chain station --------------------------------------------------------------------------------------------
    wire        tc_v;
    wire [31:0] tc_d;
    ot_qkvd_kcmd_tap #(.ROW0(ROW0)) u_tap (.clk(hclk), .rst_n(h_rn), .i_v(ki[0]), .i_d(ki[32:1]),
        .o_v(ko[0]), .o_d(ko[32:1]), .c_v(tc_v), .c_d(tc_d));

    // ---- W-face pin flops (CDC ho) -----------------------------------------------------------------------------------
    (* keep *) reg         wv_q, cv_q, hf_q;
    (* keep *) reg [23:0]  wsec_q, csec_q;
    (* keep *) reg [255:0] cdata_q;
    (* keep *) reg [8:0]   ctag_q;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin wv_q <= 1'b0; cv_q <= 1'b0; hf_q <= 1'b0; end
        else begin wv_q <= ci[3]; cv_q <= ci[28]; hf_q <= ci[318]; end
    always @(posedge hclk) begin wsec_q <= ci[27:4]; csec_q <= ci[52:29]; cdata_q <= ci[308:53]; ctag_q <= ci[317:309]; end

    // ---- E-face pin flops (PHY return) -------------------------------------------------------------------------------
    (* keep *) reg         rv_q;
    (* keep *) reg [287:0] rd_q;
    always @(posedge hclk or negedge h_rn) if (!h_rn) rv_q <= 1'b0; else rv_q <= pi[0];
    always @(posedge hclk) rd_q <= pi[288:1];

    // ---- command arbiter ---------------------------------------------------------------------------------------------
    wire        c_v;                 // embedding static command, HBM side of its crossing (below)
    wire [286:0] c_d;
    reg  [3:0]  cr;
    reg  [2:0]  hold;
    reg         cur_v;
    reg  [18:0] cur_row;
    reg         hand_q;
    reg  [12:0] late_c;
    reg         f_late, f_cmd, f_early;
    wire        cmd_credit;
    // w_sec (ot_qkvd_kv_wq sec_of) = {7'b0, layer[5:0], v, g, t[6], t[13:9], t[5:3]}: the PC-local sector j is the 10
    // bits {v, g, t[6], t[12:9], t[5:3]} (t[13] = sec[7] is 0 for T <= 8,192; a set bit is out of range and never issued)
    wire [9:0]  wj     = {wsec_q[10:8], wsec_q[6:0]};
    wire [18:0] wrow   = 19'(ROW0) + {13'd0, wsec_q[16:11]};
    wire        w_match = (cur_v && cur_row == wrow && !wsec_q[7]) || (MUT == 4);
    wire        w_pend = hgo && wv_q && hold == 3'd0;
    wire        w_go   = w_pend && w_match && cr > 4'd2 && !tc_v;
    wire        cmd_v  = tc_v | w_go;
    wire [31:0] cmd    = tc_v ? tc_d : {2'd2, 20'd0, wj[6:2], wj[9:7], wj[1:0]};
    always @(posedge hclk or negedge hgo)
        if (!hgo) begin
            cr <= 4'd8; hold <= 3'd0; cur_v <= 1'b0; hand_q <= 1'b0; late_c <= 13'd0; f_late <= 1'b0; f_cmd <= 1'b0;
        end else begin
            cr <= cr - {3'd0, cmd_v} + {3'd0, cmd_credit};
            if (cmd_v && cr == 4'd0) f_cmd <= 1'b1;
            hand_q <= w_go;
            if (w_go) hold <= 3'(HOFF); else if (hold != 3'd0) hold <= hold - 3'd1;
            if (tc_v && tc_d[31:30] == 2'd0) cur_v <= 1'b1;
            if (w_pend && !w_match) begin
                if (late_c == 13'(LATE - 1)) f_late <= 1'b1; else late_c <= late_c + 13'd1;
            end else late_c <= 13'd0;
        end
    always @(posedge hclk) if (tc_v && tc_d[31:30] == 2'd0) cur_row <= tc_d[18:0];
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) f_early <= 1'b0;
        else if (!hgo && (tc_v || c_v)) f_early <= 1'b1;      // traffic inside the strap delay

    // ---- the scheduler -----------------------------------------------------------------------------------------------
    wire        row_v, col_v, col_we, col_sr, ctl_fault, s_cr;
    wire [2:0]  row_op;
    wire [4:0]  row_bank, col_bank, col_col;
    wire [18:0] row_row;
    ot_qwen_ctrl_pc_emb #(.ENABLE(1), .PC(0), .PHASE(0)) u_ctl (
        .clk(hclk), .rst_n(hgo), .cmd_v(cmd_v), .cmd(cmd), .read_credit(ci[2:0]), .cmd_credit(cmd_credit),
        .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),
        .col_v(col_v), .col_bank(col_bank), .col_col(col_col), .col_we(col_we), .busy(), .fault(ctl_fault),
        .s_v(c_v), .s_we(c_d[285]), .s_bank(c_d[284:280]), .s_col(c_d[279:275]), .s_row(c_d[274:256]),
        .s_cr(s_cr), .col_sr(col_sr));

    // ---- WR column -> h_wcon, the delayed column of the pcport, completion check, write-done -------------------------
    reg         wcon_q;
    reg  [LW:0] dv, dwe, dsr;                     // [0] = one edge after the pin column ... [LW-1] = the pcport's
    reg  [9:0]  dbc [0:LW];
    integer     di;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin wcon_q <= 1'b0; dv <= 0; dwe <= 0; dsr <= 0; end
        else begin
            wcon_q <= col_v && col_we && !col_sr;
            dv <= {dv[LW-1:0], col_v}; dwe <= {dwe[LW-1:0], col_we}; dsr <= {dsr[LW-1:0], col_sr};
        end
    always @(posedge hclk) begin
        dbc[0] <= {col_bank, col_col};
        for (di = 1; di <= LW; di = di + 1) dbc[di] <= dbc[di-1];
    end
    wire        pcol_v = dv[LW-1], pcol_we = dwe[LW-1], pcol_sr = dsr[LW-1];
    reg         f_wmis;
    wire [9:0]  cj = {csec_q[10:8], csec_q[6:0]};
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) f_wmis <= 1'b0;
        else if (cv_q && dbc[LW] != {cj[9:7], cj[1:0], cj[6:2]}) f_wmis <= 1'b1;
    reg  [WDS:0] av_s;
    reg  [8:0]   at_s [0:WDS];
    integer      wi;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) av_s <= 0; else av_s <= {av_s[WDS-1:0], cv_q};
    always @(posedge hclk) begin
        at_s[0] <= ctag_q;
        for (wi = 1; wi <= WDS; wi = wi + 1) at_s[wi] <= at_s[wi-1];
    end

    // ---- PC port: read class, embedding ECC, PHY write data ----------------------------------------------------------
    wire [287:0] wd, kv_d;
    wire         kv_v, em_v, port_fault;
    wire [257:0] em_d;
    ot_qfd_emb_pcport #(.KVW(2), .MUT(MUT == 2 ? 4 : 0)) u_port (
        .clk(hclk), .rst_n(h_rn), .col_v(pcol_v), .col_we(pcol_we), .col_sr(pcol_sr),
        .w_v(c_v && c_d[286]), .w_d(c_d[255:0]), .wd(wd), .kw_v(cv_q), .kw_d(cdata_q),
        .r_v(rv_q), .r_d(rd_q), .kv_v(kv_v), .kv_d(kv_d), .em_v(em_v), .em_d(em_d), .fault(port_fault));

    // ---- read tags: {open row, j} per KV RD, in order ----------------------------------------------------------------
    reg  [7:0]  brow [0:31];
    reg  [17:0] tq [0:31];
    reg  [5:0]  tw, tr;
    reg         f_tag;
    wire        rd_kv   = col_v && !col_we && !col_sr;
    wire [9:0]  rj      = {col_bank[4:2], col_col, col_bank[1:0]};
    wire        t_empty = tw == tr;
    wire        t_full  = tw[4:0] == tr[4:0] && tw[5] != tr[5];
    wire [17:0] t_head  = tq[tr[4:0]];
    wire [9:0]  t_j     = (MUT == 3) ? {t_head[9:2], t_head[0], t_head[1]} : t_head[9:0];
    wire [7:0]  t_layer = t_head[17:10] - 8'(ROW0);
    always @(posedge hclk) begin
        if (row_v && row_op == 3'd1) brow[row_bank] <= row_row[7:0];
        if (rd_kv) tq[tw[4:0]] <= {brow[col_bank], rj};
    end
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin tw <= 6'd0; tr <= 6'd0; f_tag <= 1'b0; end
        else begin
            if (rd_kv) begin tw <= tw + 6'd1; if (t_full) f_tag <= 1'b1; end
            if (kv_v)  begin tr <= tr + 6'd1; if (t_empty) f_tag <= 1'b1; end
        end

    // ---- landing ECC -> CDC hi ---------------------------------------------------------------------------------------
    wire         l_v, ecc_fault;
    wire [255:0] l_data;
    wire [16:0]  l_sec;
    wire [7:0]   l_row;
    ot_qfd_kv_landing_ecc #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (
        .hclk(hclk), .h_rst_n(h_rn), .i_v(kv_v), .i_code(kv_d), .i_sec({t_layer[5:0], t_j[9:7], 1'b0, t_j[6:0]}), .i_row(t_head[17:10]),
        .o_v(l_v), .o_data(l_data), .o_sec(l_sec), .o_row(l_row), .ce(), .ue(), .fault(ecc_fault), .ce_count());
    assign co = {at_s[WDS], av_s[WDS], wcon_q, hand_q, l_data, l_row, l_sec, l_v};
    assign po = {wd, col_col, col_bank, col_we, col_v, row_row, row_bank, row_op, row_v};

    // ---- embedding static port crossing (strip engine on the core clock) ---------------------------------------------
    (* keep *) reg         es_v_q;
    (* keep *) reg [286:0] es_d_q;
    always @(posedge ck or negedge rs_q) if (!rs_q) es_v_q <= 1'b0; else es_v_q <= es[0];
    always @(posedge ck) es_d_q <= es[287:1];
    wire         e_v, s_credit, f_core, f_ecdc;
    wire [257:0] e_d;
    ot_qfd_emb_cdc #(.ENABLE(1)) u_ecdc (
        .clk(ck), .rst_n(rs_q), .hclk(hclk), .hrst_n(h_rn), .s_v(es_v_q), .s_d(es_d_q), .c_v(c_v), .c_d(c_d),
        .h_credit(s_cr), .s_credit(s_credit), .h_v(em_v), .h_d(em_d), .e_v(e_v), .e_d(e_d),
        .fault_core(f_core), .fault_hbm(f_ecdc));
    reg          er_v, er_cr, er_f;
    reg  [257:0] er_d;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin er_v <= 1'b0; er_cr <= 1'b0; er_f <= 1'b0; end
        else begin er_v <= e_v; er_cr <= s_credit; er_f <= f_core; end
    always @(posedge ck) er_d <= e_d;
    assign er = {er_f, er_cr, er_d, er_v};

    // ---- sticky fault chain, S -> N ----------------------------------------------------------------------------------
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo <= 1'b0;
        else fo <= fi | ctl_fault | port_fault | ecc_fault | hf_q | f_ecdc | f_late | f_cmd | f_early | f_wmis | f_tag;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// qkd_ctrl_kc: the kc stream-command crossing of one controller strip (N end).  The issuer's word kc = {d 32, v}
// (ot_qkvd_kv_seq kc_v / kc_d, core clock, no back-pressure) is captured at the pin, crosses into the HBM controller
// clock through ot_async_fifo (8 words; the issuer sends 2 words a layer) and enters the tap chain on ko (registered).
// The strip's sticky fault chain ends here: fi (hclk) -> two core-clock flops -> kf, OR the FIFO overflow.
// MUT 1 (bench mutant): the command word's layer bit 14 inverted.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ctrl_kc #(
    parameter integer MUT = 0
) (
    input  wire        ck,
    input  wire        rsi,
    input  wire        pll_hbm,
    input  wire        hrst,
    input  wire [32:0] kc,
    output reg  [32:0] ko,
    input  wire        fi,
    output reg         kf
);
    (* keep *) reg hr_q;
    (* keep *) reg rs_q;
    always @(posedge pll_hbm) hr_q <= hrst;
    always @(posedge ck)      rs_q <= rsi;
    (* keep *) reg        kv_q;
    (* keep *) reg [31:0] kd_q;
    always @(posedge ck or negedge rs_q) if (!rs_q) kv_q <= 1'b0; else kv_q <= kc[0];
    always @(posedge ck) kd_q <= kc[32:1];
    wire        w_rdy, r_v;
    wire [31:0] r_d;
    ot_async_fifo #(.WIDTH(32), .DEPTH(8)) u_x (
        .wr_clk(ck), .wr_rst_n(rs_q), .wr_valid(kv_q), .wr_ready(w_rdy), .wr_data(kd_q), .wr_overflow(),
        .rd_clk(pll_hbm), .rd_rst_n(hr_q), .rd_valid(r_v), .rd_ready(1'b1), .rd_data(r_d), .rd_underflow());
    always @(posedge pll_hbm or negedge hr_q) if (!hr_q) ko[0] <= 1'b0; else ko[0] <= r_v;
    always @(posedge pll_hbm) ko[32:1] <= (MUT == 1) ? (r_d ^ 32'h0000_4000) : r_d;
    reg f_ovf;
    (* async_reg = "true" *) reg f1, f2;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin f_ovf <= 1'b0; f1 <= 1'b0; f2 <= 1'b0; kf <= 1'b0; end
        else begin
            if (kv_q && !w_rdy) f_ovf <= 1'b1;
            f1 <= fi; f2 <= f1; kf <= f2 | f_ovf;
        end
endmodule
