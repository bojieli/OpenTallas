#!/usr/bin/env python3
"""Transaction-level exactness bench for BF native pair variants (BF rowfix closure, 2026-10-07).

Inside the full exact BF bench (tb_bfcolumn: real ROM contents, workload, numerical + wake gates), the candidate pair
element stays the ORIGINAL element (HITFIX 0, PINREG 0, cycle-exact against the reference, so the bench's own oracle
judges the workload), and a SHADOW instance of the variant under test is fed the same pins.  A scoreboard records,
per macro lane, every partial {pval, prow, pseg, pnseg, perr, ppos} the original emits (pv) and every partial the
shadow emits, in order, and requires the two sequences to be identical (same count > 0, same values, same order);
busy must be low and fault never set on both at the end.  Latency may differ (transaction level, owner rule 1).

  --variant half   : shadow = HITFIX 1, PINREG 1, HALF 1 on a 2x clock (clkf, edges 100 ps before each clk edge,
                     so a gated (slow) edge samples exactly what the reference samples at its rising edge); the
                     shadow reset is released half a cycle later so its gated edges are the ones before clk rises.
  --variant recut  : shadow = HITFIX 1, PINREG 1, RECUT 1 on clk.

Negatives (must FAIL): half: +define+W10_MUTANT_FRONT_PAIR (shadow HITFIX class offset off by one); recut: QP_MUTANT_DP (x-need pair offset); and a
variant-specific mutant (half: BF_HALF_MUTANT_PV, pv not qualified to the slow cycle; recut: W10_MUTANT_RECUT).
The candidate sources are refreshed from this worktree (module names prefixed cand_ like the prepared package)."""
import argparse, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

# prepared cand file -> worktree source
SRC = {'cand_ot_v41_rom_elem_w10.sv': 'rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv',
       'cand_ot_v41_bf16_lanes2.sv': 'rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv',
       'cand_ot_v41_bmul2_rne_prepare.sv': 'rtl/v41rom/ot_v41_bmul2_rne_prepare.sv',
       'cand_ot_v41_bmul_subnormal_rne_prepare.sv': 'rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv',
       'cand_ot_v41_segtree2.sv': 'rtl/v41rom/ot_v41_segtree2.sv', 'cand_ot_v41_chain2.sv': 'rtl/v41rom/ot_v41_chain2.sv',
       'cand_ot_v41_fadd.sv': 'rtl/v41rom/ot_v41_fadd.sv', 'cand_ot_v41_bterm2_w10.sv': 'rtl/v41rom/ot_v41_bterm2_w10.sv',
       'cand_ot_prefix.sv': 'rtl/common/ot_prefix.sv'}
# recut: the q-element and its re-cut modules (not in the prepared package), compiled as extra cand-namespace files
EXTRA = ['ot_v41_rom_elem_qx_w10', 'ot_v41_chain2u2', 'ot_v41_kreg', 'ot_v41_chain3', 'ot_v41_chain4', 'ot_v41_fadd2', 'ot_v41_bterm3_w10',
         'ot_v41_bterm4_w10', 'ot_v41_bterm5_w10', 'ot_v41_segtree3', 'ot_v41_segtree4', 'ot_v41_segtree5', 'ot_v41_segtree6']

