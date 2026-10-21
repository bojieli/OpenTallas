from pathlib import Path
import json,subprocess
p=Path.cwd();v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';files=[str(p/x['path'])for x in json.load(open('manifest.json'))['files']]
for name,mut in [('good',0),('old_header',1)]:
 args=[str(v),'--binary','--timing','-Wno-fatal','--top-module','tb_k_status_header','--Mdir','obj_'+name,'-j','1','-GMUT_LEGACY='+str(mut)]+files+['tb_k_status_header.sv']
 with open(name+'_build.log','w')as o:r=subprocess.run(args,stdout=o,stderr=o)
 assert r.returncode==0,name
 with open(name+'.log','w')as o:r=subprocess.run([str(p/('obj_'+name)/'Vtb_k_status_header')],stdout=o,stderr=o)
 t=(p/(name+'.log')).read_text();assert (r.returncode==0 and 'K_STATUS_HEADER_PASS'in t)if mut==0 else(r.returncode!=0 and 'K_STATUS_EXTENSION_REJECTED'in t)
 print(name,'expected verdict PASS',flush=True)
