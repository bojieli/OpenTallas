W="/srv/opentallas-scratch2/claude/wt/claude-tok17-head"
s=open(W+"/rtl/dsrom_sys/s81_head/test/tb_s81hd_ctl_physical.sv").read()
def rep(a,b):
    global s
    assert s.count(a)>=1, a
    s=s.replace(a,b,1)
rep("module tb_s81hd_ctl_physical;","""// TOK-ALL-17 latency probes (copy of tb_s81hd_ctl_physical, REAL ot_s81hd_ctl_core): +B2B = 80 XB beats back to back
//   in gidx order (line rate); LAT lines report ingress, own-BEST issue, peer->merge and merge->token/RESULT edges.
module tb_tok17_ctl_lat;""")
rep("for (k = 79; k > 0; k = k - 1) begin t","if (!b2b) for (k = 79; k > 0; k = k - 1) begin t")
rep("if (b % 3 == 0) tick;","if (!b2b && b % 3 == 0) tick;")
rep("ri = 0; ri[0] = 1; ri[3:1] = 3'd2;","if (b == 0) e_f = cyc; e_l = cyc; ri = 0; ri[0] = 1; ri[3:1] = 3'd2;")
rep("sn_i=0;sn_i[514]=1;","sn_i=0;sn_i[514]=1; e_bi = cyc;")
probe = """
    integer b2b = 0, e_f = -1, e_l = -1, e_x = -1, e_s = -1, e_g = -1, e_bi = -1, e_ob = -1, e_pr = -1, e_mg = -1, e_tk = -1, e_ro = -1, e_hr = -1;
    initial if ($test$plusargs("B2B")) b2b = 1;
    reg xr_d = 0;
    always @(negedge ck) if (rst_n) begin
        xr_d <= dut.u_logic.xrdy;
        if (dut.u_logic.xrdy && !xr_d) e_x = cyc;
        if (dut.u_logic.start) e_s = cyc;
        if (sn_o[512]) begin e_g = cyc;
            $display("LAT ingress first_beat=%0d last_beat=%0d xrdy=%0d start=%0d go=%0d | last->xrdy %0d start->go %0d first->go %0d (b2b %0d)",
                     e_f, e_l, e_x, e_s, e_g, e_x - e_l, e_g - e_s, e_g - e_f, b2b); end
        if (dut.mtv != 0 && e_ob < e_bi) begin e_ob = cyc; $display("LAT own_best b_i->mtx_v %0d", e_ob - e_bi); end
        if (dut.mrv != 0) e_pr = cyc;
        if (dut.u_logic.mg4) begin e_mg = cyc; $display("LAT merge last_peer_frame->mg4 %0d", e_mg - e_pr); end
        if (dut.u_logic.tk_pop) begin e_tk = cyc; $display("LAT mg4->tk_pop %0d", e_tk - e_mg); end
        if (ro[0] && ro[3:1] == 3'd5) begin e_ro = cyc; $display("LAT token mg4->ro_K_TOK %0d", e_ro - e_mg); end
        if (htx_v[0]) begin e_hr = cyc; $display("LAT host mg4->RESULT_frame_at_sink %0d", e_hr - e_mg); end
    end
"""
rep("    integer errs = 0;\n", "    integer errs = 0;\n"+probe)
rep('$display("PASS hd_ctl_physical','$display("PASS tok17_ctl_lat')
open("/srv/opentallas-scratch2/claude/tok17-head/ctl/tb_tok17_ctl_lat.sv","w").write(s)
