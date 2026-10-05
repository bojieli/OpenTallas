#!/usr/bin/env python3
"""Resume the source-identical parent map after its OpenSTA delay API failure.

Use the project's retained-netlist resume method: skip exactly the completed
mapped-netlist make goal, protect that target with make -o, then run every
physical step. No source behavior or constraint value changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__)
 a.add_argument('--donor-root',type=Path,required=True)
 a.add_argument('--output-root',type=Path,required=True)
 args=a.parse_args();donor=args.donor_root.resolve();out=args.output_root.resolve()
 assert (donor/'supervisor.exit').read_text().strip()!='0'
 record=json.loads((donor/'physical.json').read_text())
 assert 'invalid command name "remove_input_delay"' in record['error']
 for source in record['design']['sources']:
  assert sha(ROOT/source['path'])==source['sha256'],source['path']
 boundary=ROOT/'physical/dsrom_v9_parent_context/boundary.sdc'
 original=(donor/'work/orfs/constraint.sdc').read_text()
 # The original driver removes comments from appended SDC commands.
 old=(donor.parent/'source-r2/physical/dsrom_v9_parent_context/boundary.sdc').read_text()
 def commands(text):
  return [' '.join(line.split()) for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
 assert commands(original)[-len(commands(old)):] == commands(old)
 assert boundary.read_text()==old.replace('remove_input_delay','unset_input_delay').replace('remove_output_delay','unset_output_delay')
 mapped_files=list((donor/'work/orfs/results').rglob('1_2_yosys.v'))
 assert len(mapped_files)==1
 original_mapped=mapped_files[0];rel=original_mapped.relative_to(donor/'work/orfs')
 work=out/'work';assert not work.exists()
 mapped=work/'orfs'/rel;mapped.parent.mkdir(parents=True)
 shutil.copy2(original_mapped,mapped)
 for p in original_mapped.parent.glob('1_1_yosys_canonicalize.rtlil'):shutil.copy2(p,mapped.parent/p.name)
 argv=record['runner']['argv'][1:]
 for option,value in [('--sdc-append',boundary),('--output',out/'physical.json'),('--keep-workdir',work)]:
  argv[argv.index(option)+1]=str(value)
 import run_abi3_physical as driver
 from run_abi3_physical_persistent import remove_inherited_runtime_caps
 limits=remove_inherited_runtime_caps()
 receipt=dict(schema='dsrom.v9.parent.retained-map-resume.v1',pid=os.getpid(),started_ns=time.time_ns(),
  donor_root=str(donor),donor_record_sha256=sha(donor/'physical.json'),mapped_netlist_sha256=sha(mapped),
  source_identical=True,hardware_sources=record['design']['sources'],changed_constraint_API_only=True,
  corrected_boundary_sha256=sha(boundary),runtime_limits=limits,subprocess_wall_timeout=None,synthesis_reused=False)
 def save():(out/'resume.json').write_text(json.dumps(receipt,indent=2)+'\n')
 save();original_run=driver.run;reused=0
 def run(command,**kwargs):
  nonlocal reused
  if (command[:3]==['docker','run','--rm'] and
      '/work/'+str(rel)+' && chmod a+w /work/'+str(rel) in command[-1]):
   assert reused==0 and sha(mapped)==receipt['mapped_netlist_sha256']
   reused=1;receipt['synthesis_reused']=True;save()
   return subprocess.CompletedProcess(command,0,stdout='REUSED_R2_MAPPED_NETLIST '+sha(mapped)+'\n',stderr='')
  if command[:3]==['docker','run','--rm'] and 'make DESIGN_CONFIG=/work/config.mk' in command[-1]:
   assert reused==1
   command=list(command);command[-1]=command[-1].replace('make DESIGN_CONFIG=/work/config.mk',
     'make -o /work/'+str(rel)+' DESIGN_CONFIG=/work/config.mk',1)
  kwargs['timeout']=None
  return original_run(command,**kwargs)
 driver.run=run;driver.flow_timeout_seconds=lambda:None;driver.synth_timeout_seconds=lambda:None
 try:
  rc=driver.main(argv);receipt['exit_code']=rc;assert reused==1;return rc
 finally:
  receipt.update(ended_ns=time.time_ns(),mapped_netlist_unchanged=sha(mapped)==receipt['mapped_netlist_sha256']);save()
if __name__=='__main__':raise SystemExit(main())
