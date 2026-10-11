#!/usr/bin/env python3
"""Exact gate: the WFC kit drives the real S81 stage sequencer (mtp-lead/kitseq, 2026-10-11; option A).

System under test (one stage die, the adopted kit configuration POSTED 1 + RD2 1 + VM_LINK 1 + VMRQ 64 + WOUTW 8):
  upstream HIDDEN messages -> dsfd_wfc_stg (kit) --VM channels, 13/13 hub stations--> dsfd_vm_wfc_ep -> VM port model
  ep t_ks (START, after every payload write is at the VM pins) --KSS stations--> dsfd_sp_seq[_h] (ot_s81_kit_seq:
  CDC queue -> ot_s81_stage_seq -> kit hand-off on the program's hop entry) --cv/cd, LC stations--> one
  ot_s81_engine_adapter per die lane (QD 8, done-credit) -> behavioural dataflow engines executing the stage program
  (tools/s81_ctrl/stage_programs.py golden trace; an op starts when its descriptor is at the engine AND its inputs are
  present: the stage input + ext, every predecessor's ACTUAL end) --dv/dt, LD stations--> sequencer;
  dsfd_sp_seq t_kd (DONE) --KDS stations--> kit f_kd -> the kit's outbound prefetch reads the 46 outbound rows.
The engine that produces the outbound hidden state (the hop entry's predecessor) commits the 46 rows to the VM write
path at its completion; they land WL fast cycles later (capture -> VM stations + VM write pipe).  The VM port model
asserts on every read that the row has no write still in flight (EARLY READ = the static-schedule assertion).
Checks (PASS): the kit bench's own (RX words in the VM at START, every outbound word / header exact, no kit fault,
NJOB out); every op of every job started once and completed; every descriptor carries its job's {user, pos, tok}
and arg; the DONE word = the job's {tok, 0, pos} (layer) / the argmax (head); no sequencer / adapter / bridge fault;
no early read.  Measured (fast 1.2 GHz cycles): per hop START (ep t_ks) -> DONE at the kit pins minus the golden
hand-off point, its split, op lateness vs the golden trace, and the read-after-write margin of the outbound rows.
Mutants: drop (dsfd_sp_seq MUT 1: 3rd START dropped), early (MUT 2: DONE at accept), early_read (WL = margin + 1).

  python3 tools/s81_ctrl/kit_seq_bench.py --out DIR [--case NAME] [--jobs N]  -> DIR/summary.json, KIT_SEQ_GATE PASS|FAIL
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_ctrl'))
import dsrom_wfc_kit_bench as K          # noqa: E402
import dsrom_mtp_rom_bench as B          # noqa: E402

PROGS = ROOT / 'results/rtl/s81_ctrl_20261008/programs'
SEQ_SRCS = ['rtl/dsrom_sys/s81_ctrl/ot_s81_kit_seq.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv',
            'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv', 'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv']

SEQ_BLOCK = r'''
    // ================================================================ kit <-> stage sequencer <-> engines (kitseq)
    localparam integer KSS = @KSS@, KDS = @KDS@, LC = @LC@, LD = @LD@, NL = 10, NOPS = 128, CMDW = 84, TAGW = 8;
    localparam integer WL = @WL@, DIV = @DIV@, HEADK = @HEAD@;
    reg sq_rst = 0, sq_loaded = 0;
    wire [USER_W+2*NW:0] q_ks; wire [NW+32:0] q_kd;
    mtp_test_relay #(.W(USER_W+2*NW+1), .HOPS(KSS)) y_kss (.clk(sclk), .rst_n(sq_rst), .in_data(ks), .out_data(q_ks));
    mtp_test_relay #(.W(NW+33), .HOPS(KDS)) y_kds (.clk(sclk), .rst_n(sq_rst), .in_data(q_kd), .out_data(kd));
    reg pw_v = 0; reg [6:0] pw_a = 0; reg [27:0] pw_d = 0; reg [7:0] prog_len = 0;
    wire [NL-1:0] s_cv, a_cv; wire [NL*CMDW-1:0] s_cd, a_cd; wire [NL-1:0] a_dv, s_dv; wire [NL*TAGW-1:0] a_dt, s_dt;
    wire sq_flt; wire [7:0] sq_fvec;
    reg am_v = 0; reg [20:0] am_tok = 0; reg [31:0] am_val = 0;
    generate if (HEADK) begin : g_h
        dsfd_sp_seq_h #(.MUT(@MUT@)) u_sq (.ck(fclk), .rst(sq_rst), .ckv(sclk), .rsv(sq_rst), .pw_v(pw_v), .pw_a(pw_a),
            .pw_d(pw_d), .prog_len(prog_len), .f_ks(q_ks), .t_kd(q_kd), .cv(s_cv), .cd(s_cd), .dv(s_dv), .dt(s_dt),
            .am_v(am_v), .am_tok(am_tok), .am_val(am_val), .flt(sq_flt), .fvec(sq_fvec));
    end else begin : g_l
        dsfd_sp_seq #(.MUT(@MUT@)) u_sq (.ck(fclk), .rst(sq_rst), .ckv(sclk), .rsv(sq_rst), .pw_v(pw_v), .pw_a(pw_a),
            .pw_d(pw_d), .prog_len(prog_len), .f_ks(q_ks), .t_kd(q_kd), .cv(s_cv), .cd(s_cd), .dv(s_dv), .dt(s_dt),
            .flt(sq_flt), .fvec(sq_fvec));
    end endgenerate
    // die stations on the command / completion nets (plain flops: pulse nets, no back-pressure)
    mtp_test_relay #(.W(NL*(CMDW+1)), .HOPS(LC)) y_cmd (.clk(fclk), .rst_n(sq_rst), .in_data({s_cv, s_cd}), .out_data({a_cv, a_cd}));
    mtp_test_relay #(.W(NL*(TAGW+1)), .HOPS(LD)) y_dn (.clk(fclk), .rst_n(sq_rst), .in_data({a_dv, a_dt}), .out_data({s_dv, s_dt}));
    // one engine adapter per lane (inside each slab master on the die)
    wire [NL-1:0] e_v, a_flt, a_on; wire [NL*CMDW-1:0] e_d; reg [NL-1:0] e_inp = 0, e_dv = 0; reg [NL*TAGW-1:0] e_dt = 0;
    genvar gl;
    generate for (gl = 0; gl < NL; gl = gl + 1) begin : g_ad
        ot_s81_engine_adapter #(.QD(8)) u_ad (.c_clk(fclk), .c_rst_n(sq_rst), .c_cmd_v(a_cv[gl]), .c_cmd_d(a_cd[gl*CMDW +: CMDW]),
            .c_done_v(a_dv[gl]), .c_done_tag(a_dt[gl*TAGW +: TAGW]), .fault(a_flt[gl]), .online(a_on[gl]),
            .e_clk(fclk), .e_rst_n(sq_rst), .e_cmd_v(e_v[gl]), .e_cmd_d(e_d[gl*CMDW +: CMDW]), .e_cmd_ready(1'b1),
            .e_inputs_present(e_inp[gl]), .e_done_v(e_dv[gl]), .e_done_tag(e_dt[gl*TAGW +: TAGW]));
    end endgenerate
    // ---- program (golden trace, durations / ext divided by DIV, golden starts re-derived ASAP) ----
    reg [159:0] img [0:NOPS-1];
    integer n_op, o_port [0:NOPS-1], o_dur [0:NOPS-1], o_ext [0:NOPS-1], o_np [0:NOPS-1], o_pr [0:NOPS-1][0:7], o_gst [0:NOPS-1];
    integer hop_op = -1, hop_pred = -1, qi, qj;
    string prog;
    // ---- per job ----
    localparam integer MJ = 256;
    integer j_u [0:MJ-1], j_p [0:MJ-1], j_t [0:MJ-1], j_t0 [0:MJ-1], j_kd [0:MJ-1], j_hop [0:MJ-1], j_slot [0:MJ-1], j_done [0:MJ-1];
    integer ast [0:MJ-1][0:NOPS-1], aend [0:MJ-1][0:NOPS-1], dsc [0:MJ-1][0:NOPS-1];
    integer nj = 0, nkd = 0, ctx_bad = 0, kd_bad = 0, dup = 0, early_rd = 0, min_margin = 1 << 30;
    integer lat_min = 1 << 30, lat_max = -(1 << 30), ovh_sum = 0, ovh_max = -(1 << 30), ovh_min = 1 << 30, n_ovh = 0;
    integer st_sum = 0, dn_sum = 0, n_iso = 0;
    // TX rows: scheduled landing (fast cycle) of the outbound rows of a job
    integer tx_due = -1, tx_job = -1;
    reg tx_pend = 0;
    function integer f_ready(input integer jb, input integer op);
        integer r, m;
        begin
            r = j_t0[jb] + o_ext[op];
            for (m = 0; m < o_np[op]; m = m + 1)
                r = (aend[jb][o_pr[op][m]] < 0) ? (1 << 30) : ((aend[jb][o_pr[op][m]] > r) ? aend[jb][o_pr[op][m]] : r);
            f_ready = r;
        end
    endfunction
    function integer f_job(input integer uu, input integer pp);
        integer x; begin f_job = -1; for (x = 0; x < nj; x = x + 1) if (j_u[x] == uu && j_p[x] == pp) f_job = x; end
    endfunction
    function integer f_lane(input integer p); f_lane = (p < 7) ? p : p - 1; endfunction
    initial begin : load
        integer m;
        if (!$value$plusargs("prog=%s", prog)) $fatal(1, "+prog=<hex> required");
        if (!$value$plusargs("nops=%d", n_op)) $fatal(1, "+nops=<n> required");
        for (qi = 0; qi < NOPS; qi = qi + 1) img[qi] = 0;
        $readmemh(prog, img);
        for (qi = 0; qi < n_op; qi = qi + 1) begin
            o_port[qi] = img[qi][143:140]; o_dur[qi] = (img[qi][139:116] + DIV - 1) / DIV; o_ext[qi] = img[qi][115:92] / DIV;
            o_np[qi] = img[qi][91:88];
            for (qj = 0; qj < 8; qj = qj + 1) o_pr[qi][qj] = img[qi][87 - 8*qj -: 8];
            o_gst[qi] = o_ext[qi];
            for (qj = 0; qj < o_np[qi]; qj = qj + 1)
                if (o_gst[o_pr[qi][qj]] + o_dur[o_pr[qi][qj]] > o_gst[qi]) o_gst[qi] = o_gst[o_pr[qi][qj]] + o_dur[o_pr[qi][qj]];
            if (o_port[qi] == 7) begin hop_op = qi; hop_pred = (o_np[qi] > 0) ? o_pr[qi][0] : -1; end
        end
        for (qi = 0; qi < MJ; qi = qi + 1) begin
            j_kd[qi] = -1; j_hop[qi] = -1; j_slot[qi] = -1; j_done[qi] = 0;
            for (qj = 0; qj < NOPS; qj = qj + 1) begin ast[qi][qj] = -1; aend[qi][qj] = -1; dsc[qi][qj] = -1; end
        end
        repeat (3) @(posedge fclk);
        sq_rst = 1;
        repeat (6) @(posedge fclk);
        prog_len = n_op;
        for (qi = 0; qi < n_op; qi = qi + 1) begin
            @(negedge fclk); pw_v = 1; pw_a = qi;
            pw_d = {4'(o_port[qi]), (o_port[qi] == 7) ? ((o_np[qi] > 0) ? 24'(8'h80 | o_pr[qi][0]) : 24'd0) : (24'(qi) ^ 24'h5A0000)};
        end
        @(negedge fclk); pw_v = 0;
        repeat (4) @(posedge fclk);
        sq_loaded = 1;
    end
    // START seen at the endpoint (stage input present): job context (slow-side block above records cu / cp / ct)
    always @(posedge sclk) if (ks[USER_W+2*NW]) begin
        j_u[nj] = ks[2*NW +: USER_W]; j_t[nj] = ks[NW +: NW]; j_p[nj] = ks[NW-1:0]; j_t0[nj] = cyc; nj = nj + 1;
    end
    // DONE at the kit pins
    always @(posedge sclk) if (kd[NW+32]) begin : kdseen
        integer x, want_t, want_v;
        x = nkd; nkd = nkd + 1;
        if (x >= nj) kd_bad = kd_bad + 1;
        else begin
            j_kd[x] = cyc;
            if (HEADK) begin want_t = 21'(j_t[x] ^ 21'h1234); want_v = 32'h3f800000 ^ j_p[x]; end
            else begin want_t = j_t[x]; want_v = j_p[x]; end
            if (kd[NW+31:32] != 21'(want_t) || kd[31:0] != 32'(want_v)) kd_bad = kd_bad + 1;
            if (hop_op >= 0) begin : ov
                integer o_;
                o_ = cyc - j_t0[x] - o_gst[hop_op];
                ovh_sum = ovh_sum + o_; n_ovh = n_ovh + 1;
                if (o_ > ovh_max) ovh_max = o_;
                if (o_ < ovh_min) ovh_min = o_;
            end
        end
    end
    // early-read assertion: the VM port model reads a row of the outbound set while its write is still in flight
    always @(posedge sclk) if (rst_n) begin : rdchk
        reg rd0, rd1;
        rd0 = (e_mv === 1'b1 && e_mwe === 1'b0 && e_mrow < TXW);
        rd1 = (e_m1v === 1'b1 && e_m1row < TXW);
        if ((rd0 || rd1) && tx_pend) begin
            if (cyc < tx_due) early_rd = early_rd + 1;
        end
        if ((rd0 || rd1) && tx_job >= 0 && !tx_pend && j_done[tx_job] == 0) begin
            if (cyc - tx_due < min_margin) min_margin = cyc - tx_due;
            j_done[tx_job] = 1;
        end
    end
    // ---- engines (everything on the falling edge: adapter outputs stable, inputs set up for the next edge) ----
    integer dq [0:NL-1][0:1023]; integer dqh [0:NL-1], dqt [0:NL-1];
    initial for (qi = 0; qi < NL; qi = qi + 1) begin dqh[qi] = 0; dqt[qi] = 0; end
    // accepted descriptors: e_v high at a rising edge (e_cmd_ready 1) -> the job starts at that edge (cycle cyc)
    always @(posedge fclk) if (sq_loaded) begin : acc
        integer l, jb, op, s_;
        reg [CMDW-1:0] c;
        for (l = 0; l < NL; l = l + 1) if (e_v[l]) begin
            c = e_d[l*CMDW +: CMDW];
            s_ = c[83]; op = c[6:0]; jb = f_job(c[82:73], c[72:52]);
            if (jb < 0 || op >= n_op || f_lane(o_port[op]) != l || c[51:31] != 21'(j_t[jb]) || c[30:7] != (24'(op) ^ 24'h5A0000))
                ctx_bad = ctx_bad + 1;
            else if (ast[jb][op] >= 0) dup = dup + 1;
            else begin
                ast[jb][op] = cyc; aend[jb][op] = cyc + o_dur[op]; j_slot[jb] = s_;
                if (cyc - j_t0[jb] - o_gst[op] < lat_min) lat_min = cyc - j_t0[jb] - o_gst[op];
                if (cyc - j_t0[jb] - o_gst[op] > lat_max) lat_max = cyc - j_t0[jb] - o_gst[op];
            end
        end
    end
    // ---- engines: completions and inputs-present on the falling edge (stable for the next rising edge) ----
    always @(negedge fclk) if (sq_loaded) begin : eng
        integer l, jb, op, k2;
        reg [CMDW-1:0] c;
        // the hand-off fired inside the controller (observed at the kit pins): the hop op's start / end (link transfer)
        for (jb = 0; jb < nj; jb = jb + 1)
            if (hop_op >= 0 && ast[jb][hop_op] < 0 && j_kd[jb] >= 0) begin
                ast[jb][hop_op] = j_kd[jb]; aend[jb][hop_op] = j_kd[jb] + o_dur[hop_op];
            end
        // completions due this cycle -> per-lane report queue; outbound rows committed at the hop predecessor's end
        am_v <= 1'b0;
        for (jb = 0; jb < nj; jb = jb + 1)
            for (op = 0; op < n_op; op = op + 1)
                if (aend[jb][op] == cyc && o_port[op] != 7) begin
                    l = f_lane(o_port[op]); dq[l][dqt[l] % 1024] = jb * NOPS + op; dqt[l] = dqt[l] + 1;
                    if (op == hop_pred) begin
                        tx_due = cyc + WL; tx_job = jb; tx_pend = 1;
                        if (HEADK) begin am_v <= 1'b1; am_tok <= 21'(j_t[jb] ^ 21'h1234); am_val <= 32'h3f800000 ^ j_p[jb]; end
                    end
                end
        e_dv <= 0;
        for (l = 0; l < NL; l = l + 1) if (dqh[l] != dqt[l]) begin
            k2 = dq[l][dqh[l] % 1024]; dqh[l] = dqh[l] + 1;
            e_dv[l] <= 1'b1; e_dt[l*TAGW +: TAGW] <= {1'(j_slot[k2 / NOPS]), 7'(k2 % NOPS)};
        end
        // inputs present for the descriptor at the head of each lane's adapter queue (start at the next rising edge)
        for (l = 0; l < NL; l = l + 1) begin
            c = e_d[l*CMDW +: CMDW]; op = c[6:0]; jb = f_job(c[82:73], c[72:52]);
            e_inp[l] <= (jb >= 0 && op < n_op) ? (f_ready(jb, op) <= cyc) : 1'b0;
        end
    end
    // outbound rows land in the VM WL cycles after their commit (hop predecessor end); lone-hop programs forward the
    // stage input: the rows are committed at START
    always @(posedge fclk) begin : txland
        integer k3;
        if (hop_pred < 0 && nj > 0 && tx_job != nj - 1 && j_t0[nj-1] >= 0) begin tx_job = nj - 1; tx_due = cyc + WL; tx_pend = 1; end
        if (tx_pend && cyc >= tx_due) begin
            for (k3 = 0; k3 < TXW; k3 = k3 + 1) vmem[k3] = word(2, 0, j_p[tx_job], j_t[tx_job], k3);
            tx_pend = 0;
        end
    end
'''

# the original stage-core reaction (START -> T_CORE -> outbound rows + DONE) is replaced by the engines above
CORE_RE = re.compile(r'        if \(ks\[USER_W\+2\*NW\]\) begin\n            if \(core_t >= 0\).*?            core_t = -1;\n        end\n', re.S)
CORE_NEW = '''        if (ks[USER_W+2*NW]) begin
            cu = ks[2*NW +: USER_W]; ct = ks[NW +: NW]; cp = ks[NW-1:0]; starts = starts + 1;
            for (k = 0; k < RXW; k = k + 1)
                if (vmem[k] !== word(1, 0, cp, ct, k)) begin
                    $display("MTP_STG FAIL: RX word %0d of (p%0d, t%0d) not in the VM at start (write / start order)", k, cp, ct);
                    $finish;
                end
            for (k = 0; k < jobs_in; k = k + 1) if (job_p[k] == cp && job_t[k] == ct && job_u[k] != cu) user_mis = user_mis + 1;
        end
'''
FINAL_RE = re.compile(r'(        \$display\("MTP_STG PASS )')
FINAL_NEW = '''        begin : kitseq_fin
            integer x, nst, nend, miss;
            nst = 0; miss = 0;
            for (x = 0; x < nj; x = x + 1) for (qi = 0; qi < n_op; qi = qi + 1) if (o_port[qi] != 7 && aend[x][qi] < 0) miss = miss + 1;
            $display("KITSEQ prog=%s nops=%0d jobs=%0d kd=%0d miss=%0d ctx_bad=%0d dup=%0d kd_bad=%0d sq_flt=%0d fvec=%0h ad_flt=%0h early_rd=%0d min_margin=%0d lat_min=%0d lat_max=%0d ovh_mean=%0.2f ovh_min=%0d ovh_max=%0d hop_gst=%0d kss=%0d kds=%0d lc=%0d ld=%0d wl=%0d div=%0d",
                     prog, n_op, nj, nkd, miss, ctx_bad, dup, kd_bad, sq_flt, sq_fvec, a_flt, early_rd, min_margin, lat_min, lat_max,
                     1.0 * ovh_sum / (n_ovh > 0 ? n_ovh : 1), ovh_min, ovh_max, (hop_op >= 0) ? o_gst[hop_op] : -1, KSS, KDS, LC, LD, WL, DIV);
            if (miss || ctx_bad || dup || kd_bad || sq_flt || a_flt != 0 || early_rd || nkd != nj) begin
                $display("MTP_STG FAIL: kitseq checks"); $finish; end
        end
\\1'''


def kitseq_tb(head, mut, kss, kds, lc, ld, wl, div):
    tb, body = K.kit_tb(1, 7)
    for a_, b_ in (('reg [NW+32:0] kd = 0;', 'wire [NW+32:0] kd;'), (' kd[NW+32] <= 1\'b0;', ''),
                   ('        repeat (8) @(posedge fclk);\n        rst_n = 1;', '        repeat (8) @(posedge fclk);\n        wait (sq_loaded);\n        rst_n = 1;')):
        assert a_ in body, a_
        body = body.replace(a_, b_, 1)
    body, n = CORE_RE.subn(lambda m: CORE_NEW, body, count=1)
    assert n == 1
    blk = SEQ_BLOCK
    for k, v in dict(KSS=kss, KDS=kds, LC=lc, LD=ld, WL=wl, DIV=div, HEAD=int(head), MUT=mut).items():
        blk = blk.replace(f'@{k}@', str(v))
    mark = '    // ---------------------------------------------------------------- downstream checker'
    assert mark in body
    body = body.replace(mark, blk + mark, 1)
    body, n = FINAL_RE.subn(FINAL_NEW, body, count=1)
    assert n == 1
    return tb, body


# name -> program, head, mutant, expect, overrides
CASES = {
    'S001': dict(prog='S001'), 'S029': dict(prog='S029'), 'S012': dict(prog='S012'), 'S058h': dict(prog='S058', head=1),
    'S000': dict(prog='S000'), 'S057': dict(prog='S057'),
    'S001_full': dict(prog='S001', div=1, njob=6), 'S029_full': dict(prog='S029', div=1, njob=4),
    'S058h_full': dict(prog='S058', head=1, div=1, njob=6),
    # station sweep (the per-hop overhead is linear in the KS / KD / command / completion stations: proof input)
    'sw_k0': dict(prog='S001', kss=0, kds=0, lc=0, ld=0), 'sw_k16': dict(prog='S001', kss=16, kds=16, lc=4, ld=4),
    'sw_l8': dict(prog='S001', kss=8, kds=8, lc=8, ld=8), 'sw_k13l12': dict(prog='S001', kss=13, kds=13, lc=12, ld=12),
    'neg_drop': dict(prog='S001', mut=1, expect='fail'),
    'neg_early': dict(prog='S001', mut=2, expect='fail'),
    'neg_early_read': dict(prog='S001', wl='margin+1', expect='fail'),
    'tight_read': dict(prog='S001', wl='margin', expect='pass'),
}
for _h in sorted(PROGS.glob('hex/S*.hex')):
    CASES.setdefault('all_' + _h.stem, dict(prog=_h.stem, head=int(_h.stem == 'S058')))
DEF = dict(head=0, mut=0, expect='pass', kss=8, kds=8, lc=4, ld=4, wl=8, div=8, njob=24)


def run(name, out, margin=None):
    c = dict(DEF, **CASES[name])
    wl = c['wl']
    if isinstance(wl, str):
        assert margin is not None, 'margin case needs the measured margin'
        wl = DEF['wl'] + margin + (1 if wl == 'margin+1' else 0)
    tb, body = kitseq_tb(c['head'], c['mut'], c['kss'], c['kds'], c['lc'], c['ld'], wl, c['div'])
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'tb.sv').write_text(body)
    hexf = PROGS / 'hex' / f"{c['prog']}.hex"
    nops = sum(1 for ln in hexf.read_text().splitlines() if ln.strip())
    mk = json.loads((PROGS / f"{c['prog']}.json").read_text())['makespan']
    maxc = 4 * c['njob'] * (mk // c['div'] + 400) + 50000       # a dropped START stalls: fail on this bound
    spec = B.cases()['stg_r1']
    srcs = [str(ROOT / s) for s in list(B.COMMON) + K.EXTRA + SEQ_SRCS] + [str(d / 'tb.sv')]
    params = dict(spec.get('params', {}), NJOB=c['njob'], MAXC=maxc)
    cmd = (['iverilog', '-g2012', '-s', tb, '-o', str(d / 'sim.vvp')] + [f'-D{x}' for x in spec.get('defines', [])]
           + [f'-P{tb}.{k}={v}' for k, v in params.items()] + srcs)
    b = subprocess.run(cmd, capture_output=True, text=True)
    (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=c['expect'], verdict='BUILD_ERROR', log=b.stderr[-1500:])
    r = subprocess.run(['vvp', '-n', str(d / 'sim.vvp'), f'+prog={hexf}', f'+nops={nops}'], capture_output=True,
                       text=True, cwd=d)
    (d / 'run.log').write_text(r.stdout + r.stderr)
    m = re.search(r'^MTP_STG (PASS|FAIL).*$', r.stdout, re.M)
    got = m.group(1).lower() if m else 'nolog'
    ks = re.search(r'^KITSEQ .*$', r.stdout, re.M)
    meas = {k: float(v) for k, v in re.findall(r'(\w+)=(-?[0-9.]+)', ks.group(0))} if ks else {}
    cyc = re.search(r'^MTP_STG_CYC .*$', r.stdout, re.M)
    return dict(case=name, prog=c['prog'], head=c['head'], mut=c['mut'], wl=wl, div=c['div'], njob=c['njob'],
                expect=c['expect'], got=got, verdict='OK' if got == c['expect'] else 'UNEXPECTED',
                result=m.group(0) if m else r.stdout[-600:], kitseq=meas, cyc=cyc.group(0) if cyc else None)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--case', action='append')
    p.add_argument('--jobs', type=int, default=8)
    a = p.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    names = a.case or list(CASES)
    first = [n for n in names if not isinstance(CASES[n].get('wl'), str)]
    later = [n for n in names if isinstance(CASES[n].get('wl'), str)]
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run(n, a.out), first))
    margin = None
    base = [r for r in recs if r['case'] == 'S001' and r['verdict'] == 'OK']
    if later:
        if not base:
            recs.append(run('S001', a.out))
            base = [recs[-1]]
        margin = int(base[0]['kitseq']['min_margin'])
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            recs += list(ex.map(lambda n: run(n, a.out, margin), later))
    pins = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in list(B.COMMON) + K.EXTRA + SEQ_SRCS}
    ok = all(r['verdict'] == 'OK' for r in recs)
    (a.out / 'summary.json').write_text(json.dumps(dict(all_ok=ok, margin_S001=margin, cases=recs, source_sha256=pins),
                                                   indent=1) + '\n')
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:16s} expect={r['expect']} {str(r.get('result', r.get('log', '')))[:150]}")
        if r.get('kitseq'):
            k = r['kitseq']
            print(f"           ovh mean {k.get('ovh_mean')} min {k.get('ovh_min')} max {k.get('ovh_max')} lat {k.get('lat_min')}..{k.get('lat_max')} margin {k.get('min_margin')}")
    npos = sum(1 for r in recs if r['expect'] == 'pass' and r['verdict'] == 'OK')
    nneg = sum(1 for r in recs if r['expect'] == 'fail' and r['verdict'] == 'OK')
    print(f"KIT_SEQ_GATE {'PASS' if ok else 'FAIL'} positives={npos} negatives={nneg}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
