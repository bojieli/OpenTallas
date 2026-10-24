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
// S<k>VW (TOK-FUNC3-QW-STG4 10-21, testbench probe only): one line per STN-result VM write in slice k (the 16-element
// w16 write of the station result, st_vm = r_v && stn_dst[0]), value = the 24-bit VM word address r_addr; the edge is the
// negedge sample of the cycle that presents the write to qfd_dv_vm (same convention as every other log line).
// +define+DV2_XHEAD (QW-XHEAD 10-19): port 42 HR (s0.hr_i, 453 b), and per slice S<k>XT (the heads' x write xt_v: xt_a),
// S<k>CW (the 8 column-head corridor go bits {n3..n0, s3..s0}), S<k>XL (edges with a corridor x line: the tag valid
// bits of the 8 corridor words), S<k>HF (the heads' fault, first edge).
module tb_qfd_dv2 (input wire ck);
    parameter integer MUT = 0, N = 2, SU_LT = 0, HD_W130 = 0;   // MU-SLICE-GATE: the kitted slice is SU_LT 1, HD_W130 1
    parameter integer MU_NU = 1;     // MU-ADOPT-SLICE: qfd_dv_slice2 MU_NU (R4 per-user LM-head argmax)
    parameter integer FACE = 0;      // 0 master qfd_dv_slice2; 1 the W face qfd_dv_slice2_w; 2 the E face qfd_dv_slice2_e
                                     // 3 (TOK-QW 10-24) the BOUND compute-die slice of chain position k (s8die/qfd_dv_slice_die.sv)
    parameter integer ARF = 0, RP = 0;   // QW-LAYERGAP: qfd_dv_slice2 AR message framer / RoPE row from the return chain
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
    wire [N-1:0]  vw_v;              // VM-write probe (S<k>VW): STN result written into slice k's VM
    wire [24*N-1:0] vw_a;
`ifdef DV2_XHEAD
    wire [N-1:0]  xh_xtv, xh_hf;
    wire [24*N-1:0] xh_xta;
    wire [8*N-1:0] xh_go, xh_xl;
    reg  [N-1:0]  xh_hf_seen;
`endif
    assign cmdc[0] = cmd0; assign hrc[0] = hr0; assign stu[0] = swi; assign scu[0] = 48'd0; assign chr[0] = ret0;
    assign std_[N] = 1088'd0; assign scd[N] = 48'd0; assign cho[N] = 1095'd0; assign agc[N] = 10'd0;
    wire [8:0] treqc [0:N];          // FACE 3: bound table-request lane tt_ctlm -> slice 0 (W5) -> ... (tied 0 at the head)
    assign treqc[0] = 9'd0;
    genvar k;
    generate for (k = 0; k < N; k = k + 1) begin : g_s
        wire [515:0] cn0, cn1, cn2, cn3, cs0, cs1, cs2, cs3;
        wire [513:0] l9i = (k % 2 == 0) ? ((k + 1 < N) ? l9o[k+1] : 514'd0) : l9o[k-1];
        tb_dv2_slice #(.MUT(MUT), .SU_LT(SU_LT), .HD_W130(HD_W130), .MU_NU(MU_NU), .FACE(FACE), .ARF(ARF), .RP(RP), .SIDX(k)) u (.treq_i(treqc[k]), .treq_o(treqc[k+1]),.ck(ck), .rst_n(rst_n), .cmd_i(cmdc[k]), .cmd_o(cmdc[k+1]),
            .hr_i(hrc[k]), .hr_o(hrc[k+1]), .rs_s(rss[k]), .rs_n(rsn[k]), .l9_i(l9i), .l9_o(l9o[k]),
            .st_up_i(stu[k]), .st_up_o(stu[k+1]), .st_dn_i(std_[k+1]), .st_dn_o(std_[k]),
            .sc_up_i(scu[k]), .sc_up_o(scu[k+1]), .sc_dn_i(scd[k+1]), .sc_dn_o(scd[k]),
            .ch_up_i(cho[k+1]), .ch_dn_o(cho[k]), .ch_dn_i(chr[k]), .ch_up_o(chr[k+1]),
            .cw_n0(cn0), .cw_n1(cn1), .cw_n2(cn2), .cw_n3(cn3), .cw_s0(cs0), .cw_s1(cs1), .cw_s2(cs2), .cw_s3(cs3), .st(st[k]),
            .cc_o(cc[k]), .ag_up_i(agc[k+1]), .ag_dn_o(agc[k]));
        assign vw_v[k] = u.vw_v; assign vw_a[24*k +: 24] = u.vw_a;
