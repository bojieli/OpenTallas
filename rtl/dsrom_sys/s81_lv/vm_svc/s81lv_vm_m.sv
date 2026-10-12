`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// s81lv_vm_m (el1011-s81lv/B, 2026-10-12): the S81 layer vehicle's VM = dsfd_sp_vm_m (rtl/dsrom_sys/s81_ph/vm/
// dsfd_sp_vm.sv, the exact composition the closed routes use: dsfd_vm_fe + NS x 4 dsfd_vm_bgq28-equivalent tiles +
// dsfd_vm_be) with ONE bank group real and the other three as the address-checked TLM s81lv_vm_bgq_tlm.
// The body below is dsfd_sp_vm_m verbatim (same ports, parameters, FE / BE instances and names u_fe / u_be, so every
// hierarchical probe of tb_dsfd_sp_vm works unchanged) except the tile generate: tile t of every slice is the real
// dsfd_vm_bgq #(NP 28, NPR 10, NSTG 2, EP 2) (= dsfd_vm_bgq28) when t == GREAL, else s81lv_vm_bgq_tlm.
// GREAL = 0 .. 3 (the real group: banks 8*GREAL .. 8*GREAL+7 = rows with row[4:3] == GREAL); GREAL = 4 -> all 16
// tiles real (= dsfd_sp_vm_m, reference configuration).  Source-currency: re-sync this body with dsfd_sp_vm_m when
// it changes (tools/s81_lv/vm_svc_gate.py check-sync diffs the two bodies).
// ---------------------------------------------------------------------------------------------------------------
module s81lv_vm_m #(
    parameter integer GREAL = 0,
    parameter integer NS = 4, parameter integer NSTG = 2, parameter integer QD = 4, parameter integer MACRO = 1,
    parameter integer VF = 13, parameter integer VR = 13, parameter integer NSLOT = 4, parameter integer P2D = 40,
    parameter integer CQD = 4, parameter integer LA = 12, parameter integer LTO = 16,
    parameter integer NSVC = 1, parameter integer LD = 64, parameter integer NLP = 2, parameter integer LMACRO = 1
) (
    input  wire [0:0]    ck, input wire [0:0] rst, input wire [0:0] cks, input wire [0:0] rss,
    input  wire [0:0]    f_swv, input wire [526:0] f_swd, output wire [0:0] t_swg,
    input  wire [0:0]    f_srv, input wire [30:0]  f_srd, output wire [0:0] t_srg,
    output wire [52:0]   t_ks,
    output wire [1025:0] t_srq, output wire [0:0] t_err,
    input  wire [13375:0] f_cap,
    input  wire [0:0]    vwe, input wire [13:0] vwa, input wire [511:0] vwd,
    input  wire [0:0]    vre, input wire [13:0] vra, output wire [0:0] vrv, output wire [511:0] vrq,
    input  wire [0:0]    cv, input wire [83:0] cd, output wire [0:0] dv, output wire [7:0] dt,
    input  wire [NSVC*1027-1:0] f_svc, input wire [2099:0] f_coll, output wire [2:0] t_cts,
    input  wire [514:0]  f_sel, input wire [514:0] f_col, input wire [1025:0] f_hc,
    output wire [16*513-1:0] t_bl,
    output wire [0:0]    c_wv, output wire [9:0] c_wd, input wire [0:0] c_wr,
    output wire [NSLOT-1:0] t_rdy,
    output wire [0:0]    c_l0v, output wire [603:0] c_l0d, input wire [0:0] c_l0r,
    output wire [0:0]    flt, output wire [31:0] fvec, output wire [2:0] max_occ
);
    localparam integer NP = 28, NPR = 10, NT = 4, RA = 14, OW = 3;
    // el1011-ds-vm/bgq28: the hard tile's enqueue pipeline (EP, = dsfd_vm_bgq28) adds ED = EP + 1 cycles to every op
`ifdef OT_VM28_EP1
    localparam integer EP = 1;
