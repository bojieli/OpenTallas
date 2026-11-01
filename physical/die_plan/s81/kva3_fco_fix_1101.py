"""apply delta_kva3_1031.fco_rule to a finished OUT dir (plan text rewritten with delta_ws3_1031.write_plan)"""
import json, sys
from pathlib import Path
sys.argv, out = sys.argv[:1], Path(sys.argv[1])
sys.path.insert(0, 'physical/die_plan/s81')
import delta_kva3_1031 as D
pp = out / 'plan_h2_2249.json'
txt = pp.read_text(); cur = json.loads(txt); plan = json.loads(txt); log = []
rec = json.loads((out / 'receipt.json').read_text())
D.fco_rule(plan, rec['plan_changed_types'], log)
pp.write_text(D.DW.write_plan(txt, cur, plan, log))
assert json.loads(pp.read_text()) == plan
print(log[-3:])
