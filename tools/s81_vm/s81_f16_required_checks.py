#!/usr/bin/env python3
"""Fresh effective helper and exact fixed-f16/native proof binding."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/closure_loop'));import helper_overlay as H
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--cl',type=Path);p.add_argument('--daemon',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if bool(a.cl)==bool(a.daemon):p.error('supply exactly one --cl or --daemon')
 kit=ROOT/'physical/ref_tile/dsfd_be_f16_m5';frozen=json.load(open(kit/'helper_overlay_plan.json'));plan=H.capture_plan(a.daemon,ROOT)[0] if a.daemon else json.load(open(a.cl/'helper_overlay_plan.json'));ok,why=H.compare_plans(frozen,plan)
 if not ok:raise SystemExit('HELPER_DRIFT '+why)
 assert len(plan['files'])==46
 proofs=[]
 for rel in ['results/arch/s81_fe_fault_relay_1014/waveform/record.json','results/arch/s81_fe_fault_relay_1014/native_intake/record.json']:
  proof=json.load(open(ROOT/rel))
  for s,v in proof['source_sha256'].items():assert sha(ROOT/s)==v,'PROOF_SOURCE_MISMATCH '+s
  assert all(c.get('ok',c.get('pass_',False)) for c in proof['cases'])
  proofs.append(rel)
 manifest=json.load(open(kit/'request.json'))
 for s,v in manifest['kit_sha256'].items():assert sha(ROOT/s)==v,'KIT_MISMATCH '+s
 for name in ['clock.sdc','signoff.sdc']:
  text=(kit/name).read_text();assert 'set_clock_groups' not in text,'UNEXPECTED_CLOCK_GROUP'
  for line in text.splitlines():
   if 'set_false_path' in line:assert line.strip()=='if {[llength [get_ports -quiet tile_id*]]} { set_false_path -from [get_ports tile_id*] }','UNEXPECTED_TIMING_EXCEPTION'
  assert 'tile_id' not in (ROOT/'rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv').read_text(),'INACTIVE_GUARD_BECAME_ACTIVE'
 if a.cl:
  for f in plan['files']:
   source=a.cl/Path(f['path']).name;assert sha(source)==f['sha256'];target=ROOT/f['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());target.chmod(f['mode'])
 record=dict(pass_=True,helpers=len(plan['files']),helper_content_sha256=plan['content_sha256'],proofs=proofs,N9_native_proof_pending=True,ordinary_synchronous_rn_timing=True,parent_source_clock_bound=False,new_reset_consumer_ACK=False,physical_adopted=False)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print('F16_REQUIRED_CHECKS_PASS',json.dumps(record))
if __name__=='__main__':main()
