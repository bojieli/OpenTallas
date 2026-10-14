`timescale 1ns/1ps
// r5 (2026-10-14): Qwen compute-die tile CONTROL leaf with registered admission/credit faces (default-off successor
// of ot_qwen_tile_ctl_tp8_ctx; the historical masters and every CLOSED child stand unchanged).
// Measured defects of the ctx / numeric_stream_diag leaf (CTS gate 05:18 10-14, 12,403 FF):
//   (1) query_ack_toggle -> XNOR -> cx_query_credit: combinational in->out face (the one-outstanding mailbox);
//   (2) accept_ack_toggle -> pending -> core_go -> u_me: 783 in->reg endpoints at up to 10 logic levels;
//   (3) reg->out -81.4 ps on the accepted descriptor bundle (enable flops on the go net, not at the pins).
// Structure here:
//   (1) the query identity STREAMS (XQUERY_STREAM 1): every actual issue edge exports {seq, xre, addr, epoch,
//       context, version} once, registered; there is no ACK, no toggle and no credit pin.  Capacity is owned by
//       the live-clock queue (ot_qwen_live_credit_queue) whose REGISTERED credit drives the family clock enable,
//       so a core edge never happens without a reserved slot; the queue faults on any overflow.  query_reserve is
//       therefore constant: a core-clock copy of the reservation would be stale after a stopped-clock pause.
//   (2) accept_ack_toggle and accept_transport_fence are registered at the pin on the core clock (+1 edge on the
//       ACK and the fence, together, so their order with ib_go -- itself pin-registered, IREG -- is unchanged).
//       Admission never pauses the clock (a pending ACK only withholds acceptance), so a core-clock ACK register
//       cannot deadlock: no pause-loop input is a core-clock register (proved in tb_qwen_tile_lface).
//   (3) the accepted bundle {op_accept, context, version, ib} gets one plain (no-enable) output register stage,
//       flops at the pins; lifetime qualification by op_accept is preserved because all fields shift together.
module ot_qwen_tile_ctl_tp8_lface #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    input  wire          ib_go,
    input  wire [378:0]  ib,
    input  wire [127:0]  xl,
    output wire          fault,
    output wire [3:0]    cx_xre,
    output wire [95:0]   cx_xaddr,
    output wire [20:0]   cx_xepoch,
    output wire          cx_xjrepeat,
    input  wire [15:0]   op_context,
    input  wire [31:0]   vm_version,
    output wire [15:0]   cx_xcontext,
    output wire [31:0]   cx_xversion,
    output wire [39:0]   cx_query_seq,
    output wire          cx_query_fault, cx_query_issue_v,
    input  wire          accept_ack_toggle, accept_transport_fence,
    output wire          cx_accept_toggle, cx_admission_fault,
    output wire          cx_op_accept,
    output wire          cx_issue_last,
    output wire [15:0]   cx_accepted_context,
    output wire [31:0]   cx_accepted_version,
    output wire [378:0]  cx_accepted_ib,
    output wire          cx_core_idle,
    output wire [69:0]   cx_rreq,
    input  wire [2047:0] cx_rqr,
    output wire [3127:0] cx_ld,
    input  wire [71:0]   cx_lerr,
    output wire          cx_tvd,
    input  wire          cx_nfault,
    output wire [88:0]   numeric_tuple   // streaming identity of the numeric word (TOREG edge), no mailbox
);
    // ---- input face: ACK / fence pin registers (core clock) ----
    (* keep *) reg ack_q, fence_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ack_q <= 1'b0; fence_q <= 1'b0; end
        else begin ack_q <= accept_ack_toggle; fence_q <= accept_transport_fence; end
    wire ack_i   = (MUT == 1) ? accept_ack_toggle : ack_q;
    wire fence_i = (MUT == 1) ? accept_transport_fence : fence_q;

    wire tile_fault;
    wire [583:0] cx_lq;
    genvar li;
    generate for (li = 0; li < 8; li = li + 1) begin : g_lerr
        assign cx_lq[73*li+:73] = {cx_lerr[9*li+:9], 64'd0};
    end endgenerate
    wire        op_accept_w;
    wire [15:0] actx_w;
    wire [31:0] aver_w;
    wire [378:0] aib_w;
    ot_qwen_rom_tile_logic_w12 #(.NW(18), .GT(3072), .SMIN(7), .CODE_BANKS(5), .KV_LOCAL(0), .KV_VB(131072), .KV_NH(2),
        .MEM_EXTRA(1), .ACC_LAT(7), .TREE_LAT(7), .FAST_ISSUE(1), .KV_PREP(4), .MUL_LAT(8), .ROM_PIPE(1), .ROM_ARELAY(2),
        .ROM_CAP2(1), .ROM_CAPX(2), .LRST(3), .ARPB(1), .MPR(1), .HIER(2), .HIER_HARD(1), .TOREG(1), .TIDR(1), .LRR(1),
        .RPH(2), .RQR(1), .XTX(2), .ANR(1), .BAW(12), .NDH(1), .BMUT(0), .CEXT(2), .XLOCAL(1), .XMODE_EXPORT(1),
        .XCONTEXT_EXPORT(1), .XQUERY_STREAM(1), .XADMIT(1)) u_logic (
        .clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl),
        .t_out(), .t_vout(), .n_a(512'd0), .n_b(512'd0), .n_va(1'b0), .n_y(), .n_vy(), .fault(tile_fault),
        .rom_ce(), .rom_addr(), .rom_addr_n(), .rom_addr_b(), .rom_req_m(), .rom_rd({2*5*266{1'b0}}),
        .kvs_r_ce(), .kvs_r_addr(), .kvs_rd(512'd0), .kv_re(), .kv_addr(), .kv_q({4*16*32{1'b0}}),
        .cx_xre(cx_xre), .cx_xaddr(cx_xaddr), .cx_xepoch(cx_xepoch), .cx_xjrepeat(cx_xjrepeat),
        .op_context(op_context), .vm_version(vm_version), .cx_xcontext(cx_xcontext), .cx_xversion(cx_xversion),
        .query_ack_toggle(1'b0), .query_reserve(1'b1),
        .cx_query_seq(cx_query_seq), .cx_query_toggle(), .cx_query_credit(), .cx_query_fault(cx_query_fault),
        .cx_query_issue_v(cx_query_issue_v),
        .accept_ack_toggle(ack_i), .accept_transport_fence(fence_i),
        .cx_accept_toggle(cx_accept_toggle), .cx_admission_fault(cx_admission_fault), .cx_op_accept(op_accept_w),
        .cx_issue_last(cx_issue_last), .cx_accepted_context(actx_w), .cx_accepted_version(aver_w),
        .cx_core_idle(cx_core_idle), .cx_accepted_ib(aib_w),
        .cx_rreq(cx_rreq), .cx_rq(5120'd0), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(), .cx_tvd(cx_tvd),
        .cx_nfault(cx_nfault));
    // ---- output face: accepted bundle register stage (plain flops at the pins) ----
    (* keep *) reg         op_accept_q;
    (* keep *) reg [15:0]  actx_q;
    (* keep *) reg [31:0]  aver_q;
    (* keep *) reg [378:0] aib_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) op_accept_q <= 1'b0; else op_accept_q <= op_accept_w;
    always @(posedge clk) begin actx_q <= actx_w; aver_q <= aver_w; aib_q <= aib_w; end
    assign cx_op_accept        = (MUT == 2) ? op_accept_w : op_accept_q;
    assign cx_accepted_context = actx_q;
    assign cx_accepted_version = aver_q;
    assign cx_accepted_ib      = aib_q;
    // ---- streaming numeric identity companion (registered tag on the TOREG producing edge) ----
    ot_qwen_tile_numeric_output_metadata u_metadata (.core_clk(clk), .rst_n(rst_n), .query_issue_v(cx_query_issue_v),
        .query_sequence(cx_query_seq), .query_context(cx_xcontext), .query_version(cx_xversion),
        .numeric_tuple(numeric_tuple));
    (* keep *) reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0; else fault_q <= tile_fault;
    assign fault = fault_q;
endmodule

// Bench/parent composition: the lface control + the unchanged CLOSED children (same as ..._tp8_core_ctx).
module ot_qwen_rom_tile_nkt_tp8_core_lface #(parameter integer CMUT = 0, parameter integer MUT = 0) (
    input  wire              clk_ctl,
    input  wire [4:0]        clk_rp,
    input  wire [7:0]        clk_sl,
    input  wire              clk_node,
    input  wire [7:0]        clk_tx,
    input  wire [1:0]        clk_rqr,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [378:0]      ib,
    input  wire [127:0]      x_response,
    output wire [511:0]      t_out,
    output wire              t_vout,
    input  wire [511:0]      n_a,
    input  wire [511:0]      n_b,
    input  wire              n_va,
    output wire [511:0]      n_y,
    output wire              n_vy,
    output wire              fault,
    output wire [3:0]        cx_xre,
    output wire [95:0]       cx_xaddr,
    output wire [20:0]       cx_xepoch,
    output wire              cx_xjrepeat,
    input  wire [15:0]       op_context,
    input  wire [31:0]       vm_version,
    output wire [15:0]       cx_xcontext,
    output wire [31:0]       cx_xversion,
    output wire [39:0]       cx_query_seq,
    output wire              cx_query_fault, cx_query_issue_v,
    input  wire              accept_ack_toggle, accept_transport_fence,
    output wire              cx_accept_toggle, cx_admission_fault,
    output wire              cx_op_accept, cx_issue_last,
    output wire [15:0]       cx_accepted_context,
    output wire [31:0]       cx_accepted_version,
    output wire [378:0]      cx_accepted_ib,
    output wire              cx_core_idle,
    output wire [88:0]       numeric_tuple
);
    wire [69:0]   cx_rreq;
    wire [5119:0] cx_rq;
    wire [3127:0] cx_ld;
    wire [583:0]  cx_lq;
    wire [2047:0] cx_rqr;
    wire [71:0]   cx_lerr;
    genvar li;
    generate for (li = 0; li < 8; li = li + 1) begin : g_lerr
        assign cx_lerr[9*li+:9] = cx_lq[73*li+64+:9];
    end endgenerate
    wire cx_tvd, cx_nfault;
    ot_qwen_tile_ctl_tp8_lface #(.MUT(MUT)) u_ctl (.clk(clk_ctl), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib),
        .xl(x_response), .fault(fault), .cx_xre(cx_xre), .cx_xaddr(cx_xaddr), .cx_xepoch(cx_xepoch),
        .cx_xjrepeat(cx_xjrepeat), .op_context(op_context), .vm_version(vm_version), .cx_xcontext(cx_xcontext),
        .cx_xversion(cx_xversion), .cx_query_seq(cx_query_seq), .cx_query_fault(cx_query_fault),
        .cx_query_issue_v(cx_query_issue_v), .accept_ack_toggle(accept_ack_toggle),
        .accept_transport_fence(accept_transport_fence), .cx_accept_toggle(cx_accept_toggle),
        .cx_admission_fault(cx_admission_fault), .cx_op_accept(cx_op_accept), .cx_issue_last(cx_issue_last),
        .cx_accepted_context(cx_accepted_context), .cx_accepted_version(cx_accepted_version),
        .cx_accepted_ib(cx_accepted_ib), .cx_core_idle(cx_core_idle),
        .cx_rreq(cx_rreq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lerr(cx_lerr), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault),
        .numeric_tuple(numeric_tuple));
    ot_qwen_tile_kids #(.CODE_BANKS(5), .RPS(0), .CMUT(CMUT), .MCLK(1), .SPLIT(1)) u_kids (.clk(clk_ctl), .clk_rp(clk_rp),
        .clk_sl(clk_sl), .clk_node(clk_node), .clk_tx(clk_tx), .clk_rqr(clk_rqr), .rst_n(rst_n),
        .cx_rreq(cx_rreq), .cx_rq(cx_rq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(512'd0), .cx_tvd(cx_tvd),
        .cx_nfault(cx_nfault), .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .t_out(t_out), .t_vout(t_vout),
        .rom_req_m(), .rom_rd({2*5*266{1'b0}}));
endmodule
