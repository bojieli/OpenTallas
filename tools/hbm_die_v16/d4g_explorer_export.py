#!/usr/bin/env python3
"""H-D4G 10-17: export the d4g plan to the Chip Explorer dataflow view (boxes + plan graph -> tools/fleet_viz/dataflow_links.py
hbm), as H-PLANSTUDY did for hbm_planstudy_a/b/c.
    d4g_explorer_export.py --plan-dir results/arch/hbm_die_d4g/plan/d4g_phy --id hbm_d4g_plan --out ~/.local/share/fleet-viz/explorer/dataflow/data
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan-dir', required=True); ap.add_argument('--id', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--label', default='HBM die d4g plan: (b) per-quadrant + channel-aligned quadrants (owner 0do)')
    a = ap.parse_args()
    d = ROOT / a.plan_dir
    P = json.loads((d / 'compact.P.json').read_text()); G = json.loads((d / 'compact.graph.json').read_text())
    W, H = json.loads((d / 'compact.metrics.json').read_text())['die_um']
    t = Path(tempfile.mkdtemp(prefix='d4gx_'))
    (t / 'boxes.json').write_text(json.dumps(dict(name=a.id, adoption_allowed=True, die_outline_um=[W, H],
                                                  boxes={k: dict(x=v['x'], y=v['y'], w=v['w'], h=v['h'], role=k.split('_')[0])
                                                         for k, v in P.items()})))
    (t / 'graph.json').write_text(json.dumps(dict(complete=True, source=a.id, nodes={}, edges=[
        dict(name=l['id'], source=[l['src'], l['cls']], sink=[l['dst'], l['cls']], bits=l['bits'], clock=l['cls'], binding=l['cls'])
        for l in G['links'] if l['src'] in P and l['dst'] in P])))
    cmd = [sys.executable, str(ROOT / 'tools/fleet_viz/dataflow_links.py'), 'hbm', '--id', a.id, '--out', a.out, '--label', a.label,
           '--design', 'hbm', '--token-designs', 'hbm_gen_qwen,hbm_gen_ds', '--revision', 'H-D4G 10-17 d4g.1', '--role', 'candidate',
           '--reach', '405', '--reach-source', 'results/arch/die_reach_1016.json (plan 405)', '--candidate-of', 'hbm_planstudy_b',
           '--candidate-agent', 'H-D4G', '--candidate-name', 'd4g plan', '--candidate-note',
           'owner 0do: plan (b) + lever 1 (SMs behind their PC half, centre lane channel, IDX beside PHY) + lever 2 (lanes); '
           'results/arch/hbm_die_d4g on claude/hd4g-1017', '--boxes', str(t / 'boxes.json'), '--graph', str(t / 'graph.json')]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-1500:]); sys.exit(r.returncode)


if __name__ == '__main__':
    main()
