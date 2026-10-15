`timescale 1ns/1ps
`default_nettype none
// The two die masters of the quadrant collective engine (HBM peer-to-peer step 1, contract v14), each hardened once.
// Both are ot_hfd_coll_q; they differ only in what the die must bind, so that no die port of either is tied off:
//   ot_hfd_coll_q3  SW quadrant, links S0-S2 (NPT 3).  HOME (the only engine that answers the command processor: hgi_ret)
//                   and QSOLO (ARGMAX_MERGE / TOPK_MERGE / ROW_GATHER run whole here): carries the TOPK record extension
//                   hgi_recx, the RGX memory lanes (ROW_GATHER writes by credit flow to ot_hgi_coll_rgx_snkm, a master
//                   beside the SW slice) and, with TKM = 1 (the die value), the TOPK_MERGE merge sink with its
//                   32-tile systolic array as a child cluster (KMAX 2,048 is exact only as ONE array: the four quadrants
//                   cannot each own 8 tiles, see el1014-hbm-p2p-coll.log 07:50).  The quadrant strap is fixed at 0.
//   ot_hfd_coll_q2  SE (S3-S4), NW (N0-N1), NE (N2-N3) quadrants, NPT 2, strap qid 1 / 2 / 3 (a die strap like the TKM
//                   tile's tid).  Never HOME, never QSOLO: no hgi_ret, no hgi_recx, no RGX lanes, no TOPK sink.
module ot_hfd_coll_q3 #(
    parameter integer TKM_NATIVE = 1,
    parameter integer PR_SPLIT_CLOCKS = 0,
    parameter integer INJLAT = 12,
    parameter integer TKM = 1,
    parameter integer TKM_KMAX = 2048,
    parameter integer MUT_Q = 0, parameter integer MUT_CARRY = 0, parameter integer MUT_ORDER = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        pr_clk_state,
    input  wire [7:0]        pr_clk_add,
    input wire tkm_clk_core, tkm_clk_buffer, tkm_clk_packer,
    input wire [3:0] tkm_clk_lane,
    input wire [31:0] tkm_clk_tile,
    input  wire [967:0]      hgi_rec,
    input  wire [553:0]      hgi_recx,
    output wire [2:0]        hgi_ret,
    input  wire [39:0]       hgi_cfg,
    output wire [79:0]       hgi_vmaddr,
    output wire [159:0]      hgi_inj_addr,
    output wire [31:0]       inj_idx,
    output wire [1:0]        inj_rd,
    input  wire [1023:0]     inj_d,
    output wire [3:0]        del_valid,
    output wire [4*545-1:0]  del_flit,
    output wire [159:0]      hgi_del_obase,
    output wire              fault,
    output wire [31:0]       stat_credit_stall,
    output wire [2:0]        lk_tx_v,
    output wire [3*545-1:0]  lk_tx_flit,
    output wire [2:0]        lk_rx_credit,
    input  wire [2:0]        lk_rx_v,
    input  wire [3*545-1:0]  lk_rx_flit,
    input  wire [2:0]        lk_sw_cr,
    output wire [3*24-1:0]   lk_session,
    input  wire [2:0]        lk_fault,
    input  wire [2:0]        lk_locked,
    output wire [5:0]        lk_status,
    input  wire [279:0]      pr_cw_i,
    output wire [279:0]      pr_cw_o,
    input  wire [279:0]      pr_ccw_i,
    output wire [279:0]      pr_ccw_o,
    input  wire              rc_v,
    output wire              rc_rdy,
    input  wire [2:0]        rc_tag,
    input  wire              rc_mode,
    input  wire [255:0]      rc_d,
    output wire              rr_v,
    output wire [2:0]        rr_tag,
    output wire [255:0]      rr_d,
    output wire              tkw_t_v,       // TOPK line writes -> ot_hgi_coll_vmport (credit flow)
    output wire [567:0]      tkw_t_d,
    input  wire              tkw_f_cr,
    output wire [75:0]       rgx_xq,
    input  wire [513:0]      rgx_xr,
    output wire [337:0]      rgx_vmq,
    input  wire [273:0]      rgx_vmr,
    output wire [3:0]        rgx_t_v,       // ROW_GATHER writes -> ot_hgi_coll_rgx_snkm beside the SW slice
    output wire [159:0]      rgx_t_addr,
    output wire [2047:0]     rgx_t_data,
    output wire              rgx_t_vm,
    input  wire [3:0]        rgx_f_cr,
    input  wire              rgx_f_fault
);
    ot_hfd_coll_q #(.TKM_NATIVE(TKM_NATIVE), .PR_SPLIT_CLOCKS(PR_SPLIT_CLOCKS), .INJLAT(INJLAT), .NPT(3), .HOME(0), .QSOLO(0), .SOLO_CAP(1), .TKM(TKM), .TKM_KMAX(TKM_KMAX),
                    .MUT_Q(MUT_Q), .MUT_CARRY(MUT_CARRY), .MUT_ORDER(MUT_ORDER)) u_q (
        .clk(clk), .rst_n(rst_n), .pr_clk_state(pr_clk_state), .pr_clk_add(pr_clk_add), .tkm_clk_core(tkm_clk_core), .tkm_clk_buffer(tkm_clk_buffer), .tkm_clk_packer(tkm_clk_packer), .tkm_clk_lane(tkm_clk_lane), .tkm_clk_tile(tkm_clk_tile), .qid(2'd0),
        .hgi_rec(hgi_rec), .hgi_recx(hgi_recx), .hgi_ret(hgi_ret), .hgi_cfg(hgi_cfg), .hgi_vmaddr(hgi_vmaddr),
        .hgi_inj_addr(hgi_inj_addr), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_d(inj_d), .del_valid(del_valid),
        .del_flit(del_flit), .hgi_del_obase(hgi_del_obase), .fault(fault), .stat_credit_stall(stat_credit_stall),
        .lk_tx_v(lk_tx_v), .lk_tx_flit(lk_tx_flit), .lk_rx_credit(lk_rx_credit), .lk_rx_v(lk_rx_v), .lk_rx_flit(lk_rx_flit),
        .lk_sw_cr(lk_sw_cr), .lk_session(lk_session), .lk_fault(lk_fault), .lk_locked(lk_locked), .lk_status(lk_status),
        .pr_cw_i(pr_cw_i), .pr_cw_o(pr_cw_o), .pr_ccw_i(pr_ccw_i), .pr_ccw_o(pr_ccw_o),
        .rc_v(rc_v), .rc_rdy(rc_rdy), .rc_tag(rc_tag), .rc_mode(rc_mode), .rc_d(rc_d), .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d),
        .tkw_t_v(tkw_t_v), .tkw_t_d(tkw_t_d), .tkw_f_cr(tkw_f_cr),
        .rgx_xq(rgx_xq), .rgx_xr(rgx_xr), .rgx_vmq(rgx_vmq), .rgx_vmr(rgx_vmr), .rgx_t_v(rgx_t_v), .rgx_t_addr(rgx_t_addr),
        .rgx_t_data(rgx_t_data), .rgx_t_vm(rgx_t_vm), .rgx_f_cr(rgx_f_cr), .rgx_f_fault(rgx_f_fault));
