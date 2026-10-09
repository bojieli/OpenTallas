#!/usr/bin/env python3
"""credit-ready gate (2026-10-08): credit-based ready for the HBM true-credit receiver.

--part rx: ot_ha2_truecredit_receiver_p #(.CREDIT(1)) in tb_ha2_truecredit_cr (mechanism: fwd/ret x credit depth x
  credit-return delay, tag wrap; mutants 1-4 as the ready benches, 5 = one credit too many at reset (consumer buffer
  overflow), 6 = spurious credit (receiver credit-overflow fault)) and tb_ha2_truecredit_cr_reset (2 flights; mutants
  return pipe not reset, stale sender replay, credit line not reset). Icarus.
--part endpoint: the unchanged tb_ha2_truecredit_endpoint (one PF384 endpoint, bit-exact vs the unchanged adapter) on a
  private copy that only adds .OWNER_RX_CREDIT(1) to the DUT; negatives: CORRUPT_GOLDEN, IGNORE_PEER_CREDIT (existing
  plusarg mutation) and RX_CREDIT_DOUBLE (private half-owner copy whose credit pulse lasts two cycles = one spurious
  credit per pop; credit overflow must fault, fail-closed). Verilator.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
D = 'rtl/hbm_accel/ha2_ar/'
LIBS = [D+n+'.sv' for n in ('ot_ha2_prims', 'ot_ha2_parent_quiet_prims', 'ot_ha2_truecredit', 'ot_ha2_truecredit_rxp')]
TB = D+'tb_ha2_truecredit_cr.sv'
TBR = D+'tb_ha2_truecredit_cr_reset.sv'
ENDPOINT = 'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner_truecredit.sv'
EP_TB = D+'tb_ha2_truecredit_endpoint.sv'
EP_TOP = 'tb_ha2_truecredit_endpoint'
PREDICATE = '!invalid_partial_port[p] && owner_p_r[p]) rb_pop[p]'
MUTATION = '!invalid_partial_port[p] && (owner_p_r[p] || $test$plusargs("IGNORE_PEER_CREDIT"))) rb_pop[p]'
HALF = D+'ot_ha2_tu_owner_banked_half.sv'
HR = "h_r[i]<=(H_CREDIT!=0)?(ph&&h_head_v[i]):(h_cnt[i*4+:4]<=3);"
HR_DOUBLE = ("h_r[i]<=(H_CREDIT!=0)?((ph&&h_head_v[i])||(dbl_m&&!ph&&h_r[i])):(h_cnt[i*4+:4]<=3);")
HR_DECL = " // registered ready / credit toward the senders"
HR_DECL_M = " reg dbl_m; initial dbl_m=$test$plusargs(\"RX_CREDIT_DOUBLE\");\n"+HR_DECL


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def icarus(out, top, name, params, files):
    binary = out/(name+'.vvp')
    cmd = ['iverilog', '-g2012', '-s', top, *[f'-P{top}.{k}={v}' for k, v in params.items()], '-o', str(binary), *files]
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if b.returncode:
        raise RuntimeError(name+': compile failure is not a verdict\n'+b.stdout+b.stderr)
    r = subprocess.run(['vvp', str(binary)], cwd=ROOT, capture_output=True, text=True)
    text = r.stdout+r.stderr
    (out/(name+'.log')).write_text(text)
    return r.returncode, text


def part_rx(out):
    checks = {}
    cases = [(f'f{f}_r{r}_c{c}_d{d}', dict(FWD=f, RET=r, CRD=c, CRET=d))
             for (f, r), (c, d) in itertools.product([(0, 0), (7, 7), (1, 64), (64, 1)], [(8, 3), (1, 0), (4, 7), (16, 20)])]
    cases += [('wrap_tag8', dict(FWD=7, RET=64, CRD=8, CRET=3, ROWS=640, TAGW=8))]
    for name, prm in cases:
        rc, text = icarus(out, 'tb_ha2_truecredit_cr', name, prm, LIBS+[TB])
        good = rc == 0 and 'PASS_TRUECREDIT_CR ' in text
        checks[name] = dict(passed=good, rc=rc, tail=text[-600:])
        print(name, 'PASS' if good else 'FAIL', flush=True)
    for m, name, marker in [(1, 'ignore_reservations', 'TRUECREDIT_FAULT'), (2, 'corrupt_retire_id', 'TRUECREDIT_FAULT'),
                            (3, 'corrupt_forward_id', 'TRUECREDIT_FAULT'), (4, 'misaligned_read_ring', 'TRUECREDIT_DATA'),
                            (5, 'credit_over_issue', 'TRUECREDIT_CONSUMER_OVF'),
                            (6, 'spurious_credit_overflow', 'TRUECREDIT_FAULT tx=0 rx=1')]:
        rc, text = icarus(out, 'tb_ha2_truecredit_cr', 'mut_'+name, dict(MUTANT=m), LIBS+[TB])
        good = rc != 0 and marker in text
        checks['mut_'+name] = dict(passed=good, rc=rc, mutant=m, tail=text[-600:])
        print('mut_'+name, 'CAUGHT' if good else 'MISSED', flush=True)
    for name, prm, marker, neg in [
            ('reset_flight', dict(FWD=7, RET=7), 'PASS_TRUECREDIT_CR_RESET', False),
            ('reset_long_flight', dict(FWD=64, RET=64, CRET=20), 'PASS_TRUECREDIT_CR_RESET', False),
            ('reset_return_pipe_removed', dict(MUTANT=1), 'RESET_STALE_RETURN_PIPE', True),
            ('reset_stale_sender_credit', dict(MUTANT=2), 'RESET_PROTOCOL_FAULT epoch=1 tx=1', True),
            ('reset_stale_credit_line', dict(MUTANT=3), 'RESET_PROTOCOL_FAULT epoch=1 tx=0 rx=1', True)]:
        rc, text = icarus(out, 'tb_ha2_truecredit_cr_reset', name, prm, LIBS+[TBR])
        good = marker in text and 'RESET_INTERRUPTION ' in text and ((rc != 0) if neg else (rc == 0))
        checks[name] = dict(passed=good, rc=rc, tail=text[-600:])
        print(name, 'PASS' if good else 'FAIL', flush=True)
    return checks, LIBS+[TB, TBR]


def part_endpoint(out, threads):
    import ha2_hub_credit_gate as source
    files = list(dict.fromkeys([ENDPOINT if s == 'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner.sv' else s
                                for s in source.PARENT] + source.HALF + LIBS[2:] + [EP_TB]))
    ep = (ROOT/ENDPOINT).read_text()
    assert ep.count(PREDICATE) == 1
    (out/'endpoint.sv').write_text(ep.replace(PREDICATE, MUTATION))
    half = (ROOT/HALF).read_text()
    assert half.count(HR) == 1 and half.count(HR_DECL) == 1
    (out/'half.sv').write_text(half.replace(HR, HR_DOUBLE).replace(HR_DECL, HR_DECL_M))
    tb = (ROOT/EP_TB).read_text()
    assert tb.count('.OWNER_TRUE_CREDIT(1),') == 1
    (out/'tb.sv').write_text(tb.replace('.OWNER_TRUE_CREDIT(1),', '.OWNER_TRUE_CREDIT(1),.OWNER_RX_CREDIT(1),'))
    private = {ENDPOINT: out/'endpoint.sv', HALF: out/'half.sv', EP_TB: out/'tb.sv'}
    cmd = ['verilator', '--binary', '--timing', '-O0', '-Wno-fatal', '-Wno-WIDTH', '--top-module', EP_TOP,
           '--Mdir', str(out/'obj'), '--build-jobs', str(threads)]
    cmd += [str(private.get(s, ROOT/s)) for s in files]
    with (out/'build.log').open('w') as log:
        b = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if b.returncode:
        raise RuntimeError('endpoint build failed: not a verdict (see build.log)')
    checks = {}
    for mode, marker in [('baseline', 'PASS_HA2_TRUECREDIT_ENDPOINT '),
                         ('CORRUPT_GOLDEN', 'ENDPOINT_FAIL numerical or identity mismatch'),
                         ('IGNORE_PEER_CREDIT', 'ENDPOINT_CREDIT_VIOLATION '),
                         ('RX_CREDIT_DOUBLE', 'ENDPOINT_FAIL unexpected fault')]:
        cmdr = [str(out/'obj'/('V'+EP_TOP))] + ([] if mode == 'baseline' else ['+'+mode])
        r = subprocess.run(cmdr, cwd=out, capture_output=True, text=True)
        text = r.stdout+r.stderr
        (out/(mode+'.log')).write_text(text)
        good = (marker in text) and ((r.returncode == 0) if mode == 'baseline' else (r.returncode != 0))
        checks[mode] = dict(passed=good, rc=r.returncode, tail=text[-800:])
        print(mode, 'PASS' if good else 'FAIL', flush=True)
    return checks, files+['tools/ha2_hub_credit_gate.py']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--part', choices=['rx', 'endpoint'], default='rx')
    p.add_argument('--threads', type=int, default=4)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, files = part_rx(out) if a.part == 'rx' else part_endpoint(out, a.threads)
    pins = {f: sha(ROOT/f) for f in files+['tools/ha2_credit_ready_gate.py']}
    record = dict(part=a.part, passed=all(c['passed'] for c in checks.values()), checks=checks, source_sha256=pins)
    (out/'terminal.json').write_text(json.dumps(record, indent=2)+'\n')
    print('PASSED' if record['passed'] else 'FAILED')
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
