from pathlib import Path
import subprocess,json,os
W=Path('/srv/opentallas-scratch2/claude/codex-ds-pma-peer-1106');V=str(W/'install/bin/verilator');(W/'tmp').mkdir(exist_ok=True);env=dict(os.environ,TMPDIR=str(W/'tmp'),CCACHE_DISABLE='1',CCACHE_TEMPDIR=str(W/'tmp'));rows=[]
for label,bad in [('wire_correct',0),('wire_oldprofile',1)]:
 cmd=[V,'--binary','--timing','--assert','--x-assign','fast','--x-initial','fast','-Wno-fatal','--top-module','tb','-GBAD='+str(bad),'-Mdir',str(W/(label+'_a2')),'-j','1','-f',str(W/'sources_a2.f')]
 with (W/(label+'.a2.build.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT)
 (W/(label+'.a2.build.rc')).write_text(str(q.returncode)+'\n')
 if q.returncode:print('BUILD_FAIL',label,flush=True);raise SystemExit(q.returncode)
 with (W/(label+'.a2.run.log')).open('w') as f:q=subprocess.run([str(W/(label+'_a2')/'Vtb')],cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT)
 s=(W/(label+'.a2.run.log')).read_text();ok=(q.returncode==0 and 'PMA_HOST_PASS words514=12 valid_andKS53_exact=1' in s) if bad==0 else (q.returncode!=0 and 'PMA_HOST_PASS' not in s)
 row=dict(label=label,BAD=bad,rc=q.returncode,correct=ok,diagnosis=next((x for x in s.splitlines() if 'PMA_HOST_PASS' in x or '%Error' in x or '%Fatal' in x),''));rows.append(row);(W/'result_a2.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
 if not ok:raise SystemExit(2)
