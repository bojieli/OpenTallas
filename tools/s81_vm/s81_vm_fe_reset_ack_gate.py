#!/usr/bin/env python3
"""Minimum real-consumer reset ACK proof; run through ot-run, not a reset mirror."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import s81_vm_gate as V
SOURCES=[p for p in V.SRCS if p!='rtl/dsrom_sys/s81_ph/test/tb_dsfd_sp_vm.sv']+[V.FEH_SRC,'rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_fe_reset_ack.sv']
CASES={'default':[], 'ack':['OT_SPVM_RESET_ACK'], 'mut_no_witness':['OT_SPVM_RESET_ACK','OT_VMFE_MUT_ACK_NO_WITNESS'], 'mut_forward':['OT_SPVM_RESET_ACK','OT_VMFE_MUT_ACK_FORWARD']}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 binary,version=V.verilator_bin();assert binary,version
 results={}
 for name,defines in CASES.items():
  obj=a.out/('obj_'+name);cmd=[binary,'--binary','--timing','-O1','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-UNOPTFLAT','-j','8','--top-module','tb_dsfd_vm_fe_reset_ack','--Mdir',str(obj),'-I'+str(ROOT/'rtl/dsrom_sys/s81_ph/vm')]+['+define+'+d for d in defines]+[str(ROOT/s) for s in SOURCES]
  b=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(a.out/('build_'+name+'.log')).write_text(version+'\n'+' '.join(cmd)+'\n'+b.stdout+b.stderr)
  if b.returncode:print(name,'BUILD_FAIL',b.stderr[-2500:],flush=True);results[name]={'ok':False,'build_fail':True};continue
  r=subprocess.run([str(obj/'Vtb_dsfd_vm_fe_reset_ack')],capture_output=True,text=True,cwd=ROOT);log=r.stdout+r.stderr;(a.out/('run_'+name+'.log')).write_text(log)
  import re
  trace=re.search(r'NUM_TRACE (\w+)',log);passed=r.returncode==0 and '\nPASS\n' in log
  results[name]={'ok':passed if name in ['default','ack'] else not passed and 'ACK_BAD' in log,'exit':r.returncode,'passed':passed,'numerical_trace':trace[1] if trace else None,'log':str(a.out/('run_'+name+'.log'))};print(name,json.dumps(results[name]),flush=True)
 same=results.get('default',{}).get('numerical_trace')==results.get('ack',{}).get('numerical_trace') and results.get('ack',{}).get('passed',False)
 proof={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES+['rtl/dsrom_sys/s81_ph/vm/gen_dsfd_vm_fe_h.py','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_reset_ack.svh']},'cases':results,'default_numerical_trace_matches_ack':same,'ok':same and all(c['ok'] for c in results.values()),'scope':'Five actual consumers CLT/FSR/FCN/FCC/FCW and their real adapter/FIFO states; no BE/top parent source-driver or physical qualification.'}
 (a.out/'proof.json').write_text(json.dumps(proof,indent=1)+'\n');sys.exit(0 if proof['ok'] else 1)
if __name__=='__main__':main()
