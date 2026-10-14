`timescale 1ns/1ps
// Original qkd_ctrl_pc body from origin/main source plus isolated static
// column completion observer. Existing CLOSED master/source remains untouched.
// Observer retains actual controller-domain WDONE17 and crosses ordered
// static-column events to ck; output credit er259 is still an early credit.
module qkd_ctrl_pc_host #(
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = 17,          // write-done edges after the WR column (>= CVL + 4)
    parameter integer LATE  = 4096,        // a held (layer-mismatch) write faults after this many cycles
    parameter integer EVMUT = 0,
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
    output reg          fo,
    output wire completion_v,completion_we,completion_fault
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
    qkd_ctrl_static_commit #(.WDONE(WDONE),.MUT(EVMUT)) u_static_commit(
        .hclk(hclk),.hrst_n(h_rn),.ck(ck),.rst_n(rs_q),
        .col_v(col_v),.col_we(col_we),.col_sr(col_sr),
        .completion_v(completion_v),.completion_we(completion_we),.fault(completion_fault));
endmodule
