`timescale 1ns/1ps
// Lockstep regrouping bench: original parent body (ref) vs hr+tree regrouping (dut); real SRAM models.
module tb_tt_static_regroup;
  reg clk=0; always #0.5 clk=~clk;
  integer cyc=0, errs=0;
  reg  cp_active;
  wire [55:0] r_cp, d_cp;
  wire  r_me_image_ready, d_me_image_ready;
  wire [75:0] r_program_obs, d_program_obs;
  wire  r_layer_context_v, d_layer_context_v;
  wire [17:0] r_native_tok, d_native_tok;
  wire [17:0] r_native_pos, d_native_pos;
  wire [379:0] r_rom_cmd, d_rom_cmd;
  wire [5:0] r_command_stage, d_command_stage;
  wire [379:0] r_native_cmd, d_native_cmd;
  wire [15:0] r_me_observe, d_me_observe;
  reg [94:0] native_ret;
  reg  rst_n;
  reg  h_start;
  reg [18-1:0] token;
  reg [18-1:0] pos;
  reg [11:0] prog_base;
  reg  pw_v;
  reg [9:0] pw_addr;
  reg [63:0] pw_data;
  reg [24-1:0] x_oacc;
  reg  x_oidle;
  reg [15:0] x_oprog;
  reg [15:0] x_orows;
  reg  kv_ok;
  reg  kv_write_drained;
  reg  me_mem_ok;
  wire [24-1:0] r_me_acc_o, d_me_acc_o;
  wire  r_me_idle_o, d_me_idle_o;
  wire [15:0] r_me_prog_o, d_me_prog_o;
  wire  r_m_fin_o, d_m_fin_o;
  wire [18-1:0] r_m_fidx_o, d_m_fidx_o;
  wire [31:0] r_m_fval_o, d_m_fval_o;
  wire  r_kvd_v, d_kvd_v;
  wire [24-1:0] r_kvd_wbase, d_kvd_wbase;
  wire [24-1:0] r_kvd_ts, d_kvd_ts;
  wire [24-1:0] r_kvd_ks, d_kvd_ks;
  wire [24-1:0] r_kvd_js, d_kvd_js;
  wire [24-1:0] r_kvd_wcs, d_kvd_wcs;
  wire [3:0] r_kvd_split, d_kvd_split;
  wire [2:0] r_kvd_jsh, d_kvd_jsh;
  wire [18-1:0] r_kvd_tiles, d_kvd_tiles;
  wire [18-1:0] r_kvd_k, d_kvd_k;
  wire [18-1:0] r_kvd_nout, d_kvd_nout;
  wire  r_kvd_kindk, d_kvd_kindk;
  wire [18-1:0] r_kvd_pos, d_kvd_pos;
  wire  r_me_clk_en, d_me_clk_en;
  wire  r_c_fault, d_c_fault;
  reg  up_fault;
  reg [15:0] land_cnt;
  wire  r_scale_re, d_scale_re;
  wire [(3072 >> 7)-1:0] r_scale_gre, d_scale_gre;
  wire [(3072 >> 7)*24-1:0] r_scale_addr, d_scale_addr;
  wire [12:0] r_t_sel_e, d_t_sel_e;
  wire [12:0] r_t_tv_e, d_t_tv_e;
  reg [16-1:0] tr_fault;
  wire  r_p_v_e2, d_p_v_e2;
  wire [113-1:0] r_p_f_e2, d_p_f_e2;
  reg [((3072 >> 7) / 4)*51-1:0] p_am;
  reg [((3072 >> 7) / 4)-1:0] p_fault;
  reg  fab_fault;
  wire  r_ov, d_ov;
  wire  r_mx_we, d_mx_we;
  wire [24-1:0] r_mx_addr, d_mx_addr;
  wire [16-1:0] r_mx_mask, d_mx_mask;
  wire [16*32-1:0] r_mx_data, d_mx_data;
  ot_qfd_tt_ctlm_static_parent_ref u_ref(.ck_me_sched(clk),.cp_active(cp_active),.cp(r_cp),.me_image_ready(r_me_image_ready),.program_obs(r_program_obs),.layer_context_v(r_layer_context_v),.native_tok(r_native_tok),.native_pos(r_native_pos),.rom_cmd(r_rom_cmd),.command_stage(r_command_stage),.native_cmd(r_native_cmd),.me_observe(r_me_observe),.native_ret(native_ret),.ck_head(clk),.ck_tree(clk),.rst_n(rst_n),.h_start(h_start),.token(token),.pos(pos),.prog_base(prog_base),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.x_oacc(x_oacc),.x_oidle(x_oidle),.x_oprog(x_oprog),.x_orows(x_orows),.kv_ok(kv_ok),.kv_write_drained(kv_write_drained),.me_mem_ok(me_mem_ok),.me_acc_o(r_me_acc_o),.me_idle_o(r_me_idle_o),.me_prog_o(r_me_prog_o),.m_fin_o(r_m_fin_o),.m_fidx_o(r_m_fidx_o),.m_fval_o(r_m_fval_o),.kvd_v(r_kvd_v),.kvd_wbase(r_kvd_wbase),.kvd_ts(r_kvd_ts),.kvd_ks(r_kvd_ks),.kvd_js(r_kvd_js),.kvd_wcs(r_kvd_wcs),.kvd_split(r_kvd_split),.kvd_jsh(r_kvd_jsh),.kvd_tiles(r_kvd_tiles),.kvd_k(r_kvd_k),.kvd_nout(r_kvd_nout),.kvd_kindk(r_kvd_kindk),.kvd_pos(r_kvd_pos),.me_clk_en(r_me_clk_en),.c_fault(r_c_fault),.up_fault(up_fault),.land_cnt(land_cnt),.scale_re(r_scale_re),.scale_gre(r_scale_gre),.scale_addr(r_scale_addr),.t_sel_e(r_t_sel_e),.t_tv_e(r_t_tv_e),.tr_fault(tr_fault),.p_v_e2(r_p_v_e2),.p_f_e2(r_p_f_e2),.p_am(p_am),.p_fault(p_fault),.fab_fault(fab_fault),.ov(r_ov),.mx_we(r_mx_we),.mx_addr(r_mx_addr),.mx_mask(r_mx_mask),.mx_data(r_mx_data));
  ot_qfd_tt_ctlm_static_parent u_dut(.ck_me_sched(clk),.cp_active(cp_active),.cp(d_cp),.me_image_ready(d_me_image_ready),.program_obs(d_program_obs),.layer_context_v(d_layer_context_v),.native_tok(d_native_tok),.native_pos(d_native_pos),.rom_cmd(d_rom_cmd),.command_stage(d_command_stage),.native_cmd(d_native_cmd),.me_observe(d_me_observe),.native_ret(native_ret),.ck_head(clk),.ck_tree(clk),.rst_n(rst_n),.h_start(h_start),.token(token),.pos(pos),.prog_base(prog_base),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.x_oacc(x_oacc),.x_oidle(x_oidle),.x_oprog(x_oprog),.x_orows(x_orows),.kv_ok(kv_ok),.kv_write_drained(kv_write_drained),.me_mem_ok(me_mem_ok),.me_acc_o(d_me_acc_o),.me_idle_o(d_me_idle_o),.me_prog_o(d_me_prog_o),.m_fin_o(d_m_fin_o),.m_fidx_o(d_m_fidx_o),.m_fval_o(d_m_fval_o),.kvd_v(d_kvd_v),.kvd_wbase(d_kvd_wbase),.kvd_ts(d_kvd_ts),.kvd_ks(d_kvd_ks),.kvd_js(d_kvd_js),.kvd_wcs(d_kvd_wcs),.kvd_split(d_kvd_split),.kvd_jsh(d_kvd_jsh),.kvd_tiles(d_kvd_tiles),.kvd_k(d_kvd_k),.kvd_nout(d_kvd_nout),.kvd_kindk(d_kvd_kindk),.kvd_pos(d_kvd_pos),.me_clk_en(d_me_clk_en),.c_fault(d_c_fault),.up_fault(up_fault),.land_cnt(land_cnt),.scale_re(d_scale_re),.scale_gre(d_scale_gre),.scale_addr(d_scale_addr),.t_sel_e(d_t_sel_e),.t_tv_e(d_t_tv_e),.tr_fault(tr_fault),.p_v_e2(d_p_v_e2),.p_f_e2(d_p_f_e2),.p_am(p_am),.p_fault(p_fault),.fab_fault(fab_fault),.ov(d_ov),.mx_we(d_mx_we),.mx_addr(d_mx_addr),.mx_mask(d_mx_mask),.mx_data(d_mx_data));
  task rnd; begin
    cp_active = {$urandom};
    native_ret = {$urandom,$urandom,$urandom};
    h_start = {$urandom};
    token = {$urandom};
    pos = {$urandom};
    prog_base = {$urandom};
    pw_v = {$urandom};
    pw_addr = {$urandom};
    pw_data = {$urandom,$urandom};
    x_oacc = {$urandom};
    x_oidle = {$urandom};
    x_oprog = {$urandom};
    x_orows = {$urandom};
    kv_ok = {$urandom};
    kv_write_drained = {$urandom};
    me_mem_ok = {$urandom};
    up_fault = {$urandom};
    land_cnt = {$urandom};
    tr_fault = {$urandom};
    p_am = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
    p_fault = {$urandom};
    fab_fault = {$urandom};
  end endtask
  initial begin rst_n=0; rnd; repeat(20) @(negedge clk) rnd; rst_n=1;
    repeat(`NCYC) begin @(negedge clk); rnd; cyc=cyc+1; if(cyc%20000==10000) begin rst_n=0; @(negedge clk); rnd; rst_n=1; end end
    seam_report;
    if(errs==0 && (cmd_pair<`MIN_PAIR || ret_pair<`MIN_PAIR)) $display("REGROUP_UNSENSITIZED cmd_pair=%0d ret_pair=%0d min=%0d",cmd_pair,ret_pair,`MIN_PAIR);
    else if(errs==0) $display("REGROUP_PASS cycles=%0d outputs=%0d cmd_pair=%0d ret_pair=%0d",cyc,43,cmd_pair,ret_pair); else $display("REGROUP_FAIL errs=%0d",errs); $finish; end
  integer ct[0:379], rt[0:94]; integer cmd_pair=0, ret_pair=0, k; reg [379:0] pc; reg [94:0] pr;
  initial begin for(k=0;k<380;k=k+1) ct[k]=0; for(k=0;k<95;k=k+1) rt[k]=0; pc=0; pr=0; end
  always @(posedge clk) if(rst_n) begin
    for(k=0;k<380;k=k+1) if(u_dut.rom_cmd[k]!==pc[k]) ct[k]=ct[k]+1;
    for(k=0;k<95;k=k+1) if(u_dut.rom_ret[k]!==pr[k]) rt[k]=rt[k]+1;
    pc=u_dut.rom_cmd; pr=u_dut.rom_ret;
    if(u_dut.rom_cmd[`CMD_A]!==u_dut.rom_cmd[`CMD_B]) cmd_pair=cmd_pair+1;
    if(u_dut.rom_ret[`RET_A]!==u_dut.rom_ret[`RET_B]) ret_pair=ret_pair+1;
  end
  task seam_report; begin
    for(k=0;k<380;k=k+1) if(ct[k]!=0) $display("SEAM_CMD_TOG %0d %0d",k,ct[k]);
    for(k=0;k<95;k=k+1) if(rt[k]!=0) $display("SEAM_RET_TOG %0d %0d",k,rt[k]);
    $display("SEAM_PAIR cmd[%0d]/cmd[%0d] differ=%0d ret[%0d]/ret[%0d] differ=%0d",`CMD_A,`CMD_B,cmd_pair,`RET_A,`RET_B,ret_pair);
  end endtask
  always @(posedge clk) if(rst_n) begin
    if(r_cp!==d_cp) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d cp",cyc); end
    if(r_me_image_ready!==d_me_image_ready) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d me_image_ready",cyc); end
    if(r_program_obs!==d_program_obs) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d program_obs",cyc); end
    if(r_layer_context_v!==d_layer_context_v) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d layer_context_v",cyc); end
    if(r_native_tok!==d_native_tok) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d native_tok",cyc); end
    if(r_native_pos!==d_native_pos) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d native_pos",cyc); end
    if(r_rom_cmd!==d_rom_cmd) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d rom_cmd",cyc); end
    if(r_command_stage!==d_command_stage) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d command_stage",cyc); end
    if(r_native_cmd!==d_native_cmd) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d native_cmd",cyc); end
    if(r_me_observe!==d_me_observe) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d me_observe",cyc); end
    if(r_me_acc_o!==d_me_acc_o) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d me_acc_o",cyc); end
    if(r_me_idle_o!==d_me_idle_o) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d me_idle_o",cyc); end
    if(r_me_prog_o!==d_me_prog_o) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d me_prog_o",cyc); end
    if(r_m_fin_o!==d_m_fin_o) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d m_fin_o",cyc); end
    if(r_m_fidx_o!==d_m_fidx_o) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d m_fidx_o",cyc); end
    if(r_m_fval_o!==d_m_fval_o) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d m_fval_o",cyc); end
    if(r_kvd_v!==d_kvd_v) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_v",cyc); end
    if(r_kvd_wbase!==d_kvd_wbase) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_wbase",cyc); end
    if(r_kvd_ts!==d_kvd_ts) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_ts",cyc); end
    if(r_kvd_ks!==d_kvd_ks) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_ks",cyc); end
    if(r_kvd_js!==d_kvd_js) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_js",cyc); end
    if(r_kvd_wcs!==d_kvd_wcs) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_wcs",cyc); end
    if(r_kvd_split!==d_kvd_split) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_split",cyc); end
    if(r_kvd_jsh!==d_kvd_jsh) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_jsh",cyc); end
    if(r_kvd_tiles!==d_kvd_tiles) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_tiles",cyc); end
    if(r_kvd_k!==d_kvd_k) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_k",cyc); end
    if(r_kvd_nout!==d_kvd_nout) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_nout",cyc); end
    if(r_kvd_kindk!==d_kvd_kindk) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_kindk",cyc); end
    if(r_kvd_pos!==d_kvd_pos) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d kvd_pos",cyc); end
    if(r_me_clk_en!==d_me_clk_en) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d me_clk_en",cyc); end
    if(r_c_fault!==d_c_fault) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d c_fault",cyc); end
    if(r_scale_re!==d_scale_re) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d scale_re",cyc); end
    if(r_scale_gre!==d_scale_gre) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d scale_gre",cyc); end
    if(r_scale_addr!==d_scale_addr) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d scale_addr",cyc); end
    if(r_t_sel_e!==d_t_sel_e) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d t_sel_e",cyc); end
    if(r_t_tv_e!==d_t_tv_e) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d t_tv_e",cyc); end
    if(r_p_v_e2!==d_p_v_e2) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d p_v_e2",cyc); end
    if(r_p_f_e2!==d_p_f_e2) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d p_f_e2",cyc); end
    if(r_ov!==d_ov) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d ov",cyc); end
    if(r_mx_we!==d_mx_we) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d mx_we",cyc); end
    if(r_mx_addr!==d_mx_addr) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d mx_addr",cyc); end
    if(r_mx_mask!==d_mx_mask) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d mx_mask",cyc); end
    if(r_mx_data!==d_mx_data) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d mx_data",cyc); end
  end
endmodule
