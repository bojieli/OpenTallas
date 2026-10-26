#!/usr/bin/env python3
"""TOK-DS-CMP (10-26): collect the L14 compressed-row svc bench (run_cmp.sh) into the committed result dir.

  check_svc_cmp.py --runs RUN_DIR --img IMG_DIR --dest results/rtl/s81_l14_cmp_1026/bench_cmp

PASS = base seeds 1 and 2 verdict PASS (every tb_svc_lower check: all T x 16 root scores, 16 x T SE rows, on-die P,
640 P.V words at the compiled cycles, SO / gather, no fault).  Selection mutants must FAIL: sel_id (one held id -> its
block neighbour, wrong HBM row gathered), rows_pair (ROWS pair field p ^ 1).  pio_early / base_safe are calibration
information only.  Logs are committed as the witnesses.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

MUTANTS = {
    'sel_id': dict(what='SEL_IDS: the first held id g -> g ^ 1 (the slice fetches the block neighbour row)',
                   regex=r'SC MISMATCH|verdict=FAIL'),
    'rows_pair': dict(what='ROWS: every word pair field p -> p ^ 1 (rows of other dies land in the wrong tiles)',
                      regex=r'SC MISMATCH|verdict=FAIL'),
}
INFO = ('pio_early', 'base_safe')
LINE = re.compile(r'^SVCLOW .*$', re.M)
SCHED = re.compile(r'^SVCLOW_SCHED .*$', re.M)


def last(rx, text):
    m = rx.findall(text)
    return m[-1] if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', required=True)
    ap.add_argument('--img', required=True)
    ap.add_argument('--dest', required=True)
    a = ap.parse_args()
    runs, img, dest = Path(a.runs), Path(a.img), Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    rel = dest.as_posix()
    rec = dict(schema='opentallas.s81_dv.compiler_bench.v1', family='svc', layer='L14',
               ops_proven=['attn.own_row_write', 'attn.window_load', 'attn.gather (held rows by SEL_IDS index fetch; '
                           'other rows ROWS words)', 'attn.scores', 'attn.max', 'attn.exp', 'attn.pv (all 512 dims, ALLQ)'],
               vehicle='the 16 real dsdv_svc_rs slices + 2 entries (closing protect-libs: ALLQ, ATTN_HCORE, CTLA, '
                       'RST_TIMED; DIE 0, ST 0), q / j pins driven only by lower_svc.py images at the compiled cycles; '
                       'HBM = elastic per-PC model',
               scope='T 640 = 128 window FP8 rows + 512 indexer-selected FP4 compressed rows of the L14 fixture '
                     '(attn.idx.topk_final ids; their on-die producer bk_sel -> svc_selq and the ROWS cross-die '
                     'producer attn.rows_allgather are NOT lowered: driven at the compiled q cycles)',
               base=[], mutants=[], info=[])
    ok = True
    for s in (1, 2):
        f = runs / f'run_base_s{s}.log'
        t = f.read_text() if f.exists() else ''
        line = last(LINE, t)
        v = 'PASS' if line and 'verdict=PASS' in line else 'FAIL'
        ok &= v == 'PASS'
        shutil.copy(f, dest / f.name) if f.exists() else None
        rec['base'].append(dict(seed=s, verdict=v, line=line, sched=last(SCHED, t)))
    for m, d in MUTANTS.items():
        f = runs / f'run_{m}_s1.log'
        t = f.read_text() if f.exists() else ''
        failed = bool(t) and bool(re.search(d['regex'], t)) and 'verdict=PASS' not in (last(LINE, t) or '')
        w = dest / f'mut_{m}_fail_witness.log'
        if failed:
            shutil.copy(f, w)
        ok &= failed
        rec['mutants'].append(dict(name=m, what=d['what'], failed=failed, line=last(LINE, t),
                                   witness=w.as_posix() if failed else None))
    for m in INFO:
        f = runs / f'run_{m}_s1.log'
        t = f.read_text() if f.exists() else ''
        rec['info'].append(dict(name=m, line=last(LINE, t), sched=last(SCHED, t)))
    im = json.loads((img / 'base' / 'image.json').read_text())
    rec['image'] = {k: im[k] for k in ('frames', 'go', 'pio', 'po', 'pvo', 'pv_first', 'pv_last', 'done_w', 'done_e', 'T',
                                       'timing_profile', 'engine_profile', 'sha256')}
    rec['pass'] = bool(ok)
    (dest / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(pass_=rec['pass'], base=[b['verdict'] for b in rec['base']],
                          mutants={m['name']: m['failed'] for m in rec['mutants']})))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
