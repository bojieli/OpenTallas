import time, pathlib, subprocess, re, os, json
start=int(time.time()); conf=pathlib.Path('/etc/ot-heavy.conf')
log=pathlib.Path('/var/tmp/ot-heavy/codex-ram-release-monitor.log')
while True:
 try:
  mem=pathlib.Path('/proc/meminfo').read_text(); avail=int(re.search(r'^MemAvailable:\s+(\d+)',mem,re.M)[1])/1024**2
  journal=subprocess.run(['journalctl','-u','earlyoom','--since','@'+str(start),'--no-pager','-o','cat'],capture_output=True,text=True).stdout
  oom=bool(re.search(r'Sending SIG(?:TERM|KILL)|killing process|killed process',journal,re.I))
  event=dict(epoch=int(time.time()),avail_gb=round(avail,2),pressure=pathlib.Path('/proc/pressure/memory').read_text().strip(),new_earlyoom=oom)
  if avail<64 or oom:
   text=conf.read_text(); text=re.sub(r'^INV_PAST_PEAK_FACTOR=.*$', 'INV_PAST_PEAK_FACTOR=1',text,flags=re.M)
   st=conf.stat(); tmp=conf.with_name(conf.name+'.codex-guard-'+str(os.getpid()));tmp.write_text(text);os.chmod(tmp,st.st_mode);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,conf)
   event['action']='RESTORED_FACTOR_1_NEW_ADMISSIONS_ONLY'
  with log.open('a') as f:f.write(json.dumps(event)+'\n')
  if avail<64 or oom:break
 except Exception as e:
  with log.open('a') as f:f.write(json.dumps(dict(epoch=int(time.time()),error=str(e)))+'\n')
 time.sleep(15)
