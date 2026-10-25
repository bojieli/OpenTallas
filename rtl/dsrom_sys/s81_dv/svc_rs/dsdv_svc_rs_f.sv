`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// PL-SVC (PARENTS-LANDED, 10-18): dsdv_svc_rs_f, the WIRES-ONLY flat form of the regional service slice dsdv_svc_rs
// (the 14 non-entry slices; ENTRY = 0 of dsdv_svc_rs_c), the input of tools/landed_parent/lp.py.
// Same ports and the same cycle behaviour as dsdv_svc_rs (proved by tb_dsdv_svc_rs_feq: lockstep against the original),
// except that the up tree face up_i / up_o [16 a face] is split into two lanes (coordinator 10-18, option (a)):
//   up_d_i / up_d_o [13 a face] = {done, cr 6, ack 6}       = up bits {[13], [11:0]}
//   up_f_i / up_f_o [3 a face]  = {rg fault, rg live, fault} = up bits {[15], [14], [12]}
// so that the job END / done reduce never depends on the SM head's fault o_fo (clock region sm): in the landed slice
// up_d keeps offset 0 and only up_f sits behind the o_fo landing.  The entry variant is dsdv_svc_rs_entry_f.
// The glue of dsdv_svc_rs_c is moved, unchanged, into small children, one per function, so that each child can sit in the
// clock region of its neighbours:
//   dsdv_svc_rs_dn    dn stream tree: face in flops + relay, centre register cs, face out relay + pin flop, stray check
//   dsdv_svc_rs_attw  dsdv_svc_att + its role inputs (tile, gd, pvs; root = 0)
//   dsdv_svc_rs_se    SE row assembler (tap -> 16-score rows) + the SM row mux + its collision fault
//   dsdv_svc_rs_pv    P.V return tree (child faces -> parent face, compiled windows, collision / stray fault)
//   dsdv_svc_rs_ud    up_d lane node (done AND, credit / ack sums)
//   dsdv_svc_rs_uf    local fault OR, ctrl_rg2 hs status synchroniser, up_f lane node (fault OR, rg fault OR, rg live AND)
//   dsdv_svc_rs_smw   ot_s81_su_sms + its head strap (cfg_g = tile)
// plus the unchanged children 2 x dsfd_svc_pc and dsdv_svc_sx.  Every glue child re-derives the slice's reset
// synchroniser (2 flops) and role register from rst / sid exactly as dsdv_svc_rs_c did once (dsdv_svc_rs_rl), so each
// copy holds the same value in the same cycle as the original single copy.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_rs_f #(
    parameter integer AMUT = 0,             // dsdv_svc_rs MUT (attention bench negative controls); lp.py owns MUT
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer SRAM_MACRO = 0,
    parameter integer PMEM = 1              // SVCB: att p store (0 = dropped: kits for non-owner positions)
) (
    input  wire              ck,
    input  wire              rst,
    input  wire [3:0]        sid,
    input  wire [4*805-1:0]  dn_i,
    output wire [4*805-1:0]  dn_o,
    input  wire [4*13-1:0]   up_d_i,
    output wire [4*13-1:0]   up_d_o,
    input  wire [4*3-1:0]    up_f_i,
    output wire [4*3-1:0]    up_f_o,
    input  wire [4*514-1:0]  ri,
    output wire [4*514-1:0]  ro,
    input  wire [3:0]        gi_v,
    input  wire [4*2132-1:0] gi_d,
    output wire [3:0]        go_v,
    output wire [4*2132-1:0] go_d,
    input  wire [3:0]        si_v,
    input  wire [4*1076-1:0] si_d,
    output wire [3:0]        so_v,
    output wire [4*1076-1:0] so_d,
    output wire [2*341-1:0]  rq,
    input  wire [1:0]        rk,
    input  wire [1:0]        wd,
    input  wire [1:0]        rv,
    input  wire [2*256-1:0]  r_data,
    input  wire [2*17-1:0]   r_tag,
    input  wire [2*4-1:0]    r_beat,
    input  wire [1:0]        hs,
    output wire              w_v,
    output wire [13:0]       w_a,
    output wire [15:0]       w_m,
    output wire [511:0]      w_d,
    output wire [11:0]       w_st
);
    wire [804:0] cs;
    wire dstray;
    wire [2*341-1:0] qrq; wire [1:0] qrk, qwd, qrv; wire [2*256-1:0] qr_data; wire [2*17-1:0] qr_tag; wire [2*4-1:0] qr_beat;
    wire l_v; wire [2131:0] l_d; wire a_pv_v; wire [512:0] a_pv_d;
    wire sm_st, sm_rv, sm_rp; wire [3:0] sm_kind; wire [7:0] sm_jid; wire [2:0] sm_rj; wire [511:0] sm_rd;
    wire go, done; wire [9:0] tjob; wire [7:0] tagj; wire [1:0] hcr, hack; wire a_f;
    wire rt_v, t_v, x_f; wire [2131:0] rt_d; wire [19:0] t_tag; wire [127:0] t_y; wire [3:0] t_f;
    wire r_v, r_p, rcol; wire [2:0] r_j; wire [511:0] r_d;
    wire o_fo, r_f;

    dsdv_svc_rs_dn #(.ST(ST)) u_dn (.ck(ck), .rst(rst), .sid(sid), .hst(805'd0), .dn_i(dn_i), .dn_o(dn_o), .cs(cs), .dstray(dstray));

    dsfd_svc_pc u_pc0 (.ck(ck), .rst(rst), .qrq(qrq[340:0]), .rq(rq[340:0]), .rk(rk[0]), .qrk(qrk[0]),
        .wd(wd[0]), .qwd(qwd[0]), .rv(rv[0]), .r_data(r_data[255:0]), .r_tag(r_tag[16:0]),
        .r_beat(r_beat[3:0]), .qrv(qrv[0]), .qr_data(qr_data[255:0]), .qr_tag(qr_tag[16:0]),
        .qr_beat(qr_beat[3:0]));
    dsfd_svc_pc u_pc1 (.ck(ck), .rst(rst), .qrq(qrq[681:341]), .rq(rq[681:341]), .rk(rk[1]), .qrk(qrk[1]),
        .wd(wd[1]), .qwd(qwd[1]), .rv(rv[1]), .r_data(r_data[511:256]), .r_tag(r_tag[33:17]),
        .r_beat(r_beat[7:4]), .qrv(qrv[1]), .qr_data(qr_data[511:256]), .qr_tag(qr_tag[33:17]),
        .qr_beat(qr_beat[7:4]));

    dsdv_svc_rs_attw #(.MUT(AMUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .PMEM(PMEM)) u_att (.ck(ck), .rst(rst), .sid(sid),
        .cs(cs), .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(a_pv_v), .pv_od(a_pv_d),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go), .tjob_o(tjob), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(a_f));

    dsdv_svc_sx #(.MUT(0)) u_sx (.ck(ck), .rst(rst), .sid(sid), .l_v(l_v), .l_d(l_d),
        .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v), .go_d(go_d), .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d),
        .rt_v(rt_v), .rt_d(rt_d), .t_v(t_v), .t_tag(t_tag), .t_y(t_y), .t_f(t_f), .gh_i(4272'd0), .gh_o(), .fault(x_f));

    dsdv_svc_rs_se u_se (.ck(ck), .rst(rst), .t_v(t_v), .t_tag(t_tag), .t_y(t_y), .t_f(t_f), .tjob(tjob), .go(go),
        .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd), .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(r_d), .rcol(rcol));

    dsdv_svc_rs_smw u_sm (.ck(ck), .rst(rst), .sid(sid), .j_st(sm_st), .j_kind(sm_kind), .j_jid(sm_jid),
        .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(r_d), .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st), .o_fo(o_fo));

    dsdv_svc_rs_pv #(.ST(ST)) u_pv (.ck(ck), .rst(rst), .sid(sid), .ri(ri), .ro(ro), .a_pv_v(a_pv_v), .a_pv_d(a_pv_d),
        .r_f(r_f), .pv_v(), .pv_d());

    dsdv_svc_rs_ud #(.ST(ST)) u_ud (.ck(ck), .rst(rst), .sid(sid), .done(done), .hcr(hcr), .hack(hack),
        .up_d_i(up_d_i), .up_d_o(up_d_o), .ucd());

    dsdv_svc_rs_uf #(.ST(ST)) u_uf (.ck(ck), .rst(rst), .sid(sid), .hs(hs), .a_f(a_f), .x_f(x_f), .rcol(rcol), .o_fo(o_fo),
        .dstray(dstray), .r_f(r_f), .up_f_i(up_f_i), .up_f_o(up_f_o), .ucf(), .hl());
endmodule

