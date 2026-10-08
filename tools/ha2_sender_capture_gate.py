#!/usr/bin/env python3
"""Smallest full-width registered sender gate; no full endpoint build."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tb_ha2_hub_credit_sender_capture'
FILES = ['rtl/hbm_accel/ha2_ar/' + n + '.sv' for n in (
    'ot_ha2_prims', 'ot_ha2_parent_quiet_prims', 'ot_ha2_hub_credit_sender',
    'ot_ha2_hub_credit_sender_capture', TOP)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pins = {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    checks = {}
    for name, mutant, stall in [('stalls', 0, 1), ('no_stalls', 0, 0),
            ('ignore_reservations', 1, 1), ('ignore_receiver_credit', 2, 1)]:
        binary = out / (name + '.vvp')
        cmd = ['iverilog', '-g2012', '-s', TOP, f'-P{TOP}.MUTANT={mutant}',
               f'-P{TOP}.STALL={stall}', '-o', str(binary), *FILES]
        build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (out/(name+'.compile.log')).write_text(build.stdout+build.stderr)
        if build.returncode:
            raise RuntimeError(name + ': compile failed; not a valid negative')
        run = subprocess.run(['vvp', str(binary)], cwd=ROOT, capture_output=True, text=True)
        text = run.stdout + run.stderr
        (out/(name+'.log')).write_text(text)
        expected = ('CREDIT_FAIL reservation or FIFO fault' if mutant == 1 else
                    'CREDIT_FAIL send without prior-edge receiver credit')
        good = (run.returncode != 0 and expected in text) if mutant else (
            run.returncode == 0 and 'PASS_HA2_HUB_CREDIT_CAPTURE' in text)
        checks[name] = dict(returncode=run.returncode, passed=good, output=text)
    assert pins == {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    record = dict(passed=all(c['passed'] for c in checks.values()), checks=checks,
        source_sha256=pins,
        scope='One 2x192-row full-width sender, 35-cycle hub flight. Endpoint, die relays and physical adoption pending.')
    (out/'terminal.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(dict(passed=record['passed'], checks={k:v['passed'] for k,v in checks.items()})))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
