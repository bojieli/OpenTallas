import sys,subprocess,json,hashlib
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/ref_gate/hv16_vm_cal_f20_ww-20261016-090750');sys.path.insert(0,str(r/'src/tools/closure_loop'));import ck_insertion as ck
b=next((r/'routes/gate/work/orfs/results/asap7').glob('*/base'));out=r/'native_cts_diag';out.mkdir(exist_ok=True)
manifest={'basis':'read-only original completed CTS with placement RC; diagnostic only, no routed native or CLOSED qualification','odb_sha256':hashlib.sha256((b/'4_1_cts.odb').read_bytes()).hexdigest(),'sdc_sha256':hashlib.sha256((b/'4_cts.sdc').read_bytes()).hexdigest()}
for c in ['tt','ff']:
 src,libs=ck.macro_libs(b,c);s=ck.tcl(c,'4_1_cts.odb','4_cts.sdc',False,'clk_tgt',libs,True)
 s=s.replace('puts "OT_CK [expr','puts "OT_CK_NAMED $cp [expr')
 pos=s.rfind('\nexit');s=s[:pos]+f'\nwrite_timing_model -library_name f20_cts_diag_{c} /out/f20_cts_diag_{c}.lib\nputs "F20_CTS_ETM_DONE {c}"\nexit\n'
 (out/(c+'.tcl')).write_text(s)
 cmd=['docker','run','--rm','-v',str(b)+':/base:ro','-v',str(src)+':/src:ro','-v',str(out)+':/out','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/out/'+c+'.tcl']
 with (out/(c+'.log')).open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 assert p.returncode==0,(c,p.returncode);assert ('F20_CTS_ETM_DONE '+c) in (out/(c+'.log')).read_text()
 print('F20_CTS_ETM_DONE',c,flush=True)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
