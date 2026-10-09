#!/usr/bin/env python3
"""safe-hbm S-C4 gate (2026-10-08): SRAM-queue true-credit receiver ot_ha2_truecredit_receiver_s.

Runs the credit-ready mechanism and reset benches (tb_ha2_truecredit_cr / _cr_reset, unchanged files) on private
copies whose only edit is the DUT module name receiver_p -> receiver_s; the macro model is the 64x512 1R1W SRAM.
Positives: the same fwd/ret x credit depth x credit-return delay grid as tools/ha2_credit_ready_gate.py --part rx,
tag wrap, and the two reset flights.  Negatives (must be detected): sender reservations (1), corrupt retire id (2),
corrupt forward id (3), read address off by one (4), credit over-issue (5), spurious credit (6), read overtakes the
WREG write (7), credit-return pulses dropped (8: deadlock), plus the three reset mutants.  Mutants 4 and 7 deliver a wrong slot; the receiver's own retire-tag check catches
it first (fail-closed rx fault), which is the detection the gate requires.  Records elapsed cycles per case.  Icarus.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
D = 'rtl/hbm_accel/ha2_ar/'
MACRO = 'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v'
LIBS = [D+n+'.sv' for n in ('ot_ha2_prims', 'ot_ha2_parent_quiet_prims', 'ot_ha2_truecredit', 'ot_ha2_truecredit_rxs')]+[MACRO]
TB = D+'tb_ha2_truecredit_cr.sv'
TBR = D+'tb_ha2_truecredit_cr_reset.sv'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_tb(out, src):
    text = (ROOT/src).read_text()
    assert text.count('\n ot_ha2_truecredit_receiver_p #(') == 1, src
    dst = out/Path(src).name
    dst.write_text(text.replace('\n ot_ha2_truecredit_receiver_p #(', '\n ot_ha2_truecredit_receiver_s #('))
    return str(dst)


def icarus(out, top, name, params, files):
    binary = out/(name+'.vvp')
    cmd = ['iverilog', '-g2012', '-s', top, *[f'-P{top}.{k}={v}' for k, v in params.items()], '-o', str(binary), *files]
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if b.returncode:
        raise RuntimeError(name+': compile failure is not a verdict\n'+b.stdout+b.stderr)
    r = subprocess.run(['vvp', '-n', str(binary)], cwd=ROOT, capture_output=True, text=True)
    text = r.stdout+r.stderr
    (out/(name+'.log')).write_text(text)
    return r.returncode, text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tb, tbr = private_tb(out, TB), private_tb(out, TBR)
    checks = {}
    cases = [(f'f{f}_r{r}_c{c}_d{d}', dict(FWD=f, RET=r, CRD=c, CRET=d))
             for (f, r), (c, d) in itertools.product([(0, 0), (7, 7), (1, 64), (64, 1)], [(8, 3), (1, 0), (4, 7), (16, 20)])]
    cases += [('wrap_tag8', dict(FWD=7, RET=64, CRD=8, CRET=3, ROWS=640, TAGW=8))]
    for name, prm in cases:
        rc, text = icarus(out, 'tb_ha2_truecredit_cr', name, prm, LIBS+[tb])
        good = rc == 0 and 'PASS_TRUECREDIT_CR ' in text
        m = re.search(r'elapsed=(\d+)', text)
        checks[name] = dict(passed=good, rc=rc, elapsed=int(m.group(1)) if m else None, tail=text[-600:])
        print(name, 'PASS' if good else 'FAIL', flush=True)
    for m, name, marker in [(1, 'ignore_reservations', 'TRUECREDIT_FAULT'), (2, 'corrupt_retire_id', 'TRUECREDIT_FAULT'),
                            (3, 'corrupt_forward_id', 'TRUECREDIT_FAULT'), (4, 'read_addr_off_by_one', 'TRUECREDIT_FAULT tx=0 rx=1'),
                            (5, 'credit_over_issue', 'TRUECREDIT_CONSUMER_OVF'),
                            (6, 'spurious_credit_overflow', 'TRUECREDIT_FAULT tx=0 rx=1'),
                            (7, 'read_overtakes_wreg_write', 'TRUECREDIT_FAULT tx=0 rx=1'),
                            (8, 'credit_return_dropped', 'TRUECREDIT_TIMEOUT')]:
        rc, text = icarus(out, 'tb_ha2_truecredit_cr', 'mut_'+name, dict(MUTANT=m), LIBS+[tb])
        good = rc != 0 and marker in text
        checks['mut_'+name] = dict(passed=good, rc=rc, mutant=m, tail=text[-600:])
        print('mut_'+name, 'CAUGHT' if good else 'MISSED', flush=True)
    for name, prm, marker, neg in [
            ('reset_flight', dict(FWD=7, RET=7), 'PASS_TRUECREDIT_CR_RESET', False),
            ('reset_long_flight', dict(FWD=64, RET=64, CRET=20), 'PASS_TRUECREDIT_CR_RESET', False),
            ('reset_return_pipe_removed', dict(MUTANT=1), 'RESET_STALE_RETURN_PIPE', True),
            ('reset_stale_sender_credit', dict(MUTANT=2), 'RESET_PROTOCOL_FAULT epoch=1 tx=1', True),
            ('reset_stale_credit_line', dict(MUTANT=3), 'RESET_PROTOCOL_FAULT epoch=1 tx=0 rx=1', True)]:
        rc, text = icarus(out, 'tb_ha2_truecredit_cr_reset', name, prm, LIBS+[tbr])
        good = marker in text and 'RESET_INTERRUPTION ' in text and ((rc != 0) if neg else (rc == 0))
        checks[name] = dict(passed=good, rc=rc, tail=text[-600:])
        print(name, 'PASS' if good else 'FAIL', flush=True)
    pins = {f: sha(ROOT/f) for f in LIBS+[TB, TBR, 'tools/ha2_rxs_gate.py']}
    record = dict(gate='ha2_rxs', dut='ot_ha2_truecredit_receiver_s', passed=all(c['passed'] for c in checks.values()),
                  checks=checks, source_sha256=pins,
                  cycles_added='vs receiver_p CREDIT=1: arrival -> readable +1 edge (WREG), fetch -> send_v/return_v +2 '
                               'edges (macro read + capture flop); credit round trip +2 edges')
    (out/'terminal.json').write_text(json.dumps(record, indent=2)+'\n')
    print('HA2_RXS PASSED' if record['passed'] else 'HA2_RXS FAILED')
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
