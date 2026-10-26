from pathlib import Path
import subprocess
w=Path(__file__).resolve().parent;v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
for mode,flags in [('pass',[]),('mut',['-DOT_S81ENG_REQ39_MUT_SECTOR'])]:
 with (w/('build_'+mode+'.log')).open('w')as f:subprocess.run([v,'--binary','--timing','-Wno-fatal','-j','8','--Mdir','obj_'+mode,'--top-module','tb']+flags+['old_tap.sv','new_tap.sv','ot_rst_relay.sv','ot_rst_relay_bounded32.sv','tb.sv'],cwd=w,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in [1,2,3]:
  p=subprocess.run([str(w/('obj_'+mode)/'Vtb'),'+seed='+str(seed)],cwd=w,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(w/(mode+'_'+str(seed)+'.log')).write_text(p.stdout);line=next(x for x in p.stdout.splitlines()if x.startswith('REQ39 '));print(line,flush=True)
  if mode=='pass' and ' PASS 'not in line:raise SystemExit(1)
  if mode=='mut' and ' FAIL 'not in line:raise SystemExit(2)
print('REQ39_QUALIFIED 3PCBASE x east/west x3seeds;wrongsectorprefixmutantCAUGHT',flush=True)
