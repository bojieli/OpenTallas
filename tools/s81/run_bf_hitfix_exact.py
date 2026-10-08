#!/usr/bin/env python3
"""BF native pair HITFIX=1 exactness (BF rowfix closure, 2026-10-07): the full exact BF bench (tb_bfcolumn, real ROM
contents and workload) runs the candidate pair element with HITFIX=1, so its own
numerical and wake gates judge the change, while a HITFIX=0 shadow of the same element, fed the same pins,
must match it EVERY cycle (pv..ppos, busy, fault): HITFIX adds no cycle.  The element's own HITFIX_CHECK also
asserts every cycle that the registered-offset match equals the original adder match.
Negative control: +define+W10_MUTANT_FRONT_PAIR (the registered class offset off by one) must fail."""
import argparse, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 's81'))
import run_bf_pinreg_shadow as P   # noqa: E402


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
    assert src.rstrip().endswith('endmodule') and src.count('ot_s81_bf_native #(') == 1
    # candidate HITFIX=1, shadow the original (HITFIX=0), both PINREG=0 (PINREG equivalence: run_bf_pinreg_shadow.py), same-cycle compare
    src = src.replace('ot_s81_bf_native #(', 'ot_s81_bf_native #(.HITFIX(1), ', 1)
    shadow = P.SHADOW.replace('.PINREG(1)) u_shadow', '.PINREG(0), .HITFIX(0)) u_shadow')
    assert shadow != P.SHADOW
    files[pair] = src.rstrip()[:-len('endmodule')] + shadow + '\n'
    out = {'cases': {}, 'pass': True, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
           'extra_cycles': 0}
    for name, defs in (('positive', []), ('mutant_front_pair', ['+define+W10_MUTANT_FRONT_PAIR'])):
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
        cmd[1:1] = ['+define+SHADOW_MUT=1'] + defs     # SHADOW_MUT=1: same-cycle compare (no offset)
        with (w / 'build.log').open('w') as f:
            b = subprocess.run(cmd, cwd=w, stdout=f, stderr=subprocess.STDOUT)
        if b.returncode:
            out['cases'][name] = dict(ok=False, why='build failed')
            out['pass'] = False
            continue
        with (w / 'run.log').open('w') as f:
            r = subprocess.run([str(w / 'obj_bfcolumn' / 'Vtb_bfcolumn')], cwd=w, stdout=f, stderr=subprocess.STDOUT)
        log = (w / 'run.log').read_text()
        marks = [s for s in log.splitlines() if any(k in s for k in ('PASS', 'DIFF', 'PINREG', 'HITFIX', 'NUMERICAL', 'FAIL'))][:8]
        if name == 'positive':
            ok = (r.returncode == 0 and 'PASS independent-numerical BF=1' in log and 'PASS wake-source BF=1' in log
                  and 'PINREG shadow compared' in log and 'pv_cycles=0' not in log and 'HITFIX_CHECK FAIL' not in log)
        else:
            ok = r.returncode != 0 and ('DIFF' in log or 'NUMERICAL' in log or 'FAIL' in log)
        out['cases'][name] = dict(returncode=r.returncode, ok=ok, markers=marks)
        out['pass'] &= ok
        print(name, 'ok' if ok else 'UNEXPECTED', marks[:4], flush=True)
    (a.work / 'terminal.json').write_text(json.dumps(out, indent=1) + '\n')
    raise SystemExit(0 if out['pass'] else 1)


if __name__ == '__main__':
    main()
