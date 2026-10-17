import concurrent.futures,json,pathlib,subprocess,sys,hashlib
root=pathlib.Path.cwd();out=root.parent/'refresh_6b42bd40d';out.mkdir(exist_ok=True)
cases=[(pc,0)for pc in range(32)]+[(13,m)for m in (1,2,3,4,5)]
def run(c):
 pc,m=c;p=out/f'pc{pc}_m{m}';r=subprocess.run([sys.executable,'tools/qwen_static_kv/run_refresh_context_controller.py',str(p),'--pc',str(pc),'--mutant',str(m)],capture_output=True,text=True);(p/'driver.log').write_text(r.stdout+r.stderr);rec=json.loads((p/'receipt.json').read_text())if(p/'receipt.json').exists()else {};ok=r.returncode==(0 if m==0 else 1)and('PASS refresh context controller'if m==0 else'FAIL refresh context controller')in rec.get('output','');v=dict(pc=pc,mutant=m,exit=r.returncode,pass_expected=ok,receipt=rec);print('REFRESH_CASE',pc,m,r.returncode,ok,flush=True);return v
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(run,cases))
passed=all(v['pass_expected']for v in results)
(out/'summary.json').write_text(json.dumps(dict(passed=passed,runner_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),results=results,scope='component only; no measured physical PHY service/phase/drain/whole-token claim'),indent=2)+'\n');print('REFRESH_ALL',passed,flush=True);raise SystemExit(0 if passed else 1)
