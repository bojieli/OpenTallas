#!/usr/bin/env python3
"""Launch exactly one immutable reset-CAP diagnostic; no adaptive stimulus."""
from pathlib import Path
import hashlib,json,subprocess,time,resource,datetime,os
b=Path.cwd();exe=b/'obj/Vtb_fullsix_trace'
if (b/'diagnostic.log').exists():raise SystemExit('REFUSE_EXISTING_DIAGNOSTIC')
assert hashlib.sha256(exe.read_bytes()).hexdigest()=='53da2c56f8c3881b9e9c6935eec46fe7179ecadce7779fd3e8d1821e461f1cc1'
for r in json.load(open('frozen_inputs.json'))['files']:
 assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
cgtext=Path('/proc/self/cgroup').read_text();cg=Path('/sys/fs/cgroup'+cgtext.strip().split(':',2)[2])
start=time.monotonic();UTC=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
with (b/'diagnostic.log').open('x') as log:
 p=subprocess.Popen([str(exe),'+DIR=.','+OT_ROM_DIR=images'],stdout=log,stderr=subprocess.STDOUT)
 # Record actual native image/PID/cgroup before waiting for its completion.
 identified=False
 while p.poll() is None:
  try:
   image=Path('/proc',str(p.pid),'exe').resolve()
   if image==exe:
    record=dict(UTC=UTC(),PID=p.pid,executable=str(image),argv=Path('/proc',str(p.pid),'cmdline').read_bytes().decode().split('\0'),native_proc_cgroup=Path('/proc',str(p.pid),'cgroup').read_text(),launcher_proc_cgroup=cgtext,cgroup_path=str(cg),same_native_and_launcher_cgroup=Path('/proc',str(p.pid),'cgroup').read_text()==cgtext)
    (b/'diagnostic_native_process.json').write_text(json.dumps(record,indent=2)+'\n');identified=True;break
  except OSError:pass
  time.sleep(.001)
 with (b/'diagnostic_process_samples.jsonl').open('x',buffering=1) as samples:
  while p.poll() is None:
   try:rss=int(Path('/proc',str(p.pid),'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
   except (OSError,IndexError):rss=None
   try:charge=int((cg/'memory.current').read_text());peak=int((cg/'memory.peak').read_text())
   except OSError:charge=peak=None
   samples.write(json.dumps(dict(UTC=UTC(),PID=p.pid,native_RSS_bytes=rss,cgroup_current_bytes=charge,cgroup_memory_peak_bytes=peak))+'\n');time.sleep(.5)
 rc=p.wait()
ru=resource.getrusage(resource.RUSAGE_CHILDREN)
try:peak=int((cg/'memory.peak').read_text())
except OSError:peak=None
(b/'diagnostic_execution.json').write_text(json.dumps(dict(scope='Exactly one original reset-CAP/F9 diagnostic; no healthy numeric/native/token claim',exit_status=rc,wall_seconds=time.monotonic()-start,child_user_seconds=ru.ru_utime,child_system_seconds=ru.ru_stime,single_native_child_max_RSS_KiB=ru.ru_maxrss,native_PID=p.pid,native_membership_recorded=identified,cgroup_path=str(cg),cgroup_kernel_memory_peak_bytes=peak,cgroup_peak_includes='launcher/input hashing and native image, including charged cache; not RSS',source_horizon=11900,source_horizon_is_original_observation_not_deadline=True,programme_retired_or_retimed=False,adaptive_stimulus=False,CAP_config='Original reset rcnt0/fmt1; source has0 target3 commands',numerical_PASS=None,native_phase=None),indent=2)+'\n')
print('ORIGINAL_RESET_CAP_DIAGNOSTIC_TERMINAL',rc,'NO_NUMERIC_PASS')
raise SystemExit(rc if rc>=0 else 128-rc)
