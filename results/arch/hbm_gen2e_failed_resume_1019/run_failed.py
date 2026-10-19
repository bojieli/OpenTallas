import subprocess,json,pathlib,concurrent.futures,datetime,shlex
A=pathlib.Path(__file__).resolve().parent
M=json.loads(pathlib.Path('/home/ubuntu/wt/hbm-gen2e-failed-resume-1019/results/arch/hbm_synth_source_unique_1019/failed_only_resume.json').read_text())
R='/srv/opentallas-scratch/claude/hd4g/gen2e2/failed_resume_1019'
S='/srv/opentallas-scratch/claude/hd4g/gen2e2/src_6f783d0a1'
def run(x):
 cell,m,w,mem,bb,env=x['row'];extra=x['failure']['rounds'][0]['extra'];pref='v16w/prefer_'+cell+'.txt';out=R+'/'+cell
 # No output deletion: a pre-existing directory is refused.
 cmd='set -e; test ! -e '+shlex.quote(out)+'; '+shlex.join(['env','MEMG='+mem,'HIER=1','EXTRA='+','.join(extra),'WTOP='+w]+shlex.split(env)+['bash',R+'/synth_master.sh','.',out,cell,m,'-',bb,'--prefer',pref])+'; '+shlex.join(['env','MEMG='+mem,'bash','tools/hbm_die_v15/synth_etm.sh','.',out,cell])
 with (A/(cell+'.client.log')).open('w') as f:
  rc=subprocess.run(['/home/ubuntu/bin/ot-run','--mem',mem,'--threads','4','--dir',S,'--priority','die','--','bash','-c',cmd],stdout=f,stderr=subprocess.STDOUT).returncode
 rec={'cell':cell,'rc':rc,'output':out,'status':'PASS_SYNTH_AND_ETM' if rc==0 else 'FAIL_PRESERVED','row':x['row'],'extra':extra,'prefer':pref}
 (A/(cell+'.receipt.json')).write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True)
rows=[x for x in M['failed_only'] if x['cell'] not in ['ot_hgi_sfu_core_split3','ot_hbm_su_static_pgslice_lg__pv0']]
assert len(rows)==16
(A/'launched_manifest.json').write_text(json.dumps({'source':'6f783d0a1','overlay_sha256':M['helper_sha256'],'rows':rows,'reused':['ot_hgi_sfu_core_split3','ot_hbm_su_static_pgslice_lg__pv0'],'no_S3_or_GO':True,'original_live_preserved':M['preserve_live']},indent=2)+'\n')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(run,rows))
