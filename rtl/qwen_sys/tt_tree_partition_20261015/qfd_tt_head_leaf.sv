`timescale 1ns/1ps
// qfd_tt_head_leaf (Q-ELEM-TTP 2026-10-16): the TT slot's head-side hard leaf = ot_qfd_tt_ctlm_static_hr (head + native
// route + resident relocation + loaded stage; CMDREG +1 accepted edge, HFC 32) on ONE clock root.  hr h4 measured two
// std roots (ck_head 5,903 / ck_me_sched 877 sinks) plus two raw SRAM entries: ck_head TT insertion 535.9 / spread
// 245.8 ps.  ck_me_sched clocks only this head and is the same PLL phase as ck_head (related, 0 ps), and the program
// SRAMs ck_pm0/1 were ck_head before r14: one root (6,780 sinks + 2 SRAM clock pins < 15k) is the same logic and edges
// with an ordinary CTS tree, as the closed core/scale leaves (SRAMs on the tree).
module qfd_tt_head_leaf (
    input wire clk,
    input wire [94:0] rom_ret_i,
    input wire cp_active,
    output wire [55:0] cp,
    output wire me_image_ready,
    output wire [75:0] program_obs,
    output wire layer_context_v,
    output wire [17:0] native_tok,
    output wire [17:0] native_pos,
    output wire [379:0] rom_cmd,
    output wire [5:0] command_stage,
    output wire [379:0] native_cmd,
    output wire [15:0] me_observe,
    input wire [94:0] native_ret,
    input wire rst_n,
    input wire h_start,
    input wire [18-1:0] token,
    input wire [18-1:0] pos,
    input wire [11:0] prog_base,
    input wire pw_v,
    input wire [9:0] pw_addr,
    input wire [63:0] pw_data,
    input wire [24-1:0] x_oacc,
    input wire x_oidle,
    input wire [15:0] x_oprog,
    input wire [15:0] x_orows,
    input wire kv_ok,
    input wire kv_write_drained,
    input wire me_mem_ok,
    output wire m_fin_o,
    output wire [18-1:0] m_fidx_o,
    output wire [31:0] m_fval_o,
    output wire kvd_v,
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
    output wire kvd_kindk,
    output wire [18-1:0] kvd_pos,
    output wire me_clk_en,
    output wire c_fault
);
    ot_qfd_tt_ctlm_static_hr #(.CMDREG(1)) u_hr (.rom_ret_i(rom_ret_i),.ck_me_sched(clk),.cp_active(cp_active),.cp(cp),.me_image_ready(me_image_ready),.program_obs(program_obs),.layer_context_v(layer_context_v),.native_tok(native_tok),.native_pos(native_pos),.rom_cmd(rom_cmd),.command_stage(command_stage),.native_cmd(native_cmd),.me_observe(me_observe),.native_ret(native_ret),.ck_head(clk),.ck_pm0(clk),.ck_pm1(clk),.rst_n(rst_n),.h_start(h_start),.token(token),.pos(pos),.prog_base(prog_base),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.x_oacc(x_oacc),.x_oidle(x_oidle),.x_oprog(x_oprog),.x_orows(x_orows),.kv_ok(kv_ok),.kv_write_drained(kv_write_drained),.me_mem_ok(me_mem_ok),.m_fin_o(m_fin_o),.m_fidx_o(m_fidx_o),.m_fval_o(m_fval_o),.kvd_v(kvd_v),.kvd_wbase(kvd_wbase),.kvd_ts(kvd_ts),.kvd_ks(kvd_ks),.kvd_js(kvd_js),.kvd_wcs(kvd_wcs),.kvd_split(kvd_split),.kvd_jsh(kvd_jsh),.kvd_tiles(kvd_tiles),.kvd_k(kvd_k),.kvd_nout(kvd_nout),.kvd_kindk(kvd_kindk),.kvd_pos(kvd_pos),.me_clk_en(me_clk_en),.c_fault(c_fault));
endmodule
