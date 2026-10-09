import os,pathlib,json,hashlib,shutil,signal,time
pid=1753201
p=pathlib.Path(f'/proc/{pid}')
stat=p.joinpath('stat').read_text();fields=stat[stat.rfind(')')+2:].split()
argv=[x.decode() for x in p.joinpath('cmdline').read_bytes().split(b'\0') if x]
cwd=os.readlink(p/'cwd')
assert fields[19]=='10042562', 'PID start changed'
assert argv==['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-exit','/probe/probe_sr_displacement.tcl'],argv
assert cwd=='/OpenROAD-flow-scripts',cwd
assert fields[1]=='1753187','Parent changed'
j=pathlib.Path('/srv/opentallas-scratch2/scratch/codex/hbm-collector-sr-dpl-inspect-20261009')
a=j/'infeasible-fixed-geometry-1753201';a.mkdir(exist_ok=False)
names=['probe_sr_displacement.tcl','run_probe_sr.sh','sr-displacement-probe.log','sr-displacement-probe-guard.log','sr-pin-anchor-bbox-audit.log','audit_sr_pin_anchor_bboxes.tcl','probe_sr_bounded_release181.tcl','sr-geometry-selftest-positive.log','sr-geometry-selftest-wrongmovement.log']
hashes={}
for name in names:
 src=j/name;shutil.copyfile(src,a/name);hashes[name]=hashlib.sha256((a/name).read_bytes()).hexdigest()
r={'verdict':'TERMINATED_INFEASIBLE_FIXED_GEOMETRY','authorization':'Root explicitly authorized onlydiagnostic stop after exact identity/archive;181 actual frozen-anchor physical overlaps establish infeasibility, not elapsed/iteration cutoff','pid':pid,'start_ticks':fields[19],'parent':fields[1],'argv':argv,'cwd':cwd,'stat':stat,'status':p.joinpath('status').read_text(),'archived_sha256':hashes,'signal':'SIGTERM','source_branch':'codex/hbm-collector-dpl-20261009','bounded_source':'b0139ca07','bounded_sha256':hashlib.sha256((j/'probe_sr_bounded_release181.tcl').read_bytes()).hexdigest(),'timing_or_RTL_verdict':False}
(a/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
os.kill(pid,signal.SIGTERM)
while p.exists():
 try:
  now=p.joinpath('stat').read_text(); nf=now[now.rfind(')')+2:].split()
  if nf[19]!='10042562':break
 except FileNotFoundError:break
 time.sleep(1)
shutil.copyfile(j/'sr-displacement-probe.log',a/'sr-displacement-probe-terminal.log')
r['actual_identity_absent']=True;r['terminal_log_sha256']=hashlib.sha256((a/'sr-displacement-probe-terminal.log').read_bytes()).hexdigest()
(a/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'verdict':r['verdict'],'pid':pid,'actual_identity_absent':True,'archive':str(a),'bounded_sha256':r['bounded_sha256']}))
