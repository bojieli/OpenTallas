`timescale 1ns/1ps
// TOK-QK/S8 DIAGNOSTIC (not a deliverable bench): N qfd_dv_s8_flat in a tb_qfd_dv2-style chain, same +EV / +LOG format,
// plus per-edge debug of slice DBG internals (SU start / PROG table writes / SU progress / lanes).
module tb_s8dbg (input wire ck);
    parameter integer N = 2, DBG = 1;
    reg rst_n = 1'b0;
    reg  [115:0] cmd0; reg [452:0] hr0; reg [1037:0] ret0; reg [1087:0] swi;
    reg  [1027:0] rss [0:N-1], rsn [0:N-1];
    wire [115:0] cmdc [0:N]; wire [452:0] hrc [0:N]; wire [1087:0] stu [0:N], std_ [0:N];
    wire [47:0] scu [0:N], scd [0:N]; wire [1094:0] cho [0:N]; wire [9:0] agc [0:N]; wire [49:0] cc [0:N-1];
    wire [1037:0] chr [0:N]; wire [513:0] l9o [0:N-1]; wire [106:0] st [0:N-1]; wire [8:0] treqc [0:N];
    assign cmdc[0] = cmd0; assign hrc[0] = hr0; assign stu[0] = swi; assign scu[0] = 48'd0; assign chr[0] = ret0;
    assign std_[N] = 0; assign scd[N] = 0; assign cho[N] = 0; assign agc[N] = 0; assign treqc[0] = 9'd0;
    genvar k;
    generate for (k = 0; k < N; k = k + 1) begin : g_s
        wire [515:0] cn0, cn1, cn2, cn3, cs0, cs1, cs2, cs3;
        wire [513:0] l9i = (k % 2 == 0) ? ((k + 1 < N) ? l9o[k+1] : 514'd0) : l9o[k-1];
        qfd_dv_s8_flat u (.ck(ck), .rst_n(rst_n), .cmd_i(cmdc[k]), .cmd_o(cmdc[k+1]), .hr_i(hrc[k]), .hr_o(hrc[k+1]),
            .rs_s(rss[k]), .rs_n(rsn[k]), .l9_i(l9i), .l9_o(l9o[k]), .st_up_i(stu[k]), .st_up_o(stu[k+1]),
            .st_dn_i(std_[k+1]), .st_dn_o(std_[k]), .sc_up_i(scu[k]), .sc_up_o(scu[k+1]), .sc_dn_i(scd[k+1]), .sc_dn_o(scd[k]),
            .ch_up_i(cho[k+1]), .ch_dn_o(cho[k]), .ch_dn_i(chr[k]), .ch_up_o(chr[k+1]),
            .cw_n0(cn0), .cw_n1(cn1), .cw_n2(cn2), .cw_n3(cn3), .cw_s0(cs0), .cw_s1(cs1), .cw_s2(cs2), .cw_s3(cs3),
            .st(st[k]), .cc_o(cc[k]), .ag_up_i(agc[k+1]), .ag_dn_o(agc[k]), .treq_i(treqc[k]), .treq_o(treqc[k+1]));
    end endgenerate
    integer fd, lg, cyc, ncyc, ec, ep, r, i, pre = 0;
    reg [1087:0] ev; reg have; reg [1023:0] evf, lgf;
    task automatic clear; begin cmd0 = 0; hr0 = 0; ret0 = 0; swi = 0; for (i = 0; i < N; i = i + 1) begin rss[i] = 0; rsn[i] = 0; end end endtask
    task automatic apply(input integer p, input [1087:0] v);
        begin
            if (p == 0) cmd0 = v[115:0];
            else if (p == 1) ret0 = ret0 | {v[517:0], 520'd0};
            else if (p == 40) ret0 = ret0 | {518'd0, v[519:0]};
            else if (p == 41) swi = v;
            else if (p == 42) hr0 = v[452:0];
            else if (p >= 2 && p < 2 + 2 * N) begin
                if (p % 2 == 0) rss[(p - 2) / 2] = rss[(p - 2) / 2] | v[1027:0]; else rsn[(p - 3) / 2] = rsn[(p - 3) / 2] | v[1027:0];
            end
        end
    endtask
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w"); clear; cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
    end
`define D g_s[DBG].u
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            for (i = 0; i < N; i = i + 1) begin
                if (scu[i+1][47]) $fdisplay(lg, "%0d S%0dSU %h", cyc, i, scu[i+1]);
                if (scd[i][47])   $fdisplay(lg, "%0d S%0dSD %h", cyc, i, scd[i]);
            end
            if (`D.cmd_q[0]) $fdisplay(lg, "%0d D cmd_q %h", cyc, `D.cmd_q);
            if (`D.tw_we) $fdisplay(lg, "%0d D tw kind %0d addr %h d[63:0] %h", cyc, `D.tw_kind, `D.tw_addr, `D.tw_data[63:0]);
            if (`D.rp_tw_we) $fdisplay(lg, "%0d D vtw kind %0d addr %h", cyc, `D.rp_tw_kind, `D.rp_tw_addr);
            if (`D.su_cmd[9]) $fdisplay(lg, "%0d D su_cmd %h", cyc, `D.su_cmd);
            if (`D.u_suvm.u_su8.c_start | `D.u_suvm.u_su8.su_go) $fdisplay(lg, "%0d D su8 c_start %b su_go %b si[60:0] %h", cyc, `D.u_suvm.u_su8.c_start, `D.u_suvm.u_su8.su_go, `D.u_suvm.u_su8.c_si[60:0]);
            if (|`D.gv || |`D.lv1) $fdisplay(lg, "%0d D gv %b lv1 %b", cyc, `D.gv, `D.lv1);
            if (|`D.L_va_re || |`D.L_retire || |`D.L_l_fault || |`D.L_l_ov) $fdisplay(lg, "%0d D lanes va_re %b retire %b last %b fault %b ov %b", cyc, `D.L_va_re, `D.L_retire, `D.L_l_last, `D.L_l_fault, `D.L_l_ov);
            if (`D.rd_v | `D.red_we | `D.red_fault) $fdisplay(lg, "%0d D red rd_v %b we %b addr %h fault %b", cyc, `D.rd_v, `D.red_we, `D.red_addr, `D.red_fault);
            if ((cyc % 50) == 0 || `D.su_fault) $fdisplay(lg, "%0d D stat idle %b nr %b fault %b prog %0d rows %0d vm_fault %b sc_busy %b red_busy %b st %h", cyc, `D.su_idle, `D.su_nr, `D.su_fault, `D.su_prog, `D.su_rows, `D.vm_fault, `D.sc_busy, `D.red_busy, st[DBG]);
            if ((cyc >= 50 && cyc < 75) || (cyc >= 1570 && cyc < 1600)) $fdisplay(lg, "%0d P ptw_w %b twp_w %b twp_a %h twp_d0[36:0] %h pp_re %b pp_idx %h |p_rd %b |pcap %b pg.p_q[36:0] %h vm8q.p_q[36:0] %h c_si[36:0] %h acc0 %b", cyc, `D.u_suvm.u_vm8q.u_pg.ptw_w, `D.u_suvm.u_vm8q.u_pg.twp_w, `D.u_suvm.u_vm8q.u_pg.twp_a, `D.u_suvm.u_vm8q.u_pg.twp_d0[36:0], `D.u_suvm.u_vm8q.u_pg.pp_re, `D.u_suvm.u_vm8q.u_pg.pp_idx, |`D.u_suvm.u_vm8q.u_pg.p_rd, |`D.u_suvm.u_vm8q.u_pg.pcap, `D.u_suvm.u_vm8q.u_pg.p_q[36:0], `D.u_suvm.u_vm8q.p_q[36:0], `D.u_suvm.u_su8.c_si[36:0], `D.u_suvm.u_su8.acc_k[0]);
            clear;
            while (have && ec == cyc) begin apply(ep, ev); r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3); end
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                for (i = 0; i < N; i = i + 1) $fdisplay(lg, "%0d S%0dST %h", cyc, i, st[i]);
                $fclose(lg); $finish;
            end
        end
    end
endmodule
