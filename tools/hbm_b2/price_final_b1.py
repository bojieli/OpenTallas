#!/usr/bin/env python3
"""Compose one complete HBM baseline/candidate pair, never sums of lane deltas.

This produces a conditional architecture-model result. It does not accept a
rate, qualify native source throughput, or claim die timing/token closure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, root, log, env=None):
    with log.open('w') as out:
        result = subprocess.run(command, cwd=root, stdout=out, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        raise RuntimeError(f'{command[0]} exited {result.returncode}; see {log}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--base-stages', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--source-scope', required=True)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'tools'))
    from die_plan.schema import Plan
    if a.out.exists():
        ap.error('output exists; preserve previous result')
    # The old model silently defaults to an empty ledger if this input is absent.
    ledger = root / 'results/arch/hbm_d4g_price_1017/latency_ledger.json'
    if not json.loads(ledger.read_text()).get('entries'):
        ap.error('measured architecture latency ledger must be present')
    a.out.mkdir(parents=True)
    plans, inputs, tables = {}, {}, {}
    for label, source in [('baseline', a.baseline), ('candidate', a.candidate)]:
        source = source / 'die_plan.json' if source.is_dir() else source
        source = source.resolve()
        plan = json.loads(source.read_text())
        p = Plan(plan, str(source))
        # Recompute every lane from the exact geometry and coherent group pads.
        plan['latency'] = dict(lanes={lane['id']: p.lane_latency(lane['id']) for lane in plan['lanes']})
        out = a.out / label
        out.mkdir()
        (out / 'die_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
        inputs[label] = dict(path=str(source), sha256=digest(source), lanes=len(plan['lanes']))
        plans[label] = plan
        run([sys.executable, 'physical/die_plan/hbm_arch/hbm_rows.py', str(out)], root, out/'rows.log')
        env = dict(os.environ, HBM_ARCH_B2='1')
        run([sys.executable, 'physical/die_plan/hbm_arch/stages_arch.py', str(out),
             str(a.base_stages.resolve()), str(out/'stages.json'), '--slot', 'plan_c_inner', '--slot', 'plan_c'],
            root, out/'stages.log', env)
        stages = json.loads((out/'stages.json').read_text())
        if stages['plan_c'] != stages['plan_c_inner']:
            raise RuntimeError('plan_c and plan_c_inner must both consume the same exact plan')
        env = dict(os.environ, PYTHONPATH=str(root/'tools'))
        run([sys.executable, '-m', 'hgi_sim.plan_study_price_1017', '--stages', str(out/'stages.json'),
             '--x-c', '377.6', '--jobs', '4', '--out', str(out/'price.json')], root, out/'price.log', env)
        tables[label] = json.loads((out/'price.json').read_text())['table']['c_L4|377.6']
        if digest(source) != inputs[label]['sha256']:
            raise RuntimeError('source plan changed during price; use a stable artifact')
    def lane_map(plan):
        ports = {p['id']: p for p in plan['ports']}
        result = {}
        for lane in plan['lanes']:
            src, dst = ports[lane['ports'][0]], ports[lane['ports'][-1]]
            result[lane['id']] = dict(source=src['src'], destination=dst['dst'], width=src['width'],
                                      latency=plan['latency']['lanes'][lane['id']])
        return result
    before, after = lane_map(plans['baseline']), lane_map(plans['candidate'])
    changes = {}
    for lid in sorted(set(before)|set(after)):
        b, c = before.get(lid), after.get(lid)
        if b != c:
            same = bool(b and c and all(b[k] == c[k] for k in ['source','destination','width']))
            changes[lid] = dict(before=b, after=c, same_contract=same,
                cycle_delta=c['latency']['cycles']-b['latency']['cycles'] if same else None)
    b, c = tables['baseline'], tables['candidate']
    result = dict(schema='opentallas.hbm_final_plan_pair_price.v1', status='CONDITIONAL_MODEL_NOT_ADOPTED',
        source_scope=a.source_scope, inputs=inputs, measured_latency_ledger_sha256=digest(ledger),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        prices=tables, added_ar_cycles=c['ar_cycles']-b['ar_cycles'],
        added_mtp_step_cycles=c['mtp_step_cycles']-b['mtp_step_cycles'],
        ar_loss_pct=100*(1-b['ar_cycles']/c['ar_cycles']),
        mtp_loss_pct=100*(1-b['mtp_step_cycles']/c['mtp_step_cycles']),
        changed_lanes=changes, headline_or_acceptance_changed=False,
        qualification='No native arithmetic/source throughput, physical timing or G5 qualification from this model')
    (a.out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','prices','added_ar_cycles','added_mtp_step_cycles','ar_loss_pct','mtp_loss_pct']}))


if __name__ == '__main__':
    main()
