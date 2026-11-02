"""Collect sole existing n4 pilot only after its exact scope finishes; never run CAD."""
import json,pathlib,subprocess,time,shlex
r=pathlib.Path(__file__).parent
root='/srv/opentallas-scratch2/claude/kw-eco-1/pilot/hd_st_n4/eco_20261101_215110_796908'
unit='oth-ubuntu-3838594-1793595776.scope'
probe=r'''
import json,pathlib,subprocess
root=pathlib.Path('/srv/opentallas-scratch2/claude/kw-eco-1/pilot/hd_st_n4/eco_20261101_215110_796908')
u='oth-ubuntu-3838594-1793595776.scope'
x=subprocess.run(['systemctl','--user','show',u,'-p','ActiveState','-p','SubState','-p','Result','-p','LoadState'],capture_output=True,text=True,timeout=10)
state=dict(l.split('=',1) for l in x.stdout.splitlines() if '=' in l)
try:cmd=pathlib.Path('/proc/796908/cmdline').read_bytes().replace(b'\0',b' ').decode()
except FileNotFoundError:cmd=''
worker='eco_loop.py run --kit /srv/opentallas-scratch2/claude/kw-eco-1/pilot/hd_st_n4 ' in cmd
try:d=json.loads((root/'eco_loop.json').read_text())
except (OSError,ValueError):d=None
print(json.dumps(dict(scope=state,systemctl_rc=x.returncode,exact_worker_present=worker,record=d)))
'''
while True:
 try:
  x=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','intel2','python3 -c '+shlex.quote(probe)],capture_output=True,text=True,timeout=25)
  if x.returncode:raise RuntimeError('SSH probe rc='+str(x.returncode))
  q=json.loads(x.stdout);q['checked_at']=time.time()
  (r/'N4_WATCH_STATUS.json').write_text(json.dumps(q,indent=1)+'\n')
  state=q['scope'];finished=state.get('ActiveState') in ('inactive','failed') or state.get('LoadState')=='not-found'
  if finished and not q['exact_worker_present']:
   d=q['record'];raw=d.get('verdict') if d else None;verdict=raw or 'ERROR_MISSING_RECORD'
   if raw=='PASS':
    lec=d.get('lec') or {}
    if not lec:verdict='PHYSICAL_PASS_LEC_MISSING'
    elif lec.get('exit')!=0 or lec.get('verdict')!='EQUIVALENT':verdict='LEC_FAIL_RECORDED'
   if d:(r/'N4_TERMINAL.json').write_text(json.dumps(d,indent=1)+'\n')
   notice=dict(verdict=verdict,raw_verdict=raw,source='intel2:'+root+'/eco_loop.json',exact_scope=unit,scope_state=state,exact_worker_present=False,collected_at=time.time(),scope='existing producer finished; raw record preserved, paired LEC joined; no source/parent credit inferred')
   (r/'N4_NOTICE.json').write_text(json.dumps(notice,indent=1)+'\n');break
 except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
  (r/'N4_WATCH_ERROR.json').write_text(json.dumps(dict(checked_at=time.time(),error=str(e)))+'\n')
 time.sleep(60)
