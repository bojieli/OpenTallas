#!/usr/bin/env python3
"""Bind exact Gray CDC proof, explicit leaf ABI, and fresh effective helper bytes."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/closure_loop'))
import helper_overlay as HO
import submit_lint as SL
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--daemon',type=Path);ap.add_argument('--cl',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 assert bool(a.daemon)!=bool(a.cl),'one helper origin required'
 kit=ROOT/'physical/s81_be_gray_m7_candidate'; req=json.loads((kit/'request.json').read_text()); proof=json.loads((kit/'exact_gate_binding.json').read_text())
 for rel,h in req['kit_sha256'].items():assert sha(ROOT/rel)==h,rel
 for rel,h in proof['source_sha256'].items():assert sha(ROOT/rel)==h,rel
 assert {x['case'] for x in proof['cases']}=={'default_gold','default_tp','gray_gold','gray_tp','gray_wrong_entry'}
 assert all(x['gate']['ok'] for x in proof['cases'])
 assert proof['wrong_entry_numerical_mismatches']==3017
 text=subprocess.check_output(['verilator','-E','-DOT_BE_RCDC_GRAY',str(ROOT/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv')],text=True,cwd=ROOT)
 text=re.sub(r'^`line.*$', '',text,flags=re.M)
 bits=set(SL.bit_names(SL.top_ports(text,'dsfd_vm_be_sl')))
 contacts=json.loads((kit/'ports.json').read_text()); assigned={x[0] for g in contacts['ports'].values() for x in g['pins']}
 assert bits==assigned,dict(missing=sorted(bits-assigned),extra=sorted(assigned-bits))
 assert len(bits)==4099
 frozen=json.loads((kit/'helper_overlay_plan.json').read_text()); effective=HO.capture_plan(a.daemon,ROOT)[0] if a.daemon else json.loads((a.cl/'helper_overlay_plan.json').read_text())
 ok,why=HO.compare_plans(frozen,effective);assert ok,why
 assert len(effective['files'])==46
 if a.cl:
  for f in effective['files']:
   source=a.cl/Path(f['path']).name;assert sha(source)==f['sha256']; target=ROOT/f['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());target.chmod(f['mode'])
 record=dict(schema='opentallas.be_gray_required_checks.v1',checks_pass=True,exact_source_bound=True,proof_rerun=False,helper_count=46,helper_content_sha256=effective['content_sha256'],preprocessed_actual_top_contacts=len(bits),default_off_define='OT_BE_RCDC_GRAY',old_CLOSED_replaced=False,physical_qualified=False,source_slot_allocated=False,global_clock_reset_bound=False)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print('BE_GRAY_REQUIRED_CHECKS_PASS')
if __name__=='__main__':main()
