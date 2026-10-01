import json,pathlib,subprocess,time,os,sys
out=pathlib.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/local_disk_recovery_20261001');main='/home/ubuntu/OpenTallas'
p=sys.argv[1];head_expected=sys.argv[2]
# Own audit wrapper commands mention candidates; ignore only our current ancestor PIDs.
anc=set();pid=os.getpid()
while pid>1:
 anc.add(pid)
 try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
snap=subprocess.check_output(['sudo','-n','python3','/tmp/disk-recovery-proc.py'],text=True);rows=json.loads(snap);assert not rows['errors']
hits=[r['pid'] for r in rows['rows'] if r['pid'] not in anc and (p in r['cmd'] or any(x==p or x.startswith(p+'/') for x in r['links']) or p+'/' in r.get('maps',''))];assert not hits,hits
r=subprocess.run(['git','-C',p,'status','--porcelain=v1','--untracked-files=all'],capture_output=True,text=True);assert r.returncode==0 and not r.stdout,(r.stdout,r.stderr)
head=subprocess.check_output(['git','-C',p,'rev-parse','HEAD'],text=True).strip();assert head==head_expected
merged=subprocess.run(['git','-C',p,'merge-base','--is-ancestor',head,'89eace61f']).returncode==0
assert merged or len(sys.argv)>3, 'Unmerged HEAD needs explicit owner retirement'
raw=subprocess.check_output(['git','-C',main,'worktree','list','--porcelain'],text=True);block=next(b for b in raw.split('\n\n') if b.startswith('worktree '+p+'\n'));assert '\nlocked' not in block
ref='refs/maintenance/disk-recovery-20261001/'+pathlib.Path(p).name;subprocess.run(['git','-C',main,'update-ref',ref,head,'0'*40],check=True)
free=lambda:os.statvfs(main).f_bavail*os.statvfs(main).f_frsize
size=int(subprocess.check_output(['du','-s','-B1',p],text=True).split()[0]);before=free();rec={'path':p,'head':head,'preserved_ref':ref,'allocated_bytes_before':size,'free_before':before,'process_hits':hits,'own_ancestor_pids_excluded':list(anc),'processes_scanned':len(rows['rows']),'status':r.stdout,'locked':False,'merged_to':'89eace61f' if merged else None,'owner_retirement':sys.argv[3] if len(sys.argv)>3 else None,'timestamp':time.time()}
(out/(pathlib.Path(p).name+'_removal_before.json')).write_text(json.dumps(rec,indent=2)+'\n')
r=subprocess.run(['git','-C',main,'worktree','remove',p],capture_output=True,text=True)
rec.update(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,free_after=free(),path_exists=pathlib.Path(p).exists());rec['filesystem_free_delta']=rec['free_after']-before
(out/(pathlib.Path(p).name+'_removal_after.json')).write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2),flush=True)
