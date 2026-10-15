`timescale 1ns/1ps
// Real SU physical parent successor; compiled own2calendar and fixed cache stage start.
module ot_qfd_seq_su_bi_gateway #(
    parameter integer RRG = 0,   // el1011-q-seq: replicated tile reset (rst_regions); 0 = one u_rs copy
    parameter integer PCUT = 0,  // el1011-q-seq: exact controller path cuts (ctrl_pcut)
    parameter integer OLAG = 0,  // el1011-q-seq: lagged other-unit counter (ctrl_olag)
    parameter integer W = 16, parameter integer G = 3072, parameter integer AW = 24, parameter integer NW = 18,
    parameter integer PAW = 12, parameter integer SW = 64, parameter integer LV = 7, parameter integer D = 8,
    parameter integer SMIN = 7, parameter integer SMAX = 11, parameter integer TCUT = 7,
    parameter integer IS = 1, parameter integer OS = 1, parameter integer RT = 4,
    parameter integer RLY = 0, parameter integer CRED = 0,
    parameter integer ROW_LAT = 13, // measured NOX native row response latency
    parameter integer VWA = 20, // native VM row address; no implicit base
    // PSRAM = 1 (hardcore-1010 D fallback, 2026-10-10; 0 = unchanged): the 64 x 1,024 program store is two
    // ot_sram_1r1w_64x512_m1_r2c2 macros (64 x 512, bit-masked 64-bit writes) instead of 65,536 flops; the read is
    // issued at the prog_re edge with the unregistered address (12-bit add -> macro address pins), the macro output is
    // captured in prog_q one edge later = the PRL 2 timing of the flop store (0 cycles).  Contract: the store is
    // written only while no program read of the same word is in flight (boot load; read-before-write macro).
    // PMUT = 1: bench negative control (the read issued one edge late, with the registered address).
    parameter integer PSRAM = 1, parameter integer PMUT = 0,
    // HQ2 = 1 (hardcore-1010 fe-h): the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2):
    // fba-0ef4d7781 TT -131 / fbb post-CTS -537 on u_ctrl.st -> skip/issue -> load -> hq_fill -> hq[1023:0] enable (26 lv)
    // HQ2 = 2: bench negative control (FQ_HEAD 3: a third fill overwrites an unread head word)
    parameter integer HQ2 = 1,
    // qwen-tp8/seq (2026-10-12): tensor-parallel degree D (= TP, the dies of one tensor group; the argmax gather covers D
    // ranks) and lane groups G (TP4 6,144; TP8 3,072) are parameters; RBW = the collective's rank width (TP4 2, TP8 3).
    // The TP4 defaults (D 4, G 6144) elaborate to the unchanged block.  TPMUT: bench negative controls only (0 = off):
    // 1 = the rank compare sees only rank bits [1:0] (the old 2-bit literal), 2 = the gather ends after 4 ranks.
    parameter integer RBW = (D > 1) ? $clog2(D) : 1,
    parameter integer TPMUT = 0
) (
    // Actual external SU operand request -> existing core INT8 decoder -> SU.
    input wire [SW-1:0] su_va_re,
    input wire [SW*AW-1:0] su_va_addr,
    output wire [SW*32-1:0] su_va_q,
    output wire [SW-1:0] su_vm_va_re,
    output wire [SW*AW-1:0] su_vm_va_addr,
    input wire [SW*32-1:0] su_vm_va_q,
    output wire embed_code_re,
    output wire [AW-1:0] embed_code_addr,
    input wire [511:0] embed_code_q,
    output wire embed_scale_re,
    output wire [NW-1:0] embed_scale_addr,
    input wire [15:0] embed_scale_q,
    input wire ck_gateway,
    input wire clk,
    input wire ck_sched,
    // D1 receipts from the actual SRAM/descriptor write edges, not PW admission.
    output reg [75:0] program_obs,
    output reg [68:0] descriptor_obs,
    output reg cfg_image_ready,
    output wire [15:0] su_observe,
    input  wire rst_n,
    input  wire [1-1:0] h_start,
    input  wire [5:0] stage_in,           // the stage (layer / HEAD) this start runs
    input  wire [1-1:0] cb_st_rdy,        // constant buffer: stage cb_st_rdy_stage resident
    input  wire [5:0] cb_st_rdy_stage,
    output wire [5:0] cb_stage,           // to every constant-buffer group: the stage the SU runs
    output wire [1-1:0] cb_tok_start,
    output wire [NW-1:0] cb_tpos,
    input  wire [NW-1:0] tp_token,
    input  wire [NW-1:0] tp_pos,
    input  wire [1-1:0] kv_write_drained,
    input  wire [512-1:0] vm_rq,
    input  wire vm_rvalid, // actual completed row, aligned with vm_rq
    input  wire [1-1:0] c_ready,
    input  wire [1-1:0] r_valid,
    input  wire [512-1:0] r_data,
    input  wire [1-1:0] r_last,
    input  wire [RBW-1:0] r_rank,
    input  wire [1-1:0] r_err,
    input  wire [1-1:0] pw_v,
    input  wire [10-1:0] pw_addr,
    input  wire [64-1:0] pw_data,
    input  wire [1-1:0] dw_v,
    input  wire [3-1:0] dw_addr,
    input  wire [64-1:0] dw_data,
    input  wire [1-1:0] pi_su_rt_active,
    input  wire [8-1:0] pi_su_rt_inflight,
    input  wire [1-1:0] pi_su_ready,
    input  wire [1-1:0] pi_su_idle,
`ifndef OT_QFD_SEQ_SU_NOWROM
    // q14 r9: the split compute die's SU issues no weight-ROM reads (OT_QFD_SEQ_SU_NOWROM removes these two ports; the
    // controller's SU weight-read request is then absent, not tied at a pin)
    input  wire [1-1:0] pi_su_wrom_re,
    input  wire [AW-1:0] pi_su_wrom_addr,