`ifdef DV2_XHEAD
        // corridor word {tag 8 [515:508], xl 128, ib 379, go [0]}; tag = {vB, sB 3, vA, sA 3}
        assign xh_xtv[k] = u.xt_v; assign xh_xta[24*k +: 24] = u.xt_a; assign xh_hf[k] = u.hd_fault;
        assign xh_go[8*k +: 8] = {cn3[0], cn2[0], cn1[0], cn0[0], cs3[0], cs2[0], cs1[0], cs0[0]};
        assign xh_xl[8*k +: 8] = {cn3[515] | cn3[511], cn2[515] | cn2[511], cn1[515] | cn1[511], cn0[515] | cn0[511],
                                  cs3[515] | cs3[511], cs2[515] | cs2[511], cs1[515] | cs1[511], cs0[515] | cs0[511]};
`endif
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
`ifdef DV2_XHEAD
            else if (p == 42) hr0 = v[452:0];
`endif
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
`ifdef DV2_XHEAD
        xh_hf_seen = 0;
`endif
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
                if (st[i][24])    $fdisplay(lg, "%0d S%0dTOK %h", cyc, i, st[i][27:0]);   // [27:26] token user (MU_NU > 1)
                if (cc[i][49])    $fdisplay(lg, "%0d S%0dCC %h", cyc, i, cc[i]);
                if (vw_v[i])      $fdisplay(lg, "%0d S%0dVW %h", cyc, i, vw_a[24*i +: 24]);
            end
            if (stu[N][1087]) $fdisplay(lg, "%0d S%0dE %h", cyc, N - 1, stu[N]);
