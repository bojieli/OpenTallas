`ifndef TX_SRAM
`define TX_SRAM 0
`endif
`ifndef VM_MUT
`define VM_MUT 0
`endif
`ifndef DL_MUT
`define DL_MUT 0
`endif
`ifndef VDLY
`define VDLY 28
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
module tb_idx_tree;
    localparam integer V = 276, ND = 6, LMAX = 4096;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer ncyc, cyc = 0, fd, r, e, dd, leg;
    integer par [0:ND-1], pin [0:ND-1];
    reg [V-1:0] i_s [0:ND-1], vi_n [0:ND-1], i_a [0:ND-1], i_b [0:ND-1];
    wire [V-1:0] vi_s [0:ND-1], vo_s [0:ND-1], vo_n [0:ND-1], lo [0:ND-1];
    wire [ND-1:0] f_sel, f_vm; wire [15:0] tst [0:ND-1];
    reg [V-1:0] ss [int]; reg [V-1:0] sn [int];
    reg [V-1:0] hist [0:ND-1][0:LMAX-1];
    reg [V-1:0] a;
    reg [7:0] pt;
    string fn;
    genvar g;
    generate for (g = 0; g < ND; g = g + 1) begin : d
`ifdef TREE_DIEM_N32
        // STW-S81-TOPK-VMUX (10-21): vmtx' = dsdv_bk_sel_vmtx_n32 (vmux_n32 + landed PlanA n32 parent + vdly + tx_n32);
        // every parent region on the bench clock / reset (regional skew is the die's, not this bench's); stimulus booked
        // with lower_bk tree-rd --plana
        dsdv_bk_sel_vmtx_n32 #(.TX_MUT(`TX_MUT), .TX_SRAM(`TX_SRAM), .VM_MUT(`VM_MUT), .DL_MUT(`DL_MUT), .VDLY(`VDLY)) u_die (
            .clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10),
            .ik(3'd4), .ek(3'd5), .uid(8'h5B), .eg_n(1'b0), .vi_s({V{1'b0}}), .vo_n(vo_n[g]), .vi_n(vi_n[g]), .vo_s(vo_s[g]),
            .vi_idx(i_s[g]), .ca(i_a[g]), .cb(i_b[g]), .fault(f_sel[g]), .vm_fault(f_vm[g]), .tl_o(lo[g]), .tx_st(tst[g]),
            .ck_core(clk), .ck_r1(clk), .ck_r2(clk), .ck_r3(clk), .ck_r4(clk), .ck_r5(clk), .ck_r6(clk), .ck_r7(clk), .ck_r8(clk), .ck_r9(clk), .ck_r10(clk), .ck_r11(clk), .ck_r12(clk), .ck_r13(clk), .ck_r14(clk), .ck_r15(clk), .ck_r16(clk), .ck_r17(clk), .ck_r18(clk), .ck_r19(clk), .ck_r20(clk), .ck_r21(clk), .ck_r22(clk), .ck_r23(clk), .ck_r24(clk), .ck_r25(clk), .ck_r26(clk), .ck_r27(clk), .ck_r28(clk), .ck_r29(clk), .ck_r30(clk), .ck_r31(clk), .ck_r32(clk), .ck_r33(clk), .ck_r34(clk), .ck_r35(clk), .ck_r36(clk), .ck_r37(clk), .ck_r38(clk), .rst_n_core(rst_n), .rst_n_r1(rst_n), .rst_n_r2(rst_n), .rst_n_r3(rst_n), .rst_n_r4(rst_n), .rst_n_r5(rst_n), .rst_n_r6(rst_n), .rst_n_r7(rst_n), .rst_n_r8(rst_n), .rst_n_r9(rst_n), .rst_n_r10(rst_n), .rst_n_r11(rst_n), .rst_n_r12(rst_n), .rst_n_r13(rst_n), .rst_n_r14(rst_n), .rst_n_r15(rst_n), .rst_n_r16(rst_n), .rst_n_r17(rst_n), .rst_n_r18(rst_n), .rst_n_r19(rst_n), .rst_n_r20(rst_n), .rst_n_r21(rst_n), .rst_n_r22(rst_n), .rst_n_r23(rst_n), .rst_n_r24(rst_n), .rst_n_r25(rst_n), .rst_n_r26(rst_n), .rst_n_r27(rst_n), .rst_n_r28(rst_n), .rst_n_r29(rst_n), .rst_n_r30(rst_n), .rst_n_r31(rst_n), .rst_n_r32(rst_n), .rst_n_r33(rst_n), .rst_n_r34(rst_n), .rst_n_r35(rst_n), .rst_n_r36(rst_n), .rst_n_r37(rst_n), .rst_n_r38(rst_n));
`elsif TREE_DIEM
        // S81-RTLGAP/RG-L20 (10-21): the 72-frame die bk_sel master itself (dsdv_bk_sel_vmtx = vmux + bk_sel +
        // dsdv_idx_tx_n32), die straps as the IDX4 bind table; i_r (column rung) idle as before
        dsdv_bk_sel_vmtx #(.TX_MUT(`TX_MUT), .TX_SRAM(`TX_SRAM)) u_die (.clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10),
            .ik(3'd4), .ek(3'd5), .uid(8'h5B), .eg_n(1'b0), .vi_s({V{1'b0}}), .vo_n(vo_n[g]), .vi_n(vi_n[g]), .vo_s(vo_s[g]),
            .vi_idx(i_s[g]), .ca(i_a[g]), .cb(i_b[g]), .fault(f_sel[g]), .vm_fault(f_vm[g]), .tl_o(lo[g]), .tx_st(tst[g]));
`else
`ifdef TREE_VMN32
        dsdv_idx_vmux_n32 #(.MUT(`VM_MUT)) u_vm (.ck(clk), .rst(rst_n), .i_r({V{1'b0}}), .i_s(i_s[g]), .i_a(i_a[g]), .i_b(i_b[g]), .o(vi_s[g]), .fault(f_vm[g]));
`else
        dsdv_idx_vmux u_vm (.ck(clk), .rst(rst_n), .i_r({V{1'b0}}), .i_s(i_s[g]), .i_a(i_a[g]), .i_b(i_b[g]), .o(vi_s[g]), .fault(f_vm[g]));
`endif
        dsdv_bk_sel u_bk_sel (.clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10), .ik(3'd4), .ek(3'd5), .uid(8'h5B),
            .eg_n(1'b0), .vi_s(vi_s[g]), .vo_n(vo_n[g]), .vi_n(vi_n[g]), .vo_s(vo_s[g]), .fault(f_sel[g]));
        dsdv_idx_tx #(.MUT(`TX_MUT), .SRAM_MACRO(`TX_SRAM)) u_tx (.ck(clk), .rst(rst_n), .vi(vi_s[g]), .vo(vo_s[g]), .lo(lo[g]), .st(tst[g]));
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
            vi_n[i] <= sn.exists(cyc * 8 + i) ? sn[cyc * 8 + i] : '0;
            i_a[i] <= '0; i_b[i] <= '0;
        end
        for (int c = 0; c < ND; c++) if (par[c] >= 0 && cyc - 1 - leg >= 0) begin
            if (pin[c] == 0) i_a[par[c]] <= hist[c][(cyc - 1 - leg) % LMAX];
            else             i_b[par[c]] <= hist[c][(cyc - 1 - leg) % LMAX];
        end
        if (cyc == 10) rst_n <= 1'b1;
    end
    integer fs [0:ND-1], fv [0:ND-1], ft [0:ND-1];
    initial for (int i = 0; i < ND; i++) begin fs[i] = -1; fv[i] = -1; ft[i] = -1; end
    always @(posedge clk) begin
        #0.1;
        for (int i = 0; i < ND; i++) begin
            if (vo_s[i] != 0) $display("VO %0d %0d %h", i, cyc, vo_s[i]);
            if (lo[i] != 0) $display("TX %0d %0d %h", i, cyc, lo[i]);
            hist[i][cyc % LMAX] = lo[i];
            if (rst_n && f_sel[i] === 1'b1 && fs[i] < 0) begin fs[i] = cyc; $display("FAULT sel %0d %0d", i, cyc); end
            if (rst_n && f_vm[i] === 1'b1 && fv[i] < 0) begin fv[i] = cyc; $display("FAULT vmux %0d %0d", i, cyc); end
            if (rst_n && tst[i][0] === 1'b1 && ft[i] < 0) begin ft[i] = cyc; $display("FAULT tx %0d %0d st %h", i, cyc, tst[i]); end
        end
        cyc++;
        if (cyc >= ncyc) begin
            for (int i = 0; i < ND; i++) $display("TXST %0d %h", i, tst[i]);
            $display("TB_TREE done cycles %0d", cyc);
            $finish;
        end
    end
endmodule
