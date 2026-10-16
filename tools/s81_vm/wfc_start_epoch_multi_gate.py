#!/usr/bin/env python3
"""Three actual producer lifetimes in fixed serial slots; physical epoch UNBOUND."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from wfc_start_epoch_gate import FILES

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--bench',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 files=[a.source/f for f in FILES];pins={f:hashlib.sha256(p.read_bytes()).hexdigest()for f,p in zip(FILES,files)};pins['bench']=hashlib.sha256(a.bench.read_bytes()).hexdigest()
 r=subprocess.run(['iverilog','-g2012','-s','tb_wfc_epoch_multi','-o',str(a.out/'sim'),*map(str,files),str(a.bench)],capture_output=True,text=True);(a.out/'build.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError('compile')
 rows=[]
 for phase in range(8):
  for mode in range(3):
   r=subprocess.run(['vvp',str(a.out/'sim'),f'+PHASE={phase}',f'+MODE={mode}'],capture_output=True,text=True)
   (a.out/f'p{phase}_m{mode}.log').write_text(r.stdout+r.stderr)
   m=re.search(r'EPOCH_MULTI_RESULT (.*)',r.stdout)
   if r.returncode or not m:raise RuntimeError('actual multi-slot failure '+str((phase,mode)))
   rows.append(dict(phase=phase,mode=mode,result=m.group(1)))
 rec=dict(schema='opentallas.s81.offdefault-start-epoch-multislot.v1',source_sha256=pins,one_fixed_programme_start_phase=3,one_fixed_epoch=dict(FIRST_SLOT_S=148,PERIOD_S=60,SLOT_COUNT=3),source_f_vw_and_f_cs_core_edges='200+offset,280+offset,360+offset; middlemissing/late mutants explicit',fixed_t_ks_serial=[163,223,283],fixed_command_core=[261,341,421],fixed_KIT_serial=[204,264,324],context_sequence=[0,1,0],rows=rows,production_admissible=False,physical_common_epoch_bound=False,actual_compiler_parameter_producer='UNBOUND',native_physical_image=None,scope='realvmx_w/40generatedstationsemantics/c8PW36; logical ideal common reset; no mappedSRAM; PERIOD60 componentexample only, notnativeII')
 (a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('EPOCH_MULTI PASS',len(rows))
if __name__=='__main__':main()
