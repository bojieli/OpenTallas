import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:80])
    t = t.replace(old, new)
hdr = """// TOKSIM-S81C/GATH (10-19): OBSERVATION COPY of tb_dsdv_svc_rs.sv (bench only; no RTL, every check unchanged).
// Adds (a) +sel_gap=<n>: with +static_io=1 the q stream holds n cycles before the SEL_IDS header (the compiled issue of
// the selection after the window load; default 0 = back to back, as tb_dsdv_svc_rs), and (b) the GATH_T line: the tb
// cycles at which the WIN_LOAD / SEL_IDS headers and the last SEL_IDS word are driven on both entries' q pins, and per
// HBM read class (address >= the job's compressed-row base SB = owned selected rows; below = window ring) the first /
// last request and the cycle the LAST BEAT of the last read is driven on the slice's r_data (lands the next edge).
"""
t = hdr + t
rep("module tb_dsdv_svc_rs;", "module tb_toksim_gath;")
rep("    integer static_io = 0, start2 = 8192; bit j0_checked = 0;",
    "    integer static_io = 0, start2 = 8192; bit j0_checked = 0;\n"
    "    integer sel_gap = 0, sel_wait = 0, wl_qi = -1, sel_qi = -1, sel_last_qi = -1, t_wl = -1, t_sel = -1, t_sel_last = -1;\n"
    "    integer g_orq_f = -1, g_orq_l = -1, g_odn_l = -1, g_on = 0, g_wrq_f = -1, g_wrq_l = -1, g_wdn_l = -1, g_wn = 0, g_obeats = 0;")
rep("        if ($value$plusargs(\"static_io=%d\", static_io)) ;",
    "        if ($value$plusargs(\"static_io=%d\", static_io)) ;\n        if ($value$plusargs(\"sel_gap=%d\", sel_gap)) ;")
rep("        qw[nq] = hdr(4'd2, 0, sp);", "        wl_qi = nq; qw[nq] = hdr(4'd2, 0, sp);")
rep("            qw[nq] = hdr(4'd7, 12'(n), sp); nq = nq + 1;",
    "            sel_qi = nq; sel_last_qi = nq + n; qw[nq] = hdr(4'd7, 12'(n), sp); nq = nq + 1;")
rep("                if (static_io != 0 || ($urandom % 8) != 0) begin q_v <= 1; q_d <= qw[qi]; qi = qi + 1; if (qi == nq_go) t_pre = cyc; end",
    "                if (static_io != 0 && qi == sel_qi && sel_wait < sel_gap) sel_wait = sel_wait + 1;\n"
    "                else if (static_io != 0 || ($urandom % 8) != 0) begin q_v <= 1; q_d <= qw[qi];\n"
    "                    if (cur_job == 0 && qi == wl_qi) t_wl = cyc; if (cur_job == 0 && qi == sel_qi) t_sel = cyc; if (cur_job == 0 && qi == sel_last_qi) t_sel_last = cyc;\n"
    "                    qi = qi + 1; if (qi == nq_go) t_pre = cyc; end")
rep("                pq_n[pc] = pq_n[pc] + 1;\n                if (pq_n[pc] > 8) cred_err = cred_err + 1;",
    "                pq_n[pc] = pq_n[pc] + 1;\n                if (pq_n[pc] > 8) cred_err = cred_err + 1;\n"
    "                if (cur_job == 0 && !rq[sd][341*pp + 1]) begin\n"
    "                    if (rq[sd][341*pp + 2 +: 30] >= 30'(cur_sb)) begin if (g_orq_f < 0) g_orq_f = cyc; g_orq_l = cyc; end\n"
    "                    else begin if (g_wrq_f < 0) g_wrq_f = cyc; g_wrq_l = cyc; end\n"
    "                end")
rep("                        pq_b[pc] = 0; pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1; rk[sd][pp] <= 1'b1;",
    "                        if (cur_job == 0) begin if (w341[31:2] >= 30'(cur_sb)) begin g_odn_l = cyc; g_on = g_on + 1; g_obeats = g_obeats + w341[35:32]; end\n"
    "                                                else begin g_wdn_l = cyc; g_wn = g_wn + 1; end end\n"
    "                        pq_b[pc] = 0; pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1; rk[sd][pp] <= 1'b1;")
rep("            $display(\"SVCRS_SCHED T=%0d",
    "            $display(\"GATH_T static_io=%0d sel_gap=%0d lat=%0d t_wl=%0d t_sel=%0d t_sel_last=%0d own_rq_first=%0d own_rq_last=%0d own_done_last=%0d own_reads=%0d own_beats=%0d win_rq_first=%0d win_rq_last=%0d win_done_last=%0d win_reads=%0d gather_span=%0d winload_span=%0d go=%0d\",\n"
    "                static_io, sel_gap, lat, t_wl, t_sel, t_sel_last, g_orq_f, g_orq_l, g_odn_l, g_on, g_obeats, g_wrq_f, g_wrq_l, g_wdn_l, g_wn,\n"
    "                g_odn_l - t_sel + 1, g_wdn_l - t_wl + 1, go_cyc);\n"
    "            $display(\"SVCRS_SCHED T=%0d")
open(dst, 'w').write(t)
print('ok', len(t))
