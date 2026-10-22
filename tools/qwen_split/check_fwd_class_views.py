#!/usr/bin/env python3
"""Bind generated parallel classes to actual closed native views; no view aliases."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_fwd_class_emit import Composition, V
from qwen_split import fwd_class_emit as F
from qwen_split.audit_fwd_class_bind import audit
from qwen_tp8 import bind_real

out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
repo=Path(sys.argv[2]).resolve()
v,m=Composition().vehicle(1088);F.install(v,m)
v.write_netlist(m,1,out/'die.v')
pw=v.port_widths(m,1)
(out/'elements.lef').write_text('\n'.join(V.lef_text(mst,1,{p:pw.get((name,p),0) for p in mst.order})[0]
                                            for name,mst in v.masters(m,1).items()))
with patch.object(sys,'argv',['bind_real.py','--case',str(out),'--repo',str(repo),'--out',str(out/'bind.json')]):
    bind_real.main()
r=audit(out/'die.v',json.loads((out/'bind.json').read_text()))
(out/'class_bind_audit.json').write_text(json.dumps(r,indent=1)+'\n')
print(f'CLASS_NATIVE_VIEWS {r["verdict"]} instances={r["lane_instances"]} masters={len(r["class_masters"])} failures={r["failures"]}')
if r['verdict']!='PASS':raise SystemExit(1)
# A missing native row must not be silently categorized as a skipped relay.
b=json.loads((out/'bind.json').read_text());b['masters_detail'].pop(next(iter(b['masters_detail'])))
assert audit(out/'die.v',b)['verdict']=='FAIL'
print('CLASS_MISSING_NATIVE_REFUSED PASS')