SHADOW = '''
    // ---- transaction shadow (tools/s81/bf_txn_bench.py, variant @VAR@) ----
    wire [1:0] s_pv; wire [63:0] s_pval; wire [31:0] s_prow; wire [9:0] s_pseg, s_pnseg; wire [1:0] s_perr; wire [5:0] s_ppos;
    wire s_busy, s_fault, s_hph;
    reg s_rst_n = 1'b0;
@CLOCK@
    ot_s81_bf_native #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NB(2), .MTP(MTP), .EARLY(EARLY),
                      .FAST(FAST), .PP(PP), .BP(BP), .FRONT_PAR(0), .FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX), .WAKE_REG(WAKE_REG),
                      .GRADUAL_RNE(GRADUAL_RNE), .INSTANCE(INSTANCE), .PINREG(1), .HITFIX(1)@PARAMS@) u_shadow (
        .clk(s_clk), .rst_n(s_rst_n), .cfg_v(c_v), .cfg_a(c_a), .cfg_d(c_d),
        .go(go_e), .go_bf(go_bf), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv), .xb_u(xb_u), .xb_d(xb_d),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0),
        .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .ppos(s_ppos),
        .pv(s_pv), .pval(s_pval), .prow(s_prow), .pseg(s_pseg), .pnseg(s_pnseg), .perr(s_perr),
        .busy(s_busy), .fault(s_fault), .hph(s_hph));
    function automatic [61:0] t_slice(input integer m, input [63:0] v, input [31:0] r, input [9:0] sg, input [9:0] ns,
                                      input [1:0] er, input [5:0] po);
        t_slice = {v[32*m +: 32], r[16*m +: 16], sg[5*m +: 5], ns[5*m +: 5], er[m], po[3*m +: 3]};
    endfunction
    reg [61:0] t_ref [0:1][0:8191];
    reg [61:0] t_sh  [0:1][0:8191];
    integer t_nr [0:1]; integer t_ns [0:1]; integer t_cmp = 0, t_im;
    realtime t_tr [0:1][0:8191]; realtime t_ts [0:1][0:8191];
    reg t_rf = 1'b0, t_sf = 1'b0;
    initial begin t_nr[0] = 0; t_nr[1] = 0; t_ns[0] = 0; t_ns[1] = 0; end
    always @(posedge clk) begin
        if (fault) t_rf <= 1'b1;
        for (t_im = 0; t_im < 2; t_im = t_im + 1) if (rst_n && pv[t_im]) begin
            t_ref[t_im][t_nr[t_im]] = t_slice(t_im, pval, prow, pseg, pnseg, perr, ppos); t_tr[t_im][t_nr[t_im]] = $realtime;
            if (t_ns[t_im] > t_nr[t_im]) begin
                if (t_sh[t_im][t_nr[t_im]] !== t_ref[t_im][t_nr[t_im]]) $fatal(1, "DIFF TXN lane=%0d n=%0d ref=%h shadow=%h",
                    t_im, t_nr[t_im], t_ref[t_im][t_nr[t_im]], t_sh[t_im][t_nr[t_im]]);
                t_cmp = t_cmp + 1;
            end
            t_nr[t_im] = t_nr[t_im] + 1;
        end
    end
    always @(posedge s_clk) begin
        if (s_fault) t_sf <= 1'b1;
        for (t_im = 0; t_im < 2; t_im = t_im + 1) if (s_rst_n && s_pv[t_im]) begin
            t_sh[t_im][t_ns[t_im]] = t_slice(t_im, s_pval, s_prow, s_pseg, s_pnseg, s_perr, s_ppos); t_ts[t_im][t_ns[t_im]] = $realtime;
            if (t_nr[t_im] > t_ns[t_im]) begin
                if (t_sh[t_im][t_ns[t_im]] !== t_ref[t_im][t_ns[t_im]]) $fatal(1, "DIFF TXN lane=%0d n=%0d ref=%h shadow=%h",
                    t_im, t_ns[t_im], t_ref[t_im][t_ns[t_im]], t_sh[t_im][t_ns[t_im]]);
                t_cmp = t_cmp + 1;
            end
            t_ns[t_im] = t_ns[t_im] + 1;
        end
    end
    final begin : t_fin
        realtime lag, lmin, lmax, lsum; integer n, m;
        lmin = 1e18; lmax = -1e18; lsum = 0; n = 0;
        for (m = 0; m < 2; m = m + 1) for (t_im = 0; t_im < t_nr[m] && t_im < t_ns[m]; t_im = t_im + 1) begin
            lag = t_ts[m][t_im] - t_tr[m][t_im]; n = n + 1; lsum = lsum + lag;
            if (lag < lmin) lmin = lag; if (lag > lmax) lmax = lag;
        end
        // lag in ns (pair-file timescale); one cycle = 0.833 ns
        if (n > 0) $display("TXN LAG ns min=%0.3f max=%0.3f mean=%0.3f n=%0d", lmin, lmax, lsum / n, n);
        $display("TXN ref=%0d/%0d shadow=%0d/%0d compared=%0d fault=%b/%b busy=%b/%b", t_nr[0], t_nr[1], t_ns[0], t_ns[1], t_cmp,
                 t_rf, t_sf, busy, s_busy);
        if (t_nr[0] != t_ns[0] || t_nr[1] != t_ns[1] || t_nr[0] == 0 || t_cmp != t_nr[0] + t_nr[1] || t_rf || t_sf || s_busy)
            $display("DIFF TXN FINAL");
        else $display("TXN MATCH");
    end
endmodule'''

