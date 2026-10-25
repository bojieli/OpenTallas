// Hardened-root REMAINDER of qkd_ctrl_pc_host_static (Q-KVSYS-DIE KVCTRL split 2026-10-16): the original body with
// u_port (ot_qfd_emb_pcport) and u_ecc (ot_qfd_kv_landing_ecc) peeled into their own hardened children (separate HBM
// clock roots; e1 measured 17,150 sinks on one root, insertion 426.8 ps). Traffic timing is edge-for-edge unchanged
// except: static write data reaches the port +1 hclk (the column follows c_v by >= 4 edges) and the native commit
// observation leaves +1 hclk through a pin register.
module qkd_ctrl_pc_host_static_core #(
    parameter integer CORE_CLOCK = 0,
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = CORE_CLOCK ? 19 : 17,          // write-done edges after the WR column (>= CVL + 4)
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
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    input  wire [62:0]  ci_c,       // {ci[318:309], ci[52:0]}: the KV write data ci[308:53] lands in the port child
    output wire [11:0]  co_c,       // co[293:282] = {at, av, wcon, hand}; co[281:0] is the ECC child
    input  wire [287:0] es,
    output wire [260:0] er,
    output reg [327:0] po,
    input  wire         pi_v,       // pi[0]; pi[288:1] lands in the port child
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output reg          fo,
    input wire static_cmd_owner,input wire [42:0] static_cmd,input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
    input wire [15:0] static_epoch,input wire expected_raw_valid,
    input wire [1:0] cfg_stack,
    input wire [317:0] es_context,
    input wire es_expected_valid,input wire [60:0] es_expected_identity,
    input wire [28:0] es_expected_address,input wire [4:0] es_expected_pc,input wire [1:0] es_expected_stack,
    output wire native_commit_valid,output wire [60:0] native_commit_identity,
    output wire [28:0] native_commit_address,
    output wire [15:0] corrected_epoch,
    output wire completion_v,completion_we,completion_fault,
    // Registered observations only. A parent drain barrier must join BOTH
    // domains plus actual upstream quiet, front idle and return-ring idle.
    output wire idle_core,output reg idle_hbm,output reg drain_fault_core,drain_fault_hbm,
    // ---- hardened-child seams (wires-parent qkd_ctrl_pc_host_static); every seam output is flop-driven ----
    output wire         p_col_v, p_col_we, p_col_sr,     // dv[LW-2] flops: one edge before the port's pin capture
    output reg          p_w_v,                         // static write data, registered (+1 hclk, hidden by >= 4-edge column)
    output reg  [255:0] p_w_d,
    input  wire [287:0] p_wd,
    input  wire         p_kv_v, p_em_v,
    input  wire [257:0] p_em_d,
    input  wire         p_fault,
    output reg  [16:0]  e_sec,                         // tag-queue head, registered one edge ahead (lookahead pop)
    output reg  [7:0]   e_row,
    input  wire         e_l_v, e_fault
);
    localparam integer LW  = CVL + 1;              // column delay in front of the pcport
    localparam integer WDS = WDONE - (CVL + 3) + 1;    // write-done stages after the completion pin flop
    wire hclk = pll_hbm;
    wire obs_commit_valid;wire [60:0] obs_commit_identity;wire [28:0] obs_commit_address;

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
    wire        c_v;                 // embedding static command, HBM side of its crossing (below)
    wire [286:0] c_d;wire [61:0] c_context;wire [346:0] col_context;wire native_observer_fault;
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
    wire [2:0]  row_op;
    wire [4:0]  row_bank, col_bank, col_col;
    wire [18:0] row_row;
    ot_qkd_static_ctrl_pc_emb #(.CORE_CLOCK(CORE_CLOCK),.STATIC_REFRESH(STATIC_REFRESH),.CONTEXT_DESC(CONTEXT_DESC),.ENABLE(1), .PC(0), .PHASE(0),.PROFILE(PROFILE)) u_ctl (
        .clk(hclk), .rst_n(hgo), .cmd_v(cmd_v), .cmd(cmd), .cmd_first(static_owner_q?static_first_q:10'd0),.reserved_rd(rdslot_q),.reserved_static_col(srslot_q),.reserved_write_col(wrslot_q),.boot_window(1'b0),.col_boot(), .cmd_credit(cmd_credit),   // KV-TOK B: legacy (ci) controller, not on the static KV die: no boot window
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
    wire [257:0] em_d = p_em_d;
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
    reg physical_col_sr;
    reg [3:0] expected_sr_pipe;
    always @(posedge hclk or negedge h_rn)if(!h_rn)expected_sr_pipe<=0;else expected_sr_pipe<={expected_sr_pipe[2:0],reserved_static_col};
    reg [346:0] physical_context;
    always @(posedge hclk)physical_context<=col_context;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin po<=0;physical_col_sr<=0;end
      else begin po<={wd,col_col,col_bank,col_we,col_v,row_row,row_bank,row_op,row_v};physical_col_sr<=col_sr;end

    // ---- embedding static port crossing (strip engine on the core clock) ---------------------------------------------
    (* keep *) reg         es_v_q;
    (* keep *) reg [286:0] es_d_q;
    (* keep *) reg [317:0] es_context_q;
    (* keep *) reg es_expected_q;
    (* keep *) reg [60:0] es_expected_identity_q;
    (* keep *) reg [28:0] es_expected_address_q;
    (* keep *) reg [4:0] es_expected_pc_q,pc_core_q;
    (* keep *) reg [4:0] pc_core_meta;
    (* keep *) reg [1:0] stack_q,es_expected_stack_q;
    reg native_intake_fault;
    always @(posedge ck)begin
      es_context_q<=es_context;es_expected_identity_q<=es_expected_identity;
      es_expected_address_q<=es_expected_address;es_expected_pc_q<=es_expected_pc;
      es_expected_stack_q<=es_expected_stack;stack_q<=cfg_stack;
      pc_core_meta<=pc_q;pc_core_q<=(STRAP_CDC!=0)?pc_core_meta:pc;
    end
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin es_expected_q<=0;native_intake_fault<=0;end
      else begin
        es_expected_q<=es_expected_valid;
        if(PROFILE==0 && ((es_v_q&&es_context_q[317])!=es_expected_q))native_intake_fault<=1;
        if(es_v_q&&es_context_q[317] && (es_context_q[316:256]!=es_expected_identity_q ||
          es_context_q[255:0]!={256{1'b1}} || !es_d_q[286] || !es_d_q[285] ||
          {es_d_q[274:256],es_d_q[284:280],es_d_q[279:275]}!=es_expected_address_q ||
          pc_core_q!=es_expected_pc_q || stack_q!=es_expected_stack_q))native_intake_fault<=1;
      end
    always @(posedge ck or negedge rs_q) if (!rs_q) es_v_q <= 1'b0; else es_v_q <= es[0];
    always @(posedge ck) es_d_q <= es[287:1];
    wire         e_v, s_credit, f_core, f_ecdc;
    wire [257:0] e_d;
    ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (
        .clk(ck), .rst_n(rs_q), .hclk(hclk), .hrst_n(h_rn), .s_v(es_v_q), .s_d(es_d_q),.s_context(es_context_q[317:256]), .c_v(c_v), .c_d(c_d),.c_context(c_context),
        .h_credit(s_cr), .s_credit(s_credit), .h_v(em_v), .h_d(em_d), .e_v(e_v), .e_d(e_d),
        .fault_core(f_core), .fault_hbm(f_ecdc));
    reg          er_v, er_cr, er_f;
    reg  [257:0] er_d;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin er_v <= 1'b0; er_cr <= 1'b0; er_f <= 1'b0; end
        else begin er_v <= e_v; er_cr <= s_credit; er_f <= f_core | native_intake_fault; end
    always @(posedge ck) er_d <= e_d;
    assign er = {er_f, er_cr, er_d, er_v};

    // ---- sticky fault chain, S -> N ----------------------------------------------------------------------------------
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo <= 1'b0;
        else fo <= fo | fi | ctl_fault | port_fault | ecc_fault | hf_q | f_ecdc | f_late | f_cmd | f_early | f_wmis | f_tag | raw_bad | native_observer_fault;
    qkd_static_kv_write_observer #(.STRICT(PROFILE==0),.WL(CORE_CLOCK ? 7 : 5)) u_native_write_observer(
        .hclk(hclk),.rst_n(h_rn),.po(po),.static_column(physical_col_sr),.expected_static_column(expected_sr_pipe[3]),.context_word(physical_context),
        .commit_valid(obs_commit_valid),.commit_identity(obs_commit_identity),.commit_address(obs_commit_address),.fault(native_observer_fault));
    // Output pin stage (structural fix of the e2 native_commit_identity output path): the observer's commit flops sit
    // with the payload pipe; these flops sit at the W pins. +1 hclk on the commit observation, none on traffic.
    (* keep *) reg nc_v_q;(* keep *) reg [60:0] nc_id_q;(* keep *) reg [28:0] nc_ad_q;
    always @(posedge hclk or negedge h_rn)if(!h_rn)nc_v_q<=1'b0;else nc_v_q<=obs_commit_valid;
    always @(posedge hclk)begin nc_id_q<=obs_commit_identity;nc_ad_q<=obs_commit_address;end
    assign native_commit_valid=nc_v_q;assign native_commit_identity=nc_id_q;assign native_commit_address=nc_ad_q;
    qkd_ctrl_static_commit #(.WDONE(WDONE),.MUT(EVMUT)) u_static_commit(
        .hclk(hclk),.hrst_n(h_rn),.ck(ck),.rst_n(rs_q),
        .col_v(po[28]),.col_we(po[29]),.col_sr(physical_col_sr),
        .completion_v(completion_v),.completion_we(completion_we),.fault(completion_fault));

    // ---- actual outstanding work observations (not execution/admission gates) ----
    // Completion is WDONE, not the early er credit. Reads additionally wait
    // for the actual returned payload; elastic PHY lateness cannot assert idle.
    // Credits are counted separately so no hidden credit FIFO entry is ignored.
    reg [15:0] drain_desc,drain_reads,drain_credits;
    wire dc_push=es_v_q,dc_pop=completion_v;
    wire dr_push=es_v_q&&!es_d_q[285],dr_pop=e_v;
    wire dq_push=es_v_q,dq_pop=s_credit;
    // Register wide reductions independently, and require two quiet edges so
    // a stale zero summary cannot hide an intake captured on the previous edge.
    // Current activity remains an eager veto; only idle assertion may be later.
    wire core_drain_activity_q=es_v_q||completion_v||e_v||er_v||s_credit||er_cr;   // all but the raw es[0] pin
    // KVCTRL core_s6 (2026-10-16): the raw es[0] pin no longer enters the quiet pipe. es_v_q <= es[0] on the same reset
    // and every edge, and es_v_q is in core_drain_activity_q, so the edge after es[0] already vetoes every idle_core_r
    // that the raw bit vetoed (core_quiet_q[0] is only read through &core_quiet_q one edge later, beside
    // !core_drain_activity_q): cycle-identical. es[0] now loads ONLY pin flops (es_v_q, es0_idle_q), so the flow's input
    // hold pad covers it (s5 route: ports with a combinational load get no pad and RSZ could not buffer them).
    wire core_drain_activity=core_drain_activity_q;
    // KVCTRL core_s5 (2026-10-16): idle split, cycle-identical. idle_core_r registers the idle AND WITHOUT the raw es[0]
    // pin; es0_idle_q is a dedicated es[0] pin flop; idle_core = idle_core_r & !es0_idle_q is exactly the former
    // registered AND (both flops capture on the same edge). core_s4 gate: es[0] -> idle_core in->reg -34.9 ps.
    reg idle_core_r;
    (* keep *) reg es0_idle_q;
    always @(posedge ck or negedge rs_q) if(!rs_q) es0_idle_q<=1'b0; else es0_idle_q<=es[0];
    assign idle_core=idle_core_r&&!es0_idle_q;
    reg core_debt_zero_q;reg [1:0] core_quiet_q;
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin core_debt_zero_q<=0;core_quiet_q<=0;end
      else begin
        core_debt_zero_q<=drain_desc==0&&drain_reads==0&&drain_credits==0;
        core_quiet_q<={core_quiet_q[0],!core_drain_activity};
      end
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin
        drain_desc<=0;drain_reads<=0;drain_credits<=0;
        drain_fault_core<=0;idle_core_r<=0;
      end else begin
        case({dc_push,dc_pop})
          2'b10:drain_desc<=drain_desc+16'd1;
          2'b01:drain_desc<=drain_desc-16'd1;
          default:;
        endcase
        case({dr_push,dr_pop})
          2'b10:drain_reads<=drain_reads+16'd1;
          2'b01:drain_reads<=drain_reads-16'd1;
          default:;
        endcase
        case({dq_push,dq_pop})
          2'b10:drain_credits<=drain_credits+16'd1;
          2'b01:drain_credits<=drain_credits-16'd1;
          default:;
        endcase
        if((dc_pop&&!dc_push&&drain_desc==0)||
           (dr_pop&&!dr_push&&drain_reads==0)||
           (dq_pop&&!dq_push&&drain_credits==0)||
           (dc_push&&!dc_pop&&drain_desc==16'hffff)||
           (dr_push&&!dr_pop&&drain_reads==16'hffff)||
           (dq_push&&!dq_pop&&drain_credits==16'hffff))drain_fault_core<=1;
        if(DRAIN_PIPE!=0)idle_core_r<=core_debt_zero_q&&(&core_quiet_q)&&!core_drain_activity_q&&
          !drain_fault_core&&!completion_fault&&!f_core&&!native_intake_fault;
        else idle_core_r<=drain_desc==0&&drain_reads==0&&drain_credits==0&&
          !es_v_q&&!completion_v&&!e_v&&!er_v&&!s_credit&&!er_cr&&
          !drain_fault_core&&!completion_fault&&!f_core&&!native_intake_fault;
      end
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

// ================================================================================================================
// KVCTRL core_s7 (lead Q-KV 2026-10-17): core_s6w CLOSED but native FAIL (one hclk root 13.8k sinks over 116.6 x 216 um:
// R 265 > the 220 ps launch budget). The core is split into three hardened children with short roots: qkd_ctrl_pc_sched
// (u_ctl, tags, raw check, arbiter, W/E pin flops, KV drain), qkd_ctrl_pc_cdc_child, qkd_ctrl_pc_obs_child. The monolith
// qkd_ctrl_pc_host_static_core above is kept for history / the r2 alternative; qkd_ctrl_pc_host_static binds the children.
module qkd_ctrl_pc_sched #(
    parameter integer CORE_CLOCK = 0,
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = CORE_CLOCK ? 19 : 17,          // write-done edges after the WR column (>= CVL + 4)
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
    parameter integer STATIC_REFRESH = 0,
    // KVCTRL sched_s8 (KV-SCHED8 2026-10-17; s7b native audit FAIL: launch 308.9 on 309 po/ko pins, capture 306.2 on 175
    // pins): 1 = flop-first pins.  Every input feeding logic or a cross-tile wire lands in a pin flop, and every output
    // whose s7b register sat at the far face is re-registered at its own pin.  Exact contract: the outputs po, p_w_v,
    // p_w_d, physical_context, physical_col_sr, expected_sr, idle_hbm, fo and ko are the s7b outputs ONE hclk later
    // (bit-identical, every cycle, any input sequence); every other output is the s7b output on the same cycle.
    // 0 = s7b (byte-identical logic).  2 (KV-NATIVE sched_s10) = 1 plus e_sec / e_row registered at the pin (one hclk
    // later than s7b; pair with qkd_ctrl_pc_ecc_child_sl, which takes section / row one edge after the beat).
    parameter integer PINREG = 0
) (
    input  wire         pll_hbm,
    input  wire         hrst,
    input  wire [4:0]   pc,
    input  wire [62:0]  ci_c,       // {ci[318:309], ci[52:0]}: the KV write data ci[308:53] lands in the port child
    output wire [11:0]  co_c,       // co[293:282] = {at, av, wcon, hand}; co[281:0] is the ECC child
    output wire [327:0] po,
    input  wire         pi_v,       // pi[0]; pi[288:1] lands in the port child
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output wire         fo,
    input wire static_cmd_owner,input wire [42:0] static_cmd,input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
    input wire [15:0] static_epoch,input wire expected_raw_valid,
    output wire [15:0] corrected_epoch,
    // Registered observations only. A parent drain barrier must join BOTH
    // domains plus actual upstream quiet, front idle and return-ring idle.
    output wire idle_hbm,output reg drain_fault_hbm,
    // ---- hardened-child seams (wires-parent qkd_ctrl_pc_host_static); every seam output is flop-driven ----
    output wire         p_col_v, p_col_we, p_col_sr,     // dv[LW-2] flops: one edge before the port's pin capture
    output wire         p_w_v,                         // static write data, registered (+1 hclk, hidden by >= 4-edge column)
    output wire [255:0] p_w_d,
    input  wire [287:0] p_wd,
    input  wire         p_kv_v, p_em_v,                // p_em_v: activity veto only (the beat itself lands in the cdc child)
    input  wire         p_fault,
    output wire [16:0]  e_sec,                         // tag-queue head, registered one edge ahead (lookahead pop)
    output wire [7:0]   e_row,                         // PINREG: 2:1 select of two registers by the p_kv_v pin flop
    input  wire         e_l_v, e_fault,
    // ---- KVCTRL core_s7 seams (lead Q-KV 2026-10-17: the core is split into sched / cdc / obs hardened children) ----
    output reg  [4:0]   pc_q,                          // -> cdc (core-domain strap capture)
    output reg          s_cr_o,                        // u_ctl s_cr register -> cdc credit pin register
    input  wire         c_v,                           // cdc down-FIFO output registers (+1 hclk vs core_s6)
    input  wire [286:0] c_d,
    input  wire [61:0]  c_context,
    input  wire         f_ecdc,                        // cdc fault_hbm register
    output wire [346:0] physical_context,              // -> obs input pin registers
    output wire         physical_col_sr,
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
    wire [32:0] ko_r;                              // s7b ko (u_tap o_v / o_d)
    wire        tap_cv;
    wire [31:0] tap_cd;
    ot_qkvd_kcmd_tap #(.ROW0(ROW0)) u_tap (.clk(hclk), .rst_n(h_rn), .i_v(ki[0]), .i_d(ki[32:1]),
        .o_v(ko_r[0]), .o_d(ko_r[32:1]), .c_v(tap_cv), .c_d(tap_cd));
    // KVCTRL sched_s8 (PINREG): the tap's c_v / c_d registers are exactly the decode of its o_v / o_d registers on the
    // same edge (both load i_v / i_d on one edge, same reset), so the chain-word pin flops o_v / o_d alone capture ki
    // and the controller command is decoded after them (0 cycles; s7b ki[32:31] -> c_v / c_d decode before the flop).
    wire [1:0]  tap_op = ko_r[32:31];
    assign tc_v = (PINREG != 0) ? (ko_r[0] && (tap_op == 2'd0 || tap_op == 2'd1)) : tap_cv;
    assign tc_d = (PINREG != 0) ? ((tap_op == 2'd0) ? {2'd0, 11'd1024, 19'(ROW0 + ko_r[20:15])} : {2'd1, 30'd0}) : tap_cd;

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
            if(static_owner_q!=static_owner_d && (!ctl_phase_idle||tw!=trv||c_v||cv_q||wv_q))f_cmd<=1'b1;
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
    ot_qkd_static_ctrl_pc_emb #(.CORE_CLOCK(CORE_CLOCK),.STATIC_REFRESH(STATIC_REFRESH),.CONTEXT_DESC(CONTEXT_DESC),.ENABLE(1), .PC(0), .PHASE(0),.PROFILE(PROFILE)) u_ctl (
        .clk(hclk), .rst_n(hgo), .cmd_v(cmd_v), .cmd(cmd), .cmd_first(static_owner_q?static_first_q:10'd0),.reserved_rd(rdslot_q),.reserved_static_col(srslot_q),.reserved_write_col(wrslot_q),.boot_window(1'b0),.col_boot(), .cmd_credit(cmd_credit),   // KV-TOK B: legacy (ci) controller, not on the static KV die: no boot window
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
    reg          p_w_v_r;
    reg  [255:0] p_w_d_r;
    always @(posedge hclk or negedge h_rn) if (!h_rn) p_w_v_r <= 1'b0; else p_w_v_r <= c_v && c_d[286];
    always @(posedge hclk) p_w_d_r <= c_d[255:0];

    // ---- read tags: {open row, j} per KV RD, in order ----------------------------------------------------------------
    reg  [7:0]  brow [0:31];
    reg  [33:0] tq [0:TQD-1];
    reg  [TQA:0] tw, tr;
    reg         f_tag;
    wire        rd_kv   = col_v && !col_we && !col_sr;
    wire [9:0]  rj      = {col_bank[4:2], col_col, col_bank[1:0]};
    // KVCTRL sched_s8 (PINREG): the read pointer is formed from registers only -- trd counts pops through the p_kv_v
    // pin flop kvc_q (one edge late) and trv = trd + kvc_q (= the s7b tr on every edge; a mux of precomputed
    // trd / trd + 1 / trd + 2 registers), so p_kv_v loads only its pin flops and the e_sec / e_row select.
    wire [TQA:0]   trv;
    wire [TQA-1:0] tr1v;
    wire        t_empty = tw == trv;
    wire        t_full  = tw[TQA-1:0] == trv[TQA-1:0] && tw[TQA] != trv[TQA];
    wire [33:0] t_head  = tq[trv[TQA-1:0]];
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
    wire        kvs;                               // PINREG: the p_kv_v pin flop (kvc_q); 0 otherwise
    generate if (PINREG != 0) begin : g_trd
        reg kvc_q;
        assign kvs = kvc_q;
        reg [TQA:0] trd, trd_p1, trd_p2;
        always @(posedge hclk or negedge h_rn)
            if (!h_rn) begin kvc_q <= 1'b0; trd <= '0; trd_p1 <= (TQA+1)'(1); trd_p2 <= (TQA+1)'(2); end
            else begin
                kvc_q <= kv_v;
                if (kvc_q) begin trd <= trd_p1; trd_p1 <= trd_p2; trd_p2 <= trd_p2 + 1'b1; end
            end
        assign trv  = kvc_q ? trd_p1 : trd;
        assign tr1v = kvc_q ? trd_p2[TQA-1:0] : trd_p1[TQA-1:0];
    end else begin : g_tr
        assign kvs = 1'b0;
        assign trv = tr; assign tr1v = tr1;
    end endgenerate
    wire [33:0]  h_c0    = tq[trv[TQA-1:0]];
    wire [33:0]  h_c1    = tq[tr1v];
    wire [9:0]   h_c0_j  = (MUT == 3) ? {h_c0[9:2], h_c0[0], h_c0[1]} : h_c0[9:0];
    wire [9:0]   h_c1_j  = (MUT == 3) ? {h_c1[9:2], h_c1[0], h_c1[1]} : h_c1[9:0];
    wire [7:0]   h_c0_l  = h_c0[17:10] - 8'(ROW0);
    wire [7:0]   h_c1_l  = h_c1[17:10] - 8'(ROW0);
    wire [16:0]  e_sec_c0 = {h_c0_l[5:0], h_c0_j[9:7], 1'b0, h_c0_j[6:0]};
    wire [16:0]  e_sec_c1 = {h_c1_l[5:0], h_c1_j[9:7], 1'b0, h_c1_j[6:0]};
    // KVCTRL sched_s9 (PINREG): p_kv_v lands ONLY in its pin flop kvc_q.  Both lookahead candidates are registered
    // (es0/er0 = f(tq[tr]), es1/er1 = f(tq[tr + 1]) at the same edge as the s7b e_sec register) and the pin flop selects
    // between the two registers after the edge: e_sec = kvc_q ? es1 : es0 = the s7b register (kv_v ? c1 : c0) on every
    // edge (0 cycles).  s8 probe: p_kv_v capture 222.4 ps (> 190) on the 25-bit select fan-out before the flops.
    reg  [16:0]  es0, es1, e_sec_r;
    reg  [7:0]   er0, er1, e_row_r;
    always @(posedge hclk) begin
        e_sec_r <= kv_v ? e_sec_c1 : e_sec_c0; e_row_r <= kv_v ? h_c1[17:10] : h_c0[17:10];
        es0 <= e_sec_c0; es1 <= e_sec_c1; er0 <= h_c0[17:10]; er1 <= h_c1[17:10];
    end
    // s9 gate f8ca7be68 probe: with ONE pin flop (kvc_q also drives trv = the 64-entry tag-queue read address) the
    // output select launched at 251.7 ps on e_sec / e_row.  Two dedicated p_kv_v pin-flop copies (kept) drive only
    // the e_sec (17) and e_row (8) selects; kvc_q keeps the read pointer / tag check / idle veto.  p_kv_v: 3 flop loads.
    (* keep *) reg kvse_q, kvsr_q;
    always @(posedge hclk or negedge h_rn) if (!h_rn) begin kvse_q <= 1'b0; kvsr_q <= 1'b0; end
                                           else begin kvse_q <= kv_v; kvsr_q <= kv_v; end
`ifdef OT_SCHED_ESEC_MUT
    wire         esel = 1'b0, rsel = 1'b0;         // mutant: drops the late p_kv_v select (always the tq[tr] head)
`else
    wire         esel = kvse_q, rsel = kvsr_q;
`endif
    // KV-NATIVE sched_s10 (PINREG 2; routed native audit of s9 qkd_ctrl_pc_sched_s9-s9-623df1d3e, receipt
    // claude/native-batch-1017 029f539c5: launch e_sec[0..10] 243.1-245.8 > 220 = the 2:1 select AFTER the es0/es1
    // registers drove the pins): the select result is registered at the pin (e_sec_p / e_row_p) -> e_sec / e_row are the
    // s9 (= s7b) values exactly ONE hclk later.  The cycle is absorbed in the ECC child (qkd_ctrl_pc_ecc_child_sl), whose
    // section / row enter at its P1 stage instead of the P0 pin flops: the landed o_sec / o_row / o_v / o_data are
    // unchanged on every edge (0 cycles end to end).
    reg  [16:0]  e_sec_p;
    reg  [7:0]   e_row_p;
    always @(posedge hclk) begin e_sec_p <= esel ? es1 : es0; e_row_p <= rsel ? er1 : er0; end
    assign e_sec = (PINREG >= 2) ? e_sec_p : (PINREG != 0) ? (esel ? es1 : es0) : e_sec_r;
    assign e_row = (PINREG >= 2) ? e_row_p : (PINREG != 0) ? (rsel ? er1 : er0) : e_row_r;
    reg [15:0] ep0,ep1,ep2;
    always @(posedge hclk)begin ep0<=t_head[33:18];ep1<=ep0;ep2<=ep1;end
    assign corrected_epoch=ep2;
    assign co_c = {at_s[WDS], av_s[WDS], wcon_q, hand_q};
    // Dedicated raw PHY pin stage: all command and write-data bits move
    // together, preserving JEDEC spacings and CWL alignment. Physical static
    // completion and KV write retirement move with the actual launched column.
    reg [3:0] expected_sr_pipe;
    reg [327:0] po_r;
    reg [346:0] physical_context_r;
    reg         physical_col_sr_r;
    always @(posedge hclk or negedge h_rn)if(!h_rn)expected_sr_pipe<=0;else expected_sr_pipe<={expected_sr_pipe[2:0],reserved_static_col};
    always @(posedge hclk)physical_context_r<=col_context;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin po_r<=0;physical_col_sr_r<=0;end
      else begin po_r<={wd,col_col,col_bank,col_we,col_v,row_row,row_bank,row_op,row_v};physical_col_sr_r<=col_sr;end

    // ---- sticky fault chain, S -> N ----------------------------------------------------------------------------------
    // KVCTRL core_s7: the observer fault arrives from the obs child's fault register (its own logic one edge later).
    reg fo_r;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo_r <= 1'b0;
        else fo_r <= fo_r | fi | ctl_fault | port_fault | ecc_fault | hf_q | f_ecdc | f_late | f_cmd | f_early | f_wmis | f_tag | raw_bad | native_observer_fault;

    // KV corrected returns include tag, PHY raw, pcport and landing ECC
    // pipelines. Static reads are covered above through their actual e_v.
    reg [15:0] drain_kv;
    reg idle_hbm_r;
    // KVCTRL core_s6 (2026-10-16): the raw e_l_v pin left the activity veto (structural fix of core_s5 EARLY_FAIL_HOLD:
    // e_l_v -> l_v_q/D FF hold -17.17 ps was the ONE endpoint the CTS hold repair could not fix -- the port also fed this
    // combinational OR, so the flow gave it no input hold pad, and the repair could not buffer it). A legal landing always
    // has drain_kv >= 1 two edges before l_v (rd_kv precedes its landing by >= RL + PHY edges), so hbm_debt_zero_q already
    // vetoes idle_hbm on every edge the raw bit did; l_v (= e_l_v one edge later) stays in the veto. Cycle-identical for
    // all legal traffic; an unsolicited zero-debt landing still raises drain_fault_hbm and drops idle_hbm one edge later.
    // e_l_v now loads only its pin flop.
    wire hbm_drain_activity=obs_commit_valid||rd_kv||tc_v||cmd_v||static_v_q||c_v||s_cr||wv_q||cv_q||hand_q||
      wcon_q||row_v||col_v||po_r[0]||po_r[28]||rv_q||rawslot_q||kv_v||em_v||l_v||native_commit_valid;
    reg hbm_debt_zero_q;reg [1:0] hbm_quiet_q;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin hbm_debt_zero_q<=0;hbm_quiet_q<=0;end
      else begin
        hbm_debt_zero_q<=raw_out==0&&drain_kv==0&&hold==0&&dv==0&&av_s==0;
        hbm_quiet_q<={hbm_quiet_q[0],!hbm_drain_activity};
      end
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin drain_kv<=0;drain_fault_hbm<=0;idle_hbm_r<=0;end
      else begin
        case({rd_kv,l_v})
          2'b10:drain_kv<=drain_kv+16'd1;
          2'b01:drain_kv<=drain_kv-16'd1;
          default:;
        endcase
        if((l_v&&!rd_kv&&drain_kv==0)||
           (rd_kv&&!l_v&&drain_kv==16'hffff))drain_fault_hbm<=1;
        if(DRAIN_PIPE!=0)idle_hbm_r<=hgo&&ctl_phase_idle&&t_empty&&hbm_debt_zero_q&&
          (&hbm_quiet_q)&&!hbm_drain_activity&&!drain_fault_hbm&&!fo_r&&!f_ecdc;
        else idle_hbm_r<=hgo&&ctl_phase_idle&&t_empty&&raw_out==0&&drain_kv==0&&
          !tc_v&&!cmd_v&&!static_v_q&&!c_v&&!s_cr&&!wv_q&&!cv_q&&!hand_q&&
          hold==0&&!wcon_q&&dv==0&&av_s==0&&!row_v&&!col_v&&!po_r[0]&&!po_r[28]&&
          !rv_q&&!rawslot_q&&!kv_v&&!em_v&&!l_v&&!e_l_v&&!native_commit_valid&&!obs_commit_valid&&
          !drain_fault_hbm&&!fo_r&&!f_ecdc;
      end

    // ---- KVCTRL sched_s8 (PINREG): flop-first pins -------------------------------------------------------------------
    // s7b classification (routed s7b view, TT): every po / ko output was flop-driven, but the flop sat at the FAR face
    // (po = p_wd E -> S and ko = ki N -> S feed-throughs through one register; S-face pin-flop columns over capacity),
    // behind the 3-cell outhold chain (~75 ps); c_d[255:0] reached its single register (p_w_d at E) over ~100 um of N -> E
    // wire behind an inhold pad; the single-pin captures (c_v, p_kv_v, p_em_v, obs_commit_valid, native_commit_valid,
    // f_ecdc, p_fault, e_fault, fi, native_observer_fault) fed the idle_hbm veto / fo OR trees (3-5 gates) before a flop.
    // Successor: (1) feed-throughs get a register at each face -- the s7b register stays as the input pin flop and a new
    // output pin register re-times it (po, p_w_d, ko, and physical_context / physical_col_sr / expected_sr with po so
    // every observer sees the launched column on the same edge as before); (2) fo / idle_hbm / p_w_v are computed one
    // edge later from pin flops of their raw inputs and plain registers of their internal terms (D-form: exactly the
    // s7b register delayed one edge).  p_kv_v keeps only its 0-cycle select of the e_sec / e_row lookahead (the ECC child
    // captures the port beat and e_sec on the same edge): it leaves the idle veto, the tag check (D(f_tag)) and the read
    // pointer (trv).  ki lands only in the tap's o_v / o_d pin flops; the tap command is decoded after them (0 cycles).
    // Gate 374e1e726 CTS probe: launch max 99 ps (was 308.9); capture over on p_kv_v 256 (tr counter) and ki 223 (tap
    // decode) -> both moved behind pin flops here.
    generate if (PINREG != 0) begin : g_pin
        // pin flops of raw inputs (plain registers: D(x))
        (* keep *) reg c_v_q, cw_q, em_v_q, obs_q, nat_q, fi_q, pf_q, ef_q, fe_q, nof_q;
        wire kv_v_q = kvs;                         // sched_s9: the one p_kv_v pin flop (kvc_q)
        always @(posedge hclk) begin
            c_v_q <= c_v; cw_q <= c_d[286]; em_v_q <= em_v; obs_q <= obs_commit_valid;
            nat_q <= native_commit_valid; fi_q <= fi; pf_q <= port_fault; ef_q <= ecc_fault; fe_q <= f_ecdc;
            nof_q <= native_observer_fault;
        end
        // plain registers of internal terms (all registers or logic of registers in s7b)
        reg ftag_a_d, ftag_e_d, f_tag_d;
        reg h_rn_d, hgo_d, fint_d, cmd_a_d, cmd_b_d, early_d, act_int_d, gate_d, hdz_d, dfh_d;
        wire cmd_a = (cmd_v && cr == 4'd0) || ((static_owner_q && (tc_v || w_pend)) || (!static_owner_q && static_v_q)) ||
                     (static_owner_q != static_owner_d && (!ctl_phase_idle || tw != trv || cv_q || wv_q));
        wire act_int = rd_kv || tc_v || cmd_v || static_v_q || s_cr || wv_q || cv_q || hand_q || wcon_q || row_v || col_v ||
                       po_r[0] || po_r[28] || rv_q || rawslot_q || l_v;
        always @(posedge hclk) begin
            h_rn_d <= h_rn; hgo_d <= hgo;
            fint_d <= ctl_fault | hf_q | f_late | f_wmis | raw_bad;
            ftag_a_d <= rd_kv && t_full; ftag_e_d <= t_empty;
            cmd_a_d <= cmd_a; cmd_b_d <= static_owner_q != static_owner_d;
            early_d <= !hgo && (tc_v || static_v_q);
            act_int_d <= act_int;
            gate_d <= hgo && ctl_phase_idle && t_empty;
            hdz_d <= hbm_debt_zero_q; dfh_d <= drain_fault_hbm;
        end
        // D(f_cmd), D(f_early): the s7b sticky checks one edge later (their raw c_v term from its pin flop)
        reg f_cmd_d, f_early_d;
        always @(posedge hclk or negedge hgo_d)
            if (!hgo_d) f_cmd_d <= 1'b0; else if (cmd_a_d || (cmd_b_d && c_v_q)) f_cmd_d <= 1'b1;
        always @(posedge hclk or negedge h_rn_d)
            if (!h_rn_d) f_early_d <= 1'b0; else if (early_d || (!hgo_d && c_v_q)) f_early_d <= 1'b1;
        // D(f_tag): the tag check one edge later (its raw p_kv_v term from the pin flop)
        always @(posedge hclk or negedge h_rn_d)
            if (!h_rn_d) f_tag_d <= 1'b0; else if (ftag_a_d || (kv_v_q && ftag_e_d)) f_tag_d <= 1'b1;
        // D(fo): fault chain output register at the N pin
        reg fo_p;
        always @(posedge hclk or negedge h_rn_d)
            if (!h_rn_d) fo_p <= 1'b0;
            else fo_p <= fo_p | fi_q | pf_q | ef_q | fe_q | nof_q | fint_d | f_tag_d | f_cmd_d | f_early_d;
        // D(idle_hbm) (DRAIN_PIPE form): veto from the pin flops + the registered internal activity
        reg [1:0] hq_p;
        reg idle_p;
        wire act_d = act_int_d || c_v_q || kv_v_q || em_v_q || obs_q || nat_q;
        always @(posedge hclk or negedge h_rn_d)
            if (!h_rn_d) begin hq_p <= 2'd0; idle_p <= 1'b0; end
            else begin
                hq_p <= {hq_p[0], !act_d};
`ifdef OT_SCHED_PINREG_MUT
                idle_p <= gate_d && hdz_d && (&hq_p) && !(act_int_d || c_v_q || kv_v_q || obs_q || nat_q) && !dfh_d && !fo_p && !fe_q;
`else
                idle_p <= gate_d && hdz_d && (&hq_p) && !act_d && !dfh_d && !fo_p && !fe_q;
`endif
            end
        // D(p_w_v) from pin flops; output pin registers of the feed-throughs and the launched-column observations
        reg p_w_v_p;
        always @(posedge hclk or negedge h_rn_d) if (!h_rn_d) p_w_v_p <= 1'b0; else p_w_v_p <= c_v_q && cw_q;
        reg [327:0] po_p;
        reg [255:0] p_w_d_p;
        reg [346:0] pctx_p;
        reg         pcsr_p, esr_p;
        reg [32:0]  ko_p;
        always @(posedge hclk) begin
            po_p <= po_r; p_w_d_p <= p_w_d_r; pctx_p <= physical_context_r; pcsr_p <= physical_col_sr_r;
            esr_p <= expected_sr_pipe[3]; ko_p <= ko_r;
        end
        assign po = po_p; assign p_w_v = p_w_v_p; assign p_w_d = p_w_d_p; assign physical_context = pctx_p;
        assign physical_col_sr = pcsr_p; assign expected_sr = esr_p; assign ko = ko_p;
        reg idle_hbm_d;   // DRAIN_PIPE 0: plain D(idle_hbm) (not flop-first; the production kit uses DRAIN_PIPE 1)
        always @(posedge hclk) idle_hbm_d <= idle_hbm_r;
        assign fo = fo_p; assign idle_hbm = DRAIN_PIPE != 0 ? idle_p : idle_hbm_d;
    end else begin : g_s7b
        assign po = po_r; assign p_w_v = p_w_v_r; assign p_w_d = p_w_d_r; assign physical_context = physical_context_r;
        assign physical_col_sr = physical_col_sr_r; assign expected_sr = expected_sr_pipe[3]; assign ko = ko_r;
        assign fo = fo_r; assign idle_hbm = idle_hbm_r;
    end endgenerate
endmodule
// KVCTRL core_s7 (lead Q-KV 2026-10-17): CDC child -- the embedding static crossing u_ecdc (both clocks), the core-clock
// intake pin flops / native intake check, the core-domain drain counters / idle_core, the er response registers and the
// static column completion crossing. Pins are flop-first: the embedding return (p_em_v / p_em_d) and the u_ctl credit
// (s_cr) are captured in pin registers before the FIFO write (+1 hclk each); the down-FIFO outputs leave through output
// registers c_v / c_d / c_context (+1 hclk on the static command into u_ctl). Everything else is the core_s6 logic.
module qkd_ctrl_pc_cdc_child #(
    parameter integer CORE_CLOCK = 0,
    parameter integer WDONE = CORE_CLOCK ? 19 : 17,
    parameter integer PROFILE = 0,
    parameter integer EVMUT = 0,
    parameter integer STRAP_CDC = 0,
    parameter integer DRAIN_PIPE = 0
) (
    input  wire         pll_hbm,
    input  wire         hrst,
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    input  wire [4:0]   pc_q,                          // sched hclk strap register
    input  wire [287:0] es,
    output wire [260:0] er,
    input wire [1:0] cfg_stack,
    input wire [317:0] es_context,
    input wire es_expected_valid,input wire [60:0] es_expected_identity,
    input wire [28:0] es_expected_address,input wire [4:0] es_expected_pc,input wire [1:0] es_expected_stack,
    output wire completion_v,completion_we,completion_fault,
    output reg idle_core,output reg drain_fault_core,
    input  wire         s_cr,                          // sched u_ctl credit register
    input  wire         p_em_v,                        // port child embedding return
    input  wire [257:0] p_em_d,
    output reg          c_v,                           // -> sched (registered)
    output reg  [286:0] c_d,
    output reg  [61:0]  c_context,
    output wire         f_ecdc,
    input  wire         col_v, col_we, col_sr          // sched po[28] / po[29] / physical_col_sr registers
);
    wire hclk = pll_hbm;
    (* keep *) reg hr_q;
    (* keep *) reg rs_q;
    always @(posedge hclk) hr_q <= hrst;
    always @(posedge ck)   rs_q <= rsi;
    wire h_rn = hr_q;
    // pin registers (flop-first): u_ctl credit and the embedding return beat
    (* keep *) reg s_cr_q, em_v_q;
    (* keep *) reg [257:0] em_d_q;
    always @(posedge hclk or negedge h_rn) if(!h_rn)begin s_cr_q<=1'b0;em_v_q<=1'b0;end else begin s_cr_q<=s_cr;em_v_q<=p_em_v;end
    always @(posedge hclk) em_d_q<=p_em_d;
    // ---- embedding static port crossing (strip engine on the core clock) ---------------------------------------------
    (* keep *) reg         es_v_q;
    (* keep *) reg [286:0] es_d_q;
    (* keep *) reg [317:0] es_context_q;
    (* keep *) reg es_expected_q;
    (* keep *) reg [60:0] es_expected_identity_q;
    (* keep *) reg [28:0] es_expected_address_q;
    (* keep *) reg [4:0] es_expected_pc_q,pc_core_q;
    (* keep *) reg [4:0] pc_core_meta;
    (* keep *) reg [1:0] stack_q,es_expected_stack_q;
    reg native_intake_fault;
    always @(posedge ck)begin
      es_context_q<=es_context;es_expected_identity_q<=es_expected_identity;
      es_expected_address_q<=es_expected_address;es_expected_pc_q<=es_expected_pc;
      es_expected_stack_q<=es_expected_stack;stack_q<=cfg_stack;
      pc_core_meta<=pc_q;pc_core_q<=(STRAP_CDC!=0)?pc_core_meta:pc;
    end
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin es_expected_q<=0;native_intake_fault<=0;end
      else begin
        es_expected_q<=es_expected_valid;
        if(PROFILE==0 && ((es_v_q&&es_context_q[317])!=es_expected_q))native_intake_fault<=1;
        if(es_v_q&&es_context_q[317] && (es_context_q[316:256]!=es_expected_identity_q ||
          es_context_q[255:0]!={256{1'b1}} || !es_d_q[286] || !es_d_q[285] ||
          {es_d_q[274:256],es_d_q[284:280],es_d_q[279:275]}!=es_expected_address_q ||
          pc_core_q!=es_expected_pc_q || stack_q!=es_expected_stack_q))native_intake_fault<=1;
      end
    always @(posedge ck or negedge rs_q) if (!rs_q) es_v_q <= 1'b0; else es_v_q <= es[0];
    always @(posedge ck) es_d_q <= es[287:1];
    wire         e_v, s_credit, f_core;
    wire [257:0] e_d;
    wire         c_v_w;
    wire [286:0] c_d_w;
    wire [61:0]  c_context_w;
    ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (
        .clk(ck), .rst_n(rs_q), .hclk(hclk), .hrst_n(h_rn), .s_v(es_v_q), .s_d(es_d_q),.s_context(es_context_q[317:256]), .c_v(c_v_w), .c_d(c_d_w),.c_context(c_context_w),
        .h_credit(s_cr_q), .s_credit(s_credit), .h_v(em_v_q), .h_d(em_d_q), .e_v(e_v), .e_d(e_d),
        .fault_core(f_core), .fault_hbm(f_ecdc));
    // down-FIFO output registers (the FIFO read mux never reaches a pin)
    always @(posedge hclk or negedge h_rn) if(!h_rn) c_v<=1'b0; else c_v<=c_v_w;
    always @(posedge hclk) begin c_d<=c_d_w; c_context<=c_context_w; end
    reg          er_v, er_cr, er_f;
    reg  [257:0] er_d;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin er_v <= 1'b0; er_cr <= 1'b0; er_f <= 1'b0; end
        else begin er_v <= e_v; er_cr <= s_credit; er_f <= f_core | native_intake_fault; end
    always @(posedge ck) er_d <= e_d;
    assign er = {er_f, er_cr, er_d, er_v};
    qkd_ctrl_static_commit #(.WDONE(WDONE),.MUT(EVMUT)) u_static_commit(
        .hclk(hclk),.hrst_n(h_rn),.ck(ck),.rst_n(rs_q),
        .col_v(col_v),.col_we(col_we),.col_sr(col_sr),
        .completion_v(completion_v),.completion_we(completion_we),.fault(completion_fault));
    // ---- actual outstanding work observations (not execution/admission gates) ----
    reg [15:0] drain_desc,drain_reads,drain_credits;
    wire dc_push=es_v_q,dc_pop=completion_v;
    wire dr_push=es_v_q&&!es_d_q[285],dr_pop=e_v;
    wire dq_push=es_v_q,dq_pop=s_credit;
    wire core_drain_activity_q=es_v_q||completion_v||e_v||er_v||s_credit||er_cr;   // all but the raw es[0] pin
    wire core_drain_activity=core_drain_activity_q;
    // cdc_s7c (Q-KVELEM2 2026-10-17): idle_core is ONE export flop. cdc_s7b exported idle_core_r && !es0_idle_q (an AND
    // after two flops, both async-cleared by rs_q and loaded on the same ck edge): native launch 225.1 > 220 on that pin.
    // The flop now registers the same AND of the two next states, idle_next && !es[0], so on every edge
    //   idle_core(t+1) = idle_next(t) && !es[0](t) = idle_core_r(t+1) && !es0_idle_q(t+1)   (both reset to 0)
    // i.e. 0 cycles, bit-identical at the pin (bench tb_cdc_idle_export_equiv vs the s7b reference). The raw es[0] pin
    // passes one gate (the keep boundary below) before the flop; es[0] still loads the es_v_q pin flop.
    (* keep *) wire idle_next;
`ifdef OT_CDC_IDLE_EXPORT_MUT
    wire es0_veto = 1'b0;           // mutant: the es[0] same-edge veto is dropped (s7b would drop idle_core here)
`else
    wire es0_veto = es[0];
`endif
    reg core_debt_zero_q;reg [1:0] core_quiet_q;
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin core_debt_zero_q<=0;core_quiet_q<=0;end
      else begin
        core_debt_zero_q<=drain_desc==0&&drain_reads==0&&drain_credits==0;
        core_quiet_q<={core_quiet_q[0],!core_drain_activity};
      end
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin
        drain_desc<=0;drain_reads<=0;drain_credits<=0;
        drain_fault_core<=0;idle_core<=0;
      end else begin
        case({dc_push,dc_pop})
          2'b10:drain_desc<=drain_desc+16'd1;
          2'b01:drain_desc<=drain_desc-16'd1;
          default:;
        endcase
        case({dr_push,dr_pop})
          2'b10:drain_reads<=drain_reads+16'd1;
          2'b01:drain_reads<=drain_reads-16'd1;
          default:;
        endcase
        case({dq_push,dq_pop})
          2'b10:drain_credits<=drain_credits+16'd1;
          2'b01:drain_credits<=drain_credits-16'd1;
          default:;
        endcase
        if((dc_pop&&!dc_push&&drain_desc==0)||
           (dr_pop&&!dr_push&&drain_reads==0)||
           (dq_pop&&!dq_push&&drain_credits==0)||
           (dc_push&&!dc_pop&&drain_desc==16'hffff)||
           (dr_push&&!dr_pop&&drain_reads==16'hffff)||
           (dq_push&&!dq_pop&&drain_credits==16'hffff))drain_fault_core<=1;
        idle_core<=idle_next&&!es0_veto;
      end
    assign idle_next=(DRAIN_PIPE!=0)?
        (core_debt_zero_q&&(&core_quiet_q)&&!core_drain_activity_q&&
         !drain_fault_core&&!completion_fault&&!f_core&&!native_intake_fault):
        (drain_desc==0&&drain_reads==0&&drain_credits==0&&
         !es_v_q&&!completion_v&&!e_v&&!er_v&&!s_credit&&!er_cr&&
         !drain_fault_core&&!completion_fault&&!f_core&&!native_intake_fault);
endmodule

// KVCTRL core_s7: observer child -- the native write observer behind input pin registers (po / context / static column /
// expected static column all delayed by the same one hclk edge, so the observer's internal alignment is unchanged) and
// the native commit output pin registers. Observation +1 hclk vs core_s6 (observation only; no traffic edge).
module qkd_ctrl_pc_obs_child #(parameter integer PROFILE = 0, CORE_CLOCK = 0)(
    input  wire         pll_hbm,
    input  wire         hrst,
    input  wire [327:0] po,
    input  wire         static_column,
    input  wire         expected_static_column,
    input  wire [346:0] context_word,
    output wire         obs_commit_valid,
    output wire         native_commit_valid,
    output wire [60:0]  native_commit_identity,
    output wire [28:0]  native_commit_address,
    output wire         fault
);
    wire hclk = pll_hbm;
    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    wire h_rn = hr_q;
    (* keep *) reg [327:0] po_q;
    (* keep *) reg [346:0] ctx_q;
    (* keep *) reg sc_q, esc_q;
    always @(posedge hclk or negedge h_rn) if(!h_rn)begin po_q<=0;sc_q<=0;esc_q<=0;end else begin po_q<=po;sc_q<=static_column;esc_q<=expected_static_column;end
    always @(posedge hclk) ctx_q<=context_word;
    wire [60:0] obs_commit_identity; wire [28:0] obs_commit_address;
    qkd_static_kv_write_observer #(.STRICT(PROFILE==0),.WL(CORE_CLOCK ? 7 : 5)) u_native_write_observer(
        .hclk(hclk),.rst_n(h_rn),.po(po_q),.static_column(sc_q),.expected_static_column(esc_q),.context_word(ctx_q),
        .commit_valid(obs_commit_valid),.commit_identity(obs_commit_identity),.commit_address(obs_commit_address),.fault(fault));
    (* keep *) reg nc_v_q;(* keep *) reg [60:0] nc_id_q;(* keep *) reg [28:0] nc_ad_q;
    always @(posedge hclk or negedge h_rn)if(!h_rn)nc_v_q<=1'b0;else nc_v_q<=obs_commit_valid;
    always @(posedge hclk)begin nc_id_q<=obs_commit_identity;nc_ad_q<=obs_commit_address;end
    assign native_commit_valid=nc_v_q;assign native_commit_identity=nc_id_q;assign native_commit_address=nc_ad_q;
endmodule
