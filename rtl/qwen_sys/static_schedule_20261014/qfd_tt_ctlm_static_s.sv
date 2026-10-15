// New native static slot master; fresh physical qualification required.
// Existing c341/f104/lc26 packing retained; obsolete VM xd/xr removed.
module qfd_tt_ctlm_static_s #(parameter integer XPF_TRANSPORT_EDGES=-1) (
    input wire ck_xpf,
    input wire ck_me_sched,
    input wire cp_active,output wire [55:0] cp,
    input wire su_image_ready,output wire control_stores_ready,output wire [75:0] program_obs,
    output wire layer_context_v,output wire [17:0] native_tok,native_pos,
    output wire [379:0] native_cmd,
    input wire [94:0] native_ret,
    output wire [5:0] command_stage,
    output wire [379:0] ib,
    input wire [15:0] su_observe,output wire [71:0] xpf,
    output wire mer0,mer1,mer2,
    input wire rf0,rf1,rf2,xflt,
    input wire ck_head,
    input wire ck_tree,
    output wire [340:0] c0,
    input  wire [103:0] f0,
    output wire [25:0] lc0,
    output wire [340:0] c1,
    input  wire [103:0] f1,
    output wire [25:0] lc1,
    output wire [340:0] c2,
    input  wire [103:0] f2,
    output wire [25:0] lc2,
    input  wire [15:0] ld,
    output wire [7:0] mee,
    input  wire meok,
    output wire [552:0] mx,
    input  wire [74:0] pw,
    input  wire rsi,
    output wire [25:0] sel,
    input  wire [48:0] st,
    input  wire [3:0] uf,
    output wire [91:0] xm,
    input  wire [56:0] xs,
    input  wire kok,
    input  wire kwd,
    input  wire fab,
    output wire cf,
    output wire ovf
);
    generate if(XPF_TRANSPORT_EDGES<0)begin:g_unassigned_arm_route
      initial $error("native XPF transport edges require assigned physical route");
    end endgenerate
    wire w_rst_n;
    wire w_h_start;
    wire [17:0] w_token;
    wire [17:0] w_pos;
    wire [11:0] w_prog_base;
    wire w_pw_v;
    wire [9:0] w_pw_addr;
    wire [63:0] w_pw_data;
    wire [23:0] w_x_oacc;
    wire w_x_oidle;
    wire [15:0] w_x_oprog;
    wire [15:0] w_x_orows;
    wire w_kv_ok;
    wire w_kv_write_drained;
    wire w_me_mem_ok;
    wire [23:0] w_me_acc_o;
    wire w_me_idle_o;
    wire [15:0] w_me_prog_o;
    wire w_m_fin_o;
    wire [17:0] w_m_fidx_o;
    wire [31:0] w_m_fval_o;
    wire w_kvd_v;
    wire [23:0] w_kvd_wbase;
    wire [23:0] w_kvd_ts;
    wire [23:0] w_kvd_ks;
    wire [23:0] w_kvd_js;
    wire [23:0] w_kvd_wcs;
    wire [3:0] w_kvd_split;
    wire [2:0] w_kvd_jsh;
    wire [17:0] w_kvd_tiles;
    wire [17:0] w_kvd_k;
    wire [17:0] w_kvd_nout;
    wire w_kvd_kindk;
    wire [17:0] w_kvd_pos;
    wire w_me_clk_en;
    wire w_c_fault;
    wire w_up_fault;
    wire [15:0] w_land_cnt;
    wire w_scale_re;
    wire [23:0] w_scale_gre;
    wire [575:0] w_scale_addr;
    wire [12:0] w_t_sel_e;
    wire [12:0] w_t_tv_e;
    wire [15:0] w_tr_fault;
    wire w_p_v_e2;
    wire [112:0] w_p_f_e2;
    wire [305:0] w_p_am;
    wire [5:0] w_p_fault;
    wire w_fab_fault;
    wire w_ov;
    wire w_mx_we;
    wire [23:0] w_mx_addr;
    wire [15:0] w_mx_mask;
    wire [511:0] w_mx_data;
    assign w_tr_fault = 16'd0;   // retired: the band faults reach the control element through the upper tile (up_fault); as ot_qfd_spine_band
    wire [340:0] m_c0 = {w_scale_addr[191:0], w_scale_gre[7:0], w_scale_re, w_p_f_e2[112:0], w_p_v_e2, w_t_tv_e[12:0], w_t_sel_e[12:0]};
`ifdef OT_QFD_TT_CTLM_SLOT_MUT
    assign c0 = {m_c0[340:2], m_c0[0], m_c0[1]};
`else
    assign c0 = m_c0;
