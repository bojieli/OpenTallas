`timescale 1ns/1ps
// emb-hbm 2026-10-08: ot_qwen_die_hub_emb = ot_qwen_die_hub_fr (left byte-identical) + the EMBEDDING class:
//   * receive: link words with tag [10] = 1 (EMB) are not merged onto ar; they wait at their link's output FIFO head
//     for the embedding gateway ot_qfd_emb_gw (e_take pops them).  The output FIFO keeps the 11-b tag (523 b a word).
//   * transmit: the gateway's FETCH word goes on all four links at once (priority over the x3 skid, every link credit
//     in hand); x3 words with an EMB tag (the loader's BOOT_WR / BOOT_END, through the existing x3 path) carry their
//     full 512 data bits and go to the stack that holds the sector (BOOT_WR: stack_of(E), computed when the word
//     enters the skid) or to all four (BOOT_END, snooped for the gateway's boot check).  KV words are unchanged.
//   * the SU face of the embedding (ea {v, kind, 24-b address} + credit return, eq 512 b) at the hub pins, captured /
//     launched from flops (die-wide rule: register at every block pin).
// ---- original header (ot_qwen_die_hub_fr) ----
// Qwen ROM die HUB, FULL-RATE successor of ot_qwen_die_hub (left byte-identical; default-off: selected only by the
// qfd_hub_fr master cfg and its benches).  Gate link_credit_rtt (unified ledger 2026-10-07): the predecessor's link
// credit window (4 words, remote IBUF 4) against the measured 117..119-cycle credit round trip of a 54/55-station
// forwarded link sustains at most 4/118 = 3.4 % of the 528-bit link rate.  This successor sizes every loop of the
// hub to its round trip so a link streams one word a cycle:
//   link credits CR (default 128 >= 120-cycle measured window restart + margin): the remote endpoint's receive buffer
//     (ot_qwen_die_cdc_ch IBUF = CR); local credit counter widened to $clog2(CR+1); Gray credit return unchanged
//     (4-bit cumulative count mod 16 -- at most two increments between two samples of equal-rate clocks).
//   receive output credits OD (default 8 >= the 5-cycle cdc_ch -> merge -> credit loop): a per-link OD-entry output
//     FIFO replaces the predecessor's one-word `held` register (OCRED 1 = one word every 5 cycles a link).
//   x3 skid XS (default 8 >= the 4-cycle x3_v -> send -> x3_cr loop; predecessor 2 = half rate).
//   ar downstream credits ARC (default 4 >= the 3-cycle take -> ar_cr loop at a one-cycle consumer).
// ABI unchanged: link word [527:16] data, [15:5] tag, [4:1] Gray credit count, [0] valid; x3_d[511:510] = link.
// Native faults (sticky, one cause bit each in fault_cause):
//   [0] x3 skid overflow (source ignored x3 credits)            [1] receive buffer overflow (remote ignored credits)
//   [2] cdc_ch output-credit overflow                           [3] link credit OVERFLOW (returned > outstanding)
//   [4] ar credit overflow (consumer returned > ARC)            [5] per-link output FIFO overflow
module ot_qwen_die_hub_emb #(
    parameter integer NL  = 4,
    parameter integer LW  = 528,
    parameter integer CR  = 128,
    parameter integer OD  = 8,
    parameter integer XS  = 8,
    parameter integer ARC = 4,
    parameter integer AD  = 8,
    parameter integer RQD = 32,
    parameter integer MUT = 0
) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire [NL-1:0]     fck,
    input  wire [NL*LW-1:0]  l_i,
    output wire [NL*LW-1:0]  l_o,
    input  wire              x3_v,
    input  wire [511:0]      x3_d,
    input  wire [10:0]       x3_tag,
    output wire              x3_cr,
    output wire              ar_v,
    output wire [511:0]      ar_d,
    input  wire              ar_cr,
    output wire              fault,
    output wire [5:0]        fault_cause,
    // embedding: SU face (pins) and status
    input  wire              ea_v,
    input  wire              ea_kind,
    input  wire [23:0]       ea_addr,
    output wire              ea_cr,
    output wire              eq_v,
    output wire [511:0]      eq_d,
    output wire              emb_ready,
    output wire              emb_fault,
    output wire [7:0]        emb_fault_code
);
    import ot_qfd_emb_pkg::*;
    localparam integer CW  = $clog2(CR + 1) + 1;     // one spare bit: overflow is detected, never wrapped
    localparam integer OA  = $clog2(OD);
    localparam integer XA  = $clog2(XS);
    localparam integer AW  = $clog2(ARC + 1) + 1;
    genvar k;
    wire rn;
    ot_reset_sync u_rs (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(rn));
    // ---- receive side ------------------------------------------------------------------------------------------------
    wire [NL-1:0]      rv, rcr, rwf, rrf;
    wire [NL*523-1:0]  rd;                 // {tag 11, data 512}
    reg  [NL-1:0]      rtake;              // a word popped from a link's output FIFO (its credit back to the cdc_ch)
    reg  [3:0]         rcg  [0:NL-1];
    reg  [3:0]         rcnt [0:NL-1];
    generate for (k = 0; k < NL; k = k + 1) begin : g_rx
        wire [LW-1:0] w = l_i[k*LW +: LW];
        ot_qwen_die_cdc_ch #(.W(523), .IBUF(CR), .OCRED(OD), .AD(AD)) u_rx (
            .wclk(fck[k]), .wrst_n(rst_n), .i_v(w[0]), .i_d({w[15:5], w[LW-1:16]}), .i_cr(rcr[k]), .w_fault(rwf[k]),
            .rclk(ck), .rrst_n(rst_n), .o_v(rv[k]), .o_d(rd[k*523 +: 523]), .o_cr(rtake[k]), .r_fault(rrf[k]));
        reg [3:0] cb, cg;
        always @(posedge fck[k] or negedge rst_n)
            if (!rst_n) begin cb <= 0; cg <= 0; end
            else begin cb <= cb + rcr[k]; cg <= (cb + rcr[k]) ^ ((cb + rcr[k]) >> 1); end
        (* async_reg = "true" *) reg [3:0] s1, s2;
        always @(posedge ck or negedge rn) if (!rn) begin s1 <= 0; s2 <= 0; end else begin s1 <= cg; s2 <= s1; end
        always @(*) rcg[k] = s2;
        (* async_reg = "true" *) reg [3:0] t1, t2;
        always @(posedge ck or negedge rn) if (!rn) begin t1 <= 0; t2 <= 0; end else begin t1 <= w[4:1]; t2 <= t1; end
        always @(*) rcnt[k] = t2;
    end endgenerate
    // ---- per-link output FIFOs (OD words) and the ar merge (round robin, one word a cycle) --------------------------
    reg [523-1:0] lf   [0:NL*OD-1];
    reg [OA:0]    lfw  [0:NL-1];
    reg [OA:0]    lfr  [0:NL-1];
    reg [NL-1:0]  lne;                      // link FIFO non-empty
    reg [NL-1:0]  lfo;                      // link FIFO overflow (sticky, per link)
    integer i;
    always @(*) for (i = 0; i < NL; i = i + 1) lne[i] = (lfw[i] != lfr[i]);
    // EMB-class heads wait for the gateway; only KV heads are merged onto ar
    reg [NL-1:0] lemb, lkv;
    reg [NL*523-1:0] lhd;
    wire [NL-1:0] e_take;
    always @(*) for (i = 0; i < NL; i = i + 1) begin
        lhd[i*523 +: 523] = lf[i*OD + lfr[i][OA-1:0]];
        lemb[i] = lne[i] && lhd[i*523 + 522];
        lkv[i] = lne[i] && !lhd[i*523 + 522];
    end
    reg [1:0] rr;
    reg [AW-1:0] arc;
    reg       arv_q, arcr_q, aro;
    reg [511:0] ard_q;
    reg [1:0] pick; reg any;
    always @(*) begin
        any = 1'b0; pick = rr;
        for (i = NL - 1; i >= 0; i = i - 1)
            if (lkv[(rr + i) % NL]) begin any = 1'b1; pick = (rr + i) % NL; end
    end
    wire take = any && (arc != 0);
    wire [AW-1:0] arc_n = arc - {{(AW-1){1'b0}}, take} + {{(AW-1){1'b0}}, arcr_q};
    always @(posedge ck or negedge rn)
        if (!rn) begin
            rr <= 0; arc <= ARC[AW-1:0]; arv_q <= 1'b0; arcr_q <= 1'b0; rtake <= 0; lfo <= 0; aro <= 1'b0;
            for (i = 0; i < NL; i = i + 1) begin lfw[i] <= 0; lfr[i] <= 0; end
        end else begin
            arcr_q <= ar_cr;
            arc <= arc_n;
            aro <= aro | (arc_n > ARC[AW-1:0]);
            arv_q <= take;
            rtake <= 0;
            for (i = 0; i < NL; i = i + 1)
                if (rv[i]) begin
                    lfw[i] <= lfw[i] + 1'b1;
                    if ((lfw[i][OA-1:0] == lfr[i][OA-1:0]) && (lfw[i][OA] != lfr[i][OA])) lfo[i] <= 1'b1;
                end
            if (take) begin lfr[pick] <= lfr[pick] + 1'b1; rtake[pick] <= 1'b1; rr <= pick + 1'b1; end
            for (i = 0; i < NL; i = i + 1) if (e_take[i]) begin lfr[i] <= lfr[i] + 1'b1; rtake[i] <= 1'b1; end
        end
    always @(posedge ck) begin
        for (i = 0; i < NL; i = i + 1) if (rv[i]) lf[i*OD + lfw[i][OA-1:0]] <= {rd[i*523 + 512 +: 11], rd[i*523 +: 512]};
        if (take) ard_q <= lf[pick*OD + lfr[pick][OA-1:0]][511:0];
    end
    assign ar_v = arv_q; assign ar_d = ard_q;
    // ---- transmit side: x3 staging -> XS-word skid -> the selected link ---------------------------------------------
    reg         xv_q; reg [511:0] xd_q; reg [10:0] xt_q;
    always @(posedge ck) begin xd_q <= x3_d; xt_q <= x3_tag; end
    always @(posedge ck or negedge rn) if (!rn) xv_q <= 1'b0; else xv_q <= x3_v;
    reg [511:0] sd [0:XS-1]; reg [10:0] st [0:XS-1]; reg [1:0] sdst [0:XS-1]; reg sbc [0:XS-1];
    reg [XA:0]  sw, sr;
    wire        sne  = (sw != sr);
    wire        sful = (sw[XA-1:0] == sr[XA-1:0]) && (sw[XA] != sr[XA]);
    reg [CW-1:0] lc    [0:NL-1];
    reg [3:0]    lseen [0:NL-1];
    reg [NL*LW-1:0] lo_q;
    reg        xcr_q, ovf, lco;
    wire [511:0] shd = sd[sr[XA-1:0]];
    wire [10:0]  sht = st[sr[XA-1:0]];
    wire       semb = sht[10];
    wire [1:0] dst  = sdst[sr[XA-1:0]];
    wire       sbcw = sbc[sr[XA-1:0]];
    // the gateway's FETCH (all four links) first, then the skid head (one link, or all four for BOOT_END)
    wire       g_v; wire [10:0] g_tag; wire [511:0] g_d;
    reg  [NL-1:0] lcnz;
    always @(*) for (i = 0; i < NL; i = i + 1) lcnz[i] = (lc[i] != 0);
    wire       gsend = g_v && (&lcnz);
    wire       send = !gsend && sne && (sbcw ? (&lcnz) : lcnz[dst]);
    wire       bend_v = send && semb && sht[9:8] == K_BOOT_END;
    function [3:0] g2b(input [3:0] g); g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; endfunction
    reg [CW-1:0] lc_n [0:NL-1];
    reg [3:0]    dlt;
    always @(*)
        for (i = 0; i < NL; i = i + 1) begin
            dlt = g2b(rcnt[i]) - g2b(lseen[i]);
            lc_n[i] = lc[i] - (((send && (sbcw || dst == i)) || gsend) ? {{(CW-1){1'b0}}, 1'b1} : {CW{1'b0}}) + {{(CW-4){1'b0}}, dlt};
        end
    always @(posedge ck) if (xv_q && !sful) begin
        sd[sw[XA-1:0]] <= xd_q; st[sw[XA-1:0]] <= xt_q;
        sdst[sw[XA-1:0]] <= xt_q[10] ? stack_of(xd_q[24:0]) : xd_q[511:510];
        sbc[sw[XA-1:0]] <= xt_q[10] && xt_q[9:8] == K_BOOT_END;
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin sw <= 0; sr <= 0; xcr_q <= 0; ovf <= 0; lco <= 0; lo_q <= 0;
            for (i = 0; i < NL; i = i + 1) begin lc[i] <= CR[CW-1:0]; lseen[i] <= 0; end end
        else begin
            if (xv_q) begin if (sful) ovf <= 1'b1; else sw <= sw + 1'b1; end
            if (send) sr <= sr + 1'b1;
            xcr_q <= send;
            for (i = 0; i < NL; i = i + 1) begin
                lc[i] <= lc_n[i];
                if (lc_n[i] > CR[CW-1:0]) lco <= 1'b1;
                lseen[i] <= rcnt[i];
                lo_q[i*LW +: LW] <= gsend ? {g_d, g_tag, rcg[i], 1'b1} :
                                    (send && (sbcw || dst == i)) ? {semb ? shd : {shd[509:0], 2'b00}, sht, rcg[i], 1'b1} :
                                    {512'd0, 11'd0, rcg[i], 1'b0};
            end
        end
    assign l_o = lo_q;
    assign x3_cr = xcr_q;
    // ---- embedding gateway + its SU face (pin flops both ways) ---------------------------------------------------------
    (* keep *) reg eav_p, eak_p; (* keep *) reg [23:0] eaa_p;
    (* keep *) reg ecr_p, eqv_p; (* keep *) reg [511:0] eqd_p;
    wire g_ecr, g_eqv; wire [511:0] g_eqd;
    always @(posedge ck or negedge rn) if (!rn) begin eav_p <= 1'b0; ecr_p <= 1'b0; eqv_p <= 1'b0; end
        else begin eav_p <= ea_v; ecr_p <= g_ecr; eqv_p <= g_eqv; end
    always @(posedge ck) begin eak_p <= ea_kind; eaa_p <= ea_addr; eqd_p <= g_eqd; end
    assign ea_cr = ecr_p; assign eq_v = eqv_p; assign eq_d = eqd_p;
    wire [31:0] g_fetches;
    ot_qfd_emb_gw #(.RQD(RQD), .MUT(MUT)) u_gw (.ck(ck), .rn(rn), .ea_v(eav_p), .ea_kind(eak_p), .ea_addr(eaa_p),
        .ea_cr(g_ecr), .eq_v(g_eqv), .eq_d(g_eqd), .e_v(lemb), .e_d(lhd), .e_take(e_take),
        .g_v(g_v), .g_tag(g_tag), .g_d(g_d), .g_rdy(gsend), .bend_v(bend_v), .bend_d(shd[63:0]),
        .emb_ready(emb_ready), .fault(emb_fault), .fault_code(emb_fault_code), .fetches(g_fetches));
    (* async_reg = "true" *) reg [NL-1:0] wf1, wf2;
    always @(posedge ck or negedge rn) if (!rn) begin wf1 <= 0; wf2 <= 0; end else begin wf1 <= rwf; wf2 <= wf1; end
    reg [5:0] fc_q;
    always @(posedge ck or negedge rn)
        if (!rn) fc_q <= 6'd0;
        else fc_q <= fc_q | {(|lfo), aro, lco, (|rrf), (|wf2), ovf};
    assign fault_cause = fc_q;
    assign fault = |fc_q;
endmodule

// Routed top of qfd_hub_emb: the qfd_hub_fr pins + the embedding SU face (ea 26 b in, ea_cr, eq 512 b + valid out)
// and the embedding status.
module ot_qwen_die_hub_emb_top #(
    parameter integer CR = 128, parameter integer OD = 8, parameter integer XS = 8, parameter integer ARC = 4,
    parameter integer RQD = 32, parameter integer MUT = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         fck0, input wire fck1, input wire fck2, input wire fck3,
    input  wire [527:0] l0_i, output wire [527:0] l0_o,
    input  wire [527:0] l1_i, output wire [527:0] l1_o,
    input  wire [527:0] l2_i, output wire [527:0] l2_o,
    input  wire [527:0] l3_i, output wire [527:0] l3_o,
    input  wire         x3_v, input wire [511:0] x3_d, input wire [10:0] x3_tag, output wire x3_cr,
    output wire         ar_v, output wire [511:0] ar_d, input wire ar_cr,
    output wire         fault,
    output wire [5:0]   fault_cause,
    input  wire         ea_v, input wire ea_kind, input wire [23:0] ea_addr, output wire ea_cr,
    output wire         eq_v, output wire [511:0] eq_d,
    output wire         emb_ready, output wire emb_fault, output wire [7:0] emb_fault_code
);
    ot_qwen_die_hub_emb #(.NL(4), .LW(528), .CR(CR), .OD(OD), .XS(XS), .ARC(ARC), .RQD(RQD), .MUT(MUT)) u (.ck(ck),
        .rst_n(rst_n), .fck({fck3, fck2, fck1, fck0}), .l_i({l3_i, l2_i, l1_i, l0_i}), .l_o({l3_o, l2_o, l1_o, l0_o}),
        .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(x3_cr), .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr),
        .fault(fault), .fault_cause(fault_cause), .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_d(eq_d), .emb_ready(emb_ready), .emb_fault(emb_fault), .emb_fault_code(emb_fault_code));
endmodule