endmodule

module ot_hfd_coll_q2 #(
    parameter integer PR_SPLIT_CLOCKS = 0,
    parameter integer INJLAT = 12,
    parameter integer MUT_Q = 0, parameter integer MUT_CARRY = 0, parameter integer MUT_ORDER = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        pr_clk_state,
    input  wire [7:0]        pr_clk_add,
    input  wire [1:0]        qid,           // die strap: 1 SE, 2 NW, 3 NE
    input  wire [967:0]      hgi_rec,
    input  wire [39:0]       hgi_cfg,
    output wire [79:0]       hgi_vmaddr,
    output wire [159:0]      hgi_inj_addr,
    output wire [31:0]       inj_idx,
    output wire [1:0]        inj_rd,
    input  wire [1023:0]     inj_d,
    output wire [3:0]        del_valid,
    output wire [4*545-1:0]  del_flit,
    output wire [159:0]      hgi_del_obase,
    output wire              fault,
    output wire [31:0]       stat_credit_stall,
    output wire [1:0]        lk_tx_v,
    output wire [2*545-1:0]  lk_tx_flit,
    output wire [1:0]        lk_rx_credit,
    input  wire [1:0]        lk_rx_v,
    input  wire [2*545-1:0]  lk_rx_flit,
    input  wire [1:0]        lk_sw_cr,
    output wire [2*24-1:0]   lk_session,
    input  wire [1:0]        lk_fault,
    input  wire [1:0]        lk_locked,
    output wire [3:0]        lk_status,
    input  wire [279:0]      pr_cw_i,
    output wire [279:0]      pr_cw_o,
    input  wire [279:0]      pr_ccw_i,
    output wire [279:0]      pr_ccw_o,
    input  wire              rc_v,
    output wire              rc_rdy,
    input  wire [2:0]        rc_tag,
    input  wire              rc_mode,
    input  wire [255:0]      rc_d,
    output wire              rr_v,
    output wire [2:0]        rr_tag,
    output wire [255:0]      rr_d
);
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && qid == 2'd0) $fatal(1, "ot_hfd_coll_q2: strap qid 0 is the SW master ot_hfd_coll_q3");
`endif
    ot_hfd_coll_q #(.PR_SPLIT_CLOCKS(PR_SPLIT_CLOCKS), .INJLAT(INJLAT), .NPT(2), .HOME(0), .QSOLO(0), .SOLO_CAP(0), .TKM(0),
                    .MUT_Q(MUT_Q), .MUT_CARRY(MUT_CARRY), .MUT_ORDER(MUT_ORDER)) u_q (
        .clk(clk), .rst_n(rst_n), .pr_clk_state(pr_clk_state), .pr_clk_add(pr_clk_add), .tkm_clk_core(clk), .tkm_clk_buffer(clk), .tkm_clk_packer(clk), .tkm_clk_lane({4{clk}}), .tkm_clk_tile({32{clk}}), .qid(qid),
        .hgi_rec(hgi_rec), .hgi_recx(554'd0), .hgi_ret(), .hgi_cfg(hgi_cfg), .hgi_vmaddr(hgi_vmaddr),
        .hgi_inj_addr(hgi_inj_addr), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_d(inj_d), .del_valid(del_valid),
        .del_flit(del_flit), .hgi_del_obase(hgi_del_obase), .fault(fault), .stat_credit_stall(stat_credit_stall),
        .lk_tx_v(lk_tx_v), .lk_tx_flit(lk_tx_flit), .lk_rx_credit(lk_rx_credit), .lk_rx_v(lk_rx_v), .lk_rx_flit(lk_rx_flit),
        .lk_sw_cr(lk_sw_cr), .lk_session(lk_session), .lk_fault(lk_fault), .lk_locked(lk_locked), .lk_status(lk_status),
        .pr_cw_i(pr_cw_i), .pr_cw_o(pr_cw_o), .pr_ccw_i(pr_ccw_i), .pr_ccw_o(pr_ccw_o),
        .rc_v(rc_v), .rc_rdy(rc_rdy), .rc_tag(rc_tag), .rc_mode(rc_mode), .rc_d(rc_d), .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d),
        .tkw_t_v(), .tkw_t_d(), .tkw_f_cr(1'b0),
        .rgx_xq(), .rgx_xr(514'd0), .rgx_vmq(), .rgx_vmr(274'd0), .rgx_t_v(), .rgx_t_addr(), .rgx_t_data(), .rgx_t_vm(),
        .rgx_f_cr(4'd0), .rgx_f_fault(1'b0));
endmodule
`default_nettype wire
