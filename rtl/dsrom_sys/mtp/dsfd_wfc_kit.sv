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
                      parameter integer VWA = 15, parameter bit VM_LINK = 0,
                      parameter integer WOUTW = 5, parameter integer VMRQ = 16,
                      parameter integer POSTED = 0, parameter integer RD2 = 0,
                      parameter bit HEP = 0,
                      parameter bit TOKIN = 0) (   // 1: link-in from the collective MTP lane token return (f_mrt / t_mrg)
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lir,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_lor,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [(RD2 ? 2*VWA+1 : VWA)-1:0] t_srd, input wire [0:0] f_srr,
    input wire [(RD2 ? 2*FLIT+2 : FLIT+1)-1:0] f_srq,
    output wire [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    output wire [USER_W+NW+4:0] t_hep,                       // HEP: {v, user, pos, issue epoch} per stage start (0 if HEP 0)
    input  wire [2+USER_W+2*NW:0] f_c,
    input  wire [FLIT:0] f_mrt, output wire [0:0] t_mrg,      // TOKIN: {data, valid} from dsfd_sp_collective t_mrt
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
    wire x_swv, x_swr, x_srv, x_srr; wire [VWA+FLIT-1:0] x_swd; wire [(RD2 ? 2*VWA+1 : VWA)-1:0] x_srd;
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
    // TOKIN (mtp-wfc 2026-10-10): the S0 die's collective MTP lane hands the head sequencer's token-return flits
    // (single-flit messages, last = 1) in the grant protocol; the lnk's grant receiver takes them unchanged
    wire li_v = TOKIN ? f_mrt[0] : f_liv[0]; wire [FLIT:0] li_d = TOKIN ? {1'b1, f_mrt[FLIT:1]} : f_lid; wire li_g;
    assign t_lir = TOKIN ? 1'b0 : li_g; assign t_mrg = TOKIN ? li_g : 1'b0;
    dsfd_wfc_lnk u_lnk (.ck(ck), .rst(rst), .f_liv(li_v), .f_lid(li_d), .t_lir(li_g),
        .t_wiv(w_in_valid), .t_wid({w_in_last, w_in_data}), .f_wig(w_in_ready),
        .f_wov(w_out_valid), .f_wod({w_out_last, w_out_data}), .t_wog(w_out_ready),
        .t_lov(t_lov), .t_lod(t_lod), .f_lor(f_lor), .t_dw(dw), .f_vc(vc_ret), .t_ft(lnk_ft));
    dsfd_wfc_tok_hard u_tok (.ck(ck), .rst(rst), .f_c(f_c), .t_cfg({cfg_users, cfg_plen, cfg_glen}), .f_dw(dw),
        .f_pr({pr_re, pr_user, pr_pos, pr_blk}), .t_pr({pr_qk, pr_q}), .t_ft(tok_ft));
    dsfd_wfc_vmx #(.XWORDS(41), .RQFREE(2), .WOUTW(WOUTW), .RQ(VMRQ), .POSTED(POSTED), .RD2(RD2)) u_vmx (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq),
        .f_cs({core_start, core_user, core_token, core_pos}), .t_cd({core_done_w, cnt_tok, cnt_val}), .t_vc(vc_ret),
        .t_swv(x_swv), .t_swd(x_swd), .f_swr(x_swr), .f_swa(f_swa), .t_srv(x_srv), .t_srd(x_srd), .f_srr(x_srr),
        .f_srq(f_srq), .t_ks(t_ks), .f_kd(f_kd), .t_ft(vmx_ft));
    // VM request channels (serial domain).  VM_LINK 0: the vmx skids' valid / ready straight to the die (exact only
    // with the VM abutting).  VM_LINK 1 (mtp-wfc 2026-10-10, lat-audit "WFC VM read over 13/13 hub stages + CDC"):
    // the registered grant protocol of the closed link pair (ot_dsrom_mtp_ltx here; the VM side receives with an
    // ot_dsrom_mtp_lrx_rtt sized for the hub relay round trip), so a request is launched only against a grant and
    // no relay station can drop one.  The read response f_srq and the write ACK f_swa are push-only and already
    // safe: the vmx issues a read only with response-queue space (rq_n + r_out < RQ).
    generate if (VM_LINK) begin : g_vm_link
        ot_dsrom_mtp_ltx #(.W(VWA + FLIT)) u_swl (.clk(ckv[0]), .rst_n(rsv[0]), .c_valid(x_swv), .c_ready(x_swr),
            .c_data(x_swd), .l_valid(t_swv[0]), .l_ready(f_swr[0]), .l_data(t_swd));
        ot_dsrom_mtp_ltx #(.W(RD2 ? 2*VWA+1 : VWA)) u_srl (.clk(ckv[0]), .rst_n(rsv[0]), .c_valid(x_srv), .c_ready(x_srr),
            .c_data(x_srd), .l_valid(t_srv[0]), .l_ready(f_srr[0]), .l_data(t_srd));
    end else begin : g_vm_direct
        assign t_swv = x_swv; assign t_swd = x_swd; assign x_swr = f_swr;
        assign t_srv = x_srv; assign t_srd = x_srd; assign x_srr = f_srr;
    end endgenerate
    // committed-token egress and faults leave from flops (registered die boundary)
    reg [USER_W+2*NW:0] tok_q; reg [3:0] ft_q;
    always @(posedge clk) begin
        tok_q <= {tok_valid, tok_user, tok_pos, tok_id};
        ft_q <= {proto_fault, lnk_ft, tok_ft, vmx_ft};
    end
    assign t_tok = tok_q; assign t_ft = ft_q; assign t_cfg = {cfg_users, cfg_plen, cfg_glen};
    generate if (HEP) begin : g_hep
        // el1011-ds-mtp 2026-10-11 (wave bench finding): under POSTED the vmx never pulses k_start -- the VM endpoint
        // starts the core from the START doorbell, a write to VM address all-ones carrying {user, token, pos} -- so
        // t_ks is dead and HEP saw no stage start.  The doorbell's accepted write (vmx side, issue order, ckv domain)
        // is the stage start HEP counts; non-posted kits keep t_ks.
        wire [USER_W+2*NW:0] hks;
        if (POSTED) begin : g_post
            assign hks = {x_swv && x_swr && (&x_swd[FLIT +: VWA]), x_swd[USER_W+2*NW-1:0]};
        end else begin : g_ks
            assign hks = t_ks;
        end
        dsfd_wfc_hep #(.NW(NW), .USER_W(USER_W)) u_hep (.clk(ckv[0]), .rst_n(rsv[0]), .ks(hks), .hep(t_hep));
    end else begin : g_nohep
        assign t_hep = '0;
    end endgenerate
