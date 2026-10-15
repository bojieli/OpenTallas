`timescale 1ns/1ps
// NEW static physical masters; archived closed head/tree remain unchanged.
// Fixed normal engine cadence; actual decoder/fold state, no shadow controller.
module qfd_tt_ctlm_head_static #(
    parameter integer DCU_M = 2, parameter integer DUC_M = 2,   // in-tile issue / status stations
    parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1,
    // PSRAM = 1 (fe-push-qwen-1010, port of the seq_su_bi hardcore-1010 PSRAM; 0 = unchanged): the 64 x 1,024 program
    // store is two ot_sram_1r1w_64x512_m1_r2c2 macros (bit-masked 64-bit writes) instead of 65,536 flops; the read is
    // issued at the prog_re edge with the unregistered address, the macro output captured in prog_q one edge later = the
    // PRL 2 timing of the flop store (0 cycles).  Writes come from registered macro pins (valid, row, bank, one-hot
    // 64-bit slice) one edge after q_pw_v, as the flop store's registered selects.  Contract: the store is written
    // only while no program read of the same word is in flight (boot load; read-before-write macro).
    // PMUT = 1: bench negative control (the read issued one edge late, with the registered address).
    // HQ2 = 1: the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2; seq_su fea/feb
    // f3e3d6b6f: feb TT +95.26 after fbb post-CTS -537 on st -> load -> hq_fill -> 1,024-b hq enable).
    // HQ2 = 2: bench negative control (FQ_HEAD 3: a third fill overwrites an unread head word).
    parameter integer DENSE_IMAGE=1,
    parameter integer PSRAM = 1, parameter integer PMUT = 0, parameter integer HQ2 = 1,
    parameter integer MEREG = 3,  // el1011-q-seq: registered engine clock enable (ctlm_mereg)
    parameter integer RRG = 1,    // el1011-q-seq: replicated tile reset (ctlm_rrg)
    parameter integer PCUT = 1,   // el1011-q-seq: exact controller path cuts (ctrl_pcut)
    // qwen-tp8/seq (2026-10-12): G = lane groups of the die (TP4 6,144; TP8 3,072 = 768 tiles in 3 bands).  It sets the
    // controller's G (dynamic attention rounds, ot_hdc_dyn_ttiles), the tree-top control's GT, and the G-sized ports:
    // NPG = G >> 7 scale groups, NPE = NPG / 4 argmax partials (p_am / p_fault: 2 per band), t_sel_e / t_tv_e
    // $clog2(G) + 1 bits.  The default elaborates to the unchanged TP4 block.
    parameter integer G = 3072,
    parameter integer TPMUT = 0,  // qwen-tp8/seq bench negative controls (0 = off): 1 = DYN_TTILES rounds at the TP4 literal
                                  //   G 6144 (:496-507 left), 2 = the controller instance at G 6144 (:1224 left)
    parameter integer AUD = 33975     // el1011-q-seq: textbook-audit rebuild (ctlm_aud) bits: 1 no x_addr, 2 SRAM tag delays, 4 kv pin flops, 16 die-input pin flops (not p_am), 32 kept output stations, 64 no engine idle clock gate (power; the ICG enable then = the registered supply word); 8 = SRAM one-short mutant; 128 exact prefix cuts (u_tt PK: KS progress subtract + registered u_ttag read; controller FKS: argmax-merge compare / add); 256 = PK negative control, 512 = FKS negative control; 1024 setup cuts SC (fpapk-4e9afc303 classes a-d, exact, 0 cycles: u_tt pre-scale compare from flops, mx write pre-decoded with a registered slot maximum, scale_addr 2-operand, 32 h_rd copies); negative controls 2048 (no rk forwarding), 4096 (>= for >), 8192 (offset without nbs), 16384 (h_rd copy 0 stuck); 32768 p_am pin register at the ctlm pin (coordinator 10-11: routed p_am -> argmax -58 ps, textbook class 3; the argmax loop +1 cycle: am_* / mx_* / idle one edge later, sequence unchanged), 65536 = its negative control (register without the +1 compensation)
) (
    input wire clk,
    input wire ck_sched,
    input wire cp_active,
    output reg [55:0] cp,
    output reg layer_context_v,
    output reg [17:0] native_tok,native_pos,
    output wire me_image_ready,
    output reg [75:0] program_obs,
    input wire  rst_n,
    input wire  h_start,
    input wire [18-1:0] token,
    input wire [18-1:0] pos,
    input wire [11:0] prog_base,
    input wire  pw_v,
    input wire [9:0] pw_addr,
    input wire [63:0] pw_data,
    input wire [XW-1:0] x_oacc,
    input wire  x_oidle,
    input wire [15:0] x_oprog,
    input wire [15:0] x_orows,
    input wire  kv_ok,
    input wire  kv_write_drained,
    input wire  me_mem_ok,
    output wire  m_fin_o,
    output wire [18-1:0] m_fidx_o,
    output wire [31:0] m_fval_o,
    output wire  me_clk_en,
    output wire  c_fault,
    output wire  kvd_v,
    output wire [24-1:0] kvd_wbase,
    output wire [24-1:0] kvd_ts,
    output wire [24-1:0] kvd_ks,
    output wire [24-1:0] kvd_js,
    output wire [24-1:0] kvd_wcs,
    output wire [3:0] kvd_split,
    output wire [2:0] kvd_jsh,
    output wire [18-1:0] kvd_tiles,
    output wire [18-1:0] kvd_k,
    output wire [18-1:0] kvd_nout,
    output wire  kvd_kindk,
    output wire [18-1:0] kvd_pos,
    output wire [379:0] cmd,
    output reg [15:0] me_observe,
    input wire [94:0] ret
);

    wire rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));
    wire kv_ok_c, kvwd_c;   // AUD: pin flops (kv_ok / kv_write_drained announced one edge ahead)
    generate if ((AUD & 4) != 0) begin : g_kvreg
        reg kv_ok_q, kvwd_q;
        always @(posedge clk) begin kv_ok_q <= kv_ok; kvwd_q <= kv_write_drained; end
        assign kv_ok_c = kv_ok_q; assign kvwd_c = kvwd_q;
    end else begin : g_kvdir
        assign kv_ok_c = kv_ok; assign kvwd_c = kv_write_drained;
    end endgenerate
    (* keep = "true" *) wire [8-1:0] rsv;   // RRG: reset copies (el1011-q-seq)
    wire [8-1:0] rrv;                      // the raw-port users: rsv under RRG, else rst_n
    generate if (RRG != 0 && IS > 0) begin : g_rrg
        genvar rk;
        for (rk = 0; rk < 8; rk = rk + 1) begin : g_r
            (* keep = "true", dont_touch = "true" *) reg [IS-1:0] r;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) r <= {IS{1'b0}};
                else r <= {r, 1'b1};
            assign rsv[rk] = r[IS-1];
        end
        assign rrv = rsv;
    end else begin : g_rr0
        assign rsv = {8{rs}};
        assign rrv = {8{rst_n}};
    end endgenerate
    // die-facing input pin stations (registered boundary); kv_ok / kv_write_drained / me_mem_ok stay direct (readiness
    // the controller pairs with its own same-edge state, and the ICG enable path)
    wire q_h_start; wire [18-1:0] q_token, q_pos; wire [11:0] q_prog_base; wire q_pw_v; wire [9:0] q_pw_addr; wire [63:0] q_pw_data;
    wire [XW-1:0] q_x_oacc; wire q_x_oidle; wire [15:0] q_x_oprog, q_x_orows;
    ot_hdc_delay #(.W(3), .D(IS), .RESET(1)) u_is1 (.clk(clk), .rst_n(rrv[3]), .d({h_start, pw_v, x_oidle}), .q({q_h_start, q_pw_v, q_x_oidle}));
    ot_hdc_delay #(.W(2*18 + 12 + 10 + 64 + XW + 32), .D(IS)) u_isd (.clk(clk), .rst_n(rrv[4]),
        .d({token, pos, prog_base, pw_addr, pw_data, x_oacc, x_oprog, x_orows}),
        .q({q_token, q_pos, q_prog_base, q_pw_addr, q_pw_data, q_x_oacc, q_x_oprog, q_x_orows}));
    // program-store copy (the sequencer master's semantics)
    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q;
    wire [11:0] prog_a = q_prog_base + prog_addr;
    reg prog_re_r; reg [11:0] prog_a_r;                 // PRL 2: the read address registered
    always @(posedge clk or negedge rsv[7]) if (!rsv[7]) prog_re_r <= 1'b0; else prog_re_r <= prog_re;
    always @(posedge clk) prog_a_r <= prog_a;
    generate if (PSRAM != 0) begin : g_psram
        //: the program store as two 64 x 512 SRAM macros; every macro write pin from a register (no decode at the pins)
        reg pw_v2, pw_b2; reg [5:0] pw_row2; reg [7:0] pw_sl2; reg [63:0] pw_d2;
        always @(posedge clk or negedge rsv[7]) if (!rsv[7]) pw_v2 <= 1'b0; else pw_v2 <= q_pw_v;
        always @(posedge clk) begin
            pw_b2 <= q_pw_addr[3]; pw_row2 <= q_pw_addr[9:4]; pw_sl2 <= 8'd1 << q_pw_addr[2:0]; pw_d2 <= q_pw_data;
        end
        reg rng_r;                                       // the read word is inside the store (else prog_q = 0)
        always @(posedge clk) rng_r <= (PMUT != 0) ? (prog_a_r < 64) : (prog_a < 64);
        wire [1023:0] p_rd;
        wire p_rce = (PMUT != 0) ? prog_re_r : prog_re;
        wire [5:0] p_ra = (PMUT != 0) ? prog_a_r[5:0] : prog_a[5:0];
        wire [511:0] w_mask;
        genvar m, s;
        for (s = 0; s < 8; s = s + 1) begin : g_s
            assign w_mask[64*s +: 64] = {64{pw_sl2[s]}};
        end
        wire [1:0] program_raw_ce;wire [11:0] program_raw_row;wire [1023:0]program_raw_data,program_raw_mask;
        for (m = 0; m < 2; m = m + 1) begin : g_m
            wire w_ce = pw_v2 && (pw_b2 == ((m != 0) ? 1'b1 : 1'b0));
            assign program_raw_ce[m]=w_ce;assign program_raw_row[6*m+:6]=pw_row2;
            assign program_raw_data[512*m+:512]={8{pw_d2}};assign program_raw_mask[512*m+:512]=w_mask;
            ot_sram_1r1w_64x512_m1_r2c2 u_pm (.clk(clk), .r_ce_in(p_rce), .r_addr_in(p_ra), .rd_out(p_rd[512*m +: 512]),
                .w_ce_in(program_raw_ce[m]), .w_addr_in(program_raw_row[6*m+:6]), .wd_in(program_raw_data[512*m+:512]), .w_mask_in(program_raw_mask[512*m+:512]),
                .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        end
        wire observed_v,observed_full;wire [9:0]observed_addr;wire [63:0]observed_data;
        qkd_program_pw_observer u_program_observer(.macro_ce(program_raw_ce),.macro_row(program_raw_row),.macro_data(program_raw_data),.macro_mask(program_raw_mask),.consumed_v(observed_v),.consumed_addr(observed_addr),.consumed_data(observed_data),.full_word(observed_full));
        always @(posedge clk or negedge rst_n)
          if(!rst_n)program_obs<=0;else program_obs<={observed_v,observed_full,observed_addr,observed_data};
        if (PMUT != 0) begin : g_pmut
            reg pre_rr;
            always @(posedge clk or negedge rsv[7]) if (!rsv[7]) pre_rr <= 1'b0; else pre_rr <= prog_re_r;
            always @(posedge clk) if (pre_rr) prog_q <= rng_r ? p_rd : 1024'd0;
        end else begin : g_pq
            always @(posedge clk) if (prog_re_r) prog_q <= rng_r ? p_rd : 1024'd0;
        end
    end else begin : g_pflop
        reg [9:0]observed_ff_addr;
        always @(posedge clk)observed_ff_addr<=q_pw_addr;
        always @(posedge clk or negedge rst_n)
          if(!rst_n)program_obs<=0;else program_obs<={|pw_row2,((pw_row2&(pw_row2-1))==0)&&((pw_word2&(pw_word2-1))==0),observed_ff_addr,pw_d2};
        reg [1023:0] prog_mem [0:63];
        reg [63:0] pw_row2; reg [15:0] pw_word2; reg [63:0] pw_d2; integer pw_r, pw_w;
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
    wire [1-1:0] c_me_clk, u_me_clk;
    wire [1-1:0] c_me_go, u_me_go;
    wire [1-1:0] c_me_ready, u_me_ready;
    wire [1-1:0] c_me_idle, u_me_idle;
    wire [18-1:0] c_me_i_nout, u_me_i_nout;
    wire [18-1:0] c_me_i_tiles, u_me_i_tiles;
    wire [18-1:0] c_me_i_k, u_me_i_k;
    wire [1-1:0] c_me_i_wsrc, u_me_i_wsrc;
    wire [24-1:0] c_me_i_wbase, u_me_i_wbase;
    wire [24-1:0] c_me_i_ts, u_me_i_ts;
    wire [24-1:0] c_me_i_ks, u_me_i_ks;
    wire [24-1:0] c_me_i_js, u_me_i_js;
    wire [24-1:0] c_me_i_xbase, u_me_i_xbase;
    wire [24-1:0] c_me_i_xks, u_me_i_xks;
    wire [24-1:0] c_me_i_xjs, u_me_i_xjs;
    wire [24-1:0] c_me_i_xcs, u_me_i_xcs;
    wire [3-1:0] c_me_i_jsh, u_me_i_jsh;
    wire [4-1:0] c_me_i_split, u_me_i_split;
    wire [24-1:0] c_me_i_wcs, u_me_i_wcs;
    wire [1-1:0] c_me_i_round, u_me_i_round;
    wire [24-1:0] c_me_i_obase, u_me_i_obase;
    wire [24-1:0] c_me_i_ots, u_me_i_ots;
    wire [24-1:0] c_me_i_ojs, u_me_i_ojs;
    wire [1-1:0] c_me_i_mmode, u_me_i_mmode;
    wire [1-1:0] c_me_i_oen, u_me_i_oen;
    wire [1-1:0] c_me_i_amax, u_me_i_amax;
    wire [1-1:0] c_me_i_rmax, u_me_i_rmax;
    wire [24-1:0] c_me_i_mbase, u_me_i_mbase;
    wire [1-1:0] c_me_mx_we, u_me_mx_we;
    wire [1-1:0] c_me_wrom_re, u_me_wrom_re;
    wire [24-1:0] c_me_wrom_addr, u_me_wrom_addr;
    wire [(G >> 7)-1:0] c_me_o_we, u_me_o_we;
    wire [18-1:0] c_me_am_idx, u_me_am_idx;
    wire [32-1:0] c_me_am_val, u_me_am_val;
    wire [1-1:0] c_me_am_any, u_me_am_any;
    wire [16-1:0] c_me_progress, u_me_progress;
    wire [1-1:0] c_me_fault, u_me_fault;
    wire fixed_issue,fixed_end,schedule_fault,candidate_v,candidate_available,candidate_end_ok,cp_v,accepted_start,schedule_active;
    wire [55:0] cp_cmd;
    wire [11:0] candidate_pc,fixed_pc;
    wire [1:0] candidate_unit,fixed_unit;
    reg cp_active_q;
    always @(posedge ck_sched or negedge rst_n)
      if(!rst_n)cp_active_q<=0;
      else cp_active_q<=cp_active;
    reg program_load_fault;
    always @(posedge clk or negedge rst_n)
      if(!rst_n)program_load_fault<=0;
      else if(q_pw_v && q_pw_addr<976 && schedule_active)program_load_fault<=1;
    always @(posedge clk or negedge rrv[6])
      if(!rrv[6])begin layer_context_v<=0;native_tok<=0;native_pos<=0;end
      else begin
        layer_context_v<=accepted_start && q_prog_base==0;
        if(accepted_start)begin native_tok<=q_token;native_pos<=q_pos;end
      end
    reg [5:0] schedule_stage;
    always @(posedge ck_sched or negedge rst_n)
      if(!rst_n) schedule_stage<=0;
      else if(q_pw_v && q_pw_addr==1017) schedule_stage<=q_pw_data[17:12];
    // ck_sched and clk are independently entered, compiler phase-matched roots.
    // Candidate is sampled at the real decoder issue phase; there is no wait.
    ot_qwen_fixed_issue_pw #(.DENSE_IMAGE(DENSE_IMAGE),.OWN(1)) u_fixed_issue (
      .clk(ck_sched),.rst_n(rsv[1]),.pw_v(q_pw_v),.pw_addr(q_pw_addr),.pw_data(q_pw_data),
      .start(q_h_start && q_prog_base==0),.stage(schedule_stage),
      .candidate_v(candidate_v),.candidate_pc(q_prog_base+candidate_pc),.candidate_unit(candidate_unit),
      .available(candidate_available),.end_ok(candidate_end_ok),.cp_available(!cp_active_q),
      .issue_v(fixed_issue),.end_v(fixed_end),.cp_cmd(cp_cmd),.cp_v(cp_v),.issue_pc(fixed_pc),.issue_unit(fixed_unit),
      .active(schedule_active),.done(),.cycle(),.image_ready(me_image_ready),.fault(schedule_fault));
    wire s_me_ready, s_me_idle; wire [15:0] s_me_progress; wire m_fin; wire [18-1:0] m_fidx; wire [31:0] m_fval;
    ot_qwen_rom_core_ctrl_static #(.OWN(1), .XW(XW), .XMUT(0), .XREG(1), .ICUT(1), .PRL(2), .W(16), .G((TPMUT == 2) ? 6144 : G), .DG((TPMUT != 0) ? 6144 : G), .AW(24), .NW(18), .PAW(12), .SU_VEC(1), .SW(64), .LV(7), .KV_FP8(1), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1), .INT8_EMBED(1), .QWEN_FULLSHAPE(1), .HID(4096), .HALF(64), .HD(128), .EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .KV_HBM(1), .KV_VEC_WRITE_BRIDGE(1), .ME_STALL(1), .ME_IDLE_GATE(((AUD & 64) != 0) ? 0 : 1), .MEREG(MEREG), .PCUT(PCUT), .FKS(((AUD & 512) != 0) ? 2 : ((AUD & 128) != 0) ? 1 : 0), .HRC(((AUD & 1024) != 0) ? 32 : 0), .HRCM(((AUD & 16384) != 0) ? 1 : 0), .SMIN(7), .SMAX(11), .TCUT(7), .FQ_HEAD((HQ2 >= 2) ? 3 : (HQ2 != 0) ? 2 : 1)) u_ctrl_me (
        .clk(clk),
        .rst_n(rsv[1]),
        .start(q_h_start),
        .fixed_issue(fixed_issue),.fixed_end(fixed_end),.fixed_unit(fixed_unit),.fixed_fault(schedule_fault|program_load_fault),
        .accepted_start(accepted_start),.candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),
        .candidate_available(candidate_available),.candidate_end_ok(candidate_end_ok),
        .token(q_token),
        .pos(q_pos),
        .done(),
        .next_token(),
        .next_val(),
        .cycles(),
        .fault(c_fault),
        .prog_re(prog_re),
        .prog_addr(prog_addr),
        .prog_q(prog_q),
        .wrom_re(),
        .wrom_addr(),
        .wrom_q('0),
        .int8_wrom_re(),
        .int8_wrom_addr(),
        .scale_re(),
        .scale_gre(),
        .scale_addr(),
        .scale_q('0),
        .embed_code_re(),
        .embed_code_addr(),
        .embed_code_q('0),
        .embed_scale_re(),
        .embed_scale_addr(),
        .embed_scale_q('0),
        .crom_re(),
        .crom_addr(),
        .crom_q('0),
        .kv_re(),
        .kv_we(),
        .kv_waddr(),
        .kv_wdata(),
        .kv_write_drained(kvwd_c),
        .kv_write_flush(),
        .va_re(),
        .va_addr(),
        .va_q('0),
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
        .kvd_v(kvd_v),
        .kvd_wbase(kvd_wbase),
        .kvd_ts(kvd_ts),
        .kvd_ks(kvd_ks),
        .kvd_js(kvd_js),
        .kvd_wcs(kvd_wcs),
        .kvd_split(kvd_split),
        .kvd_jsh(kvd_jsh),
        .kvd_tiles(kvd_tiles),
        .kvd_k(kvd_k),
        .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk),
        .kvd_pos(kvd_pos),
        .kv_ok(kv_ok_c),
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
        .me_mem_ok(me_mem_ok),
        .me_clk_en(me_clk_en),
        .po_me_clk(c_me_clk),
        .po_me_go(c_me_go),
        .pi_me_ready(s_me_ready),
        .pi_me_idle(s_me_idle),
        .po_me_i_nout(c_me_i_nout),
        .po_me_i_tiles(c_me_i_tiles),
        .po_me_i_k(c_me_i_k),
        .po_me_i_wsrc(c_me_i_wsrc),
        .po_me_i_wbase(c_me_i_wbase),
        .po_me_i_ts(c_me_i_ts),
        .po_me_i_ks(c_me_i_ks),
        .po_me_i_js(c_me_i_js),
        .po_me_i_xbase(c_me_i_xbase),
        .po_me_i_xks(c_me_i_xks),
        .po_me_i_xjs(c_me_i_xjs),
        .po_me_i_xcs(c_me_i_xcs),
        .po_me_i_jsh(c_me_i_jsh),
        .po_me_i_split(c_me_i_split),
        .po_me_i_wcs(c_me_i_wcs),
        .po_me_i_round(c_me_i_round),
        .po_me_i_obase(c_me_i_obase),
        .po_me_i_ots(c_me_i_ots),
        .po_me_i_ojs(c_me_i_ojs),
        .po_me_i_mmode(c_me_i_mmode),
        .po_me_i_oen(c_me_i_oen),
        .po_me_i_amax(c_me_i_amax),
        .po_me_i_rmax(c_me_i_rmax),
        .po_me_i_mbase(c_me_i_mbase),
        .pi_me_mx_we('0),
        .pi_me_wrom_re(c_me_wrom_re),
        .pi_me_wrom_addr(c_me_wrom_addr),
        .pi_me_o_we('0),
        .pi_me_am_idx(c_me_am_idx),
        .pi_me_am_val(c_me_am_val),
        .pi_me_am_any(c_me_am_any),
        .pi_me_progress(s_me_progress),
        .pi_me_fault(c_me_fault),
        .pi_su_rt_active('0),
        .pi_su_rt_inflight('0),
        .po_su_go(),
        .pi_su_ready('0),
        .pi_su_idle('0),
        .po_su_i_nout(),
        .po_su_i_nin(),
        .po_su_i_asrc(),
        .po_su_i_abase(),
        .po_su_i_aso(),
        .po_su_i_asi(),
        .po_su_i_bsrc(),
        .po_su_i_bbase(),
        .po_su_i_bso(),
        .po_su_i_bsi(),
        .po_su_i_csrc(),
        .po_su_i_cbase(),
        .po_su_i_cso(),
        .po_su_i_csi(),
        .po_su_i_ma(),
        .po_su_i_mb(),
        .po_su_i_ad(),
        .po_su_i_sfu(),
        .po_su_i_mc(),
        .po_su_i_md(),
        .po_su_i_dst(),
        .po_su_i_dbase(),
        .po_su_i_dso(),
        .po_su_i_dsi(),
        .po_su_i_red(),
        .po_su_i_redsq(),
        .po_su_i_rbase(),
        .po_su_i_rso(),
        .po_su_i_imm1(),
        .po_su_i_imm2(),
        .pi_su_va_re('0),
        .pi_su_va_addr('0),
        .po_su_va_q(),
        .pi_su_wrom_re('0),
        .pi_su_wrom_addr('0),
        .pi_su_kv_we('0),
        .pi_su_progress('0),
        .pi_su_progress_rows('0),
        .pi_su_fault('0),
        .po_su_asrc_raw(),
        .x_oacc(q_x_oacc),
        .x_oidle(q_x_oidle),
        .x_oprog(q_x_oprog),
        .x_orows(q_x_orows),
        .x_ofin(1'b1),
        .x_fidx('0),
        .x_fval('0),
        .o_fin(m_fin),
        .o_fidx(m_fidx),
        .o_fval(m_fval));
    ot_qfd_issue_shell #(.RT_ME(DCU_M + DUC_M), .RT_SU(0), .COMP(1)) u_shell_me (.clk(clk), .rst_n(rsv[5]),
        .me_go(c_me_go), .su_go(1'b0), .me_en(me_clk_en), .su_sfu(3'd0), .me_amax(c_me_i_amax),
        .d_me_ready(c_me_ready), .d_me_idle(c_me_idle), .d_me_progress(c_me_progress),
        .d_su_ready(1'b0), .d_su_idle(1'b0), .d_su_active(1'b0), .d_su_inflight(8'd0), .d_su_progress(16'd0), .d_su_rows(16'd0),
        .c_me_ready(s_me_ready), .c_me_idle(s_me_idle), .c_me_progress(s_me_progress),
        .c_su_ready(), .c_su_idle(), .c_su_progress(), .c_su_rows());
    ot_tt_ce_delay #(.W(1), .D(1), .RESET(1)) u_sd_me_go (.clk(clk), .en(me_clk_en), .rst_n(rrv[6]), .d(c_me_go), .q(u_me_go));
    ot_tt_ce_delay #(.W(1), .D(1), .RESET(1)) u_su_me_ready (.clk(clk), .en(me_clk_en), .rst_n(rrv[7]), .d(u_me_ready), .q(c_me_ready));
    ot_tt_ce_delay #(.W(1), .D(1), .RESET(1)) u_su_me_idle (.clk(clk), .en(me_clk_en), .rst_n(rrv[2]), .d(u_me_idle), .q(c_me_idle));
    ot_tt_ce_delay #(.W(18), .D(1)) u_sd_me_i_nout (.clk(clk), .en(me_clk_en), .rst_n(rrv[3]), .d(c_me_i_nout), .q(u_me_i_nout));
    ot_tt_ce_delay #(.W(18), .D(1)) u_sd_me_i_tiles (.clk(clk), .en(me_clk_en), .rst_n(rrv[4]), .d(c_me_i_tiles), .q(u_me_i_tiles));
    ot_tt_ce_delay #(.W(18), .D(1)) u_sd_me_i_k (.clk(clk), .en(me_clk_en), .rst_n(rrv[5]), .d(c_me_i_k), .q(u_me_i_k));
    ot_tt_ce_delay #(.W(1), .D(1)) u_sd_me_i_wsrc (.clk(clk), .en(me_clk_en), .rst_n(rrv[6]), .d(c_me_i_wsrc), .q(u_me_i_wsrc));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_wbase (.clk(clk), .en(me_clk_en), .rst_n(rrv[7]), .d(c_me_i_wbase), .q(u_me_i_wbase));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_ts (.clk(clk), .en(me_clk_en), .rst_n(rrv[2]), .d(c_me_i_ts), .q(u_me_i_ts));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_ks (.clk(clk), .en(me_clk_en), .rst_n(rrv[3]), .d(c_me_i_ks), .q(u_me_i_ks));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_js (.clk(clk), .en(me_clk_en), .rst_n(rrv[4]), .d(c_me_i_js), .q(u_me_i_js));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_xbase (.clk(clk), .en(me_clk_en), .rst_n(rrv[5]), .d(c_me_i_xbase), .q(u_me_i_xbase));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_xks (.clk(clk), .en(me_clk_en), .rst_n(rrv[6]), .d(c_me_i_xks), .q(u_me_i_xks));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_xjs (.clk(clk), .en(me_clk_en), .rst_n(rrv[7]), .d(c_me_i_xjs), .q(u_me_i_xjs));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_xcs (.clk(clk), .en(me_clk_en), .rst_n(rrv[2]), .d(c_me_i_xcs), .q(u_me_i_xcs));
    ot_tt_ce_delay #(.W(3), .D(1)) u_sd_me_i_jsh (.clk(clk), .en(me_clk_en), .rst_n(rrv[3]), .d(c_me_i_jsh), .q(u_me_i_jsh));
    ot_tt_ce_delay #(.W(4), .D(1)) u_sd_me_i_split (.clk(clk), .en(me_clk_en), .rst_n(rrv[4]), .d(c_me_i_split), .q(u_me_i_split));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_wcs (.clk(clk), .en(me_clk_en), .rst_n(rrv[5]), .d(c_me_i_wcs), .q(u_me_i_wcs));
    ot_tt_ce_delay #(.W(1), .D(1)) u_sd_me_i_round (.clk(clk), .en(me_clk_en), .rst_n(rrv[6]), .d(c_me_i_round), .q(u_me_i_round));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_obase (.clk(clk), .en(me_clk_en), .rst_n(rrv[7]), .d(c_me_i_obase), .q(u_me_i_obase));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_ots (.clk(clk), .en(me_clk_en), .rst_n(rrv[2]), .d(c_me_i_ots), .q(u_me_i_ots));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_ojs (.clk(clk), .en(me_clk_en), .rst_n(rrv[3]), .d(c_me_i_ojs), .q(u_me_i_ojs));
    ot_tt_ce_delay #(.W(1), .D(1)) u_sd_me_i_mmode (.clk(clk), .en(me_clk_en), .rst_n(rrv[4]), .d(c_me_i_mmode), .q(u_me_i_mmode));
    ot_tt_ce_delay #(.W(1), .D(1)) u_sd_me_i_oen (.clk(clk), .en(me_clk_en), .rst_n(rrv[5]), .d(c_me_i_oen), .q(u_me_i_oen));
    ot_tt_ce_delay #(.W(1), .D(1)) u_sd_me_i_amax (.clk(clk), .en(me_clk_en), .rst_n(rrv[6]), .d(c_me_i_amax), .q(u_me_i_amax));
    ot_tt_ce_delay #(.W(1), .D(1)) u_sd_me_i_rmax (.clk(clk), .en(me_clk_en), .rst_n(rrv[7]), .d(c_me_i_rmax), .q(u_me_i_rmax));
    ot_tt_ce_delay #(.W(24), .D(1)) u_sd_me_i_mbase (.clk(clk), .en(me_clk_en), .rst_n(rrv[2]), .d(c_me_i_mbase), .q(u_me_i_mbase));
    ot_tt_ce_delay #(.W(1), .D(1), .RESET(1)) u_su_me_wrom_re (.clk(clk), .en(me_clk_en), .rst_n(rrv[3]), .d(u_me_wrom_re), .q(c_me_wrom_re));
    ot_tt_ce_delay #(.W(24), .D(1)) u_su_me_wrom_addr (.clk(clk), .en(me_clk_en), .rst_n(rrv[4]), .d(u_me_wrom_addr), .q(c_me_wrom_addr));
    ot_tt_ce_delay #(.W(18), .D(1)) u_su_me_am_idx (.clk(clk), .en(me_clk_en), .rst_n(rrv[5]), .d(u_me_am_idx), .q(c_me_am_idx));
    ot_tt_ce_delay #(.W(32), .D(1)) u_su_me_am_val (.clk(clk), .en(me_clk_en), .rst_n(rrv[6]), .d(u_me_am_val), .q(c_me_am_val));
    ot_tt_ce_delay #(.W(1), .D(1), .RESET(1)) u_su_me_am_any (.clk(clk), .en(me_clk_en), .rst_n(rrv[7]), .d(u_me_am_any), .q(c_me_am_any));
    ot_tt_ce_delay #(.W(16), .D(1), .RESET(1)) u_su_me_progress (.clk(clk), .en(me_clk_en), .rst_n(rrv[2]), .d(u_me_progress), .q(c_me_progress));
    ot_tt_ce_delay #(.W(1), .D(1), .RESET(1)) u_su_me_fault (.clk(clk), .en(me_clk_en), .rst_n(rrv[3]), .d(u_me_fault), .q(c_me_fault));
    always @(posedge clk or negedge rrv[6])
      if(!rrv[6])begin me_observe<=0;cp<=0;end
      else begin me_observe<={fixed_issue||cp_v,candidate_v,fixed_unit,q_prog_base+candidate_pc};cp<=cp_cmd;end
    assign cmd = {u_me_i_mbase, u_me_i_rmax, u_me_i_amax, u_me_i_oen, u_me_i_mmode, u_me_i_ojs, u_me_i_ots, u_me_i_obase, u_me_i_round, u_me_i_wcs, u_me_i_split, u_me_i_jsh, u_me_i_xcs, u_me_i_xjs, u_me_i_xks, u_me_i_xbase, u_me_i_js, u_me_i_ks, u_me_i_ts, u_me_i_wbase, u_me_i_wsrc, u_me_i_k, u_me_i_tiles, u_me_i_nout, u_me_go};
    assign {u_me_fault, u_me_progress, u_me_am_any, u_me_am_val, u_me_am_idx, u_me_wrom_addr, u_me_wrom_re, u_me_idle, u_me_ready} = ret;
    ot_hdc_delay #(.W(1),.D(OS),.RESET(1)) u_os_fin (.clk(clk),.rst_n(rsv[4]),.d(m_fin),.q(m_fin_o));
    ot_hdc_delay #(.W(18 + 32), .D(OS)) u_os_f (.clk(clk), .rst_n(rsv[5]), .d({m_fidx, m_fval}), .q({m_fidx_o, m_fval_o}));
endmodule
module qfd_tt_ctlm_tree_static #(
    parameter integer DCU_M = 2, parameter integer DUC_M = 2,   // in-tile issue / status stations
    parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1,
    // PSRAM = 1 (fe-push-qwen-1010, port of the seq_su_bi hardcore-1010 PSRAM; 0 = unchanged): the 64 x 1,024 program
    // store is two ot_sram_1r1w_64x512_m1_r2c2 macros (bit-masked 64-bit writes) instead of 65,536 flops; the read is
    // issued at the prog_re edge with the unregistered address, the macro output captured in prog_q one edge later = the
    // PRL 2 timing of the flop store (0 cycles).  Writes come from registered macro pins (valid, row, bank, one-hot
    // 64-bit slice) one edge after q_pw_v, as the flop store's registered selects.  Contract: the store is written
    // only while no program read of the same word is in flight (boot load; read-before-write macro).
    // PMUT = 1: bench negative control (the read issued one edge late, with the registered address).
    // HQ2 = 1: the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2; seq_su fea/feb
    // f3e3d6b6f: feb TT +95.26 after fbb post-CTS -537 on st -> load -> hq_fill -> 1,024-b hq enable).
    // HQ2 = 2: bench negative control (FQ_HEAD 3: a third fill overwrites an unread head word).
    parameter integer PSRAM = 1, parameter integer PMUT = 0, parameter integer HQ2 = 1,
    parameter integer MEREG = 3,  // el1011-q-seq: registered engine clock enable (ctlm_mereg)
    parameter integer RRG = 1,    // el1011-q-seq: replicated tile reset (ctlm_rrg)
    parameter integer PCUT = 1,   // el1011-q-seq: exact controller path cuts (ctrl_pcut)
    // qwen-tp8/seq (2026-10-12): G = lane groups of the die (TP4 6,144; TP8 3,072 = 768 tiles in 3 bands).  It sets the
    // controller's G (dynamic attention rounds, ot_hdc_dyn_ttiles), the tree-top control's GT, and the G-sized ports:
    // NPG = G >> 7 scale groups, NPE = NPG / 4 argmax partials (p_am / p_fault: 2 per band), t_sel_e / t_tv_e
    // $clog2(G) + 1 bits.  The default elaborates to the unchanged TP4 block.
    parameter integer G = 3072,
    parameter integer TPMUT = 0,  // qwen-tp8/seq bench negative controls (0 = off): 1 = DYN_TTILES rounds at the TP4 literal
                                  //   G 6144 (:496-507 left), 2 = the controller instance at G 6144 (:1224 left)
    parameter integer AUD = 33975     // el1011-q-seq: textbook-audit rebuild (ctlm_aud) bits: 1 no x_addr, 2 SRAM tag delays, 4 kv pin flops, 16 die-input pin flops (not p_am), 32 kept output stations, 64 no engine idle clock gate (power; the ICG enable then = the registered supply word); 8 = SRAM one-short mutant; 128 exact prefix cuts (u_tt PK: KS progress subtract + registered u_ttag read; controller FKS: argmax-merge compare / add); 256 = PK negative control, 512 = FKS negative control; 1024 setup cuts SC (fpapk-4e9afc303 classes a-d, exact, 0 cycles: u_tt pre-scale compare from flops, mx write pre-decoded with a registered slot maximum, scale_addr 2-operand, 32 h_rd copies); negative controls 2048 (no rk forwarding), 4096 (>= for >), 8192 (offset without nbs), 16384 (h_rd copy 0 stuck); 32768 p_am pin register at the ctlm pin (coordinator 10-11: routed p_am -> argmax -58 ps, textbook class 3; the argmax loop +1 cycle: am_* / mx_* / idle one edge later, sequence unchanged), 65536 = its negative control (register without the +1 compensation)
) (
    input wire  clk,
    input wire  rst_n,
    output wire [XW-1:0] me_acc_o,
    output wire  me_idle_o,
    output wire [15:0] me_prog_o,
    input wire  up_fault,
    input wire [15:0] land_cnt,
    output wire  scale_re,
    output wire [(G >> 7)-1:0] scale_gre,
    output wire [(G >> 7)*24-1:0] scale_addr,
    output wire [$clog2(G):0] t_sel_e,
    output wire [$clog2(G):0] t_tv_e,
    input wire [16-1:0] tr_fault,
    output wire  p_v_e2,
    output wire [113-1:0] p_f_e2,
    input wire [((G >> 7) / 4)*51-1:0] p_am,
    input wire [((G >> 7) / 4)-1:0] p_fault,
    input wire  fab_fault,
    output wire  ov,
    output wire  mx_we,
    output wire [24-1:0] mx_addr,
    output wire [16-1:0] mx_mask,
    output wire [16*32-1:0] mx_data,
    input wire [379:0] cmd,
    output wire [94:0] ret
);
    wire rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk),.rst_n(rst_n),.rst_q(rs));
    // Static tree owns no duplicate/shadow instruction controller. Every assigned
    // production edge clocks the real engine; schedule violations fault upstream.
    wire ec=clk;
    wire up_fault_c, fab_fault_c; wire [15:0] land_cnt_c; wire [16-1:0] tr_fault_c;
    localparam integer NPE = (G >> 7) / 4, DPW = 34 + NPE;   // DPW: 47 at the TP4 default
    wire [NPE-1:0] p_fault_c;
    wire [DPW-1:0] dpin = {up_fault, land_cnt, tr_fault, p_fault, fab_fault};
    generate if ((AUD & 16) != 0) begin : g_dpin
        reg [DPW-1:0] dpin_q;    // AUD 16: die-input pin flops (status / count / fault inputs; p_am stays direct)
        always @(posedge clk) dpin_q <= dpin;
        assign {up_fault_c, land_cnt_c, tr_fault_c, p_fault_c, fab_fault_c} = dpin_q;
    end else begin : g_ddir
        assign {up_fault_c, land_cnt_c, tr_fault_c, p_fault_c, fab_fault_c} = dpin;
    end endgenerate
    wire [0:0] u_me_go;
    wire [17:0] u_me_i_nout;
    wire [17:0] u_me_i_tiles;
    wire [17:0] u_me_i_k;
    wire [0:0] u_me_i_wsrc;
    wire [23:0] u_me_i_wbase;
    wire [23:0] u_me_i_ts;
    wire [23:0] u_me_i_ks;
    wire [23:0] u_me_i_js;
    wire [23:0] u_me_i_xbase;
    wire [23:0] u_me_i_xks;
    wire [23:0] u_me_i_xjs;
    wire [23:0] u_me_i_xcs;
    wire [2:0] u_me_i_jsh;
    wire [3:0] u_me_i_split;
    wire [23:0] u_me_i_wcs;
    wire [0:0] u_me_i_round;
    wire [23:0] u_me_i_obase;
    wire [23:0] u_me_i_ots;
    wire [23:0] u_me_i_ojs;
    wire [0:0] u_me_i_mmode;
    wire [0:0] u_me_i_oen;
    wire [0:0] u_me_i_amax;
    wire [0:0] u_me_i_rmax;
    wire [23:0] u_me_i_mbase;
    wire [0:0] u_me_ready;
    wire [0:0] u_me_idle;
    wire [0:0] u_me_wrom_re;
    wire [23:0] u_me_wrom_addr;
    wire [17:0] u_me_am_idx;
    wire [31:0] u_me_am_val;
    wire [0:0] u_me_am_any;
    wire [15:0] u_me_progress;
    wire [0:0] u_me_fault;
    reg [379:1] cmd_data;
    reg cmd_go;
    always @(posedge ec) cmd_data<=cmd[379:1];
    always @(posedge ec or negedge rs) if(!rs) cmd_go<=0; else cmd_go<=cmd[0];
    wire [379:0] cq_raw={cmd_data,cmd_go};
`ifdef OT_TT_SPLIT_MUT
    wire [379:0] cq=cq_raw ^ (cmd_go ? ({380{1'b0}} | (380'd1 << 19)) : 380'd0);
`else
    wire [379:0] cq=cq_raw;
`endif
    assign {u_me_i_mbase, u_me_i_rmax, u_me_i_amax, u_me_i_oen, u_me_i_mmode, u_me_i_ojs, u_me_i_ots, u_me_i_obase, u_me_i_round, u_me_i_wcs, u_me_i_split, u_me_i_jsh, u_me_i_xcs, u_me_i_xjs, u_me_i_xks, u_me_i_xbase, u_me_i_js, u_me_i_ks, u_me_i_ts, u_me_i_wbase, u_me_i_wsrc, u_me_i_k, u_me_i_tiles, u_me_i_nout, u_me_go} = cq;
    reg [94:0] ret_q;
    always @(posedge ec or negedge rs) if(!rs) ret_q<=0; else ret_q<={u_me_fault, u_me_progress, u_me_am_any, u_me_am_val, u_me_am_idx, u_me_wrom_addr, u_me_wrom_re, u_me_idle, u_me_ready};
    assign ret=ret_q;
    ot_qfd_tt_ctl_static #(.W(16), .IL(8), .AW(24), .NW(18), .GT(G), .TG(4), .SMIN(7), .SMAX(11), .TCUT(7), .XD(105), .XVM(15), .ORD(7), .ACC_LAT(7), .TREE_LAT(7), .MUL_LAT(6), .FAST_ISSUE(1), .KV_PREP(3), .SCALE_LAT(6), .LANDED(1), .BAND(1), .LNK(0), .CLNK(0), .AMR(1), .SPRE(2), .IS(0), .OS(OS), .XADDR(((AUD & 1) != 0) ? 0 : 1), .RDMEM(((AUD & 8) != 0) ? 2 : ((AUD & 2) != 0) ? 1 : 0), .OKEEP(((AUD & 32) != 0) ? 1 : 0), .PK(((AUD & 256) != 0) ? 2 : ((AUD & 128) != 0) ? 1 : 0), .SC(((AUD & 1024) != 0) ? (1 | ((AUD >> 10) & 14)) : 0), .AMI(((AUD & 65536) != 0) ? 2 : ((AUD & 32768) != 0) ? 1 : 0)) u_tt (
        .clk(ec), .rst_n(rs), .up_fault(up_fault_c), .land_cnt(land_cnt_c), .go(u_me_go), .ready(u_me_ready),
        .idle(u_me_idle), .i_nout(u_me_i_nout), .i_tiles(u_me_i_tiles), .i_k(u_me_i_k), .i_wsrc(u_me_i_wsrc), .i_wbase(u_me_i_wbase), .i_ts(u_me_i_ts), .i_ks(u_me_i_ks), .i_js(u_me_i_js), .i_xbase(u_me_i_xbase), .i_xks(u_me_i_xks), .i_xjs(u_me_i_xjs), .i_xcs(u_me_i_xcs), .i_jsh(u_me_i_jsh), .i_split(u_me_i_split), .i_wcs(u_me_i_wcs), .i_round(u_me_i_round), .i_obase(u_me_i_obase), .i_ots(u_me_i_ots), .i_ojs(u_me_i_ojs), .i_mmode(u_me_i_mmode), .i_oen(u_me_i_oen), .i_amax(u_me_i_amax), .i_rmax(u_me_i_rmax), .i_mbase(u_me_i_mbase),
        .wrom_re(u_me_wrom_re), .wrom_addr(u_me_wrom_addr), .kv_re(),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr),
        .x_dv(), .x_dc(), .x_dcs(), .x_dsp(),
        .t_sel_e(t_sel_e), .t_tv_e(t_tv_e), .tr_fault(tr_fault_c),
        .p_v_e2(p_v_e2), .p_f_e2(p_f_e2), .p_am(p_am), .p_fault(p_fault_c), .fab_fault(fab_fault_c),
        .ov(ov), .am_idx(u_me_am_idx), .am_val(u_me_am_val), .am_any(u_me_am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(u_me_progress), .fault(u_me_fault));
    reg [XW-1:0] me_acc;
    always @(posedge ec or negedge rs) if(!rs) me_acc<=0; else if(u_me_go) me_acc<=me_acc+1'b1;
    ot_hdc_delay #(.W(XW+17),.D(OS),.RESET(1)) u_snap(.clk(clk),.rst_n(rs),.d({me_acc,u_me_idle,u_me_progress}),.q({me_acc_o,me_idle_o,me_prog_o}));
endmodule
