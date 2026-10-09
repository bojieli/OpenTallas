#!/usr/bin/env python3
"""Remote gate driver: admission wrapper plus observed whole process group peak."""
import json,os,pathlib,subprocess,sys,time
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
with (out/'driver.log').open('w') as log:
 p=subprocess.Popen(sys.argv[2:],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 peak=0;samples=0
 while p.poll() is None:
  rss=0
  for f in pathlib.Path('/proc').iterdir():
   if not f.name.isdigit():continue
   try:
    st=(f/'stat').read_text().rsplit(')',1)[1].split()
    if int(st[2])==p.pid:rss+=int(st[21])*os.sysconf('SC_PAGE_SIZE')
   except (OSError,ValueError,IndexError):pass
  peak=max(peak,rss);samples+=1;time.sleep(.02)
 rc=p.wait()
 (out/'process_group.json').write_text(json.dumps(dict(driver_pid=p.pid,returncode=rc,observed_whole_pg_peak_bytes=peak,samples=samples,sample_seconds=.02),indent=2)+'\n')
sys.exit(rc)
