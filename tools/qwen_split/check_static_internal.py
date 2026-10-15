#!/usr/bin/env python3
"""Lightweight actual-decoder/PW-calendar and native-route mechanism gates."""
from pathlib import Path
import subprocess,tempfile,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
D=Path('rtl/qwen_sys/static_schedule_20261014')
def run():
 out=ROOT/'results/rtl/qwen_q_export_1014/static_internal';out.mkdir(exist_ok=True,parents=True)
 src=['rtl/hdc/ot_hdc_dyn_ttiles.sv']+[str(D/f) for f in ['ot_qwen_rom_core_ctrl_static.sv','ot_qwen_fixed_issue.sv','ot_qwen_fixed_issue_pw.sv','tb_qfd_static_internal_issue.sv']]
 program=Path('results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/head_program_rank7.hex')
 program_bytes=subprocess.check_output(['git','show','origin/main:'+str(program)],cwd=ROOT)
 if hashlib.sha256(program_bytes).hexdigest()!='08c4c30c2c41cc3473280e33bf84dba3c0bca9180a21f233aad4682b5558a6a9':raise RuntimeError('source program changed; review pin')
 with tempfile.TemporaryDirectory(prefix='q_static_internal_') as tmp:
  program_local=Path(tmp)/'head_rank7.hex';program_local.write_bytes(program_bytes)
  exe=str(Path(tmp)/'sim')
  for name,params,success in [('actual_head',[],True),('unavailable_fault_timeline',['AVAIL_FALSE=1'],True),('row18_boundary',['ROW_HIGH=1'],True),('row18_mutant',['ROW_HIGH=1','MUT_DROP_ROW_HIGH=1'],False)]:
   cmd=['iverilog','-g2012','-s','tb_qfd_static_internal_issue','-o',exe]+['-Ptb_qfd_static_internal_issue.'+x for x in params]+src
   subprocess.run(cmd,cwd=ROOT,check=True);r=subprocess.run(['vvp',exe,'+PROGRAM='+str(program_local)],cwd=ROOT,capture_output=True,text=True)
   (out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)!=success:raise RuntimeError(name+': '+r.stdout+r.stderr)
  route=ROOT/D/'ot_qfd_native_cmd_route.sv';tb=str(D/'tb_qfd_native_cmd_route.sv')
  for name,mut in [('native_route',False),('native_route_mutant',True)]:
   p=Path(tmp)/'route.sv';s=route.read_text()
   if mut:s=s.replace("cmd[0]&&!cmd[55]", "cmd[0]")
   p.write_text(s);subprocess.run(['iverilog','-g2012','-s','tb_qfd_native_cmd_route','-o',exe,str(p),tb],cwd=ROOT,check=True)
   r=subprocess.run(['vvp',exe],cwd=ROOT,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)==mut:raise RuntimeError(name+': '+r.stdout+r.stderr)
 status={'scope':'Actual production decoder+PW FF issuer internal mechanism, explicit engine-response stimuli; not native end-to-end qualification','source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in src+[str(D/'ot_qfd_native_cmd_route.sv'),tb]},'program_source':str(program),'program_sha256':hashlib.sha256(program_bytes).hexdigest(),'fixed_issue_cycles':[40,60,80,100],'fixed_END_cycle':120,'clock_enable':'normal1; mem_ok0 leaves clocks unchanged','row18_boundary_variant':'Actual ISA bit898 set1 in four head ME words','remaining':['actual endpoint/status and parent composition','physical phase/reset/pin/cost qualification','real fullstage compiler calendar']}
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 print('PASS actual decoder/PW/internal numeric fold, availability fault timeline and native route; row18/route mutants observed FAIL')
if __name__=='__main__':run()
