#!/usr/bin/env python3
"""Collect actual immutable embedding stage; link cached RTL only if needed.

This driver supplies no DUT operands/results. The SV bench loads the released
HBM-boundary records, programs actual SRAMs and checks mapped VM storage.
"""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def run(cmd, log, cwd):
 with log.open('w') as f:r=subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
 return r.returncode

def collect(source,build,vectors,out,helper_root):
 out.mkdir(exist_ok=False)
 pins={}
 for line in (build/'source.sha256').read_text().splitlines():
  expected,name=line.split(maxsplit=1);p=Path(name);p=p if p.is_absolute() else source/p
  assert sha(p)==expected,'frozen source/input differs: '+str(p)
  pins[str(p)]=expected
 archives=sorted((build/'obj').rglob('*.a'))
 assert archives and (build/'obj/Vtb_qwen_embedding_stage__ALL.a').is_file(),'unfinished RTL archives'
 archive_pins={str(p):sha(p) for p in archives}
 exe=build/'obj/Vtb_qwen_embedding_stage'
 link_exit=None
 if not exe.is_file():
  inc=Path('/usr/share/verilator/include')
  cmd=['g++','-std=c++20','-O2','-I'+str(build/'obj'),'-I'+str(inc),'-I'+str(inc/'vltstd'),source/'tools/qwen_split/embedding_stage_main.cpp',inc/'verilated.cpp',inc/'verilated_timing.cpp',inc/'verilated_threads.cpp','-Wl,--start-group']+[p for p in archives if p.name!='libverilated.a']+['-Wl,--end-group','-pthread','-latomic','-o',out/'embedding_stage']
  link_exit=run(cmd,out/'cached_link.log',source)
  assert link_exit==0,'cached RTL link failed'
  exe=out/'embedding_stage'
 args=[exe,'+VECTORS='+str(vectors),'+IMAGE='+str(build/'image')]
 runs=[]
 for name,extra in [('positive',[]),('missing_beat_mutant',['+MUT=1'])]:
  old=build/(name+'.log');log=out/(name+'.log')
  if old.is_file():log.write_bytes(old.read_bytes());rc=None
  else:rc=run(args+extra,log,source)
  t=log.read_text();ok='PASS actual source embedding stage token151935 129beats realTT/SU fixedEND realFP64 VMmacros4096 cells checked no fixturecompletion' in t
  if name=='positive':assert ok and (rc is None or rc==0),t[-3000:]
  else:assert not ok and 'actual embedding region faults' in t and (rc is None or rc!=0),'mutant must fail actual integrity check, not launch/compiler failure: '+t[-3000:]
  runs.append(dict(name=name,exit=rc,exit_source='inherited log only' if rc is None else 'direct subprocess',log_sha256=sha(log)))
 helper=helper_root/'tools/qwen_split/embedding_stage_reduction_readback.py'
 assert run(['python3',helper,build,vectors],out/'scalar_bind.log',helper_root)==0,'scalar observer bind failed'
 rx=build/'obj/Vtb_qwen_embedding_stage_readback'
 rc=run([rx]+args[1:],out/'scalar_readback.log',source)
 text=(out/'scalar_readback.log').read_text()
 assert rc==0 and 'PASS actual mapped SRAM RMS scalar14240=' in text,text[-3000:]
 contract=json.loads((build/'image/contract.json').read_text())
 ledger=[]
 for row in contract['operation_binding']:
  ledger.append(dict(**row,status='component runtime verified; physical profile absent',arithmetic='RTL INT8/BF16 decode, FP32 vector arithmetic and canonical chunked RMS reduction' if row['pc']==0 else 'fixed compiler END; no arithmetic',operand_storage='actual mapped64x512 embedding codes+registered BF16 scale' if row['pc']==0 else None,result_storage='actual NOX VM SRAM;4096 vectorcells + scalar14240 observed' if row['pc']==0 else None))
 record=dict(scope='actual two-instruction embedding region only',full_native_token=False,physical_qualified=False,source_sha256=pins,archives_sha256=archive_pins,binary_sha256=sha(exe),readback_binary_sha256=sha(rx),cached_link_exit=link_exit,runs=runs,scalar_readback_exit=rc,operation_ledger=ledger,calendar=contract['fixed_test_slots'],unqualified=['physical C17 clocks/routes/phase/profile','all other layer operations and full token','external HBM producer is component-boundary retained records'])
 (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
 print('PASS_COLLECT_ACTUAL_EMBEDDING_STAGE_VECTOR_AND_RMS_SRAM_NOT_FULL_NATIVE_TOKEN')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ('source','build','vectors','out','helper-root'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();collect(a.source.resolve(),a.build.resolve(),a.vectors.resolve(),a.out.resolve(),a.helper_root.resolve())
