import sys,json,hashlib
from pathlib import Path
root=Path.cwd().resolve();sys.path.insert(0,str(root/'tools'))
import ds_full_checkpoint_continuation_plan as P
manifest=P.load(root/P.MANIFEST);native=P.load(root/P.NATIVE)
checks={};original=P.missing_binding
for op in native['instructions']:
 for tid,bindings in op['provider_bindings'].items():
  for name,b in bindings.items():
   if b['kind']=='explicit_auxiliary_provider' and P.provider_handler(op,name,b)=='explicit immutable auxiliary manifest record':
    rec=manifest['view_bindings'].get(f"{op['pc']}/{tid}/{name}")
    if rec is None:continue
    p=Path(rec['path']);p=p if p.is_absolute() else root/p
    entry=checks.setdefault(str(p),{'references':[],'exists_at_audit':p.is_file(),'inside_checkout':p.is_relative_to(root)})
    entry['references'].append({'PC':op['pc'],'family':op['family'],'operand':name})
external={p for p,v in checks.items() if not v['inside_checkout']}
orig_is_file=Path.is_file
def absent(p):return False if str(p) in external else orig_is_file(p)
Path.is_file=absent
result=P.reconcile_from_retained(root/'results/uarch/ds_full_checkpoint_continuation_plan_20261003/r1/model.json')
Path.is_file=orig_is_file
record={'status':'EXTERNAL_PRESENCE_REQUIRED_FOR_FROZEN_BINDING_CLASSIFICATION','checked_payload_paths':checks,'external_unique_paths':len(external),'external_references':sum(len(checks[p]['references']) for p in external),'absence_model_gap_counts':result['binding_gap_counts'],'absence_model_sha256':hashlib.sha256(P.canonical(result)).hexdigest(),'first_external_PC':min(r['PC'] for p in external for r in checks[p]['references']),'payload_bytes_read':0,'frozen_model_modified':False,'numerical_execution':False}
Path('/tmp/ds-continuation-independent-evidence-20261003/external_presence_dependency.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='checked_payload_paths'}))
