#!/usr/bin/env python3
"""LB2-S81/CC-svc: collect the svc attention-job bench (run_svc_bench.sh) into the committed result dir.

  check_svc.py --runs OUT --img IMG --dest results/rtl/s81_layer_tput_1018/compiler/bench_svc

PASS = both base seeds verdict PASS (every check of tb_svc_lower.sv, incl. the compiled P.V / done cycles); each
compiler mutant (slot: wrong OWN_ROW pos field; late: PV frame 40 edges after the compiled p-feed start) must FAIL
with its regex; their logs are the committed fail witnesses.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

MUTANTS = {
    'slot': dict(what='OWN_ROW pos field = position - 1 (the own row lands in slot 126; slot 127 reads stale HBM)',
                 regex=r'SC MISMATCH|verdict=FAIL'),
    'late': dict(what='PV frame driven 40 edges after the cycle the compiled PO / PVO assume (the static p feed takes words that have not landed: P.V wrong)',
                 regex=r'PV MISMATCH|first_fault_code=0*[1-9a-f]'),
}
LINE = re.compile(r'^SVCLOW .*$', re.M)
SCHED = re.compile(r'^SVCLOW_SCHED .*$', re.M)


def kv(line):
    return {k: v for k, v in re.findall(r'(\w+)=(\S+)', line)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', required=True)
    ap.add_argument('--img', required=True)
    ap.add_argument('--dest', required=True)
    a = ap.parse_args()
    runs, dest = Path(a.runs), Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    base = []
    for s in (1, 2):
        log = (runs / f'run_base_s{s}.log').read_text()
        m, sc = LINE.search(log), SCHED.search(log)
        rec = dict(seed=s, line=m.group(0) if m else None, sched=sc.group(0) if sc else None,
                   verdict=kv(m.group(0)).get('verdict') if m else 'NO_RESULT')
        if m:
            rec.update(fields=kv(m.group(0)), sched_fields=kv(sc.group(0)) if sc else {})
        base.append(rec)
        shutil.copy(runs / f'run_base_s{s}.log', dest / f'run_base_s{s}.log')
    muts = []
    for name, spec in MUTANTS.items():
        log = (runs / f'run_{name}_s1.log').read_text()
        w = dest / f'mut_{name}_fail_witness.log'
        w.write_text(log)
        m = LINE.search(log)
        verdict = kv(m.group(0)).get('verdict') if m else 'NO_RESULT'
        failed = verdict != 'PASS' and bool(re.search(spec['regex'], log))
        muts.append(dict(name=name, what=spec['what'], regex=spec['regex'], verdict=verdict, failed=failed,
                         witness=str(dest / w.name), line=m.group(0) if m else None))
    img = {}
    for d in sorted(Path(a.img).iterdir()):
        if (d / 'image.json').exists():
            img[d.name] = json.loads((d / 'image.json').read_text())
    shutil.copy(runs / 'sources.sha256', dest / 'sources.sha256')
    shutil.copy(runs / 'verilator.version', dest / 'verilator.version')
    ok = all(b['verdict'] == 'PASS' for b in base) and all(m['failed'] for m in muts)
    chk = dict(schema='opentallas.s81_dv.compiler_bench.v1', family='svc', layer='L0', **{'pass': ok},
               ops_proven=['attn.own_row_write', 'attn.window_load', 'attn.scores', 'attn.pv (quarter ST 0 words)'],
               vehicle='the 16 real dsdv_svc_rs slices (protect-lib, DIE 0, ST 0 = die.v), entry j / q pins driven '
                       'only by lower_svc.py images at the compiled cycles; HBM = elastic per-PC model (DQ 8, '
                       'latency 40..55 + queue, seeds 1 / 2)',
               checks='all 128 x 16 root scores + 16 x 128 SE rows bit-exact (golden dots of fixture q / rows; '
                      'x attn_scale = fixture attn.scores bitwise), 160 P.V words bit-exact vs fixture attn.pv '
                      '(heads 0..15, dims 0..127) with the first word and both jd done pulses AT the compiled '
                      'cycles, every q word on its cycle, no fault, HBM credits <= 8',
               base=base, mutants=muts, images=img,
               bench='tools/s81_dv/layer_prog/svc/{tb_svc_lower.sv,run_svc_bench.sh,check_svc.py}',
               lowering='tools/s81_dv/layer_prog/lower_svc.py')
    (dest / 'check.json').write_text(json.dumps(chk, indent=1) + '\n')
    print('PASS' if ok else 'FAIL', [b['verdict'] for b in base], [(m['name'], m['failed']) for m in muts])


if __name__ == '__main__':
    main()
