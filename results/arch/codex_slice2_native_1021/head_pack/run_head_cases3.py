import subprocess,concurrent.futures,os
os.environ['PYTHONPATH']='/work/pydeps'
def run(case):
 h,n=case
 with open(n+'.log','w') as f:return subprocess.run(['python3','head_pack2.py','561.6',h,n],stdout=f,stderr=subprocess.STDOUT).returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as ex:codes=list(ex.map(run,[('648','n648'),('691.2','n691'),('734.4','n734'),('777.6','n777')]))
print('CASE_EXITS',codes,flush=True)
raise SystemExit(0 if all(c==0 for c in codes) else 1)
