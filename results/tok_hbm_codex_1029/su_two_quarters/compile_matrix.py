"""Compile actual shapes; retain failures and count the real finite calendars."""
from pathlib import Path
from types import SimpleNamespace,ModuleType
import contextlib,io,json,sys,subprocess,traceback
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
src=root/'tools/hbm_static/toksim_su/suvop/prod_compile.py'
def load(text,name):
 m=ModuleType(name);m.__file__=str(src);sys.modules[name]=m;exec(compile(text,str(src),'exec'),m.__dict__);return m
new=load(src.read_text(),'candidate')
old=load(subprocess.check_output(['git','show','a1d3c708f:tools/hbm_static/toksim_su/suvop/prod_compile.py'],cwd=root).decode(),'baseline')
def options(directory,record,nq,pin,qpr=1):
 return SimpleNamespace(out=str(directory),rec=record,quarters=nq,pin_reg=pin,full_side=True,rr=25,wr=22,
  fill_slack=1,drain_slack=2,side_ii=0,rfd_slack=1,pretree=True,qpr=qpr)
# A real lowered reduction and vector record are byte-identical under default
# four-quarter mode, including every operand and expected result/event.
identity=[]
for name in ['ds_moe_sum2','ds_route_total']:
 for m,label in [(old,'old'),(new,'new')]:
  m.MLAT,m.ALAT,m.WCOPY=4,3,0;m.LIN=m.SLB.lin(4,3,1)
  a=options(out/'identity'/name/label,name,4,None)
  with contextlib.redirect_stdout(io.StringIO()):m.compile_rec(a)
 files=['prog.mem','expw.mem','exps.mem','explw.mem','programme.json','arith/seed.mem','tree.mem']
 for f in files:
  a=out/'identity'/name/'old'/f;b=out/'identity'/name/'new'/f
  if a.exists() or b.exists():assert a.read_bytes()==b.read_bytes(),(name,f,'default changed')
 identity.append(name)
result={'default_byte_identity':identity,'source_qualified':False,'profiles':{},'remaining':[]}
for profile,mlat,alat,wcopy in [('minimal4_4_0',4,4,0),('alternate5_4_1',5,4,1)]:
 rows=[]
 for name,spec in sorted(new.RECS.items()):
  row={'record':name,'N':spec[1],'rows':spec[2],'cases':{}}
  for nq in [4,2]:
   new.MLAT,new.ALAT,new.WCOPY=mlat,alat,wcopy
   trials=[]
   for qpr in ([1,2] if nq==2 else [1,2,4]) if spec[5] else [1]:
    directory=out/profile/name/f'q{nq}_r{qpr}'
    try:
     with contextlib.redirect_stdout(io.StringIO()):cycles=new.compile_rec(options(directory,name,nq,1,qpr))
     p=json.loads((directory/'programme.json').read_text());trials.append({'qpr':qpr,'cycles':cycles,'edges':p['edges'],
      'issues':p['issues'],'emissions':p['emissions'],'expected_writes':p['expected_vm_writes'],
      'golden_reduction':p['reduction'].get('model_check'),'path':str(directory)})
    except Exception as e:
     directory.mkdir(parents=True,exist_ok=True);(directory/'compile_failure.txt').write_text(traceback.format_exc())
     trials.append({'qpr':qpr,'failure':str(e),'path':str(directory)})
   passing=[t for t in trials if 'cycles'in t]
   row['cases'][str(nq)]={'trials':trials,'best':min(passing,key=lambda t:t['cycles']) if passing else None}
  a,b=row['cases']['4']['best'],row['cases']['2']['best']
  if a and b:row.update(added_cycles=b['cycles']-a['cycles'],ratio=b['cycles']/a['cycles'])
  if not b:result['remaining'].append({'profile':profile,'record':name,'failures':row['cases']['2']['trials']})
  rows.append(row)
  print(profile,name,'2Q',b['cycles'] if b else 'FAIL','4Q',a['cycles'] if a else 'FAIL',flush=True)
 result['profiles'][profile]=rows
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print('MATRIX_DONE',len(result['remaining']),'unhandled_shapes',flush=True)
