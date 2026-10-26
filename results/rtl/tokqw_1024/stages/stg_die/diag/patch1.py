p = "/srv/opentallas-scratch2/claude/tok-qw/s8exp/dbg/src/tb_s8dbg.sv"; s = open(p).read()
G = "`D.u_suvm.u_vm8q.u_pg."
add = ('            if ((cyc >= 50 && cyc < 75) || (cyc >= 1570 && cyc < 1600)) $fdisplay(lg, "%0d P ptw_w %b twp_w %b twp_a %h '
       'twp_d0[36:0] %h pp_re %b pp_idx %h |p_rd %b |pcap %b pg.p_q[36:0] %h vm8q.p_q[36:0] %h c_si[36:0] %h acc0 %b", cyc, '
       f'{G}ptw_w, {G}twp_w, {G}twp_a, {G}twp_d0[36:0], {G}pp_re, {G}pp_idx, |{G}p_rd, |{G}pcap, {G}p_q[36:0], '
       '`D.u_suvm.u_vm8q.p_q[36:0], `D.u_suvm.u_su8.c_si[36:0], `D.u_suvm.u_su8.acc_k[0]);\n')
assert "P ptw_w" not in s
s = s.replace("            clear;\n", add + "            clear;\n", 1)
open(p, "w").write(s)
