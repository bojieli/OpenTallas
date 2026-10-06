#!/usr/bin/env python3
"""BF native pair PINREG=1 exactness: inside the full exact BF bench (tb_bfcolumn, real ROM contents and workload),
a PINREG=1 shadow of the candidate pair element is fed the candidate's own pin inputs; every cycle its pv..ppos must
equal the candidate's one cycle earlier and its busy/fault two cycles earlier. The candidate itself (PINREG=0) still
passes the bench's numerical and wake gates. Negatives: compare without the offset; one xb_d bit mis-staged."""
import argparse, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

SHADOW = '''
    // PINREG=1 shadow (run_bf_pinreg_shadow.py): same pins, compared at +1 (outputs) / +2 (busy, fault)
    wire [1:0] s_pv; wire [63:0] s_pval; wire [31:0] s_prow; wire [9:0] s_pseg, s_pnseg; wire [1:0] s_perr; wire [5:0] s_ppos;
    wire s_busy, s_fault; reg [1023:0] s_xbd1; always @(posedge clk) s_xbd1 <= xb_d;
    wire [1023:0] s_xb_d = (`SHADOW_MUT == 2) ? {xb_d[1023:1], s_xbd1[0]} : xb_d;
    ot_s81_bf_native #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NB(2), .MTP(MTP), .EARLY(EARLY),
                      .FAST(FAST), .PP(PP), .BP(BP), .FRONT_PAR(0), .FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX), .WAKE_REG(WAKE_REG), .GRADUAL_RNE(GRADUAL_RNE), .INSTANCE(INSTANCE), .PINREG(1)) u_shadow (
        .clk(clk), .rst_n(rst_n), .cfg_v(c_v), .cfg_a(c_a), .cfg_d(c_d),
        .go(go_e), .go_bf(go_bf), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv), .xb_u(xb_u), .xb_d(s_xb_d),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0),
        .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .ppos(s_ppos),
        .pv(s_pv), .pval(s_pval), .prow(s_prow), .pseg(s_pseg), .pnseg(s_pnseg), .perr(s_perr),
        .busy(s_busy), .fault(s_fault));
    // pv-qualified view: a lane's data fields count only in a cycle its pv is set (the element captures o_val/o_row/..
    // every gated edge; after an async mid-test reset the unqualified data of an idle lane may hold a different stale word)
    function automatic [125:0] s_q(input [125:0] o);
        integer m; s_q = o;
        for (m = 0; m < 2; m = m + 1) if (!o[124 + m]) begin
            s_q[60 + 32*m +: 32] = 0; s_q[28 + 16*m +: 16] = 0; s_q[18 + 5*m +: 5] = 0; s_q[8 + 5*m +: 5] = 0;
            s_q[6 + m] = 0; s_q[3*m +: 3] = 0;
        end
    endfunction
    reg [125:0] s_o1; reg [1:0] s_b, s_f; integer s_n = 0, s_k = 0, s_pvn = 0; reg s_arm = 1'b0;
    always @(posedge clk) begin
        s_o1 <= {pv, pval, prow, pseg, pnseg, perr, ppos}; s_b <= {s_b[0], e_busy}; s_f <= {s_f[0], fault};
        // async mid-test resets (reset_now): re-arm only once both copies have run 4 cycles past the release
        if (!rst_n) begin s_arm <= 1'b0; s_k <= 0; end else begin s_k <= s_k + 1; if (s_k > 3) s_arm <= 1'b1; end
        s_n <= s_n + 1;
        if (s_arm && rst_n) begin
            if ((`SHADOW_MUT == 1 ? s_q({s_pv, s_pval, s_prow, s_pseg, s_pnseg, s_perr, s_ppos}) !== s_q({pv, pval, prow, pseg, pnseg, perr, ppos})
                                  : s_q({s_pv, s_pval, s_prow, s_pseg, s_pnseg, s_perr, s_ppos}) !== s_q(s_o1)) ||
                s_busy !== (`SHADOW_MUT == 1 ? e_busy : s_b[1]) || s_fault !== (`SHADOW_MUT == 1 ? fault : s_f[1]))
                begin $display("PINREG_DETAIL o=%0d busy=%b/%b/%b fault=%b/%b/%b pv=%b/%b", {s_pv, s_pval, s_prow, s_pseg, s_pnseg, s_perr, s_ppos} !== s_o1,
                    s_busy, s_b[1], e_busy, s_fault, s_f[1], fault, s_pv, s_o1[125:124]);
                $fatal(1, "DIFF PINREG shadow cycle=%0d", s_n); end
            if (|s_pv) s_pvn = s_pvn + 1;
        end
    end
    final $display("PINREG shadow compared cycles=%0d pv_cycles=%0d", s_n, s_pvn);
endmodule'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=8)
    p.add_argument('--only', nargs='*')
    p.add_argument('--verilator', default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
    a = p.parse_args()
    prep = a.work / 'prep'
    if not (prep / 'prepared.json').exists():
        subprocess.run([sys.executable, str(ROOT / 'tools/s81/run_bf_native_exact.py'), '--prepare-only', '--work', str(prep)], check=True)
    d = json.loads((prep / 'prepared.json').read_text())
    files, base = d['files'], d['base']
    pair = 'cand_ot_v41_pair_w17w10.sv'
    src = files[pair]
    assert src.rstrip().endswith('endmodule') and 'ot_s81_bf_native #(' in src
    files[pair] = src.rstrip()[:-len('endmodule')] + SHADOW + '\n'
    out = {'cases': {}, 'pass': True}
    for name, mut in (('positive', 0), ('no_offset', 1), ('bit_mis_staged', 2)):
        if a.only and name not in a.only: continue
        w = a.work / name; w.mkdir(parents=True, exist_ok=True)
        for n, t in files.items(): (w / n).write_text(t)
        cmd = list(base); cmd[0] = a.verilator; cmd[cmd.index('-j') + 1] = str(a.jobs)
        cmd = [str(prep / 'dsrom_actual_element_numerical_rom.cpp') if x.startswith('/ABS/FRESH/') else x for x in cmd]
        cmd.insert(1, f'+define+SHADOW_MUT={mut}')
        with (w / 'build.log').open('w') as f: b = subprocess.run(cmd, cwd=w, stdout=f, stderr=subprocess.STDOUT)
        if b.returncode: out['cases'][name] = dict(ok=False, why='build failed'); out['pass'] = False; continue
        with (w / 'run.log').open('w') as f: r = subprocess.run([str(w / 'obj_bfcolumn' / 'Vtb_bfcolumn')], cwd=w, stdout=f, stderr=subprocess.STDOUT)
        log = (w / 'run.log').read_text()
        marks = [s for s in log.splitlines() if 'PASS' in s or 'DIFF' in s or 'PINREG' in s][:6]
        ok = (r.returncode == 0 and 'PASS independent-numerical BF=1' in log and 'PASS wake-source BF=1' in log
              and 'PINREG shadow compared' in log and 'pv_cycles=0' not in log) if mut == 0 else (r.returncode != 0 and 'DIFF PINREG' in log)
        out['cases'][name] = dict(returncode=r.returncode, ok=ok, markers=marks); out['pass'] &= ok
        print(name, 'ok' if ok else 'UNEXPECTED', marks[:3], flush=True)
    (a.work / 'terminal.json').write_text(json.dumps(out, indent=1) + '\n')
    raise SystemExit(0 if out['pass'] else 1)


if __name__ == '__main__':
    main()
