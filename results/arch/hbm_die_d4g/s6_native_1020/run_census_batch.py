import json,sys,hashlib,subprocess,re,gzip
from pathlib import Path
rows=json.loads(Path(sys.argv[1]).read_text());work=Path(sys.argv[2]);work.mkdir(exist_ok=True,parents=True)
source=json.loads(Path('/work/current_source_check.json').read_text());source={r['cell']:r for r in source['rows']}
libroot=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');summary=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for row in rows:
 cell=row['cell'];m=row['meta'];remote=Path(m['remote']);out=work/cell;out.mkdir(exist_ok=True)
 receipt={'cell':cell,'master':row['view']['master'],'params':row['view']['params'],'top':m['actual_top'],'source_declared':m.get('declared_source_snapshot'),'source_current':'0ae60e322','local_identity_flags':row['local_identity_flags'],'current_source_mismatches':source[cell]['mismatches'],'errors':[],'status':'NOT RUN'}
 try:
  if receipt['local_identity_flags'] or receipt['current_source_mismatches']:raise ValueError('source/top/parameter wrapper correspondence refused')
  net=remote/(cell+'.netlist.v');ys=remote/(cell+'.ys');etm=remote/'etm_tt.tcl'
  fj_path=remote/(cell+'.files.json');fj=json.loads(fj_path.read_text());receipt['actual_files_json_sha256']=sha(fj_path)
  if fj.get('macros')!=m.get('actual_macro_declarations'):raise ValueError('actual mapped macro/master resolution differs from metadata')
  if fj.get('unresolved') or fj.get('ambiguous'):raise ValueError('unresolved or ambiguous source master graph '+str({'unresolved':fj.get('unresolved'),'ambiguous':fj.get('ambiguous')}))
  receipt['mapped_sha256']=sha(net);receipt['synthesis_script_sha256_actual']=sha(ys);receipt['etm_tt_sha256_actual']=sha(etm)
  if receipt['synthesis_script_sha256_actual']!=m['synthesis_script_sha256']:raise ValueError('actual synthesis script differs from metadata')
  if receipt['etm_tt_sha256_actual']!=m['etm_script_sha256']['tt']:raise ValueError('actual TT library script differs from metadata')
  expected_top=re.findall(r'^hierarchy -check -top (\S+)\s*$',ys.read_text(),re.M)
  if expected_top!=[m['actual_top']]:raise ValueError('actual synthesis top differs')
  actual_libs=re.findall(r'^read_liberty (\S+)\s*$',etm.read_text(),re.M)
  if not actual_libs:raise ValueError('actual TT library inventory missing')
  libs=[]
  for lib in actual_libs:
   if lib.startswith('/tmp/lib/'):
    name=Path(lib).name;candidates=[p for p in [libroot/name,libroot/(name+'.gz')] if p.is_file()]
    if len(candidates)!=1:raise ValueError('missing/ambiguous actual image Liberty '+lib)
    libs.append(candidates[0])
   elif lib.startswith('/src/'):
    rel=lib[5:];p=Path('/work/source_libs')/rel
    if rel not in m['source_file_sha256'] or sha(p)!=m['source_file_sha256'][rel]:raise ValueError('actual macro Liberty identity refused '+rel)
    libs.append(p)
   else:raise ValueError('unsupported actual Liberty location '+lib)
  receipt['actual_liberty']=[{'path':str(p),'sha256':sha(p)} for p in libs]
  cmd=[sys.executable,'/work/caller/tools/ref_tile/native_census.py','--netlist',str(net),'--top',m['actual_top'],'--out',str(out/'native.json')]
  for p in libs:cmd+=['--liberty',str(p)]
  with (out/'native.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
  raw=json.loads((out/'native.json').read_text());receipt.update(status=raw['status'],native_rc=rc,roots_examined=raw.get('roots_examined'),max_dynamic_loads=raw.get('max_dynamic_loads'),violations=len(raw.get('violations',[])),role_errors=raw.get('role_errors',[]))
 except Exception as exc:receipt['errors'].append(type(exc).__name__+': '+str(exc))
 (out/'correspondence.json').write_text(json.dumps(receipt,indent=2)+'\n');summary.append(receipt)
 (work/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('S6_NATIVE',cell,receipt['status'],receipt.get('max_dynamic_loads'),receipt['errors'],flush=True)
print('S6_BATCH_DONE',len(summary),flush=True)
