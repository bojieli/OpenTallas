`ifndef TX_SRAM
`define TX_SRAM 0
`endif
`ifndef IDX_MUT
`define IDX_MUT 0
`endif
`ifndef VM_MUT
`define VM_MUT 0
`endif
`timescale 1ns/1ps
// S81-L20DIE (10-19): compose bench of the static index RANK TREE on the REAL die units: per die a dsdv_idx_vmux
// (bk_sel S-face ingress merge), the selector dsdv_bk_sel (die.v u_bk_sel straps: tap_k 0x11, sink_k 0x10, ik 4, ek 5,
// uid 0x5B, eg_n 0) and the tree transmitter dsdv_idx_tx (UID 0x5C) on its vi_s / vo_s taps; a child's tx output (lo)
// reaches its parent's vmux child input (i_a / i_b) over a fixed-latency link of LEG edges (the die-to-die leg; no
// credit / ready).  NDIE = 6 dies are built; the tree (parent, parent input) is given per die by plusargs, so one build
// runs every tree shape (k 3, k 6).  Stimulus = the COMPILER's plan (lower_bk.py tree-rd gen): the reader-shaped score
// beats at each die's vmux i_s (the score-chain tail) and the drain / tx-job CTL beats at each die's bk_sel vi_n.
// Edge convention as tb_bk_layer: stimulus for edge e is driven before posedge e; "VO d e" / "TX d e" print a die's
// vo_s / tx lo right after posedge e.  Link: the parent's vmux input at edge e = the child's lo printed at e - 1 - LEG.
// The checker (lower_bk.py tree-rd check) compares every die's vo_s beats with its compiled egress and every tx beat
// sequence with its compiled words, and checks the reserved slot windows.
// S81/IDXNET (2026-10-25) TREE_TP (needs TREE_DIEM): +TPD=<mask> dies send their TX job with DST 1 (the bench sets the job
// CTL's p[101:100] = 1 on vi_n): their beats leave on tpn_o (topk_final TP lane) and reach the parent's tpn_i (vmux i_n)
// over the same leg instead of tl_o -> ca / cb; the compiler's golden check must stay exact (same edges), tl_o of a TPD
// die must never be valid, tpn_o / tps_o of other dies never valid (stray).  +LPD=<die> also sets LOOP (p[102]) on that
// die's TX job (DST 3: nothing leaves) and checks the loop-back at the selector input: every lo beat appears at u_sel.vi_s
// 3 edges later with lane 3 (LOOP_OK / LOOP_BAD; the checker verdict is not used for that run).
module tb_idx_tree;
    localparam integer V = 276, ND = 6, LMAX = 4096;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer ncyc, cyc = 0, fd, r, e, dd, leg;
    integer par [0:ND-1], pin [0:ND-1];
    reg [V-1:0] i_s [0:ND-1], vi_n [0:ND-1], i_a [0:ND-1], i_b [0:ND-1];
    wire [V-1:0] vi_s [0:ND-1], vo_s [0:ND-1], vo_n [0:ND-1], lo [0:ND-1];
    wire [ND-1:0] f_sel, f_vm; wire [15:0] tst [0:ND-1];
    reg  [V-1:0] i_n [0:ND-1]; wire [V-1:0] tpo [0:ND-1], tso [0:ND-1]; wire [V-1:0] txo [0:ND-1];
    integer tpd = 0, lpd = -1, tp_stray = 0, loop_ok = 0, loop_bad = 0;
    reg [V-1:0] ss [int]; reg [V-1:0] sn [int];
    reg [V-1:0] hist [0:ND-1][0:LMAX-1];
    reg [V-1:0] a;
    reg [7:0] pt;
    string fn;
    genvar g;
    generate for (g = 0; g < ND; g = g + 1) begin : d
