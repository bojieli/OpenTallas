// Reference: qkd_ctrl_pc_sched exactly as CLOSED in sched_s7b (claude/qkvctrl-split-1016 eab86b667 / bfe218fc8, main f863de3b4),
// renamed. Golden for tb_sched_pinreg_equiv (sched_s8 PINREG=1: listed outputs one hclk later, the rest same-cycle).
module qkd_ctrl_pc_sched_s7b_ref #(
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = 17,          // write-done edges after the WR column (>= CVL + 4)
    parameter integer LATE  = 4096,        // a held (layer-mismatch) write faults after this many cycles
    parameter integer PROFILE = 0,
    parameter integer EVMUT = 0,
    parameter integer MUT   = 0,
    // HANDOFF 0az: 1 = the PHY read return is elastic (HBM/PHY latency not
    // compile-time fixed). expected_raw_valid is then the NOMINAL (minimum)
    // raw return slot: a return earlier than the nominal count is a fault, a
    // return later is absorbed (tag queue + landing ECC are in order, and the
    // qkd_kv_hbm_elastic_front block buffer re-times the corrected sectors),
    // and an outstanding nominal return with no PHY data for RAW_WD edges is a
    // PHY-late fault (watchdog). 0 = historical exact-slot check.
    parameter integer ELASTIC = 0,
    parameter integer RAW_WD = 256,
    // In-order read tag / pcport class queue depth. The fixed RL23 calendar
    // needs 32; the elastic PHY window needs CMD 4 + RL 23 + window + ECC
    // outstanding reads, so ELASTIC uses 64 (sized in the 0az parent proof).
    parameter integer STRAP_CDC = 0, // 1: physical HBM pin capture -> two core-domain captures
    parameter integer DRAIN_PIPE = 0, // 1: conservative two-edge drain summary; no traffic latency change
    parameter integer TQD = (ELASTIC != 0) ? 64 : 32,
    parameter integer CONTEXT_DESC = 0,
    parameter integer STATIC_REFRESH = 0
) (
    input  wire         pll_hbm,
    input  wire         hrst,
    input  wire [4:0]   pc,
    input  wire [62:0]  ci_c,       // {ci[318:309], ci[52:0]}: the KV write data ci[308:53] lands in the port child
    output wire [11:0]  co_c,       // co[293:282] = {at, av, wcon, hand}; co[281:0] is the ECC child
    output reg [327:0] po,
    input  wire         pi_v,       // pi[0]; pi[288:1] lands in the port child
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output reg          fo,
    input wire static_cmd_owner,input wire [42:0] static_cmd,input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
    input wire [15:0] static_epoch,input wire expected_raw_valid,
    output wire [15:0] corrected_epoch,
    // Registered observations only. A parent drain barrier must join BOTH
    // domains plus actual upstream quiet, front idle and return-ring idle.
    output reg idle_hbm,output reg drain_fault_hbm,
    // ---- hardened-child seams (wires-parent qkd_ctrl_pc_host_static); every seam output is flop-driven ----
    output wire         p_col_v, p_col_we, p_col_sr,     // dv[LW-2] flops: one edge before the port's pin capture
    output reg          p_w_v,                         // static write data, registered (+1 hclk, hidden by >= 4-edge column)
    output reg  [255:0] p_w_d,
    input  wire [287:0] p_wd,
    input  wire         p_kv_v, p_em_v,                // p_em_v: activity veto only (the beat itself lands in the cdc child)
    input  wire         p_fault,
    output reg  [16:0]  e_sec,                         // tag-queue head, registered one edge ahead (lookahead pop)
    output reg  [7:0]   e_row,
    input  wire         e_l_v, e_fault,
    // ---- KVCTRL core_s7 seams (lead Q-KV 2026-10-17: the core is split into sched / cdc / obs hardened children) ----
    output reg  [4:0]   pc_q,                          // -> cdc (core-domain strap capture)
    output reg          s_cr_o,                        // u_ctl s_cr register -> cdc credit pin register
    input  wire         c_v,                           // cdc down-FIFO output registers (+1 hclk vs core_s6)
    input  wire [286:0] c_d,
    input  wire [61:0]  c_context,
    input  wire         f_ecdc,                        // cdc fault_hbm register
    output reg  [346:0] physical_context,              // -> obs input pin registers
    output reg          physical_col_sr,
    output wire         expected_sr,
    input  wire         obs_commit_valid,              // obs commit / native commit registers (+1 hclk vs core_s6)
    input  wire         native_commit_valid,
    input  wire         native_observer_fault
);
    localparam integer LW  = CVL + 1;              // column delay in front of the pcport
    localparam integer WDS = WDONE - (CVL + 3) + 1;    // write-done stages after the completion pin flop
    wire hclk = pll_hbm;

    // ---- resets: pin flops; hrst is hclk-synchronous, rsi core-synchronous -------------------------------------------
    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
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
    (* keep *) reg [8:0]   ctag_q;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin wv_q <= 1'b0; cv_q <= 1'b0; hf_q <= 1'b0; end
        else begin wv_q <= ci_c[3]; cv_q <= ci_c[28]; hf_q <= ci_c[62]; end
    always @(posedge hclk) begin wsec_q <= ci_c[27:4]; csec_q <= ci_c[52:29]; ctag_q <= ci_c[61:53]; end

    // ---- E-face pin flops (PHY return) -------------------------------------------------------------------------------
    (* keep *) reg         rv_q,rawslot_q;
    (* keep *) reg [15:0] epoch_q;
    always @(posedge hclk)epoch_q<=static_epoch;
    always @(posedge hclk or negedge h_rn)if(!h_rn)rawslot_q<=0;else rawslot_q<=expected_raw_valid;
    always @(posedge hclk or negedge h_rn) if (!h_rn) rv_q <= 1'b0; else rv_q <= pi_v;

    // ---- raw PHY return check: exact slot (historical) or elastic window (0az) ---------------------------------------
    localparam integer TQA = $clog2(TQD);
    reg [6:0] raw_out;               // nominal raw returns not yet received (<= TQD outstanding tags)
    reg [8:0] raw_age;
    reg f_raw;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin raw_out <= 6'd0; raw_age <= 9'd0; f_raw <= 1'b0; end
        else if (ELASTIC != 0) begin
            raw_out <= raw_out + {6'd0, rawslot_q} - {6'd0, rv_q};
            if (rv_q && raw_out == 7'd0 && !rawslot_q) f_raw <= 1'b1;           // earlier than nominal / unsolicited
            if (raw_out == 7'(TQD) && rawslot_q && !rv_q) f_raw <= 1'b1;        // outstanding count overflow
            if (rv_q || raw_out == 7'd0) raw_age <= 9'd0;
            else if (raw_age == 9'(RAW_WD - 1)) f_raw <= 1'b1;                  // PHY late beyond watchdog
            else raw_age <= raw_age + 9'd1;
        end
    wire raw_bad = (ELASTIC == 0) ? (rv_q != rawslot_q) : f_raw;

    // ---- command arbiter ---------------------------------------------------------------------------------------------
    wire [346:0] col_context;
    reg  [3:0]  cr;
    reg  [2:0]  hold;
    reg         cur_v;
    reg  [18:0] cur_row;
    reg         hand_q;
    reg  [12:0] late_c;
    reg         f_late, f_cmd, f_early;
    wire        cmd_credit,ctl_phase_idle;
    reg static_owner_d;
    always @(posedge hclk or negedge h_rn)if(!h_rn)static_owner_d<=0;else static_owner_d<=static_owner_q;
    // w_sec (ot_qkvd_kv_wq sec_of) = {7'b0, layer[5:0], v, g, t[6], t[13:9], t[5:3]}: the PC-local sector j is the 10
    // bits {v, g, t[6], t[12:9], t[5:3]} (t[13] = sec[7] is 0 for T <= 8,192; a set bit is out of range and never issued)
    wire [9:0]  wj     = {wsec_q[10:8], wsec_q[6:0]};
    wire [18:0] wrow   = 19'(ROW0) + {13'd0, wsec_q[16:11]};
    wire        w_match = (cur_v && cur_row == wrow && !wsec_q[7]) || (MUT == 4);
    wire        w_pend = hgo && wv_q && hold == 3'd0;
    wire        w_go   = w_pend && w_match && cr > 4'd2 && !tc_v && !static_owner_q;
    (* keep *) reg static_owner_q,static_v_q,rdslot_q,srslot_q,wrslot_q;
    (* keep *) reg [31:0] static_d_q;
    (* keep *) reg [9:0] static_first_q;
    always @(posedge hclk)begin static_d_q<=static_cmd[32:1];static_first_q<=static_cmd[42:33];end
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin static_owner_q<=0;static_v_q<=0;rdslot_q<=0;srslot_q<=0;wrslot_q<=0;end
      else begin static_owner_q<=static_cmd_owner;static_v_q<=static_cmd[0];rdslot_q<=reserved_rd;srslot_q<=reserved_static_col;wrslot_q<=reserved_write_col;end
    wire        cmd_v  = static_owner_q ? static_v_q : (tc_v | w_go);
    wire [31:0] cmd    = static_owner_q ? static_d_q : tc_v ? tc_d : {2'd2, 20'd0, wj[6:2], wj[9:7], wj[1:0]};
    always @(posedge hclk or negedge hgo)
        if (!hgo) begin
            cr <= 4'd8; hold <= 3'd0; cur_v <= 1'b0; hand_q <= 1'b0; late_c <= 13'd0; f_late <= 1'b0; f_cmd <= 1'b0;
        end else begin
            cr <= cr - {3'd0, cmd_v} + {3'd0, cmd_credit};
            if (cmd_v && cr == 4'd0) f_cmd <= 1'b1;
            if((static_owner_q&&(tc_v||w_pend))||(!static_owner_q&&static_v_q))f_cmd<=1'b1;
            if(static_owner_q!=static_owner_d && (!ctl_phase_idle||tw!=tr||c_v||cv_q||wv_q))f_cmd<=1'b1;
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
        else if (!hgo && (tc_v || c_v || static_v_q)) f_early <= 1'b1;      // traffic inside the strap delay

    // ---- the scheduler -----------------------------------------------------------------------------------------------
    wire        row_v, col_v, col_we, col_sr, ctl_fault, s_cr;
    always @(*) s_cr_o = s_cr;   // u_ctl.s_cr is a register (output pin flop of the child: no logic)
    wire [2:0]  row_op;
    wire [4:0]  row_bank, col_bank, col_col;
    wire [18:0] row_row;
    ot_qkd_static_ctrl_pc_emb #(.STATIC_REFRESH(STATIC_REFRESH),.CONTEXT_DESC(CONTEXT_DESC),.ENABLE(1), .PC(0), .PHASE(0),.PROFILE(PROFILE)) u_ctl (
        .clk(hclk), .rst_n(hgo), .cmd_v(cmd_v), .cmd(cmd), .cmd_first(static_owner_q?static_first_q:10'd0),.reserved_rd(rdslot_q),.reserved_static_col(srslot_q),.reserved_write_col(wrslot_q),.boot_window(1'b0),.col_boot(), .cmd_credit(cmd_credit),
        .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),
        .col_v(col_v), .col_bank(col_bank), .col_col(col_col), .col_we(col_we), .busy(), .phase_idle(ctl_phase_idle), .fault(ctl_fault),
        .s_context({c_context,c_d[274:256],c_d[284:280],c_d[279:275],c_d[255:0]}),.col_context(col_context),.s_v(c_v), .s_we(c_d[285]), .s_bank(c_d[284:280]), .s_col(c_d[279:275]), .s_row(c_d[274:256]),
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
    // u_port (ot_qfd_emb_pcport KVW2) is the hardened child qkd_ctrl_pc_port_child: it captures the column at its
    // pin from dv[LW-2] (same edge as the historical dv[LW-1]), and the KV write / PHY read data at its own pin flops.
    wire [287:0] wd = p_wd;
    wire         kv_v = p_kv_v, em_v = p_em_v, port_fault = p_fault;
    assign p_col_v = dv[LW-2], p_col_we = dwe[LW-2], p_col_sr = dsr[LW-2];   // CVL >= 1
    always @(posedge hclk or negedge h_rn) if (!h_rn) p_w_v <= 1'b0; else p_w_v <= c_v && c_d[286];
    always @(posedge hclk) p_w_d <= c_d[255:0];

    // ---- read tags: {open row, j} per KV RD, in order ----------------------------------------------------------------
    reg  [7:0]  brow [0:31];
    reg  [33:0] tq [0:TQD-1];
    reg  [TQA:0] tw, tr;
    reg         f_tag;
    wire        rd_kv   = col_v && !col_we && !col_sr;
    wire [9:0]  rj      = {col_bank[4:2], col_col, col_bank[1:0]};
    wire        t_empty = tw == tr;
    wire        t_full  = tw[TQA-1:0] == tr[TQA-1:0] && tw[TQA] != tr[TQA];
    wire [33:0] t_head  = tq[tr[TQA-1:0]];
    wire [9:0]  t_j     = (MUT == 3) ? {t_head[9:2], t_head[0], t_head[1]} : t_head[9:0];
    wire [7:0]  t_layer = t_head[17:10] - 8'(ROW0);
    always @(posedge hclk) begin
        if (row_v && row_op == 3'd1) brow[row_bank] <= row_row[7:0];
        if (rd_kv) tq[tw[TQA-1:0]] <= {epoch_q,brow[col_bank], rj};
    end
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin tw <= '0; tr <= '0; f_tag <= 1'b0; end
        else begin
            if (rd_kv) begin tw <= tw + 1'b1; if (t_full) f_tag <= 1'b1; end
            if (kv_v)  begin tr <= tr + 1'b1; if (t_empty) f_tag <= 1'b1; end
        end

    // ---- landing ECC -> CDC hi ---------------------------------------------------------------------------------------
    // u_ecc (ot_qfd_kv_landing_ecc) is the hardened child qkd_ctrl_pc_ecc_child. Its PIPE stage 0 captures i_v / i_code
    // (port flops) and i_sec / i_row on the same edge; the head metadata is registered here one edge ahead: the head
    // at edge t is tq[tr + kv_v] at t-1 (an entry is written >= RL + PHY edges before its beat returns).
    // KVCTRL core_s4 (2026-10-16): e_l_v is captured in a pin flop (was a 13-level input cone into drain_kv). l_v only
    // feeds the drain debt / idle observations: drain_kv now counts the landing one hclk edge later (debt held one edge
    // longer, never early); the raw pin bit stays in the activity veto so idle cannot assert in between. Traffic 0 edges.
    reg          l_v_q;
    always @(posedge hclk or negedge h_rn) if (!h_rn) l_v_q <= 1'b0; else l_v_q <= e_l_v;
    wire         l_v = l_v_q, ecc_fault = e_fault;
    // KVCTRL core_s4: identical to e_sec/e_row <= f(tq[tr + kv_v]), but both candidates f(tq[tr]) and f(tq[tr1]) (tr1 a
    // register = tr + 1) are formed in parallel and the port child's kv_v selects LAST (core_s1: p_kv_v -> e_sec 13 levels).
    reg  [TQA-1:0] tr1;
    always @(posedge hclk or negedge h_rn) if (!h_rn) tr1 <= TQA'(1); else if (kv_v) tr1 <= tr1 + 1'b1;
    wire [33:0]  h_c0    = tq[tr[TQA-1:0]];
    wire [33:0]  h_c1    = tq[tr1];
    wire [9:0]   h_c0_j  = (MUT == 3) ? {h_c0[9:2], h_c0[0], h_c0[1]} : h_c0[9:0];
    wire [9:0]   h_c1_j  = (MUT == 3) ? {h_c1[9:2], h_c1[0], h_c1[1]} : h_c1[9:0];
    wire [7:0]   h_c0_l  = h_c0[17:10] - 8'(ROW0);
    wire [7:0]   h_c1_l  = h_c1[17:10] - 8'(ROW0);
    wire [16:0]  e_sec_c0 = {h_c0_l[5:0], h_c0_j[9:7], 1'b0, h_c0_j[6:0]};
    wire [16:0]  e_sec_c1 = {h_c1_l[5:0], h_c1_j[9:7], 1'b0, h_c1_j[6:0]};
    always @(posedge hclk) begin e_sec <= kv_v ? e_sec_c1 : e_sec_c0; e_row <= kv_v ? h_c1[17:10] : h_c0[17:10]; end
    reg [15:0] ep0,ep1,ep2;
    always @(posedge hclk)begin ep0<=t_head[33:18];ep1<=ep0;ep2<=ep1;end
    assign corrected_epoch=ep2;
    assign co_c = {at_s[WDS], av_s[WDS], wcon_q, hand_q};
    // Dedicated raw PHY pin stage: all command and write-data bits move
    // together, preserving JEDEC spacings and CWL alignment. Physical static
    // completion and KV write retirement move with the actual launched column.
    reg [3:0] expected_sr_pipe;
    assign expected_sr=expected_sr_pipe[3];
    always @(posedge hclk or negedge h_rn)if(!h_rn)expected_sr_pipe<=0;else expected_sr_pipe<={expected_sr_pipe[2:0],reserved_static_col};
    always @(posedge hclk)physical_context<=col_context;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin po<=0;physical_col_sr<=0;end
      else begin po<={wd,col_col,col_bank,col_we,col_v,row_row,row_bank,row_op,row_v};physical_col_sr<=col_sr;end

    // ---- sticky fault chain, S -> N ----------------------------------------------------------------------------------
    // KVCTRL core_s7: the observer fault arrives from the obs child's fault register (its own logic one edge later).
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo <= 1'b0;
        else fo <= fo | fi | ctl_fault | port_fault | ecc_fault | hf_q | f_ecdc | f_late | f_cmd | f_early | f_wmis | f_tag | raw_bad | native_observer_fault;

    // KV corrected returns include tag, PHY raw, pcport and landing ECC
    // pipelines. Static reads are covered above through their actual e_v.
    reg [15:0] drain_kv;
    // KVCTRL core_s6 (2026-10-16): the raw e_l_v pin left the activity veto (structural fix of core_s5 EARLY_FAIL_HOLD:
    // e_l_v -> l_v_q/D FF hold -17.17 ps was the ONE endpoint the CTS hold repair could not fix -- the port also fed this
    // combinational OR, so the flow gave it no input hold pad, and the repair could not buffer it). A legal landing always
    // has drain_kv >= 1 two edges before l_v (rd_kv precedes its landing by >= RL + PHY edges), so hbm_debt_zero_q already
    // vetoes idle_hbm on every edge the raw bit did; l_v (= e_l_v one edge later) stays in the veto. Cycle-identical for
    // all legal traffic; an unsolicited zero-debt landing still raises drain_fault_hbm and drops idle_hbm one edge later.
    // e_l_v now loads only its pin flop.
    wire hbm_drain_activity=obs_commit_valid||rd_kv||tc_v||cmd_v||static_v_q||c_v||s_cr||wv_q||cv_q||hand_q||
      wcon_q||row_v||col_v||po[0]||po[28]||rv_q||rawslot_q||kv_v||em_v||l_v||native_commit_valid;
    reg hbm_debt_zero_q;reg [1:0] hbm_quiet_q;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin hbm_debt_zero_q<=0;hbm_quiet_q<=0;end
      else begin
        hbm_debt_zero_q<=raw_out==0&&drain_kv==0&&hold==0&&dv==0&&av_s==0;
        hbm_quiet_q<={hbm_quiet_q[0],!hbm_drain_activity};
      end
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin drain_kv<=0;drain_fault_hbm<=0;idle_hbm<=0;end
      else begin
        case({rd_kv,l_v})
          2'b10:drain_kv<=drain_kv+16'd1;
          2'b01:drain_kv<=drain_kv-16'd1;
          default:;
        endcase
        if((l_v&&!rd_kv&&drain_kv==0)||
           (rd_kv&&!l_v&&drain_kv==16'hffff))drain_fault_hbm<=1;
        if(DRAIN_PIPE!=0)idle_hbm<=hgo&&ctl_phase_idle&&t_empty&&hbm_debt_zero_q&&
          (&hbm_quiet_q)&&!hbm_drain_activity&&!drain_fault_hbm&&!fo&&!f_ecdc;
        else idle_hbm<=hgo&&ctl_phase_idle&&t_empty&&raw_out==0&&drain_kv==0&&
          !tc_v&&!cmd_v&&!static_v_q&&!c_v&&!s_cr&&!wv_q&&!cv_q&&!hand_q&&
          hold==0&&!wcon_q&&dv==0&&av_s==0&&!row_v&&!col_v&&!po[0]&&!po[28]&&
          !rv_q&&!rawslot_q&&!kv_v&&!em_v&&!l_v&&!e_l_v&&!native_commit_valid&&!obs_commit_valid&&
          !drain_fault_hbm&&!fo&&!f_ecdc;
      end
endmodule
