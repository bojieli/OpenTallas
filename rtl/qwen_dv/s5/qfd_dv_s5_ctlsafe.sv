module qfd_dv_s5_ctlsafe #(parameter integer HARD = 1, parameter integer MUT = 0, parameter integer MU_NU = 4) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [115:0]   cmd_q,
    input  wire [1037:0]  chd_q,
    // station (region 0 copies + every region's data slice)
    input  wire           r_v,
    input  wire [7:0]     r_idx,
    input  wire           r_last,
    input  wire [511:0]   r_d,
    input  wire           l9o_v,          // l9_o[512]
    input  wire           stn_fault,
    // SU lane write ports (lane relay outputs)
    input  wire [7:0]     vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire [7:0]     kv_we,
    input  wire [8*24-1:0] kv_waddr,
    input  wire [8*32-1:0] kv_wdata,
    input  wire           su_nr,          // su_go && !su_ready (suvm)
    input  wire           su_idle,
    input  wire           su_fault,
    input  wire [15:0]    su_prog,
    input  wire [15:0]    su_rows,
    input  wire           vm_fault,
    // reducer
    input  wire           red_we,
    input  wire [23:0]    red_addr,
    input  wire [31:0]    red_data,
    // scalar tree
    input  wire           sc_w1_we,
    input  wire [23:0]    sc_w1_addr,
    input  wire [31:0]    sc_w1_data,
    input  wire           tok_v,
    input  wire [23:0]    tok_idx,
    input  wire           tok_own,
    input  wire [31:0]    tok_val,
    input  wire [1:0]     tok_user,
    input  wire           sc_busy,
    input  wire           sc_fault,
    input  wire           stm_fault,
    input  wire           tld_fault,
    input  wire           hd_fault,
    input  wire           pc_bad,
    // decoded command bundles
    output wire [3:0]     sid,
    output wire [28:0]    stn_cfg,        // {v, mode 2, wsrc, nwords 8, sbase 9, kcm1 8}
    output wire [100:0]   sc_cfg,         // {v, root, rdir, nb 6, ss 24, fuse, rx 24, eps 32, k 5, amnb 6}
    output wire [30:0]    stm_cfg,        // {v, dir 2, tag 28}
    output wire [9:0]     su_cmd,         // {c_su, p_idx 9}
    output wire           am_v,
    output wire [23:0]    am_idx,
    output wire [31:0]    am_val,
    output wire [1:0]     am_u,
    // VM writes
    output wire           w16_we,
    output wire [23:0]    w16_addr,
    output wire [511:0]   w16_data,
    output wire           w1_we,
    output wire [23:0]    w1_addr,
    output wire [31:0]    w1_data,
    // outbound chain own word and status
    output wire [1094:0]  own_ch,
    output wire [9:0]     ag_own,
    output wire  [106:0]   st,
    output wire  [49:0]    cc_o
);
// HARD0 keeps the shared original logical cut. HARD1 production shape NU4 is
// exact, recursively bounded structural source constructed from1f858dec1.
// No added data edge or reset release edge compared with that HARD1 reference.
generate if(HARD==0) begin:g_original
 qfd_dv_s5_ctl #(.HARD(0),.MUT(MUT),.MU_NU(MU_NU)) u_ctl(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_q),.chd_q(chd_q),.r_v(r_v),.r_idx(r_idx),.r_last(r_last),.r_d(r_d),.l9o_v(l9o_v),.stn_fault(stn_fault),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.su_nr(su_nr),.su_idle(su_idle),.su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows),.vm_fault(vm_fault),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),.sc_w1_we(sc_w1_we),.sc_w1_addr(sc_w1_addr),.sc_w1_data(sc_w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.sc_busy(sc_busy),.sc_fault(sc_fault),.stm_fault(stm_fault),.tld_fault(tld_fault),.hd_fault(hd_fault),.pc_bad(pc_bad),.sid(sid),.stn_cfg(stn_cfg),.sc_cfg(sc_cfg),.stm_cfg(stm_cfg),.su_cmd(su_cmd),.am_v(am_v),.am_idx(am_idx),.am_val(am_val),.am_u(am_u),.w16_we(w16_we),.w16_addr(w16_addr),.w16_data(w16_data),.w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.own_ch(own_ch),.ag_own(ag_own),.st(st),.cc_o(cc_o));
end else begin:g_safe4
 qfd_dv_s5_ctl_bounded4 u_ctl(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_q),.chd_q(chd_q),.r_v(r_v),.r_idx(r_idx),.r_last(r_last),.r_d(r_d),.l9o_v(l9o_v),.stn_fault(stn_fault),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.su_nr(su_nr),.su_idle(su_idle),.su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows),.vm_fault(vm_fault),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),.sc_w1_we(sc_w1_we),.sc_w1_addr(sc_w1_addr),.sc_w1_data(sc_w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.sc_busy(sc_busy),.sc_fault(sc_fault),.stm_fault(stm_fault),.tld_fault(tld_fault),.hd_fault(hd_fault),.pc_bad(pc_bad),.sid(sid),.stn_cfg(stn_cfg),.sc_cfg(sc_cfg),.stm_cfg(stm_cfg),.su_cmd(su_cmd),.am_v(am_v),.am_idx(am_idx),.am_val(am_val),.am_u(am_u),.w16_we(w16_we),.w16_addr(w16_addr),.w16_data(w16_data),.w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.own_ch(own_ch),.ag_own(ag_own),.st(st),.cc_o(cc_o));
end endgenerate
`ifndef SYNTHESIS
initial if(HARD!=0 && (MU_NU!=4 || MUT!=0)) $fatal(1,"CTLSAFE fixed production shape requires MU_NU4 MUT0");
`endif
endmodule
