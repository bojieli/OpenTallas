import os, subprocess,sys,json,hashlib
from pathlib import Path
b=Path(__file__).resolve().parent
root=Path.cwd()
cases={'default':[], 'pair':['--c-real','1','--k-real','3','--stages','2,2,2,3,2,2/11,11,9,9,9,9,9'], 'pair_phy9':['--c-real','1','--k-real','3','--phy','9'], 'pair_l0':['--c-real','1','--k-real','3','--layer','L0'], 'abut':['--stages','0,0,0,0,0,0/0,0,0,0,0,0,0']}
rows=[]
env=dict(os.environ,PYTHONPATH=str(root/'tools/qwen_split'))
for name,args in cases.items():
 a,bn=b/name/'baseline',b/name/'current'
 for src,out in [(b/'baseline.py',a),(root/'tools/qwen_split/xdie_exchange_cal.py',bn)]:
  p=subprocess.run([sys.executable,str(src),'--out',str(out),*args],env=env,text=True,capture_output=True)
  (b/(name+('_baseline.log' if out==a else '_current.log'))).write_text(p.stdout+p.stderr)
  assert p.returncode==0,(name,src,p.stderr)
 row={'case':name,'args':args,'files':{}}
 for n in ['cal_C_tx.memh','cal_C_rx.memh','cal_K_tx.memh','cal_K_rx.memh','txdp.svh']:
  x,y=(a/n).read_bytes(),(bn/n).read_bytes();assert x==y,(name,n)
  row['files'][n]=hashlib.sha256(x).hexdigest()
 def params(p):
  return {s.split('=')[0].strip():s.split('=')[1].strip() for s in p.read_text().splitlines() if '=' in s}
 x,y=params(a/'xdie_params.svh'),params(bn/'xdie_params.svh')
 assert all(y[k]==v for k,v in x.items()),(name,'params')
 row['legacy_params_equal']=True;row['additive_parameters']={k:v for k,v in y.items() if k not in x}
 rows.append(row)
r=dict(status='PASS',baseline='f4c1582ab',candidate='a31d2150824f072066a080c4cb35771013c18baf',scope='zero-default new flags:5historicalconfigurations, exact4memh+txdp equality and every preexistingparams equal; newmetadata allowed',cases=rows)
(b/'record.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'status':'PASS','cases':len(rows)}))
