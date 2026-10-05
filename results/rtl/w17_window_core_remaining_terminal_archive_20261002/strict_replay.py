#!/usr/bin/env python3
"""Additional per-process checks over the portable archived evidence, never executes RTL."""
import argparse,json,hashlib,importlib.util,sys
sys.dont_write_bytecode=True
from pathlib import Path

def verify(archive):
 archive=Path(archive);spec=importlib.util.spec_from_file_location('portable_recovery_receipts',archive/'replay.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 result=r.verify(archive);details=[]
 for name in ('first','remaining'):
  p=r.load(archive/'plans'/f'{name}.json');record=r.load(archive/'runs'/name/'record.json');context=r.load(archive/'context.json')['runs'][name]
  expected_steps=[]
  for job in p['jobs']:
   home=archive/'runs'/name/job['label']
   for kind in ('frontend','CXX'):
    command=[x.format(out=context['original_output']) for x in job[kind+'_command']]
    expected_steps.append((job['label'],kind,command))
   expected_steps.append((job['label'],'runtime_0',[str(Path(context['original_output'])/job['label']/'obj/Vtb')]+job['cases'][0]['args']))
  r.need(len(record['steps'])==len(expected_steps),'all actual compile/runtime steps')
  compile_seconds=runtime_seconds=0
  for step,(label,kind,command) in zip(record['steps'],expected_steps):
   r.need(step['command']==command,'exact actual command '+label+'/'+kind)
   path=archive/'runs'/name/label/(kind+'.log');r.need(r.sha(path)==step['log_sha256'],'actual process log SHA')
   r.need(step['returncode']==(1 if kind.startswith('runtime') else 0),'actual process exit')
   if kind.startswith('runtime'):runtime_seconds+=step['wall_seconds']
   else:compile_seconds+=step['wall_seconds']
   details.append({'run':name,'phase':label,'stage':kind,'exit':step['returncode'],'seconds':step['wall_seconds'],'log_sha256':step['log_sha256']})
  r.need(abs(compile_seconds-record['compile_shared_wall_seconds'])<1e-6 and compile_seconds<=p['budget']['compile_shared_seconds'],'aggregate actual compile accounting')
  r.need(abs(runtime_seconds-record['runtime_shared_wall_seconds'])<1e-6 and runtime_seconds<=p['budget']['runtime_shared_seconds'],'aggregate runtime accounting')
  for job in p['jobs']:
   steps=[s for s,(label,kind,command) in zip(record['steps'],expected_steps) if label==job['label']]
   r.need(steps[0]['wall_seconds']<=p['budget']['frontend_phase_seconds'] and sum(s['wall_seconds'] for s in steps[:2])<=p['budget']['phase_compile_seconds'],'phase compile time cap')
   r.need(steps[2]['wall_seconds']<=job['cases'][0]['seconds'],'case runtime cap')
 result['strict_actual_processes']=details;result['actual_compilation_commands_and_accounting']='PASS';return result
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--archive',default=str(Path(__file__).resolve().parent/'archive'));a=ap.parse_args();print(json.dumps(verify(a.archive),indent=2))
