`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE S81-PH selector, TILED (redesign pass 2026-10-06, DESIGN SIMPLIFICATION RULES).  sel_m1 (ot_s81ph_sel_core
// as one 5270 x 322 view) reached post-CTS -3300 ps with 4.8 ns of clock insertion across the slab and then died in
// GRT (OOM).  Split into hardened tiles clustered at the slab centre:
//
//   dsfd_selt_q   one select quarter per scan service (x4: two stacked on each side of the control tile; the E pair
//                 MY-mirrored): pin flop on the die lane, the lane decoder with the reconstructed index
//                 (ot_s81ph_sel_in, STG 0), one UNCHANGED ot_hdc_v41x_sel_slice with its three 256x256 line-memory
//                 macros, command pin flops, status outputs from flops, and the selected beats sent under credits.
//                 The slice serves the quarter its lane's header names (no crossbar: the qslot goes to the control).
//   dsfd_selt_c   the select control ot_hdc_v41x_sel_ctl (XD 2: one pin flop each side of every hop; PERM 1: tie
//                 quotas in quarter order of the slices' qslots), the segment header / k / tag / fault logic, a
//                 DM-entry landing FIFO per quarter (credits), the quarter-order output merger, the paced vd word.
//   ot_s81ph_sel_t the composition: the four quarter tiles abut the control tile (pin-to-pin hops, no station); the
//                 die lanes reach each quarter tile through LSTG die stations from the slab faces.
//
// Exactness: the select arithmetic is the unchanged slice + control; the control's waits and holdoffs grow by the
// added round trip (2 x XD each way, and the search unit's group round trip by 2 x XD) so every count it uses is as
// final / as fresh as in the native unit; the selection, its order, the replays and the fault bits are the native
// ones (bench tb_s81ph_sel, transaction compare against the native ot_hdc_v41x_sel).  A DONE / REP word still leaves
// only when every quarter is ready (the readiness is observed through the hop, after it is true).
// ---------------------------------------------------------------------------------------------------------------

// status bundle quarter -> control (SB bits)
//   [239:0] s_gc  [479:240] s_gf  [655:480] s_bc  [831:656] s_bf
//   [837:832] {s_ovf, s_emitted, s_done2, s_stopped, s_hfin, s_last}
//   [838] in_ready  [839] accept (a beat entered the slice)  [840] header  [850:841] header k  [858:851] header tag
//   [859] lane active  [861:860] lane qslot  [864:862] sticky {link, format, overrun}
`define SELT_SB 865
// command bundle control -> quarter (CB bits)
//   [15:0] c_T [23:16] c_Bt [24] c_fclr [28:25] c_cg [32:29] c_fg [33] c_ing [34] c_stop [35] c_p2 [36] c_p3
//   [37] c_rep [53:38] c_st [64:54] c_rem [65] c_hclr
`define SELT_CB 66
// beat quarter -> control: {last, ninf16, lv16, idx320, valid}
`define SELT_OB 354

