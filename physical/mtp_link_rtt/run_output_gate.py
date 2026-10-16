#!/usr/bin/env python3
"""Full512b RTT receiver with elastic output: exact/full-rate/hold under stalls."""
import argparse, ast, hashlib, json, sys
from pathlib import Path
from run_gate import ROOT,SRC,run
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
pairs=[(0,0),(5,6),(6,7),(9,10),(10,9)]
node=next(n for n in ast.parse((ROOT/'tools/uarch_model.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_mtp_grant_rtt_model')
ns={'DFF_UM2':.2916};exec(compile(ast.Module(body=[node],type_ignores=[]),'unified_model','exec'),ns)
models=[ns[node.name](f,r,output_pipe=True) for f,r in pairs];(a.out/'model.json').write_text(json.dumps(models,indent=2)+'\n')
rows=[run(a.out,f,r,s,1,stress=t,output_pipe=1) for f,r in pairs for s in (0,1) for t in (0,1)]
rows += [run(a.out,f,r,s,1,mutant=True,output_pipe=1) for f,r in pairs for s in (0,1)]
record=dict(status='PASS' if all(r['gate_pass'] for r in rows) else 'FAIL',scope='Full512bit optional elastic output stage; exact payload/order/fullrate and stable stalled outputs at actual registered relay counts; charged +1cycle',adopted=False,physical_closed=False,sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SRC},models=models,runs=rows)
(a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
print(record['status'],'RTT_OUTPUT',len(rows),'cases',sum(r['measurement'].get('received',0) for r in rows),'exact flits')
if record['status']!='PASS':sys.exit(1)
