#!/usr/bin/env python3
"""Register GLOBAL-FP-S candidates in the data-flow explorer (screen only).

For each selected candidate of candidates.json: explorer_export.export() -> record JSON ->
tools/fleet_viz/dataflow_links.py import --candidate-of s81_gen18c (validated, re-measured with the explorer's own
metric code, indexed in data/index.json).  Writes explorer_metrics.json {candidate: coverage.metrics} next to
candidates.json for the comparison page.
"""
import argparse, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import explorer_export as X

REPO = Path(__file__).resolve().parents[3]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cands', required=True)
    ap.add_argument('--graph', required=True)
    ap.add_argument('--canon', required=True, help='s81_gen18c.links.json.gz')
    ap.add_argument('--plan', required=True, help='GEN18c construction_pass0_plan.json.gz')
    ap.add_argument('--out', required=True, help='explorer data dir (tools/fleet_viz/explorer/dataflow/data)')
    ap.add_argument('--only', nargs='*', default=None)
    ap.add_argument('--log', default='/home/ubuntu/claude-takeover-20261007/el1015-globalfp-s81.log')
    ap.add_argument('--work', default=None)
    a = ap.parse_args()
    cdir = Path(a.cands).parent
    C = json.loads(Path(a.cands).read_text())['candidates']
    canon = X.load(a.canon); plan = X.load(a.plan)
    base_graph = json.loads(Path(a.graph).read_text())
    work = Path(a.work or tempfile.mkdtemp(prefix='gfp_s81_rec_'))
    work.mkdir(parents=True, exist_ok=True)
    res = {}
    for c in C:
        m = c['metrics']; name = m['candidate']
        if a.only and name not in a.only:
            continue
        gpath = cdir / c['graph_ref'] if c.get('graph_ref') else Path(a.graph)
        g = json.loads(gpath.read_text()) if c.get('graph_ref') else base_graph
        cid = 'gfp_s81_' + name
        inputs = [dict(path='tools/fleet_viz/explorer/dataflow/data/s81_gen18c.links.json.gz', sha256=sha(a.canon), role='canonical base record'),
                  dict(path=str(a.plan), sha256=sha(a.plan), role='GEN18c pass0 construction plan (transport components)'),
                  dict(path=str(gpath), sha256=sha(gpath), role='GLOBAL-FP-S die data-flow graph (graph.py)'),
                  dict(path=str(a.cands), sha256=sha(a.cands), role='GLOBAL-FP-S candidates (layouts + objective)')]
        rec = X.export(canon, plan, g, c['layout'], m['vm_shape'], cid, 'S81 GLOBAL-FP-S · ' + name,
                       corridor=m.get('corridor'), region_x=tuple(m['region_x']) if m.get('region_x') else None, inputs=inputs)
        rp = work / (cid + '.json')
        rp.write_text(json.dumps(rec, separators=(',', ':')))
        note = ('%s | screen-only block-level candidate; hub links re-planned (stations every 215 um on L-routes, facing-face '
                'ends); t = width x class duty x 828,878 cycles/token (activity proxy); cr = 1 for field/su/coll classes. '
                'Objective (GLOBAL-FP-S score.py): traffic x length %.1f M bit.um/cycle, worst field round trip %.1f mm, '
                'legality overlaps %d') % ('; '.join(n for n in m['notes'] if not n.startswith('columns'))[:600],
                                          m['sum_traffic_bit_um_M'], m['field_worst_path_um'] / 1e3, m['legality']['overlaps'])
        subprocess.run([sys.executable, str(REPO / 'tools/fleet_viz/dataflow_links.py'), 'import', '--record', str(rp), '--out', a.out,
                        '--candidate-of', 's81_gen18c', '--candidate-agent', 'GLOBAL-FP-S', '--candidate-name', name,
                        '--candidate-note', note, '--candidate-log', a.log], check=True)
        idx = json.loads((Path(a.out) / 'index.json').read_text())
        row = next(r for r in idx['records'] if r['id'] == cid)
        res[name] = dict(id=cid, metrics=row['coverage']['metrics'], replan=rec['replan'])
        rp.unlink()
    idx = json.loads((Path(a.out) / 'index.json').read_text())
    canon_row = next(r for r in idx['records'] if r['id'] == 's81_gen18c')
    res['_canonical_s81_gen18c'] = dict(id='s81_gen18c', metrics=canon_row['coverage']['metrics'])
    (cdir / 'explorer_metrics.json').write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        mm = v['metrics']
        print('%-28s over_reach %7d  worst_cut %.3f (%d>0.6)  bit.um hops %.3f G  relay bit.stages %.2f M  t*L %s' % (
            k, mm['over_reach_bits'], mm['worst_cut'], mm['cut_windows_over_limit'], mm['sum_bit_um_hops'] / 1e9,
            (mm['relay_bit_stages'] or 0) / 1e6, mm['sum_traffic_length']))


if __name__ == '__main__':
    main()
