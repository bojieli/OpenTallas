#!/usr/bin/env python3
"""Exactness gate for the pipelined true-credit receiver (ot_ha2_truecredit_receiver_p).

Runs the unchanged mechanism bench (tb_ha2_truecredit) and reset bench (tb_ha2_truecredit_reset)
with the receiver instance swapped to the pipelined module (the bench text is copied with the
module name replaced; the committed benches are not edited). Positive cases must PASS; negative
mutants (sender reservations, corrupted retire/forward ids, misaligned read ring) must fault.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
D = 'rtl/hbm_accel/ha2_ar/'
LIBS = [D+n+'.sv' for n in ('ot_ha2_prims', 'ot_ha2_parent_quiet_prims', 'ot_ha2_truecredit',
                            'ot_ha2_truecredit_rxp')]
BENCHES = {'tb_ha2_truecredit': D+'tb_ha2_truecredit.sv',
           'tb_ha2_truecredit_reset': D+'tb_ha2_truecredit_reset.sv'}


def swapped(out, top):
    text = (ROOT/BENCHES[top]).read_text()
    assert text.count('ot_ha2_truecredit_receiver #') == 1, top
    path = out/(top+'_rxp.sv')
    path.write_text(text.replace('ot_ha2_truecredit_receiver #', 'ot_ha2_truecredit_receiver_p #'))
    return path


def run(out, top, name, params, files):
    binary = out/(name+'.vvp')
    cmd = ['iverilog', '-g2012', '-s', top, *[f'-P{top}.{k}={v}' for k, v in params.items()],
           '-o', str(binary), *LIBS, str(files)]
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (out/(name+'.compile.log')).write_text(b.stdout+b.stderr)
    if b.returncode:
        raise RuntimeError(name+': compile failure is not a verdict\n'+b.stdout+b.stderr)
    r = subprocess.run(['vvp', str(binary)], cwd=ROOT, capture_output=True, text=True)
    text = r.stdout+r.stderr
    (out/(name+'.log')).write_text(text)
    return r.returncode, text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    out = p.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pinned = LIBS+list(BENCHES.values())+['tools/ha2_truecredit_rxp_gate.py']
    pins = {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pinned}
    tb = swapped(out, 'tb_ha2_truecredit')
    tbr = swapped(out, 'tb_ha2_truecredit_reset')
    checks = {}
    cases = [(f'f{f}_r{r}', f, r, 0, 192, 16) for f, r in itertools.product([0, 1, 7, 64], repeat=2)]
    cases += [('sequence_wrap', 7, 64, 0, 640, 8),
              ('ignore_reservations', 7, 7, 1, 192, 16),
              ('corrupt_retire_id', 7, 7, 2, 192, 16),
              ('corrupt_forward_id', 7, 7, 3, 192, 16),
              ('misaligned_read_ring', 7, 7, 4, 192, 16)]
    for name, fwd, ret, mutant, rows, tag in cases:
        rc, text = run(out, 'tb_ha2_truecredit', name,
                       dict(FWD=fwd, RET=ret, MUTANT=mutant, ROWS=rows, TAGW=tag), tb)
        caught = 'TRUECREDIT_FAULT' in text or (mutant == 4 and 'TRUECREDIT_DATA' in text)
        good = (rc != 0 and caught) if mutant else (
            rc == 0 and 'PASS_TRUECREDIT ' in text)
        checks[name] = dict(passed=good, returncode=rc, mutant=mutant, output=text[-2000:])
        print(name, 'PASS' if good else 'FAIL', flush=True)
    for name, fwd, ret, mutant, marker in [
            ('reset_candidate_flight', 7, 7, 0, 'PASS_TRUECREDIT_RESET'),
            ('reset_long_flight', 64, 64, 0, 'PASS_TRUECREDIT_RESET'),
            ('reset_return_pipe_removed', 7, 7, 1, 'RESET_STALE_RETURN_PIPE'),
            ('reset_stale_credit', 7, 7, 2, 'RESET_PROTOCOL_FAULT epoch=1 tx=1')]:
        rc, text = run(out, 'tb_ha2_truecredit_reset', name, dict(FWD=fwd, RET=ret, MUTANT=mutant), tbr)
        good = marker in text and 'RESET_INTERRUPTION ' in text and (rc != 0 if mutant else rc == 0)
        checks[name] = dict(passed=good, returncode=rc, mutant=mutant, output=text[-2000:])
        print(name, 'PASS' if good else 'FAIL', flush=True)
    assert pins == {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pinned}
    record = dict(passed=all(c['passed'] for c in checks.values()), checks=checks, source_sha256=pins,
                  scope='Pipelined receiver in the unchanged full-width 2x544 mechanism and reset benches; '
                        'transaction-exact (+1 arrival cycle, registered quiet/fault).')
    (out/'terminal.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASSED' if record['passed'] else 'FAILED')
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
