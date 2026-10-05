#!/usr/bin/env python3
"""Repack W19 operands with another LC importer; replay retained RTL outputs, no RTL rerun."""
import argparse, ast, hashlib, importlib.util, json, pickle, sys
from pathlib import Path
import w19_sm_real_ops as W


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--lc', type=Path, required=True)
    a.add_argument('--fixtures', type=Path, required=True)
    a.add_argument('--work', type=Path, required=True)
    a.add_argument('--record', type=Path, required=True)
    v = a.parse_args()
    if v.record.exists():
        raise SystemExit('Fresh evidence path required')
    pin = sha(v.lc)
    spec = importlib.util.spec_from_file_location('w19_actual_main_lc', v.lc)
    lc = importlib.util.module_from_spec(spec); sys.modules[spec.name] = lc; spec.loader.exec_module(lc)
    root = Path(__file__).resolve().parents[1]
    historical = root / 'tools/rtl_v41_fullshape_layer_campaign.py'
    def nodes(path):
        return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    h, c = nodes(historical), nodes(v.lc)
    same = {k: h[k] == c[k] for k in ('Checkpoint', 'LazyWeights', 'build_model')}
    ck = lc.Checkpoint(); m, _ = lc.build_model(ck, engram=False)
    dump = root / 'results/rtl/w19_sm_operands/ar_L0_oreduce.pkl'
    entries = pickle.loads(dump.read_bytes())
    baseline = json.loads((root / 'results/rtl/w19_fetch_sm.json').read_text())
    cases, artifacts = [], {}
    for d in v.fixtures.glob('s_*'):
        cfg = d / 'cfg.hex'
        if cfg.exists() and int(cfg.read_text().splitlines()[7], 16) == 0:
            artifacts[(sha(d/'lines.hex'), sha(d/'x.hex'))] = d
    v.work.mkdir(parents=True, exist_ok=True)
    for b in baseline['cases']:
        if b['stall'] or b['corrupt_exponent']:
            continue
        fixture = b['rtl']['fixture_sha256']
        d = artifacts[(fixture['lines.hex'], fixture['x.hex'])]
        def runner(params, generated):
            for f in ('lines.hex', 'x.hex'):
                assert sha(generated/f) == fixture[f], f
            results, meta = {}, {}
            for line in (d/'out.txt').read_text().splitlines():
                if line.startswith('# '):
                    fields = line[2:].split();meta.update({fields[i]:int(fields[i+1]) for i in range(0,len(fields),2)})
                else:
                    row, data = line.split();results[int(row)] = data
            return results, meta
        r = W.case(m, b['op'], [entries[b['op']]], str(v.work), sim_runner=runner)
        r['retained_rtl_output_sha256'] = sha(d/'out.txt'); cases.append(r)
    assert sha(v.lc) == pin, 'Importer changed during verification'
    record = dict(status='pass' if all(same.values()) and all(c['exact'] for c in cases) else 'fail',
        claim_boundary='Actual alternate LC importer reproduces all 18 historical packed expert weight/x fixtures '
            'and golden accumulator/output checks against retained RTL outputs. This is importer compatibility, not an RTL rerun.',
        actual_lc_sha256=pin, historical_lc_sha256=sha(historical), identical_required_definitions=same,
        dump_sha256=sha(dump), baseline_record_sha256=sha(root/'results/rtl/w19_fetch_sm.json'), cases=cases,
        source_sha256={'tools/w19_lc_compat.py':sha(__file__), 'tools/w19_sm_real_ops.py':sha(root/'tools/w19_sm_real_ops.py')})
    v.record.write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],len(cases),same)
    return record['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
