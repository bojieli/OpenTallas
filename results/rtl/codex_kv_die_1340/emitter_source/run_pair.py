from pathlib import Path
import os,sys,json,subprocess,collections,re,xml.etree.ElementTree as ET,hashlib,time
B=Path.cwd();old=B.parent/'codex-k-die-1340/paired_main14c';source=B.parent/'codex-kdie-main92-captured/source92'
import tarfile
for name in ['baseline','final']:
 root=B/name;root.mkdir()
 with tarfile.open(B/'main_tools_aecb.tar.gz')as tf:tf.extractall(root,filter='data')
 for n in ['rtl','physical','results']:(root/n).symlink_to((old/'baseline'/n).resolve(),target_is_directory=True)
subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(B/'selector.patch')],cwd=B/'final',check=True)
env=dict(os.environ,PYTHONPATH=str(old/'runtime902'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-c','import pytest,numpy;print(pytest.__version__,numpy.__version__)'],env=env,capture_output=True,text=True);assert p.returncode==0,p.stderr
runtime_preflight=p.stdout
records={}
for name in ['baseline','final']:
 env['PYTHONPATH']=str(old/'runtime902')+':'+str(B/name/'tools')
 with (B/(name+'.log')).open('w') as log:
  start=time.time();rc=subprocess.run(['/usr/bin/python3','-m','pytest','-q','--continue-on-collection-errors','tools/qwen_kv_die','--junitxml='+str(B/(name+'.xml'))],cwd=B/name,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900).returncode
 counter=collections.Counter();tests=0
 for tc in ET.parse(B/(name+'.xml')).iter('testcase'):
  tests+=1
  for e in tc:
   if e.tag not in ('failure','error'):continue
   msg=e.get('message','').replace(str(B/name),'<ROOT>');msg=re.sub(r'/tmp/tmp[a-zA-Z0-9_]+','<TMP>',msg)
   counter[json.dumps([tc.get('classname',''),tc.get('name',''),e.tag,msg])]+=1
 assert tests>0 and rc in (0,1,2),(name,tests,rc)
 records[name]=dict(returncode=rc,tests=tests,failure_counter=dict(counter),elapsed_seconds=round(time.time()-start,2));print(name,tests,len(counter),flush=True)
causal=r'''
import sys,json,re,os
sys.path.insert(0,'tools/qwen_kv_die');import kv_static_die as S
checks=[]
def yes(n,f):assert f(),n;checks.append(n)
selected=os.getenv('SELECTED')=='1'
bs=S.bindings()
if not selected:
 yes('default actual emitter identity',lambda:S.PUBLIC_RTL_FILE==S.RTL_FILE)
 yes('default CTL binding emitter',lambda:bs['qkd_kvs_ctl']['file']==S.RTL_FILE)
else:
 yes('selected exact gs2g6c emitter path',lambda:S.RTL_FILE.endswith('_ds_gs2_g6c.sv'))
 yes('selected emitter exists',lambda:(S.ROOT/S.RTL_FILE).is_file())
 yes('stale public absent fixture',lambda:not(S.ROOT/S.PUBLIC_RTL_FILE).exists())
 yes('CTL selects actual emitter',lambda:bs['qkd_kvs_ctl']['file']==S.RTL_FILE)
 text=(S.ROOT/S.RTL_FILE).read_text();body=re.search(r'\bmodule\s+qkd_kvs_ctl\b.*?\bendmodule',text,re.S)[0]
 yes('actual CTL109 attention interface',lambda:bool(re.search(r'output wire \[108:0\] o_attn',body)))
 yes('GRP exact CLOSEDsource override',lambda:bs['qkd_kvs_grp_s6c']['file']==S.GRP_S6C_RTL['grp'])
 yes('GRPH exact CLOSEDsource override',lambda:bs['qkd_kvs_grp_h_s6c']['file']==S.GRP_S6C_RTL['grp_h'])
 yes('GRP overrides not common emitter',lambda:bs['qkd_kvs_grp_s6c']['file']!=S.RTL_FILE)
 yes('all selected nonGRP static bindings emitter',lambda:all(bs['qkd_kvs_'+k]['file']==S.RTL_FILE for k in ['ctl','attn','emb','pc','pc_h']))
print(json.dumps(dict(checks=checks,count=len(checks),verdict='PASS')))
'''
causals={}
for flag in ['0','1']:
 ce={k:v for k,v in env.items()if not k.startswith('OT_KV_')}
 if flag=='1':
  ep=subprocess.check_output(['bash','-c','set -a; source "$1"; env -0','bash',str(B.parent/'codex-kdie-main92-captured/successor/kv_flags.env')])
  ce.update({k.decode():v.decode()for pair in ep.split(b'\0')if pair for k,v in [pair.split(b'=',1)]if k.startswith(b'OT_KV_')})
 ce['SELECTED']=flag
 p=subprocess.run(['/usr/bin/python3','-c',causal],cwd=B/'final',env=ce,capture_output=True,text=True);causals[flag]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
new=collections.Counter(records['final']['failure_counter'])-collections.Counter(records['baseline']['failure_counter'])
r=dict(baseline='aecb150bbc9c2228bd723956315dab1157163cdd',runtime=runtime_preflight,variants=records,causals=causals,new_failure_occurrences=dict(new),fixture_root=str(old/'baseline'),source_sha256={v:{n:hashlib.sha256((B/v/'tools/qwen_kv_die'/n).read_bytes()).hexdigest()for n in ['kv_static_die.py','kv_die.py','kv_grp_safe2.py','bind_views.py']}for v in records})
r['verdict']='PASS_NEW0'if not new and all(v['returncode']==0 for v in causals.values())else'FAIL';(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(r['verdict'],flush=True);sys.exit(0 if r['verdict']=='PASS_NEW0'else 1)
