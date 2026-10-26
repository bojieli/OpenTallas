from pathlib import Path
import os,sys,json,subprocess,collections,re,xml.etree.ElementTree as ET,hashlib,time,tarfile,shutil
B=Path.cwd();old=B.parent/'codex-k-die-1340/paired_main14c';base='5f43b44264ae01c39c9b0e42055d177e1fb94555';names=['kv_static_die.py','kv_bound_netlist.py','kv_port_bind_v2.sh'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['baseline','final']:
 root=B/name;root.mkdir()
 with tarfile.open(B/'base_tools.tar.gz')as tf:tf.extractall(root,filter='data')
 for n in ['rtl','physical','results']:(root/n).symlink_to((old/'baseline'/n).resolve(),target_is_directory=True)
for n in names:shutil.copyfile(B/n,B/'final/tools/qwen_kv_die'/n)
env={k:v for k,v in os.environ.items()if not k.startswith('OT_KV_')};env.update(PYTHONPATH=str(old/'runtime902'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-c','import pytest,numpy;print(pytest.__version__,numpy.__version__)'],env=env,capture_output=True,text=True);assert p.returncode==0,p.stderr
runtime=p.stdout;records={}
for name in ['baseline','final']:
 env['PYTHONPATH']=str(old/'runtime902')+':'+str(B/name/'tools');start=time.time()
 with (B/(name+'.log')).open('w')as log:rc=subprocess.run(['/usr/bin/python3','-m','pytest','-q','--continue-on-collection-errors','tools/qwen_kv_die','--junitxml='+str(B/(name+'.xml'))],cwd=B/name,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 tests=collections.Counter();failures=collections.Counter()
 for tc in ET.parse(B/(name+'.xml')).iter('testcase'):
  tests[json.dumps([tc.get('classname',''),tc.get('name','')])]+=1
  for e in tc:
   if e.tag not in ('failure','error'):continue
   msg=e.get('message','').replace(str(B/name),'<ROOT>');msg=re.sub(r'/tmp/tmp[a-zA-Z0-9_]+','<TMP>',msg)
   failures[json.dumps([tc.get('classname',''),tc.get('name',''),e.tag,msg])]+=1
 assert sum(tests.values())>0 and rc in (0,1,2),(name,rc,sum(tests.values()))
 records[name]=dict(returncode=rc,testcases=sum(tests.values()),testcase_counter=dict(tests),failure_counter=dict(failures),failure_occurrences=sum(failures.values()),elapsed_seconds=round(time.time()-start,2));print(name,records[name]['testcases'],records[name]['failure_occurrences'],flush=True)
new=collections.Counter(records['final']['failure_counter'])-collections.Counter(records['baseline']['failure_counter']);cases=collections.Counter(records['final']['testcase_counter'])==collections.Counter(records['baseline']['testcase_counter'])
r=dict(schema='opentallas.kv_source_authority.current_main_pair.v1',base_commit=base,runtime=runtime,fixture_root=str((old/'baseline').resolve()),fixture_paths={n:str((B/'baseline'/n).resolve())for n in ['rtl','physical','results']},same_fixture_paths=all((B/'baseline'/n).resolve()==(B/'final'/n).resolve()for n in ['rtl','physical','results']),variants=records,new_failure_occurrences=dict(new),same_testcase_counter=cases,tool_sha256={v:{n:sha(B/v/'tools/qwen_kv_die'/n)for n in names}for v in records},tools_archive_sha256=sha(B/'base_tools.tar.gz'),scope='full current-main KV helper suite against identical existing complete fixtures; source/native causals already accepted, no repeat/no native/build/physical')
r['verdict']='PASS_NEW0'if not new and cases and r['same_fixture_paths']else'FAIL';(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(r['verdict'],flush=True);sys.exit(0 if r['verdict']=='PASS_NEW0'else 1)
