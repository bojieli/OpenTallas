from pathlib import Path
import os,sys,json,subprocess,collections,re,xml.etree.ElementTree as ET,hashlib,time
B=Path.cwd();old=B.parent/'codex-k-die-1340/paired_main14c';source=B.parent/'codex-kdie-main92-captured/source92'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='92bccf72660ba3fb1e2de261a7e98b255591c900'
for name in ['baseline','final']:
 root=B/name;root.mkdir()
 subprocess.run(['cp','-a','--reflink=auto',str(source/'tools'),str(root/'tools')],check=True)
 for n in ['rtl','physical','results']:(root/n).symlink_to((old/'baseline'/n).resolve(),target_is_directory=True)
subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(B/'partial.patch')],cwd=B/'final',check=True)
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
import sys,json
sys.path.insert(0,'tools/qwen_kv_die');import kv_grp_safe2 as G
checks=[]
def yes(n,f):assert f(),n;checks.append(n)
def no(n,f):
 try:f()
 except ValueError:checks.append(n);return
 raise AssertionError(n+' accepted')
g=G.MASTERS['grp'];h=G.MASTERS['grp_h'];parent=lambda m,e='n[0:0]',c='c[193:0]':m+' u (.x__est('+e+'),.i_ctl('+c+'));'
yes('partial absent EST remains absent',lambda:G.frame_port_widths(g,{'other':7},partial=True)=={'other':7})
yes('partial H no private ports',lambda:G.frame_port_widths(h,{'other':7},partial=True)=={'other':7})
yes('partial H EST present normalized',lambda:G.frame_port_widths(h,{'x__est':13},partial=True)=={'x__est':1})
yes('partial H CTL present normalized',lambda:G.frame_port_widths(h,{'i_ctl':271},partial=True)=={'i_ctl':194})
no('full missing EST',lambda:G.frame_port_widths(g,{}))
no('full missing HCTL',lambda:G.frame_port_widths(h,{'x__est':13}))
no('partial wrong present EST',lambda:G.frame_port_widths(g,{'x__est':12},partial=True))
no('partial wrong present HCTL',lambda:G.frame_port_widths(h,{'i_ctl':270},partial=True))
no('full unsliced EST',lambda:G.frame_port_widths(g,{'x__est':13},parent(g,e='n')))
no('full unsliced HCTL',lambda:G.frame_port_widths(h,{'x__est':13,'i_ctl':271},parent(h,c='c')))
yes('full strict private slices',lambda:G.frame_port_widths(h,{'x__est':13,'i_ctl':271},parent(h))=={'x__est':1,'i_ctl':194})
yes('unselected default unchanged',lambda:G.frame_port_widths('qkd_kvs_grp',{'x__est':13},partial=True)=={'x__est':13})
print(json.dumps(dict(checks=checks,count=len(checks),verdict='PASS')))
'''
causals={}
for flag in ['0','1']:
 ce={k:v for k,v in env.items()if not k.startswith('OT_KV_')};ce['OT_KV_GRP_S6C']=flag
 p=subprocess.run(['/usr/bin/python3','-c',causal],cwd=B/'final',env=ce,capture_output=True,text=True);causals[flag]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
new=collections.Counter(records['final']['failure_counter'])-collections.Counter(records['baseline']['failure_counter'])
r=dict(baseline='92bccf72660ba3fb1e2de261a7e98b255591c900',runtime=runtime_preflight,variants=records,causals=causals,new_failure_occurrences=dict(new),fixture_root=str(old/'baseline'),source_sha256={v:{n:hashlib.sha256((B/v/'tools/qwen_kv_die'/n).read_bytes()).hexdigest()for n in ['kv_die.py','kv_grp_safe2.py','bind_views.py']}for v in records})
r['verdict']='PASS_NEW0'if not new and all(v['returncode']==0 for v in causals.values())else'FAIL';(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(r['verdict'],flush=True);sys.exit(0 if r['verdict']=='PASS_NEW0'else 1)
