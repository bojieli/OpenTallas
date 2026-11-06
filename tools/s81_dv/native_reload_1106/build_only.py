from pathlib import Path
import subprocess,json,os,time
R=Path(__file__).resolve().parent;V='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator';(R/'tmp').mkdir(exist_ok=True);env=dict(os.environ,TMPDIR=str(R/'tmp'),CCACHE_DISABLE='1',CCACHE_TEMPDIR=str(R/'tmp'))
def run(cmd,label,cwd=R):
 t=time.time()
 with (R/(label+'.log')).open('w') as f:p=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 (R/(label+'.rc')).write_text(str(p.returncode)+'\n');print(label,p.returncode,round(time.time()-t,2),flush=True);return p.returncode
cmd=[V,'--binary','--timing','--assert','-Wno-fatal','--top-module','tb','--output-groups','8','--output-split','10000','--output-split-cfuncs','1000','-CFLAGS','-O1 -fno-var-tracking','-Mdir',str(R/'obj'),'-j','4','-f',str(R/'sources.f')]
(R/'build_command.json').write_text(json.dumps(cmd,indent=2)+'\n');rc=run(cmd,'build')
if rc:raise SystemExit(rc)
