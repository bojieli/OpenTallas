// el1011-ds-coll 2026-10-11 (owner TEXTBOOK AUDIT, class 1/2/4/5/6 on dsfd_coll_cb): the cb tile rebuilt as HARDENED
// sub-elements, each with its own local clock tree and registered seams (the smh_tcc/bdc recipe).  The flat cb had one
// clock root over 63,916 sinks across 680.4 x 340.2 um (462 ps insertion), 2,700 boundary flops on its S face, a
// 2,100-bit 16:1 queue read mux into the anchored t_vm pin flops, and lane relays spanning two faces.
//
//   x:   0 ....... 113.4 ...... 178.2 ..... 5 x 77.76 ..... 567.0 ....... 680.4      (all tiles 340.2 tall)
//        dsfd_coll_cbr   dsfd_coll_cbf   dsfd_coll_cbq0, dsfd_coll_cbq x 4   dsfd_coll_cbr (mirrored)
//        lane 0 relays   f_vm pass-thru  output queue slices (420 bits of     lane 4 relays
//        (W face)        (+ cbj job)     t_vm each, own take / push copies)   (E face)
//
// dsfd_coll_cbh has dsfd_coll_cb's ports and function (bench: +define+OT_S81PH_CB_MASTER=dsfd_coll_cbh).  Cycle changes:
// t_vm +1 (pin relay, as TVR); lane credits +1 (PCR); fault sticky bits reach bw_flt up to 4 cycles later (chain).
// Datapath registers carry no reset (class 2); each tile synchronises rs itself (same edge in every tile).
`timescale 1ns/1ps

// OT_S81PH_CBH_PARENT (the parent route): the children below are hard macros (closed tiles), so their bodies are left
// out and synthesis binds them to their liberty views; the parent is wiring only.
`ifndef OT_S81PH_CBH_PARENT
// FIFO with a registered head: the D-deep array sits behind a head register, so the consumer reads a flop, and the
// array read mux lands in the head register (never in the consumer's logic).  Same push -> visible latency as
// ot_s81ph_rfifo (1 cycle); capacity D + 1.
// RREP (el1011-ds-coll 2026-10-11, opt-in, default 1 = byte-identical): the head-load read pointer is replicated RREP
// times (kept ot_s81ph_keep_ff bits), copy c selects head columns [c*SW +: SW] (cel u_sk: one rp bit drove 8,755 loads).
module ot_s81ph_hfifo #(parameter integer W = 8, parameter integer D = 16, parameter integer RREP = 1) (
    input  wire         clk, input wire rst_n,
    input  wire         push, input wire [W-1:0] wd,
    input  wire         pop,
    output reg          hv, output reg [W-1:0] hd,
    output reg          fault
);
    localparam integer AW = $clog2(D);
    reg [W-1:0] m [0:D-1];
    reg [AW-1:0] wp, rp;
    reg [AW:0] n;                                   // entries in the array (behind the head)
    wire take = pop && hv;
    wire m_ne = n != 0;
    // the head is (re)loaded when it is empty or taken: from the array if it holds words, else from the pushed word
    wire h_ld_m = (!hv || take) && m_ne;
    wire h_ld_w = (!hv || take) && !m_ne && push;
    wire m_wr = push && !h_ld_w;
    wire [W-1:0] m_rd;
    wire [AW-1:0] rp_nx = h_ld_m ? rp + 1'b1 : rp;
    generate if (RREP <= 1) begin : g_rp1
        assign m_rd = m[rp];
    end else begin : g_rpn
        localparam integer SW = (W + RREP - 1) / RREP;
        genvar c, b;
        for (c = 0; c < RREP; c = c + 1) begin : g_c
            localparam integer LO = c * SW, HI = ((c + 1) * SW > W) ? W : (c + 1) * SW;
            if (LO < W) begin : g_on
                wire [AW-1:0] rpc;
                for (b = 0; b < AW; b = b + 1) begin : g_b
                    ot_s81ph_keep_ff u_k (.clk(clk), .rst_n(rst_n), .d(rp_nx[b]), .q(rpc[b]));
                end
                wire [W-1:0] row = m[rpc];
                assign m_rd[HI-1:LO] = row[HI-1:LO];
            end
        end
    end endgenerate
    always @(posedge clk) begin
        if (m_wr) m[wp] <= wd;
        if (h_ld_m) hd <= m_rd;
        else if (h_ld_w) hd <= wd;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hv <= 1'b0; wp <= 0; rp <= 0; n <= 0; fault <= 1'b0; end
        else begin
            hv <= h_ld_m || h_ld_w || (hv && !take);
            if (m_wr) wp <= wp + 1'b1;
            if (h_ld_m) rp <= rp + 1'b1;
            n <= n + (m_wr ? 1'b1 : 1'b0) - (h_ld_m ? 1'b1 : 1'b0);
            if ((m_wr && n == D) || (pop && !hv)) fault <= 1'b1;
        end