`endif
    assign w_p_am[101:0] = f0[101:0];
    assign w_p_fault[1:0] = f0[103:102];
    assign lc0 = {w_t_tv_e[12:0], w_t_sel_e[12:0]};
    assign c1 = {w_scale_addr[383:192], w_scale_gre[15:8], w_scale_re, w_p_f_e2[112:0], w_p_v_e2, w_t_tv_e[12:0], w_t_sel_e[12:0]};
    assign w_p_am[203:102] = f1[101:0];
    assign w_p_fault[3:2] = f1[103:102];
    assign lc1 = {w_t_tv_e[12:0], w_t_sel_e[12:0]};
    assign c2 = {w_scale_addr[575:384], w_scale_gre[23:16], w_scale_re, w_p_f_e2[112:0], w_p_v_e2, w_t_tv_e[12:0], w_t_sel_e[12:0]};
    assign w_p_am[305:204] = f2[101:0];
    assign w_p_fault[5:4] = f2[103:102];
    assign lc2 = {w_t_tv_e[12:0], w_t_sel_e[12:0]};
    assign w_land_cnt[15:0] = ld[15:0];
    assign mee = {w_me_clk_en, w_me_clk_en, w_me_clk_en, w_me_clk_en, w_me_clk_en, w_me_clk_en, w_me_clk_en, w_me_clk_en};
    assign w_me_mem_ok = meok;
    assign mx = {w_mx_we, w_mx_mask[15:0], w_mx_addr[23:0], w_mx_data[511:0]};
    assign w_pw_data[63:0] = pw[63:0];
    assign w_pw_addr[9:0] = pw[73:64];
    assign w_pw_v = pw[74];
    assign w_rst_n = rsi;
    assign sel = {w_t_tv_e[12:0], w_t_sel_e[12:0]};
    assign w_prog_base[11:0] = st[11:0];
    assign w_pos[17:0] = st[29:12];
    assign w_token[17:0] = st[47:30];
    assign w_h_start = st[48];
    assign w_up_fault = |uf; // Four real upper leaves; existing downstream fault capture is retained.
    wire [91:0] m_xm = {w_me_acc_o[23:0], w_me_idle_o, w_me_prog_o[15:0], w_m_fin_o, w_m_fidx_o[17:0], w_m_fval_o[31:0]};
`ifdef OT_QFD_TT_CTLM_SLOT_MUT
    assign xm = {m_xm[91:2], m_xm[0], m_xm[1]};
