`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_ha2_ar: N dies, each on its own core clock and PHY clock (random phases
// per seed), fully wired with ot_ha2_link directions (both directions of
// every port), running ONE all-reduce of the given shape end to end.
// Every die checks every committed result flit against the golden image
// (tools/ha2_ar_fixture.py: hdc_golden.add pairwise tree + to_bf16) and
// reports issue / last-commit times.  Latency = earliest issue on any die
// -> last result committed at the hub on the slowest die (the W15 rule).
// ---------------------------------------------------------------------------
// Shape and link constants come from macros (+define+HA2_<NAME>=...), so the per-die endpoint and the per-link
// direction are parameter-free wrappers that Verilator compiles ONCE as hierarchical blocks (a 96-die flat
// elaboration of parameter overrides exceeds 128 GB).
`ifndef HA2_GS
`define HA2_GS 16
`endif
`ifndef HA2_NG
`define HA2_NG 6
`endif
`ifndef HA2_NC
`define HA2_NC 8
`endif
`ifndef HA2_NOG
`define HA2_NOG 8
`endif
`ifndef HA2_E
`define HA2_E 1024
`endif
`ifndef HA2_LANES
`define HA2_LANES 16
`endif
`ifndef HA2_ONESHOT
`define HA2_ONESHOT 0
`endif
`ifndef HA2_BF16
`define HA2_BF16 1
`endif
`ifndef HA2_INJ
`define HA2_INJ 2
`endif
`ifndef HA2_DEL
`define HA2_DEL 4
`endif
`ifndef HA2_HUBW
`define HA2_HUBW 35
`endif
`ifndef HA2_WSTG
`define HA2_WSTG 14
`endif
`ifndef HA2_BITS_X100
`define HA2_BITS_X100 21165
`endif
`ifndef HA2_PWB
`define HA2_PWB 551
`endif
`ifndef HA2_PHY_L
`define HA2_PHY_L 130
`endif
`ifndef HA2_PHY_G
`define HA2_PHY_G 138
`endif
`ifndef HA2_JS
`define HA2_JS 3
`endif
`ifndef HA2_DMAX
`define HA2_DMAX 192
`endif
`ifndef HA2_RXAW
`define HA2_RXAW 5
`endif
`ifndef HA2_QAW
`define HA2_QAW 5
`endif
`ifndef HA2_LAT
`define HA2_LAT 7
`endif
`ifndef HA2_T_PHY
`define HA2_T_PHY 1.0
`endif

module tb_ha2_ar #(
    parameter integer GS = `HA2_GS, NG = `HA2_NG, NC = `HA2_NC, NOG = `HA2_NOG, E = `HA2_E, LANES = `HA2_LANES,
    parameter integer ONESHOT = `HA2_ONESHOT, BF16 = `HA2_BF16, INJ = `HA2_INJ, DEL = `HA2_DEL,
    parameter integer HUBW = `HA2_HUBW, WSTG = `HA2_WSTG,
    parameter integer BITS_X100 = `HA2_BITS_X100, PWB = `HA2_PWB,
    parameter integer PHY_L = `HA2_PHY_L, PHY_G = `HA2_PHY_G, JS = `HA2_JS, DMAX = `HA2_DMAX,
    parameter integer RXAW = `HA2_RXAW, QAW = `HA2_QAW, LAT = `HA2_LAT,
    parameter real    T_CORE = 0.833333, T_PHY = `HA2_T_PHY,
    parameter real    T0 = 400.0
);
    localparam integer N = GS * NG, NP = (GS - 1) + (NG - 1), NL = GS - 1;
    localparam integer FW = 32 * LANES, PWT = FW + 25;
    localparam integer PF = E / LANES, OF = ONESHOT ? PF : PF / NC, RPF = BF16 ? 2 : 1;
    localparam integer TOT = ONESHOT ? OF / RPF : NOG * NC * (OF / RPF);
    localparam integer NCTR = NOG * NC;

    integer seed, seed0;
    string vecdir;
    reg [FW-1:0] part [0:NCTR*PF-1];
    reg [FW-1:0] expw [0:TOT-1];
    reg go_clk = 0, go = 0;
    real ph [0:2*N-1];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "missing VEC");
        for (integer i = 0; i < 2*N; i = i + 1) ph[i] = (($unsigned($random(seed)) % 1000) / 1000.0);
        $readmemh({vecdir, "/part.hex"}, part);
        $readmemh({vecdir, "/expected.hex"}, expw);
        $display("HA2CFG seed=%0d N=%0d GS=%0d NG=%0d NC=%0d NOG=%0d E=%0d LANES=%0d ONESHOT=%0d BF16=%0d INJ=%0d DEL=%0d HUBW=%0d WSTG=%0d BITS_X100=%0d PWB=%0d PHY_L=%0d PHY_G=%0d JS=%0d T_CORE=%f T_PHY=%f TOT=%0d",
                 seed0, N, GS, NG, NC, NOG, E, LANES, ONESHOT, BF16, INJ, DEL, HUBW, WSTG, BITS_X100, PWB,
                 PHY_L, PHY_G, JS, T_CORE, T_PHY, TOT);
        go_clk = 1;
        #(T0) go = 1;
    end
    wire [N-1:0] clk, pclk, rst_n, prst_n;
    genvar d, p;
    generate for (d = 0; d < N; d = d + 1) begin : g_clk
        reg c = 0, pc = 0, r = 0, pr = 0;
        initial begin wait(go_clk); #(T_CORE * ph[2*d] + 0.001);  forever #(T_CORE/2) c = ~c; end
        initial begin wait(go_clk); #(T_PHY * ph[2*d+1] + 0.001); forever #(T_PHY/2) pc = ~pc; end
        always @(posedge c)  r  <= ($realtime > 40.0);
        always @(posedge pc) pr <= ($realtime > 40.0);
        assign clk[d] = c; assign pclk[d] = pc; assign rst_n[d] = r; assign prst_n[d] = pr;
    end endgenerate

    // ---- per-die endpoint and checker -------------------------------------------------------------------
    wire [NP-1:0]     txv [0:N-1];
    wire [NP*PWT-1:0] txf [0:N-1];
    wire [NP-1:0]     crr [0:N-1];
    wire [NP-1:0]     rxv [0:N-1];
    wire [NP*PWT-1:0] rxf [0:N-1];
    wire [NP-1:0]     rxc [0:N-1];
    wire [N-1:0]      dfault;
    wire [N*NP-1:0]   lfault;
    wire [N-1:0]      done;
    real t_issue [0:N-1], t_done [0:N-1];
    integer mism = 0, stalls = 0;
    generate for (d = 0; d < N; d = d + 1) begin : g_die
        wire [INJ*16-1:0] ii;
        wire [INJ-1:0] ir;
        reg  [INJ*FW-1:0] idata;
        always @* for (integer i = 0; i < INJ; i = i + 1)
            idata[FW*i +: FW] = (d < NCTR) ? part[d * PF + integer'(ii[16*i +: 16])] : '0;
        wire [DEL-1:0] dv;
        wire [DEL*PWT-1:0] dfl;
        wire [31:0] cst;
        tb_ha2_ep u_ep (.clk(clk[d]), .rst_n(rst_n[d]), .rank(8'(d)), .go(go), .inj_idx(ii), .inj_rd(ir), .inj_data(idata),
            .tx_valid(txv[d]), .tx_flit(txf[d]), .cr_ret(crr[d]), .rx_valid(rxv[d]), .rx_flit(rxf[d]),
            .rx_credit(rxc[d]), .del_valid(dv), .del_flit(dfl), .fault(dfault[d]), .stat_credit_stall(cst));
        integer got = 0;
        reg dn = 0;
        assign done[d] = dn;
        reg [TOT-1:0] seen = 0;
        reg issued = 0;
        always @(posedge clk[d]) begin
            if (go && !issued) begin issued <= 1'b1; t_issue[d] = $realtime; end
            for (integer i = 0; i < DEL; i = i + 1) if (dv[i]) begin : chk
                integer gi;
                gi = integer'(dfl[i*PWT + FW +: 16]);
                if (gi >= TOT || seen[gi] || dfl[i*PWT +: FW] !== expw[gi]) begin
                    mism = mism + 1;
                    if (mism < 10) $display("HA2MISMATCH die=%0d gi=%0d dup=%0d", d, gi, gi < TOT ? seen[gi] : 1'b0);
                end
                if (gi < TOT) seen[gi] = 1'b1;
                got = got + 1;
                if (got == TOT) begin dn <= 1'b1; t_done[d] = $realtime; end
            end
        end
        always @(posedge done[d]) stalls = stalls + integer'(cst);
    end endgenerate

    // ---- links: every port of every die, both directions ------------------------------------------------
    integer dly_tab [0:2*N*NP-1];
    integer phy_l, phy_g, js;
    initial begin : draw
        integer s2;
        if (!$value$plusargs("PHY_L=%d", phy_l)) phy_l = PHY_L;     // run-time override (stages of T_PHY)
        if (!$value$plusargs("PHY_G=%d", phy_g)) phy_g = PHY_G;
        if (!$value$plusargs("JS=%d", js)) js = JS;
        if (phy_l + js > DMAX || phy_g + js > DMAX) $fatal(1, "PHY latency exceeds DMAX");
        $display("HA2PHY phy_l=%0d phy_g=%0d js=%0d", phy_l, phy_g, js);
        if (!$value$plusargs("SEED=%d", s2)) s2 = 1;
        s2 = s2 * 7919 + 17;
        for (integer i = 0; i < N * NP; i = i + 1) begin
            integer base;
            base = ((i % NP) < NL) ? phy_l : phy_g;
            dly_tab[2*i]   = base + (js > 0 ? ($unsigned($random(s2)) % (js + 1)) : 0);
            dly_tab[2*i+1] = base + (js > 0 ? ($unsigned($random(s2)) % (js + 1)) : 0);
        end
    end
    generate for (d = 0; d < N; d = d + 1) begin : g_lk
        for (p = 0; p < NP; p = p + 1) begin : g_p
            localparam integer G = d / GS, L = d % GS;
            localparam integer LOC = (p < NL) ? 1 : 0;
            localparam integer PL  = p + (p >= L ? 1 : 0);                       // peer lane (local)
            localparam integer Q   = p - NL, PG = Q + (Q >= G ? 1 : 0);          // peer group (global)
            localparam integer R   = LOC ? (G * GS + PL) : (PG * GS + L);
            localparam integer RP  = LOC ? (L - (L > PL ? 1 : 0)) : (NL + G - (G > PG ? 1 : 0));
            wire ov, cr;
            wire [PWT-1:0] of_;
            wire [31:0] nfl;
            tb_ha2_lk u_l (.s_clk(clk[d]), .s_rst_n(rst_n[d]), .s_pclk(pclk[d]), .s_prst_n(prst_n[d]),
                   .r_clk(clk[R]), .r_rst_n(rst_n[R]), .r_pclk(pclk[R]), .r_prst_n(prst_n[R]),
                   .dly(16'(dly_tab[2*(d*NP+p)])), .dly_r(16'(dly_tab[2*(d*NP+p)+1])),
                   .in_valid(txv[d][p]), .in_flit(txf[d][p*PWT +: PWT]), .cr_ret(cr),
                   .out_valid(ov), .out_flit(of_), .r_credit(rxc[R][RP]), .fault(lfault[d*NP+p]),
                   .stat_flits(nfl));
            assign crr[d][p] = cr;
            assign rxv[R][RP] = ov;
            assign rxf[R][RP*PWT +: PWT] = of_;
        end
    end endgenerate

    initial begin : fin
        real tmin, tmax;
        integer worst;
        wait (&done);
        repeat (50) @(posedge clk[0]);
        tmin = 1.0e18; tmax = 0.0; worst = 0;
        for (integer i = 0; i < N; i = i + 1) begin
            if (t_issue[i] < tmin) tmin = t_issue[i];
            if (t_done[i] > tmax) begin tmax = t_done[i]; worst = i; end
        end
        for (integer i = 0; i < N; i = i + 1)
            $display("HA2DIE die=%0d issue_ns=%0.3f done_ns=%0.3f lat_ns=%0.3f", i, t_issue[i], t_done[i],
                     t_done[i] - tmin);
        $display("HA2DONE seed=%0d lat_ns=%0.3f lat_cyc_1p2=%0.1f worst_die=%0d mismatches=%0d faults=%0d credit_stall_cycles=%0d",
                 seed0, tmax - tmin, (tmax - tmin) * 1.2, worst, mism, (|dfault) || (|lfault), stalls);
        $finish;
    end
    initial begin #(200000.0); $display("HA2TIMEOUT done=%0d", $countones(done)); $finish; end
endmodule

// ---- parameter-free wrappers (hierarchical blocks) ---------------------------------------------------------
module tb_ha2_ep (
    input  wire clk, rst_n, input wire [7:0] rank, input wire go,
    output wire [`HA2_INJ*16-1:0] inj_idx, output wire [`HA2_INJ-1:0] inj_rd,
    input  wire [`HA2_INJ*32*`HA2_LANES-1:0] inj_data,
    output wire [`HA2_GS+`HA2_NG-3:0] tx_valid, output wire [(`HA2_GS+`HA2_NG-2)*(32*`HA2_LANES+25)-1:0] tx_flit,
    input  wire [`HA2_GS+`HA2_NG-3:0] cr_ret,
    input  wire [`HA2_GS+`HA2_NG-3:0] rx_valid, input wire [(`HA2_GS+`HA2_NG-2)*(32*`HA2_LANES+25)-1:0] rx_flit,
    output wire [`HA2_GS+`HA2_NG-3:0] rx_credit,
    output wire [`HA2_DEL-1:0] del_valid, output wire [`HA2_DEL*(32*`HA2_LANES+25)-1:0] del_flit,
    output wire fault, output wire [31:0] stat_credit_stall
);
    /*verilator hier_block*/
    ot_ha2_ar_endpoint #(.ENABLE(1), .GS(`HA2_GS), .NG(`HA2_NG), .NC(`HA2_NC), .NOG(`HA2_NOG), .E(`HA2_E),
        .LANES(`HA2_LANES), .ONESHOT(`HA2_ONESHOT), .BF16(`HA2_BF16), .INJ(`HA2_INJ), .DEL(`HA2_DEL),
        .HUBW(`HA2_HUBW), .RXAW(`HA2_RXAW), .QAW(`HA2_QAW), .LAT(`HA2_LAT))
      u (.clk(clk), .rst_n(rst_n), .rank(rank), .go(go), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_data(inj_data),
         .tx_valid(tx_valid), .tx_flit(tx_flit), .cr_ret(cr_ret), .rx_valid(rx_valid), .rx_flit(rx_flit),
         .rx_credit(rx_credit), .del_valid(del_valid), .del_flit(del_flit), .fault(fault),
         .stat_credit_stall(stat_credit_stall));
endmodule

module tb_ha2_lk (
    input  wire s_clk, s_rst_n, s_pclk, s_prst_n, r_clk, r_rst_n, r_pclk, r_prst_n,
    input  wire [15:0] dly, dly_r,
    input  wire in_valid, input wire [32*`HA2_LANES+24:0] in_flit, output wire cr_ret,
    output wire out_valid, output wire [32*`HA2_LANES+24:0] out_flit, input wire r_credit,
    output wire fault, output wire [31:0] stat_flits
);
    /*verilator hier_block*/
    ot_ha2_link #(.W(32*`HA2_LANES+25), .PWB(`HA2_PWB), .WSTG(`HA2_WSTG), .BITS_X100(`HA2_BITS_X100),
        .DMAX(`HA2_DMAX), .AW(`HA2_RXAW))
      u (.s_clk(s_clk), .s_rst_n(s_rst_n), .s_pclk(s_pclk), .s_prst_n(s_prst_n), .r_clk(r_clk), .r_rst_n(r_rst_n),
         .r_pclk(r_pclk), .r_prst_n(r_prst_n), .dly(dly), .dly_r(dly_r), .in_valid(in_valid), .in_flit(in_flit),
         .cr_ret(cr_ret), .out_valid(out_valid), .out_flit(out_flit), .r_credit(r_credit), .fault(fault),
         .stat_flits(stat_flits));
endmodule