`ifdef DV2_XHEAD
            for (i = 0; i < N; i = i + 1) begin
                if (xh_xtv[i]) $fdisplay(lg, "%0d S%0dXT %h", cyc, i, xh_xta[24*i +: 24]);
                if (|xh_go[8*i +: 8]) $fdisplay(lg, "%0d S%0dCW %h", cyc, i, xh_go[8*i +: 8]);
                if (|xh_xl[8*i +: 8]) $fdisplay(lg, "%0d S%0dXL %h", cyc, i, xh_xl[8*i +: 8]);
                if (xh_hf[i] && !xh_hf_seen[i]) $fdisplay(lg, "%0d S%0dHF 1", cyc, i);
            end
            xh_hf_seen = xh_hf_seen | xh_hf;
`endif
`ifdef DV2_DEBUG
            if (g_s[0].u.g_m.u.su_go || g_s[0].u.g_m.u.c_su || g_s[0].u.g_m.u.c_prt)
                $display("%0d s0 c_su %0d su_go %0d ready %0d pidx %0d si_lo %h cmdq %h", cyc, g_s[0].u.g_m.u.c_su,
                         g_s[0].u.g_m.u.su_go, g_s[0].u.g_m.u.su_ready, g_s[0].u.g_m.u.cmd_q[12:4], g_s[0].u.g_m.u.si[60:0], g_s[0].u.g_m.u.cmd_q);
            if (g_s[0].u.g_m.u.port_fault && !dbg_pf) begin $display("%0d s0 PORT FAULT", cyc); dbg_pf = 1; end
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

// MU-ADOPT-SLICE 10-19: the master port list on a master core (FACE 0) or on a generated face wrapper (FACE 1 W, 2 E),
// so every dv_bench2 bench runs unchanged on the face RTL (the face is a port map: dn face = master W for _w, E for _e).
module tb_dv2_slice #(parameter integer MUT = 0, parameter integer SU_LT = 0, parameter integer HD_W130 = 0,
                      parameter integer MU_NU = 1, parameter integer FACE = 0, parameter integer ARF = 0,
                      parameter integer RP = 0, parameter integer SIDX = 0) (
    input  wire [8:0] treq_i, output wire [8:0] treq_o,
    input  wire ck, input wire rst_n,
    input  wire [115:0] cmd_i, output wire [115:0] cmd_o, input wire [452:0] hr_i, output wire [452:0] hr_o,
    input  wire [1027:0] rs_s, input wire [1027:0] rs_n, input wire [513:0] l9_i, output wire [513:0] l9_o,
    input  wire [1087:0] st_up_i, output wire [1087:0] st_up_o, input wire [1087:0] st_dn_i, output wire [1087:0] st_dn_o,
    input  wire [47:0] sc_up_i, output wire [47:0] sc_up_o, input wire [47:0] sc_dn_i, output wire [47:0] sc_dn_o,
    input  wire [1094:0] ch_up_i, output wire [1094:0] ch_dn_o, input wire [1037:0] ch_dn_i, output wire [1037:0] ch_up_o,
    output wire [515:0] cw_n0, cw_n1, cw_n2, cw_n3, cw_s0, cw_s1, cw_s2, cw_s3,
    output wire [106:0] st, output wire [49:0] cc_o, input wire [9:0] ag_up_i, output wire [9:0] ag_dn_o);
    // VM-write probe (testbench observation only; read by tb_qfd_dv2 as u.vw_v / u.vw_a): the station-result write port
    wire vw_v; wire [23:0] vw_a;
    // QW-XHEAD heads probe (+DV2_XHEAD, read as u.xt_v / u.xt_a / u.hd_fault): the slice x-stream tap write + heads fault
    wire xt_v, hd_fault; wire [23:0] xt_a;
    generate if (FACE == 0) begin : g_m
        qfd_dv_slice2 #(.MUT(MUT), .SU_LT(SU_LT), .HD_W130(HD_W130), .MU_NU(MU_NU), .ARF(ARF), .RP(RP)) u (.ck(ck), .rst_n(rst_n), .cmd_i(cmd_i), .cmd_o(cmd_o),
            .hr_i(hr_i), .hr_o(hr_o), .rs_s(rs_s), .rs_n(rs_n), .l9_i(l9_i), .l9_o(l9_o),
            .st_up_i(st_up_i), .st_up_o(st_up_o), .st_dn_i(st_dn_i), .st_dn_o(st_dn_o),
            .sc_up_i(sc_up_i), .sc_up_o(sc_up_o), .sc_dn_i(sc_dn_i), .sc_dn_o(sc_dn_o),
            .ch_up_i(ch_up_i), .ch_dn_o(ch_dn_o), .ch_dn_i(ch_dn_i), .ch_up_o(ch_up_o),
            .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0), .cw_s1(cw_s1), .cw_s2(cw_s2),
            .cw_s3(cw_s3), .st(st), .cc_o(cc_o), .ag_up_i(ag_up_i), .ag_dn_o(ag_dn_o));
        assign vw_v = u.st_vm; assign vw_a = u.r_addr;
        assign xt_v = u.xt_v; assign xt_a = u.xt_a; assign hd_fault = u.hd_fault;
    end else if (FACE == 1) begin : g_w
        qfd_dv_slice2_w #(.MUT(MUT), .SU_LT(SU_LT), .HD_W130(HD_W130), .MU_NU(MU_NU), .ARF(ARF), .RP(RP)) u (.ck(ck), .rst_n(rst_n), .cmd_wi(cmd_i), .cmd_eo(cmd_o),
            .hr_wi(hr_i), .hr_eo(hr_o), .st_wo(st_dn_o), .st_wi(st_up_i), .st_eo(st_up_o), .st_ei(st_dn_i),
            .sc_wo(sc_dn_o), .sc_wi(sc_up_i), .sc_eo(sc_up_o), .sc_ei(sc_dn_i),
            .arv_wo(ch_dn_o[1094]), .art_wo(ch_dn_o[1093:1062]), .arm_wo(ch_dn_o[1061]), .arl_wo(ch_dn_o[1060]),
            .ard_wo(ch_dn_o[1059:548]), .dd_wo(ch_dn_o[547:0]),
            .arv_ei(ch_up_i[1094]), .art_ei(ch_up_i[1093:1062]), .arm_ei(ch_up_i[1061]), .arl_ei(ch_up_i[1060]),
            .ard_ei(ch_up_i[1059:548]), .dd_ei(ch_up_i[547:0]),
            .rv_wi(ch_dn_i[1037]), .re_wi(ch_dn_i[1036]), .rr_wi(ch_dn_i[1035:1033]), .rl_wi(ch_dn_i[1032]),
            .rd_wi(ch_dn_i[1031:520]), .dr_wi(ch_dn_i[519:0]),
            .rv_eo(ch_up_o[1037]), .re_eo(ch_up_o[1036]), .rr_eo(ch_up_o[1035:1033]), .rl_eo(ch_up_o[1032]),
            .rd_eo(ch_up_o[1031:520]), .dr_eo(ch_up_o[519:0]),
            .ag_wo(ag_dn_o), .ag_ei(ag_up_i), .ss_wo(st),
            .ccv_wo(cc_o[49]), .ccm_wo(cc_o[48]), .ccw_wo(cc_o[47:32]), .cct_wo(cc_o[31:0]),
            .l9_wi(l9_i), .l9_eo(l9_o), .rs_n0(rs_n[513:0]), .rs_n1(rs_n[1027:514]), .rs_s0(rs_s[513:0]),
            .rs_s1(rs_s[1027:514]), .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0),
            .cw_s1(cw_s1), .cw_s2(cw_s2), .cw_s3(cw_s3));
        assign vw_v = u.u_core.st_vm; assign vw_a = u.u_core.r_addr;
        assign xt_v = u.u_core.xt_v; assign xt_a = u.u_core.xt_a; assign hd_fault = u.u_core.hd_fault;
    end else if (FACE == 2) begin : g_e
        qfd_dv_slice2_e #(.MUT(MUT), .SU_LT(SU_LT), .HD_W130(HD_W130), .MU_NU(MU_NU), .ARF(ARF), .RP(RP)) u (.ck(ck), .rst_n(rst_n), .cmd_ei(cmd_i), .cmd_wo(cmd_o),
            .hr_ei(hr_i), .hr_wo(hr_o), .st_eo(st_dn_o), .st_ei(st_up_i), .st_wo(st_up_o), .st_wi(st_dn_i),
            .sc_eo(sc_dn_o), .sc_ei(sc_up_i), .sc_wo(sc_up_o), .sc_wi(sc_dn_i),
            .arv_eo(ch_dn_o[1094]), .art_eo(ch_dn_o[1093:1062]), .arm_eo(ch_dn_o[1061]), .arl_eo(ch_dn_o[1060]),
            .ard_eo(ch_dn_o[1059:548]), .dd_eo(ch_dn_o[547:0]),
            .arv_wi(ch_up_i[1094]), .art_wi(ch_up_i[1093:1062]), .arm_wi(ch_up_i[1061]), .arl_wi(ch_up_i[1060]),
            .ard_wi(ch_up_i[1059:548]), .dd_wi(ch_up_i[547:0]),
            .rv_ei(ch_dn_i[1037]), .re_ei(ch_dn_i[1036]), .rr_ei(ch_dn_i[1035:1033]), .rl_ei(ch_dn_i[1032]),
            .rd_ei(ch_dn_i[1031:520]), .dr_ei(ch_dn_i[519:0]),
            .rv_wo(ch_up_o[1037]), .re_wo(ch_up_o[1036]), .rr_wo(ch_up_o[1035:1033]), .rl_wo(ch_up_o[1032]),
            .rd_wo(ch_up_o[1031:520]), .dr_wo(ch_up_o[519:0]),
            .ag_eo(ag_dn_o), .ag_wi(ag_up_i), .ss_eo(st),
            .ccv_eo(cc_o[49]), .ccm_eo(cc_o[48]), .ccw_eo(cc_o[47:32]), .cct_eo(cc_o[31:0]),
            .l9_wi(l9_i), .l9_eo(l9_o), .rs_n0(rs_n[513:0]), .rs_n1(rs_n[1027:514]), .rs_s0(rs_s[513:0]),
            .rs_s1(rs_s[1027:514]), .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0),
            .cw_s1(cw_s1), .cw_s2(cw_s2), .cw_s3(cw_s3));
        assign vw_v = u.u_core.st_vm; assign vw_a = u.u_core.r_addr;
        assign xt_v = u.u_core.xt_v; assign xt_a = u.u_core.xt_a; assign hd_fault = u.u_core.hd_fault;
    end else begin : g_die
        // FACE 3 (TOK-QW 10-24): the bound die slice at this position; MUT / SU_LT / HD_W130 / MU_NU / ARF / RP do not
        // apply (the bound s8 slice is fixed: SU_LT 1, HD_W130 1, MU_NU 4, ARF 1, RP 1 equivalent, HARD leaves)
        qfd_dv_slice_die #(.SIDX(SIDX)) u (.ck(ck), .rst_n(rst_n), .cmd_i(cmd_i), .cmd_o(cmd_o),
            .hr_i(hr_i), .hr_o(hr_o), .rs_s(rs_s), .rs_n(rs_n), .l9_i(l9_i), .l9_o(l9_o),
            .st_up_i(st_up_i), .st_up_o(st_up_o), .st_dn_i(st_dn_i), .st_dn_o(st_dn_o),
            .sc_up_i(sc_up_i), .sc_up_o(sc_up_o), .sc_dn_i(sc_dn_i), .sc_dn_o(sc_dn_o),
            .ch_up_i(ch_up_i), .ch_dn_o(ch_dn_o), .ch_dn_i(ch_dn_i), .ch_up_o(ch_up_o),
            .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(cw_s0), .cw_s1(cw_s1), .cw_s2(cw_s2),
            .cw_s3(cw_s3), .st(st), .cc_o(cc_o), .ag_up_i(ag_up_i), .ag_dn_o(ag_dn_o), .treq_i(treq_i), .treq_o(treq_o),
            .vw_v(vw_v), .vw_a(vw_a), .xt_v(xt_v), .xt_a(xt_a), .hd_fault(hd_fault));
    end endgenerate
    generate if (FACE != 3) begin : g_notreq
        assign treq_o = 9'd0;
    end endgenerate
endmodule