endmodule

module dsfd_wfc_stg #(parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
                      parameter integer VWA = 15, parameter integer LAG = 0, parameter bit VM_LINK = 0,
                      parameter integer WOUTW = 5, parameter integer VMRQ = 16,
                      parameter integer POSTED = 0, parameter integer RD2 = 0,
                      parameter bit HEP = 0) (
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lir,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_lor,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [(RD2 ? 2*VWA+1 : VWA)-1:0] t_srd, input wire [0:0] f_srr,
    input wire [(RD2 ? 2*FLIT+2 : FLIT+1)-1:0] f_srq,
    output wire [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    output wire [USER_W+NW+4:0] t_hep,                       // HEP: {v, user, pos, issue epoch} per stage start (0 if HEP 0)
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
    wire x_swv, x_swr, x_srv, x_srr; wire [VWA+FLIT-1:0] x_swd; wire [(RD2 ? 2*VWA+1 : VWA)-1:0] x_srd;
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
    dsfd_wfc_vmx #(.XWORDS(46), .RQFREE(2), .LAG(LAG), .WOUTW(WOUTW), .RQ(VMRQ), .POSTED(POSTED), .RD2(RD2)) u_vmx (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_vw({vm_we, vm_waddr, vm_wdata}), .f_vr({vm_re, vm_raddr}), .t_vq(vm_rq),
        .f_cs({core_start, core_user, core_token, core_pos}), .t_cd({core_done_w, cnt_tok, cnt_val}), .t_vc(vc_ret),
        .t_swv(x_swv), .t_swd(x_swd), .f_swr(x_swr), .f_swa(f_swa), .t_srv(x_srv), .t_srd(x_srd), .f_srr(x_srr),
        .f_srq(f_srq), .t_ks(t_ks), .f_kd(f_kd), .t_ft(vmx_ft));
    // VM request channels (serial domain).  VM_LINK 0: the vmx skids' valid / ready straight to the die (exact only
    // with the VM abutting).  VM_LINK 1 (mtp-wfc 2026-10-10, lat-audit "WFC VM read over 13/13 hub stages + CDC"):
    // the registered grant protocol of the closed link pair (ot_dsrom_mtp_ltx here; the VM side receives with an
    // ot_dsrom_mtp_lrx_rtt sized for the hub relay round trip), so a request is launched only against a grant and
    // no relay station can drop one.  The read response f_srq and the write ACK f_swa are push-only and already
    // safe: the vmx issues a read only with response-queue space (rq_n + r_out < RQ).
    generate if (VM_LINK) begin : g_vm_link
        ot_dsrom_mtp_ltx #(.W(VWA + FLIT)) u_swl (.clk(ckv[0]), .rst_n(rsv[0]), .c_valid(x_swv), .c_ready(x_swr),
            .c_data(x_swd), .l_valid(t_swv[0]), .l_ready(f_swr[0]), .l_data(t_swd));
        ot_dsrom_mtp_ltx #(.W(RD2 ? 2*VWA+1 : VWA)) u_srl (.clk(ckv[0]), .rst_n(rsv[0]), .c_valid(x_srv), .c_ready(x_srr),
            .c_data(x_srd), .l_valid(t_srv[0]), .l_ready(f_srr[0]), .l_data(t_srd));
    end else begin : g_vm_direct
        assign t_swv = x_swv; assign t_swd = x_swd; assign x_swr = f_swr;
        assign t_srv = x_srv; assign t_srd = x_srd; assign x_srr = f_srr;
    end endgenerate
    reg [3:0] ft_q; always @(posedge clk) ft_q <= {proto_fault, lnk_ft, 1'b0, vmx_ft};
    assign t_ft = ft_q;
    generate if (HEP) begin : g_hep
        // el1011-ds-mtp 2026-10-11 (wave bench finding): under POSTED the vmx never pulses k_start -- the VM endpoint
        // starts the core from the START doorbell, a write to VM address all-ones carrying {user, token, pos} -- so
        // t_ks is dead and HEP saw no stage start.  The doorbell's accepted write (vmx side, issue order, ckv domain)
        // is the stage start HEP counts; non-posted kits keep t_ks.
        wire [USER_W+2*NW:0] hks;
        if (POSTED) begin : g_post
            assign hks = {x_swv && x_swr && (&x_swd[FLIT +: VWA]), x_swd[USER_W+2*NW-1:0]};
        end else begin : g_ks
            assign hks = t_ks;
        end
        dsfd_wfc_hep #(.NW(NW), .USER_W(USER_W)) u_hep (.clk(ckv[0]), .rst_n(rsv[0]), .ks(hks), .hep(t_hep));
    end else begin : g_nohep
        assign t_hep = '0;
    end endgenerate
endmodule

// dsfd_wfc_hep (mtp-wfc 2026-10-11; DSpark hrow 624e71528): the ISSUE EPOCH of every stage start, for the hidden-row
// senders ot_dsrom_mtp_hrow_tx on the layer 37 / 38 / 39 stage dies (rows versioned {user, pos, issue epoch}).
// Definition (= ot_dsrom_mtp_seq's epoch: +1 on every rejection): every stage sees one user's positions in issue order;
// a rejection squashes and re-issues from b + a + 1 <= the last issued position, so a start whose position is <= the
// user's last started position opens the user's next epoch.  Output {v, user, pos, epoch} from a flop, one per start.
module dsfd_wfc_hep #(parameter integer NW = 21, parameter integer USER_W = 10, parameter integer EW = 4) (
    input  wire clk, rst_n,
    input  wire [USER_W+2*NW:0] ks,          // the kit's stage start {start, user, token, pos}
    output wire [USER_W+NW+EW:0] hep         // {v, user, pos, epoch}, FOUR edges after the start (was one)
);
    // el1013-s81-wfcstg 2026-10-13: the 2^USER_W x (NW + EW + 1) flop table (26.6k flops; as two 13.3k-flop banks the
    // pre-route gate refused it: 72k cells, util 70 %, the user pin on 12,661 loads, CTS failed) is the die tile
    // dsfd_wfc_hep_t below: one 1R1W SRAM macro + pin flops.  The start is registered once before the tile -- in the
    // sp_wfc cluster that register is leaf dsfd_wfc_vmx_w's t_hks output (register -> wire -> register at the tile
    // pin) -- so the kit and the cluster are the same function cycle for cycle: t_hep moves +3 serial cycles against
    // the flop table.  The consumer dsfd_mtp_hrow_src only queues the event (valid-driven FIFO, the VM row read waits
    // for the row's completion), so a constant delay changes nothing there (benches hep_* / posthep_* / prc_*).
    reg [USER_W+NW:0] hq;
    always @(posedge clk) hq <= {ks[USER_W+2*NW], ks[2*NW +: USER_W], ks[NW-1:0]};
    dsfd_wfc_hep_t #(.NW(NW), .USER_W(USER_W), .EW(EW)) u_t (.ckv(clk), .rsv(rst_n), .f_hks(hq), .t_hep(hep));
