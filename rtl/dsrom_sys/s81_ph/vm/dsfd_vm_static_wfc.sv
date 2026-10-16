`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_wfc (claude S81 VM owner r9, 2026-10-14): the STATIC VM end of the WFC stage kit's VM channels
// (die master dsfd_wfc_stg = dsfd_wfc_stg_cl: t_swv/t_swd, t_srv/t_srd out, f_swr, f_srr, f_swa, f_srq in).
// Successor of dsfd_vm_wfc_ep (RTT grant receivers lrx_rtt + one in-order op pipe): the static VM takes EVERY kit
// request the serial cycle it arrives (one write and one read pair a serial cycle, never stalled), so the grants are
// constant-high levels from flops and no receiver queue exists (owner rule 2026-10-14T18:59).
// Die ports (serial domain, directions the VM's; S-BIND packing):
//   f_wfc 560 = {f_srd 31 {v1, row1 15, row0 15}, f_srv, f_swd 527 {addr 15, data 512}, f_swv}   (lsb f_swv)
//   t_wfc 1029 = {t_err, t_srq 1026 {rv1, rq1 512, rv, rq 512}, t_srg, t_swg}                    (lsb t_swg)
// Function (stream domain after the fixed 3:4 transfer ot_s81_vm_x34 W 560):
//   write  addr 0 .. 16383 -> VM write source 52 {row addr[13:0], mask ffff, data}; addr 15'h7fff = the kit's START
//          doorbell (POSTED kit: its own t_ks carries START to the capture; the doorbell is not a VM op and is
//          ordered after every earlier write of the channel by construction: one request a serial cycle, in order,
//          each written at a fixed edge); any other addr >= 16384 -> t_err (sticky), nothing written.
//   read   row0 (and row1 when v1) -> aux read ports 8 + row[1:0] (FSR lane rule; a pair on one lane = fault);
//          the returned rows leave on t_srq at ONE fixed latency (the core's L 12 + this block's two registers +
//          the transfers): request at serial edge k of epoch n -> t_srq registered at serial edge k of epoch n + 5.
//          Reads and writes of one serial cycle: the read sees the VM before that write (separate fixed paths; the
//          kit never reads a row it writes in the same cycle: its prefetch runs after k_done).
//   t_swg / t_srg  = serial live (constant high after reset: every request is accepted, never a back-pressure level)
//   t_err          = sticky: write/read range error, read lane collision, return-slot mismatch, x34/x43 assertion,
//                    or the VM's own fault level (POSTED kit: checked at the transaction end, as the legacy t_err).
// Phase bookkeeping: x34 presents requests at stream sample indices 2 / 3 / 0; the fixed 15-edge stream path
// (decode 1 + core 13 + return 1) lands every response on sample index 2 / 3 / 0 of ot_s81_vm_x43 (never 1).
// Mutant OT_VM_WFC_MUT_PAIR: row1's response is returned in the rq slot (pair swapped): must FAIL.
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_wfc_ctl (S-VM 2026-10-15): the WFC endpoint's control flops as ONE hard leaf with its two die clock
// categories (ck_wfc_control_t = stream decode/return, ck_wfc_control_s = serial grant/t_err), so the parent
// dsfd_vm_static_wfc is wires only (x34 + ctl + x43).  Logic and edges identical to the r9 parent body, except:
//  * fault is registered here (+1 stream edge on this sticky diagnostic level; no input->output combinational pin);
//  * the x43 send valid {r_q[512] | r_q[1025]} is a flop (r_qv, same edge as r_q) instead of a parent OR.
module dsfd_vm_static_wfc_ctl #(parameter integer RLAT = 13, parameter integer RESPONSE_PAD = 0) (
    input wire ck_control_s, ck_control_t, rst_control_s, rss_control_t,
    input wire xv, input wire [559:0] xd, input wire x34f, input wire x43f,
    output reg           w_v, output reg [13:0] w_row, output reg [511:0] w_d,
    output reg  [3:0]    a_v, output reg [55:0] a_row,
    input  wire [3:0]    e_v, input wire [2047:0] e_d,
    input  wire          vm_fault,
    output wire          s_v, output wire [1025:0] s_d,
    output reg           g_q, e_q,
    output reg           fault
);
    reg [1:0] tq;
    always @(posedge ck_control_t or negedge rss_control_t) if (!rss_control_t) tq <= 2'b00; else tq <= {tq[0], 1'b1};
    wire tn = tq[1];
    wire        q_wv  = xv && xd[0];
    wire [14:0] q_wa  = xd[527:513];
    wire [511:0] q_wd = xd[512:1];
    wire        q_rv  = xv && xd[528];
    wire [14:0] q_r0  = xd[529 +: 15];
    wire [14:0] q_r1  = xd[544 +: 15];
    wire        q_v1  = xd[559];
    reg err;
    reg [RLAT:0] dv0, dv1; reg [1:0] dl0 [0:RLAT]; reg [1:0] dl1 [0:RLAT];
    always @(posedge ck_control_t) begin : p_dec integer k; reg r0ok, r1ok;
        if (!tn) begin w_v <= 1'b0; a_v <= 4'd0; err <= 1'b0; dv0 <= '0; dv1 <= '0; end
        else begin
            w_v <= q_wv && q_wa < 15'd16384;
            if (q_wv && q_wa >= 15'd16384 && q_wa != 15'h7fff) err <= 1'b1;
            r0ok = q_rv && q_r0 < 15'd16384;
            r1ok = q_rv && q_v1 && q_r1 < 15'd16384;
            if ((q_rv && q_r0 >= 15'd16384) || (q_rv && q_v1 && q_r1 >= 15'd16384)) err <= 1'b1;
            if (r0ok && r1ok && q_r0[1:0] == q_r1[1:0]) err <= 1'b1;
            a_v <= (r0ok ? (4'd1 << q_r0[1:0]) : 4'd0) | ((r1ok && !(r0ok && q_r0[1:0] == q_r1[1:0])) ? (4'd1 << q_r1[1:0]) : 4'd0);
            dv0 <= {dv0[RLAT-1:0], r0ok}; dv1 <= {dv1[RLAT-1:0], r1ok && !(r0ok && q_r0[1:0] == q_r1[1:0])};
        end
        w_row <= q_wa[13:0]; w_d <= q_wd;
        for (k = 0; k < 4; k = k + 1) a_row[14*k +: 14] <= (q_rv && q_r1[1:0] == k[1:0] && !(q_r0[1:0] == k[1:0])) ? q_r1[13:0] : q_r0[13:0];
        dl0[0] <= q_r0[1:0]; dl1[0] <= q_r1[1:0];
        for (k = 1; k <= RLAT; k = k + 1) begin dl0[k] <= dl0[k-1]; dl1[k] <= dl1[k-1]; end
    end
    reg [1025:0] r_q; reg r_qv; reg r_bad;
    wire        e0 = dv0[RLAT], e1 = dv1[RLAT];
    wire [1:0]  l0 = dl0[RLAT], l1 = dl1[RLAT];
    always @(posedge ck_control_t) begin
        if (!tn) begin r_q <= 1026'd0; r_qv <= 1'b0; r_bad <= 1'b0; end
        else begin
`ifdef OT_VM_WFC_MUT_PAIR
            r_q <= {e0, e0 ? e_d[512*l0 +: 512] : 512'd0, e1, e1 ? e_d[512*l1 +: 512] : 512'd0};
