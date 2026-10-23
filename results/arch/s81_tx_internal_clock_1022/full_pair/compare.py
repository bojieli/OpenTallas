from collections import Counter
from pathlib import Path
import hashlib, json, re

root = Path(__file__).resolve().parent
result = {'frozen_main': '47962969f5104ac62d0c9868caff013319cfda5f',
          'candidate_clock_spine_sha256': '445df4540e22d4deb27c5b31c44d912dd2361892b1d6440ed612f7d24cec5bff',
          'suites': {}, 'new_problems': [], 'count_changes': []}
for suite in ('closure_loop', 'ref_tile', 'hier_contract', 'tt_views'):
    sides = {}
    for side in ('baseline', 'candidate'):
        path = root / (side + '.' + suite + '.log')
        data = path.read_bytes(); text = data.decode(errors='replace')
        runs = re.findall(r'^Ran (\d+) tests? in ', text, re.M)
        if len(runs) != 1:
            raise SystemExit(f'Incomplete or ambiguous test result: {path}')
        problems = Counter((kind, label) for kind, label in
                           re.findall(r'^(FAIL|ERROR): (.+)$', text, re.M))
        summary = re.findall(r'^(?:FAILED \(.*\)|OK(?: \(.*\))?)$', text, re.M)
        if len(summary) != 1:
            raise SystemExit(f'Incomplete final status: {path}')
        skipped = re.search(r'\bskipped=(\d+)', summary[0])
        sides[side] = {'tests': int(runs[0]), 'skipped': int(skipped[1]) if skipped else 0,
                       'summary': summary[0], 'problems': sorted([{'kind': k, 'id': i, 'count': n}
                       for (k, i), n in problems.items()], key=lambda x: (x['kind'], x['id'])),
                       'sha256': hashlib.sha256(data).hexdigest()}
    base, cand = sides['baseline'], sides['candidate']
    bp = Counter({(p['kind'], p['id']): p['count'] for p in base['problems']})
    cp = Counter({(p['kind'], p['id']): p['count'] for p in cand['problems']})
    delta = cp - bp
    result['new_problems'] += [{'suite': suite, 'kind': k, 'id': i, 'count': n}
                               for (k, i), n in sorted(delta.items())]
    for field in ('tests', 'skipped'):
        if base[field] != cand[field]:
            result['count_changes'].append({'suite': suite, 'field': field,
                                           'baseline': base[field], 'candidate': cand[field]})
    sides['same_problem_ids_and_multiplicities'] = bp == cp
    result['suites'][suite] = sides
result['same_baseline_failures'] = all(s['same_problem_ids_and_multiplicities'] for s in result['suites'].values())
result['no_new_regressions'] = not result['new_problems'] and not result['count_changes'] and result['same_baseline_failures']
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['no_new_regressions'] else 1)
