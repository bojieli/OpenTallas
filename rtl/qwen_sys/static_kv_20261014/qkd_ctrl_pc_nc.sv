`timescale 1ns/1ps
// KV-PLAN-CI 2026-10-17 (coordinator decision 3): the static controller WITHOUT the legacy controller command / KV-write
// word ci (319 b, the old qkd_cdc_wleaf ho: h_cred / h_wv / h_wsec / h_cv / h_csec / h_cdata / h_ctag / hf).  On the
// static die nothing produces ci (the write leaf / write queue are gone): static KV and boot writes arrive on es ->
// u_cdc -> c_d -> p_w_v / p_w_d (col_sr columns), commands come from the kc chain (ki) before the calendar takes
// ownership and from the calendar after.  The legacy write path is REMOVED logic here, not a tied input:
//   qkd_ctrl_pc_sched_nc       = qkd_ctrl_pc_sched minus ci_c / co_c: no W-face pin flops, no w_pend / w_go write
//                                command (open-row match, HOFF hold, LATE watchdog), no h_wcon / KV completion check
//                                (f_wmis) / write-done (av_s / at_s), no hf; drain and idle drop those terms.
//   ot_qfd_emb_pcport_nkw      = ot_qfd_emb_pcport KVW 2 minus kw_v / kw_d: a KV WR column (col_we && !col_sr, only a
//                                compiled type-2 command can make one) has no data source, so it faults as the KVW 2
//                                port does with kw_v low, and its PHY write data is the KVW 2 kenc(0) = 0.
//   qkd_ctrl_pc_port_child_nc  = qkd_ctrl_pc_port_child minus kw_vi / kw_di and their pin flops (cv_q / cdata_q).
//   qkd_ctrl_pc_host_static_nc = qkd_ctrl_pc_host_static (wires only) minus ci; co is co[281:0] (ECC child only): the
//                                co[293:282] pass fields {at, av, wcon, hand} fed only the legacy leaf.
// The ci-ful modules (and their closed views) are unchanged.  Lockstep proof: tools/qwen_kv_die/kvplan_ci_nc_gate.sh
// (variant vs original with ci held 0, every output every edge, mutants observed).
module qkd_ctrl_pc_sched_nc #(
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
    input  wire [4:0]   pc,
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

    // ---- (nc) no W face: the legacy KV-write word ci (qkd_cdc_wleaf ho) and its pin flops are removed ----------------

    // ---- E-face pin flops (PHY return) -------------------------------------------------------------------------------
    (* keep *) reg         rv_q,rawslot_q;
    (* keep *) reg [15:0] epoch_q;
    always @(posedge hclk)epoch_q<=static_epoch;
    always @(posedge hclk or negedge h_rn)if(!h_rn)rawslot_q<=0;else rawslot_q<=expected_raw_valid;
    always @(posedge hclk or negedge h_rn) if (!h_rn) rv_q <= 1'b0; else rv_q <= pi_v;

    // ---- KV-TOK B 2026-10-24: controller BOOT WINDOW ------------------------------------------------------------------
    // Maintenance mode before mission mode (as a memory controller's init / BIST phase). From the scheduler's reset until
    // the HBM calendar first takes ownership of this PC (static_cmd_owner: set by the first compiled layer go, never
    // cleared) the static queue head's column issues as soon as it is JEDEC-legal, without a calendar reservation. This
    // is what the destructive cold-boot scratch check (qkd_hbm_boot_pc: WR, RD, WR, RD of one reserved sector, issued
    // while the die is held in reset) needs: the calendar image that would reserve its columns is in the boot image,
    // which loads only after the die leaves reset, which the HOST does only after every slice's check passed.
    // The window closes on the first ownership edge and never reopens, so the compiled static schedule is unchanged:
    // every later column needs its reservation exactly as before (lockstep vs the original controller,
    // tools/qwen_kv_die/kv_boot_window_gate.sh). Ownership needs an idle controller (f_cmd), so no boot column is in
    // flight when it closes. A boot column carries the observations a reserved one gets from the calendar: the write
    // observer's expected static column (expected_sr) and, for a boot read, the elastic raw-return nominal slot RAW =
    // PHYSICAL_CMD_EDGES 4 + HBM_RL 23 edges after its virtual reservation (qkd_static_kv_return_calendar), i.e. BRAW
    // edges after u_ctl's col_boot register (reservation R -> sched srslot_q R+1 -> u_ctl srslot_q R+2 -> col R+3).
    localparam integer BRAW = 4 + (CORE_CLOCK ? 29 : 23) + 1 - 3;
    reg boot_win;
    reg [BRAW-1:0] boot_raw;
    wire col_boot;
    localparam integer TQA = $clog2(TQD);
    reg [6:0] raw_out;               // nominal raw returns not yet received (<= TQD outstanding tags)
    reg [8:0] raw_age;
    reg f_raw;
    // KV-TOK B: the nominal raw slot is the calendar's (rawslot_q) or, in the boot window, a boot static read's own
    // nominal slot (boot_raw, the same RAW edges after its virtual reservation; see BOOT WINDOW below). The two are
    // exclusive (the window closes before the calendar can reserve); with the window closed boot_raw is 0.
    wire raw_nom = rawslot_q | boot_raw[BRAW-1];
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin raw_out <= 6'd0; raw_age <= 9'd0; f_raw <= 1'b0; end
        else if (ELASTIC != 0) begin
            raw_out <= raw_out + {6'd0, raw_nom} - {6'd0, rv_q};
            if (rv_q && raw_out == 7'd0 && !raw_nom) f_raw <= 1'b1;             // earlier than nominal / unsolicited
            if (raw_out == 7'(TQD) && raw_nom && !rv_q) f_raw <= 1'b1;          // outstanding count overflow
            if (rv_q || raw_out == 7'd0) raw_age <= 9'd0;
            else if (raw_age == 9'(RAW_WD - 1)) f_raw <= 1'b1;                  // PHY late beyond watchdog
            else raw_age <= raw_age + 9'd1;
        end
    wire raw_bad = (ELASTIC == 0) ? (rv_q != raw_nom) : f_raw;

    // ---- command arbiter ---------------------------------------------------------------------------------------------
    wire [346:0] col_context;
    reg  [3:0]  cr;
    reg         f_cmd, f_early;
    wire        cmd_credit,ctl_phase_idle;
    reg static_owner_d;
    always @(posedge hclk or negedge h_rn)if(!h_rn)static_owner_d<=0;else static_owner_d<=static_owner_q;
    // (nc) the legacy write path (w_pend / w_go: wq write command, its open-row match, hand-off hold, late watchdog) is
    // removed with its ci producer: before ownership only the kc chain (ki) issues, after it only the calendar.
    (* keep *) reg static_owner_q,static_v_q,rdslot_q,srslot_q,wrslot_q;
    (* keep *) reg [31:0] static_d_q;
    (* keep *) reg [9:0] static_first_q;
    always @(posedge hclk)begin static_d_q<=static_cmd[32:1];static_first_q<=static_cmd[42:33];end
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin static_owner_q<=0;static_v_q<=0;rdslot_q<=0;srslot_q<=0;wrslot_q<=0;end
      else begin static_owner_q<=static_cmd_owner;static_v_q<=static_cmd[0];rdslot_q<=reserved_rd;srslot_q<=reserved_static_col;wrslot_q<=reserved_write_col;end
    always @(posedge hclk or negedge h_rn) if (!h_rn) boot_win <= 1'b1; else if (static_owner_q) boot_win <= 1'b0;
    wire        cmd_v  = static_owner_q ? static_v_q : tc_v;
    wire [31:0] cmd    = static_owner_q ? static_d_q : tc_d;
    always @(posedge hclk or negedge hgo)
        if (!hgo) begin
            cr <= 4'd8; f_cmd <= 1'b0;
        end else begin
            cr <= cr - {3'd0, cmd_v} + {3'd0, cmd_credit};
            if (cmd_v && cr == 4'd0) f_cmd <= 1'b1;
            if((static_owner_q&&tc_v)||(!static_owner_q&&static_v_q))f_cmd<=1'b1;
            if(static_owner_q!=static_owner_d && (!ctl_phase_idle||tw!=tr||c_v))f_cmd<=1'b1;
        end
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
        .clk(hclk), .rst_n(hgo), .cmd_v(cmd_v), .cmd(cmd), .cmd_first(static_owner_q?static_first_q:10'd0),.reserved_rd(rdslot_q),.reserved_static_col(srslot_q),.reserved_write_col(wrslot_q),.boot_window(boot_win),.col_boot(col_boot), .cmd_credit(cmd_credit),
        .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),
        .col_v(col_v), .col_bank(col_bank), .col_col(col_col), .col_we(col_we), .busy(), .phase_idle(ctl_phase_idle), .fault(ctl_fault),
        .s_context({c_context,c_d[274:256],c_d[284:280],c_d[279:275],c_d[255:0]}),.col_context(col_context),.s_v(c_v), .s_we(c_d[285]), .s_bank(c_d[284:280]), .s_col(c_d[279:275]), .s_row(c_d[274:256]),
        .s_cr(s_cr), .col_sr(col_sr));

    // ---- the delayed column of the pcport ((nc) no h_wcon / KV completion check / write-done: no legacy write leaf) --
    reg  [LW:0] dv, dwe, dsr;                     // [0] = one edge after the pin column ... [LW-1] = the pcport's
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin dv <= 0; dwe <= 0; dsr <= 0; end
        else begin
            dv <= {dv[LW-1:0], col_v}; dwe <= {dwe[LW-1:0], col_we}; dsr <= {dsr[LW-1:0], col_sr};
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
    // Dedicated raw PHY pin stage: all command and write-data bits move
    // together, preserving JEDEC spacings and CWL alignment. Physical static
    // completion and KV write retirement move with the actual launched column.
    // KV-TOK B: expected_sr is ONE flop: the reservation 4 edges late (was expected_sr_pipe[3]) or a boot column one
    // edge late (aligned with physical_col_sr <= col_sr); boot_raw delays a boot READ column to its nominal raw slot.
    reg [2:0] expected_sr_pipe;
    reg expected_sr_q;
    assign expected_sr=expected_sr_q;
    always @(posedge hclk or negedge h_rn)if(!h_rn)begin expected_sr_pipe<=0;expected_sr_q<=0;boot_raw<=0;end
      else begin expected_sr_pipe<={expected_sr_pipe[1:0],reserved_static_col};expected_sr_q<=expected_sr_pipe[2]|col_boot;
        boot_raw<={boot_raw[BRAW-2:0],col_boot&&!col_we};end
    always @(posedge hclk)physical_context<=col_context;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin po<=0;physical_col_sr<=0;end
      else begin po<={wd,col_col,col_bank,col_we,col_v,row_row,row_bank,row_op,row_v};physical_col_sr<=col_sr;end

    // ---- sticky fault chain, S -> N ----------------------------------------------------------------------------------
    // KVCTRL core_s7: the observer fault arrives from the obs child's fault register (its own logic one edge later).
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo <= 1'b0;
        else fo <= fo | fi | ctl_fault | port_fault | ecc_fault | f_ecdc | f_cmd | f_early | f_tag | raw_bad | native_observer_fault;

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
    wire hbm_drain_activity=obs_commit_valid||rd_kv||tc_v||cmd_v||static_v_q||c_v||s_cr||
      row_v||col_v||po[0]||po[28]||rv_q||rawslot_q||(|boot_raw)||kv_v||em_v||l_v||native_commit_valid;
    reg hbm_debt_zero_q;reg [1:0] hbm_quiet_q;
    always @(posedge hclk or negedge h_rn)
      if(!h_rn)begin hbm_debt_zero_q<=0;hbm_quiet_q<=0;end
      else begin
        hbm_debt_zero_q<=raw_out==0&&drain_kv==0&&dv==0;
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
          !tc_v&&!cmd_v&&!static_v_q&&!c_v&&!s_cr&&
          dv==0&&!row_v&&!col_v&&!po[0]&&!po[28]&&
          !rv_q&&!rawslot_q&&!(|boot_raw)&&!kv_v&&!em_v&&!l_v&&!e_l_v&&!native_commit_valid&&!obs_commit_valid&&
          !drain_fault_hbm&&!fo&&!f_ecdc;
      end
endmodule

// PC port child without the legacy KV write data pins (see the header): pin flops of the column / static write data /
// PHY read data exactly as qkd_ctrl_pc_port_child.
module qkd_ctrl_pc_port_child_nc #(
    parameter integer RQD = 64,
    parameter integer MUT = 0
) (
    input  wire         hclk,
    input  wire         hrst,
    input  wire         col_v_e, col_we_e, col_sr_e,   // one edge early
    input  wire         w_v,
    input  wire [255:0] w_d,
    input  wire [288:0] pi,
    output wire [287:0] wd,
    output wire         kv_v,
    output wire [287:0] kv_d,
    output wire         em_v,
    output wire [257:0] em_d,
    output wire         fault
);
    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    wire h_rn = hr_q;
    (* keep *) reg rv_q, col_v_q, col_we_q, col_sr_q;
    (* keep *) reg [287:0] rd_q;
    (* keep *) reg w_v_q;
    (* keep *) reg [255:0] w_d_q;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin rv_q <= 1'b0; col_v_q <= 1'b0; col_we_q <= 1'b0; col_sr_q <= 1'b0; w_v_q <= 1'b0; end
        else begin rv_q <= pi[0]; col_v_q <= col_v_e; col_we_q <= col_we_e; col_sr_q <= col_sr_e; w_v_q <= w_v; end
    always @(posedge hclk) begin rd_q <= pi[288:1]; w_d_q <= w_d; end
    ot_qfd_emb_pcport_nkw #(.RQD(RQD), .MUT(MUT)) u_port (
        .clk(hclk), .rst_n(h_rn), .col_v(col_v_q), .col_we(col_we_q), .col_sr(col_sr_q),
        .w_v(w_v_q), .w_d(w_d_q), .wd(wd),
        .r_v(rv_q), .r_d(rd_q), .kv_v(kv_v), .kv_d(kv_d), .em_v(em_v), .em_d(em_d), .fault(fault));
endmodule

// ot_qfd_emb_pcport (rtl/qwen_sys/emb_hbm_20261008/synth) at KVW 2 without the KV write data port kw_v / kw_d.
// Class FIFO, embedding SECDED decode, static write FIFO and the KVW 2 wd timing (every WR's PHY write data two edges
// after its column) are identical.  MUT 3 (bench mutant): the correction is skipped.
module ot_qfd_emb_pcport_nkw #(
    parameter integer RQD = 32,
    parameter integer WQD = 4,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         col_v,
    input  wire         col_we,
    input  wire         col_sr,
    input  wire         w_v,
    input  wire [255:0] w_d,
    output wire [287:0] wd,
    input  wire         r_v,
    input  wire [287:0] r_d,
    output reg          kv_v,
    output reg  [287:0] kv_d,
    output reg          em_v,
    output reg  [257:0] em_d,             // {ue, ce, data}
    output reg          fault
);
  // ---- SECDED(72,64): ot_gpu_w6_secded_pkg layout (Hamming positions 1..71, check bits at 2^k, overall parity bit 71)
  function automatic [71:0] enc64(input [63:0] data);
    reg [71:0] c; integer p, k, j;
    begin
      c = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
      for (k = 0; k < 7; k = k + 1)
        for (p = 1; p <= 71; p = p + 1)
          if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
      c[71] = ^c[70:0]; enc64 = c;
    end
  endfunction
  function automatic [287:0] enc256(input [255:0] d);
    enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
  endfunction
  // decode stage A: {syndrome[6:0], overall parity}
  function automatic [7:0] syn64(input [71:0] code);
    reg [6:0] sy; integer p, k;
    begin
      sy = '0;
      for (k = 0; k < 7; k = k + 1)
        for (p = 1; p <= 71; p = p + 1)
          if ((p & (1 << k)) != 0) sy[k] = sy[k] ^ code[p-1];
      syn64 = {sy, ^code};
    end
  endfunction
  // decode stage B: {ue, corrected, data[63:0]} from the code and its stage-A syndrome
  function automatic [65:0] cor64(input [71:0] code, input [7:0] so);
    reg [71:0] c; reg [6:0] sy; reg ov, ue, ce; reg [63:0] d; integer p, j;
    begin
      c = code; sy = so[7:1]; ov = so[0]; ue = 1'b0; ce = 1'b0;
      if (sy != 0) begin
        if (ov && sy <= 71) begin c[sy-1] = ~c[sy-1]; ce = 1'b1; end
        else ue = 1'b1;
      end else if (ov) begin c[71] = ~c[71]; ce = 1'b1; end
      d = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin d[j] = c[p-1]; j = j + 1; end
      cor64 = {ue, ce, d};
    end
  endfunction

    localparam integer RA = $clog2(RQD);
    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;
    reg [RQD-1:0] kq;
    reg [RA:0] kw, kr;
    reg [287:0] wq [0:WQD-1];
    reg [WA:0] ww, wr;
    wire rd_issue = col_v && !col_we;
    wire wr_static = col_v && col_we && col_sr;
    wire wr_kv = col_v && col_we && !col_sr;      // no KV write data source: a KV WR column is a fault
    wire k_empty = kw == kr;
    wire k_full = (kw[RA-1:0] == kr[RA-1:0]) && (kw[RA] != kr[RA]);
    wire w_empty = ww == wr;
    wire w_full = (ww[WA-1:0] == wr[WA-1:0]) && (ww[WA] != wr[WA]);
    wire cls = kq[kr[RA-1:0]];
    // KVW 2 timing: wd two edges after every WR column
    reg wc1_kv, wc1_st; reg [287:0] st1_wd, s2_wd;
    assign wd = s2_wd;
    always @(posedge clk) begin
        if (wr_static) st1_wd <= wq[wr[WA-1:0]];
        if (wc1_kv) s2_wd <= 288'd0; else if (wc1_st) s2_wd <= st1_wd;
    end
    reg v1; reg [287:0] c1; reg [31:0] y1;
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            kw <= 0; kr <= 0; ww <= 0; wr <= 0; kv_v <= 1'b0; em_v <= 1'b0; v1 <= 1'b0; fault <= 1'b0;
            wc1_kv <= 1'b0; wc1_st <= 1'b0;
        end else begin
            if (rd_issue) begin kw <= kw + 1'b1; if (k_full) fault <= 1'b1; end
            if (r_v) begin kr <= kr + 1'b1; if (k_empty) fault <= 1'b1; end
            kv_v <= r_v && !cls;
            v1 <= r_v && cls;
            em_v <= v1;
            if (w_v) begin ww <= ww + 1'b1; if (w_full) fault <= 1'b1; end
            if (wr_static) begin wr <= wr + 1'b1; if (w_empty) fault <= 1'b1; end
            wc1_kv <= wr_kv; wc1_st <= wr_static;
            if (wc1_kv) fault <= 1'b1;
        end
    always @(posedge clk) begin : dp
        reg [65:0] dc; reg ue, ce; reg [255:0] d;
        if (rd_issue) kq[kw[RA-1:0]] <= col_sr;
        if (w_v) wq[ww[WA-1:0]] <= enc256(w_d);
        if (r_v) begin
            kv_d <= r_d; c1 <= r_d;
            for (i = 0; i < 4; i = i + 1) y1[i*8 +: 8] <= syn64(r_d[i*72 +: 72]);
        end
        ue = 1'b0; ce = 1'b0;
        for (i = 0; i < 4; i = i + 1) begin
            dc = cor64(c1[i*72 +: 72], (MUT == 3) ? 8'd0 : y1[i*8 +: 8]);
            d[i*64 +: 64] = dc[63:0]; ue = ue | dc[65]; ce = ce | dc[64];
        end
        if (v1) em_d <= {ue, ce, d};
    end
endmodule

// Wires-only controller parent without ci (see the header); hard children u_sched (nc), u_cdc, u_obs, u_port (nc), u_ecc.
module qkd_ctrl_pc_host_static_nc #(
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
    // Clock entries (lead 2026-10-16 option A, wires-only cluster rule: one top clock port per hard-child clock pin):
    // pll_hbm -> u_core, pll_hbm_port -> u_port, pll_hbm_ecc -> u_ecc. All three carry the SAME HBM clock; the die
    // clock tree delivers each as its own entry (phi - R_i). Data ports and module name unchanged.
    input  wire         pll_hbm_port,
    input  wire         pll_hbm_ecc,
    // KVCTRL core_s7 (lead Q-KV 2026-10-17): the core is three hardened children; each gets its own HBM clock entry:
    // pll_hbm -> u_sched, pll_hbm_cdc -> u_cdc (with ck), pll_hbm_obs -> u_obs. Same HBM clock, one die entry each.
    input  wire         pll_hbm_cdc,
    input  wire         pll_hbm_obs,
    input  wire         hrst,
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    output wire [281:0] co,           // (nc) the ECC child landing {l_data, l_row, l_sec, l_v}; no legacy pass fields
    input  wire [287:0] es,
    output wire [260:0] er,
    output wire [327:0] po,
    input  wire [288:0] pi,
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output wire         fo,
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
    output wire idle_core,idle_hbm,output wire drain_fault_core,drain_fault_hbm
);

    // ---- wires only: three hardened children ----------------------------------------------------------------------
    wire         p_col_v, p_col_we, p_col_sr, p_w_v, p_kv_v, p_em_v, p_fault, e_l_v, e_fault;
    wire [255:0] p_w_d, l_data;
    wire [287:0] p_wd, p_kv_d;
    wire [257:0] p_em_d;
    wire [16:0]  e_sec, l_sec;
    wire [7:0]   e_row, l_row;
    // core_s7: sched / cdc / obs children (was u_core qkd_ctrl_pc_host_static_core). Seams register to register;
    // priced edges vs core_s6: static embed command +1 hclk (cdc down-FIFO output registers), embedding return +1 hclk
    // and u_ctl credit +1 hclk (cdc pin registers), native commit observation +1 hclk (obs input pin registers).
    wire [4:0]   pc_q;
    wire         s_cr, c_v, f_ecdc, physical_col_sr, expected_sr, obs_commit_valid, native_observer_fault;
    wire [286:0] c_d;
    wire [61:0]  c_context;
    wire [346:0] physical_context;
    qkd_ctrl_pc_sched_nc #(.CORE_CLOCK(CORE_CLOCK),.ROW0(ROW0),.CVL(CVL),.HOFF(HOFF),.WDONE(WDONE),.LATE(LATE),.PROFILE(PROFILE),.EVMUT(EVMUT),.MUT(MUT),.ELASTIC(ELASTIC),.RAW_WD(RAW_WD),.STRAP_CDC(STRAP_CDC),.DRAIN_PIPE(DRAIN_PIPE),.TQD(TQD),.CONTEXT_DESC(CONTEXT_DESC),.STATIC_REFRESH(STATIC_REFRESH)) u_sched (
        .pll_hbm(pll_hbm), .hrst(hrst), .pc(pc),
        .po(po), .pi_v(pi[0]), .ki(ki), .ko(ko), .fi(fi), .fo(fo),
        .static_cmd_owner(static_cmd_owner), .static_cmd(static_cmd), .reserved_rd(reserved_rd),
        .reserved_static_col(reserved_static_col), .reserved_write_col(reserved_write_col),
        .static_epoch(static_epoch), .expected_raw_valid(expected_raw_valid), .corrected_epoch(corrected_epoch),
        .idle_hbm(idle_hbm), .drain_fault_hbm(drain_fault_hbm),
        .p_col_v(p_col_v), .p_col_we(p_col_we), .p_col_sr(p_col_sr), .p_w_v(p_w_v), .p_w_d(p_w_d),
        .p_wd(p_wd), .p_kv_v(p_kv_v), .p_em_v(p_em_v), .p_fault(p_fault),
        .e_sec(e_sec), .e_row(e_row), .e_l_v(e_l_v), .e_fault(e_fault),
        .pc_q(pc_q), .s_cr_o(s_cr), .c_v(c_v), .c_d(c_d), .c_context(c_context), .f_ecdc(f_ecdc),
        .physical_context(physical_context), .physical_col_sr(physical_col_sr), .expected_sr(expected_sr),
        .obs_commit_valid(obs_commit_valid), .native_commit_valid(native_commit_valid),
        .native_observer_fault(native_observer_fault));
    qkd_ctrl_pc_cdc_child #(.WDONE(WDONE),.PROFILE(PROFILE),.EVMUT(EVMUT),.STRAP_CDC(STRAP_CDC),.DRAIN_PIPE(DRAIN_PIPE)) u_cdc (
        .pll_hbm(pll_hbm_cdc), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(pc), .pc_q(pc_q),
        .es(es), .er(er), .cfg_stack(cfg_stack),
        .es_context(es_context), .es_expected_valid(es_expected_valid), .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address), .es_expected_pc(es_expected_pc), .es_expected_stack(es_expected_stack),
        .completion_v(completion_v), .completion_we(completion_we), .completion_fault(completion_fault),
        .idle_core(idle_core), .drain_fault_core(drain_fault_core),
        .s_cr(s_cr), .p_em_v(p_em_v), .p_em_d(p_em_d), .c_v(c_v), .c_d(c_d), .c_context(c_context), .f_ecdc(f_ecdc),
        .col_v(po[28]), .col_we(po[29]), .col_sr(physical_col_sr));
    qkd_ctrl_pc_obs_child #(.PROFILE(PROFILE)) u_obs (
        .pll_hbm(pll_hbm_obs), .hrst(hrst), .po(po), .static_column(physical_col_sr), .expected_static_column(expected_sr),
        .context_word(physical_context), .obs_commit_valid(obs_commit_valid), .native_commit_valid(native_commit_valid),
        .native_commit_identity(native_commit_identity), .native_commit_address(native_commit_address),
        .fault(native_observer_fault));
    qkd_ctrl_pc_port_child_nc #(.RQD(TQD), .MUT(MUT == 2 ? 4 : 0)) u_port (
        .hclk(pll_hbm_port), .hrst(hrst), .col_v_e(p_col_v), .col_we_e(p_col_we), .col_sr_e(p_col_sr),
        .w_v(p_w_v), .w_d(p_w_d), .pi(pi),
        .wd(p_wd), .kv_v(p_kv_v), .kv_d(p_kv_d), .em_v(p_em_v), .em_d(p_em_d), .fault(p_fault));
    qkd_ctrl_pc_ecc_child u_ecc (
        .hclk(pll_hbm_ecc), .hrst(hrst), .i_v(p_kv_v), .i_code(p_kv_d), .i_sec(e_sec), .i_row(e_row),
        .o_v(e_l_v), .o_data(l_data), .o_sec(l_sec), .o_row(l_row), .fault(e_fault));
    assign co = {l_data, l_row, l_sec, e_l_v};
endmodule
