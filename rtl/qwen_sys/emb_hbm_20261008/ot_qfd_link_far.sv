`timescale 1ns/1ps
// Strip-end endpoint of one hub <-> stack link (emb-hbm 2026-10-08): the far-end counterpart of the full-rate hub's
// per-link logic (ot_qwen_die_hub_fr), with a CLASS split for the embedding engine.  Link ABI unchanged: word
// [527:16] data, [15:5] tag, [4:1] Gray credit count returned for the opposite direction, [0] valid.
//   receive (hub -> stack, l_i launched on the hub's forwarded clock ck): ot_qwen_die_cdc_ch (IBUF = CR = the hub's
//     link credits) into the local clock lclk, an OD-word output FIFO, then by tag [10]: EMB words to the engine
//     (e_v / e_d, ECR credits the engine returns with e_cr), the rest to the KV far end (k_v / k_d, k_cr).  Its credit
//     pulses count a 4-bit binary counter in ck, Gray-coded, two-flop synchronised into lclk and sent in our tx control.
//   transmit (stack -> hub, l_o launched from lclk = the forwarded clock of this direction): the engine's words
//     (t_v / t_d, a TQ-word queue whose slots are its credits: t_cr) and the KV far end's (kt_v / kt_d / kt_cr),
//     round robin, one word a cycle against CR link credits (the hub's receive buffer); the hub's returned Gray count
//     arrives in its words' control and is synchronised into lclk.
// Faults (sticky): receive buffer / output FIFO overflow, link credit overflow, a class credit returned in excess.
module ot_qfd_link_far #(
    parameter integer CR  = 128,
    parameter integer OD  = 8,
    parameter integer ECR = 4,
    parameter integer KCR = 4,
    parameter integer TQ  = 4,
    parameter integer AD  = 8,
    // AFW (sys-takeover 2026-10-09, opt-in): the receive channel's wide async FIFO with a registered write
    // (ot_qwen_die_cdc_ch AFW = 1, +1 ck before visibility): qfd_emb_far92 PREROUTE -941 = ir -> 128:1 receive-buffer
    // mux -> async FIFO mem write.  Default from `OT_QFD_FAR_AFW (bench) else 0.
`ifdef OT_QFD_FAR_AFW
    parameter integer AFW = 1,
`else
    parameter integer AFW = 0,
`endif
    // RXP (sys-takeover, opt-in): receive buffer with one-hot pointers and a registered 2-stage read (ot_qwen_die_cdc_ch
    // RXP; qfd_emb_far92_afw TT -557: ir -> 128:1 x 523-b receive mux).  Default from `OT_QFD_FAR_RXP (bench) else 0.
`ifdef OT_QFD_FAR_RXP
    parameter integer RXP = 1
`else
    parameter integer RXP = 0
