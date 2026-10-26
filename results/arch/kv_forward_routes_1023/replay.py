"""Replay exact KV-v3.2 coverage and causal lane removals. No P&R or source writes.

python3 replay.py --plan-dir PATH --output witness.json
The plan directory supplies its original census map; this script installs the four explicit routes in a temp copy.
"""
import argparse, copy, hashlib, json, shutil, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import schema, census_cov, check

ap = argparse.ArgumentParser()
ap.add_argument('--plan-dir', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
a = ap.parse_args()
raw = json.loads((a.plan_dir / 'die_plan.json').read_text())
meta = {'plan_sha256': hashlib.sha256((a.plan_dir/'die_plan.json').read_bytes()).hexdigest(),
        'scope': 'G0 plan/census route identity only; not RTL bind or physical closure', 'cases': {}}
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    shutil.copytree(a.plan_dir/'census', d/'census')
    mpfile = d/raw['census'][0]['map']
    original = json.loads(mpfile.read_text())
    meta['map_sha256'] = hashlib.sha256(mpfile.read_bytes()).hexdigest()
    routes = json.loads((HERE/'forward_routes.json').read_text())
    mp = dict(original, forward_routes=routes)

    def run(name, plan, mapping, expected):
        mpfile.write_text(json.dumps(mapping))
        R = check.Report()
        s = census_cov.coverage(schema.Plan(plan), d, R)
        result = dict(errors=[r['msg'] for r in R.errors()], dropped_bits=s['dropped_bits'])
        meta['cases'][name] = result
        assert bool(R.errors()) == expected, (name, result)

    run('old_metadata_four_bit_failure', raw, original, True)
    run('explicit_routes_positive', raw, mp, False)
    for lid in ['L745', 'L746', 'L747', 'L2046', 'L2047', 'L2049', 'L2051']:
        p = copy.deepcopy(raw)
        p['lanes'] = [ln for ln in p['lanes'] if ln['id'] != lid]
        run('missing_'+lid, p, mp, True)
    for mode in ['short', 'wrong_source', 'wrong_dst', 'duplicate', 'malformed']:
        m = copy.deepcopy(mp)
        if mode == 'short': m['forward_routes'][0]['lanes'] = ['L745']
        if mode == 'wrong_source': m['forward_routes'][0]['src_bus'] = 'absent'
        if mode == 'wrong_dst': m['forward_routes'][0]['dst'] = 'serdes_E'
        if mode == 'duplicate': m['forward_routes'].append(copy.deepcopy(m['forward_routes'][0]))
        if mode == 'malformed': m['forward_routes'][0] = 'malformed'
        run(mode+'_declaration', raw, m, True)
    p = copy.deepcopy(raw)
    first = next(ln for ln in p['lanes'] if ln['id']=='L745')['ports'][0]
    next(pr for pr in p['ports'] if pr['id']==first)['width'] = 2
    run('wrong_route_width', p, mp, True)
    p = copy.deepcopy(raw)
    first = next(ln for ln in p['lanes'] if ln['id']=='L745')['ports'][0]
    next(pr for pr in p['ports'] if pr['id']==first)['dst']['bus'] = 'ft_missing_i'
    run('broken_internal_slot', p, mp, True)
    m = copy.deepcopy(mp)
    m['forward_via'] = []
    run('undeclared_forwarders', raw, m, True)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(meta, indent=2)+'\n')
print('PASS',len(meta['cases']),'cases',a.output)
