#!/usr/bin/env python3
"""Exercise a pinned HCP partition binary against real full43 resident ROM data.

Equal-phase clocks prove arithmetic and calendar only. This is not CTS, pin
reach, physical closure, native VM integration or whole-token qualification.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--vectors', type=Path, required=True)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--cycles', type=int, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for tag, layer in [('L00', 0), ('L24', 24), ('L25', 25), ('L39', 39), ('M0R0', 40), ('M1R0', 41), ('M2R4', 42)]:
        cmd = [str(a.binary), '+DIR=' + str(a.vectors / tag), '+OT_ROM_DIR=' + str(a.rom), f'+LAYER={layer}']
        run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (a.out / (tag + '.log')).write_text(run.stdout)
        ok = run.returncode == 0 and 'HCX_PROJECTION PASS' in run.stdout and run.stdout.count(f'native_cycles{a.cycles}') == 2
        rows.append({'tag': tag, 'layer': layer, 'returncode': run.returncode,
                     'exact_outputs': 2 if ok else 0, 'cycles': a.cycles if ok else None, 'pass': ok})
        print(tag, ok, flush=True)
    cmd = [str(a.binary), '+DIR=' + str(a.vectors / 'L25'), '+OT_ROM_DIR=' + str(a.rom), '+LAYER=25', '+MUT_STAGE']
    run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (a.out / 'stage_mutant.log').write_text(run.stdout)
    mutant = run.returncode != 0 and 'HCX_PROJECTION FAIL errors2' in run.stdout and run.stdout.count(f'native_cycles{a.cycles}') == 2
    summary = {'scope': __doc__, 'rows': rows, 'mutant_rejected': mutant,
               'mutant_returncode': run.returncode, 'all_pass': all(r['pass'] for r in rows) and mutant,
               'binary_sha256': hashlib.sha256(a.binary.read_bytes()).hexdigest(),
               'mutant': 'Same binary replaces first staged4096bit beat by256BF16 1.0words for both sublayers; golden targets unchanged'}
    (a.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0 if summary['all_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
