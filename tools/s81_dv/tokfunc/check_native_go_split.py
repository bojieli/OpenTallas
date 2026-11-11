#!/usr/bin/env python3
"""S81-PLAN-1 D (11-10): check the gb_split GO/TAG provider bench (tb_native_go_split.sv) per station contract and write the
sha-bound qualification record lower_xs reads (COORD ruling 11-10: regenerated L0 field, gb_split leg on the candidate's
exact bytes, all six X ages + a second-macro row, must-fail mutants per contract, record read per station).

Per contract dd (= station X age - 2), PASS iff
  * original direct GB0 (_gb, old calendar) and the candidate gb_split GB1 (advance-1 calendar) both PASS the independent
    checkpoint gold (values, OPTAG1 tag sequence, row identities incl. the second-macro row, terminal idle, no fault);
  * candidate == original exactly on GO capture dates/tags, partial words with dates, EF feedback, CFG words and X stream;
  * dates = the dd 0 reference + dd (partials and GO capture; the contract is a pure delay of the station);
  * every mutant is caught: wrong_date (old calendar on GB1), wrong_tag, counterfactual 4-FF tag retime, skew (x one
    stage late against cfg/go).
"""
from pathlib import Path
import argparse, hashlib, json, re, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_native_go_pair import inspect  # noqa: E402

KEYS = ['core', 'partial_words', 'feedback', 'cfg', 'stream']
MUTANTS = ['wrong_date', 'wrong_tag', 'counterfactual_retime', 'skew']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def shift(case, d):
    return dict(core=[(t + d, g) for t, g in case['core']], partial_words=[[r[0] + d] + r[1:] for r in case['partial_words']])


def contract(root, dd, gold, ops, ref0):
    d = root / 'runs' / f'dd{dd}'
    names = ['original_direct', 'current_direct', 'candidate'] + MUTANTS
    cases = {n: inspect(d, n, gold, ops) for n in names}
    orig, cand = cases['original_direct'], cases['candidate']
    exact = {k: orig[k] == cand[k] for k in KEYS}
    s0 = shift(ref0, dd) if ref0 is not None else None
    delay = None if s0 is None else dict(core=cand['core'] == s0['core'], partial_words=cand['partial_words'] == s0['partial_words'])
    caught = {m: cases[m]['status'] == 'FAIL' or any(cases[m][k] != orig[k] for k in KEYS) for m in MUTANTS}
    diffs = {m: [k for k in KEYS if cases[m][k] != orig[k]] for m in MUTANTS}
    ok = (orig['status'] == cand['status'] == 'PASS' and all(exact.values()) and (delay is None or all(delay.values()))
          and all(caught.values()))
    return dict(dd=dd, x_age=dd + 2, verdict='PASS' if ok else 'FAIL', original=orig['status'], candidate=cand['status'],
                candidate_errors=cand['errors'], current_gb1=cases['current_direct']['status'], exact_vs_original=exact,
                pure_delay_vs_dd0=delay, mutants_caught=caught, mutant_differences=diffs,
                second_macro_rows=sorted({r[2] & 16383 for r in cand['partial_words'] if r[1] == 1}),
                partials=len(cand['partial_words'])), cases


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--cand', type=Path, required=True, help='candidate source root (frame root copy) of sources.f')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--dd', type=int, nargs='+', default=[0, 2, 16, 17, 26, 27])
    a = p.parse_args()
    assert not a.out.exists(); a.out.mkdir(parents=True)
    gold = json.loads((a.root / 'independent_gold.json').read_text())
    ops = len(json.loads((a.root / 'programme/programme.json').read_text())['programmes']['old']['phases'])
    ref0 = None
    res, allcases = [], {}
    for dd in sorted(a.dd):
        r, c = contract(a.root, dd, gold, ops, ref0)
        if dd == 0:
            ref0 = c['original_direct']
        res.append(r); allcases[dd] = {n: {k: v[k] for k in ('status', 'errors')} for n, v in c.items()}
    assert sorted(a.dd)[0] == 0, 'dd 0 is the date reference'
    cand = a.cand.resolve()
    srcs = [Path(l.strip()) for l in (a.root / 'sources.f').read_text().split() if l.strip()]
    provider = {str(f.resolve().relative_to(cand)): sha(f) for f in srcs if f.resolve().is_relative_to(cand)}
    bench = {str(f): sha(f) for f in srcs if not f.resolve().is_relative_to(cand)}
    split = 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv'
    assert split in provider, 'the bench did not elaborate the candidate gb_split'
    passed = sorted(r['x_age'] for r in res if r['verdict'] == 'PASS')
    rec = dict(schema='opentallas.s81.gb_provider_qualification.v1',
               verdict='PASS' if len(passed) == len(res) else 'FAIL',
               ruling='COORD 11-10: regenerated L0 field + gb_split leg on the candidate exact bytes + six X ages + '
                      'second-macro row + must-fail mutants per contract; sha-bound record read by lower_xs per station',
               element=dict(module='ot_v41_rom_elem_q_qxpq_w10_gb_split', call='#(.OLAT(1)) (plan-kit call; IFN 1 default)',
                            source=split, sha256=provider[split]),
               required_go_issue_advance_edges=1, go_boundary_edges=1, qualified_x_ages=passed,
               contracts=res, first_tag_authority=dict(OPTAG=gold['first_operation_tag'],
                                                       frame_model_sha256=gold.get('frame_model_sha256')),
               provider_source_sha256=provider, bench_source_sha256=bench,
               binary_sha256=(a.root / 'binary.sha256').read_text().split()[0],
               gold_sha256=sha(a.root / 'independent_gold.json'), programme_sha256=sha(a.root / 'programme/programme.json'),
               field_frame_sha256=sha(a.root / 'field/frame.json'), fixture_sha256=gold.get('source_sha256'),
               scope='one L0 u_f_0L01/e0 NB2 pair (phase 0 a_proj wq_a, rows %s), 5 operations at 512 spacing, controlled '
                     'common-phase/L3 startup; contract = uniform station input delay + equal feedback delay; '
                     'fresh producer versions / minimum cadence NOT covered' % gold.get('rows'),
               production_enabled=False)
    (a.out / 'gb_provider_qualification.json').write_text(json.dumps(rec, indent=1) + '\n')
    (a.out / 'cases.json').write_text(json.dumps(allcases, indent=1) + '\n')
    for r in res:
        print(f"CONTRACT x_age {r['x_age']:2d} {r['verdict']} exact={all(r['exact_vs_original'].values())} "
              f"delay={r['pure_delay_vs_dd0']} caught={r['mutants_caught']} mb1_rows={r['second_macro_rows']}")
    print('GB_PROVIDER_QUAL', rec['verdict'], passed)
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
