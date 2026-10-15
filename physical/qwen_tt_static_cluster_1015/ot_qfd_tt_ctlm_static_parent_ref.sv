// Static successor parent: actual WSRC classification and real native status.
// No native command reaches the ROM tree; native completion comes from endpoint.
module ot_qfd_tt_ctlm_static_parent_ref (
    input wire ck_me_sched,
    input wire cp_active,output wire [55:0] cp,
    output wire me_image_ready,output wire [75:0] program_obs,
    output wire layer_context_v,output wire [17:0] native_tok,native_pos,
    output wire [379:0] rom_cmd,
    output wire [5:0] command_stage,
    output wire [379:0] native_cmd,
    output wire [15:0] me_observe,
    input wire [94:0] native_ret,
    input wire ck_head,
    input wire ck_tree,
    input wire  rst_n,
    input wire  h_start,
    input wire [18-1:0] token,
    input wire [18-1:0] pos,
    input wire [11:0] prog_base,
    input wire  pw_v,
    input wire [9:0] pw_addr,
    input wire [63:0] pw_data,
    input wire [24-1:0] x_oacc,
    input wire  x_oidle,
    input wire [15:0] x_oprog,
    input wire [15:0] x_orows,
    input wire  kv_ok,
    input wire  kv_write_drained,
    input wire  me_mem_ok,
    output wire [24-1:0] me_acc_o,
    output wire  me_idle_o,
    output wire [15:0] me_prog_o,
    output wire  m_fin_o,
    output wire [18-1:0] m_fidx_o,
    output wire [31:0] m_fval_o,
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
    output wire  me_clk_en,
    output wire  c_fault,
    input wire  up_fault,
    input wire [15:0] land_cnt,
    output wire  scale_re,
    output wire [(3072 >> 7)-1:0] scale_gre,
    output wire [(3072 >> 7)*24-1:0] scale_addr,
    output wire [12:0] t_sel_e,
    output wire [12:0] t_tv_e,
    input wire [16-1:0] tr_fault,
    output wire  p_v_e2,
    output wire [113-1:0] p_f_e2,
    input wire [((3072 >> 7) / 4)*51-1:0] p_am,
    input wire [((3072 >> 7) / 4)-1:0] p_fault,
    input wire  fab_fault,
    output wire  ov,
    output wire  mx_we,
    output wire [24-1:0] mx_addr,
    output wire [16-1:0] mx_mask,
    output wire [16*32-1:0] mx_data
);
    wire [379:0] cmd;
    wire [94:0] ret,rom_ret;
    wire [379:0] local_rom_cmd;
    wire head_fault,relocation_fault;
    reg [5:0] loaded_stage;
    reg relocation_sticky;
    always @(posedge ck_head or negedge rst_n)
      if(!rst_n)begin loaded_stage<=0;relocation_sticky<=0;end
      else begin
        if(pw_v && pw_addr==1017 && pw_data[63:32]==32'h43414c53)
          loaded_stage<=pw_data[17:12];
        if(relocation_fault)relocation_sticky<=1;
      end
    assign command_stage=loaded_stage;
    ot_qwen_tp8_rom_relocate u_resident_relocation(
      .in_cmd(local_rom_cmd),.in_stage(loaded_stage),.out_cmd(rom_cmd),.fault(relocation_fault));
    assign c_fault=head_fault|relocation_sticky;
    ot_qfd_native_cmd_route u_native_route (
      .clk(ck_head),.rst_n(rst_n),.cmd(cmd),.rom_ret(rom_ret),.native_ret(native_ret),
      .rom_cmd(local_rom_cmd),.native_cmd(native_cmd),.ret(ret));
    qfd_tt_ctlm_head_static u_head (
        .me_observe(me_observe),.cp_active(cp_active),.cp(cp),
        .me_image_ready(me_image_ready),.program_obs(program_obs),
        .layer_context_v(layer_context_v),.native_tok(native_tok),.native_pos(native_pos),

        .clk(ck_head),
        .ck_sched(ck_me_sched),
        .rst_n(rst_n),
        .h_start(h_start),
        .token(token),
        .pos(pos),
        .prog_base(prog_base),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_orows(x_orows),
        .kv_ok(kv_ok),
        .kv_write_drained(kv_write_drained),
        .me_mem_ok(me_mem_ok),
        .m_fin_o(m_fin_o),
        .m_fidx_o(m_fidx_o),
        .m_fval_o(m_fval_o),
        .me_clk_en(me_clk_en),
        .c_fault(head_fault),
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
        .cmd(cmd),.ret(ret));
    qfd_tt_ctlm_tree_static u_tree (

        .clk(ck_tree),
        .rst_n(rst_n),
        .me_acc_o(me_acc_o),
        .me_idle_o(me_idle_o),
        .me_prog_o(me_prog_o),
        .up_fault(up_fault),
        .land_cnt(land_cnt),
        .scale_re(scale_re),
        .scale_gre(scale_gre),
        .scale_addr(scale_addr),
        .t_sel_e(t_sel_e),
        .t_tv_e(t_tv_e),
        .tr_fault(tr_fault),
        .p_v_e2(p_v_e2),
        .p_f_e2(p_f_e2),
        .p_am(p_am),
        .p_fault(p_fault),
        .fab_fault(fab_fault),
        .ov(ov),
        .mx_we(mx_we),
        .mx_addr(mx_addr),
        .mx_mask(mx_mask),
        .mx_data(mx_data),
        .cmd(rom_cmd),.ret(rom_ret));
endmodule
