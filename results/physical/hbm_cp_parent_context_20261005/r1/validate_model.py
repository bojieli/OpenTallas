import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import ast,types
model_path=Path.cwd()/'tools/uarch_model.py'
tree=ast.parse(model_path.read_text())
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'hbm_cp_balanced_veto_model','hbm_cp_validate_allocated_sources'}]
assert len(selected)==2
# Execute the actual bounded model bodies, without unrelated ROM import-time records.
ns={'__file__':str(model_path)}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(model_path),'exec'),ns)
m=types.SimpleNamespace(**ns)
r=m.hbm_cp_balanced_veto_model(measurement='results/rtl/hbm_cp_balanced_veto_20261005/exact_r1/terminal.json',parent_measurement='results/rtl/hbm_cp_parent_association_20261005/functional_r1/terminal.json',parent_context='results/rtl/hbm_child_contract_20261005/child_reservations.json')
assert r['allocated_parent_context']['physical_characterization_admitted']
assert r['allocated_parent_context']['slot_fit'] and r['allocated_parent_context']['channel_fit']
print(json.dumps(r,indent=2))
