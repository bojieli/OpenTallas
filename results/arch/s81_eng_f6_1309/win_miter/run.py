from pathlib import Path
import subprocess,os,re,shutil
r=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-eng-1309');o=Path('/srv/opentallas-scratch2/claude/codex-s81-eng-1309/win_miter');o.mkdir(parents=True,exist_ok=True)
path='rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv'
old=subprocess.check_output(['git','-C',str(r),'show','88ec67b9f3:'+path],text=True)
mods=re.findall(r'\bmodule\s+(\w+)',old);old=re.sub(r'\b('+'|'.join(mods)+r')\b',lambda m:m.group(1)+'_ref',old)
(o/'ref.sv').write_text(old);(o/'new.sv').write_bytes((r/path).read_bytes())
base=Path('/srv/opentallas-scratch2/claude/codex-s81-eng-1309/miter/build_xq_pass/sh')
for f in ['ot_rom_4096x72_m8.v','ot_sram_1r1w_512x128_m4_r2c2.v']:shutil.copy2(base/f,o/f)
env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
for mode,flags in [('pass',[]),('mut',['-DOT_S81ENG_MUT_HIST_FORWARD'])]:
 with (o/('build_'+mode+'.log')).open('w') as f:subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','8','--Mdir','obj_'+mode,'--top-module','tb','-DSYNTHESIS','-DOT_S81ENG_TMAP_CPRE','-DOT_S81ENG_MACRO_F6']+flags+['ref.sv','new.sv','tb.sv','ot_rom_4096x72_m8.v','ot_sram_1r1w_512x128_m4_r2c2.v'],cwd=o,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in [1,2,3]:
  q=subprocess.run([str(o/('obj_'+mode)/'Vtb'),'+seed='+str(seed)],cwd=o,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(o/(mode+'_'+str(seed)+'.log')).write_text(q.stdout)
  ok=('WIN_MITER PASS' in q.stdout)if mode=='pass' else('WIN_MITER FAIL' in q.stdout and 'WIN_DIFF' in q.stdout)
  if not ok:print(q.stdout);raise SystemExit(1)
print('PASS Win +1readstage ALLoutputs3seeds, noforwardmutantCAUGHT')
