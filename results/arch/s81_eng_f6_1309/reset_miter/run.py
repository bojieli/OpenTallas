from pathlib import Path
import os,subprocess
r=Path('/srv/opentallas-scratch2/claude/codex-s81-eng-1309/reset_miter');r.mkdir(parents=True,exist_ok=True);src=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-eng-1309/rtl/dsrom_sys/s81_dv/eng/ot_s81eng_reset3n32.sv').read_text();(r/'src.sv').write_text(src);(r/'mut.sv').write_text(src.replace('q<=mid[l/32];','q<=root_d;'))
env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
for mode,f in [('pass','src.sv'),('mut','mut.sv')]:
 with (r/('build_'+mode+'.log')).open('w') as out:subprocess.run(['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','-j','1','--Mdir','obj_'+mode,'-DOT_S81ENG_RST_TIMED',f,'tb.sv'],cwd=r,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
 p=subprocess.run([str(r/('obj_'+mode)/'Vtb')],cwd=r,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(r/(mode+'.log')).write_text(p.stdout)
 if ('RESET_TIMED PASS' not in p.stdout)if mode=='pass' else('RESET_TIMED FAIL' not in p.stdout):print(p.stdout);raise SystemExit(1)
print('PASS 3-edge assertion/release and wrong-depth mutant caught')