`else
            r_q <= {e1, e1 ? e_d[512*l1 +: 512] : 512'd0, e0, e0 ? e_d[512*l0 +: 512] : 512'd0};
`endif
`ifdef OT_VM_WFC_CTL_MUT_LANE
            if (e1) r_q[1024:513] <= e_d[512*l0 +: 512];   // MUTANT: second response from the first lane
`endif
            r_qv <= e0 | e1;
            if (e_v != ((e0 ? (4'd1 << l0) : 4'd0) | (e1 ? (4'd1 << l1) : 4'd0))) r_bad <= 1'b1;
        end
    end
    generate if (RESPONSE_PAD == 0) begin : no_pad
        assign s_d = r_q; assign s_v = r_qv;
    end else begin : fixed_pad
        reg [1025:0] pad [0:RESPONSE_PAD-1]; reg [RESPONSE_PAD-1:0] padv; integer k;
        always @(posedge ck_control_t) begin
            if (!tn) begin for (k=0;k<RESPONSE_PAD;k=k+1) pad[k]<=1026'd0; padv <= '0; end
            else begin pad[0]<=r_q; for(k=1;k<RESPONSE_PAD;k=k+1) pad[k]<=pad[k-1];
                       padv <= {padv, r_qv}; end
        end
        assign s_d = pad[RESPONSE_PAD-1]; assign s_v = padv[RESPONSE_PAD-1];
    end endgenerate
    reg [1:0] sq; always @(posedge ck_control_s or negedge rst_control_s) if (!rst_control_s) sq <= 2'b00; else sq <= {sq[0], 1'b1};
    wire own = err | r_bad | x34f;
    always @(posedge ck_control_s) begin g_q <= sq[1]; e_q <= sq[1] && (own | x43f | vm_fault); end
`ifdef OT_VM_WFC_CTL_MUT_FAULT
    always @(posedge ck_control_t) if (!tn) fault <= 1'b0; else fault <= err | x34f | x43f;   // MUTANT: return-slot fault dropped
`else
    always @(posedge ck_control_t) if (!tn) fault <= 1'b0; else fault <= own | x43f;
`endif
endmodule

module dsfd_vm_static_wfc #(parameter integer RLAT = 13, parameter integer RESPONSE_PAD = 0) (
    input wire ck_control_s, ck_control_t,
    input wire ck_x34_s, ck_x34_t, ck_x43_s, ck_x43_t,
    input wire rst_control_s, rss_control_t,
    input wire rst_x34_s, rss_x34_t, rst_x43_s, rss_x43_t,
    input  wire [559:0]  f_wfc,
    output wire [1028:0] t_wfc,
    // stream side to / from dsfd_vm_static_core
    output wire          w_v, output wire [13:0] w_row, output wire [511:0] w_d,
    output wire [3:0]    a_v, output wire [55:0] a_row,         // aux ports 8..11
    input  wire [3:0]    e_v, input wire [2047:0] e_d,          // aux ports 8..11 returns (core output registers)
    input  wire          vm_fault,                              // stream level
    output wire          fault                                  // stream level, registered in u_ctl (+1 edge)
);
    // Wires only: the 3:4 x34 (serial -> stream), the control leaf dsfd_vm_static_wfc_ctl and the 4:3 x43.
    wire xv; wire [559:0] xd; wire x34f; wire ov; wire [1025:0] od; wire x43f; wire sv; wire [1025:0] sd; wire g_q, e_q;
    ot_s81_vm_x34 #(.W(560)) u_xi (.s_ck(ck_x34_s), .s_rst_n(rst_x34_s), .s_v(f_wfc[0] | f_wfc[528]), .s_d(f_wfc),
        .t_ck(ck_x34_t), .t_rst_n(rss_x34_t), .o_v(xv), .o_d(xd), .fault(x34f));
    dsfd_vm_static_wfc_ctl #(.RLAT(RLAT), .RESPONSE_PAD(RESPONSE_PAD)) u_ctl (
        .ck_control_s(ck_control_s), .ck_control_t(ck_control_t), .rst_control_s(rst_control_s), .rss_control_t(rss_control_t),
        .xv(xv), .xd(xd), .x34f(x34f), .x43f(x43f), .w_v(w_v), .w_row(w_row), .w_d(w_d), .a_v(a_v), .a_row(a_row),
        .e_v(e_v), .e_d(e_d), .vm_fault(vm_fault), .s_v(sv), .s_d(sd), .g_q(g_q), .e_q(e_q), .fault(fault));
    ot_s81_vm_x43 #(.W(1026)) u_xo (.t_ck(ck_x43_t), .t_rst_n(rss_x43_t), .s_v(sv), .s_d(sd),
        .s_ck(ck_x43_s), .s_rst_n(rst_x43_s), .o_v(ov), .o_d(od), .fault(x43f));
    assign t_wfc = {e_q, od, g_q, g_q};
endmodule
`default_nettype wire