`ifdef TREE_DIEM
        // S81-RTLGAP/RG-L20 (10-21): the 72-frame die bk_sel master itself (dsdv_bk_sel_vmtx = vmux + bk_sel +
        // dsdv_idx_tx_n32), die straps as the IDX4 bind table; i_r (column rung) idle as before
        dsdv_bk_sel_vmtx #(.TX_MUT(`TX_MUT), .TX_SRAM(`TX_SRAM), .IDX_MUT(`IDX_MUT), .VM_MUT(`VM_MUT)) u_die (.clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10),
            .ik(3'd4), .ek(3'd5), .uid(8'h5B), .eg_n(1'b0), .vi_s({V{1'b0}}), .vo_n(vo_n[g]), .vi_n(vi_n[g]), .vo_s(vo_s[g]),
            .vi_idx(i_s[g]), .ca(i_a[g]), .cb(i_b[g]), .fault(f_sel[g]), .vm_fault(f_vm[g]), .tl_o(lo[g]), .tx_st(tst[g]),
            .tpn_o(tpo[g]), .tps_o(tso[g]), .tpn_i(i_n[g]));
        assign txo[g] = tpd[g] ? tpo[g] : lo[g];
`ifdef TREE_TP
        // loop-back probe: the die's tx lo (u_die.lo) -> u_sel.vi_s 3 edges later, lane field 3
        reg [V-1:0] lq1, lq2, lq3;
        reg [V-1:0] loop_expected;
        always @(posedge clk) begin
            lq3 <= lq2; lq2 <= lq1; lq1 <= u_die.lo;
            if (g == lpd && rst_n && lq3[0]) begin
                loop_expected = {lq3[V-1:6], 2'd3, lq3[3:0]};
                if (u_die.vi_m === loop_expected) loop_ok++;
                else begin loop_bad++; if (loop_bad < 4) $display("LOOP_BAD die %0d cyc %0d", g, cyc); end
            end
        end
`endif
`else
        dsdv_idx_vmux u_vm (.ck(clk), .rst(rst_n), .i_r({V{1'b0}}), .i_s(i_s[g]), .i_a(i_a[g]), .i_b(i_b[g]), .o(vi_s[g]), .fault(f_vm[g]));
        dsdv_bk_sel u_bk_sel (.clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10), .ik(3'd4), .ek(3'd5), .uid(8'h5B),
            .eg_n(1'b0), .vi_s(vi_s[g]), .vo_n(vo_n[g]), .vi_n(vi_n[g]), .vo_s(vo_s[g]), .fault(f_sel[g]));
`ifdef TX_LPX
        // MU.S81.CAL (DIE4 10-22): reference with the booked TOPK TX x lookup pipe (LPX edges longer; needs RTL 100457dd6+)
        dsdv_idx_tx #(.MUT(`TX_MUT), .SRAM_MACRO(`TX_SRAM), .LPX(`TX_LPX)) u_tx (.ck(clk), .rst(rst_n), .vi(vi_s[g]), .vo(vo_s[g]), .lo(lo[g]), .st(tst[g]));
`else
        dsdv_idx_tx #(.MUT(`TX_MUT), .SRAM_MACRO(`TX_SRAM)) u_tx (.ck(clk), .rst(rst_n), .vi(vi_s[g]), .vo(vo_s[g]), .lo(lo[g]), .st(tst[g]));
`endif
`endif
    end endgenerate
    initial begin
        if (!$value$plusargs("STIM=%s", fn)) fn = "stim.txt";
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 1000;
        if (!$value$plusargs("LEG=%d", leg)) leg = 729;
        if (leg + 2 >= LMAX) $fatal(1, "LEG too large");
        for (int i = 0; i < ND; i++) begin
            par[i] = -1; pin[i] = 0; i_s[i] = 0; vi_n[i] = 0; i_a[i] = 0; i_b[i] = 0;
            for (int j = 0; j < LMAX; j++) hist[i][j] = 0;
        end
        void'($value$plusargs("PAR1=%d", par[1])); void'($value$plusargs("PIN1=%d", pin[1]));
        void'($value$plusargs("PAR2=%d", par[2])); void'($value$plusargs("PIN2=%d", pin[2]));
        void'($value$plusargs("PAR3=%d", par[3])); void'($value$plusargs("PIN3=%d", pin[3]));
        void'($value$plusargs("PAR4=%d", par[4])); void'($value$plusargs("PIN4=%d", pin[4]));
        void'($value$plusargs("PAR5=%d", par[5])); void'($value$plusargs("PIN5=%d", pin[5]));
        void'($value$plusargs("TPD=%d", tpd)); void'($value$plusargs("LPD=%d", lpd));
        for (int i = 0; i < ND; i++) i_n[i] = 0;
        fd = $fopen(fn, "r");
        if (fd == 0) begin $display("TB_TREE no stim %s", fn); $finish; end
        while (!$feof(fd)) begin
            string p;
            r = $fscanf(fd, "%d %d %s %h\n", e, dd, p, a);
            if (r == 4) begin
                if (p == "s") ss[e * 8 + dd] = a; else sn[e * 8 + dd] = a;
            end
        end
        $fclose(fd);
        $display("TB_TREE stim s %0d n %0d ncyc %0d leg %0d tx_mut %0d", ss.num(), sn.num(), ncyc, leg, `TX_MUT);
    end
    always @(negedge clk) begin
        for (int i = 0; i < ND; i++) begin
            i_s[i] <= ss.exists(cyc * 8 + i) ? ss[cyc * 8 + i] : '0;
            a = sn.exists(cyc * 8 + i) ? sn[cyc * 8 + i] : '0;
            // S81/IDXNET TREE_TP: the TX job CTL (kind 0, p[7:0] 0x5C, p[10:8] 2) of a TPD die gets DST 1, of LPD DST 3 + LOOP
            if (a[0] && a[3:1] == 3'd0 && a[28:21] == 8'h5C && a[31:29] == 3'd2) begin
                if (tpd[i]) a[21+101 -: 2] = 2'd1;
                if (i == lpd) begin a[21+101 -: 2] = 2'd3; a[21+102] = 1'b1; end
            end
            vi_n[i] <= a;
            i_a[i] <= '0; i_b[i] <= '0; i_n[i] <= '0;
        end
        for (int c = 0; c < ND; c++) if (par[c] >= 0 && cyc - 1 - leg >= 0) begin
            if (tpd[c])           i_n[par[c]] <= hist[c][(cyc - 1 - leg) % LMAX];
            else if (pin[c] == 0) i_a[par[c]] <= hist[c][(cyc - 1 - leg) % LMAX];
            else                  i_b[par[c]] <= hist[c][(cyc - 1 - leg) % LMAX];
        end
        if (cyc == 10) rst_n <= 1'b1;
    end
    integer fs [0:ND-1], fv [0:ND-1], ft [0:ND-1];
    initial for (int i = 0; i < ND; i++) begin fs[i] = -1; fv[i] = -1; ft[i] = -1; end
    always @(posedge clk) begin
        #0.1;
        for (int i = 0; i < ND; i++) begin
            if (vo_s[i] != 0) $display("VO %0d %0d %h", i, cyc, vo_s[i]);
`ifdef TREE_DIEM
            if (txo[i][0]) $display("TX %0d %0d %h", i, cyc, txo[i]);   // valid beats (S81/IDXNET: outputs share lo's data)
            hist[i][cyc % LMAX] = txo[i][0] ? txo[i] : '0;
            if (rst_n && ((tpd[i] && lo[i][0]) || (!tpd[i] && tpo[i][0]) || tso[i][0])) begin
                tp_stray++; if (tp_stray < 4) $display("TP_STRAY die %0d cyc %0d", i, cyc); end
`else
            if (lo[i] != 0) $display("TX %0d %0d %h", i, cyc, lo[i]);
            hist[i][cyc % LMAX] = lo[i];
`endif
            if (rst_n && f_sel[i] === 1'b1 && fs[i] < 0) begin fs[i] = cyc; $display("FAULT sel %0d %0d", i, cyc); end
            if (rst_n && f_vm[i] === 1'b1 && fv[i] < 0) begin fv[i] = cyc; $display("FAULT vmux %0d %0d", i, cyc); end
            if (rst_n && tst[i][0] === 1'b1 && ft[i] < 0) begin ft[i] = cyc; $display("FAULT tx %0d %0d st %h", i, cyc, tst[i]); end
        end
        cyc++;
        if (cyc >= ncyc) begin
            for (int i = 0; i < ND; i++) $display("TXST %0d %h", i, tst[i]);
            $display("TB_TREE done cycles %0d", cyc);
`ifdef TREE_DIEM
            $display("TB_TREE_TP tpd %0d lpd %0d tp_stray %0d loop_ok %0d loop_bad %0d", tpd, lpd, tp_stray, loop_ok, loop_bad);
`endif
            $finish;
        end
    end
endmodule
