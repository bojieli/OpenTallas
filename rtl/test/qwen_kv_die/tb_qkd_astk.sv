`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// el1013-qwen-kvstrips 2026-10-13: exact bench of the aggregator strip masters (qkd_astk_pv / _ep / _ex / _zn / _ctl in
// the die wiring ot_qkd_astk_strip) against the golden aggregator ot_qkd_astk_gold = ot_qwen_nearhbm_attn_stack_h with
// its row engines replaced by ports (tools/qwen_kv_die/astk_gold_gen.py).  Both sides are driven by the same engine
// model (ot_qkd_astk_feng: the qkd_ectl so / si protocol -- K-pass scores of the positions j = engine with the running
// maximum, V-pass e reads of the groups gam = engine mod 8 behind exp_done with the one-cycle read contract, level-3
// nodes in 4 beats under one credit) with data that depends only on the position, so the two sides may run at different
// times.  Compared per layer: the 8 lmax words, every Z block sum, Z done, the 64 P.V beats, every e the engines read,
// and no fault.  Layers: T = 8192, 8191, 4097, 2048, 129, 1, 600, 8192 (two of them behind an empty start that the real
// one overtakes after 100 / 150 cycles); plusarg +T=: that layer only; stack S = parameter.
//   PASS qkd_astk S=<s>: <n> layers exact ...     /    FAIL qkd_astk ...
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkd_astk_feng #(
    parameter integer S = 0,
    parameter integer E = 0,
    parameter integer ERL = 1                 // e read latency (the golden: 1; the die slice: 3 = KVD_ERL)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [31:0]   seed,
    input  wire [633:0]  si,
    output reg  [424:0]  so,
    output reg  [4095:0] nb,
    output reg           done,
    output reg           ev,              // an e word read: {g, k, gam, j} and its data
    output reg  [11:0]   ea,
    output reg  [63:0]   ed
);
    function automatic [31:0] hsh(input [31:0] x);
        reg [31:0] h;
        begin
            h = x ^ seed; h = h * 32'h9E3779B1; h = h ^ (h >> 15); h = h * 32'h85EBCA77; h = h ^ (h >> 13);
            hsh = h;
        end
    endfunction
    function automatic [31:0] fl(input [31:0] x);          // a finite float, |v| in 2^-9 .. 2^6
        reg [31:0] h;
        begin h = hsh(x); fl = {h[31], 8'd118 + {4'd0, h[26:23]}, h[22:0]}; end
    endfunction
    function automatic fgt(input [31:0] a, input [31:0] b);
        fgt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction
    wire        start = si[0];
    wire [13:0] T = si[14:1];
    wire [31:0] xdone = si[568:537];
    wire [13:0] base_s = 14'd128 * S;
    wire [13:0] rem = T - base_s;
    wire [4:0]  gmax = (T <= base_s) ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));
    localparam [2:0] IDLE = 0, KP = 1, VW = 2, VR = 3, NW = 4, NB = 5, FIN = 6;
    reg [2:0]   st;
    reg         g, rnd;
    reg [3:0]   k;
    reg [4:0]   gam;
    reg [2:0]   j;
    reg [3:0]   wt;
    reg [1:0]   beat;
    reg [1:0]   cred;
    reg [255:0] lm;
    reg [1:0]   la;
    reg         erq;
    reg [11:0]  erq_a;
    reg [ERL:0] erd_v;
    reg [11:0]  erd_a [0:ERL];
    integer     d_;
    reg [15:0]  lf;
    wire [13:0] tk = {k, 9'd0} + base_s + {6'd0, gam[3:0], 3'd0} + E;          // K pass: position (k, gam, j = E)
    wire [3:0]  vgam = {rnd, 3'(E)};
    wire [13:0] tv = {k, 9'd0} + base_s + {6'd0, vgam, 3'd0} + {11'd0, j};
    integer h_, c_;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= IDLE; so <= 425'd0; done <= 1'b0; ev <= 1'b0; cred <= 2'd1; lm <= 256'd0; la <= 2'b00; erq <= 1'b0; erd_v <= 0;
            lf <= 16'hACE1; g <= 1'b0; rnd <= 1'b0; k <= 4'd0; gam <= 5'd0; j <= 3'd0; wt <= 4'd0; beat <= 2'd0;
        end else begin
            lf <= {lf[14:0], lf[15] ^ lf[13] ^ lf[12] ^ lf[10]};
            so[0] <= 1'b0; so[13] <= 1'b0; so[412] <= 1'b0;
            // er_valid is out the cycle after erq; its data is on si ERL cycles after that
            erd_v <= {erd_v[ERL-1:0], erq}; erd_a[0] <= erq_a; for (d_ = 1; d_ <= ERL; d_ = d_ + 1) erd_a[d_] <= erd_a[d_-1];
            ev <= erd_v[ERL-1]; ea <= erd_a[ERL-1]; ed <= si[632:569]; erq <= 1'b0;
            if (si[633]) cred <= cred + 2'd1;
            // the running maximum follows the score by one cycle
            if (so[13]) begin
                for (h_ = 0; h_ < 4; h_ = h_ + 1)
                    if (!la[so[25]] || fgt(so[26 + 32*h_ +: 32], lm[32*(4*so[25] + h_) +: 32]))
                        lm[32*(4*so[25] + h_) +: 32] <= so[26 + 32*h_ +: 32];
                la[so[25]] <= 1'b1;
            end
            so[409:154] <= lm; so[411:410] <= la;
            case (st)
                KP: if (lf[1:0] != 2'd0) begin
                    if (tk < T) begin
                        so[13] <= 1'b1; so[25:14] <= {g, k, gam[3:0], 3'(E)};
                        for (h_ = 0; h_ < 4; h_ = h_ + 1) so[26 + 32*h_ +: 32] <= fl({4'd1, g, k, gam[3:0], 3'(E), 2'(h_), 14'd0});
                    end
                    if (gam == 5'd15) begin
                        gam <= 5'd0;
                        if (k == 4'd15) begin
                            k <= 4'd0;
                            if (g) begin g <= 1'b0; rnd <= 1'b0; st <= VW; end else g <= 1'b1;
                        end else k <= k + 4'd1;
                    end else gam <= gam + 5'd1;
                end
                VW: begin                                   // the group's e must be written
                    k <= 4'd0; j <= 3'd0;
                    if ({1'b0, vgam} >= gmax) st <= NW;        // no such group: nothing to read, nothing to send
                    else if (xdone[{g, vgam}]) st <= VR;
                end
                VR: if (lf[2:0] != 3'd0) begin
                    if (tv < T) begin so[0] <= 1'b1; so[12:1] <= {g, k, vgam, j}; erq <= 1'b1; erq_a <= {g, k, vgam, j}; end
                    j <= j + 3'd1;
                    if (j == 3'd7) begin
                        if ({k, 9'd0} + 14'd512 + base_s + {6'd0, vgam, 3'd0} >= T || k == 4'd15) begin st <= NW; wt <= lf[7:4]; end
                        else k <= k + 4'd1;
                    end
                end
                NW: begin
                    beat <= 2'd0;
                    if ({1'b0, vgam} >= gmax) begin          // skip
                        if (rnd) begin rnd <= 1'b0; if (g) st <= FIN; else begin g <= 1'b1; st <= VW; end end
                        else begin rnd <= 1'b1; st <= VW; end
                    end else if (wt != 4'd0) wt <= wt - 4'd1;
                    else if (cred != 2'd0) begin st <= NB; cred <= cred - 2'd1 + {1'b0, si[633]}; end
                end
                NB: begin
                    so[412] <= 1'b1; so[416:413] <= {2'b00, beat}; so[417] <= g; so[421:418] <= vgam;
                    for (h_ = 0; h_ < 4; h_ = h_ + 1) for (c_ = 0; c_ < 32; c_ = c_ + 1)
                        nb[1024*h_ + 32*c_ +: 32] <= fl({4'd2, g, vgam, 3'(E), 2'(h_), 5'(c_), beat, 11'd0});
                    beat <= beat + 2'd1;
                    if (beat == 2'd3) begin
                        if (rnd) begin rnd <= 1'b0; if (g) st <= FIN; else begin g <= 1'b1; st <= VW; end end
                        else begin rnd <= 1'b1; st <= VW; end
                    end
                end
                FIN: done <= 1'b1;
                default: ;
            endcase
            if (start) begin
                st <= KP; g <= 1'b0; rnd <= 1'b0; k <= 4'd0; gam <= 5'd0; j <= 3'd0; done <= 1'b0; lm <= 256'd0; la <= 2'b00;
                cred <= 2'd1;
            end
        end
    end
endmodule

// one side: an aggregator's observable results of a layer, and the M words it is sent
module ot_qkd_astk_obs (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire          so_valid,
    input  wire [1:0]    so_type,
    input  wire          so_g,
    input  wire [1:0]    so_hh,
    input  wire [3:0]    so_k,
    input  wire          so_any,
    input  wire [31:0]   so_data,
    input  wire          pv_valid,
    input  wire          pv_g,
    input  wire [5:0]    pv_beat,
    input  wire [511:0]  pv_data,
    output reg           mi_valid,
    output reg           mi_g,
    output reg  [1:0]    mi_hh,
    output reg  [31:0]   mi_data
);
    reg [32:0]  lm [0:7];             // {any, data}
    reg [7:0]   lm_v;
    reg [31:0]  zs [0:127];           // {g, hh, k}
    reg [127:0] zs_v;
    reg [1:0]   zd;
    reg [511:0] pvb [0:63];
    reg [63:0]  pv_v;
    integer     n_lm, n_zs, n_zd, n_pv, dup, ooo;
    reg [5:0]   pv_exp;
    reg [1:0]   msent;
    reg [5:0]   mw;
    reg [2:0]   mh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lm_v <= 0; zs_v <= 0; zd <= 0; pv_v <= 0; n_lm <= 0; n_zs <= 0; n_zd <= 0; n_pv <= 0; dup <= 0; ooo <= 0; pv_exp <= 0;
            mi_valid <= 1'b0; msent <= 2'b00; mw <= 0; mh <= 0;
        end else begin
            mi_valid <= 1'b0;
            if (so_valid && so_type == 2'd0) begin
                if (lm_v[{so_g, so_hh}]) dup <= dup + 1;
                lm[{so_g, so_hh}] <= {so_any, so_data}; lm_v[{so_g, so_hh}] <= 1'b1; n_lm <= n_lm + 1;
            end
            if (so_valid && so_type == 2'd1) begin
                if (zs_v[{so_g, so_hh, so_k}]) dup <= dup + 1;
                zs[{so_g, so_hh, so_k}] <= so_data; zs_v[{so_g, so_hh, so_k}] <= 1'b1; n_zs <= n_zs + 1;
            end
            if (so_valid && so_type == 2'd2) begin zd[so_g] <= 1'b1; n_zd <= n_zd + 1; end
            if (pv_valid) begin
                if (pv_v[{pv_g, pv_beat[4:0]}]) dup <= dup + 1;
                if (pv_beat[4:0] != pv_exp[4:0] || pv_g != pv_exp[5]) ooo <= ooo + 1;       // the hub counts beats: in order
                pv_exp <= pv_exp + 6'd1;
                pvb[{pv_g, pv_beat[4:0]}] <= pv_data; pv_v[{pv_g, pv_beat[4:0]}] <= 1'b1; n_pv <= n_pv + 1;
            end
            // M of pass g: 24 cycles after its four lmax words, the reported maximum (0 if the stack has no position)
            if (!msent[0] && (&lm_v[3:0])) begin
                if (mw == 6'd24) begin
                    mi_valid <= 1'b1; mi_g <= 1'b0; mi_hh <= mh[1:0]; mi_data <= lm[{1'b0, mh[1:0]}][32] ? lm[{1'b0, mh[1:0]}][31:0] : 32'd0;
                    if (mh == 3'd3) begin msent[0] <= 1'b1; mh <= 0; mw <= 0; end else mh <= mh + 3'd1;
                end else mw <= mw + 6'd1;
            end else if (msent[0] && !msent[1] && (&lm_v[7:4])) begin
                if (mw == 6'd24) begin
                    mi_valid <= 1'b1; mi_g <= 1'b1; mi_hh <= mh[1:0]; mi_data <= lm[{1'b1, mh[1:0]}][32] ? lm[{1'b1, mh[1:0]}][31:0] : 32'd0;
                    if (mh == 3'd3) begin msent[1] <= 1'b1; mh <= 0; mw <= 0; end else mh <= mh + 3'd1;
                end else mw <= mw + 6'd1;
            end
            if (start) begin
                lm_v <= 0; zs_v <= 0; zd <= 0; pv_v <= 0; n_lm <= 0; n_zs <= 0; n_zd <= 0; n_pv <= 0; pv_exp <= 0;
                msent <= 2'b00; mw <= 0; mh <= 0;
            end
        end
    end
endmodule

module tb_qkd_astk #(
    parameter integer S = 0
);
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    reg         start = 1'b0;
    reg [13:0]  T = 14'd0;
    reg [31:0]  seed = 32'h1234_5678;
    // two sides: 0 = golden, 1 = the die masters
    wire [425*8-1:0]  so_f [0:1];
    wire [634*8-1:0]  si_f [0:1];
    wire [4096*8-1:0] nb_f [0:1];
    wire [7:0]        e_done [0:1];
    wire [1:0]        sv, sg, sany, pvv, pvg, flt, miv, mig;
    wire [3:0]        stype, shh, mihh, pvd;
    wire [7:0]        sk;
    wire [63:0]       sdata, midata;
    wire [11:0]       pvbeat;
    wire [1023:0]     pvdata;
    // e words the engines read, by address {g, k, gam, j}
    reg  [63:0] em [0:1][0:4095];
    reg  [4095:0] em_v [0:1];
    integer     n_e [0:1];
    genvar d, e;
    generate for (d = 0; d < 2; d = d + 1) begin : g_d
        wire [7:0]  ev;
        wire [95:0] ea;
        wire [511:0] ed;
        for (e = 0; e < 8; e = e + 1) begin : g_e
            ot_qkd_astk_feng #(.S(S), .E(e), .ERL(d ? 3 : 1)) u_f (.clk(clk), .rst_n(rst_n), .seed(seed), .si(si_f[d][634*e +: 634]),
                .so(so_f[d][425*e +: 425]), .nb(nb_f[d][4096*e +: 4096]), .done(e_done[d][e]), .ev(ev[e]),
                .ea(ea[12*e +: 12]), .ed(ed[64*e +: 64]));
        end
        integer q_;
        always @(posedge clk) begin
            if (start) begin em_v[d] <= 4096'd0; n_e[d] <= 0; end
            else for (q_ = 0; q_ < 8; q_ = q_ + 1) if (ev[q_]) begin
                em[d][ea[12*q_ +: 12]] <= ed[64*q_ +: 64]; em_v[d][ea[12*q_ +: 12]] <= 1'b1; n_e[d] <= n_e[d] + 1;
            end
        end
        ot_qkd_astk_obs u_o (.clk(clk), .rst_n(rst_n), .start(start), .so_valid(sv[d]), .so_type(stype[2*d +: 2]), .so_g(sg[d]),
            .so_hh(shh[2*d +: 2]), .so_k(sk[4*d +: 4]), .so_any(sany[d]), .so_data(sdata[32*d +: 32]), .pv_valid(pvv[d]),
            .pv_g(pvg[d]), .pv_beat(pvbeat[6*d +: 6]), .pv_data(pvdata[512*d +: 512]), .mi_valid(miv[d]), .mi_g(mig[d]),
            .mi_hh(mihh[2*d +: 2]), .mi_data(midata[32*d +: 32]));
    end endgenerate
    ot_qkd_astk_gold #(.HD(128), .S(S), .R(8), .LFB(4), .ND(1)) u_gold (.clk(clk), .rst_n(rst_n), .start(start), .T(T),
        .q_valid(1'b0), .q_beat(6'd0), .q_data(512'd0), .so_f(so_f[0]), .si_f(si_f[0]), .nb_f(nb_f[0]),
        .mi_valid(miv[0]), .mi_g(mig[0]), .mi_hh(mihh[1:0]), .mi_data(midata[31:0]), .so_valid(sv[0]), .so_type(stype[1:0]),
        .so_g(sg[0]), .so_hh(shh[1:0]), .so_k(sk[3:0]), .so_any(sany[0]), .so_data(sdata[31:0]), .pv_valid(pvv[0]),
        .pv_g(pvg[0]), .pv_beat(pvbeat[5:0]), .pv_data(pvdata[511:0]), .pv_done(pvd[1:0]), .fault(flt[0]), .ev());
    ot_qkd_astk_strip #(.S(S)) u_dut (.clk(clk), .rst_n(rst_n), .start(start), .T(T),
        .q_valid(1'b0), .q_beat(6'd0), .q_data(512'd0), .so_f(so_f[1]), .si_f(si_f[1]), .nb_f(nb_f[1]),
        .mi_valid(miv[1]), .mi_g(mig[1]), .mi_hh(mihh[3:2]), .mi_data(midata[63:32]), .so_valid(sv[1]), .so_type(stype[3:2]),
        .so_g(sg[1]), .so_hh(shh[3:2]), .so_k(sk[7:4]), .so_any(sany[1]), .so_data(sdata[63:32]), .pv_valid(pvv[1]),
        .pv_g(pvg[1]), .pv_beat(pvbeat[11:6]), .pv_data(pvdata[1023:512]), .pv_done(pvd[3:2]), .fault(flt[1]));
    integer cyc = 0, t0 = 0, nl = 0, bad = 0, li, i, tend [0:1];
    reg [1:0] fin;
    integer tl [0:15];
    integer ntl;
    wire [1:0] fin_c = {(&e_done[1]) && g_d[1].u_o.n_pv == 64 && g_d[1].u_o.n_zd == 2 && g_d[1].u_o.n_lm == 8,
                        (&e_done[0]) && g_d[0].u_o.n_pv == 64 && g_d[0].u_o.n_zd == 2 && g_d[0].u_o.n_lm == 8};
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (fin_c[0] && !fin[0]) begin fin[0] <= 1'b1; tend[0] <= cyc; end
        if (fin_c[1] && !fin[1]) begin fin[1] <= 1'b1; tend[1] <= cyc; end
        if (start) fin <= 2'b00;
    end
    task automatic check(input integer tt);
        integer m, a;
        begin
            m = 0;
            if (flt != 2'b00) begin $display("MISMATCH T=%0d fault gold=%b dut=%b", tt, flt[0], flt[1]); m = m + 1; end
            if (g_d[1].u_o.dup != 0 || g_d[1].u_o.ooo != 0 || g_d[0].u_o.ooo != 0) begin
                $display("MISMATCH T=%0d dut dup=%0d out-of-order P.V beats dut=%0d gold=%0d", tt, g_d[1].u_o.dup, g_d[1].u_o.ooo, g_d[0].u_o.ooo);
                m = m + 1;
            end
            if (g_d[0].u_o.n_zs != g_d[1].u_o.n_zs || em_v[0] != em_v[1]) begin
                $display("MISMATCH T=%0d counts: Z sums gold %0d dut %0d, e words read gold %0d dut %0d", tt, g_d[0].u_o.n_zs,
                         g_d[1].u_o.n_zs, $countones(em_v[0]), $countones(em_v[1]));
                m = m + 1;
            end
            for (a = 0; a < 8; a = a + 1)
                if (g_d[0].u_o.lm[a][32] != g_d[1].u_o.lm[a][32] ||
                    (g_d[0].u_o.lm[a][32] && g_d[0].u_o.lm[a][31:0] != g_d[1].u_o.lm[a][31:0])) begin
                    if (m < 8) $display("MISMATCH T=%0d lmax[%0d] gold %h dut %h", tt, a, g_d[0].u_o.lm[a], g_d[1].u_o.lm[a]);
                    m = m + 1;
                end
            for (a = 0; a < 128; a = a + 1)
                if (g_d[0].u_o.zs_v[a] != g_d[1].u_o.zs_v[a] || (g_d[0].u_o.zs_v[a] && g_d[0].u_o.zs[a] != g_d[1].u_o.zs[a])) begin
                    if (m < 8) $display("MISMATCH T=%0d Z sum {g,hh,k}=%0d gold %b %h dut %b %h", tt, a, g_d[0].u_o.zs_v[a],
                                        g_d[0].u_o.zs[a], g_d[1].u_o.zs_v[a], g_d[1].u_o.zs[a]);
                    m = m + 1;
                end
            for (a = 0; a < 64; a = a + 1)
                if (g_d[0].u_o.pvb[a] != g_d[1].u_o.pvb[a]) begin
                    if (m < 8) $display("MISMATCH T=%0d P.V beat %0d gold %h dut %h", tt, a, g_d[0].u_o.pvb[a][63:0], g_d[1].u_o.pvb[a][63:0]);
                    m = m + 1;
                end
            for (a = 0; a < 4096; a = a + 1)
                if (em_v[0][a] != em_v[1][a] || (em_v[0][a] && em[0][a] != em[1][a])) begin
                    if (m < 8) $display("MISMATCH T=%0d e[%0d] gold %b %h dut %b %h", tt, a, em_v[0][a], em[0][a], em_v[1][a], em[1][a]);
                    m = m + 1;
                end
            $display("LAYER T=%0d S=%0d: %0d mismatches; lmax %0d, Z sums %0d, P.V beats %0d, e reads %0d; cycles gold %0d dut %0d",
                     tt, S, m, g_d[1].u_o.n_lm, g_d[1].u_o.n_zs, g_d[1].u_o.n_pv, $countones(em_v[1]), tend[0] - t0, tend[1] - t0);
            bad = bad + m;
        end
    endtask
    integer tx;
    initial begin
        tl[0] = 8192; tl[1] = 8191; tl[2] = 4097; tl[3] = 2048; tl[4] = 129; tl[5] = 1; tl[6] = 600; tl[7] = 8192; ntl = 8;
        if ($value$plusargs("T=%d", tx)) begin tl[0] = tx; ntl = 1; end
        repeat (20) @(posedge clk);
        rst_n = 1'b1;
        repeat (20) @(posedge clk);
        for (li = 0; li < ntl; li = li + 1) begin
            seed = 32'h1234_5678 + li * 32'h0101_0101;
            T = tl[li][13:0];
            if (li == 4 || li == 6) begin                 // a start that is overtaken: T 0, then the real start 100 / 150 cycles later
                T = 14'd0;
                @(posedge clk); start <= 1'b1;
                @(posedge clk); start <= 1'b0;
                repeat ((li == 4) ? 100 : 150) @(posedge clk);       // (the M words of the empty layer are in before the second start)
                T = tl[li][13:0];
            end
            @(posedge clk); start <= 1'b1; t0 = cyc;
            @(posedge clk); start <= 1'b0;
            repeat (8) @(posedge clk);
            i = 0;
            while (!(fin == 2'b11) && i < 400000) begin @(posedge clk); i = i + 1; end
            if (fin != 2'b11) begin
                $display("MISMATCH T=%0d timeout: done gold %b dut %b; engines %b %b; dut lmax %0d Z %0d Zdone %0d P.V %0d; gold lmax %0d Z %0d Zdone %0d P.V %0d",
                         tl[li], fin[0], fin[1], e_done[0], e_done[1], g_d[1].u_o.n_lm, g_d[1].u_o.n_zs, g_d[1].u_o.n_zd,
                         g_d[1].u_o.n_pv, g_d[0].u_o.n_lm, g_d[0].u_o.n_zs, g_d[0].u_o.n_zd, g_d[0].u_o.n_pv);
                bad = bad + 1; tend[0] = cyc; tend[1] = cyc;
            end
            repeat (300) @(posedge clk);                    // late words would show as counts
            check(tl[li]);
            nl = nl + 1;
        end
        if (bad == 0) $display("PASS qkd_astk S=%0d: %0d layers exact (lmax, Z block sums, Z done, 64 P.V beats in order, every e read; no fault)", S, nl);
        else $display("FAIL qkd_astk S=%0d: %0d mismatches in %0d layers", S, bad, nl);
        $finish;
    end
endmodule
