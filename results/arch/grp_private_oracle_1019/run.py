#!/usr/bin/env python3
import os,subprocess,json,re,hashlib,sys
from pathlib import Path
D=Path(__file__).resolve().parent; os.chdir(D)
v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
version=subprocess.check_output([v,'--version'],text=True).strip(); assert '5.050' in version
print(version,flush=True)
original=(D/'private.sv').read_text()
cases=[('positive',None,None),('est_grp','qkd_kvs_grp_private0','y__est__0_1'),('down_grp','qkd_kvs_grp_private0','o_dn'),('ctl_h','qkd_kvs_grp_h_private0','o_ctl'),('est_h','qkd_kvs_grp_h_private0','y__est__0_1')]
if '--extra-permutation' in sys.argv:
 cases=[('down_permutation','qkd_kvs_grp_private0','o_dn')]
results=[]
for name,mod,port in cases:
 text=original
 if mod:
  a=text.index('module '+mod+' '); b=text.index('endmodule',a)
  body=text[a:b]; pat=r'(assign '+port+r' = )(.*?);'; m=re.search(pat,body); assert m
  expr='~('+m.group(2)+')' if port.startswith('y__est') else ('{'+m.group(2)+'} ^ 1')
  if name=='down_permutation': expr='i_ctl'
  # Mutate the retained source equation itself. EST inversions, down-word bit corruption, H control status corruption.
  body=body[:m.start()]+m.group(1)+expr+';'+body[m.end():]; text=text[:a]+body+text[b:]
 (D/(name+'.sv')).write_text(text)
 cmd=[str(v),'--binary','--timing','-j','8','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb','--Mdir','build_'+name,'tb.sv','original.sv',name+'.sv','leaves.sv']
 with open(name+'.build.log','w') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
 if rc: raise RuntimeError((name,'build',rc))
 with open(name+'.log','w') as log: rc=subprocess.run(['./build_'+name+'/Vtb'],stdout=log,stderr=subprocess.STDOUT).returncode
 log=Path(name+'.log').read_text(); expected='PRIVATE_PASS' if mod is None else 'PRIVATE_FAIL'
 ok=(rc==0 and expected in log) if mod is None else (rc!=0 and expected in log and f'output={port} ' in log)
 results.append(dict(case=name,source_sha256=hashlib.sha256(text.encode()).hexdigest(),rc=rc,expected=expected,pass_=ok,witness=log))
 print(json.dumps(results[-1]),flush=True)
 Path('permutation_results.json' if '--extra-permutation' in sys.argv else 'results.json').write_text(json.dumps(dict(version=version,cases=results),indent=2)+'\n')
 if not ok: raise RuntimeError((name,'unexpected verdict'))
print('ALL_PRIVATE_CASES_PASS',flush=True)