// SAFE quarter tile line memory (sel_q SAFE, 2026-10-06): 256 lines x 592 b on SIX ot_sram_1r1w_128x256_m1_r2c2
// (455 ps SS clk->q vs 511; 2 depth banks x 3 width slices), every macro output registered AT the macro, the bank
// mux after the registers.  rdata is valid one edge later than ot_s81ph_sel_mem's (slice MREG 1 consumes it there).
module ot_s81ph_sel_mem2 (
    input  wire         clk,
    input  wire         we,
    input  wire [7:0]   waddr,
    input  wire [591:0] wdata,
    input  wire         re,
    input  wire [7:0]   raddr,
    output wire [591:0] rdata
);
    wire [767:0] wd = {176'd0, wdata};
    wire [767:0] rd [0:1];
    reg  [767:0] q [0:1];
    reg          b1, b2;
    genvar b, w;
    generate for (b = 0; b < 2; b = b + 1) begin : g_b
        for (w = 0; w < 3; w = w + 1) begin : g_w
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re && raddr[7] == b), .r_addr_in(raddr[6:0]),
                .rd_out(rd[b][256*w +: 256]), .w_ce_in(we && waddr[7] == b), .w_addr_in(waddr[6:0]),
                .wd_in(wd[256*w +: 256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00),
                .cr_sel(16'd0));
        end
        always @(posedge clk) q[b] <= rd[b];
    end endgenerate
    always @(posedge clk) begin if (re) b1 <= raddr[7]; b2 <= b1; end
    assign rdata = b2 ? q[1][591:0] : q[0][591:0];
endmodule

module dsfd_selt_q #(
    parameter integer DM = 4,                // landing FIFO depth at the control = initial credits
    parameter integer SAFE = 0               // 1: 128x256 macros, registered macro outputs, slice MREG 1 (dsfd_selt_q2)
) (
    input  wire [0:0]            ck,
    input  wire [0:0]            rst,        // die reset net (active low)
    input  wire [514:0]          lane,       // die lane {fault, live, data 512, valid}
    input  wire [`SELT_CB-1:0]   f_c,
    input  wire [0:0]            f_cr,
    output wire [`SELT_SB-1:0]   t_s,
    output wire [`SELT_OB-1:0]   t_o
);
    localparam integer W = 16, IW = 20, K = 512, AW = 8, KW = 10, CB = 11, EW = 37, GW = CB + 4;
    localparam integer CW = $clog2(DM + 1);
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // lane: pin flop (inside ot_s81ph_sel_in, STG 0) + decode
    wire b_v, b_last, h_v, act, e_fmt, e_orphan, e_link;
    wire [15:0] b_lv; wire [255:0] b_val; wire [319:0] b_idx; wire [1:0] b_q, h_q, act_q; wire [9:0] h_k; wire [7:0] h_tag;
    ot_s81ph_sel_in #(.STG(0)) u_in (.clk(ck[0]), .rst_n(rst_n), .lane(lane), .b_v(b_v), .b_lv(b_lv), .b_val(b_val),
        .b_idx(b_idx), .b_last(b_last), .b_q(b_q), .h_v(h_v), .h_k(h_k), .h_tag(h_tag), .h_q(h_q), .act(act),
        .act_q(act_q), .e_fmt(e_fmt), .e_orphan(e_orphan), .e_link(e_link));
    // beat register in front of the slice (the native crossbar register)
    reg x_v, x_last; reg [15:0] x_lv; reg [255:0] x_val; reg [319:0] x_idx;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= b_v;
    always @(posedge ck[0]) begin x_last <= b_last; x_lv <= b_lv; x_val <= b_val; x_idx <= b_idx; end
    // command pin flops
    reg [`SELT_CB-1:0] cq; reg crq;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) begin cq <= {`SELT_CB{1'b0}}; crq <= 1'b0; end
                                            else begin cq <= f_c; crq <= f_cr[0]; end
    // the slice (unchanged) and its line memory
    wire s_rdy, o_valid, o_last; reg o_ready;
    wire [W-1:0] o_lv, o_ninf; wire [W*16-1:0] o_val; wire [W*IW-1:0] o_idx;
    wire [16*GW-1:0] s_gc, s_gf; wire [16*CB-1:0] s_bc, s_bf;
    wire s_last, s_hfin, s_stopped, s_done2, s_emitted, s_ovf;
    wire m_we, m_re; wire [AW-1:0] m_wa, m_ra; wire [W*EW-1:0] m_wd, m_rd;
    ot_hdc_v41x_sel_slice #(.W(W), .IW(IW), .K(K), .AW(AW), .DG(8), .OD(4), .KW(KW), .CB(CB), .MREG(SAFE)) u_s (
        .clk(ck[0]), .rst_n(rst_n), .in_valid(x_v), .in_ready(s_rdy), .in_last(x_last), .in_lv(x_lv), .in_val(x_val),
        .in_idx(x_idx), .c_T(cq[15:0]), .c_Bt(cq[23:16]), .c_fclr(cq[24]), .c_cg(cq[28:25]), .c_fg(cq[32:29]),
        .c_ing(cq[33]), .c_stop(cq[34]), .c_p2(cq[35]), .c_p3(cq[36]), .c_rep(cq[37]), .c_st(cq[53:38]),
        .c_rem(cq[64:54]), .c_hclr(cq[65]), .s_gc(s_gc), .s_gf(s_gf), .s_bc(s_bc), .s_bf(s_bf), .s_last(s_last),
        .s_hfin(s_hfin), .s_stopped(s_stopped), .s_done2(s_done2), .s_emitted(s_emitted), .s_ovf(s_ovf),
        .s_nhead(), .s_n2(), .s_n3(), .mem_we(m_we), .mem_waddr(m_wa), .mem_wdata(m_wd), .mem_re(m_re),
        .mem_raddr(m_ra), .mem_rdata(m_rd), .out_valid(o_valid), .out_ready(o_ready), .out_last(o_last),
        .out_lv(o_lv), .out_val(o_val), .out_idx(o_idx), .out_ninf(o_ninf));
    generate if (SAFE != 0) begin : g_m2
        ot_s81ph_sel_mem2 u_mem (.clk(ck[0]), .we(m_we), .waddr(m_wa), .wdata(m_wd), .re(m_re), .raddr(m_ra),
            .rdata(m_rd));
    end else begin : g_m1
        ot_s81ph_sel_mem u_mem (.clk(ck[0]), .we(m_we), .waddr(m_wa), .wdata(m_wd), .re(m_re), .raddr(m_ra),
            .rdata(m_rd));
    end endgenerate
    // faults (sticky, fail closed): overrun = a beat while the slice is not ready, or a beat / rebase with no header
    reg [2:0] flt;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) flt <= 3'd0;
        else flt <= flt | {e_link, e_fmt, (x_v & ~s_rdy) | e_orphan};
    // status from flops
    reg [`SELT_SB-1:0] sq;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) sq <= {`SELT_SB{1'b0}};
        else sq <= {flt, act_q, act, h_tag, h_k, h_v, x_v & s_rdy, s_rdy,
                    s_ovf, s_emitted, s_done2, s_stopped, s_hfin, s_last, s_bf, s_bc, s_gf, s_gc};
    assign t_s = sq;
    // selected beats under credits
    reg [CW-1:0] crd;
    always @(*) o_ready = crd != 0;
    reg [`SELT_OB-1:0] oq;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) begin crd <= DM[CW-1:0]; oq <= {`SELT_OB{1'b0}}; end
        else begin
            crd <= crd + (crq ? 1'b1 : 1'b0) - ((o_valid && o_ready) ? 1'b1 : 1'b0);
            oq <= {o_last, o_ninf, o_lv, o_idx, o_valid && o_ready};
        end
    assign t_o = oq;
endmodule

// SAFE quarter tile master (same ports as dsfd_selt_q)
module dsfd_selt_q2 #(parameter integer DM = 4) (
    input  wire [0:0]            ck,
    input  wire [0:0]            rst,
    input  wire [514:0]          lane,
    input  wire [`SELT_CB-1:0]   f_c,
    input  wire [0:0]            f_cr,
    output wire [`SELT_SB-1:0]   t_s,
    output wire [`SELT_OB-1:0]   t_o
);
    dsfd_selt_q #(.DM(DM), .SAFE(1)) u_q (.ck(ck), .rst(rst), .lane(lane), .f_c(f_c), .f_cr(f_cr), .t_s(t_s), .t_o(t_o));
