#!/usr/bin/env python3
"""Reset live reservations, forward frames and return credits, then restart."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tb_ha2_truecredit_reset'
FILES = ['rtl/hbm_accel/ha2_ar/' + name + '.sv' for name in (
    'ot_ha2_prims', 'ot_ha2_parent_quiet_prims', 'ot_ha2_truecredit', TOP)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pin_files = FILES + ['tools/ha2_truecredit_reset_gate.py']
    pins = {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pin_files}
    checks = {}
    for name, fwd, ret, mutant, marker in [
        ('candidate_flight_reset',7,7,0,'PASS_TRUECREDIT_RESET'),
        ('long_flight_reset',64,64,0,'PASS_TRUECREDIT_RESET'),
        ('return_pipe_reset_removed',7,7,1,'RESET_STALE_RETURN_PIPE'),
        ('stale_credit_before_new_send',7,7,2,'RESET_PROTOCOL_FAULT epoch=1 tx=1 rx=0')]:
        binary = out/(name+'.vvp')
        command = ['iverilog','-g2012','-s',TOP,f'-P{TOP}.FWD={fwd}',
                   f'-P{TOP}.RET={ret}',f'-P{TOP}.MUTANT={mutant}',
                   '-o',str(binary),*FILES]
        build = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        (out/(name+'.compile.log')).write_text(build.stdout+build.stderr)
        if build.returncode:
            raise RuntimeError(name+': compile failure is not a valid negative')
        run = subprocess.run(['vvp',str(binary)],cwd=ROOT,capture_output=True,text=True)
        text = run.stdout+run.stderr
        (out/(name+'.log')).write_text(text)
        good = marker in text and 'RESET_INTERRUPTION ' in text and (
            run.returncode!=0 if mutant else run.returncode==0)
        checks[name] = dict(passed=good,returncode=run.returncode,
                            forward_hops=fwd,return_hops=ret,mutant=mutant,output=text)
        print(name, 'PASS' if good else 'FAIL', flush=True)
    assert pins == {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pin_files}
    record = dict(passed=all(c['passed'] for c in checks.values()),checks=checks,
        source_sha256=pins,
        reset_contract='One common reset asynchronously clears sender/receiver accounting, FIFO validity and EVERY hub/forward/return valid pipeline. Payload arrays need not clear. Release is common before fresh traffic.',
        session_identity='Forward/return sequence IDs reset together. They are ordering IDs, not persistent epochs. A partial reset retaining matching old traffic is outside this contract; the reset-pipeline negative proves flushing is necessary.',
        scope='Minimum full-width 2x544 mechanism. Reset interrupts simultaneous hub, forward and return flights; fresh epoch-coded payloads complete192rows/injector and fully drain64-slot accounting. No production RTL change or new physical claim.')
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
