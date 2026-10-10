`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical tops of the DS-ROM S81 MTP elements (stream mtp-rom, 2026-10-08).  Pin naming as the S81-PH views:
// f_* inputs, t_* outputs, ck / ckv clocks, rst / rsv resets (active low, asynchronous assert, release
// synchronised inside).  Every grant-protocol port uses the WFC's own registered pair
// (ot_dsrom_mtp_lrx: pin flops on valid / data, the grant from a flop; ot_dsrom_mtp_ltx: the
// grant in a pin flop, valid / data launched from flops), every valid / ready port a 2-entry skid.
// The two fixed-timing synchronous-read ports of the closed WFC (the prompt port into dsfd_wfc_tok, the VM read
// port into dsfd_wfc_vmx) are the only inputs that reach logic before a flop: the WFC samples the response on
// the next edge (its VM_REG / pr contract), so they are placed abutting the WFC (intra-region 90 ps budget).
//   dsfd_mtp_seq   head die      ot_dsrom_mtp_seq      MTP sequencer (accept mirror, hold, draft chain)
//   dsfd_wfc_tok   layer die S0  ot_dsrom_wfc_tok      cfg / prompt producer + draft-block store (binding 2)
//   dsfd_wfc_lnk   layer die     ot_dsrom_wfc_lnk      link bridge, DRAFT divert, VM write credits (binding 4)
//   dsfd_wfc_vmx   layer die     ot_dsrom_wfc_vmx      1.2 / 0.9 GHz VM + core-endpoint transport (bindings 1, 3)
//   dsfd_drf_fan   draft die     ot_dsrom_drf_fan      2-level draft link fan-out / fan-in node
// ---------------------------------------------------------------------------
module ot_dsrom_mtp_rstsync (input wire clk, input wire rst_n_async, output wire rst_n);
    reg [1:0] s;
    always @(posedge clk or negedge rst_n_async) if (!rst_n_async) s <= 2'b00; else s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule

module dsfd_mtp_seq #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
    parameter integer MAXU = 8, parameter integer G = 5,
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer DW = USER_W + 3 + NW
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [2*NW-1:0]   f_cfg,          // {glen, plen} (static)
    input  wire [0:0]        f_rv,  input  wire [FLIT-1:0] f_rd,  output wire [0:0] t_rg,   // RESULT in
    output wire [0:0]        t_tv,  output wire [FLIT-1:0] t_td,  input  wire [0:0] f_tg,   // token return out
    output wire [0:0]        t_sv,  output wire [SW-1:0]   t_sd,  input  wire [0:0] f_sg,   // seed out
    input  wire [0:0]        f_wv,  input  wire [USER_W-1:0] f_wd, output wire [0:0] t_wg,  // rows ready in
    output wire [0:0]        t_hv,  output wire [DW-1:0]   t_hd,  input  wire [0:0] f_hg,   // draft-head step out
    input  wire [0:0]        f_qv,  input  wire [DW-1:0]   f_qd,  output wire [0:0] t_qg,   // draft-head result in
    output wire [2*NW+USER_W+4:0] t_acc      // {fault, acc_v, acc_u, acc_a, acc_c, acc_y} (from flops)
);
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    reg [2*NW-1:0] cfg_q; always @(posedge clk) cfg_q <= f_cfg;
    wire rv, rr; wire [FLIT-1:0] rd;
    ot_dsrom_mtp_lrx #(.W(FLIT)) u_r (.clk(clk), .rst_n(rn), .l_valid(f_rv[0]), .l_ready(t_rg[0]), .l_data(f_rd),
        .c_valid(rv), .c_ready(rr), .c_data(rd));
    wire tv, tr; wire [FLIT-1:0] td;
    ot_dsrom_mtp_ltx #(.W(FLIT)) u_t (.clk(clk), .rst_n(rn), .c_valid(tv), .c_ready(tr), .c_data(td),
        .l_valid(t_tv[0]), .l_ready(f_tg[0]), .l_data(t_td));
    wire sv, sr; wire [SW-1:0] sd;
    ot_dsrom_mtp_ltx #(.W(SW)) u_s (.clk(clk), .rst_n(rn), .c_valid(sv), .c_ready(sr), .c_data(sd),
        .l_valid(t_sv[0]), .l_ready(f_sg[0]), .l_data(t_sd));
    wire wv, wr; wire [USER_W-1:0] wd;
    ot_dsrom_mtp_lrx #(.W(USER_W)) u_w (.clk(clk), .rst_n(rn), .l_valid(f_wv[0]), .l_ready(t_wg[0]), .l_data(f_wd),
        .c_valid(wv), .c_ready(wr), .c_data(wd));
    wire hv, hr; wire [DW-1:0] hd;
    ot_dsrom_mtp_ltx #(.W(DW)) u_h (.clk(clk), .rst_n(rn), .c_valid(hv), .c_ready(hr), .c_data(hd),
        .l_valid(t_hv[0]), .l_ready(f_hg[0]), .l_data(t_hd));
    wire qv, qr; wire [DW-1:0] qd;
    ot_dsrom_mtp_lrx #(.W(DW)) u_q (.clk(clk), .rst_n(rn), .l_valid(f_qv[0]), .l_ready(t_qg[0]), .l_data(f_qd),
        .c_valid(qv), .c_ready(qr), .c_data(qd));
    wire av, fl; wire [USER_W-1:0] au; wire [2:0] aa; wire [NW-1:0] ac, ay;
    ot_dsrom_mtp_seq #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .MAXU(MAXU), .G(G)) u_seq (
        .clk(clk), .rst_n(rn), .cfg_plen(cfg_q[NW-1:0]), .cfg_glen(cfg_q[2*NW-1:NW]),
        .r_valid(rv), .r_ready(rr), .r_data(rd), .t_valid(tv), .t_ready(tr), .t_data(td),
        .s_valid(sv), .s_ready(sr), .s_data(sd), .w_valid(wv), .w_ready(wr), .w_user(wd),
        .h_valid(hv), .h_ready(hr), .h_data(hd), .q_valid(qv), .q_ready(qr), .q_data(qd),
        .acc_v(av), .acc_u(au), .acc_a(aa), .acc_c(ac), .acc_y(ay), .fault(fl));
    reg [2*NW+USER_W+4:0] acc_q; always @(posedge clk) acc_q <= {fl, av, au, aa, ac, ay};
    assign t_acc = acc_q;
endmodule

module dsfd_wfc_tok #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer UCW = 10,
    parameter integer MAXU = 8, parameter integer PU = 8, parameter integer PMAX = 16, parameter integer G = 5
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [2+USER_W+2*NW:0] f_c,       // {we, sel[1:0], user, pos, val} static configuration
    output wire [UCW+2*NW-1:0] t_cfg,        // {users, plen, glen} to the WFC cfg_* (flops)
    input  wire [FLIT:0]     f_dw,           // {v, DRAFT flit} from dsfd_wfc_lnk
    input  wire [USER_W+NW+4:0] f_pr,        // {re, user, pos, blk} from the WFC (fixed one-edge read)
    output wire [NW:0]       t_pr,           // {qk, q} (flops)
    output wire [0:0]        t_ft
);
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    reg [2+USER_W+2*NW:0] c_q; always @(posedge clk) c_q <= f_c;
    wire [UCW-1:0] cu; wire [NW-1:0] cp, cg, q; wire qk, fl;
    ot_dsrom_wfc_tok #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .UCW(UCW), .MAXU(MAXU), .PU(PU), .PMAX(PMAX), .G(G)) u_tok (
        .clk(clk), .rst_n(rn), .c_we(c_q[2+USER_W+2*NW]), .c_sel(c_q[USER_W+2*NW +: 2]), .c_user(c_q[2*NW +: USER_W]),
        .c_pos(c_q[NW +: NW]), .c_val(c_q[NW-1:0]), .cfg_users(cu), .cfg_prompt_len(cp), .cfg_gen_len(cg),
        .dw_v(f_dw[FLIT]), .dw_d(f_dw[FLIT-1:0]),
        .pr_re(f_pr[USER_W+NW+4]), .pr_user(f_pr[NW+4 +: USER_W]), .pr_pos(f_pr[4 +: NW]), .pr_blk(f_pr[3:0]),
        .pr_q(q), .pr_qk(qk), .fault(fl));
    assign t_cfg = {cu, cp, cg};
    assign t_pr = {qk, q};
    assign t_ft = fl;
endmodule

module dsfd_wfc_lnk #(parameter integer FLIT = 512, parameter integer VCRED = 8) (
    input  wire [0:0]      ck,
    input  wire [0:0]      rst,
    input  wire [0:0]      f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lir,   // die link in {last, data}
    output wire [0:0]      t_wiv, output wire [FLIT:0] t_wid, input  wire [0:0] f_wig,   // to WFC in_*
    input  wire [0:0]      f_wov, input  wire [FLIT:0] f_wod, output wire [0:0] t_wog,   // from WFC out_*
    output wire [0:0]      t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_lor,   // die link out
    output wire [FLIT:0]   t_dw,                                                         // {v, DRAFT} to dsfd_wfc_tok
    input  wire [0:0]      f_vc,                                                         // VM credit return
    output wire [0:0]      t_ft
);
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    reg vc_q; always @(posedge clk) vc_q <= f_vc[0];
    wire dv; wire [FLIT-1:0] dd; wire fl;
    ot_dsrom_wfc_lnk #(.FLIT(FLIT), .VCRED(VCRED)) u_lnk (.clk(clk), .rst_n(rn),
        .li_valid(f_liv[0]), .li_ready(t_lir[0]), .li_data(f_lid[FLIT-1:0]), .li_last(f_lid[FLIT]),
        .wi_valid(t_wiv[0]), .wi_grant(f_wig[0]), .wi_data(t_wid[FLIT-1:0]), .wi_last(t_wid[FLIT]),
        .wo_valid(f_wov[0]), .wo_grant(t_wog[0]), .wo_data(f_wod[FLIT-1:0]), .wo_last(f_wod[FLIT]),
        .lo_valid(t_lov[0]), .lo_ready(f_lor[0]), .lo_data(t_lod[FLIT-1:0]), .lo_last(t_lod[FLIT]),
        .dw_v(dv), .dw_d(dd), .vc_ret(vc_q), .fault(fl));
    assign t_dw = {dv, dd};
    assign t_ft = fl;
endmodule

module dsfd_wfc_vmx #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer VWA = 15,
    parameter integer TXB = 0, parameter integer XWORDS = 46, parameter integer SIDE_TXB = 0, parameter integer SIDE_WORDS = 0,
    parameter integer LAG = 0,
    parameter integer RQFREE = `ifdef OT_WFCVMX_PRED 2 `elsif OT_WFCVMX_RQ_FREE 1 `else 0 `endif
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        ckv,
    input  wire [0:0]        rst,
    input  wire [0:0]        rsv,
    // fast: the WFC
    input  wire [VWA+FLIT:0] f_vw,           // {we, waddr, wdata}
    input  wire [VWA:0]      f_vr,           // {re, raddr} (fixed one-edge read)
    output wire [FLIT-1:0]   t_vq,
    input  wire [USER_W+2*NW:0] f_cs,        // {start, user, token, pos}
    output wire [NW+32:0]    t_cd,           // {done, next_token, next_val}
    output wire [0:0]        t_vc,           // VM write credit return (to dsfd_wfc_lnk)
    // slow: the VM and the stage core
    output wire [0:0]        t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swr,   // VM write {addr, data}
    input  wire [0:0]        f_swa,                                                          // VM write ACK
    output wire [0:0]        t_srv, output wire [VWA-1:0] t_srd, input wire [0:0] f_srr,        // VM read request
    input  wire [FLIT:0]     f_srq,                                                          // {rv, rq} read response
    output wire [USER_W+2*NW:0] t_ks,                                                        // {start, user, token, pos}
    input  wire [NW+32:0]    f_kd,                                                           // {done, next_token, next_val}
    output wire [0:0]        t_ft
);
    wire fclk = ck[0];
    wire sclk = ckv[0];
    wire frn, srn;
    ot_dsrom_mtp_rstsync u_rf (.clk(fclk), .rst_n_async(rst[0]), .rst_n(frn));
    ot_dsrom_mtp_rstsync u_rsl (.clk(sclk), .rst_n_async(rsv[0]), .rst_n(srn));
    // slow-side pin flops
    reg swa_q, srv_q, kd_v; reg [FLIT-1:0] srq_q; reg [NW+31:0] kd_q;
    always @(posedge sclk) begin
        swa_q <= f_swa[0] && srn; srv_q <= f_srq[FLIT] && srn; srq_q <= f_srq[FLIT-1:0];
        kd_v <= f_kd[NW+32] && srn; kd_q <= f_kd[NW+31:0];
    end
    wire swv, swr, srv, srr; wire [VWA-1:0] swa, sra; wire [FLIT-1:0] swd;
    wire ks; wire [USER_W-1:0] ku; wire [NW-1:0] kt, kp; wire cd; wire [NW-1:0] ct; wire [31:0] cv; wire vc, fl;
    ot_dsrom_wfc_vmx #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .VWA(VWA), .TXB(TXB), .XWORDS(XWORDS),
                       .SIDE_TXB(SIDE_TXB), .SIDE_WORDS(SIDE_WORDS), .LAG(LAG), .RQFREE(RQFREE)) u_vmx (
        .fclk(fclk), .frst_n(frn), .vm_we(f_vw[VWA+FLIT]), .vm_waddr(f_vw[FLIT +: VWA]), .vm_wdata(f_vw[FLIT-1:0]),
        .vm_re(f_vr[VWA]), .vm_raddr(f_vr[VWA-1:0]), .vm_rq(t_vq),
        .core_start(f_cs[USER_W+2*NW]), .core_user(f_cs[2*NW +: USER_W]), .core_token(f_cs[NW +: NW]), .core_pos(f_cs[NW-1:0]),
        .core_done(cd), .core_next_token(ct), .core_next_val(cv), .vc_ret(vc),
        .sclk(sclk), .srst_n(srn), .sw_valid(swv), .sw_ready(swr), .sw_addr(swa), .sw_data(swd), .sw_ack(swa_q),
        .sr_valid(srv), .sr_ready(srr), .sr_addr(sra), .sr_rv(srv_q), .sr_rq(srq_q),
        .k_start(ks), .k_user(ku), .k_token(kt), .k_pos(kp), .k_done(kd_v), .k_next_token(kd_q[NW+31:32]),
        .k_next_val(kd_q[31:0]), .fault(fl));
    ot_dsrom_mtp_skid #(.W(VWA + FLIT)) u_sw (.clk(sclk), .rst_n(srn), .in_valid(swv), .in_ready(swr), .in_data({swa, swd}),
        .out_valid(t_swv[0]), .out_ready(f_swr[0]), .out_data(t_swd));
    ot_dsrom_mtp_skid #(.W(VWA)) u_sr (.clk(sclk), .rst_n(srn), .in_valid(srv), .in_ready(srr), .in_data(sra),
        .out_valid(t_srv[0]), .out_ready(f_srr[0]), .out_data(t_srd));
    assign t_ks = {ks, ku, kt, kp};
    assign t_cd = {cd, ct, cv};
    assign t_vc = vc;
    assign t_ft = fl;
endmodule

module dsfd_drf_fan #(parameter integer FLIT = 512, parameter integer N = 4) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [0:0]        f_uiv, input  wire [FLIT:0] f_uid, output wire [0:0] t_uir,      // from the parent
    output wire [0:0]        t_uov, output wire [FLIT:0] t_uod, input  wire [0:0] f_uor,      // to the parent
    output wire [0:0]        t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_lor,      // to this die's engine
    input  wire [0:0]        f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lir,      // from this die's engine
    output wire [N-1:0]      t_cov, output wire [N*(FLIT+1)-1:0] t_cod, input wire [N-1:0] f_cor,  // to children
    input  wire [N-1:0]      f_civ, input  wire [N*(FLIT+1)-1:0] f_cid, output wire [N-1:0] t_cir, // from children
    output wire [0:0]        t_ft
);
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    wire fl;
    ot_dsrom_drf_fan #(.FLIT(FLIT), .N(N)) u_fan (.clk(clk), .rst_n(rn),
        .up_in_valid(f_uiv[0]), .up_in_ready(t_uir[0]), .up_in_data(f_uid),
        .up_out_valid(t_uov[0]), .up_out_ready(f_uor[0]), .up_out_data(t_uod),
        .lo_out_valid(t_lov[0]), .lo_out_ready(f_lor[0]), .lo_out_data(t_lod),
        .lo_in_valid(f_liv[0]), .lo_in_ready(t_lir[0]), .lo_in_data(f_lid),
        .ch_out_valid(t_cov), .ch_out_ready(f_cor), .ch_out_data(t_cod),
        .ch_in_valid(f_civ), .ch_in_ready(t_cir), .ch_in_data(f_cid), .fault(fl));
    assign t_ft = fl;
endmodule
