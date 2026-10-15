#!/usr/bin/env python3
"""GLOBAL-FP-H: write data-flow explorer records for scored candidates and register them as candidates of the HBM
canonical record (tools/fleet_viz/dataflow_links.py import --candidate-of).

sel.json: [{"tag", "dir", "label", "note", "graph"?}, ...]
  python3 tools/hbm_globalfp_publish.py --graph G.json --ref R.json --sel sel.json --opmap OPMAP.json --rec-dir DIR \
      --data-dir tools/fleet_viz/explorer/dataflow/data [--data-dir ~/.local/share/fleet-viz/explorer/dataflow/data]
"""
import argparse, hashlib, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_globalfp as F
import hbm_globalfp_run as R

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = '/home/ubuntu/claude-takeover-20261007/el1015-globalfp-hbm.log'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--ref', required=True); ap.add_argument('--sel', required=True)
    ap.add_argument('--opmap', required=True); ap.add_argument('--rec-dir', required=True)
    ap.add_argument('--data-dir', action='append', required=True); ap.add_argument('--base', default='hbm_v15_compact')
    a = ap.parse_args()
    os.makedirs(a.rec_dir, exist_ok=True)
    om = json.load(open(a.opmap))
    for s in json.load(open(a.sel)):
        mm = json.load(open(os.path.join(s['dir'], s['tag'] + '.metrics.json')))
        F.set_die(mm.get('die_h') or F.H_DIE_V15)
        gp = s.get('graph', a.graph)
        G = json.load(open(gp))
        for t in mm.get('transforms', []):
            G = {'hc_quad': R.t_hc_per_quadrant, 'npg4': R.t_npg4}[t](G)
        P = json.load(open(os.path.join(s['dir'], s['tag'] + '.P.json')))
        ref = json.load(open(a.ref))
        m = F.score(G, P, ref)
        rid = 'hbm_gfp_' + s['tag']
        inputs = [dict(path=gp, sha256=sha(gp), role='GLOBAL-FP-H die graph'),
                  dict(path=os.path.join(s['dir'], s['tag'] + '.P.json'), sha256=sha(os.path.join(s['dir'], s['tag'] + '.P.json')), role='placement')]
        rec = F.explorer_record(G, P, m, rid, s['label'], s['note'], LOG, base=a.base, inputs=inputs)
        rec['op_map'] = om['ops']
        rec['globalfp_metrics'] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()
                                   if k in ('J', 'sum_bits_mm', 'traffic_mm_qwen', 'traffic_mm_ds', 'relay_flops', 'bits_over_500',
                                            'fixed_return_violations', 'n_long_returns')}
        rec['globalfp_metrics']['worst_cut'] = m['worst_cut']['ratio']
        rec['globalfp_metrics']['die_mm2'] = round(F.W_DIE * F.H_DIE / 1e6, 2)
        rp = os.path.join(a.rec_dir, rid + '.json')
        json.dump(rec, open(rp, 'w'))
        for d in a.data_dir:
            cmd = [sys.executable, os.path.join(HERE, 'fleet_viz', 'dataflow_links.py'), 'import', '--record', rp, '--out', os.path.expanduser(d),
                   '--candidate-of', a.base, '--candidate-agent', 'GLOBAL-FP-H', '--candidate-name', s['label'],
                   '--candidate-note', s['note'], '--candidate-log', LOG]
            r = subprocess.run(cmd, capture_output=True, text=True)
            print(d, r.stdout.strip() or r.stderr.strip()[-400:])


if __name__ == '__main__':
    main()
