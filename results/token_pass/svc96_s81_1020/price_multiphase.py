"""All-layer MODEL sensitivities on the committed composer; no rate admission.

361 is the measured one-phase work span. Conservative serial configuration
adds one edge after retirement plus the existing 52-edge CFG_LEAD: 414 extra
cycles per a_proj occurrence. CAP/physical landing ages remain separate debts.
"""
import importlib.util
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D/'root'
sp = importlib.util.spec_from_file_location('tc', ROOT/'tools/toksim_s81_compose.py')
tc = importlib.util.module_from_spec(sp)
sp.loader.exec_module(tc)
orig = tc.node_cycles

def main():
    rows = []
    for groups in (16,8,4):
        for phase_cost in (0,361,414):
            counts = {}
            def priced(n,ov):
                v,how = orig(n,ov)
                op = n.get('op','')
                delta = phase_cost if op == 'attn.a_proj' else 0
                if op == 'attn.pv' or op.startswith('attn.scores'):
                    delta += 160*(16//groups-1)
                if delta:
                    counts[op] = counts.get(op,0)+1
                    return (float(n['cycles']) if v is None else v)+delta,'exact'
                return v,how
            tc.node_cycles = priced
            r = tc.build(ROOT/'results/token_pass/measured_s81_1019/elements')
            rows.append(dict(groups=groups, added_phase_cycles=phase_cost, changed_node_calls=counts,
                             workloads={k:{x:w[x] for x in ('T_cycles_fixed','T_cycles_solved','T_cycles','tok_s')}
                                        for k,w in r['workloads'].items()}))
    rec = dict(scope='ALL_LAYER_COMPOSER_MODEL_SENSITIVITY_NOT_SERVICE_OR_DIE_QUALIFICATION',
               phase_budget=dict(work=361, serial_config_guard=1, cfg_lead=52, conservative_added=414),
               excluded=['actual physical stage count and expert topology', 'new MU resource calendar',
                         'new CAP FIN/gather/landing ages','NT1/NT2 actual service throughput proof'],rows=rows)
    (D/'multiphase_price.json').write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps(rec,indent=1))

if __name__ == '__main__':
    main()
