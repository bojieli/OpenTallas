#!/usr/bin/env python3
"""TOK-FUNC-QW stage xt1 collector: RUNROOT/xt1/<variant>/log_<run>.txt.xt1n.json (xt1n_bench.py check) -> result.json.

    stage_xt1.collect.py RUNROOT --variants "landed nobind nl oldtags" --grade GRADE
"""
import argparse, json
from pathlib import Path

NOMINAL = {'landed': ('nominal_l8_g4', 'nominal_l4_g2'), 'nl': ('nominal_l8_g4', 'nominal_l4_g2')}
MUTANT = {'landed': ('romswap_l8_g4',), 'nobind': ('nominal_l8_g4',), 'oldtags': ('nominal_l8_g4',)}
OPS = ('qkv', 'o', 'gu', 'down')


def load(o, v, tag):
    p = o / v / f'log_{tag}.txt.xt1n.json'
    return json.loads(p.read_text()) if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runroot', type=Path)
    ap.add_argument('--variants', default='landed nobind nl oldtags')
    ap.add_argument('--grade', default='RTL-functional (source assembly)')
    a = ap.parse_args()
    o = a.runroot / 'xt1'
    vs = a.variants.split()
    src = (a.runroot / 'src' / 'ASM_COMMIT').read_text().strip() if (a.runroot / 'src' / 'ASM_COMMIT').exists() else None
    runs, cycles, mutants, bad, logs = {}, {}, {}, [], []
    for v in vs:
        for tag in NOMINAL.get(v, ()) + MUTANT.get(v, ()):
            r = load(o, v, tag)
            key = f'{v}_{tag}'
            logs += [f'{v}/log_{tag}.txt', f'{v}/result_{tag}.txt', f'{v}/sim_{tag}.out']
            if r is None:
                vo = o / v / 'variant.out'
                runs[key] = dict(verdict='MISSING', note=vo.read_text().strip()[-400:] if vo.exists() else 'no output')
            else:
                runs[key] = dict(verdict=r['verdict'], near=r['near']['exact'], far=r['far']['exact'],
                                 errors=(r['near']['errors'] + r['far']['errors'])[:6])
            if tag in NOMINAL.get(v, ()):
                if runs[key]['verdict'] != 'PASS':
                    bad.append(f'{key} {runs[key]["verdict"]}')
                if r:
                    cycles[key] = {side: {op: {k: r[side]['per_op'].get(op, {}).get(k)
                                               for k in ('d_head', 'first_rs', 'first_final', 'last_final', 'round_period')}
                                          for op in OPS} for side in ('near', 'far')}
            else:
                ok = runs[key]['verdict'] == 'FAIL' and (r is None or 'romswap' not in tag or r['far']['verdict'] == 'FAIL')
                # a MISSING run (build / gen failure) is no fail witness
                mutants[key] = 'FAIL as required' if ok else f'NOT FAILED ({runs[key]["verdict"]})'
                if not ok:
                    bad.append(f'mutant {key} {mutants[key]}')
    for side in ('near', 'far'):
        a_, b_ = cycles.get('landed_nominal_l8_g4'), cycles.get('nl_nominal_l8_g4')
        if a_ and b_:
            cycles[f'landing_delta_{side}_l8_g4'] = {
                op: {k: (a_[side][op][k] - b_[side][op][k]) if a_[side][op][k] is not None and b_[side][op][k] is not None
                     else None for k in ('first_rs', 'first_final', 'last_final')} for op in OPS}
    expected = sum(len(NOMINAL.get(v, ())) + len(MUTANT.get(v, ())) for v in vs)
    verdict = 'PASS' if not bad and len(runs) == expected else 'FAIL'
    res = dict(stage='xt1', grade=a.grade, src_commit=src, verdict=verdict,
               golden='every rs word of the near (c16_W5_2, cid 2) and far (c16_W5_3, cid 3) cluster for the L0 stage-1 '
                      'qkv/o/gu/down matvecs vs the level-6 golden parts (xt1_prep.py: hdc_golden chunk sums on the '
                      'QW-REALSTG fixture int8 rows x BF16 x), 64 final words per side (qkv 8, o 24, gu 8, down 24), plus the '
                      'word count rounds x k x 8 and zero faults; ROM layout precheck 0 mismatched bytes vs the fixtures',
               cycles=cycles, cycles_note='edges from the hr go at the slice W pin; near = RS at slice rs_n0, far = RSO at '
                      'rs_n1 (after the die landings in landed); landed = with the 11 qfd_landh0 landings, nl = without',
               runs=runs, mutants=mutants, failures=bad,
               stand_ins=['hr / cmd / x-stream driven at the slice W pins (tt_ctlm + its relay lane = bench events, the '
                          'unit_c4 stage-1 ROM commands); one column piece (N side of dvs_W5: near + far cluster of 48)',
                          'other slice inputs idle (S band-1 clusters, W4 neighbour, ring return), as the XT1g die carve',
                          'one bench clock + one bench reset for every region (functional cycles; landing K 3 = plan E 2)'],
               logs=sorted(set(logs)))
    (o / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
    print(f'XT1 {verdict}: ' + json.dumps({k: (r['verdict'], r.get('near'), r.get('far')) for k, r in runs.items()}))
    for b in bad:
        print('  BAD', b)


if __name__ == '__main__':
    main()
