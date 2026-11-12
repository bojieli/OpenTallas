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

X-age basis (DIE-S81-88 11-12).  A frame schedule's station X age is its added_edges = the as-built path minus the LP
frame calendar's flat link (frame_schedule_asb.py), so the age of one physical station depends on the LP calendar it is
measured against.  The bench's dd 0 is its own station path: cf -> ot_s81_sstn_base566 -> ot_s81_rly -> dsfd_qbank_S ->
element for x (go: the same lc chain into ot_s81_cfg7_seq, then qbank_S; go_tag: cfg7_seq -> element direct), no added
stage, no feedback delay.
  * default (no --lp-schedule): the pre-FIX-1 LP calendar (1-flop stations, no station_depth), on which that bench path
    is X age 2: x_age = dd + 2, record byte-identical to the 11-10 form.
  * --lp-schedule REL (the LP calendar of the field's master, under --cand): x_age = dd + offset, offset = bench base
    path - that calendar's flat at the bench station, computed from the candidate RTL's station register depths
    (station_depth.py) for x, go (seq leg and whole path) and go_tag, refused unless all four agree (one uniform shift)
    and unless the calendar was extracted at the candidate's station depths.  On the S81-FRAME-FIX-1 calendar
    (2-flop stations, 11-11) the offset is 0: X age 0 is the bench's dd 0 station itself.  The record carries the basis
    (age_basis.station_depth) and lower_xs admits it only for schedules whose LP calendar has those depths.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_native_go_pair import inspect  # noqa: E402

KEYS = ['core', 'partial_words', 'feedback', 'cfg', 'stream']
MUTANTS = ['wrong_date', 'wrong_tag', 'counterfactual_retime', 'skew']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def shift(case, d):
    return dict(core=[(t + d, g) for t, g in case['core']], partial_words=[[r[0] + d] + r[1:] for r in case['partial_words']])


LEGACY_X_AGE_MINUS_DD = 2   # the bench path on the pre-FIX-1 (1-flop station) LP calendar
BENCH_STATION = 'e0'        # u_f_0L01.u_r0.u_e0 (prepare_native_go_split_gold.selected_native_leaf)
LP_SCHED = 'results/arch/s81_dv_1016/frame_l4_cluster/compiler/{m}_schedule.json'


def age_basis(cand, lp_rel, master):
    """(x_age - dd, basis record) of the bench station on the LP calendar lp_rel under the candidate root cand."""
    assert lp_rel == LP_SCHED.format(m=master), ('not the LP calendar of the field master', lp_rel, master)
    os.environ['OT_S81_FRAME_SOURCE_ROOT'] = str(cand)   # station depths of the candidate's own RTL bytes
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import station_depth as SD  # noqa: E402
    assert SD.rtl_root() == cand
    fp = SD.fingerprint()
    raw = (cand / lp_rel).read_bytes(); lp = json.loads(raw)
    assert lp.get('station_depth') == fp, ('LP calendar extracted at other station depths than the candidate RTL',
                                           lp.get('station_depth'), fp)
    d = lambda m, p: SD.step(m, p)[1]  # noqa: E731
    lc = d('ot_s81_sstn_base566', 'cc') + d('ot_s81_rly', 'o')            # cf.cc -> station -> relay_cc -> cfg7_seq.lc
    bench = dict(x=d('ot_s81_sstn_base566', 'xa') + d('ot_s81_rly', 'o') + d('dsfd_qbank_S', 'o_x0'),
                 go=d('dsfd_qbank_S', 'o_go'), go_path=lc + d('dsfd_qbank_S', 'o_go'), go_tag=0)
    st = lp['station_inputs'][BENCH_STATION]
    xf = {p['flat_link_edges'] for v in st['inputs'].values() for p in v['paths']}
    assert len(xf) == 1, ('LP x inputs of the bench station differ', xf)
    c = st['control']
    flat = dict(x=xf.pop(), go=c['go']['flat_link_edges'], go_path=c['go']['path_edges'],
                go_tag=c['go_tag']['flat_link_edges'])
    assert c['cfg_v']['flat_link_edges'] == flat['go'] and c['cfg_v']['path_edges'] == flat['go_path'], c
    off = {k: bench[k] - flat[k] for k in bench}
    assert len(set(off.values())) == 1, ('bench base is not one uniform shift of the LP calendar', off)
    return off['x'], dict(lp_schedule=lp_rel, lp_schedule_sha256=hashlib.sha256(raw).hexdigest(), station_depth=fp,
                          bench_station=BENCH_STATION, bench_base_edges=bench, lp_flat_edges=flat,
                          x_age_minus_dd=off['x'],
                          rule='x_age = dd + bench base path - LP flat at the bench station (x, go seq leg, go path, '
                               'go_tag agree); lower_xs admits the record only for schedules whose LP calendar has '
                               'station_depth equal to this basis')


def contract(root, dd, gold, ops, ref0, age_off=LEGACY_X_AGE_MINUS_DD):
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
    return dict(dd=dd, x_age=dd + age_off, verdict='PASS' if ok else 'FAIL', original=orig['status'], candidate=cand['status'],
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
    p.add_argument('--lp-schedule', help='LP frame calendar (relative to --cand) the X ages are measured against; '
                                         'omitted = the pre-FIX-1 calendar, x_age = dd + 2 (see module doc)')
    a = p.parse_args()
    assert not a.out.exists()
    basis = None
    age_off = LEGACY_X_AGE_MINUS_DD
    if a.lp_schedule is not None:
        master = json.loads((a.root / 'field/frame.json').read_text())['master'].removesuffix('_l4')
        age_off, basis = age_basis(a.cand.resolve(), a.lp_schedule, master)
    a.out.mkdir(parents=True)
    gold = json.loads((a.root / 'independent_gold.json').read_text())
    ops = len(json.loads((a.root / 'programme/programme.json').read_text())['programmes']['old']['phases'])
    ref0 = None
    res, allcases = [], {}
    for dd in sorted(a.dd):
        r, c = contract(a.root, dd, gold, ops, ref0, age_off)
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
    if basis is not None:
        rec['age_basis'] = basis
    (a.out / 'gb_provider_qualification.json').write_text(json.dumps(rec, indent=1) + '\n')
    (a.out / 'cases.json').write_text(json.dumps(allcases, indent=1) + '\n')
    for r in res:
        print(f"CONTRACT x_age {r['x_age']:2d} {r['verdict']} exact={all(r['exact_vs_original'].values())} "
              f"delay={r['pure_delay_vs_dd0']} caught={r['mutants_caught']} mb1_rows={r['second_macro_rows']}")
    print('GB_PROVIDER_QUAL', rec['verdict'], passed)
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
