import subprocess,concurrent.futures,os
os.environ['PYTHONPATH']='/work/pydeps'
def run(case):
 h,n=case
 with open(n+'.log','w') as f:return subprocess.run(['python3','head_pack.py','561.6',h,n],stdout=f,stderr=subprocess.STDOUT).returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as ex:codes=list(ex.map(run,[('518.4','h518'),('604.8','h604'),('691.2','h691'),('777.6','h777')]))
print('CASE_EXITS',codes,flush=True)
raise SystemExit(0 if all(c==0 for c in codes) else 1)
