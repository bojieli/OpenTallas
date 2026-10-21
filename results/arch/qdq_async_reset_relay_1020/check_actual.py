"""Replay the recognition against the unchanged real mapped netlist + causal negatives."""
import importlib.util
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('textbook_lint', ROOT / 'tools/textbook_lint.py')
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
D = Path(__file__).resolve().parent
text = (D / 'mapped.v').read_text()

def graph():
    return T.flatten(T.parse_verilog(text), 'ot_hgi_qdq_transport_ctl_r4')[0]

def proof(g):
    return T.async_reset_relay_proof(g, T.build(g, None), g.ports['rst_n'][1])

r = proof(graph())
assert r['pass'] and r['raw_clear_loads'] == 6 and r['regional_leaves'] == 4
assert r['release_edges'] == 3 and r['max_regional_loads'] == 27
checks = {'actual': r}
for scenario in ['wrong_clock', 'raw_functional_bypass', 'insufficient_stage', 'wrong_polarity']:
    g = graph()
    if scenario == 'wrong_clock':
        cell = next(c for c in g.cells if c[1] == 'u_rst.sync_q[1]$_DFF_PN0_')
        cell[2]['CLK'] = [g.net('causal_foreign_clock')]
    elif scenario == 'insufficient_stage':
        cell = next(c for c in g.cells if c[1] == 'u_rst.rst_n[0]$_DFF_PN0_')
        cell[2]['D'] = [g.net('u_rst.sync_q[0]')]
    elif scenario == 'wrong_polarity':
        cell = next(c for c in g.cells if c[1] == 'u_rst.sync_q[1]$_DFF_PN0_')
        first = next(c for c in g.cells if c[1] == 'u_rst.sync_q[0]$_DFF_PN0_')
        cell[2]['D'] = first[2]['QN'][:]
    else:
        cell = next(c for c in g.cells if c[0].startswith('DFFASRHQN') and not c[1].startswith('u_rst.'))
        cell[2]['RESETN'] = [g.ports['rst_n'][1]]
    result = proof(g)
    assert not result['pass'], scenario
    checks[scenario] = result
print(json.dumps(checks, indent=2))
