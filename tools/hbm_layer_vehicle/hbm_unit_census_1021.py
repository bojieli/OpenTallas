#!/usr/bin/env python3
"""Report original functional instances dropped or changed by generated transport."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
a,b,out=map(Path,sys.argv[1:]);A=json.loads(a.read_text());B=json.loads(b.read_text())
x,y=A['instances'],B['instances'];removed=sorted(set(x)-set(y));changes=[]
for key in sorted(set(x)&set(y)):
    before={k:x[key].get(k) for k in ['master','source','params','rtl_deps']}
    after={k:y[key].get(k) for k in before}
    if before!=after:changes.append({'instance':key,'before':before,'after':after})
r={'status':'PASS' if not removed and not changes else 'CHANGED','baseline_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'baseline_instances':len(x),'generated_instances':len(y),'removed_original_instances':removed,'changed_original_sources_or_params':changes,'added_master_counts':dict(sorted(Counter(v['master'] for k,v in y.items() if k not in x).items())),'scope':'Original functional instance/source/dependency/parameter census only. Added relay timing, wiring equivalence and calendar correctness require separate execution and final post-S8b comparison.'}
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print('HBM_UNIT_CENSUS',r['status'],len(x),len(y),'removed',len(removed),'changed',len(changes))
