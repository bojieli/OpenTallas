// WHAT-IF DIAGNOSTIC COPY (TOK-QK/S8): SU8 start delayed 3 edges vs su_cmd (PROG read); not RTL of record.
`timescale 1ns/1ps
// QW-S5-LP 10-21: = qfd_dv_s5_suvm_su8p2 (Codex 5949f90af) with the VM8 group P3 qfd_dv_s5_vm8q (claude/qw-slice2w3-1021 a2e2190cf, same ports;
// VM reads/writes +1, reset release +2 vs P2; p_q (SU8 si) timing unchanged). UNCLOSED composition: u_vm8q = hard child (vm8q view
// once it closes), u_su8 = CLOSED qfd_dv_s5_su8_rst3 422d006e2.
module qfd_dv_s8_suvm_rp1 #(parameter integer HARD = 1, parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [9:0]     su_cmd,         // {c_su, p_idx 9}
    // group relay (stage 1) -> the 8 lane relays
    output wire [499:0]   gb,             // GBW = NW + (NW + 1) + 5 AW + 6 + 8 + 9 + 64 + WR 16 = 500
    output wire [2:0]     gv,
    output wire [7:0]     lv1,            // live, relay stage 1 (per lane)
    output wire [8*96-1:0] pd1,           // {cura, curb, curc, curd} + lane offsets, relay stage 1 (per lane)
    // lane relay outputs (to the VM / the issue control)
    input  wire [7:0]     va_re, vb_re, vc_re, cr_re, vm_we, kv_we, l_retire, l_last, l_fault, l_wrom_re,
    input  wire [8*24-1:0] va_addr, vb_addr, vc_addr, cr_addr, vm_waddr, l_wrom_addr,
    input  wire [8*32-1:0] vm_wdata,
    output wire [8*32-1:0] va_q, vb_q, vc_q,
    output wire [8*64-1:0] cr_q,
    // reducer state (qfd_dv_s5_red)
    input  wire           rd_v,
    input  wire           red_busy,
    input  wire           red_fault,
    // VM writes from ctl / tables from the stream (+ tload)
    input  wire           w16_we,
    input  wire [23:0]    w16_addr,
    input  wire [511:0]   w16_data,
    input  wire           w1_we,
    input  wire [23:0]    w1_addr,
    input  wire [31:0]    w1_data,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data,
    output wire           su_nr,
    output wire            su_idle,
    output wire            su_fault,
    output wire  [15:0]    su_prog,
    output wire  [15:0]    su_rows,
    output wire           vm_fault
);
    wire [456:0] si;
    wire [243:0] su_gb;
    wire [255:0] bs_q;
    reg [255:0] bs_group;
    reg [7:0] lvm_we;
    // Same edge as VM8's pwin[] input publications (and original VM7 lvm_we).
    always @(posedge ck)begin lvm_we<=vm_we;bs_group<=bs_q;end
    // BTAB takes only its original parent group relay, bypassing SU8 internals.
    assign gb={su_gb,bs_group};
    wire f_va,f_vb,f_vc,f_crl,f_crh,f_bt;
    assign vm_fault=f_va|f_vb|f_vc|f_crl|f_crh|f_bt;
    qfd_dv_s8_vm8q_rp1 u_vm8q(.ck(ck),.rst_n(rst_n),
        .a_re(va_re),.b_re(vb_re),.c_re(vc_re),.a_addr(va_addr),.b_addr(vb_addr),.c_addr(vc_addr),
        .a_q(va_q),.b_q(vb_q),.c_q(vc_q),.cr_re(cr_re),.cr_addr(cr_addr),.cr_q(cr_q),
        .bs_re(l_wrom_re[0]),.bs_addr(l_wrom_addr[23:0]),.bs_q(bs_q),
        .p_re(su_cmd[9]),.p_idx(su_cmd[8:0]),.p_q(si),
        .vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
        .w16_we(w16_we),.w16_addr(w16_addr),.w16_data(w16_data),
        .w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),
        .tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data),
        .f_va(f_va),.f_vb(f_vb),.f_vc(f_vc),.f_crl(f_crl),.f_crh(f_crh),.f_bt(f_bt));
    // CLOSED 422d006e2 child, exact MUT0 interface. Start and program request
    // use the SAME landed su_cmd source; no retiming of one independently.
    reg [2:0] wf_st; always @(posedge ck or negedge rst_n) if (!rst_n) wf_st <= 0; else wf_st <= {wf_st, su_cmd[9]};
    qfd_dv_s5_su8_rst3 u_su8(.ck(ck),.rst_n(rst_n),.start(wf_st[2]),.si(si),
        .l_retire(l_retire[0]),.l_last(l_last[0]),.l_fault(l_fault),.kv_we(kv_we),
        .rd_v(rd_v),.red_busy(red_busy),.red_fault(red_fault),.lvm_we(lvm_we),
        .gb(su_gb),.gv(gv),.lv1(lv1),.pd1(pd1),.su_nr(su_nr),.su_idle(su_idle),
        .su_fault(su_fault),.su_prog(su_prog),.su_rows(su_rows));
endmodule
