from pathlib import Path
import json,subprocess,os,sys,time,signal,tarfile,collections,re,xml.etree.ElementTree as ET
B=Path.cwd();old=json.loads((B/'receipt.json').read_text());old['verdict']='NOTRUN_PYTEST_MISSING';(B/'rejected_empty_receipt.json').write_text(json.dumps(old,indent=2)+'\n')
assert json.loads((B/'runtime_preflight.json').read_text())['pytest']['returncode']==0
old['runtime_preflight']=json.loads((B/'runtime_preflight.json').read_text())
env=dict(os.environ,PYTHONPATH=str(B/'runtime902'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
records={}
for name in ['baseline','final']:
 env['PYTHONPATH']=str(B/'runtime902')+':'+str(B/name/'tools')
 (B/(name+'.xml')).unlink(missing_ok=True)
 with(B/(name+'.log')).open('w')as log:
  t=time.time();p=subprocess.Popen(['/usr/bin/python3','-m','pytest','-q','--continue-on-collection-errors','tools/qwen_kv_die','--junitxml='+str(B/(name+'.xml'))],cwd=B/name,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=p.wait(timeout=900)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait();rc=124
  xp=B/(name+'.xml');failures={};tests=0;counter=collections.Counter()
  if xp.exists():
   for tc in ET.parse(xp).iter('testcase'):
    tests+=1;key=tc.get('classname','')+'::'+tc.get('name','');es=[e for e in tc if e.tag in('error','failure')]
    if es:
     failures[key]=[{'kind':e.tag,'message':e.get('message','')}for e in es]
     for e in es:
      message=e.get('message','').replace(str(B/name),'<ROOT>')
      message=re.sub(r'/tmp/tmp[a-zA-Z0-9_]+','<TMP>',message)
      counter[json.dumps([key,e.tag,message])]+=1
  records[name]={'returncode':rc,'elapsed_seconds':round(time.time()-t,2),'counts':{'tests':tests,'failure_cases':len(failures)},'failures':failures,'failure_counter':dict(counter)}
  print(name,rc,tests,len(failures),flush=True)
old['variants']=records;old['new_failure_cases']=sorted(set(records['final']['failures'])-set(records['baseline']['failures']))
newcounter=collections.Counter(records['final']['failure_counter'])-collections.Counter(records['baseline']['failure_counter'])
old['new_failure_occurrences']=dict(newcounter)
old['pytest_runtime']='ROOT runtime902 SHA db0143f7bfd98f8a7dc733594840ea8d445bfe6aacd6bc8f9036bbb61611e291 + py.py SHA b71675b5d9845ba0814e9e88767f88dac3b3cc0d3128da028bd45edbb523e871; identical isolated environment; system NumPy2.3.5 preflight PASS'
old['verdict']='PASS_NEW0'if not old['new_failure_cases']and not newcounter and all(x['counts']['tests']>0 and x['returncode']in(0,1,2)for x in records.values())and all(x['returncode']==0 for x in old['causals'].values())else'FAIL_OR_INCOMPLETE'
(B/'receipt.json').write_text(json.dumps(old,indent=2)+'\n');print(old['verdict'],flush=True)
raise SystemExit(0 if old['verdict']=='PASS_NEW0'else 1)
