// Additive metadata-visible successor; original hub remains byte-identical.
`timescale 1ns/1ps
// Qwen ROM die HUB master (r21 qfd_hub, 412.536 x 412.536; die-top answer 2026-10-07: after r18 the hub is the four
// stack-link endpoints + plain registered staging x3 / ar + the pll_r* region clock roots, near-HBM combine dropped).
//   links: ln (2 links, north), lsw, lse (south split) = NL 4 links of 528 b a direction (512 data + 16 control).
//     link word control (low 16 b): [0] valid, [4:1] Gray credit count returned for the opposite direction,
//     [15:5] tag.  Receive: ot_qwen_die_cdc_ch from the link's forwarded clock fck[k] into ck (IBUF 4 = the remote
//     sender's credits); its credit pulses count up a 4-bit counter in fck[k], sent back Gray-coded in our tx control
//     and synchronised by the remote.  Transmit: launched from flops on ck (forwarded with the data).
//   x3 (from sp_su64_sfu.q, 512 b): x3_d[511:510] selects the stack link, [509:0] + x3_tag ride the link data;
//     captured at the pin, credit x3_cr per word taken (2 credits), sent when the link holds a credit (4 from the
//     remote endpoint's buffer; the remote returns them through its Gray count).
//   ar (to sp_vector_memory.ar, 512 b): the received words of the four links, round robin, launched from a flop;
//     downstream credits ar_cr (4).
// The pll_r* pins are clock-tree roots (no data path) and are not part of this timing view.
module ot_qwen_die_hub_identity #(
    parameter integer ENABLE_IDENTITY = 0,
    parameter integer NL = 4,
    parameter integer LW = 528
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
    output wire [10:0]       ar_tag,
    output wire [1:0]        ar_source,
    input  wire              ar_cr,
    output wire              fault
);
    genvar k;
    wire rn;
    ot_reset_sync u_rs (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(rn));
    // ---- receive side ------------------------------------------------------------------------------------------------
    wire [NL-1:0]      rv, rcr, rwf, rrf;
    wire [NL*523-1:0]  rd;                 // {tag 11, data 512}
    reg  [NL-1:0]      rtake;              // a received word taken by the ar merge (its credit back to the cdc_ch)
    reg  [3:0]         rcg [0:NL-1];       // Gray credit counter, synchronised into ck for our tx control
    reg  [3:0]         rcnt [0:NL-1];      // remote credit count seen (Gray, synchronised) for our tx
    generate for (k = 0; k < NL; k = k + 1) begin : g_rx
        wire [LW-1:0] w = l_i[k*LW +: LW];
        ot_qwen_die_cdc_ch #(.W(523), .IBUF(4), .OCRED(1)) u_rx (
            .wclk(fck[k]), .wrst_n(rst_n), .i_v(w[0]), .i_d({w[15:5], w[LW-1:16]}), .i_cr(rcr[k]), .w_fault(rwf[k]),
            .rclk(ck), .rrst_n(rst_n), .o_v(rv[k]), .o_d(rd[k*523 +: 523]), .o_cr(rtake[k]), .r_fault(rrf[k]));
        // credit pulses -> 4-bit binary count in fck, Gray-coded, two-flop synchronised into ck
        reg [3:0] cb, cg;
        always @(posedge fck[k] or negedge rst_n)
            if (!rst_n) begin cb <= 0; cg <= 0; end
            else begin cb <= cb + rcr[k]; cg <= (cb + rcr[k]) ^ ((cb + rcr[k]) >> 1); end
        (* async_reg = "true" *) reg [3:0] s1, s2;
        always @(posedge ck or negedge rn) if (!rn) begin s1 <= 0; s2 <= 0; end else begin s1 <= cg; s2 <= s1; end
        always @(*) rcg[k] = s2;
        // the remote's returned-credit Gray count arrives in its rx word control [4:1] (forwarded clock): sync it
        (* async_reg = "true" *) reg [3:0] t1, t2;
        always @(posedge ck or negedge rn) if (!rn) begin t1 <= 0; t2 <= 0; end else begin t1 <= w[4:1]; t2 <= t1; end
        always @(*) rcnt[k] = t2;
    end endgenerate
    // ---- ar merge (round robin), one cdc_ch word at a time (OCRED 1 a link: hold until taken) ---------------------
    reg [1:0] rr;
    reg [2:0] arc;                          // ar downstream credits
    reg       arv_q, arcr_q;
    reg [511:0] ard_q;
    reg [NL-1:0] held;                      // a link's cdc_ch output word waiting (o_v seen, not yet taken)
    reg [523*NL-1:0] hd;
    integer i;
    reg [1:0] pick; reg any;
    always @(*) begin
        any = 1'b0; pick = rr;
        for (i = NL - 1; i >= 0; i = i - 1)
            if (held[(rr + i) % NL]) begin any = 1'b1; pick = (rr + i) % NL; end
    end
    wire take = any && (arc != 0);
    always @(posedge ck or negedge rn)
        if (!rn) begin held <= 0; rr <= 0; arc <= 3'd4; arv_q <= 1'b0; arcr_q <= 1'b0; rtake <= 0; end
        else begin
            arcr_q <= ar_cr;
            arc <= arc - take + arcr_q;
            arv_q <= take;
            rtake <= 0;
            for (i = 0; i < NL; i = i + 1) if (rv[i]) held[i] <= 1'b1;
            if (take) begin held[pick] <= 1'b0; rtake[pick] <= 1'b1; rr <= pick + 1'b1; end
        end
    always @(posedge ck) begin
        for (i = 0; i < NL; i = i + 1) if (rv[i]) hd[i*523 +: 523] <= rd[i*523 +: 523];
        if (take) ard_q <= hd[pick*523 +: 512];
    end
    assign ar_v = arv_q; assign ar_d = ard_q;
    generate if (ENABLE_IDENTITY != 0) begin : g_identity
        reg [10:0] tag_q;
        reg [1:0] source_q;
        always @(posedge ck) if (take) begin
            tag_q <= hd[pick*523 + 512 +: 11];
            source_q <= pick;
        end
        assign ar_tag = tag_q;
        assign ar_source = source_q;
    end else begin : g_identity_off
        assign ar_tag = 11'd0;
        assign ar_source = 2'd0;
    end endgenerate
    // ---- transmit side: x3 staging -> the selected link -----------------------------------------------------------
    reg         xv_q; reg [511:0] xd_q; reg [10:0] xt_q;
    always @(posedge ck) begin xd_q <= x3_d; xt_q <= x3_tag; end
    always @(posedge ck or negedge rn) if (!rn) xv_q <= 1'b0; else xv_q <= x3_v;
    reg [1:0]  sv; reg [511:0] sd [0:1]; reg [10:0] st [0:1]; reg sw, sr;   // 2-word skid (x3 credits = 2)
    reg [2:0]  lc [0:NL-1];                 // link credits (remote buffer 4)
    reg [3:0]  lseen [0:NL-1];              // last Gray count seen
    reg [NL*LW-1:0] lo_q;
    reg        xcr_q, ovf;
    wire [1:0] dst = sd[sr][511:510];
    wire       send = sv[sr] && (lc[dst] != 0);
    function [3:0] g2b(input [3:0] g); g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; endfunction
    always @(posedge ck) if (xv_q) begin sd[sw] <= xd_q; st[sw] <= xt_q; end
    always @(posedge ck or negedge rn)
        if (!rn) begin sv <= 0; sw <= 0; sr <= 0; xcr_q <= 0; ovf <= 0; lo_q <= 0;
            for (i = 0; i < NL; i = i + 1) begin lc[i] <= 3'd4; lseen[i] <= 0; end end
        else begin
            if (xv_q) begin if (sv[sw]) ovf <= 1'b1; sv[sw] <= 1'b1; sw <= ~sw; end
            if (send) begin sv[sr] <= 1'b0; sr <= ~sr; end
            xcr_q <= send;
            for (i = 0; i < NL; i = i + 1) begin
                lc[i] <= lc[i] - ((send && dst == i) ? 3'd1 : 3'd0) + (g2b(rcnt[i]) - g2b(lseen[i]));
                lseen[i] <= rcnt[i];
                lo_q[i*LW +: LW] <= {(send && dst == i) ? sd[sr][509:0] : 510'd0, 2'b00,
                                     (send && dst == i) ? st[sr] : 11'd0, rcg[i], send && dst == i};
            end
        end
    assign l_o = lo_q;
    assign x3_cr = xcr_q;
    (* async_reg = "true" *) reg [NL-1:0] wf1, wf2;   // sticky receive-buffer overflows (fck domains) into ck
    always @(posedge ck or negedge rn) if (!rn) begin wf1 <= 0; wf2 <= 0; end else begin wf1 <= rwf; wf2 <= wf1; end
    reg f_q;
    always @(posedge ck or negedge rn) if (!rn) f_q <= 1'b0; else f_q <= f_q | ovf | (|rrf) | (|wf2);
    assign fault = f_q;
endmodule

// Routed top of qfd_hub: the same hub with one port pair per link (pin placement by link: ln = links 0 / 1, lsw = 2,
// lse = 3) and one forwarded clock per link.
module ot_qwen_die_hub_identity_top #(parameter integer ENABLE_IDENTITY = 0) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         fck0, input wire fck1, input wire fck2, input wire fck3,
    input  wire [527:0] l0_i, output wire [527:0] l0_o,
    input  wire [527:0] l1_i, output wire [527:0] l1_o,
    input  wire [527:0] l2_i, output wire [527:0] l2_o,
    input  wire [527:0] l3_i, output wire [527:0] l3_o,
    input  wire         x3_v, input wire [511:0] x3_d, input wire [10:0] x3_tag, output wire x3_cr,
    output wire         ar_v, output wire [511:0] ar_d, input wire ar_cr,
    output wire [10:0] ar_tag, output wire [1:0] ar_source,
    output wire         fault
);
    ot_qwen_die_hub_identity #(.ENABLE_IDENTITY(ENABLE_IDENTITY), .NL(4), .LW(528)) u (.ck(ck), .rst_n(rst_n), .fck({fck3, fck2, fck1, fck0}),
        .l_i({l3_i, l2_i, l1_i, l0_i}), .l_o({l3_o, l2_o, l1_o, l0_o}), .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag),
        .x3_cr(x3_cr), .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .ar_tag(ar_tag), .ar_source(ar_source), .fault(fault));
endmodule
