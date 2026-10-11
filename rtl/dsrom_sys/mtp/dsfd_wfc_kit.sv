`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_wfc_src / dsfd_wfc_stg: the WFC kit as one die master per layer-class stage die (Claude mtp-wfc,
// 2026-10-10; budget-audit gap dsrom_mtp_draft_hw (b): "WFC and accept not integrated").
// The S81 generator's --wfc-hard slab (master dsfd_wfc) reserved the closed SOURCE + STG tokpipe outlines only and
// wired six aggregate buses whose widths did not match any port.  The kit is what a stage die actually instantiates,
// built ONLY from closed elements with their closed parameters:
//   SOURCE (S0 die)  ot_dsrom_wfc_tokpipe_src  (mtp-wfc-src-hard-mxb-910e67c7b: physical/dsrom_wfc_tokpipe/src_basis.json,
//                    PROMPT_EXTRA 2)  + dsfd_wfc_tok_hard (e829cb457-r2, HARD_READ)  + dsfd_wfc_lnk (b-0cd6caa1b)
//                    + dsfd_wfc_vmx RQFREE 2 (prd-c39e235bb-o292-r2), XWORDS 41
//   STAGE (others)   ot_dsrom_wfc_tokpipe_stg  (9f7a7f35e: stg_basis.json) + dsfd_wfc_lnk + dsfd_wfc_vmx RQFREE 2, XWORDS 46
// Die-facing ports (exact widths; each grant / ready travels against its data):
//   link in   f_liv f_lid[513] t_lir          (collective -> wfc 514, wfc -> collective grant 1)
//   link out  t_lov t_lod[513] f_lor          (wfc -> collective 514, collective -> wfc grant 1)
//   VM        t_swv t_swd[527] f_swr f_swa t_srv t_srd[15] f_srr f_srq[513]   (serial 0.9 GHz domain, ckv)
//   capture   t_ks[53] f_kd[54]                (stage core start / done, serial domain)
//   SOURCE    f_c[55] (static configuration, host), t_tok[53] {valid, user, pos, id} committed token (to host),
//             t_cfg[52] {users, plen, glen} (to the head-die sequencer's static f_cfg)
//   t_ft[4]   {proto, lnk, tok, vmx} faults (from flops inside each element)
// Transactions are exactly those of the separately benched elements: no logic sits between them.
// ---------------------------------------------------------------------------
module dsfd_wfc_src #(parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
                      parameter integer VWA = 15) (
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lir,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_lor,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [VWA-1:0] t_srd, input wire [0:0] f_srr, input wire [FLIT:0] f_srq,
    output wire [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    input  wire [2+USER_W+2*NW:0] f_c,
    output wire [USER_W+2*NW:0] t_tok,
    output wire [USER_W+2*NW-1:0] t_cfg,
    output wire [3:0] t_ft
);
    wire clk = ck[0];
    wire w_in_valid, w_in_ready, w_in_last, w_out_valid, w_out_ready, w_out_last;
    wire [FLIT-1:0] w_in_data, w_out_data;
    wire core_start, core_done_w; wire [NW-1:0] core_token, core_pos, cnt_tok; wire [31:0] cnt_val;
    wire [USER_W-1:0] core_user; wire [29:0] kv_base;
    wire vm_we, vm_re; wire [VWA-1:0] vm_waddr, vm_raddr; wire [FLIT-1:0] vm_wdata, vm_rq;
    wire pr_re; wire [USER_W-1:0] pr_user; wire [NW-1:0] pr_pos, pr_q; wire [3:0] pr_blk; wire pr_qk;
    wire core_busy, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash;
    wire [USER_W-1:0] tok_user, users_done; wire [NW-1:0] tok_pos, tok_id;
    wire [9:0] cfg_users; wire [NW-1:0] cfg_plen, cfg_glen;
    wire [FLIT:0] dw; wire vc_ret, lnk_ft, tok_ft, vmx_ft;
    ot_dsrom_wfc_tokpipe_src #(.WAVE(1), .WIN(6), .FLIT(FLIT), .NW(NW), .AW(30), .VWA(VWA), .USER_W(USER_W), .MAXU(866),
        .KVW(32768), .SEND_HIDDEN(1), .HID_DEST(1), .FWD_TOKEN(1), .SOURCE(1), .XWORDS(41), .RXWORDS(41), .REC_SRAM(1),
        .UPOS_LWR(1), .CONTROL_PIPE(1), .CFG_Q(1), .PRECOMP(1), .IN_DEC(1), .TXQ_SLICE(1), .RDY_LT(1), .FANOUT_COPY(1),
        .MARGIN(1), .LINK_REG(1), .LINK_SEL(1), .VM_REG(1), .RD_PIPE(1), .SLEW_COPY(1), .PROMPT_EXTRA(2)) u_wfc (
        .clk(clk), .rst_n(rst[0]), .cfg_users(cfg_users), .cfg_prompt_len(cfg_plen), .cfg_gen_len(cfg_glen),
        .in_valid(w_in_valid), .in_ready(w_in_ready), .in_data(w_in_data), .in_last(w_in_last),
        .out_valid(w_out_valid), .out_ready(w_out_ready), .out_data(w_out_data), .out_last(w_out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(core_done_w), .core_next_token(cnt_tok), .core_next_val(cnt_val), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q), .pr_blk(pr_blk), .pr_qk(pr_qk),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id),
        .users_done(users_done), .proto_fault(proto_fault), .wf_issue(wf_issue), .wf_reject(wf_reject),
        .wf_squash(wf_squash));
    dsfd_wfc_lnk u_lnk (.ck(ck), .rst(rst), .f_liv(f_liv), .f_lid(f_lid), .t_lir(t_lir),
        .t_wiv(w_in_valid), .t_wid({w_in_last, w_in_data}), .f_wig(w_in_ready),
        .f_wov(w_out_valid), .f_wod({w_out_last, w_out_data}), .t_wog(w_out_ready),
        .t_lov(t_lov), .t_lod(t_lod), .f_lor(f_lor), .t_dw(dw), .f_vc(vc_ret), .t_ft(lnk_ft));
    dsfd_wfc_tok_hard u_tok (.ck(ck), .rst(rst), .f_c(f_c), .t_cfg({cfg_users, cfg_plen, cfg_glen}), .f_dw(dw),
        .f_pr({pr_re, pr_user, pr_pos, pr_blk}), .t_pr({pr_qk, pr_q}), .t_ft(tok_ft));
    dsfd_wfc_vmx #(.XWORDS(41), .RQFREE(2)) u_vmx (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq),
        .f_cs({core_start, core_user, core_token, core_pos}), .t_cd({core_done_w, cnt_tok, cnt_val}), .t_vc(vc_ret),
        .t_swv(t_swv), .t_swd(t_swd), .f_swr(f_swr), .f_swa(f_swa), .t_srv(t_srv), .t_srd(t_srd), .f_srr(f_srr),
        .f_srq(f_srq), .t_ks(t_ks), .f_kd(f_kd), .t_ft(vmx_ft));
    // committed-token egress and faults leave from flops (registered die boundary)
    reg [USER_W+2*NW:0] tok_q; reg [3:0] ft_q;
    always @(posedge clk) begin
        tok_q <= {tok_valid, tok_user, tok_pos, tok_id};
        ft_q <= {proto_fault, lnk_ft, tok_ft, vmx_ft};
    end
    assign t_tok = tok_q; assign t_ft = ft_q; assign t_cfg = {cfg_users, cfg_plen, cfg_glen};
endmodule

module dsfd_wfc_stg #(parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
                      parameter integer VWA = 15, parameter integer LAG = 0) (
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lir,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_lor,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [VWA-1:0] t_srd, input wire [0:0] f_srr, input wire [FLIT:0] f_srq,
    output wire [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    output wire [3:0] t_ft
);
    wire clk = ck[0];
    wire w_in_valid, w_in_ready, w_in_last, w_out_valid, w_out_ready, w_out_last;
    wire [FLIT-1:0] w_in_data, w_out_data;
    wire core_start, core_done_w; wire [NW-1:0] core_token, core_pos, cnt_tok; wire [31:0] cnt_val;
    wire [USER_W-1:0] core_user; wire [29:0] kv_base;
    wire vm_we, vm_re; wire [VWA-1:0] vm_waddr, vm_raddr; wire [FLIT-1:0] vm_wdata, vm_rq;
    wire pr_re; wire [USER_W-1:0] pr_user; wire [NW-1:0] pr_pos; wire [3:0] pr_blk;
    wire core_busy, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash;
    wire [USER_W-1:0] tok_user, users_done; wire [NW-1:0] tok_pos, tok_id;
    wire [FLIT:0] dw; wire vc_ret, lnk_ft, vmx_ft;
    ot_dsrom_wfc_tokpipe_stg #(.WAVE(1), .WIN(6), .FLIT(FLIT), .NW(NW), .AW(30), .VWA(VWA), .USER_W(USER_W), .MAXU(866),
        .KVW(32768), .SEND_HIDDEN(1), .HID_DEST(1), .FWD_TOKEN(1), .SOURCE(0), .XWORDS(46), .RXWORDS(41),
        .UPOS_LWR(1), .CONTROL_PIPE(1), .PRECOMP(1), .IN_DEC(1), .TXQ_SLICE(1), .RDY_LT(1), .FANOUT_COPY(1),
        .MARGIN(1), .LINK_REG(1), .LINK_SEL(1), .VM_REG(1), .SLEW_COPY(1)) u_wfc (
        .clk(clk), .rst_n(rst[0]), .cfg_users(10'd0), .cfg_prompt_len({NW{1'b0}}), .cfg_gen_len({NW{1'b0}}),
        .in_valid(w_in_valid), .in_ready(w_in_ready), .in_data(w_in_data), .in_last(w_in_last),
        .out_valid(w_out_valid), .out_ready(w_out_ready), .out_data(w_out_data), .out_last(w_out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(core_done_w), .core_next_token(cnt_tok), .core_next_val(cnt_val), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q({NW{1'b0}}), .pr_blk(pr_blk), .pr_qk(1'b0),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id),
        .users_done(users_done), .proto_fault(proto_fault), .wf_issue(wf_issue), .wf_reject(wf_reject),
        .wf_squash(wf_squash));
    dsfd_wfc_lnk u_lnk (.ck(ck), .rst(rst), .f_liv(f_liv), .f_lid(f_lid), .t_lir(t_lir),
        .t_wiv(w_in_valid), .t_wid({w_in_last, w_in_data}), .f_wig(w_in_ready),
        .f_wov(w_out_valid), .f_wod({w_out_last, w_out_data}), .t_wog(w_out_ready),
        .t_lov(t_lov), .t_lod(t_lod), .f_lor(f_lor), .t_dw(dw), .f_vc(vc_ret), .t_ft(lnk_ft));
    dsfd_wfc_vmx #(.XWORDS(46), .RQFREE(2), .LAG(LAG)) u_vmx (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq),
        .f_cs({core_start, core_user, core_token, core_pos}), .t_cd({core_done_w, cnt_tok, cnt_val}), .t_vc(vc_ret),
        .t_swv(t_swv), .t_swd(t_swd), .f_swr(f_swr), .f_swa(f_swa), .t_srv(t_srv), .t_srd(t_srd), .f_srr(f_srr),
        .f_srq(f_srq), .t_ks(t_ks), .f_kd(f_kd), .t_ft(vmx_ft));
    reg [3:0] ft_q; always @(posedge clk) ft_q <= {proto_fault, lnk_ft, 1'b0, vmx_ft};
    assign t_ft = ft_q;
endmodule