`endif
) (
    input  wire          ck,
    input  wire          lclk,
    input  wire          rst_n,
    input  wire [527:0]  l_i,
    output reg  [527:0]  l_o,
    output reg           e_v,
    output reg  [522:0]  e_d,
    input  wire          e_cr,
    output reg           k_v,
    output reg  [522:0]  k_d,
    input  wire          k_cr,
    input  wire          t_v,
    input  wire [522:0]  t_d,
    output reg           t_cr,
    input  wire          kt_v,
    input  wire [522:0]  kt_d,
    output reg           kt_cr,
    output wire          fault
);
    localparam integer CW = $clog2(CR + 1) + 1;
    localparam integer OA = $clog2(OD);
    localparam integer TA = $clog2(TQ);
    wire rn;
    ot_reset_sync u_rs (.clk(lclk), .async_rst_n(rst_n), .sync_rst_n(rn));
    // ---- receive ---------------------------------------------------------------------------------------------------
    wire rv, rcr, rwf, rrf;
    wire [522:0] rd;
    reg rtake;
    ot_qwen_die_cdc_ch #(.W(523), .IBUF(CR), .OCRED(OD), .AD(AD), .AFW(AFW), .RXP(RXP)) u_rx (
        .wclk(ck), .wrst_n(rst_n), .i_v(l_i[0]), .i_d({l_i[15:5], l_i[527:16]}), .i_cr(rcr), .w_fault(rwf),
        .rclk(lclk), .rrst_n(rst_n), .o_v(rv), .o_d(rd), .o_cr(rtake), .r_fault(rrf));
    reg [3:0] cb, cg;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin cb <= 0; cg <= 0; end
        else begin cb <= cb + rcr; cg <= (cb + rcr) ^ ((cb + rcr) >> 1); end
    (* async_reg = "true" *) reg [3:0] s1, s2;
    always @(posedge lclk or negedge rn) if (!rn) begin s1 <= 0; s2 <= 0; end else begin s1 <= cg; s2 <= s1; end
    (* async_reg = "true" *) reg [3:0] g1, g2;          // the hub's returned Gray count, from its words (ck)
    reg [3:0] gq;
    always @(posedge ck or negedge rst_n) if (!rst_n) gq <= 0; else gq <= l_i[4:1];
    always @(posedge lclk or negedge rn) if (!rn) begin g1 <= 0; g2 <= 0; end else begin g1 <= gq; g2 <= g1; end
    // output FIFO + class split
    reg [522:0] of [0:OD-1];
    reg [OA:0] ow, orr;
    wire o_ne = ow != orr;
    wire [522:0] oh = of[orr[OA-1:0]];
    wire o_emb = oh[522];
    reg [3:0] ec, kc;
    wire fwd = o_ne && (o_emb ? ec != 0 : kc != 0);
    reg ofo, cro;
    always @(posedge lclk) if (rv) of[ow[OA-1:0]] <= rd;
    always @(posedge lclk or negedge rn)
        if (!rn) begin ow <= 0; orr <= 0; rtake <= 1'b0; e_v <= 1'b0; k_v <= 1'b0; ec <= 4'(ECR); kc <= 4'(KCR); ofo <= 1'b0; cro <= 1'b0; end
        else begin
            if (rv) begin ow <= ow + 1'b1; if ((ow[OA-1:0] == orr[OA-1:0]) && (ow[OA] != orr[OA])) ofo <= 1'b1; end
            rtake <= fwd;
            if (fwd) orr <= orr + 1'b1;
            e_v <= fwd && o_emb; k_v <= fwd && !o_emb;
            // RXP: separate enables so synthesis cannot merge e_d / k_d into one flop driving both the emb (top) and the KV
            // (bottom) pins of the 1.4-mm strip (qfd_emb_far92_afw reg->out e_d[399] -> kv_o[400] -586 ps)
            if (RXP != 0) begin if (fwd && o_emb) e_d <= oh; if (fwd && !o_emb) k_d <= oh; end
            else if (fwd) begin e_d <= oh; k_d <= oh; end
            ec <= ec - ((fwd && o_emb) ? 1'b1 : 1'b0) + (e_cr ? 1'b1 : 1'b0);
            kc <= kc - ((fwd && !o_emb) ? 1'b1 : 1'b0) + (k_cr ? 1'b1 : 1'b0);
            if ((e_cr && ec == 4'(ECR)) || (k_cr && kc == 4'(KCR))) cro <= 1'b1;
        end
    // ---- transmit ----------------------------------------------------------------------------------------------------
    reg [522:0] tq [0:TQ-1]; reg [TA:0] tw, tr;
    reg [522:0] kq [0:TQ-1]; reg [TA:0] kw, kr;
    wire t_ne = tw != tr, k_ne = kw != kr;
    reg [CW-1:0] lc; reg [3:0] lseen; reg lco, tqo, rrb;
    function [3:0] g2b(input [3:0] g); g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; endfunction
    wire pick_t = t_ne && (!k_ne || rrb);
    wire pick_k = k_ne && !pick_t;
    wire send = (pick_t || pick_k) && lc != 0;
    wire [522:0] sw = pick_t ? tq[tr[TA-1:0]] : kq[kr[TA-1:0]];
    wire [CW-1:0] lc_n = lc - (send ? 1'b1 : 1'b0) + CW'(4'(g2b(g2) - g2b(lseen)));
    always @(posedge lclk) begin
        if (t_v) tq[tw[TA-1:0]] <= t_d;
        if (kt_v) kq[kw[TA-1:0]] <= kt_d;
    end
    always @(posedge lclk or negedge rn)
        if (!rn) begin tw <= 0; tr <= 0; kw <= 0; kr <= 0; lc <= CW'(CR); lseen <= 0; lco <= 1'b0; tqo <= 1'b0; rrb <= 1'b0;
            l_o <= 0; t_cr <= 1'b0; kt_cr <= 1'b0; end
        else begin
            if (t_v) begin tw <= tw + 1'b1; if ((tw[TA-1:0] == tr[TA-1:0]) && (tw[TA] != tr[TA])) tqo <= 1'b1; end
            if (kt_v) begin kw <= kw + 1'b1; if ((kw[TA-1:0] == kr[TA-1:0]) && (kw[TA] != kr[TA])) tqo <= 1'b1; end
            t_cr <= send && pick_t; kt_cr <= send && pick_k;
            if (send && pick_t) tr <= tr + 1'b1;
            if (send && pick_k) kr <= kr + 1'b1;
            if (send) rrb <= !pick_t;
            lc <= lc_n; lseen <= g2;
            if (lc_n > CW'(CR)) lco <= 1'b1;
            l_o <= {send ? sw[511:0] : 512'd0, send ? sw[522:512] : 11'd0, s2, send};
        end
    (* async_reg = "true" *) reg wf1, wf2;
    always @(posedge lclk or negedge rn) if (!rn) begin wf1 <= 0; wf2 <= 0; end else begin wf1 <= rwf; wf2 <= wf1; end
    reg f_q;
    always @(posedge lclk or negedge rn) if (!rn) f_q <= 1'b0; else f_q <= f_q | ofo | cro | lco | tqo | rrf | wf2;
    assign fault = f_q;
endmodule
