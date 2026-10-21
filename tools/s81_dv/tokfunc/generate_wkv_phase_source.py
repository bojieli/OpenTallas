#!/usr/bin/env python3
"""Generate ONE explicit24row real-wkv MAT/nativeCAP source phase; never compile."""
import argparse,hashlib,json,subprocess,tarfile
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['compiler-root','profile-archive','profile-receipt','baseline-frame-model','die-v','plan','audit','port-bind','tap-consumer','address-readset','fixtures','producer','inventory','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in vars(a):setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(exist_ok=False);rec={'status':'SOURCE_INPUT_STAGING','simulation_performed':False,'compiler_run':False,'out':str(a.out),'inputs':{n:dict(path=str(v),sha256=sha(v)) for n,v in vars(a).items() if v.is_file()},'steps':[]}
 def save():(a.out/'receipt.json').write_text(json.dumps(rec,indent=1)+'\n')
 save();profile=json.loads(a.profile_receipt.read_text());kit=a.out/'component_basis';kit.mkdir()
 with tarfile.open(a.profile_archive) as t:
  members=[m for m in t if m.isfile()]
  assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
  assert {m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in members}==profile['staged_files_sha256']
  t.extractall(kit,members=members)
 files=[dict(path=n[4:],sha256=h,origin='EXACT_RETAINED191_SIXDEFINE_COMPONENT_SOURCE') for n,h in profile['staged_files_sha256'].items() if n.startswith('src/') and not n.startswith('src/top/')];assert len(files)==191
 (kit/'kit.json').write_text(json.dumps(dict(files=files,problems=[],defines=profile['defines'],qualification='Historical191sixdefine source-body basis only; prospectiveactualG9target sevenconfig recorded separately; no new compile'),indent=1)+'\n')
 schedule=a.out/'frame_schedule';schedule.mkdir()
 def run(label,argv):
  log=a.out/(label+'.log')
  with log.open('w') as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
  rec['steps'].append(dict(label=label,argv=argv,exit_code=r.returncode,rawlog_sha256=sha(log)));save()
  if r.returncode:rec['status']='SOURCE_GENERATION_FAIL';save();raise SystemExit(r.returncode)
 tool=a.compiler_root/'tools/s81_dv/tokfunc'
 run('frame_model',['python3',str(tool/'selected_frame_schedule.py'),'--kit',str(kit),'--compiler-root',str(a.compiler_root),'--baseline',str(a.baseline_frame_model),'--out',str(schedule/'col_h9_schedule.json')])
 argv=['python3',str(tool/'stage_aggregate_programme.py'),'--inventory',str(a.inventory),'--die-v',str(a.die_v),'--plan',str(a.plan),'--fixtures',str(a.fixtures),'--frame-schedule',str(schedule),'--functional-kit',str(kit),'--configured-receipt',str(a.profile_receipt),'--configured-source-root',str(kit/'src'),'--actual-source-audit',str(a.audit),'--actual-port-bind',str(a.port_bind),'--actual-tap-consumer',str(a.tap_consumer),'--actual-address-readset',str(a.address_readset),'--producer-receipt',str(a.producer),'--rank-rows','320:344','--tensor','wkv','--out',str(a.out/'assets')]
 run('wkv_assets',argv)
 rec.update(status='SOURCE_ASSETS_GENERATED_UNEXECUTED',actual_captured_KV_rows=0,rank_required_rows=128,global_required_rows=512,source_assets_sha256=sha(a.out/'assets/assets.json'),configured_profile_hold='ActualG9seven prospective target; prior191six syntax receipt independent; full current selected0Nsource/clock/order preflight pending')
 save();print(rec['status'])
if __name__=='__main__':main()