`else
    assign xm = m_xm;
`endif
    assign w_x_orows[15:0] = xs[15:0];
    assign w_x_oprog[15:0] = xs[31:16];
    assign w_x_oidle = xs[32];
    assign w_x_oacc[23:0] = xs[56:33];
    assign w_kv_ok = kok;
    assign w_kv_write_drained = kwd;
    assign mer0=w_me_clk_en;assign mer1=w_me_clk_en;assign mer2=w_me_clk_en;

    assign w_fab_fault = fab|rf0|rf1|rf2|xflt|xpf_loader_fault|xpf_schedule_fault;
    assign cf = w_c_fault;
    assign ovf = w_ov;
    wire me_image_ready,xpf_loader_ready,xpf_monitor_ready;
    assign control_stores_ready=me_image_ready&&su_image_ready&&xpf_loader_ready&&xpf_monitor_ready;
    wire monitor_rs;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_xpf_reset
      (.clk(ck_xpf),.async_rst_n(w_rst_n),.sync_rst_n(monitor_rs));
    wire [48:0] monitor_start;
    ot_hdc_delay #(.W(49),.D(1),.RESET(1)) u_xpf_start_face
      (.clk(ck_xpf),.rst_n(monitor_rs),.d(st),.q(monitor_start));
    wire dvm_stage_start=monitor_start[48]&&monitor_start[11:0]==0;
    wire [15:0] monitor_su;
    ot_hdc_delay #(.W(16),.D(1),.RESET(1)) u_xpf_su_face
      (.clk(ck_xpf),.rst_n(monitor_rs),.d(su_observe),.q(monitor_su));
    wire [74:0] monitor_pw;
    ot_hdc_delay #(.W(75),.D(1),.RESET(1)) u_xpf_pw_face
      (.clk(ck_xpf),.rst_n(monitor_rs),.d(pw),.q(monitor_pw));
    wire xpf_loader_fault,xpf_schedule_fault,xpf_active;
    wire cfg_clear,cfg_v,cfg_seal;wire [2:0] cfg_index;wire [187:0] cfg_data;
    wire [3:0] cfg_count;wire [5:0] xpf_stage;wire [31:0] stop_cycle,xpf_cycle;
    ot_qfd_xpf_dense_pw_loader u_xpf_loader
      (.clk(ck_xpf),.rst_n(monitor_rs),.stage_active(xpf_active),
       .pw_v(monitor_pw[74]),.pw_addr(monitor_pw[73:64]),.pw_data(monitor_pw[63:0]),
       .cfg_clear(cfg_clear),.cfg_v(cfg_v),.cfg_seal(cfg_seal),.cfg_index(cfg_index),.cfg_data(cfg_data),
       .cfg_count(cfg_count),.stage(xpf_stage),.stop_cycle(stop_cycle),.image_ready(xpf_loader_ready),.fault(xpf_loader_fault));
    wire [15:0] actual_me_observe,monitor_me;
    ot_hdc_delay #(.W(16),.D(1),.RESET(1)) u_xpf_me_face
      (.clk(ck_xpf),.rst_n(monitor_rs),.d(actual_me_observe),.q(monitor_me));
    wire xpf_me_event=monitor_me[15];
    wire [11:0] xpf_me_pc=monitor_me[11:0];
    // Transport parameter is assigned by the current die pipeline, never
    // inferred from producer readiness. Native compile sets its exact value.
    ot_qfd_xpf_static_schedule #(.N(4),.ARM_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES)) u_xpf_schedule
      (.clk(ck_xpf),.rst_n(monitor_rs),.cfg_clear(cfg_clear),.cfg_v(cfg_v),.cfg_seal(cfg_seal),
       .cfg_index(cfg_index[1:0]),.cfg_data(cfg_data),.cfg_count(cfg_count[2:0]),
       .start(dvm_stage_start),.stop(xpf_active&&xpf_cycle==stop_cycle),.stage(xpf_stage),
       .cp_issue(monitor_me[15]&&monitor_me[13:12]==3),.cp_pc(xpf_me_pc),.me_issue(xpf_me_event&&monitor_me[13:12]==1),.me_pc(xpf_me_pc),.su_issue(monitor_su[15]),.su_pc(monitor_su[11:0]),
       .xpf(xpf),.image_ready(xpf_monitor_ready),.fault(xpf_schedule_fault),.active(xpf_active),.cycle(xpf_cycle));
    ot_qfd_tt_ctlm_static_parent u_body (
        .ck_me_sched(ck_me_sched),
        .cp_active(cp_active),.cp(cp),
        .me_image_ready(me_image_ready),.program_obs(program_obs),
        .layer_context_v(layer_context_v),.native_tok(native_tok),.native_pos(native_pos),
        .native_cmd(native_cmd),.native_ret(native_ret),.command_stage(command_stage),
        .me_observe(actual_me_observe),
        .rom_cmd(ib),

        .ck_head(ck_head),
        .ck_tree(ck_tree),
        .rst_n(w_rst_n),
        .h_start(w_h_start),
        .token(w_token),
        .pos(w_pos),
        .prog_base(w_prog_base),
        .pw_v(w_pw_v),
        .pw_addr(w_pw_addr),
        .pw_data(w_pw_data),
        .x_oacc(w_x_oacc),
        .x_oidle(w_x_oidle),
        .x_oprog(w_x_oprog),
        .x_orows(w_x_orows),
        .kv_ok(w_kv_ok),
        .kv_write_drained(w_kv_write_drained),
        .me_mem_ok(w_me_mem_ok),
        .me_acc_o(w_me_acc_o),
        .me_idle_o(w_me_idle_o),
        .me_prog_o(w_me_prog_o),
        .m_fin_o(w_m_fin_o),
        .m_fidx_o(w_m_fidx_o),
        .m_fval_o(w_m_fval_o),
        .kvd_v(w_kvd_v),
        .kvd_wbase(w_kvd_wbase),
        .kvd_ts(w_kvd_ts),
        .kvd_ks(w_kvd_ks),
        .kvd_js(w_kvd_js),
        .kvd_wcs(w_kvd_wcs),
        .kvd_split(w_kvd_split),
        .kvd_jsh(w_kvd_jsh),
        .kvd_tiles(w_kvd_tiles),
        .kvd_k(w_kvd_k),
        .kvd_nout(w_kvd_nout),
        .kvd_kindk(w_kvd_kindk),
        .kvd_pos(w_kvd_pos),
        .me_clk_en(w_me_clk_en),
        .c_fault(w_c_fault),
        .up_fault(w_up_fault),
        .land_cnt(w_land_cnt),
        .scale_re(w_scale_re),
        .scale_gre(w_scale_gre),
        .scale_addr(w_scale_addr),
        .t_sel_e(w_t_sel_e),
        .t_tv_e(w_t_tv_e),
        .tr_fault(w_tr_fault),
        .p_v_e2(w_p_v_e2),
        .p_f_e2(w_p_f_e2),
        .p_am(w_p_am),
        .p_fault(w_p_fault),
        .fab_fault(w_fab_fault),
        .ov(w_ov),
        .mx_we(w_mx_we),
        .mx_addr(w_mx_addr),
        .mx_mask(w_mx_mask),
        .mx_data(w_mx_data)
    );
endmodule