endmodule

module dsfd_selt_c #(
    parameter integer DM   = 4,
    parameter integer PACE = 2
) (
    input  wire [0:0]                ck,
    input  wire [0:0]                rst,
    input  wire [4*`SELT_SB-1:0]     f_s,    // per quarter tile (lane 0 SW, 1 SE, 2 NW, 3 NE)
    output wire [4*`SELT_CB-1:0]     t_c,
    input  wire [4*`SELT_OB-1:0]     f_o,
    output wire [3:0]                t_cr,
    output wire [513:0]              vd,
    output wire [0:0]                vf
);
    localparam integer Q = 4, W = 16, IW = 20, K = 512, KW = 10, CB = 11, GW = CB + 4, SB = `SELT_SB, OB = `SELT_OB;
    localparam integer DW = OB - 1;          // landing entry {last, ninf, lv, idx}
    localparam integer CW = $clog2(DM + 1);
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin flops
    reg [Q*SB-1:0] sq; reg [Q*OB-1:0] oq;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) sq <= {Q*SB{1'b0}}; else sq <= f_s;
    always @(posedge ck[0]) oq <= f_o;
    // unpack
    wire [Q*16*GW-1:0] s_gc, s_gf; wire [Q*16*CB-1:0] s_bc, s_bf;
    wire [Q-1:0] s_last, s_hfin, s_stopped, s_done2, s_emitted, s_ovf, s_ready, s_acc, h_v, act;
    wire [Q*10-1:0] h_k; wire [Q*8-1:0] h_tag; wire [Q*2-1:0] act_q; wire [Q*3-1:0] lflt;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_u
        wire [SB-1:0] x = sq[SB * g +: SB];
        assign s_gc[16*GW*g +: 16*GW] = x[239:0];
        assign s_gf[16*GW*g +: 16*GW] = x[479:240];
        assign s_bc[16*CB*g +: 16*CB] = x[655:480];
        assign s_bf[16*CB*g +: 16*CB] = x[831:656];
        assign {s_ovf[g], s_emitted[g], s_done2[g], s_stopped[g], s_hfin[g], s_last[g]} = x[837:832];
        assign s_ready[g] = x[838]; assign s_acc[g] = x[839]; assign h_v[g] = x[840];
        assign h_k[10*g +: 10] = x[850:841]; assign h_tag[8*g +: 8] = x[858:851];
        assign act[g] = x[859]; assign act_q[2*g +: 2] = x[861:860]; assign lflt[3*g +: 3] = x[864:862];
    end endgenerate
    // segment header state, faults
    reg        seg_open;
    reg [KW-1:0] seg_k, k_r;
    reg [7:0]  seg_tag;
    reg [4:0]  flt;
    reg        e_coll, e_kt, kld_r;
    reg [2*Q-1:0] qs;                        // the quarter each slice serves (from its lane's header)
    reg        coll_n;
    integer q, s;
    always @(*) begin
        coll_n = 1'b0;
        for (s = 0; s < Q; s = s + 1)
            for (q = s + 1; q < Q; q = q + 1)
                if (act[s] && act[q] && act_q[2*s +: 2] == act_q[2*q +: 2]) coll_n = 1'b1;
    end
    // ---- the select control (native, XD 2, PERM 1)
    wire [15:0] c_T, c_st; wire [7:0] c_Bt; wire [3:0] c_cg, c_fg;
    wire c_fclr, c_ing, c_stop, c_p2, c_p3, c_rep, c_hclr, rep_req, ovf, busy;
    wire [Q*(KW+1)-1:0] c_rem;
    ot_hdc_v41x_sel_ctl #(.Q(Q), .K(K), .KW(KW), .CB(CB), .XD(2), .PERM(1)) u_ctl (
        .clk(ck[0]), .rst_n(rst_n), .k_in(k_r), .k_ld(kld_r), .qs(qs),
        .s_gc(s_gc), .s_gf(s_gf), .s_bc(s_bc), .s_bf(s_bf),
        .s_last(s_last), .s_hfin(s_hfin), .s_stopped(s_stopped), .s_done2(s_done2), .s_emitted(s_emitted),
        .s_ovf(s_ovf),
        .c_T(c_T), .c_Bt(c_Bt), .c_fclr(c_fclr), .c_cg(c_cg), .c_fg(c_fg), .c_ing(c_ing), .c_stop(c_stop),
        .c_p2(c_p2), .c_p3(c_p3), .c_rep(c_rep), .c_st(c_st), .c_rem(c_rem), .c_hclr(c_hclr),
        .rep_req(rep_req), .ovf(ovf), .busy(busy));
    // command bundles, one per tile, from flops at the pins
    reg [`SELT_CB-1:0] cmd [0:Q-1];
    generate for (g = 0; g < Q; g = g + 1) begin : g_c
        always @(posedge ck[0] or negedge rst_n)
            if (!rst_n) cmd[g] <= {`SELT_CB{1'b0}};
            else cmd[g] <= {c_hclr, c_rem[(KW+1)*g +: KW+1], c_st, c_rep, c_p3, c_p2, c_stop, c_ing, c_fg, c_cg, c_fclr,
                            c_Bt, c_T};
        assign t_c[`SELT_CB * g +: `SELT_CB] = cmd[g];
    end endgenerate
    // ---- landing FIFOs (head at entry 0), credits
    reg  [DW-1:0] lq [0:Q-1][0:DM-1];
    reg  [CW-1:0] lc [0:Q-1];
    reg  [Q-1:0]  lpop;
    wire [Q-1:0]  lv;
    integer l, e;
    generate for (g = 0; g < Q; g = g + 1) begin : g_l
        assign lv[g] = lc[g] != 0;
    end endgenerate
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) for (l = 0; l < Q; l = l + 1) lc[l] <= {CW{1'b0}};
        else for (l = 0; l < Q; l = l + 1) lc[l] <= lc[l] + (oq[OB * l] ? 1'b1 : 1'b0) - (lpop[l] ? 1'b1 : 1'b0);
    always @(posedge ck[0])
        for (l = 0; l < Q; l = l + 1)
            for (e = 0; e < DM; e = e + 1) begin
                if (lpop[l]) begin
                    if (oq[OB * l] && e == lc[l] - 1) lq[l][e] <= oq[OB * l + 1 +: DW];
                    else if (e + 1 < DM) lq[l][e] <= lq[l][(e + 1) % DM];
                end else if (oq[OB * l] && e == lc[l]) lq[l][e] <= oq[OB * l + 1 +: DW];
            end
    reg [Q-1:0] crq;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) crq <= {Q{1'b0}}; else crq <= lpop;
    assign t_cr = crq;
    // ---- output merger: quarter cq is served by the tile whose lane header named it
    reg        ovf_seen;
    reg  [1:0] rep_pend;
    reg        rep_n;
    reg  [1:0] cq;
    reg        done_pend;
    reg  [9:0] cnt;
    reg  [4:0] flt_rep;
    reg  [$clog2(PACE+1)-1:0] pc;
    wire       slot = (pc == 0);
    wire [4:0] flt_new = flt & ~flt_rep;
    reg  [1:0] ts;                           // the tile serving quarter cq
    always @(*) begin
        ts = cq;
`ifndef OT_S81PH_MUT2
        for (s = 0; s < Q; s = s + 1) if (qs[2*s +: 2] == cq) ts = s[1:0];
`endif
    end
`ifdef OT_S81PH_MUT3
    wire [1:0] tsel = ts ^ 2'd1;
`else
    wire [1:0] tsel = ts;
`endif
    wire [DW-1:0] hd = lq[tsel][0];
    wire take = slot && !(|flt_new) && rep_pend == 0 && !done_pend && lv[tsel];
    always @(*) begin lpop = {Q{1'b0}}; if (take) lpop[tsel] = 1'b1; end
    wire hd_last = hd[DW-1];
    wire [15:0] hd_ninf = hd[DW-2 -: 16];
    wire [15:0] hd_lv = hd[335:320];
    wire [319:0] hd_idx = hd[319:0];
    function automatic [4:0] pop16(input [15:0] x);
        integer j; begin pop16 = 0; for (j = 0; j < 16; j = j + 1) pop16 = pop16 + x[j]; end
    endfunction
    reg        o_v;
    reg [511:0] o_d;
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin
            seg_open <= 1'b0; seg_k <= {KW{1'b0}}; seg_tag <= 8'd0; flt <= 5'd0; e_coll <= 1'b0; e_kt <= 1'b0;
            k_r <= {KW{1'b0}}; kld_r <= 1'b0; qs <= {2'd3, 2'd2, 2'd1, 2'd0};
            ovf_seen <= 1'b0; rep_pend <= 2'd0; rep_n <= 1'b0; cq <= 2'd0; done_pend <= 1'b1; cnt <= 10'd0;
            flt_rep <= 5'd0; pc <= 0; o_v <= 1'b0; o_d <= 512'd0;
        end else begin
            kld_r <= |s_acc;
            if (|s_acc) k_r <= seg_k;
            e_coll <= coll_n;
            for (s = 0; s < Q; s = s + 1) if (h_v[s]) qs[2*s +: 2] <= act_q[2*s +: 2];
            e_kt <= 1'b0;
            begin : hdr
                integer t; reg op; reg [KW-1:0] kk; reg [7:0] tt;
                op = seg_open; kk = seg_k; tt = seg_tag;
                for (t = 0; t < Q; t = t + 1)
                    if (h_v[t]) begin
                        if (!op) begin op = 1'b1; kk = h_k[10*t +: 10]; tt = h_tag[8*t +: 8]; end
                        else if (h_k[10*t +: 10] != kk || h_tag[8*t +: 8] != tt) e_kt <= 1'b1;
                    end
                seg_open <= op; seg_k <= kk; seg_tag <= tt;
            end
            begin : fl
                reg [2:0] lf; lf = lflt[2:0] | lflt[5:3] | lflt[8:6] | lflt[11:9];
                flt <= flt | {1'b0, lf[2], e_kt, lf[1] | e_coll, lf[0]};
            end
            if (ovf) ovf_seen <= 1'b1;
            pc <= (pc == PACE - 1) ? 0 : pc + 1'b1;
            o_v <= 1'b0;
            if (rep_req) rep_pend <= rep_pend + 1'b1;
            if (slot) begin
                if (|flt_new) begin
                    o_v <= 1'b1; o_d <= {4'd5, seg_tag, 484'd0, flt, 11'd0};
                    flt_rep <= flt;
                end else if (rep_pend != 0 && &s_ready) begin
                    o_v <= 1'b1; o_d <= {4'd7, seg_tag, 499'd0, rep_n};
                    rep_n <= ~rep_n;
                    rep_pend <= rep_pend - 1'b1 + (rep_req ? 1'b1 : 1'b0);
                end else if (take) begin
                    o_v <= 1'b1;
                    o_d <= {4'd3, seg_tag, 145'd0, hd_last, cq, hd_ninf, hd_lv, hd_idx};
                    cnt <= cnt + pop16(hd_lv);
                    if (hd_last) begin
                        cq <= cq + 1'b1;
                        if (cq == 2'd3) done_pend <= 1'b1;
                    end
                end else if (done_pend && &s_ready) begin
                    o_v <= 1'b1; o_d <= {4'd4, seg_tag, 484'd0, flt, ovf_seen, cnt};
                    done_pend <= 1'b0; cnt <= 10'd0; ovf_seen <= 1'b0; seg_open <= 1'b0; rep_n <= 1'b0;
                end
            end
        end
    end
    reg [513:0] vd_q;
    always @(posedge ck[0]) vd_q <= {o_d, o_v & rst_n, rst_n};
    assign vd = vd_q;
    ot_fwd_clk_inv u_vf (.a(ck[0]), .y(vf[0]));
endmodule

// composition reference (bench and die generator): lanes {NE, NW, SE, SW} as dsfd_bk_selector
module ot_s81ph_sel_t #(
    parameter integer SAFE = 0,              // 1: dsfd_selt_q2 quarter tiles
    parameter integer LSTG = 5,              // die stations on each lane from the slab face to its quarter tile
    parameter integer DM   = 4,
    parameter integer PACE = 2
) (
    input  wire          ck, rst,
    input  wire [4*515-1:0] lanes,           // {NE, NW, SE, SW}
    output wire [513:0]  vd,
    output wire          vf
);
    localparam integer Q = 4, SB = `SELT_SB, CB = `SELT_CB, OB = `SELT_OB;
    wire [Q*SB-1:0] ts; wire [Q*CB-1:0] tc; wire [Q*OB-1:0] to; wire [Q-1:0] tcr;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_q
        reg [514:0] st [0:LSTG];
        integer h;
        always @(*) st[0] = lanes[515 * g +: 515];
        always @(posedge ck) for (h = 1; h <= LSTG; h = h + 1) st[h] <= st[h-1];
        dsfd_selt_q #(.DM(DM), .SAFE(SAFE)) u_q (.ck(ck), .rst(rst), .lane(st[LSTG]), .f_c(tc[CB * g +: CB]), .f_cr(tcr[g]),
            .t_s(ts[SB * g +: SB]), .t_o(to[OB * g +: OB]));
    end endgenerate
    dsfd_selt_c #(.DM(DM), .PACE(PACE)) u_c (.ck(ck), .rst(rst), .f_s(ts), .t_c(tc), .f_o(to), .t_cr(tcr), .vd(vd),
        .vf(vf));
endmodule
