import sys,pathlib,json
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'tools/hier_contract'));import pinreg_audit as P
o=r/'results/arch/qw_landw_1019/native_1020';rows=[]
for j in json.loads((o/'jobs.json').read_text()):
 d=r/j['view'];ins=json.loads((d/'insertion.json').read_text());x=dict(job=j['job'])
 for c in ['tt','ff']:
  f=d/(j['cell']+'_'+c+'.lib');f=f if f.exists() else pathlib.Path(str(f)+'.gz');lib=P.parse_lib(f);m=P.pin_metrics(lib,P.clock_refs(lib,ins,c));v=m.get('en',{});x[c]=v;x[c+'_capture_under_190']=v.get('inp') is not None and v['inp']<190
 rows.append(x)
(o/'en_capture.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