CLOCK_HALF = '''    // 2x clock: a pulse 316.5 ps after every clk edge = 100.5 ps before the next edge (no same-step race with the clk
    // flops); the shadow reset is released 416.5 ps after rst_n so its gated edges are the ones just before clk rises
    reg s_ca = 1'b0, s_cb = 1'b0;
    always @(posedge clk) begin #0.3165; s_ca = 1'b1; #0.2; s_ca = 1'b0; end
    always @(negedge clk) begin #0.3165; s_cb = 1'b1; #0.2; s_cb = 1'b0; end
    wire s_clk = s_ca | s_cb;
    always @(rst_n) if (!rst_n) s_rst_n = 1'b0; else begin #0.4165; if (rst_n) s_rst_n = 1'b1; end'''
CLOCK_SAME = '''    wire s_clk = clk;
    always @(rst_n) s_rst_n = rst_n;'''


def cand_names(files):
    return sorted({m for t in files.values() for m in re.findall(r'^\s*module\s+cand_(\w+)', t, re.M)}, key=len, reverse=True)


def candify(text, names):
    for n in names:
        text = re.sub(r'(?<![\w$])' + n + r'(?![\w$])', 'cand_' + n, text)
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', choices=('half', 'recut'), required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--level', type=int, default=2, help='recut: RECUT level (1 q-element as is, 2 + BF lanes re-cut)')
    p.add_argument('--prep', type=Path, help='prepared package dir (default <work>/prep, built if missing)')
    p.add_argument('--jobs', type=int, default=8)
    p.add_argument('--only', nargs='*')
    p.add_argument('--verilator', default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
    a = p.parse_args()
    prep = a.prep or a.work / 'prep'
    if not (prep / 'prepared.json').exists():
        subprocess.run([sys.executable, str(ROOT / 'tools/s81/run_bf_native_exact.py'), '--prepare-only', '--work', str(prep)], check=True)
    d = json.loads((prep / 'prepared.json').read_text())
    files, base = d['files'], d['base']
    names = cand_names(files)
    refreshed = []
    for f, src in SRC.items():
        t = candify((ROOT / src).read_text(), names)
        if t != files[f]:
            refreshed.append(f)
        files[f] = t
    wrapper = (ROOT / 'rtl/s81/ot_s81_bf_native.sv').read_text()
    wrapper = re.sub(r'(?<![\w$])ot_v41_rom_elem_w10(?![\w$])', 'cand_ot_v41_rom_elem_w10', wrapper)
    wrapper = re.sub(r'(?<![\w$])ot_hdc_cg(?![\w$])', 'cand_ot_hdc_cg', wrapper)
    files['ot_s81_bf_native.sv'] = wrapper
    # the wrapper holds the original element in generate block g_orig (RECUT = 0)
    tb = 'tb_dsrom_actual_element_rne_wake.sv'
    if 'cand_dut.u_e.g_orig.u_elem.' not in files[tb]:
        files[tb] = files[tb].replace('cand_dut.u_e.u_elem.', 'cand_dut.u_e.g_orig.u_elem.')
    extra = []
    for n in EXTRA:
        f = 'x_' + n + '.sv'
        files[f] = candify((ROOT / 'rtl/v41rom' / (n + '.sv')).read_text(), names)
        extra.append(f)
    pair = 'cand_ot_v41_pair_w17w10.sv'
    src = files[pair]
    assert src.rstrip().endswith('endmodule') and src.count('ot_s81_bf_native #(') == 1
    if a.variant == 'half':
        sh = SHADOW.replace('@CLOCK@', CLOCK_HALF).replace('@PARAMS@', ', .HALF(1)')
        muts = [('mutant_front_pair', ['+define+W10_MUTANT_FRONT_PAIR']), ('mutant_half_pv', ['+define+BF_HALF_MUTANT_PV'])]
    else:
        sh = SHADOW.replace('@CLOCK@', CLOCK_SAME).replace('@PARAMS@', f', .RECUT({a.level})')
        muts = [('mutant_dp', ['+define+QP_MUTANT_DP']), ('mutant_recut', ['+define+W10_MUTANT_RECUT'])]
        if a.level >= 3: muts.append(('mutant_u2', ['+define+W10_MUTANT_U2']))
    files[pair] = src.rstrip()[:-len('endmodule')] + sh.replace('@VAR@', a.variant) + '\n'
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--', 'rtl', 'tools/s81'], cwd=ROOT, text=True).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit, dirty = (ROOT / 'SOURCE_COMMIT').read_text().strip() if (ROOT / 'SOURCE_COMMIT').exists() else 'unknown', None
    out = {'variant': a.variant, 'cases': {}, 'pass': True, 'refreshed': refreshed, 'source_commit': commit, 'dirty': dirty}
    pos = ['+define+QP_CHECK', '+define+QT_CHECK'] if a.variant == 'recut' else []
    for name, defs in [('positive', pos)] + muts:
        if a.only and name not in a.only:
            continue
        w = a.work / name
        w.mkdir(parents=True, exist_ok=True)
        for n, t in files.items():
            (w / n).write_text(t)
        cmd = list(base)
        cmd[0] = a.verilator
        cmd[cmd.index('-j') + 1] = str(a.jobs)
        cmd = [str(prep / 'dsrom_actual_element_numerical_rom.cpp') if x.startswith('/ABS/FRESH/') else x for x in cmd]
        cmd[1:1] = defs
        cmd += extra
        with (w / 'build.log').open('w') as f:
            b = subprocess.run(cmd, cwd=w, stdout=f, stderr=subprocess.STDOUT)
        if b.returncode:
            out['cases'][name] = dict(ok=False, why='build failed')
            out['pass'] = False
            print(name, 'BUILD FAILED', flush=True)
            continue
        with (w / 'run.log').open('w') as f:
            r = subprocess.run([str(w / 'obj_bfcolumn' / 'Vtb_bfcolumn')], cwd=w, stdout=f, stderr=subprocess.STDOUT)
        log = (w / 'run.log').read_text()
        marks = [s for s in log.splitlines() if any(k in s for k in ('PASS', 'DIFF', 'TXN', 'NUMERICAL', 'FAIL', 'Fatal'))][:8]
        if name == 'positive':
            ok = (r.returncode == 0 and 'PASS independent-numerical BF=1' in log and 'PASS wake-source BF=1' in log
                  and 'TXN MATCH' in log and 'DIFF' not in log and 'HITFIX_CHECK FAIL' not in log)
        else:
            ok = r.returncode != 0 or 'DIFF TXN' in log
        out['cases'][name] = dict(returncode=r.returncode, ok=ok, markers=marks)
        out['pass'] &= ok
        print(name, 'ok' if ok else 'UNEXPECTED', marks[:4], flush=True)
    (a.work / 'terminal.json').write_text(json.dumps(out, indent=1) + '\n')
    raise SystemExit(0 if out['pass'] else 1)


if __name__ == '__main__':
    main()