endmodule

// one output-queue slice: WS bits of the packer word (bw_d) in, the same WS bits of t_vm out.  V0 = slice 0: its
// bit 0 is the t_vm valid (= its pop), it returns bw_cr and ends the fault chain (bw_flt) and gives the job endpoint
// its header copy.  Every slice pushes on its own copy of bw_v and pops on its own copy of the VM take (ts[0]); all
// slices hold the same occupancy, so they pop on the same edge (TREP).
module dsfd_coll_cbq_core #(parameter integer WS = 420, parameter integer V0 = 0, parameter integer OD = 16) (
    input  wire          ck, input wire rs,
    input  wire          bw_v, input wire [WS-1:0] bw_d,     // N face (from ce)
    input  wire          ts,                                  // S face: VM take
    output reg  [WS-1:0] t_vm,                                // S face
    input  wire          flt_i,                               // fault chain from the next slice (E)
    output reg           flt_o,                               // to the previous slice (W) / bw_flt (V0)
    output reg           bw_cr,                               // V0 only: credit to ce
    output reg  [13:0]   hq                                   // V0 only: t_vm[13:0] copy for the job endpoint
);
    localparam integer DW = V0 ? WS - 1 : WS;                 // V0: bit 0 is the valid, not data
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg bv_q, pq, ts_q, tk;
    reg [DW-1:0] bd_q, wq;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bv_q <= 1'b0; pq <= 1'b0; ts_q <= 1'b0; tk <= 1'b0; end
        else begin bv_q <= bw_v; pq <= bv_q; ts_q <= ts; tk <= ts_q; end
    always @(posedge ck) begin bd_q <= bw_d[WS-1 -: DW]; wq <= bd_q; end
    wire hv, f; wire [DW-1:0] hd;
    wire sp = hv && tk;
    ot_s81ph_hfifo #(.W(DW), .D(OD)) u_oq (.clk(ck), .rst_n(rst_n), .push(pq), .wd(wq), .pop(sp), .hv(hv), .hd(hd),
        .fault(f));
    // t_vq: the slice's t_vm word beside the queue; t_vm: a pure relay register at the S-face pins
    reg [WS-1:0] t_vq;
    wire [WS-1:0] t_nx;
    generate if (V0) begin : g_v0
        assign t_nx = sp ? {hd, 1'b1} : {WS{1'b0}};
    end else begin : g_vn
        assign t_nx = sp ? hd : {WS{1'b0}};
    end endgenerate
    always @(posedge ck) t_vq <= t_nx;
`ifdef OT_S81PH_MUT_CBH
    always @(posedge ck) t_vm <= (V0 == 0) ? {t_vq[WS-1:1], t_vm[0]} : t_vq;   // negative control: a data bit sticks
`else
    always @(posedge ck) t_vm <= t_vq;
`endif
    reg fi_q;                                                 // pin flop on the fault-chain input
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin fi_q <= 1'b0; flt_o <= 1'b0; bw_cr <= 1'b0; hq <= 14'd0; end
        else begin
            fi_q <= flt_i;
            if (f || fi_q) flt_o <= 1'b1;
            bw_cr <= V0 ? sp : 1'b0;
            hq <= V0 ? t_vq[13:0] : 14'd0;
        end
endmodule

module dsfd_coll_cbq0 (input wire ck, input wire rs, input wire bw_v, input wire [418:0] bw_d, input wire ts,
    output wire [419:0] t_vm, input wire flt_i, output wire bw_flt, output wire bw_cr, output wire [13:0] hq);
    dsfd_coll_cbq_core #(.WS(420), .V0(1)) u (.ck(ck), .rs(rs), .bw_v(bw_v), .bw_d({bw_d, 1'b0}), .ts(ts),
        .t_vm(t_vm), .flt_i(flt_i), .flt_o(bw_flt), .bw_cr(bw_cr), .hq(hq));
endmodule

module dsfd_coll_cbq (input wire ck, input wire rs, input wire bw_v, input wire [419:0] bw_d, input wire ts,
    output wire [419:0] t_vm, input wire flt_i, output wire flt_o);
    dsfd_coll_cbq_core #(.WS(420), .V0(0)) u (.ck(ck), .rs(rs), .bw_v(bw_v), .bw_d(bw_d), .ts(ts),
        .t_vm(t_vm), .flt_i(flt_i), .flt_o(flt_o), .bw_cr(), .hq());
endmodule

// one lane's relay pair: x_* = the lane tile's core face (W or E face of cb), n_* = the ce seam (N face).
// x_lo <- n_lo (core -> lane), n_li <- x_li (lane -> core); credit pulses both ways (ot_s81ph_cr_relay RSL 8, PCR).
module dsfd_coll_cbr #(parameter integer RSL = 8, parameter integer PCR = 1) (
    input  wire ck, input wire rs,
    input  wire n_lo_v, output wire n_lo_r, input  wire [552:0] n_lo_d,
    output wire x_lo_v, input  wire x_lo_r, output wire [552:0] x_lo_d,
    input  wire x_li_v, output wire x_li_r, input  wire [552:0] x_li_d,
    output wire n_li_v, input  wire n_li_r, output wire [552:0] n_li_d,
    input  wire [2:0] x_flt, output reg [2:0] n_flt
);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [2:0] flt_r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin flt_r <= 3'd0; n_flt <= 3'd0; end else begin flt_r <= x_flt; n_flt <= flt_r; end
    ot_s81ph_cr_relay #(.W(553), .RSL(RSL), .PCR(PCR)) u_lo (.clk(ck), .rst_n(rst_n), .i_v(n_lo_v), .i_cr(n_lo_r),
        .i_d(n_lo_d), .o_v(x_lo_v), .o_cr(x_lo_r), .o_d(x_lo_d));
    ot_s81ph_cr_relay #(.W(553), .RSL(RSL), .PCR(PCR)) u_li (.clk(ck), .rst_n(rst_n), .i_v(x_li_v), .i_cr(x_li_r),
        .i_d(x_li_d), .o_v(n_li_v), .o_cr(n_li_r), .o_d(n_li_d));
endmodule

// f_vm pass-through (S face in, N face out), two registers as in dsfd_coll_cb; with OT_S81PH_COLL_JOB the controller
// endpoint (ot_s81_coll_job) sits between them and reads slice 0's header copy (hq, +1 cycle vs the flat cb).
`ifdef OT_S81PH_COLL_JOB
`define OT_S81PH_CBF_M dsfd_coll_cbfj
`else
`define OT_S81PH_CBF_M dsfd_coll_cbf
`endif
module `OT_S81PH_CBF_M (
    input  wire ck, input wire rs,
    input  wire [591:0] f_vm, output wire [591:0] fvm_u,
    input  wire [13:0] hq
`ifdef OT_S81PH_COLL_JOB
    ,
    input  wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
`endif
);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rs) if (!rs) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg fv_v, fu_v;                       // record valids (reset)
    reg [591:1] fv_p, fu_p;               // payloads (no reset)
    wire [591:0] fv_r = {fv_p, fv_v};
    wire [591:0] fv_rel;
    assign fvm_u = {fu_p, fu_v};
`ifdef OT_S81PH_COLL_JOB
    wire jf_unused;
    // controller boundary registered both ways (class 3: c_cmd reached the job's state through 43 gate levels)
    reg [84:0] c_cmd_q; reg [8:0] c_done_q; reg [1:0] c_st_q;
    reg [13:0] hq_q;                                         // pin flop on the header copy from cbq0
    always @(posedge ck) hq_q <= hq;
    wire [8:0] c_done_w; wire [1:0] c_st_w;
    always @(posedge ck or negedge rs)
        if (!rs) begin c_cmd_q <= 85'd0; c_done_q <= 9'd0; c_st_q <= 2'd0; end
        else begin c_cmd_q <= c_cmd; c_done_q <= c_done_w; c_st_q <= c_st_w; end
    assign c_done = c_done_q; assign c_st = c_st_q;
    ot_s81_coll_job #(.MUT(`ifdef OT_S81PH_COLL_JOB_MUT `OT_S81PH_COLL_JOB_MUT `else 0 `endif)) u_job (.c_clk(ck),
        .c_rst_n(rs), .c_cmd(c_cmd_q), .c_done(c_done_w), .c_st(c_st_w), .ck(ck), .rs_n(rst_n), .vm_f(fv_r), .core_f(fv_rel),
        .core_h(hq_q), .fault(jf_unused));
`else
    assign fv_rel = fv_r;
    wire unused_hq = &{1'b0, hq};
`endif
    // valid / type bits (fv_r[0], the record header) are reset; the payload is not
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin fv_v <= 1'b0; fu_v <= 1'b0; end
        else begin fv_v <= f_vm[0]; fu_v <= fv_rel[0]; end
    always @(posedge ck) begin fv_p <= f_vm[591:1]; fu_p <= fv_rel[591:1]; end
endmodule

`else
`define OT_S81PH_CBF_M dsfd_coll_cbf
`endif

// the hierarchical cb: dsfd_coll_cb's ports, built from the hardened sub-elements
module dsfd_coll_cbh #(parameter integer OD = 16, parameter integer CR = 1, parameter integer TREP = 1,
    parameter integer RSL = 8, parameter integer PCR = 1) (
    input  wire [0:0]     ck,
    input  wire [0:0]     rs,
    input  wire [591:0]   f_vm,
    input  wire [2:0]     ts,
    output wire [2099:0]  t_vm,
    output wire [0:0] wlo_v,  input wire [0:0] wlo_r, output wire [552:0] wlo_d,
    input wire [0:0] wli_v,  output wire [0:0] wli_r, input  wire [552:0] wli_d,
    input  wire [2:0]     wflt,
    output wire [0:0] elo_v,  input wire [0:0] elo_r, output wire [552:0] elo_d,
    input wire [0:0] eli_v,  output wire [0:0] eli_r, input  wire [552:0] eli_d,
    input  wire [2:0]     eflt,
    output wire [591:0]   fvm_u,
    output wire [5:0]     flt_u,
    input wire [0:0] lo0_v,  output wire [0:0] lo0_r, input  wire [552:0] lo0_d,
    output wire [0:0] li0_v,  input wire [0:0] li0_r, output wire [552:0] li0_d,
    input wire [0:0] lo4_v,  output wire [0:0] lo4_r, input  wire [552:0] lo4_d,
    output wire [0:0] li4_v,  input wire [0:0] li4_r, output wire [552:0] li4_d,
    input wire [0:0] bw_v,
    input  wire [2099:1]  bw_d,
    output wire [0:0] bw_cr,
    output wire [0:0] bw_flt
`ifdef OT_S81PH_COLL_JOB
    ,
    input  wire [84:0]    c_cmd,
    output wire [8:0]     c_done,
    output wire [1:0]     c_st
`endif
);
    wire unused_p = &{1'b0, ts[2:1]};
    dsfd_coll_cbr u_rw (                                    // RSL 8 / PCR 1 = the closed tile's defaults
       .ck(ck[0]), .rs(rs[0]),
        .n_lo_v(lo0_v[0]), .n_lo_r(lo0_r[0]), .n_lo_d(lo0_d), .x_lo_v(wlo_v[0]), .x_lo_r(wlo_r[0]), .x_lo_d(wlo_d),
        .x_li_v(wli_v[0]), .x_li_r(wli_r[0]), .x_li_d(wli_d), .n_li_v(li0_v[0]), .n_li_r(li0_r[0]), .n_li_d(li0_d),
        .x_flt(wflt), .n_flt(flt_u[2:0]));
    dsfd_coll_cbr u_re (
       .ck(ck[0]), .rs(rs[0]),
        .n_lo_v(lo4_v[0]), .n_lo_r(lo4_r[0]), .n_lo_d(lo4_d), .x_lo_v(elo_v[0]), .x_lo_r(elo_r[0]), .x_lo_d(elo_d),
        .x_li_v(eli_v[0]), .x_li_r(eli_r[0]), .x_li_d(eli_d), .n_li_v(li4_v[0]), .n_li_r(li4_r[0]), .n_li_d(li4_d),
        .x_flt(eflt), .n_flt(flt_u[5:3]));
    wire [13:0] hq;
    `OT_S81PH_CBF_M u_f (.ck(ck[0]), .rs(rs[0]), .f_vm(f_vm), .fvm_u(fvm_u), .hq(hq)
`ifdef OT_S81PH_COLL_JOB
        , .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st)
`endif
    );
    wire [4:0] fc;                                            // fault chain, slice k -> slice k-1
    dsfd_coll_cbq0 u_q0 (.ck(ck[0]), .rs(rs[0]), .bw_v(bw_v[0]), .bw_d(bw_d[419:1]), .ts(ts[0]), .t_vm(t_vm[419:0]),
        .flt_i(fc[1]), .bw_flt(bw_flt[0]), .bw_cr(bw_cr[0]), .hq(hq));
    genvar k;
    generate for (k = 1; k < 5; k = k + 1) begin : g_q
        dsfd_coll_cbq u_q (.ck(ck[0]), .rs(rs[0]), .bw_v(bw_v[0]), .bw_d(bw_d[420*k +: 420]), .ts(ts[0]),
            .t_vm(t_vm[420*k +: 420]), .flt_i((k == 4) ? 1'b0 : fc[k + 1]), .flt_o(fc[k]));
    end endgenerate
    assign fc[0] = 1'b0;
`ifdef OT_S81PH_CBH_TRACE
    integer n_f = 0, n_u = 0, n_b = 0, n_t = 0, n_s = 0, n_c = 0, n_r = 0;
    always @(posedge ck[0]) begin
        n_f = n_f + f_vm[0]; n_u = n_u + fvm_u[0]; n_b = n_b + bw_v[0]; n_t = n_t + t_vm[0]; n_s = n_s + ts[0];
        n_c = n_c + bw_cr[0]; n_r = n_r + rs[0];
        if (n_r % 50000 == 1)
            $display("CBH %m t=%0t rs_cyc=%0d f_vm=%0d fvm_u=%0d bw_v=%0d t_vm=%0d ts=%0d bw_cr=%0d", $time, n_r, n_f, n_u,
                     n_b, n_t, n_s, n_c);
    end
`endif
endmodule
