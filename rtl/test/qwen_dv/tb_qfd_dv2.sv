`timescale 1ns/1ps
// Q-DV slice2 bench harness: N qfd_dv_slice2 in one die chain, slice 0 = the W5 end (down), slice N-1 = the up end.
//   cmd / hr      TB -> s0.cmd_i / hr_i -> ... (cmd 2 edges a hop, hr 1)
//   rs_s / rs_n   per slice from the event file (ports 2 + 2k / 3 + 2k)
//   l9            pairs (2j even = receiver, 2j+1 odd = sender)
//   stream        TB -> s0.st_up_i (W end); st_up_o -> next; st_dn_o -> previous; up end's st_dn_i idle
//   scalar        sc_up chain upward, sc_dn chain downward; chain ends idle
//   outbound      s[k].ch_up_i = s[k+1].ch_dn_o (up end idle); s0.ch_dn_o = the W5 edge (logged: S0AR / S0DD)
//   cc / ag       S<k>CC logged when valid; ag chain s[k].ag_up_i = s[k+1].ag_dn_o (up end 0), S0AG at the end
//   return        TB -> s0.ch_dn_i (AR ret / D2D ret, ports 1 / 40); s[k].ch_dn_i = s[k-1].ch_up_o
// Events (+EV): "cycle port hex": 0 CMD (s0.cmd_i), 1 ARET, 40 DRET, 41 SWI, 2+2k RSS(k), 3+2k RSN(k).
// Log: S0AR / S0DD (W5 edge), S<k>SU / S<k>SD (scalar words leaving slice k up / down), S<N-1>E (up-end stream),
// S<k>TOK (status token), S<k>ST at the end.
module tb_qfd_dv2 (input wire ck);
    parameter integer MUT = 0, N = 2, SU_LT = 0, HD_W130 = 0;
    reg rst_n = 1'b0;
    reg  [115:0]  cmd0;
    reg  [452:0]  hr0;
    reg  [1037:0] ret0;
    reg  [1087:0] swi;
    reg  [1027:0] rss [0:N-1], rsn [0:N-1];
    wire [115:0]  cmdc [0:N];
    wire [452:0]  hrc [0:N];
    wire [1087:0] stu [0:N], std_ [0:N];
    wire [47:0]   scu [0:N], scd [0:N];
    wire [1094:0] cho [0:N];
    wire [9:0]    agc [0:N];
    wire [49:0]   cc [0:N-1];
    wire [1037:0] chr [0:N];
    wire [513:0]  l9o [0:N-1];
    wire [106:0]  st [0:N-1];
    assign cmdc[0] = cmd0; assign hrc[0] = hr0; assign stu[0] = swi; assign scu[0] = 48'd0; assign chr[0] = ret0;
    assign std_[N] = 1088'd0; assign scd[N] = 48'd0; assign cho[N] = 1095'd0; assign agc[N] = 10'd0;
    genvar k;
    generate for (k = 0; k < N; k = k + 1) begin : g_s
        wire [513:0] l9i = (k % 2 == 0) ? ((k + 1 < N) ? l9o[k+1] : 514'd0) : l9o[k-1];
        qfd_dv_slice2 #(.MUT(MUT), .SU_LT(SU_LT), .HD_W130(HD_W130)) u (.ck(ck), .rst_n(rst_n), .cmd_i(cmdc[k]), .cmd_o(cmdc[k+1]),
            .hr_i(hrc[k]), .hr_o(hrc[k+1]), .rs_s(rss[k]), .rs_n(rsn[k]), .l9_i(l9i), .l9_o(l9o[k]),
            .st_up_i(stu[k]), .st_up_o(stu[k+1]), .st_dn_i(std_[k+1]), .st_dn_o(std_[k]),
            .sc_up_i(scu[k]), .sc_up_o(scu[k+1]), .sc_dn_i(scd[k+1]), .sc_dn_o(scd[k]),
            .ch_up_i(cho[k+1]), .ch_dn_o(cho[k]), .ch_dn_i(chr[k]), .ch_up_o(chr[k+1]),
            .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3(), .st(st[k]),
            .cc_o(cc[k]), .ag_up_i(agc[k+1]), .ag_dn_o(agc[k]));
    end endgenerate
    integer fd, lg, cyc, ncyc, ec, ep, r, i, pre = 0;
    reg dbg_pf = 0;
    reg [1087:0] ev;
    reg have;
    reg [1023:0] evf, lgf;
    task automatic clear;
        begin
            cmd0 = 0; hr0 = 0; ret0 = 0; swi = 0;
            for (i = 0; i < N; i = i + 1) begin rss[i] = 0; rsn[i] = 0; end
        end
    endtask
    task automatic apply(input integer p, input [1087:0] v);
        begin
            if (p == 0) cmd0 = v[115:0];
            else if (p == 1) ret0 = ret0 | {v[517:0], 520'd0};
            else if (p == 40) ret0 = ret0 | {518'd0, v[519:0]};
            else if (p == 41) swi = v;
            else if (p >= 2 && p < 2 + 2 * N) begin
                if (p % 2 == 0) rss[(p - 2) / 2] = rss[(p - 2) / 2] | v[1027:0];
                else rsn[(p - 3) / 2] = rsn[(p - 3) / 2] | v[1027:0];
            end else $fatal(1, "bad port %0d", p);
        end
    endtask
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w");
        clear;
        cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (cho[0][1094]) $fdisplay(lg, "%0d S0AR %h", cyc, cho[0][1094:548]);
            if (cho[0][547])  $fdisplay(lg, "%0d S0DD %h", cyc, cho[0][547:0]);
            for (i = 0; i < N; i = i + 1) begin
                if (scu[i+1][47]) $fdisplay(lg, "%0d S%0dSU %h", cyc, i, scu[i+1]);
                if (scd[i][47])   $fdisplay(lg, "%0d S%0dSD %h", cyc, i, scd[i]);
                if (st[i][24])    $fdisplay(lg, "%0d S%0dTOK %h", cyc, i, st[i][23:0]);
                if (cc[i][49])    $fdisplay(lg, "%0d S%0dCC %h", cyc, i, cc[i]);
            end
            if (stu[N][1087]) $fdisplay(lg, "%0d S%0dE %h", cyc, N - 1, stu[N]);
`ifdef DV2_DEBUG
            if (g_s[0].u.su_go || g_s[0].u.c_su || g_s[0].u.c_prt)
                $display("%0d s0 c_su %0d su_go %0d ready %0d pidx %0d si_lo %h cmdq %h", cyc, g_s[0].u.c_su,
                         g_s[0].u.su_go, g_s[0].u.su_ready, g_s[0].u.cmd_q[12:4], g_s[0].u.si[60:0], g_s[0].u.cmd_q);
            if (g_s[0].u.port_fault && !dbg_pf) begin $display("%0d s0 PORT FAULT", cyc); dbg_pf = 1; end
`endif
            clear;
            while (have && ec == cyc) begin
                apply(ep, ev);
                r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
            end
            if (have && ec < cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                for (i = 0; i < N; i = i + 1) $fdisplay(lg, "%0d S%0dST %h", cyc, i, st[i]);
                $fdisplay(lg, "%0d S0AG %h", cyc, agc[0]);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