endmodule

// dsfd_wfc_hep_t: the issue-epoch table as a die tile (ckv domain).  State per user {last pos NW, epoch EW} in ONE
// ot_sram_1r1w_512x64_m4_r2c2 (physical/s81_ph_views/mtp/macros, tools/s81_ph/wfc_macros.py: 96.6 x 29.7 um; the catalog's
// 512 x 128 is 174 um wide and half unused; two users a word: user[8:0] = address, user[9] = the 32-bit half, masked write) and a
// seen bit per user in flops (the reset state; the array powers up random and is never read as valid before its
// user's first start).  Pipeline, every port a register or the macro's own pin register:
//   edge 1  pins {start, user, pos} -> pin flops s1 and, in parallel, the macro's read address / enable
//   edge 2  rd_out (the user's half) -> register rw; s1 -> s2      (nothing but a 2:1 mux after the 420 ps macro access:
//           the first gate run, compare straight after rd_out, read macro -> macro -197 ps before routing)
//   edge 3  rw, or the result of the previous / second-previous start when it was the same user (their writes land
//           on edge 3 of their own pipeline, i.e. after or on this start's read edge: read-before-write) -> compare /
//           +1 -> output register t_hep and the masked write of {pos, epoch}; seen[user] <= 1
// A user's first start reports epoch 0 (the value stored for it).
// Mutants: OT_WFCHEP_MUT_STALE (the epoch never advances), OT_WFCHEP_MUT_NOFWD (no forwarding from the previous start),
//          OT_WFCHEP_MUT_NOFWD2 (no forwarding from the second-previous start).
module dsfd_wfc_hep_t #(parameter integer NW = 21, parameter integer USER_W = 10, parameter integer EW = 4) (
    input  wire [0:0] ckv, rsv,
    input  wire [USER_W+NW:0] f_hks,         // {start, user, pos}, from a flop
    output wire [USER_W+NW+EW:0] t_hep       // {v, user, pos, epoch}, from a flop; 0 unless a start arrived 3 edges ago
);
    localparam integer HW = 32;              // one user's field in the 128-bit word
    initial if (USER_W != 10 || NW + EW > HW) $fatal(1, "dsfd_wfc_hep_t: the 512 x 64 macro holds 1,024 users x <= 32 b");
    wire clk = ckv[0];
    wire f_st = f_hks[USER_W+NW]; wire [USER_W-1:0] f_u = f_hks[NW +: USER_W]; wire [NW-1:0] f_p = f_hks[NW-1:0];
    // reset: a pin flop, then one kept copy per quarter of the seen bits (the raw pin drove 1,057 loads in the gate);
    // the tile leaves reset 2 edges after the pin, long before a stage start can arrive
    localparam integer NR = 4, QS = (1 << USER_W) / NR;
    // A single two-stage serial-domain release synchronizer precedes all reset
    // fanout copies, so quarter banks never sample raw reset independently.
    (* async_reg = "true" *) reg [1:0] hep_rst_sync;
    always @(posedge clk or negedge rsv[0])
        if (!rsv[0]) hep_rst_sync <= 2'b00;
        else hep_rst_sync <= {hep_rst_sync[0], 1'b1};
    reg r0; (* keep *) reg [NR-1:0] rr; (* keep *) reg rc;
    always @(posedge clk) begin r0 <= hep_rst_sync[1]; rr <= {NR{r0}}; rc <= r0; end
    reg s1_st, s2_st; reg [USER_W-1:0] s1_u, s2_u; reg [NW-1:0] s1_p, s2_p;       // s1: pin flops
    wire [2*HW-1:0] rq;
    reg [NW+EW-1:0] rw;
    always @(posedge clk) begin
        s1_st <= f_st && rc; s1_u <= f_u; s1_p <= f_p;
        s2_st <= s1_st && rc; s2_u <= s1_u; s2_p <= s1_p;
        rw <= s1_u[USER_W-1] ? rq[HW +: NW+EW] : rq[0 +: NW+EW];
    end
    reg [(1<<USER_W)-1:0] seen;
    reg [USER_W+NW+EW:0] o, o2;                                             // output register and its delay: the forwarding sources
`ifdef OT_WFCHEP_MUT_NOFWD
    wire fwd = 1'b0;                                       // MUTANT: a back-to-back start reads the stale word
`else
    wire fwd = o[USER_W+NW+EW] && o[NW+EW +: USER_W] == s2_u;
`endif
`ifdef OT_WFCHEP_MUT_NOFWD2
    wire fwd2 = 1'b0;                                      // MUTANT: a start two cycles behind reads the stale word
`else
    wire fwd2 = o2[USER_W+NW+EW] && o2[NW+EW +: USER_W] == s2_u;
`endif
    wire [NW-1:0] last = fwd ? o[EW +: NW] : fwd2 ? o2[EW +: NW] : rw[EW +: NW];
    wire [EW-1:0] ep = fwd ? o[EW-1:0] : fwd2 ? o2[EW-1:0] : rw[EW-1:0];
    wire sn = seen[s2_u];
`ifdef OT_WFCHEP_MUT_STALE
    wire rew = 1'b0;                                       // MUTANT: the epoch never advances (stale rows served)
`else
    wire rew = sn && s2_p <= last;
`endif
    wire [EW-1:0] e_n = !sn ? {EW{1'b0}} : rew ? ep + 1'b1 : ep;
    always @(posedge clk) begin
        o <= (rc && s2_st) ? {1'b1, s2_u, s2_p, e_n} : '0;
        o2 <= rc ? o : '0;
    end
    integer qi;
    always @(posedge clk) begin
        if (s2_st) seen[s2_u] <= 1'b1;
        for (qi = 0; qi < NR; qi = qi + 1) if (!rr[qi]) seen[qi*QS +: QS] <= {QS{1'b0}};
    end
    wire [HW-1:0] wh = HW'({s2_p, e_n});
    ot_sram_1r1w_512x64_m4_r2c2 u_m (.clk(clk), .r_ce_in(f_st), .r_addr_in(f_u[8:0]), .rd_out(rq),
        .w_ce_in(s2_st), .w_addr_in(s2_u[8:0]), .wd_in({wh, wh}),
        .w_mask_in({{HW{s2_u[USER_W-1]}}, {HW{!s2_u[USER_W-1]}}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(12'd0));
    assign t_hep = o;
endmodule

// reference model of dsfd_wfc_hep_t (the flop-table module, bench only; never instantiated on a die).  A user's first
// start reports epoch 0 (el1013: it read the never-written ep[u] before, an X in simulation; 0 is what it stored).
module dsfd_wfc_hep_flat #(parameter integer NW = 21, parameter integer USER_W = 10, parameter integer EW = 4) (
    input  wire clk, rst_n,
    input  wire [USER_W+2*NW:0] ks,          // the kit's stage start {start, user, token, pos}
    output reg  [USER_W+NW+EW:0] hep         // {v, user, pos, epoch}
);
    localparam integer NU = 1 << USER_W;
    reg [NW-1:0] last [0:NU-1]; reg [EW-1:0] ep [0:NU-1]; reg [NU-1:0] seen;
    wire st = ks[USER_W+2*NW]; wire [USER_W-1:0] u = ks[2*NW +: USER_W]; wire [NW-1:0] p = ks[NW-1:0];
    wire rew = seen[u] && p <= last[u];
    wire [EW-1:0] e_n = !seen[u] ? {EW{1'b0}} : rew ? ep[u] + 1'b1 : ep[u];
    always @(posedge clk) begin
        if (!rst_n) begin seen <= '0; hep <= '0; end
        else begin
            hep <= st ? {1'b1, u, p, e_n} : '0;
            if (st) begin last[u] <= p; ep[u] <= seen[u] ? e_n : '0; seen[u] <= 1'b1; end
        end
    end
endmodule
