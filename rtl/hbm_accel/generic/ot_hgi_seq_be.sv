// ot_hgi_seq_be.sv -- BE child of the R25GQ sequencer split (el1013-hbm-seq-split, 2026-10-13).
// Holds the record queue, the head mux and its head-pointer copies, the indexed resolver / injector, the main FSM,
// the doorbell, the completion, the per-unit outstanding counters and the dispatch payload of the flat ot_hgi_seq.
// Logic is MOVED from ot_hgi_seq.sv; the seam contract is ot_hgi_seq_seam.svh (rules R1-R4).  Differences:
//   * the queue entry is written from the S2 RX flops (alloc, raw item) and the S3 RX flops (AU result);
//   * e_ps1 = pos1_q + the header's slot (== the flat table p1 field): no table read crosses a seam;
//   * job load: be_jl_* to FE / AU, S_DB lasts SEAM_JL_WAIT cycles, db_bad uses the registered fe_kz;
//   * injector: be_inj_hold is high while jst == J_INJ; the first be_inj is SEAM_INJ_WAIT cycles after the J_IDLE ->
//     J_INJ decision (FE items already issued drain into A0 first); S4 leaves from TX flops.
`default_nettype none
module ot_hgi_seq_be #(
    parameter integer RW   = 4096,
    parameter integer NOS  = 160,
    parameter integer USE_MACRO = 0,
    parameter integer DS_TPL = 2,
    parameter integer DS_WIN = 128,
    parameter integer DS_SCAN = 16384,
    parameter integer DS_TOPK = 512,
    parameter integer DS_HDL = 9,
    parameter integer QD = 4,
    parameter integer FD = 12,
    parameter integer IKS_I = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [17:0]   cfg_vocab,
    input  wire [20:0]   cfg_ctx_max,
    input  wire          hold,
    output wire          busy,
    input  wire          db_v,
    output wire          db_rdy,
    input  wire [17:0]   db_token,
    input  wire [19:0]   db_pos,
    input  wire [31:0]   db_job,
    input  wire [3:0]    db_gen,
    input  wire [1:0]    db_entry,
    input  wire [3:0]    db_ncol,
    input  wire [3:0]    db_kernel,
    input  wire [31:0]   db_loff,
    output wire          vr_v,
    input  wire          vr_rdy,
    output reg  [17:0]   vr_addr,
    input  wire          vr_rsp_v,
    input  wire [31:0]   vr_rsp_data,
    output wire [15:0]   u_v,
    input  wire [15:0]   u_rdy,
    output reg  [127:0]  d_hdr,
    output reg  [255:0]  d_sut,
    output reg  [1791:0] d_desc,
    output reg  [146:0]  d_n,
    output reg  [20:0]   d_pos1,
    output reg  [20:0]   d_pslot1,
    output reg  [15:0]   d_L,
    output reg  [15:0]   d_L1,
    input  wire [15:0]   u_done,
    input  wire [15:0]   u_fault,
    input  wire          wr_quiet,
    output wire          cpl_v,
    input  wire          cpl_rdy,
    output reg  [17:0]   cpl_token,
    output reg  [19:0]   cpl_pos,
    output reg  [31:0]   cpl_job,
    output reg  [3:0]    cpl_gen,
    output reg  [3:0]    cpl_status,
    output reg  [31:0]   cpl_cycles,
    output wire          cpl_tokx,
    // S5a / S5b  BE -> FE, AU
    output reg           be_jl_v,
    output reg  [1:0]    be_jl_entry,
    output reg  [3:0]    be_jl_kernel,
    output reg  [31:0]   be_jl_loff,
    output reg  [19:0]   be_jl_pos,
    output reg  [17:0]   be_jl_token,
    output reg           be_js,
    output reg           be_stop,
    output reg           be_qpop,
    output reg           be_lv_v,
    output reg  [15:0]   be_lv_cnt,
    output reg           be_inj_hold,
    input  wire          fe_kz,
    // S2  FE -> BE
    input  wire          fe_s2a_v,
    input  wire [((QD <= 2) ? 1 : $clog2(QD))-1:0] fe_s2a_tag,
    input  wire [127:0]  fe_s2a_hdr,
    input  wire [2:0]    fe_s2a_kind,
    input  wire          fe_s2a_rdy0,
    input  wire [15:0]   fe_s2a_L,
    input  wire [15:0]   fe_s2a_L1,
    input  wire          fe_s2i_v,
    input  wire [255:0]  fe_s2i_d,
    input  wire [((QD <= 2) ? 1 : $clog2(QD))-1:0] fe_s2i_tag,
    input  wire [2:0]    fe_s2i_slot,
    input  wire          fe_s2i_sut,
    input  wire          fe_s2i_np0,
    // S3  AU -> BE
    input  wire          au_s3_v,
    input  wire          au_s3_be,
    input  wire [((QD <= 2) ? 1 : $clog2(QD))-1:0] au_s3_tag,
    input  wire [2:0]    au_s3_j,
    input  wire          au_s3_last,
    input  wire          au_s3_isI,
    input  wire [63:0]   au_s3_acc,
    input  wire [20:0]   au_s3_n,
    input  wire          au_s3_px,
    input  wire          au_s3_pn,
    input  wire          au_s3_flt,
    input  wire          au_s3_badd,
    input  wire [17:0]   au_s3_iax,
    input  wire          au_s3_ixb,
    input  wire [17:0]   au_s3_ian,
    input  wire          au_s3_inb,
    input  wire          au_s3_ihbm,
    // S4  BE -> AU
    output reg           be_s4_v,
    output reg  [23:0]   be_s4_ph,
    output reg  [39:0]   be_s4_base,
    output reg  [26:0]   be_s4_dmul,
    output reg  [1:0]    be_s4_sp,
    output reg  [31:0]   be_s4_x,
    output reg  [2:0]    be_s4_j,
    output reg  [((QD <= 2) ? 1 : $clog2(QD))-1:0] be_s4_tag
);
`include "ot_hgi_seq_seam.svh"
    // ---- pins: hold-delay stage + pin flop on every input (as the flat design)
    wire [18-1:0] cfg_vocab_h; ot_hgi_seq_hd #(.W(18), .N(2)) u_hdly_cfg_vocab (.a(cfg_vocab), .y(cfg_vocab_h));
    wire [21-1:0] cfg_ctx_max_h; ot_hgi_seq_hd #(.W(21), .N(2)) u_hdly_cfg_ctx_max (.a(cfg_ctx_max), .y(cfg_ctx_max_h));
    wire [1-1:0] hold_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_hold (.a(hold), .y(hold_h));
    wire [1-1:0] db_v_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_db_v (.a(db_v), .y(db_v_h));
    wire [18-1:0] db_token_h; ot_hgi_seq_hd #(.W(18), .N(2)) u_hdly_db_token (.a(db_token), .y(db_token_h));
    wire [20-1:0] db_pos_h; ot_hgi_seq_hd #(.W(20), .N(2)) u_hdly_db_pos (.a(db_pos), .y(db_pos_h));
    wire [32-1:0] db_job_h; ot_hgi_seq_hd #(.W(32), .N(2)) u_hdly_db_job (.a(db_job), .y(db_job_h));
    wire [4-1:0] db_gen_h; ot_hgi_seq_hd #(.W(4), .N(2)) u_hdly_db_gen (.a(db_gen), .y(db_gen_h));
    wire [2-1:0] db_entry_h; ot_hgi_seq_hd #(.W(2), .N(2)) u_hdly_db_entry (.a(db_entry), .y(db_entry_h));
    wire [4-1:0] db_ncol_h; ot_hgi_seq_hd #(.W(4), .N(2)) u_hdly_db_ncol (.a(db_ncol), .y(db_ncol_h));
    wire [4-1:0] db_kernel_h; ot_hgi_seq_hd #(.W(4), .N(2)) u_hdly_db_kernel (.a(db_kernel), .y(db_kernel_h));
    wire [32-1:0] db_loff_h; ot_hgi_seq_hd #(.W(32), .N(2)) u_hdly_db_loff (.a(db_loff), .y(db_loff_h));
    wire [1-1:0] vr_rdy_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_vr_rdy (.a(vr_rdy), .y(vr_rdy_h));
    wire [1-1:0] vr_rsp_v_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_vr_rsp_v (.a(vr_rsp_v), .y(vr_rsp_v_h));
    wire [32-1:0] vr_rsp_data_h; ot_hgi_seq_hd #(.W(32), .N(2)) u_hdly_vr_rsp_data (.a(vr_rsp_data), .y(vr_rsp_data_h));
    wire [16-1:0] u_rdy_h; ot_hgi_seq_hd #(.W(16), .N(2)) u_hdly_u_rdy (.a(u_rdy), .y(u_rdy_h));
    wire [16-1:0] u_done_h; ot_hgi_seq_hd #(.W(16), .N(2)) u_hdly_u_done (.a(u_done), .y(u_done_h));
    wire [16-1:0] u_fault_h; ot_hgi_seq_hd #(.W(16), .N(2)) u_hdly_u_fault (.a(u_fault), .y(u_fault_h));
    wire [1-1:0] wr_quiet_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_wr_quiet (.a(wr_quiet), .y(wr_quiet_h));
    wire [1-1:0] cpl_rdy_h; ot_hgi_seq_hd #(.W(1), .N(2)) u_hdly_cpl_rdy (.a(cpl_rdy), .y(cpl_rdy_h));
    reg [17:0] cfg_vocab_r; reg [20:0] cfg_ctx_max_r; reg hold_r;
    reg vr_rsp_v_r; reg [31:0] vr_rsp_data_r; reg [15:0] u_done_r, u_fault_r; reg wr_quiet_r;
    // ---- reset: this child's OWN release synchroniser, three kept copies (boundary, FSM / queue control, outst)
    (* keep = 1 *) reg [1:0] rs_q, rs_m, rs_u;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rs_q <= 2'b00; rs_m <= 2'b00; rs_u <= 2'b00; end
        else begin rs_q <= {rs_q[0], 1'b1}; rs_m <= {rs_m[0], 1'b1}; rs_u <= {rs_u[0], 1'b1}; end
    wire rn = rs_q[1];                   // boundary / small control
    wire rn_m = rs_m[1];                 // BE / job FSM
    wire rn_u = rs_u[1];                 // per-unit outstanding counters
    always @(posedge clk or negedge rn)
        if (!rn) begin hold_r <= 1'b1; vr_rsp_v_r <= 1'b0; u_done_r <= 16'd0; u_fault_r <= 16'd0; wr_quiet_r <= 1'b0; end
        else begin hold_r <= hold_h; vr_rsp_v_r <= vr_rsp_v_h; u_done_r <= u_done_h; u_fault_r <= u_fault_h; wr_quiet_r <= wr_quiet_h; end
    always @(posedge clk) begin cfg_vocab_r <= cfg_vocab_h; cfg_ctx_max_r <= cfg_ctx_max_h; vr_rsp_data_r <= vr_rsp_data_h; end
    localparam integer QB = (QD <= 2) ? 1 : $clog2(QD);
    // ------------------------------------------------------------------ field positions (spec.json, v1.0)
    localparam integer H_UNIT = 124, H_OP = 118, H_WAIT = 102, H_PRED = 100, H_OPND = 93, H_TMPL = 92, H_SLOT = 89,
                       H_PARAM = 64;
    localparam integer M_SPACE = 0, M_IBC = 5, M_IDX = 6, M_BASE = 8, M_N = 48, M_M = 68, M_STRIDE = 88,
                       M_LSTR = 136, M_DSEL = 168, M_DMUL = 174, M_NSEL = 201, M_L1STR = 207;
    // ------------------------------------------------------------------ main (back-end) states
    localparam [4:0] S_IDLE = 5'd0, S_DB = 5'd1, S_DB2 = 5'd2, S_DB3 = 5'd3, S_HD = 5'd4,
                     S_DSP = 5'd8, S_FEN = 5'd9, S_LVW = 5'd10, S_LVR = 5'd11, S_ENDRD = 5'd12,
                     S_TOKX = 5'd13, S_TKB = 5'd14, S_CPL = 5'd15;
    // record queue entry kinds
    localparam [2:0] K_DISP = 3'd0, K_END = 3'd1, K_TOKX = 3'd2, K_FENCE = 3'd3, K_LVM = 3'd4, K_FLT = 3'd5;
    reg [4:0]  st;
    reg        run_q;                    // a job runs: set at the job start, cleared on S_CPL (BE gates every seam RX on it)
    reg [17:0] token; reg [19:0] pos; reg [1:0] db_entry_q; reg [20:0] pos1_q;
    // ------------------------------------------------------------------ outstanding per unit
    reg [7:0] outst [0:15];
    reg [15:0] busy_u;
    integer u;
    always @* for (u = 0; u < 16; u = u + 1) busy_u[u] = (outst[u] != 8'd0);
    function automatic waitok(input [15:0] w, input [15:0] b);
`ifdef OT_HGI_SEQ_MUT_WAIT
        waitok = 1'b1;                                     // NEGATIVE CONTROL: the drain mask ignored
`else
        waitok = ((w & 16'hFFFE) & b) == 16'd0;
`endif
    endfunction
    reg busy_q;
    always @(posedge clk or negedge rn) if (!rn) busy_q <= 1'b0; else busy_q <= (st != S_IDLE) || (busy_u != 16'd0);
    assign busy = busy_q;
    // ---- seam RX (R1): every seam input is registered once before use
    reg fe_s2a_v_r, fe_s2i_v_r, au_s3_v_r, fe_kz_r;
    always @(posedge clk or negedge rn_m)
        if (!rn_m) begin fe_s2a_v_r <= 1'b0; fe_s2i_v_r <= 1'b0; au_s3_v_r <= 1'b0; fe_kz_r <= 1'b0; end
        else begin fe_s2a_v_r <= fe_s2a_v; fe_s2i_v_r <= fe_s2i_v; au_s3_v_r <= au_s3_v; fe_kz_r <= fe_kz; end
    reg [QB-1:0] fe_s2a_tag_r, fe_s2i_tag_r, au_s3_tag_r; reg [127:0] fe_s2a_hdr_r; reg [2:0] fe_s2a_kind_r; reg fe_s2a_rdy0_r;
    reg [15:0] fe_s2a_L_r, fe_s2a_L1_r; reg [255:0] fe_s2i_d_r; reg [2:0] fe_s2i_slot_r; reg fe_s2i_sut_r, fe_s2i_np0_r;
    reg au_s3_be_r, au_s3_last_r, au_s3_isI_r, au_s3_px_r, au_s3_pn_r, au_s3_flt_r, au_s3_badd_r, au_s3_ixb_r, au_s3_inb_r, au_s3_ihbm_r;
    reg [2:0] au_s3_j_r; reg [63:0] au_s3_acc_r; reg [20:0] au_s3_n_r; reg [17:0] au_s3_iax_r, au_s3_ian_r;
    always @(posedge clk) begin
        fe_s2a_tag_r <= fe_s2a_tag; fe_s2a_hdr_r <= fe_s2a_hdr; fe_s2a_kind_r <= fe_s2a_kind; fe_s2a_rdy0_r <= fe_s2a_rdy0;
        fe_s2a_L_r <= fe_s2a_L; fe_s2a_L1_r <= fe_s2a_L1;
        fe_s2i_d_r <= fe_s2i_d; fe_s2i_tag_r <= fe_s2i_tag; fe_s2i_slot_r <= fe_s2i_slot; fe_s2i_sut_r <= fe_s2i_sut; fe_s2i_np0_r <= fe_s2i_np0;
        au_s3_be_r <= au_s3_be; au_s3_tag_r <= au_s3_tag; au_s3_j_r <= au_s3_j; au_s3_last_r <= au_s3_last; au_s3_isI_r <= au_s3_isI;
        au_s3_acc_r <= au_s3_acc; au_s3_n_r <= au_s3_n; au_s3_px_r <= au_s3_px; au_s3_pn_r <= au_s3_pn; au_s3_flt_r <= au_s3_flt;
        au_s3_badd_r <= au_s3_badd; au_s3_iax_r <= au_s3_iax; au_s3_ixb_r <= au_s3_ixb; au_s3_ian_r <= au_s3_ian; au_s3_inb_r <= au_s3_inb;
        au_s3_ihbm_r <= au_s3_ihbm;
    end
    // the flat names of the AU result (A5 flops / A6 flags), now the S3 RX flops; dropped while no job runs
    wire        a6_fe = au_s3_v_r && run_q && !au_s3_be_r;
    wire        a6_be = au_s3_v_r && run_q && au_s3_be_r;
    wire [QB-1:0] a5_tag = au_s3_tag_r;
    wire [2:0]  a5_j = au_s3_j_r;
    wire        a5_last = au_s3_last_r, a5_isI = au_s3_isI_r, a5_px = au_s3_px_r, a5_pn = au_s3_pn_r;
    wire [63:0] a5_acc = au_s3_acc_r;
    wire [20:0] a5_n = au_s3_n_r;
    wire [17:0] a6_iax = au_s3_iax_r, a5_ian = au_s3_ian_r;
    wire        a6_ixb = au_s3_ixb_r, a6_inb = au_s3_inb_r, a6_flt = au_s3_flt_r, a6_bad_d = au_s3_badd_r, a6_ihbm = au_s3_ihbm_r;
    // ---- record queue occupancy (FE allocates over S2, BE frees)
    reg [QB:0] q_cnt; reg [QB-1:0] qh, qt;
    wire        job_start;               // S_DB3 with a good doorbell (main FSM)
    wire        be_inj;                  // the injector issues one re-injection (S4) this cycle
    wire        q_alloc = fe_s2a_v_r && run_q;
    // re-injection source (the resolver's entry inj_e, descriptor be_j): wires defined with the queue below
    wire [2:0]  be_j; wire [255:0] be_d; wire [23:0] be_ph; wire be_xj;
    reg  [31:0] Xv; reg [20:0] Nv;
`ifndef SYNTHESIS
    reg seam_err; initial seam_err = 1'b0;
    reg rst_seen; initial rst_seen = 1'b0;          // the probe is armed by the first reset (2-state simulators start
    always @(negedge rst_n) rst_seen <= 1'b1;       // flops at arbitrary values: nothing before a reset is a seam event)
    always @(posedge clk) if (rst_seen && rn_m && q_alloc && (q_cnt == QD || fe_s2a_tag_r != qt)) begin
        seam_err <= 1'b1; $error("ot_hgi_seq_be: alloc with the queue full or out of order (credit violated)");
    end
`endif
    // ================================================================== RQ: the record queue (one generate block an entry)
    localparam integer EW_D = 7*256, EW_N = 7*21, EW_PH = 6*24;
    wire [QD*128-1:0] all_hdr; wire [QD*3-1:0] all_kind; wire [QD*256-1:0] all_sut; wire [QD*EW_D-1:0] all_dsc;
    wire [QD*EW_N-1:0] all_n; wire [QD*EW_PH-1:0] all_ph; wire [QD*6-1:0] all_px, all_pn; wire [QD*18-1:0] all_ixa, all_ina;
    wire [QD-1:0] all_ixb, all_inb, all_rdy, all_flt; wire [QD*16-1:0] all_L, all_L1; wire [QD*21-1:0] all_ps1;
    wire        be_pclr;                 // the resolver's entry has every pending descriptor resolved
    reg  [QB-1:0] rd_e, inj_e;         // the resolver's reader entry (VM reads) / injector entry (AU pass)
    reg         ir_flt;                  // the reader found a fault in rd_e (reported when rd_e reaches the head)
    // an FE item / SUT is written into its entry from the S2 RX flops (the flat it_d staging is the FE TX flop):
    // per-(entry, slot) enables decoded from the RX tag / slot flops
    wire [255:0] it_d = fe_s2i_d_r; wire su_np0 = fe_s2i_np0_r;
    wire [QD*7-1:0] it_we; wire [QD-1:0] su_we;
    genvar gw;
    generate for (gw = 0; gw < QD*7; gw = gw + 1) begin : g_itwe
        assign it_we[gw] = fe_s2i_v_r && run_q && !fe_s2i_sut_r && fe_s2i_tag_r == gw / 7 && fe_s2i_slot_r == gw % 7;
    end
    for (gw = 0; gw < QD; gw = gw + 1) begin : g_suwe
        assign su_we[gw] = fe_s2i_v_r && run_q && fe_s2i_sut_r && fe_s2i_tag_r == gw;
    end endgenerate
    genvar ge, gs;
    generate for (ge = 0; ge < QD; ge = ge + 1) begin : g_q
        reg [127:0] e_hdr; reg [2:0] e_kind; reg [255:0] e_sut;
        reg [17:0] e_ixa, e_ina; reg e_ixb, e_inb, e_rdy, e_flt; reg [15:0] e_L, e_L1; reg [20:0] e_ps1;
        wire [EW_D-1:0] e_dsc; wire [EW_N-1:0] e_n; wire [EW_PH-1:0] e_ph; wire [6:0] e_px7, e_pn7;
        wire al = q_alloc && qt == ge;
        wire fw = a6_fe && a5_tag == ge;
        wire bw = a6_be && inj_e == ge;
        wire pclr = al || (be_pclr && inj_e == ge);
        always @(posedge clk) begin
            if (al) begin
                e_hdr <= fe_s2a_hdr_r; e_kind <= fe_s2a_kind_r; e_L <= fe_s2a_L_r; e_L1 <= fe_s2a_L1_r;
                e_ps1 <= pos1_q + {18'd0, fe_s2a_hdr_r[H_SLOT +: 3]}; e_flt <= 1'b0;     // == the flat table p1 of the slot
                e_rdy <= fe_s2a_rdy0_r;
            end
            if (su_we[ge]) begin e_sut <= it_d; if (su_np0) e_rdy <= 1'b1; end
            if (fw) begin
                if (a5_isI) begin e_ixa <= a6_iax[17:0]; e_ixb <= a6_ixb; e_ina <= a5_ian[17:0]; e_inb <= a6_inb; end
                if (a6_flt) e_flt <= 1'b1;
                if (a5_last) e_rdy <= 1'b1;
            end
            if ((ir_flt && rd_e == ge) || (bw && a6_bad_d)) e_flt <= 1'b1;
            // IKS: an HBM-space I is no indexed-read source: an indexed / N_FROM_VM operand of the record faults (as without I)
            if (fw && a6_ihbm && ((|e_px7[5:0]) || (|e_pn7[5:0]))) e_flt <= 1'b1;
        end
        // one descriptor slot: raw at the pop, base / n patched by the AU (FE pass) and by the BE (indexed pass)
        for (gs = 0; gs < 7; gs = gs + 1) begin : g_s
            reg [255:0] s_dsc; reg [20:0] s_n; reg [23:0] s_ph; reg s_px, s_pn;
            wire [20:0] nf = s_pn ? Nv : s_n;
            always @(posedge clk) begin
                if (it_we[ge*7 + gs]) s_dsc <= it_d;
                if (pclr) begin s_px <= 1'b0; s_pn <= 1'b0; end
                if (fw && a5_j == gs) begin
                    s_dsc[M_BASE +: 40] <= a5_acc[39:0]; s_dsc[M_N +: 20] <= a5_n[19:0]; s_n <= a5_n;
                    s_ph <= a5_acc[63:40]; s_px <= a5_px; s_pn <= a5_pn;
                end
                if (bw && a5_j == gs) begin
                    s_dsc[M_BASE +: 40] <= a5_acc[39:0]; s_dsc[M_N +: 20] <= nf[19:0]; s_n <= nf;
                end
            end
            assign e_dsc[gs*256 +: 256] = s_dsc; assign e_n[gs*21 +: 21] = s_n;
            assign e_px7[gs] = s_px; assign e_pn7[gs] = s_pn;
            if (gs < 6) begin : g_ph assign e_ph[gs*24 +: 24] = s_ph; end
        end
        assign all_hdr[ge*128 +: 128] = e_hdr; assign all_kind[ge*3 +: 3] = e_kind; assign all_sut[ge*256 +: 256] = e_sut;
        assign all_dsc[ge*EW_D +: EW_D] = e_dsc; assign all_n[ge*EW_N +: EW_N] = e_n; assign all_ph[ge*EW_PH +: EW_PH] = e_ph;
        assign all_px[ge*6 +: 6] = e_px7[5:0]; assign all_pn[ge*6 +: 6] = e_pn7[5:0]; assign all_ixa[ge*18 +: 18] = e_ixa;
        assign all_ina[ge*18 +: 18] = e_ina; assign all_ixb[ge] = e_ixb; assign all_inb[ge] = e_inb; assign all_rdy[ge] = e_rdy;
        assign all_flt[ge] = e_flt; assign all_L[ge*16 +: 16] = e_L; assign all_L1[ge*16 +: 16] = e_L1; assign all_ps1[ge*21 +: 21] = e_ps1;
    end endgenerate
    // the head entry: each 64-bit chunk of the packed entry is selected by its own head-pointer copy (qh_cp)
    reg [127:0] hd_hdr; reg [2:0] hd_kind; reg [255:0] hd_sut; reg [EW_D-1:0] hd_dsc; reg [EW_N-1:0] hd_n;
    reg [5:0] hd_px, hd_pn; reg hd_rdy, hd_flt; reg [15:0] hd_L, hd_L1; reg [20:0] hd_ps1;
    wire [QD*NQC*64-1:0] ent_all;
    wire [NQC*64-1:0] hd_vec;
    genvar gv, gc;
    generate for (gv = 0; gv < QD; gv = gv + 1) begin : g_ev
        assign ent_all[gv*NQC*64 +: NQC*64] = {{(NQC*64 - HVW){1'b0}}, all_ps1[gv*21 +: 21], all_L1[gv*16 +: 16], all_L[gv*16 +: 16],
            all_flt[gv], all_rdy[gv], all_pn[gv*6 +: 6], all_px[gv*6 +: 6], all_n[gv*EW_N +: EW_N], all_dsc[gv*EW_D +: EW_D],
            all_sut[gv*256 +: 256], all_kind[gv*3 +: 3], all_hdr[gv*128 +: 128]};
    end
    for (gc = 0; gc < NQC; gc = gc + 1) begin : g_hc
        reg [63:0] m; integer qe;
        always @* begin
            m = ent_all[gc*64 +: 64];
            for (qe = 1; qe < QD; qe = qe + 1) if (qh_cp[gc*QB +: QB] == qe) m = ent_all[(qe*NQC + gc)*64 +: 64];
        end
        assign hd_vec[gc*64 +: 64] = m;
    end endgenerate
    always @* {hd_ps1, hd_L1, hd_L, hd_flt, hd_rdy, hd_pn, hd_px, hd_n, hd_dsc, hd_sut, hd_kind, hd_hdr} = hd_vec[HVW-1:0];
    // ================================================================== IR: the indexed resolver
    // An entry's I-table reads (ONE X read at I_eff + L, ONE N read at I_eff + I.stride + L) are made as soon as the
    // entry's wait mask is met with every OLDER queued dispatch counted busy (those dispatch before it, so its wait
    // would hold for them) -- the same producer-retired condition the head would see, earlier.  Its pending
    // descriptors are then re-injected through the AU (X x dyn_mul + the pre-sum) and patched in place; a read or
    // range fault marks the entry (status 3 when it reaches the head, after the records before it).  Oldest first;
    // the scan stops at an entry still in the AU, a fault, FENCE or LOOP-from-VM.
    // two halves, overlapped: the READER makes the VM reads of one entry while the INJECTOR re-injects the previous one
    localparam [1:0] I_IDLE = 2'd0, I_XR = 2'd1, I_NR = 2'd2, I_HAND = 2'd3;     // reader
    localparam [1:0] J_IDLE = 2'd0, J_INJ = 2'd1, J_IW = 2'd2;                   // injector
    reg [1:0] ir_st, jst; reg ir_sv; reg [QB-1:0] ir_se; reg [31:0] rXv; reg [20:0] rNv;
    reg [5:0] rem; reg [3:0] ninj, nres;
    // v2.3 (route 905100ec5: rd_e -> 4:1 entry mux -> vr_addr): the reader entry's N-read operands, registered (rd_e
    // and the entry are fixed while the X read is in flight; its response is >= 2 cycles after rd_e is set)
    reg [17:0] rd_ina_q; reg rd_pn_q, rd_inb_q;
    always @(posedge clk) begin rd_ina_q <= all_ina[rd_e*18 +: 18]; rd_pn_q <= |all_pn[rd_e*6 +: 6]; rd_inb_q <= all_inb[rd_e]; end
    // per-entry scan inputs
    // the per-entry scan inputs are registered (one cycle stale is conservative: an entry only becomes ready /
    // resolved / faulted, busy only drops apart from dispatches of entries still in the queue, which the scan counts)
    reg [QD-1:0] en_blk, en_pend, en_disp; reg [QD*16-1:0] en_um, en_w; integer qa;
    always @(posedge clk) for (qa = 0; qa < QD; qa = qa + 1) begin
        en_blk[qa] <= !all_rdy[qa] || all_flt[qa] || all_kind[qa*3 +: 3] == K_FLT || all_kind[qa*3 +: 3] == K_FENCE ||
                     all_kind[qa*3 +: 3] == K_LVM;
        en_pend[qa] <= (all_px[qa*6 +: 6] | all_pn[qa*6 +: 6]) != 6'd0 && !(ir_st != I_IDLE && rd_e == qa) &&
                      !(jst != J_IDLE && inj_e == qa);         // an entry the resolver holds counts as resolved
        en_disp[qa] <= all_kind[qa*3 +: 3] == K_DISP;
        en_um[qa*16 +: 16] <= 16'd1 << all_hdr[qa*128 + H_UNIT +: 4];
        en_w[qa*16 +: 16] <= all_hdr[qa*128 + H_WAIT +: 16];
    end
    // v2.5 (drain rule, HGI-1 4.1 / 4.3): the compiler drops a wait bit a record would need when an OLDER record already
    // waits for that unit ("since that unit last drained": in order, the older record's wait drains it for both).  The
    // head sees that drain; a resolver ahead of the head does not, unless it also honours the wait masks of the older
    // queued entries (ow).  Without ow the I table of an indexed reader behind e.g. a DMA.FENCE that waits for IDX was
    // read while IDX.TOPK was still running (DS route.gather: stale ids, a wrong effective base).
    reg ir_cv, sblk; reg [QB-1:0] ir_ce, se; reg [15:0] om, ow, ir_cm, ir_cw; integer si, sj;
    always @* begin
        ir_cv = 1'b0; ir_ce = {QB{1'b0}}; ir_cm = 16'd0; ir_cw = 16'd0; sblk = 1'b0; om = 16'd0; ow = 16'd0;
        for (si = 0; si < QD; si = si + 1) begin
            se = qh + si[QB-1:0];
            if (si < q_cnt && !sblk && !ir_cv)
                for (sj = 0; sj < QD; sj = sj + 1) if (se == sj[QB-1:0]) begin
                    if (en_blk[sj]) sblk = 1'b1;
                    else if (en_pend[sj]) begin ir_cv = 1'b1; ir_ce = se; ir_cm = om; ir_cw = en_w[sj*16 +: 16] | ow; end
                    else begin
`ifdef OT_HGI_SEQ_MUT_DRAIN
                        ow = 16'd0;                           // NEGATIVE CONTROL: older waits ignored (the v2.1 .. v2.4 rule)
`else
                        ow = ow | en_w[sj*16 +: 16];
`endif
                        if (en_disp[sj]) om = om | en_um[sj*16 +: 16];
                    end
                end
        end
    end
    // the injector's source: {ph 24, dmul 27, base 40, space 2} of each slot 0..5 of entry inj_e, and its pending bits
    localparam integer IJW = 93;
    wire [QD*6*IJW-1:0] inj_all;
    genvar gi2, gs2;
    generate for (gi2 = 0; gi2 < QD; gi2 = gi2 + 1) begin : g_ij
        for (gs2 = 0; gs2 < 6; gs2 = gs2 + 1) begin : g_ijs
            assign inj_all[(gi2*6 + gs2)*IJW +: IJW] = {all_ph[gi2*EW_PH + gs2*24 +: 24], all_dsc[gi2*EW_D + gs2*256 + M_DMUL +: 27],
                                                        all_dsc[gi2*EW_D + gs2*256 + M_BASE +: 40], all_dsc[gi2*EW_D + gs2*256 + M_SPACE +: 2]};
        end
    end endgenerate
    reg [6*IJW-1:0] ij_e; reg [5:0] ir_px, ir_pn; integer qr;
    always @* begin
        ij_e = inj_all[0 +: 6*IJW]; ir_px = all_px[0 +: 6]; ir_pn = all_pn[0 +: 6];
        for (qr = 1; qr < QD; qr = qr + 1) if (inj_e == qr) begin
            ij_e = inj_all[qr*6*IJW +: 6*IJW]; ir_px = all_px[qr*6 +: 6]; ir_pn = all_pn[qr*6 +: 6];
        end
    end
    reg [2:0] bj; integer qj;
    always @* begin bj = 3'd0; for (qj = 5; qj >= 0; qj = qj - 1) if (rem[qj]) bj = qj[2:0]; end
    reg [IJW-1:0] bsel; integer qk;
    always @* begin bsel = ij_e[0 +: IJW]; for (qk = 1; qk < 6; qk = qk + 1) if (bj == qk) bsel = ij_e[qk*IJW +: IJW]; end
    wire [255:0] bd = {{(256 - M_DMUL - 27){1'b0}}, bsel[42 +: 27], {(M_DMUL - M_BASE - 40){1'b0}}, bsel[2 +: 40], {(M_BASE - 2){1'b0}}, bsel[0 +: 2]};
    wire [23:0] bph = bsel[69 +: 24];
    assign be_j = bj; assign be_d = bd; assign be_ph = bph; assign be_xj = ir_px[bj];
    reg [2:0] injw;                      // injector hold wait (cycles left before the first be_inj)
    assign be_inj = run_q && (jst == J_INJ) && (rem != 6'd0) && (injw == 3'd0);
    // ---- dispatch payload: loaded from the head entry when the BE dispatches it (absent operands read 0)
    wire        hd_wok = waitok(hd_hdr[H_WAIT +: 16], busy_u);
    wire        hd_pend = |(hd_px | hd_pn);
    wire        be_go = run_q && (st == S_HD) && (q_cnt != 0) && hd_kind == K_DISP && hd_rdy && !hd_flt && hd_wok && !hd_pend &&
                        !(|(u_fault_r & ~16'd1));
    // v2.3 (route 905100ec5: outst -> busy_u -> wait rule -> be_go -> 2.4k d_* enables): the payload follows the head
    // entry every S_HD cycle (enable = a state decode, no wait / ready logic); units sample d_* only under u_v (S_DSP),
    // and the value loaded in the be_go cycle is the same head entry as before.
    wire        d_ld = (st == S_HD);
    integer qd2;
    always @(posedge clk) if (d_ld) begin
        d_hdr <= hd_hdr; d_sut <= hd_hdr[H_TMPL] ? hd_sut : 256'd0; d_L <= hd_L; d_L1 <= hd_L1; d_pos1 <= pos1_q; d_pslot1 <= hd_ps1;
        for (qd2 = 0; qd2 < 7; qd2 = qd2 + 1) begin
            d_desc[qd2*256 +: 256] <= hd_hdr[H_OPND + qd2] ? hd_dsc[qd2*256 +: 256] : 256'd0;
            d_n[qd2*21 +: 21] <= hd_hdr[H_OPND + qd2] ? hd_n[qd2*21 +: 21] : 21'd0;
        end
    end
    // ================================================================== BE + job control (main FSM)
    // VM read request (timing pass 6 of v1): the FSM sets vr_vr with a vr_new pulse, vr_tk marks the request taken
    reg vr_vr, vr_new, vr_tk;
    assign vr_v = vr_vr & ~vr_tk;
    always @(posedge clk or negedge rn)
        if (!rn) vr_tk <= 1'b0;
        else vr_tk <= vr_new ? (vr_v & vr_rdy_h) : (vr_tk | (vr_v & vr_rdy_h));
    integer k;
    wire [15:0] u_acc = u_v & u_rdy_h;
    reg db_rdy_q;
    always @(posedge clk or negedge rn)
        if (!rn) db_rdy_q <= 1'b0;
        else db_rdy_q <= (st == S_IDLE) && !hold_r && !hold_h && !(db_v_h && db_rdy_q) && !db_pend;
    assign db_rdy = db_rdy_q;
    reg db_pend; reg [17:0] dbq_token; reg [19:0] dbq_pos; reg [31:0] dbq_job; reg [3:0] dbq_gen, dbq_ncol, dbq_kernel; reg [1:0] dbq_entry; reg [31:0] dbq_loff;
    always @(posedge clk or negedge rn)
        if (!rn) db_pend <= 1'b0;
        else if (db_v_h && db_rdy_q) db_pend <= 1'b1;
        else if (st == S_IDLE) db_pend <= 1'b0;
    always @(posedge clk) if (db_rdy_q) begin
        dbq_token <= db_token_h; dbq_pos <= db_pos_h; dbq_job <= db_job_h; dbq_gen <= db_gen_h; dbq_ncol <= db_ncol_h; dbq_entry <= db_entry_h; dbq_kernel <= db_kernel_h; dbq_loff <= db_loff_h;
    end
    reg cpl_v_q, cpl_tokx_q;
    wire cpl_hs = cpl_v_q & cpl_rdy_h;
    reg  cpl_hs_q;
    always @(posedge clk or negedge rn) if (!rn) cpl_hs_q <= 1'b0; else cpl_hs_q <= cpl_hs;
    always @(posedge clk or negedge rn)
        if (!rn) begin cpl_v_q <= 1'b0; cpl_tokx_q <= 1'b0; end
        else begin
            cpl_v_q <= ((st == S_CPL) || (st == S_TKB)) && !cpl_hs && !cpl_hs_q;
            cpl_tokx_q <= (st == S_TKB) && !cpl_hs && !cpl_hs_q;
        end
    assign cpl_v = cpl_v_q;
    assign cpl_tokx = cpl_tokx_q;
    reg db_bad; reg [3:0] jlw;           // jlw: S_DB wait for the job load to settle in FE (SEAM_JL_WAIT)
    reg [15:0] cc_lo, cc_hi; reg cc_c;
    always @(*) cpl_cycles = {cc_hi, cc_lo};
    // dispatch: u_vr is set / cleared from flops only; u_tk marks a valid already taken, u_v = u_vr & ~u_tk
    reg [15:0] u_vr, u_tk, iss_q;
    always @(posedge clk or negedge rn)
        if (!rn) u_tk <= 16'd0;
        else u_tk <= (u_vr == 16'd0) ? 16'd0 : (u_tk | (u_v & u_rdy_h));
    assign u_v = u_vr & ~u_tk;
    reg [4:0]  tk_i, tk_n; reg [17:0] tk_base; reg tk_k; reg [3:0] ncol; reg [19:0] tk_pos;
    assign job_start = (st == S_DB3) && !db_bad;
    wire [3:0] nres_n = nres + {3'd0, a6_be};
    assign be_pclr = run_q && (jst == J_IW) && (nres_n == ninj);
    wire        hd_fault = |(u_fault_r & ~16'd1);
    wire        vm_free = (ir_st == I_IDLE) && !ir_sv;      // the BE may issue its own VM read (reader idle, nothing selected)
    task fault3;
        begin st <= S_CPL; run_q <= 1'b0; be_stop <= 1'b1; cpl_status <= 4'd3; cpl_token <= 18'd0; u_vr <= 16'd0;
              vr_vr <= 1'b0; end
    endtask
    // the BE frees the head (one comb term per pop site; mirrors the FSM below)
    wire be_abort = |(u_fault_r & ~16'd1) && st != S_IDLE && st != S_CPL;
    wire q_pop = !be_abort && ((st == S_DSP && |u_tk) || (st == S_FEN && (busy_u & 16'hFFFE) == 16'd0 && wr_quiet_r) ||
                 (st == S_LVR && vr_rsp_v_r && !(vr_rsp_data_r == 32'd0 || vr_rsp_data_r[31:16] != 16'd0)) ||
                 (st == S_TKB && cpl_hs_q && tk_i == tk_n));
    // outstanding records per unit: +1 at the dispatch decision (iss_q, registered), -1 on retire (done or fault)
    always @(posedge clk or negedge rn_u)
        if (!rn_u) for (k = 0; k < 16; k = k + 1) outst[k] <= 8'd0;
        else for (k = 0; k < 16; k = k + 1)
            if (iss_q[k] && !(u_done_r[k] | u_fault_r[k])) outst[k] <= outst[k] + 8'd1;
            else if (!iss_q[k] && (u_done_r[k] | u_fault_r[k]) && outst[k] != 8'd0) outst[k] <= outst[k] - 8'd1;
    // head-pointer copies: one per 64-bit chunk of the head mux (qh alone drove 7.7k mux loads)
    localparam integer HVW = 128 + 3 + 256 + EW_D + EW_N + 6 + 6 + 1 + 1 + 16 + 16 + 21;
    localparam integer NQC = (HVW + 63) / 64;
    wire [NQC*QB-1:0] qh_cp;
    genvar gk;
    generate for (gk = 0; gk < NQC; gk = gk + 1) begin : g_qc
        (* keep = 1 *) reg [QB-1:0] qc;
        always @(posedge clk or negedge rn_m)
            if (!rn_m) qc <= {QB{1'b0}};
            else if (job_start) qc <= {QB{1'b0}};
            else if (q_pop) qc <= qc + 1'b1;
        assign qh_cp[gk*QB +: QB] = qc;
    end endgenerate
    always @(posedge clk or negedge rn_m) begin
        if (!rn_m) begin
            st <= S_IDLE; run_q <= 1'b0;
            u_vr <= 16'd0; iss_q <= 16'd0; vr_vr <= 1'b0; vr_new <= 1'b0;
            be_jl_v <= 1'b0; be_js <= 1'b0; be_stop <= 1'b0; be_qpop <= 1'b0; be_inj_hold <= 1'b0; be_s4_v <= 1'b0; injw <= 3'd0; jlw <= 4'd0;
            ir_st <= I_IDLE; jst <= J_IDLE; ir_sv <= 1'b0; ir_flt <= 1'b0; rd_e <= {QB{1'b0}}; inj_e <= {QB{1'b0}};
            cpl_status <= 0; cpl_token <= 0; cc_c <= 0;
            qh <= 0; qt <= 0; q_cnt <= 0; be_lv_v <= 1'b0; rem <= 6'd0; ninj <= 4'd0; nres <= 4'd0;
        end else begin
            iss_q <= 16'd0;
            if (st != S_IDLE && st != S_CPL) {cc_c, cc_lo} <= {1'b0, cc_lo} + 17'd1; else cc_c <= 1'b0;
            if (cc_c) cc_hi <= cc_hi + 16'd1;
            vr_new <= 1'b0; be_lv_v <= 1'b0;
            be_jl_v <= 1'b0; be_js <= 1'b0; be_stop <= 1'b0;          // seam pulses (TX flops)
            be_qpop <= q_pop; be_s4_v <= be_inj;
            if (injw != 3'd0) injw <= injw - 3'd1;
            // ---- indexed resolver (owns the VM port while it works; the BE's own reads wait for vm_free)
            ir_flt <= 1'b0;
            ir_sv <= run_q && ir_cv && waitok(ir_cw, busy_u | ir_cm);
            ir_se <= ir_ce;
            if (!run_q || job_start) begin ir_st <= I_IDLE; jst <= J_IDLE; be_inj_hold <= 1'b0; end
            else begin
                case (ir_st)                                          // reader
                    I_IDLE: if (ir_sv && (all_px[ir_se*6 +: 6] | all_pn[ir_se*6 +: 6]) != 6'd0 && !(jst != J_IDLE && inj_e == ir_se) &&
                                st != S_ENDRD && st != S_TOKX && st != S_TKB && st != S_LVR) begin
                        rd_e <= ir_se;
                        if (|all_px[ir_se*6 +: 6]) begin
                            if (all_ixb[ir_se]) ir_flt <= 1'b1;
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= all_ixa[ir_se*18 +: 18]; ir_st <= I_XR; end
                        end else begin
                            if (all_inb[ir_se]) ir_flt <= 1'b1;
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= all_ina[ir_se*18 +: 18]; ir_st <= I_NR; end
                        end
                    end
                    I_XR: if (vr_rsp_v_r) begin
                        rXv <= vr_rsp_data_r;
                        if (rd_pn_q) begin
                            if (rd_inb_q) begin ir_flt <= 1'b1; ir_st <= I_IDLE; end
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= rd_ina_q; ir_st <= I_NR; end
                        end else ir_st <= I_HAND;
                    end
                    I_NR: if (vr_rsp_v_r) begin
                        if (vr_rsp_data_r[31:21] != 11'd0) begin ir_flt <= 1'b1; ir_st <= I_IDLE; end
                        else begin rNv <= vr_rsp_data_r[20:0]; ir_st <= I_HAND; end
                    end
                    default: ;                                        // I_HAND: the injector takes it below
                endcase
                case (jst)                                            // injector
                    J_IDLE: if (ir_st == I_HAND) begin
                        inj_e <= rd_e; Xv <= rXv; Nv <= rNv; rem <= all_px[rd_e*6 +: 6] | all_pn[rd_e*6 +: 6];
                        ninj <= 4'd0; nres <= 4'd0; jst <= J_INJ; ir_st <= I_IDLE;
                        be_inj_hold <= 1'b1;                          // FE stops issuing RC_DSP items two seam flops later
`ifdef OT_HGI_SEQ_MUT_SEAM_HOLD
                        injw <= SEAM_INJ_WAIT - 2;                    // NEGATIVE CONTROL: the first be_inj one cycle early
`else
                        injw <= SEAM_INJ_WAIT - 1;                    // first be_inj SEAM_INJ_WAIT cycles after this decision
`endif
                    end
                    default: begin                                    // J_INJ / J_IW: re-inject, collect, patch
                        if (be_inj) begin rem <= rem & ~(6'd1 << bj); ninj <= ninj + 4'd1; end
                        if (a6_be) nres <= nres_n;
                        if (jst == J_INJ && be_inj && (rem & ~(6'd1 << bj)) == 6'd0) begin jst <= J_IW; be_inj_hold <= 1'b0; end
                        if (be_pclr) jst <= J_IDLE;
                    end
                endcase
            end
            if (|(u_fault_r & ~16'd1) && st != S_IDLE && st != S_CPL) begin
                st <= S_CPL; run_q <= 1'b0; be_stop <= 1'b1; cpl_status <= 4'd1; cpl_token <= 0; u_vr <= 0; vr_vr <= 1'b0;
            end else case (st)
                S_IDLE: if (db_pend) begin
                    token <= dbq_token; pos <= dbq_pos; cpl_job <= dbq_job; cpl_gen <= dbq_gen; cpl_pos <= dbq_pos;
                    db_entry_q <= dbq_entry;
                    // job load to FE (image address) and AU (pos / token copies, table build)
                    be_jl_v <= 1'b1; be_jl_entry <= dbq_entry; be_jl_kernel <= dbq_kernel; be_jl_loff <= dbq_loff;
                    be_jl_pos <= dbq_pos; be_jl_token <= dbq_token; jlw <= SEAM_JL_WAIT - 1;
`ifdef OT_HGI_SEQ_CC_PRESET
                    cc_lo <= 16'hFF00; cc_hi <= 16'd0; cc_c <= 1'b0;   // bench: start near the low half's wrap
`else
                    cc_lo <= 16'd0; cc_hi <= 16'd0; cc_c <= 1'b0;
`endif
                    cpl_token <= 0; cpl_status <= 0; st <= S_DB;
                    ncol <= dbq_ncol;
                end
                S_DB: if (jlw != 4'd0) jlw <= jlw - 4'd1;                 // SEAM_JL_WAIT cycles: fe_kz_r is the new job's
                else begin
                    pos1_q <= {1'b0, pos} + 21'd1;
                    db_bad <= (token >= cfg_vocab_r || {1'b0, pos} >= cfg_ctx_max_r) || (db_entry_q == 2'd3 && fe_kz_r);
                    st <= S_DB2;
                end
                S_DB2: st <= S_DB3;
                S_DB3: begin
                    if (db_bad) begin
                        st <= S_CPL; cpl_status <= 4'd3;
                    end else begin
                        be_js <= 1'b1; run_q <= 1'b1;                 // FE starts the fetch / parser, AU flushes, two seam flops later
                        qh <= 0; qt <= 0; q_cnt <= 0;
                        st <= S_HD;
                    end
                end
                // ---- the head record: fault, FENCE, LOOP count, or wait mask -> indexed reads -> dispatch / END / TOKX
                S_HD: if (q_cnt != 0) begin
                    if (hd_kind == K_FLT) fault3;
                    else if (hd_rdy) begin
                        if (hd_flt) fault3;
                        else if (hd_kind == K_FENCE) st <= S_FEN;
                        else if (hd_kind == K_LVM) st <= S_LVW;
                        else if (hd_wok) begin
                            if (hd_pend) ;                                  // the resolver patches it
                            else if (hd_kind == K_DISP) begin
                                u_vr <= 16'd1 << hd_hdr[H_UNIT +: 4]; iss_q <= 16'd1 << hd_hdr[H_UNIT +: 4]; st <= S_DSP;
                            end else if (!vm_free) ;                        // the resolver owns the VM port
                            else if (hd_kind == K_END) begin
                                vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= hd_dsc[M_BASE +: 18]; st <= S_ENDRD;
                            end else begin                                  // TOKX: A[0] = k, then A[1..k]
                                if ({3'd0, hd_dsc[M_BASE +: 18]} + 21'd17 > 21'h40000) fault3;
                                else begin
                                    tk_base <= hd_dsc[M_BASE +: 18]; tk_i <= 5'd0; tk_k <= 1'b1; tk_pos <= pos;
                                    vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= hd_dsc[M_BASE +: 18]; st <= S_TOKX;
                                end
                            end
                        end
                    end
                end
                S_DSP: if (|u_tk) begin u_vr <= 16'd0; st <= S_HD; end
                S_FEN: if ((busy_u & 16'hFFFE) == 16'd0 && wr_quiet_r) st <= S_HD;
                S_LVW: if (hd_wok && vm_free) begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= hd_hdr[49:32]; st <= S_LVR; end
                S_LVR: if (vr_rsp_v_r) begin
                    if (vr_rsp_data_r == 32'd0 || vr_rsp_data_r[31:16] != 16'd0) fault3;
                    else begin be_lv_v <= 1'b1; be_lv_cnt <= vr_rsp_data_r[15:0]; st <= S_HD; end
                end
                S_ENDRD: if (vr_rsp_v_r) begin
                    st <= S_CPL; run_q <= 1'b0; be_stop <= 1'b1; cpl_pos <= pos;
                    cpl_token <= vr_rsp_data_r[17:0];
                    cpl_status <= (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) ? 4'd3 : 4'd0;
                end
                // CTL.TOKX (HGI-1 7.4, Q-MTP-1): each committed token is a completion beat {token A[i], pos + i - 1, 0}
                S_TOKX: if (vr_rsp_v_r) begin
                    if (tk_k) begin
                        if (vr_rsp_data_r == 32'd0 || vr_rsp_data_r > {27'd0, ncol == 4'd0, ncol}) fault3;
                        else begin
                            tk_k <= 1'b0; tk_n <= vr_rsp_data_r[4:0]; tk_i <= 5'd1;
                            vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= tk_base + 18'd1;
                        end
                    end else if (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) fault3;
                    else begin cpl_token <= vr_rsp_data_r[17:0]; cpl_pos <= tk_pos; cpl_status <= 4'd0; st <= S_TKB; end
                end
                S_TKB: if (cpl_hs_q) begin
                    tk_pos <= tk_pos + 20'd1;
                    if (tk_i == tk_n) st <= S_HD;
                    else begin
                        tk_i <= tk_i + 5'd1; vr_vr <= 1'b1; vr_new <= 1'b1; st <= S_TOKX;
`ifdef OT_HGI_SEQ_MUT_TOKX
                        vr_addr <= tk_base + {13'd0, tk_i};       // NEGATIVE CONTROL: the token address does not advance
`else
                        vr_addr <= tk_base + {13'd0, tk_i} + 18'd1;
`endif
                    end
                end
                S_CPL: if (cpl_hs_q) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
            if (st != S_DB3 || db_bad) begin
                if (q_alloc) qt <= qt + 1'b1;
                if (q_pop) qh <= qh + 1'b1;
                q_cnt <= q_cnt + {{QB{1'b0}}, q_alloc} - {{QB{1'b0}}, q_pop};
            end
        end
    end
    // ---- S4 TX data (R1): the re-injection item, one dedicated flop a bit (be_s4_v is set with be_inj above)
    always @(posedge clk) begin
        be_s4_ph <= be_ph; be_s4_base <= be_d[M_BASE +: 40]; be_s4_dmul <= be_d[M_DMUL +: 27]; be_s4_sp <= be_d[M_SPACE +: 2];
        be_s4_x <= be_xj ? Xv : 32'd0; be_s4_j <= be_j; be_s4_tag <= inj_e;
    end
endmodule
`default_nettype wire