`else
    localparam integer EP = 2;
`endif
    localparam integer ED = (EP == 0) ? 0 : EP + 1;
    localparam integer FRL = 2;         // el1011-ds-vm/fe: FE order register -> slice pin relay stages (shifts f_* and o_*
                                        // alike: MD, the tile-3 f_* -> o_* skew, is unchanged)
    localparam integer MD = 4 * NSTG + QD + 9 - 4 * (NSTG + 1) + ED;
    wire [NS*NP-1:0] mv, mwe; wire [NS*NP*RA-1:0] mrow; wire [NS*NP*4-1:0] mm; wire [NS*NP*128-1:0] md;
    wire [NS*4-1:0] mrf; wire [15:0] fe_flt;
    wire p2c;
    dsfd_vm_fe #(.NS(NS), .VF(VF), .VR(VR), .NSLOT(NSLOT), .P2D(P2D), .CQD(CQD), .LA(LA), .LTO(LTO), .NSVC(NSVC), .LD(LD),
                 .NLP(NLP), .LMACRO(LMACRO), .FRL(FRL)) u_fe (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .f_swv(f_swv), .f_swd(f_swd), .t_swg(t_swg), .f_srv(f_srv), .f_srd(f_srd),
        .t_srg(t_srg), .t_ks(t_ks), .f_cap(f_cap), .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra),
        .cv(cv), .cd(cd), .dv(dv), .dt(dt), .f_svc(f_svc), .f_coll(f_coll), .t_cts(t_cts), .f_sel(f_sel), .f_col(f_col), .f_hc(f_hc),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(c_wr), .t_rdy(t_rdy), .f_p2c(p2c),
        .m_v(mv), .m_we(mwe), .m_row(mrow), .m_mask(mm), .m_d(md), .m_rf(mrf), .fe_flt(fe_flt));
    wire [NS*NPR-1:0] ov; wire [NS*NPR*128-1:0] od; wire [NS*4-1:0] of; wire [NS*3-1:0] oo;
    wire [NP-1:0] f0v, f0we; wire [NP*128-1:0] f0d;
    genvar h, t;
    generate for (h = 0; h < NS; h = h + 1) begin : g_h
        wire [NP-1:0] cv_ [0:NT], cwe [0:NT];
        wire [NPR-1:0] cov [0:NT];
        wire [NP*RA-1:0] crow [0:NT]; wire [NP*4-1:0] cm [0:NT]; wire [NP*128-1:0] cd_ [0:NT];
        wire [NPR*128-1:0] cod [0:NT];
        wire [3:0] cof [0:NT]; wire [OW-1:0] coo [0:NT];
        assign cv_[0] = mv[h*NP +: NP]; assign cwe[0] = mwe[h*NP +: NP]; assign crow[0] = mrow[h*NP*RA +: NP*RA];
        assign cm[0] = mm[h*NP*4 +: NP*4]; assign cd_[0] = md[h*NP*128 +: NP*128];
        // chain head: no upstream tile (no read data, occupancy 0); the FE status enters on the fault lane
        assign cov[0] = {NPR{1'b0}}; assign cod[0] = {NPR*128{1'b0}}; assign cof[0] = mrf[h*4 +: 4];
        assign coo[0] = {OW{1'b0}};
        for (t = 0; t < NT; t = t + 1) begin : g_t
            wire [1:0] gid = t;
            if (GREAL == 4 || t == GREAL) begin : g_real
                // = dsfd_vm_bgq28 (the hard tile) at the default parameters
                dsfd_vm_bgq #(.NP(NP), .NPR(NPR), .NB(32), .NBL(8), .QD(QD), .RQ(8), .MACRO(MACRO), .DW(128), .NSTG(NSTG), .EP(EP)) u_bg (
                    .ck(ck), .rs(rst), .grp(gid),
                    .i_v(cv_[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cm[t]), .i_d(cd_[t]),
                    .f_v(cv_[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cm[t+1]), .f_d(cd_[t+1]),
                    .r_v(cov[t]), .r_d(cod[t]), .r_f(cof[t]), .r_o(coo[t]),
                    .o_v(cov[t+1]), .o_d(cod[t+1]), .o_f(cof[t+1]), .o_o(coo[t+1]));
            end else begin : g_tlm
                s81lv_vm_bgq_tlm #(.NP(NP), .NPR(NPR), .DW(128), .NSTG(NSTG), .QD(QD), .EP(EP)) u_bg (
                    .ck(ck), .rs(rst), .grp(gid),
                    .i_v(cv_[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cm[t]), .i_d(cd_[t]),
                    .f_v(cv_[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cm[t+1]), .f_d(cd_[t+1]),
                    .r_v(cov[t]), .r_d(cod[t]), .r_f(cof[t]), .r_o(coo[t]),
                    .o_v(cov[t+1]), .o_d(cod[t+1]), .o_f(cof[t+1]), .o_o(coo[t+1]));
            end
        end
        assign ov[h*NPR +: NPR] = cov[NT]; assign od[h*NPR*128 +: NPR*128] = cod[NT]; assign of[h*4 +: 4] = cof[NT];
        assign oo[h*3 +: 3] = coo[NT];
        if (h == 0) begin : g_f
            assign f0v = cv_[NT]; assign f0we = cwe[NT]; assign f0d = cd_[NT];
        end
    end endgenerate
    dsfd_vm_be #(.NS(NS), .P2D(P2D), .MD(MD)) u_be (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .o_v(ov), .o_d(od), .o_f(of), .o_o(oo),
        .f_v5(f0v[5]), .f_we5(f0we[5]), .f_m5(f0d[5*128 +: 92]), .fe_flt(fe_flt),
        .f_vx({f0v[9], f0v[8], f0v[2], f0v[7], f0v[6]}), .f_wex({f0we[9], f0we[8], f0we[2], f0we[7], f0we[6]}),
        .f_mx({f0d[9*128 +: 4], f0d[8*128 +: 4], f0d[2*128 +: 4], f0d[7*128 +: 4], f0d[6*128 +: 4]}),
        .t_srq(t_srq), .t_err(t_err), .vrv(vrv), .vrq(vrq), .t_bl(t_bl),
        .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(c_l0r), .t_p2c(p2c), .flt(flt), .fvec(fvec), .max_occ(max_occ));
endmodule
