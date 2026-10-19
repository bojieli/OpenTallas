"""Read an immutable pickup; enumerate the exact admitted sweep obligations."""
import hashlib
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[2]
pickup = pathlib.Path(sys.argv[1]).resolve()
out = pickup / 'coverage_audit.json'
if out.exists():
    raise SystemExit('REFUSE existing audit')
summary = json.loads((pickup / 'summary.json').read_text())
source_manifest = json.loads((pickup.parent / 'source_manifest.json').read_text())
source_checks = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() == h
                 for p, h in source_manifest.items()}
assert all(source_checks.values()), 'frozen source manifest mismatch'
rows = []
for ns in range(2, 48):
    campaign = next((pickup / pathlib.Path(r['log']).stem.removeprefix('s81-hwin-private-')
                     for r in summary['runs'] if 'sweep_' in r['log'] and
                     (pickup / pathlib.Path(r['log']).stem.removeprefix('s81-hwin-private-') /
                      f'uniform_ns{ns}').exists()), None)
    for program in ('uniform', 'nonuniform_short'):
        for seed in (1, 19, 313):
            for shift in ((-1,) if program == 'uniform' else (-1, 0, 1)):
                name = f'run_seed{seed}' + ('' if shift == -1 else f'_rxshift{shift}') + '.log'
                f = campaign / f'{program}_ns{ns}' / name if campaign else None
                text = f.read_text(errors='replace') if f and f.exists() else ''
                expected = '^MUWIN PASS$' if shift == -1 else '^MUWIN RX_EXPIRED PASS$'
                passed = bool(re.search(expected, text, re.M))
                windows = re.findall(r'^RX_MODEL input(\d+) born(\d+) boundary(\d+) shift(-?\d+) user(\d+) pos(\d+)$', text, re.M)
                fault = re.findall(r'^RX_MODEL first_fault(\d+) expected(\d+)$', text, re.M)
                if passed and program == 'nonuniform_short':
                    assert windows and all(int(a) == int(c) + shift and int(s) == shift for a,b,c,s,u,p in windows)
                    if shift >= 0:
                        assert fault and all(a == b for a,b in fault)
                rows.append({'ns': ns, 'program': program, 'seed': seed, 'rx_shift': shift,
                             'status': 'PASS_RECEIPT' if passed else 'MISSING_OR_LIVE',
                             'path': str(f.relative_to(pickup)) if f and f.exists() else None,
                             'return_tag_count': len(windows), 'first_fault': fault})
four_state = {}
for ns in (2, 47):
    d = pickup / f'four_state_ns{ns}_01' / 'four_state'
    phases = {str(n): bool(re.search(r'^MUWIN PASS$', (d/f'run_phase{n}.log').read_text(errors='replace'),re.M))
              if (d/f'run_phase{n}.log').exists() else False for n in (0,1,2,3,4,5,6,7,8,90,93)}
    trace_pairs = {str(seed): (d/f'equiv_original_seed{seed}.trace').exists() and
                   (d/f'equiv_projected_seed{seed}.trace').exists() and
                   (d/f'equiv_original_seed{seed}.trace').read_bytes() ==
                   (d/f'equiv_projected_seed{seed}.trace').read_bytes() for seed in (1,19,313)}
    causal = {m: (d/f'run_mutant_{m}.log').exists() and 'EARLY_X_CAUSAL' in
              (d/f'run_mutant_{m}.log').read_text() and 'FATAL:' in
              (d/f'run_mutant_{m}.log').read_text() for m in ('PAYLOAD','CONTROL')}
    four_state[str(ns)] = {'phase_pass': phases, 'original_projected_trace_equal': trace_pairs,
                           'qualified_x_causal': causal,
                           'primitive13': (d/'primitive_probe.log').exists() and
                           'PRIMITIVE_PROBE PASS cases13' in (d/'primitive_probe.log').read_text()}
result = {'scope': 'Receipt census only. Live campaign is not terminal qualification; original fullshape06 excluded.',
          'source_manifest_all_match': source_checks, 'sweep': rows,
          'legal_pass': sum(r['status']=='PASS_RECEIPT' and r['rx_shift']==-1 for r in rows),
          'legal_expected': 276,
          'expiry_pass': sum(r['status']=='PASS_RECEIPT' and r['rx_shift']>=0 for r in rows),
          'expiry_expected': 276, 'four_state': four_state,
          'gold': 'Frozen bench D+2 event and D+3 collision equations unchanged; source manifest verified. Nonuniform RX uses B-1 legal/B,B+1 causal expiry; assertions check actual times above.'}
out.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: result[k] for k in ('legal_pass','legal_expected','expiry_pass','expiry_expected')}))
