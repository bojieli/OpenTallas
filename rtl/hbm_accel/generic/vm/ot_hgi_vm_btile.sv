`timescale 1ns/1ps
`default_nettype none
// ot_hgi_vm_btile: one bank tile of ot_hgi_vm_tunit (el1011-hbm-hcvm/vm, 2026-10-11), a hardened sub-element with its
// own clock tree (the flat tunit's hgi_vm_tb-ee633319d stalled in CTS hold repair at -228 ps on 51k endpoints: one clock
// tree over 1.4 x 1.08 mm and 64 macros).  Defaults = the die configuration (NC 9, 3 read + 3 W2 lane groups, LQ 32);
// the hard view is built at the defaults and instantiated without parameter overrides (the parent passes them only in
// simulation).  The bank id is a port (tied at the parent), so one master serves all 32 banks.
// Contents: the bank's two VM macros (lo / hi, one column) + its read lanes g*32+b (pin flop, LQ+8-deep row queue) +
// its W2 lanes g*32+b (pin flop, one 64x512 SRAM queue each, raw capture flop) + client select / SECDED encode (cs, c2)
// + macro input registers + read raw capture / decode + client return (u) + lane responses (rr).
// Timing (gi at the tile pins in cycle T-1 = the parent's r1; the tile's pin flop is the down tree's r2, cycle T): lane
// pops at T, macro inputs at T+3, raw capture T+5, decode T+6, u / rr T+7; rq_cr / w2q_cr T+1, w2q_done T+5; the DMA
// lane's encoded word arrives one edge before its pin flop (the data line's last stage); lane events (rqh / w2h) leave one edge after the pin
// flop (the parent adds the remaining relays to the hub).
module ot_hgi_vm_btile #(
    parameter integer NC = 9,
    parameter integer NGR = 3,
    parameter integer NGW = 3,
    parameter integer LQ = 32,
    parameter integer MUT = 0
) (
    input  wire                          clk,
    input  wire                          rst_n,     // regional reset copy from the parent's relay
    input  wire [4:0]                    bid,       // bank id (tied)
    input  wire [2*((NC>1)?$clog2(NC):1)+7:0] gi,   // decision {rv, rc, wv, wc, lv, lg 2, qv, qg 2}
    input  wire [NC*274-1:0]             lanes,     // client lanes {row 10, wdata 256, word mask 8} (group relay)
    input  wire                          w_hit,     // DMA lane b at its last data-line stage
    input  wire [9:0]                    w_row,
    input  wire [311:0]                  w_enc,
    input  wire [7:0]                    w_wm,
    input  wire [(NGR>0?NGR:1)*16-1:0]   rq_in,
    output wire [(NGR>0?NGR:1)-1:0]      rqh_v,
    output wire [(NGR>0?NGR:1)-1:0]      rqh_m,
    output wire [(NGR>0?NGR:1)-1:0]      rq_cr,
    output wire [(NGR>0?NGR:1)*257-1:0]  rr,
    input  wire [(NGW>0?NGW:1)*280-1:0]  w2q_in,
    output wire [(NGW>0?NGW:1)-1:0]      w2h_v,
    output wire [(NGW>0?NGW:1)-1:0]      w2h_m,
    output wire [(NGW>0?NGW:1)-1:0]      w2q_cr,
    output wire [(NGW>0?NGW:1)-1:0]      w2q_done,
    output reg                           u_v,
    output reg  [((NC>1)?$clog2(NC):1)-1:0] u_c,
    output reg  [255:0]                  u_d,
    output reg  [3:0]                    u_ce,
    output reg                           u_ue
);
    localparam integer CW = (NC > 1) ? $clog2(NC) : 1, GW = 2 * CW + 8, LW = 274, LRD = LQ + 8;
    // ---------------------------------------------------------------- (39,32) SECDED, identical to ot_hgi_vm_core
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [32*7-1:0] cols_all(input integer dummy);
        integer i; reg [32*7-1:0] r;
        begin r = '0; for (i = 0; i < 32; i = i + 1) r[i*7 +: 7] = colv(i); cols_all = r; end
    endfunction
    localparam [32*7-1:0] COLS = cols_all(0);
    function automatic [7*32-1:0] rows_all(input integer dummy);
        integer i, j; reg [7*32-1:0] r;
        begin r = '0; for (j = 0; j < 7; j = j + 1) for (i = 0; i < 32; i = i + 1) r[j*32 + i] = COLS[i*7 + j]; rows_all = r; end
    endfunction
    localparam [7*32-1:0] ROWM = rows_all(0);
    function automatic [6:0] chk(input [31:0] d);
        integer j; reg [6:0] c;
        begin for (j = 0; j < 7; j = j + 1) c[j] = ^(d & ROWM[j*32 +: 32]); chk = c; end
    endfunction
    function automatic [311:0] enc8(input [255:0] d);
        integer k; reg [311:0] r;
        begin for (k = 0; k < 8; k = k + 1) r[k*39 +: 39] = {chk(d[k*32 +: 32]), d[k*32 +: 32]}; enc8 = r; end
    endfunction
    function automatic [33:0] dec(input [38:0] w);
        reg [6:0] syn; integer i; reg [31:0] d; reg hit;
        begin
            d = w[31:0]; syn = chk(w[31:0]) ^ w[38:32]; hit = 1'b0;
            if (syn != 7'd0) begin
                for (i = 0; i < 32; i = i + 1) if (syn == COLS[i*7 +: 7]) begin d[i] = ~d[i]; hit = 1'b1; end
                if (syn == 7'd1 || syn == 7'd2 || syn == 7'd4 || syn == 7'd8 || syn == 7'd16 || syn == 7'd32 || syn == 7'd64) hit = 1'b1;
            end
            dec = {(syn != 7'd0) && !hit, (syn != 7'd0) && hit, (MUT == 1) ? w[31:0] : d};
        end
    endfunction

    // pin flops: every tile input lands in a flop (the down tree's r2 stage and the DMA data line's last stage live
    // here, next to the bank), no logic between a pin and its flop
    reg [GW-1:0] gq; reg [NC*LW-1:0] lq; reg wh_q; reg [9:0] wr_q; reg [311:0] we_q; reg [7:0] wm_q;
    // round 2 (hgi_vm_bt{a,b}-a7bf28890 NEEDS_RTL: bid pin -> em compare -134 ps TT): the bank-id strap lands in a pin flop
    reg [4:0] bid_q;
    always @(posedge clk) bid_q <= bid;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin gq <= '0; wh_q <= 1'b0; end else begin gq <= gi; wh_q <= w_hit; end
    always @(posedge clk) begin lq <= lanes; wr_q <= w_row; we_q <= w_enc; wm_q <= w_wm; end
    wire          d_rv = gq[GW-1],  d_wv = gq[GW-2-CW];
    wire [CW-1:0] d_rc = gq[GW-2 -: CW], d_wc = gq[GW-3-CW -: CW];
    wire          d_lv = gq[5], d_qv = gq[2];
    wire [1:0]    d_lg = gq[4:3], d_qg = gq[1:0];
    wire [LW-1:0] lr = lq[d_rc*LW +: LW], lw = lq[d_wc*LW +: LW];
    // client path: select + encode (cs) -> c2
    reg cs_re, cs_we, c2_re, c2_we; reg [CW-1:0] cs_rc, c2_rc; reg [9:0] cs_ra, cs_wa, c2_ra, c2_wa;
    reg [311:0] cs_wd, c2_wd; reg [7:0] cs_wm, c2_wm;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin cs_re <= 1'b0; cs_we <= 1'b0; c2_re <= 1'b0; c2_we <= 1'b0; end
        else begin cs_re <= d_rv; cs_we <= d_wv; c2_re <= cs_re; c2_we <= cs_we; end
    always @(posedge clk) begin
        cs_rc <= d_rc; cs_ra <= lr[LW-1 -: 10];
        cs_wa <= lw[LW-1 -: 10]; cs_wd <= enc8(lw[263:8]); cs_wm <= lw[7:0];
        c2_rc <= cs_rc; c2_ra <= cs_ra; c2_wa <= cs_wa; c2_wd <= cs_wd; c2_wm <= cs_wm;
    end
    // ---- read lanes: pin flop, event flop {v, match} toward the hub, local row queue popped on the decision
    reg l1_v, l2_v; reg [1:0] l1_g, l2_g; reg [9:0] l1_ra, l2_ra;
    wire [4*10-1:0] lhead;
    for (genvar g = 0; g < 4; g = g + 1) begin : g_rl
        if (g < NGR) begin : g_on
            reg p0_v; reg [14:0] p0_s; reg ev, em; reg crq;
            always @(posedge clk or negedge rst_n) if (!rst_n) p0_v <= 1'b0; else p0_v <= rq_in[g*16 + 15];
            always @(posedge clk) p0_s <= rq_in[g*16 +: 15];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin ev <= 1'b0; em <= 1'b0; end
                else begin ev <= p0_v; em <= p0_s[4:0] == bid_q; end
            assign rqh_v[g] = ev; assign rqh_m[g] = em;
            reg [9:0] q [0:LRD-1]; reg [$clog2(LRD)-1:0] wp, rp;
            wire pop = d_lv && d_lg == 2'(g);
            always @(posedge clk) if (p0_v) q[wp] <= p0_s[14:5];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin wp <= '0; rp <= '0; crq <= 1'b0; end
                else begin
                    if (p0_v) wp <= (wp == LRD - 1) ? '0 : wp + 1'b1;
                    if (pop) rp <= (rp == LRD - 1) ? '0 : rp + 1'b1;
                    crq <= pop;
                end
            assign lhead[g*10 +: 10] = q[rp]; assign rq_cr[g] = crq;
        end else begin : g_off
            assign lhead[g*10 +: 10] = 10'd0;
        end
    end
    if (NGR == 0) begin : g_norl
        assign rqh_v = 1'b0; assign rqh_m = 1'b0; assign rq_cr = 1'b0; assign rr = '0;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin l1_v <= 1'b0; l2_v <= 1'b0; end
        else begin l1_v <= d_lv; l2_v <= l1_v; end
    always @(posedge clk) begin l1_g <= d_lg; l2_g <= l1_g; l1_ra <= lhead[d_lg*10 +: 10]; l2_ra <= l1_ra; end
    // ---- W2 write lanes: pin flop, event flop {v, match}, local SRAM queue read on the decision
    reg b1_v, b2_v; reg [1:0] b1_g, b2_g;
    wire [4*330-1:0] qraw;
    for (genvar g = 0; g < 4; g = g + 1) begin : g_w2
        if (g < NGW) begin : g_on
            reg p0_v; reg [278:0] p0_d; reg ev, em; reg crq; reg [3:0] dnl;
            always @(posedge clk or negedge rst_n) if (!rst_n) p0_v <= 1'b0; else p0_v <= w2q_in[g*280 + 279];
            always @(posedge clk) p0_d <= w2q_in[g*280 +: 279];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin ev <= 1'b0; em <= 1'b0; end
                else begin ev <= p0_v; em <= p0_d[264 +: 5] == bid_q; end
            assign w2h_v[g] = ev; assign w2h_m[g] = em;
            reg [5:0] wp, rp; wire pop = d_qv && d_qg == 2'(g);
            // round 2 (b2_g -> m_wd -92 ps TT: 4:1 select + SECDED encode + priority mux in one cycle): the queue holds the
            // ENCODED word {row 10, enc 312, mask 8} (encode on the write side, pin flop -> encode -> macro), so the read
            // side is raw capture -> one-hot AND-OR select -> m_wd.  Macro address pins through a hold-delay stage
            // (rp / wp -> u_q addr FF hold -42.85 / -21.80 ps: macro clock pin later than the pointer flops).
            wire [511:0] rd; reg [329:0] raw; wire [5:0] rpd, wpd;
            wire [511:0] wdx = {182'd0, p0_d[264 + 5 +: 10], enc8(p0_d[8 +: 256]), p0_d[7:0]};
            ot_hdly #(.W(6), .N(2)) u_hr (.a(rp), .y(rpd));
            ot_hdly #(.W(6), .N(2)) u_hw (.a(wp), .y(wpd));
            ot_sram_1r1w_64x512_m1_r2c2 u_q (.clk(clk), .r_ce_in(pop), .r_addr_in(rpd), .rd_out(rd),
                .w_ce_in(p0_v), .w_addr_in(wpd), .wd_in(wdx), .w_mask_in({512{1'b1}}),
                .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
            always @(posedge clk) if (b1_v && b1_g == 2'(g)) raw <= rd[329:0];      // raw capture at the macro
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin wp <= '0; rp <= '0; crq <= 1'b0; dnl <= '0; end
                else begin
                    if (p0_v) wp <= wp + 1'b1;
                    if (pop) rp <= rp + 1'b1;
                    crq <= pop; dnl <= {dnl[2:0], crq};
                end
            assign qraw[g*330 +: 330] = raw; assign w2q_cr[g] = crq; assign w2q_done[g] = dnl[3];
        end else begin : g_off
            assign qraw[g*330 +: 330] = '0;
        end
    end
    if (NGW == 0) begin : g_now2
        assign w2h_v = 1'b0; assign w2h_m = 1'b0; assign w2q_cr = 1'b0; assign w2q_done = 1'b0;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin b1_v <= 1'b0; b2_v <= 1'b0; end
        else begin b1_v <= d_qv; b2_v <= b1_v; end
    always @(posedge clk) begin b1_g <= d_qg; b2_g <= b1_g; end
    // one-hot select, kept copies per 55-bit slice (no 330-load select net)
    wire [329:0] qsel;
    for (genvar sl = 0; sl < 6; sl = sl + 1) begin : g_qs
        (* keep = "true" *) reg [3:0] oh;
        always @(posedge clk) for (integer k = 0; k < 4; k = k + 1) oh[k] <= (b1_g == 2'(k));
        assign qsel[sl*55 +: 55] = (qraw[0*330 + sl*55 +: 55] & {55{oh[0]}}) | (qraw[1*330 + sl*55 +: 55] & {55{oh[1]}}) |
                                   (qraw[2*330 + sl*55 +: 55] & {55{oh[2]}}) | (qraw[3*330 + sl*55 +: 55] & {55{oh[3]}});
    end
    // ---- macro input registers (next to the macros): client > DMA lane > W2 lane (the unit's order)
    reg m_re, m_we; reg [9:0] m_ra, m_wa; reg [311:0] m_wd; reg [7:0] m_wm;
    reg rp1, rp2, rp3, d_v; reg k1, k2, k3, d_k; reg [CW-1:0] rc1, rc2, rc3, d_c; reg [1:0] rg1, rg2, rg3, d_g;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin m_re <= 1'b0; m_we <= 1'b0; rp1 <= 1'b0; end
        else begin m_re <= c2_re | l2_v; m_we <= c2_we | wh_q | b2_v; rp1 <= c2_re | l2_v; end
    always @(posedge clk) begin
        m_ra <= c2_re ? c2_ra : l2_ra;
        k1 <= c2_re; rc1 <= c2_rc; rg1 <= l2_g;
        if (c2_we) begin m_wa <= c2_wa; m_wd <= c2_wd; m_wm <= c2_wm; end
        else if (wh_q) begin m_wa <= wr_q; m_wd <= we_q; m_wm <= wm_q | {8{MUT == 4}}; end
        else begin m_wa <= qsel[320 +: 10]; m_wd <= qsel[8 +: 312]; m_wm <= qsel[7:0]; end
    end
    wire [311:0] wme;
    for (genvar w = 0; w < 8; w = w + 1) begin : g_wm
        assign wme[w*39 +: 39] = {39{m_wm[w]}};
    end
    wire [511:0] wdx = {200'd0, m_wd}, wmx = {200'd0, wme}; wire [511:0] rd;
    ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(clk), .r_ce_in(m_re), .r_addr_in(m_ra), .rd_out(rd[255:0]),
        .w_ce_in(m_we), .w_addr_in(m_wa), .wd_in(wdx[255:0]), .w_mask_in(wmx[255:0]),
        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(clk), .r_ce_in(m_re), .r_addr_in(m_ra), .rd_out(rd[511:256]),
        .w_ce_in(m_we), .w_addr_in(m_wa), .wd_in(wdx[511:256]), .w_mask_in(wmx[511:256]),
        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // read return: macro edge (rp2) -> raw capture (no logic before it) -> decode (d) -> client return (u) / lane rr
    // round 2 (u_d -> u_d pins -44.89 / -43.42 ps TT; raw -> d_ce -25.39 ps): the decode register is duplicated per
    // destination (d_d toward the client-return pins, d_r toward the lane rr pins, so neither drags the other), and the
    // corrected-word count is a popcount of 8 registered flags in the u stage instead of in the decode cycle.
    reg [311:0] raw; reg [255:0] d_d; (* keep = "true" *) reg [255:0] d_r; reg [7:0] d_cf; reg d_ue;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rp2 <= 1'b0; rp3 <= 1'b0; d_v <= 1'b0; u_v <= 1'b0; end
        else begin rp2 <= rp1; rp3 <= rp2; d_v <= rp3; u_v <= d_v && d_k; end
    always @(posedge clk) begin
        k2 <= k1; k3 <= k2; d_k <= k3; rc2 <= rc1; rc3 <= rc2; d_c <= rc3; rg2 <= rg1; rg3 <= rg2; d_g <= rg3;
        if (rp2) raw <= rd[311:0];
        begin : dc
            reg [33:0] x; reg u;
            u = 1'b0;
            for (integer q = 0; q < 8; q = q + 1) begin
                x = dec(raw[q*39 +: 39]); d_d[q*32 +: 32] <= x[31:0]; d_r[q*32 +: 32] <= x[31:0];
                d_cf[q] <= rp3 && x[32]; u = u | x[33];
            end
            d_ue <= rp3 && u;
        end
        begin : pc
            reg [3:0] n; n = 4'd0;
            for (integer q = 0; q < 8; q = q + 1) n = n + {3'd0, d_cf[q]};
            u_ce <= d_v ? n : 4'd0;
        end
        u_c <= d_c; u_d <= d_d; u_ue <= d_v && d_ue;
    end
    // lane read responses, registered at the bank
    for (genvar g = 0; g < NGR; g = g + 1) begin : g_rr
        reg rv; reg [255:0] rdat;
        always @(posedge clk or negedge rst_n) if (!rst_n) rv <= 1'b0;
            else rv <= d_v && !d_k && ((MUT == 5) ? (g == 0) : (d_g == 2'(g)));
        always @(posedge clk) rdat <= d_r;
        assign rr[g*257 +: 257] = {rv, rdat};
    end
endmodule
`default_nettype wire
