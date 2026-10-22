import pathlib,subprocess,json
r=pathlib.Path(__file__).resolve().parent;o=r.parent/'kv_chain';o.mkdir(exist_ok=True)
vl=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
results=[]
for name,source in [('positive','chain.sv'),('removed_rope_exclusion','mutant.sv')]:
 obj=o/name
 with (o/(name+'.build.log')).open('w') as log:subprocess.run([vl,'--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(obj),str(r/source),str(r/'tb.sv')],stdout=log,stderr=subprocess.STDOUT,check=True)
 p=subprocess.run([str(obj/'Vtb')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(o/(name+'.log')).write_text(p.stdout)
 ok=(p.returncode==0 and 'CHAIN_COLD_RESET_BOOT_ROPE_PASS' in p.stdout) if name=='positive' else p.returncode!=0 and ('wrong identity/scale' in p.stdout or 'TOKEN_COUNTS' in p.stdout)
 results.append(dict(name=name,returncode=p.returncode,ok=ok));print(results[-1],flush=True)
(o/'record.json').write_text(json.dumps(results,indent=2)+'\n');assert all(r['ok'] for r in results)