`endif
    input  wire [SW-1:0] pi_su_kv_we,
    input  wire [16-1:0] pi_su_progress,
    input  wire [16-1:0] pi_su_progress_rows,
    input  wire [1-1:0] pi_su_fault,
    input  wire [24-1:0] x_oacc,
    input  wire [1-1:0] x_oidle,
    input  wire [16-1:0] x_oprog,
    input  wire [1-1:0] x_ofin,
    input  wire [NW-1:0] x_fidx,
    input  wire [32-1:0] x_fval,
    input  wire [24-1:0] pi_su_acc,
    output wire [1-1:0] s_done,
    output wire [NW-1:0] seq_ntok,
    output wire [32-1:0] seq_nval,
    output wire [1-1:0] s_fault,
    output wire [1-1:0] core_fault,
    output wire [1-1:0] coll_busy,
    output wire [1-1:0] kv_write_flush,
    output wire [1-1:0] vm_re,
    output wire [VWA-1:0] vm_raddr,
    output wire [1-1:0] vm_we,
    output wire [VWA-1:0] vm_waddr,
    output wire [512-1:0] vm_wdata,
    output wire [1-1:0] c_valid,
    output wire [512-1:0] c_data,
    output wire [1-1:0] c_last,
    output wire [1-1:0] c_mode,
    output wire [32-1:0] c_tag,
    output wire [1-1:0] rom_fault,
    output wire [1-1:0] su_asrc,
    output wire [NW-1:0] su_tok,
    output wire [1-1:0] po_su_go,
    output wire [NW-1:0] po_su_i_nout,
    output wire [NW-1:0] po_su_i_nin,
    output wire [1-1:0] po_su_i_asrc,
    output wire [AW-1:0] po_su_i_abase,
    output wire [AW-1:0] po_su_i_aso,
    output wire [AW-1:0] po_su_i_asi,
    output wire [1-1:0] po_su_i_bsrc,
    output wire [AW-1:0] po_su_i_bbase,
    output wire [AW-1:0] po_su_i_bso,
    output wire [AW-1:0] po_su_i_bsi,
    output wire [1-1:0] po_su_i_csrc,
    output wire [AW-1:0] po_su_i_cbase,
    output wire [AW-1:0] po_su_i_cso,
    output wire [AW-1:0] po_su_i_csi,
    output wire [2-1:0] po_su_i_ma,
    output wire [2-1:0] po_su_i_mb,
    output wire [3-1:0] po_su_i_ad,
    output wire [3-1:0] po_su_i_sfu,
    output wire [1-1:0] po_su_i_mc,
    output wire [1-1:0] po_su_i_md,
    output wire [2-1:0] po_su_i_dst,
    output wire [AW-1:0] po_su_i_dbase,
    output wire [AW-1:0] po_su_i_dso,
    output wire [AW-1:0] po_su_i_dsi,
    output wire [2-1:0] po_su_i_red,
    output wire [1-1:0] po_su_i_redsq,
    output wire [AW-1:0] po_su_i_rbase,
    output wire [AW-1:0] po_su_i_rso,
    output wire [32-1:0] po_su_i_imm1,
    output wire [32-1:0] po_su_i_imm2,
    output wire [1-1:0] me_start_o,
    output wire [NW-1:0] me_token_o,
    output wire [NW-1:0] me_pos_o,
    output wire [12-1:0] me_prog_base_o,
    output wire [24-1:0] su_acc_o,
    output wire [1-1:0] su_idle_o,
    output wire [16-1:0] su_prog_o,
    output wire [16-1:0] su_rows_o,
    output wire [1-1:0] kvd_v,
    output wire [AW-1:0] kvd_wbase,
    output wire [AW-1:0] kvd_ts,
    output wire [AW-1:0] kvd_ks,
    output wire [AW-1:0] kvd_js,
    output wire [AW-1:0] kvd_wcs,
    output wire [4-1:0] kvd_split,
    output wire [3-1:0] kvd_jsh,
    output wire [NW-1:0] kvd_tiles,
    output wire [NW-1:0] kvd_k,
    output wire [NW-1:0] kvd_nout,
    output wire [1-1:0] kvd_kindk,
    output wire [NW-1:0] kvd_pos
);
    wire rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));
    (* keep = "true" *) wire [8-1:0] rsv;   // RRG: one reset copy per region (el1011-q-seq)
    generate if (RRG != 0 && IS > 0) begin : g_rrg
        genvar rk;
        for (rk = 0; rk < 8; rk = rk + 1) begin : g_r
            (* keep = "true", dont_touch = "true" *) reg [IS-1:0] r;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) r <= {IS{1'b0}};
                else r <= {r, 1'b1};
            assign rsv[rk] = (RRG == 2 && rk == 0) ? 1'b0 : r[IS-1];   // RRG 2: negative control (u_seq copy held); RRG 3: vm_wdata bit flip only
        end
    end else begin : g_rr0
        assign rsv = {8{rs}};
    end endgenerate
    wire [1-1:0] q_h_start;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_h_start (.clk(clk), .rst_n(rsv[5]), .d(h_start), .q(q_h_start));
    wire [NW-1:0] q_tp_token;
    ot_hdc_delay #(.W(NW), .D(IS)) u_i_tp_token (.clk(clk), .rst_n(rsv[5]), .d(tp_token), .q(q_tp_token));
    wire [NW-1:0] q_tp_pos;
    ot_hdc_delay #(.W(NW), .D(IS)) u_i_tp_pos (.clk(clk), .rst_n(rsv[5]), .d(tp_pos), .q(q_tp_pos));
    wire [1-1:0] q_kv_write_drained;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_kv_write_drained (.clk(clk), .rst_n(rsv[5]), .d(kv_write_drained), .q(q_kv_write_drained));
    wire [512-1:0] q_vm_rq;
    ot_hdc_delay #(.W(512), .D(IS)) u_i_vm_rq (.clk(clk), .rst_n(rsv[5]), .d(vm_rq), .q(q_vm_rq));
    wire q_vm_rvalid;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_vm_rvalid (.clk(clk), .rst_n(rsv[5]), .d(vm_rvalid), .q(q_vm_rvalid));
    wire [1-1:0] q_c_ready;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_c_ready (.clk(clk), .rst_n(rsv[5]), .d(c_ready), .q(q_c_ready));
    wire [1-1:0] q_r_valid;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_r_valid (.clk(clk), .rst_n(rsv[5]), .d(r_valid), .q(q_r_valid));
    wire [512-1:0] q_r_data;
    ot_hdc_delay #(.W(512), .D(IS)) u_i_r_data (.clk(clk), .rst_n(rsv[5]), .d(r_data), .q(q_r_data));
    wire [1-1:0] q_r_last;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_r_last (.clk(clk), .rst_n(rsv[5]), .d(r_last), .q(q_r_last));
    wire [RBW-1:0] q_r_rank;
    ot_hdc_delay #(.W(RBW), .D(IS)) u_i_r_rank (.clk(clk), .rst_n(rsv[5]), .d(r_rank), .q(q_r_rank));
    wire [RBW-1:0] q_r_rank_s = (TPMUT == 1) ? (q_r_rank & RBW'(3)) : q_r_rank;   // TPMUT 1: negative control
    wire [1-1:0] q_r_err;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_r_err (.clk(clk), .rst_n(rsv[5]), .d(r_err), .q(q_r_err));
    wire [1-1:0] q_pw_v;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_pw_v (.clk(clk), .rst_n(rsv[5]), .d(pw_v), .q(q_pw_v));
    wire [10-1:0] q_pw_addr;
    ot_hdc_delay #(.W(10), .D(IS)) u_i_pw_addr (.clk(clk), .rst_n(rsv[5]), .d(pw_addr), .q(q_pw_addr));
    wire [64-1:0] q_pw_data;
    ot_hdc_delay #(.W(64), .D(IS)) u_i_pw_data (.clk(clk), .rst_n(rsv[5]), .d(pw_data), .q(q_pw_data));
    wire [1-1:0] q_dw_v;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_dw_v (.clk(clk), .rst_n(rsv[5]), .d(dw_v), .q(q_dw_v));
    wire [3-1:0] q_dw_addr;
    ot_hdc_delay #(.W(3), .D(IS)) u_i_dw_addr (.clk(clk), .rst_n(rsv[5]), .d(dw_addr), .q(q_dw_addr));
    wire [64-1:0] q_dw_data;
    ot_hdc_delay #(.W(64), .D(IS)) u_i_dw_data (.clk(clk), .rst_n(rsv[5]), .d(dw_data), .q(q_dw_data));
    wire [1-1:0] q_pi_su_rt_active;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_pi_su_rt_active (.clk(clk), .rst_n(rsv[3]), .d(pi_su_rt_active), .q(q_pi_su_rt_active));
    wire [8-1:0] q_pi_su_rt_inflight;
    ot_hdc_delay #(.W(8), .D(IS)) u_i_pi_su_rt_inflight (.clk(clk), .rst_n(rsv[3]), .d(pi_su_rt_inflight), .q(q_pi_su_rt_inflight));
    wire [1-1:0] q_pi_su_ready;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_pi_su_ready (.clk(clk), .rst_n(rsv[3]), .d(pi_su_ready), .q(q_pi_su_ready));
    wire [1-1:0] q_pi_su_idle;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_pi_su_idle (.clk(clk), .rst_n(rsv[3]), .d(pi_su_idle), .q(q_pi_su_idle));
    wire [1-1:0] q_pi_su_wrom_re;
    wire [AW-1:0] q_pi_su_wrom_addr;
`ifdef OT_QFD_SEQ_SU_NOWROM
    assign q_pi_su_wrom_re = 1'b0;          // no SU weight-ROM request exists on the split die (no pin, no flop)
    assign q_pi_su_wrom_addr = {AW{1'b0}};
`else
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_pi_su_wrom_re (.clk(clk), .rst_n(rsv[3]), .d(pi_su_wrom_re), .q(q_pi_su_wrom_re));
    ot_hdc_delay #(.W(AW), .D(IS)) u_i_pi_su_wrom_addr (.clk(clk), .rst_n(rsv[3]), .d(pi_su_wrom_addr), .q(q_pi_su_wrom_addr));
`endif
    wire [SW-1:0] q_pi_su_kv_we;
    ot_hdc_delay #(.W(SW), .D(IS)) u_i_pi_su_kv_we (.clk(clk), .rst_n(rsv[3]), .d(pi_su_kv_we), .q(q_pi_su_kv_we));
    wire [16-1:0] q_pi_su_progress;
    ot_hdc_delay #(.W(16), .D(IS), .RESET(1)) u_i_pi_su_progress (.clk(clk), .rst_n(rsv[3]), .d(pi_su_progress), .q(q_pi_su_progress));
    wire [16-1:0] q_pi_su_progress_rows;
    ot_hdc_delay #(.W(16), .D(IS), .RESET(1)) u_i_pi_su_progress_rows (.clk(clk), .rst_n(rsv[3]), .d(pi_su_progress_rows), .q(q_pi_su_progress_rows));
    wire [1-1:0] q_pi_su_fault;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_pi_su_fault (.clk(clk), .rst_n(rsv[3]), .d(pi_su_fault), .q(q_pi_su_fault));
    wire [24-1:0] q_x_oacc;
    ot_hdc_delay #(.W(24), .D(IS)) u_i_x_oacc (.clk(clk), .rst_n(rsv[4]), .d(x_oacc), .q(q_x_oacc));
    wire [1-1:0] q_x_oidle;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_x_oidle (.clk(clk), .rst_n(rsv[4]), .d(x_oidle), .q(q_x_oidle));
    wire [16-1:0] q_x_oprog;
    ot_hdc_delay #(.W(16), .D(IS)) u_i_x_oprog (.clk(clk), .rst_n(rsv[4]), .d(x_oprog), .q(q_x_oprog));
    wire [1-1:0] q_x_ofin;
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_x_ofin (.clk(clk), .rst_n(rsv[4]), .d(x_ofin), .q(q_x_ofin));
    wire [NW-1:0] q_x_fidx;
    ot_hdc_delay #(.W(NW), .D(IS)) u_i_x_fidx (.clk(clk), .rst_n(rsv[4]), .d(x_fidx), .q(q_x_fidx));
    wire [32-1:0] q_x_fval;
    ot_hdc_delay #(.W(32), .D(IS)) u_i_x_fval (.clk(clk), .rst_n(rsv[4]), .d(x_fval), .q(q_x_fval));
    wire [24-1:0] q_pi_su_acc;
    ot_hdc_delay #(.W(24), .D(IS), .RESET(1)) u_i_pi_su_acc (.clk(clk), .rst_n(rsv[3]), .d(pi_su_acc), .q(q_pi_su_acc));
    wire [1-1:0] b_s_done;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_s_done (.clk(clk), .rst_n(rsv[6]), .d(b_s_done), .q(s_done));
    wire [NW-1:0] b_seq_ntok;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_seq_ntok (.clk(clk), .rst_n(rsv[6]), .d(b_seq_ntok), .q(seq_ntok));
    wire [32-1:0] b_seq_nval;
    ot_hdc_delay #(.W(32), .D(OS)) u_o_seq_nval (.clk(clk), .rst_n(rsv[6]), .d(b_seq_nval), .q(seq_nval));
    wire [1-1:0] b_s_fault;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_s_fault (.clk(clk), .rst_n(rsv[6]), .d(b_s_fault), .q(s_fault));
    wire [1-1:0] b_core_fault;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_core_fault (.clk(clk), .rst_n(rsv[6]), .d(b_core_fault), .q(core_fault));
    wire [1-1:0] b_coll_busy;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_coll_busy (.clk(clk), .rst_n(rsv[6]), .d(b_coll_busy), .q(coll_busy));
    wire [1-1:0] b_kv_write_flush;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_kv_write_flush (.clk(clk), .rst_n(rsv[5]), .d(b_kv_write_flush), .q(kv_write_flush));
    wire [1-1:0] b_vm_re;
    wire [VWA-1:0] b_vm_raddr;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_vm_re (.clk(clk), .rst_n(rsv[6]), .d(b_vm_re), .q(vm_re));
    ot_hdc_delay #(.W(VWA), .D(OS)) u_o_vm_raddr (.clk(clk), .rst_n(rsv[6]), .d(b_vm_raddr), .q(vm_raddr));
    wire [1-1:0] b_vm_we;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_vm_we (.clk(clk), .rst_n(rsv[6]), .d(b_vm_we), .q(vm_we));
    wire [VWA-1:0] b_vm_waddr;
    ot_hdc_delay #(.W(VWA), .D(OS)) u_o_vm_waddr (.clk(clk), .rst_n(rsv[6]), .d(b_vm_waddr), .q(vm_waddr));
    wire [512-1:0] b_vm_wdata;
    ot_hdc_delay #(.W(512), .D(OS)) u_o_vm_wdata (.clk(clk), .rst_n(rsv[6]), .d(b_vm_wdata), .q(vm_wdata));
    wire [1-1:0] b_c_valid;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_c_valid (.clk(clk), .rst_n(rsv[6]), .d(b_c_valid), .q(c_valid));
    wire [512-1:0] b_c_data;
    ot_hdc_delay #(.W(512), .D(OS)) u_o_c_data (.clk(clk), .rst_n(rsv[6]), .d(b_c_data), .q(c_data));
    wire [1-1:0] b_c_last;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_c_last (.clk(clk), .rst_n(rsv[6]), .d(b_c_last), .q(c_last));
    wire [1-1:0] b_c_mode;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_c_mode (.clk(clk), .rst_n(rsv[6]), .d(b_c_mode), .q(c_mode));
    wire [32-1:0] b_c_tag;
    ot_hdc_delay #(.W(32), .D(OS)) u_o_c_tag (.clk(clk), .rst_n(rsv[6]), .d(b_c_tag), .q(c_tag));
    wire [1-1:0] b_rom_fault;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_rom_fault (.clk(clk), .rst_n(rsv[6]), .d(b_rom_fault), .q(rom_fault));
    wire [1-1:0] b_su_asrc;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_su_asrc (.clk(clk), .rst_n(rsv[3]), .d(b_su_asrc), .q(su_asrc));
    wire [NW-1:0] b_su_tok;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_su_tok (.clk(clk), .rst_n(rsv[3]), .d(b_su_tok), .q(su_tok));
    wire [1-1:0] b_po_su_go;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_go (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_go), .q(po_su_go));
    wire [NW-1:0] b_po_su_i_nout;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_po_su_i_nout (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_nout), .q(po_su_i_nout));
    wire [NW-1:0] b_po_su_i_nin;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_po_su_i_nin (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_nin), .q(po_su_i_nin));
    wire [1-1:0] b_po_su_i_asrc;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_i_asrc (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_asrc), .q(po_su_i_asrc));
    wire [AW-1:0] b_po_su_i_abase;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_abase (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_abase), .q(po_su_i_abase));
    wire [AW-1:0] b_po_su_i_aso;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_aso (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_aso), .q(po_su_i_aso));
    wire [AW-1:0] b_po_su_i_asi;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_asi (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_asi), .q(po_su_i_asi));
    wire [1-1:0] b_po_su_i_bsrc;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_i_bsrc (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_bsrc), .q(po_su_i_bsrc));
    wire [AW-1:0] b_po_su_i_bbase;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_bbase (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_bbase), .q(po_su_i_bbase));
    wire [AW-1:0] b_po_su_i_bso;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_bso (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_bso), .q(po_su_i_bso));
    wire [AW-1:0] b_po_su_i_bsi;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_bsi (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_bsi), .q(po_su_i_bsi));
    wire [1-1:0] b_po_su_i_csrc;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_i_csrc (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_csrc), .q(po_su_i_csrc));
    wire [AW-1:0] b_po_su_i_cbase;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_cbase (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_cbase), .q(po_su_i_cbase));
    wire [AW-1:0] b_po_su_i_cso;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_cso (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_cso), .q(po_su_i_cso));
    wire [AW-1:0] b_po_su_i_csi;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_csi (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_csi), .q(po_su_i_csi));
    wire [2-1:0] b_po_su_i_ma;
    ot_hdc_delay #(.W(2), .D(OS)) u_o_po_su_i_ma (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_ma), .q(po_su_i_ma));
    wire [2-1:0] b_po_su_i_mb;
    ot_hdc_delay #(.W(2), .D(OS)) u_o_po_su_i_mb (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_mb), .q(po_su_i_mb));
    wire [3-1:0] b_po_su_i_ad;
    ot_hdc_delay #(.W(3), .D(OS)) u_o_po_su_i_ad (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_ad), .q(po_su_i_ad));
    wire [3-1:0] b_po_su_i_sfu;
    ot_hdc_delay #(.W(3), .D(OS)) u_o_po_su_i_sfu (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_sfu), .q(po_su_i_sfu));
    wire [1-1:0] b_po_su_i_mc;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_i_mc (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_mc), .q(po_su_i_mc));
    wire [1-1:0] b_po_su_i_md;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_i_md (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_md), .q(po_su_i_md));
    wire [2-1:0] b_po_su_i_dst;
    ot_hdc_delay #(.W(2), .D(OS)) u_o_po_su_i_dst (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_dst), .q(po_su_i_dst));
    wire [AW-1:0] b_po_su_i_dbase;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_dbase (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_dbase), .q(po_su_i_dbase));
    wire [AW-1:0] b_po_su_i_dso;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_dso (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_dso), .q(po_su_i_dso));
    wire [AW-1:0] b_po_su_i_dsi;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_dsi (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_dsi), .q(po_su_i_dsi));
    wire [2-1:0] b_po_su_i_red;
    ot_hdc_delay #(.W(2), .D(OS)) u_o_po_su_i_red (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_red), .q(po_su_i_red));
    wire [1-1:0] b_po_su_i_redsq;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_po_su_i_redsq (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_redsq), .q(po_su_i_redsq));
    wire [AW-1:0] b_po_su_i_rbase;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_rbase (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_rbase), .q(po_su_i_rbase));
    wire [AW-1:0] b_po_su_i_rso;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_po_su_i_rso (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_rso), .q(po_su_i_rso));
    wire [32-1:0] b_po_su_i_imm1;
    ot_hdc_delay #(.W(32), .D(OS)) u_o_po_su_i_imm1 (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_imm1), .q(po_su_i_imm1));
    wire [32-1:0] b_po_su_i_imm2;
    ot_hdc_delay #(.W(32), .D(OS)) u_o_po_su_i_imm2 (.clk(clk), .rst_n(rsv[3]), .d(b_po_su_i_imm2), .q(po_su_i_imm2));
    wire [1-1:0] b_me_start_o;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_me_start_o (.clk(clk), .rst_n(rsv[4]), .d(b_me_start_o), .q(me_start_o));
    wire [NW-1:0] b_me_token_o;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_me_token_o (.clk(clk), .rst_n(rsv[4]), .d(b_me_token_o), .q(me_token_o));
    wire [NW-1:0] b_me_pos_o;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_me_pos_o (.clk(clk), .rst_n(rsv[4]), .d(b_me_pos_o), .q(me_pos_o));
    wire [12-1:0] b_me_prog_base_o;
    ot_hdc_delay #(.W(12), .D(OS)) u_o_me_prog_base_o (.clk(clk), .rst_n(rsv[4]), .d(b_me_prog_base_o), .q(me_prog_base_o));
    wire [24-1:0] b_su_acc_o;
    ot_hdc_delay #(.W(24), .D(OS), .RESET(1)) u_o_su_acc_o (.clk(clk), .rst_n(rsv[4]), .d(b_su_acc_o), .q(su_acc_o));
    wire [1-1:0] b_su_idle_o;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_su_idle_o (.clk(clk), .rst_n(rsv[4]), .d(b_su_idle_o), .q(su_idle_o));
    wire [16-1:0] b_su_prog_o;
    ot_hdc_delay #(.W(16), .D(OS), .RESET(1)) u_o_su_prog_o (.clk(clk), .rst_n(rsv[4]), .d(b_su_prog_o), .q(su_prog_o));
    wire [16-1:0] b_su_rows_o;
    wire [1-1:0] b_kvd_v;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_kvd_v (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_v), .q(kvd_v));
    wire [AW-1:0] b_kvd_wbase;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_kvd_wbase (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_wbase), .q(kvd_wbase));
    wire [AW-1:0] b_kvd_ts;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_kvd_ts (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_ts), .q(kvd_ts));
    wire [AW-1:0] b_kvd_ks;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_kvd_ks (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_ks), .q(kvd_ks));
    wire [AW-1:0] b_kvd_js;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_kvd_js (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_js), .q(kvd_js));
    wire [AW-1:0] b_kvd_wcs;
    ot_hdc_delay #(.W(AW), .D(OS)) u_o_kvd_wcs (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_wcs), .q(kvd_wcs));
    wire [4-1:0] b_kvd_split;
    ot_hdc_delay #(.W(4), .D(OS)) u_o_kvd_split (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_split), .q(kvd_split));
    wire [3-1:0] b_kvd_jsh;
    ot_hdc_delay #(.W(3), .D(OS)) u_o_kvd_jsh (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_jsh), .q(kvd_jsh));
    wire [NW-1:0] b_kvd_tiles;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_kvd_tiles (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_tiles), .q(kvd_tiles));
    wire [NW-1:0] b_kvd_k;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_kvd_k (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_k), .q(kvd_k));
    wire [NW-1:0] b_kvd_nout;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_kvd_nout (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_nout), .q(kvd_nout));
    wire [1-1:0] b_kvd_kindk;
    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_kvd_kindk (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_kindk), .q(kvd_kindk));
    wire [NW-1:0] b_kvd_pos;
    ot_hdc_delay #(.W(NW), .D(OS)) u_o_kvd_pos (.clk(clk), .rst_n(rsv[5]), .d(b_kvd_pos), .q(kvd_pos));
    ot_hdc_delay #(.W(16), .D(OS), .RESET(1)) u_o_su_rows_o (.clk(clk), .rst_n(rsv[4]), .d(b_su_rows_o), .q(su_rows_o));
    wire s_su_ready, s_su_idle; wire [15:0] s_su_progress, s_su_progress_rows; reg [NW-1:0] tok_l; wire es_re_w;
        ot_qfd_issue_shell #(.RT_ME(0), .RT_SU(RT), .COMP(1)) u_shell (.clk(clk), .rst_n(rsv[7]),
        .me_go(1'b0), .su_go(b_po_su_go), .me_en(1'b1), .su_sfu(b_po_su_i_sfu), .me_amax(1'b0),
        .d_me_ready(1'b0), .d_me_idle(1'b0), .d_me_progress(16'd0),
        .d_su_ready(q_pi_su_ready), .d_su_idle(q_pi_su_idle), .d_su_active(q_pi_su_rt_active),
        .d_su_inflight(q_pi_su_rt_inflight), .d_su_progress(q_pi_su_progress), .d_su_rows(q_pi_su_progress_rows),
        .c_me_ready(), .c_me_idle(), .c_me_progress(),
        .c_su_ready(s_su_ready), .c_su_idle(s_su_idle), .c_su_progress(s_su_progress), .c_su_rows(s_su_progress_rows));
    wire image_ready_w,segment_image_ready,segment_requires_cbuf;
    wire fixed_issue,fixed_end,schedule_fault,candidate_v,candidate_available,candidate_end_ok,stage_fault;
    wire [11:0] candidate_pc,fixed_pc;wire[1:0]candidate_unit,fixed_unit;
    ot_qwen_fixed_issue_pw #(.OWN(2),.DENSE_IMAGE(1))u_fixed_issue(
     .clk(ck_sched),.rst_n(rsv[2]),.pw_v(q_pw_v),.pw_addr(q_pw_addr),.pw_data(q_pw_data),
     .start(core_start&&prog_base==0),.stage(sg_stage),
     .candidate_v(candidate_v),.candidate_pc(prog_base+candidate_pc),.candidate_unit(candidate_unit),
     .available(candidate_available),.end_ok(candidate_end_ok),.cp_available(1'b0),
     .issue_v(fixed_issue),.end_v(fixed_end),.issue_pc(fixed_pc),.issue_unit(fixed_unit),
     .active(),.done(),.cycle(),.fault(schedule_fault),.image_ready(image_ready_w),.cp_cmd(),.cp_v());
    // True source-decoder issue observation, registered at the same source
    // output edge as the SU command. No expected PC or ready can fabricate it.
    ot_qfd_su_source_observer u_source_observer(
      .clk(clk),.rst_n(rsv[3]),.issue(fixed_issue),.candidate_v(candidate_v),
      .unit(fixed_unit),.program_base(prog_base),.candidate_pc(candidate_pc),.observe(su_observe));
    wire core_start, core_done, core_fault_w; wire [NW-1:0] core_tok, core_pos, core_ntok, core_tokw; wire [31:0] core_nval;
    always @(posedge clk) if (es_re_w) tok_l <= core_tokw;
    assign b_su_tok = tok_l;
    wire prog_re; wire [11:0] prog_addr, prog_base; reg [1023:0] prog_q;
    wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;
    reg [1023:0] prog_mem [0:63];                       // PSRAM 0 (the flop store)
    reg [63:0] desc_mem [0:7];
    wire [11:0] prog_a = prog_base + prog_addr;
    reg prog_re_r; reg [11:0] prog_a_r;                 // PRL 2: the read address registered
    always @(posedge clk or negedge rsv[7]) if (!rsv[7]) prog_re_r <= 1'b0; else prog_re_r <= prog_re;
    always @(posedge clk) prog_a_r <= prog_a;
    reg [63:0] pw_row2; reg [15:0] pw_word2; reg [63:0] pw_d2; integer pw_r, pw_w;
    always @(posedge clk) begin
        if (q_dw_v) desc_mem[q_dw_addr] <= q_dw_data;
        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;
    end
    wire [1:0] cfg_pm_ce;wire [11:0]cfg_pm_row;wire[1023:0]cfg_pm_data,cfg_pm_mask;
    wire cfg_pw_v,cfg_pw_full;wire[9:0]cfg_pw_addr;wire[63:0]cfg_pw_data;
    qkd_program_pw_observer u_cfg_observe(.macro_ce(cfg_pm_ce),.macro_row(cfg_pm_row),.macro_data(cfg_pm_data),.macro_mask(cfg_pm_mask),
      .consumed_v(cfg_pw_v),.consumed_addr(cfg_pw_addr),.consumed_data(cfg_pw_data),.full_word(cfg_pw_full));
    always @(posedge clk or negedge rsv[5])
      if(!rsv[5])begin program_obs<=0;descriptor_obs<=0;cfg_image_ready<=0;end
      else begin
       program_obs<={cfg_pw_v,cfg_pw_full,cfg_pw_addr,cfg_pw_data};
       descriptor_obs<={q_dw_v,1'b1,q_dw_addr,q_dw_data};
       cfg_image_ready<=image_ready_w&&segment_image_ready;
      end
    generate if (PSRAM != 0) begin : g_psram
        //: the program store as two 64 x 512 SRAM macros (bit-masked 64-bit slice writes); prog_q = the captured output
        reg rng_r;                                       // the read word is inside the store (else prog_q = 0)
        always @(posedge clk) rng_r <= (PMUT != 0) ? (prog_a_r < 64) : (prog_a < 64);
        wire [1023:0] p_rd;
        wire p_rce = (PMUT != 0) ? prog_re_r : prog_re;
        wire [5:0] p_ra = (PMUT != 0) ? prog_a_r[5:0] : prog_a[5:0];
        genvar m;
        for (m = 0; m < 2; m = m + 1) begin : g_m
            wire w_ce = q_pw_v && (q_pw_addr[3] == ((m != 0) ? 1'b1 : 1'b0));
            wire [511:0] w_mask = {448'd0, {64{1'b1}}} << (64 * q_pw_addr[2:0]);
            assign cfg_pm_ce[m]=w_ce;
            assign cfg_pm_row[m*6+:6]=q_pw_addr[9:4];
            assign cfg_pm_data[m*512+:512]={8{q_pw_data}};
            assign cfg_pm_mask[m*512+:512]=w_mask;
            ot_sram_1r1w_64x512_m1_r2c2 u_pm (.clk(clk), .r_ce_in(p_rce), .r_addr_in(p_ra), .rd_out(p_rd[512*m +: 512]),
                .w_ce_in(w_ce), .w_addr_in(q_pw_addr[9:4]), .wd_in({8{q_pw_data}}), .w_mask_in(w_mask),
                .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        end
        if (PMUT != 0) begin : g_pmut
            reg pre_rr;
            always @(posedge clk or negedge rsv[7]) if (!rsv[7]) pre_rr <= 1'b0; else pre_rr <= prog_re_r;
            always @(posedge clk) if (pre_rr) prog_q <= rng_r ? p_rd : 1024'd0;
        end else begin : g_pq
            always @(posedge clk) if (prog_re_r) prog_q <= rng_r ? p_rd : 1024'd0;
        end
    end else begin : g_pflop
        always @(posedge clk) begin
            if (pw_row2 != 64'd0) for (pw_r = 0; pw_r < 64; pw_r = pw_r + 1) for (pw_w = 0; pw_w < 16; pw_w = pw_w + 1)
                if (pw_row2[pw_r] && pw_word2[pw_w]) prog_mem[pw_r][pw_w*64 +: 64] <= pw_d2;
        end
        // program writes: one-hot row / word selects registered one edge before the store (65,536 enables)
        always @(posedge clk) begin
            pw_row2 <= q_pw_v ? (64'd1 << q_pw_addr[9:4]) : 64'd0;
            pw_word2 <= 16'd1 << q_pw_addr[3:0];
            pw_d2 <= q_pw_data;
            if (prog_re_r) prog_q <= (prog_a_r < 64) ? prog_mem[prog_a_r[5:0]] : 1024'd0;
        end
    end endgenerate
    assign embed_scale_re = es_re_w;
    wire wrom_re_w; assign b_rom_fault = wrom_re_w; assign b_core_fault = core_fault_w;
    ot_qwen_rom_core_ctrl_su_gateway #(.OWN(2), .XW(24), .XMUT(0), .XREG(1), .ICUT(1), .PRL(2), .W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(1), .SW(SW), .LV(LV), .KV_FP8(1), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1), .INT8_EMBED(1), .QWEN_FULLSHAPE(1), .HID(4096), .HALF(64), .HD(128), .EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .KV_HBM(1), .KV_VEC_WRITE_BRIDGE(1), .ME_STALL(1), .ME_IDLE_GATE(1), .PCUT(PCUT), .OLAG(OLAG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .FQ_HEAD((HQ2 >= 2) ? 3 : (HQ2 != 0) ? 2 : 1)) u_ctrl (
        .clk(clk),.ck_gateway(ck_gateway),
        .rst_n(rsv[2]),
        .start(core_start),
        .fixed_issue(fixed_issue),.fixed_end(fixed_end),.fixed_unit(fixed_unit),.fixed_fault(schedule_fault|stage_fault),
        .candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),
        .candidate_available(candidate_available),.candidate_end_ok(candidate_end_ok),
        .token(core_tokw),
        .pos(core_pos),
        .done(core_done),
        .next_token(core_ntok),
        .next_val(core_nval),
        .cycles(),
        .fault(core_fault_w),
        .prog_re(prog_re),
        .prog_addr(prog_addr),
        .prog_q(prog_q),
        .wrom_re(wrom_re_w),
        .wrom_addr(),
        .wrom_q('0),
        .int8_wrom_re(),
        .int8_wrom_addr(),
        .scale_re(),
        .scale_gre(),
        .scale_addr(),
        .scale_q('0),
        .embed_code_re(embed_code_re),
        .embed_code_addr(embed_code_addr),
        .embed_code_q(embed_code_q),
        .embed_scale_re(es_re_w),
        .embed_scale_addr(embed_scale_addr),
        .embed_scale_q(embed_scale_q),
        .crom_re(),
        .crom_addr(),
        .crom_q('0),
        .kv_re(),
        .kv_we(),
        .kv_waddr(),
        .kv_wdata(),
        .kv_write_drained(q_kv_write_drained),
        .kv_write_flush(b_kv_write_flush),
        .va_re(su_vm_va_re),
        .va_addr(su_vm_va_addr),
        .va_q(su_vm_va_q),
        .vb_re(),
        .vb_addr(),
        .vb_q('0),
        .vc_re(),
        .vc_addr(),
        .vc_q('0),
        .vw_me_we(),
        .vw_me_addr(),
        .vw_me_mask(),
        .vw_me_data(),
        .vw_su_we(),
        .vw_su_addr(),
        .vw_su_data(),
        .vw_rd_we(),
        .vw_rd_addr(),
        .vw_rd_data(),
        .vw_mx_we(),
        .vw_mx_addr(),
        .vw_mx_mask(),
        .vw_mx_data(),
        .me_ov(),
        .kvd_v(b_kvd_v),
        .kvd_wbase(b_kvd_wbase),
        .kvd_ts(b_kvd_ts),
        .kvd_ks(b_kvd_ks),
        .kvd_js(b_kvd_js),
        .kvd_wcs(b_kvd_wcs),
        .kvd_split(b_kvd_split),
        .kvd_jsh(b_kvd_jsh),
        .kvd_tiles(b_kvd_tiles),
        .kvd_k(b_kvd_k),
        .kvd_nout(b_kvd_nout),
        .kvd_kindk(b_kvd_kindk),
        .kvd_pos(b_kvd_pos),
        .kv_ok(1'b0),
        .wrom_su(),
        .wd_v(),
        .wd_wbase(),
        .wd_sbase(),
        .wd_tiles(),
        .wd_k(),
        .wd_nout(),
        .vx_re(),
        .vx_addr(),
        .vx_q('0),
        .tgo(),
        .tb(),
        .xl_d(),
        .t_lvl('0),
        .fab_fault(1'b0),
        .w_ok(1'b1),
        .emb_ok(1'b1),
        .me_mem_ok(1'b0),
        .me_clk_en(),
        .po_me_clk(),
        .po_me_go(),
        .pi_me_ready('0),
        .pi_me_idle('0),
        .po_me_i_nout(),
        .po_me_i_tiles(),
        .po_me_i_k(),
        .po_me_i_wsrc(),
        .po_me_i_wbase(),
        .po_me_i_ts(),
        .po_me_i_ks(),
        .po_me_i_js(),
        .po_me_i_xbase(),
        .po_me_i_xks(),
        .po_me_i_xjs(),
        .po_me_i_xcs(),
        .po_me_i_jsh(),
        .po_me_i_split(),
        .po_me_i_wcs(),
        .po_me_i_round(),
        .po_me_i_obase(),
        .po_me_i_ots(),
        .po_me_i_ojs(),
        .po_me_i_mmode(),
        .po_me_i_oen(),
        .po_me_i_amax(),
        .po_me_i_rmax(),
        .po_me_i_mbase(),
        .pi_me_mx_we('0),
        .pi_me_wrom_re('0),
        .pi_me_wrom_addr('0),
        .pi_me_o_we('0),
        .pi_me_am_idx('0),
        .pi_me_am_val('0),
        .pi_me_am_any('0),
        .pi_me_progress('0),
        .pi_me_fault('0),
        .pi_su_rt_active(q_pi_su_rt_active),
        .pi_su_rt_inflight(q_pi_su_rt_inflight),
        .po_su_go(b_po_su_go),
        .pi_su_ready(s_su_ready),
        .pi_su_idle(s_su_idle),
        .po_su_i_nout(b_po_su_i_nout),
        .po_su_i_nin(b_po_su_i_nin),
        .po_su_i_asrc(b_po_su_i_asrc),
        .po_su_i_abase(b_po_su_i_abase),
        .po_su_i_aso(b_po_su_i_aso),
        .po_su_i_asi(b_po_su_i_asi),
        .po_su_i_bsrc(b_po_su_i_bsrc),
        .po_su_i_bbase(b_po_su_i_bbase),
        .po_su_i_bso(b_po_su_i_bso),
        .po_su_i_bsi(b_po_su_i_bsi),
        .po_su_i_csrc(b_po_su_i_csrc),
        .po_su_i_cbase(b_po_su_i_cbase),
        .po_su_i_cso(b_po_su_i_cso),
        .po_su_i_csi(b_po_su_i_csi),
        .po_su_i_ma(b_po_su_i_ma),
        .po_su_i_mb(b_po_su_i_mb),
        .po_su_i_ad(b_po_su_i_ad),
        .po_su_i_sfu(b_po_su_i_sfu),
        .po_su_i_mc(b_po_su_i_mc),
        .po_su_i_md(b_po_su_i_md),
        .po_su_i_dst(b_po_su_i_dst),
        .po_su_i_dbase(b_po_su_i_dbase),
        .po_su_i_dso(b_po_su_i_dso),
        .po_su_i_dsi(b_po_su_i_dsi),
        .po_su_i_red(b_po_su_i_red),
        .po_su_i_redsq(b_po_su_i_redsq),
        .po_su_i_rbase(b_po_su_i_rbase),
        .po_su_i_rso(b_po_su_i_rso),
        .po_su_i_imm1(b_po_su_i_imm1),
        .po_su_i_imm2(b_po_su_i_imm2),
        .pi_su_va_re(su_va_re),
        .pi_su_va_addr(su_va_addr),
        .po_su_va_q(su_va_q),
        .pi_su_wrom_re(q_pi_su_wrom_re),
        .pi_su_wrom_addr(q_pi_su_wrom_addr),
        .pi_su_kv_we(q_pi_su_kv_we),
        .pi_su_progress(s_su_progress),
        .pi_su_progress_rows(s_su_progress_rows),
        .pi_su_fault(q_pi_su_fault),
        .po_su_asrc_raw(b_su_asrc),
        .x_oacc(q_x_oacc),
        .x_oidle(q_x_oidle),
        .x_oprog(q_x_oprog),
        .x_orows(16'd0),
        .x_ofin(q_x_ofin),
        .x_fidx(q_x_fidx),
        .x_fval(q_x_fval),
        .o_fin(),
        .o_fidx(),
        .o_fval());
    wire [5:0] q_stage_in, q_cb_st_rdy_stage; wire q_cb_st_rdy;
    ot_hdc_delay #(.W(12), .D(IS)) u_i_cbs (.clk(clk), .rst_n(rsv[6]), .d({stage_in, cb_st_rdy_stage}), .q({q_stage_in, q_cb_st_rdy_stage}));
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_cbr (.clk(clk), .rst_n(rsv[6]), .d(cb_st_rdy), .q(q_cb_st_rdy));
    wire sg_go, sg_tok; wire [NW-1:0] sg_token, sg_pos; wire [5:0] sg_stage;
    ot_qfd_stage_gate_static #(.SW_(6), .NW(NW)) u_sgate (.clk(clk), .rst_n(rsv[7]), .h_start(q_h_start), .stage(q_stage_in),
        .token(q_tp_token), .pos(q_tp_pos), .requires_cbuf(segment_requires_cbuf),.st_rdy(q_cb_st_rdy), .st_rdy_stage(q_cb_st_rdy_stage), .go(sg_go),
        .go_token(sg_token), .go_pos(sg_pos), .cur_stage(sg_stage), .tok_start(sg_tok),.fault(stage_fault));
    ot_hdc_delay #(.W(6 + 1 + NW), .D(OS)) u_o_cb (.clk(clk), .rst_n(rsv[6]), .d({sg_stage, sg_tok, q_tp_pos}), .q({cb_stage, cb_tok_start, cb_tpos}));
    ot_qwen_tp_seq_calendar #(.VRL(IS + OS + ROW_LAT + 2 * RLY), .N((TPMUT == 2) ? 4 : D), .NW(NW), .PAW(PAW), .VWA(VWA), .DAW(6), .FW(512), .RB(3)) u_seq (
        .clk(clk), .stage(sg_stage),.pw_v(q_pw_v),.pw_addr(q_pw_addr),.pw_data(q_pw_data),.image_ready(segment_image_ready),.requires_cbuf(segment_requires_cbuf),
        .rst_n(rsv[0]), .rst_nw(rsv[1]), .start(sg_go), .token(sg_token), .pos(sg_pos), .done(b_s_done),
        .next_token(b_seq_ntok), .next_val(b_seq_nval), .fault(b_s_fault), .coll_busy(b_coll_busy),
        .core_start(core_start), .core_token(core_tokw), .core_pos(core_pos), .core_done(core_done),
        .core_next_token(core_ntok), .core_next_val(core_nval), .core_fault(core_fault_w), .prog_base(prog_base),
        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(b_vm_re), .vm_raddr(b_vm_raddr),
        .vm_rq(q_vm_rq), .vm_rvalid(q_vm_rvalid), .vm_we(b_vm_we), .vm_waddr(b_vm_waddr), .vm_wdata(b_vm_wdata), .c_valid(b_c_valid),
        .c_ready(q_c_ready), .c_data(b_c_data), .c_last(b_c_last), .c_mode(b_c_mode), .c_tag(b_c_tag),
        .r_valid(q_r_valid), .r_data(q_r_data), .r_last(q_r_last), .r_rank(q_r_rank_s), .r_err(q_r_err));
    assign b_me_start_o = core_start;
    assign b_me_token_o = core_tokw;
    assign b_me_pos_o = core_pos;
    assign b_me_prog_base_o = prog_base;
    assign b_su_acc_o = q_pi_su_acc;
    assign b_su_idle_o = q_pi_su_idle;
    assign b_su_prog_o = q_pi_su_progress;
    assign b_su_rows_o = q_pi_su_progress_rows;
endmodule
