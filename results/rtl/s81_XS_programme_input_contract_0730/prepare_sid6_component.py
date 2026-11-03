#!/usr/bin/env python3
"""Materialize exact existing SID6 component images under its actual native selector; never install a mission."""
from pathlib import Path
import argparse,subprocess,json,hashlib
REV='9db068b5458b7a20a548ab165aabc8dc6c077a30'
BASE='results/rtl/s81_qf_producer_1019/sid6_vehicle/'
SELECTOR='u_s_3S.u_sl.u_xg'
KEYS=['pq_calendar_action','pq_calendar_time','pq_phase0','pq_stream0','pq_stream1','pq_stream2','pq_stream3']
def raw(p):return subprocess.check_output(['git','show',REV+':'+p])
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('fresh component directory required')
 contract=json.loads(raw(BASE+'retained_xs_program_model/contract.json'));measured=json.loads(raw(BASE+'retained_xs_result/result.json'))
 assert contract['actual_frames']==6 and contract['actual_phases']==15 and contract['semantic_rows']==512
 assert measured['actual_epochs']==15 and measured['gathers']==20 and measured['actual_read_requests']==360
 assert contract['reservation']['XS_parity']==0 and contract['source_window_open_count']==1
 # Actual current bound selector join is supplied by the coherent source event, not inferred from this fixture.
 here=Path(__file__).resolve().parent;join=json.loads((here.parent/'s81_token_source_event_0715/XS_selector_contract.json').read_text());row=next(x for x in join['selectors']if x['path']==SELECTOR)
 assert row['module']=='ot_s81sl_xg'and row['capture_added_edges']==0
 material=[]
 for k in KEYS:
  src=BASE+'retained_xs_program_model/'+k+'.viamap.hex';b=raw(src)
  assert len(b.splitlines())==512
  material.append((SELECTOR+'.'+k+'.viamap.hex',b,src))
 a.out.mkdir(parents=True)
 for n,b,_ in material:(a.out/n).write_bytes(b)
 (a.out/'source_ctl.txt').write_bytes(raw(BASE+'retained_xs_program_model/source_ctl.txt'))
 d=dict(status='INACTIVE_EXACT_EXISTING_SID6_COMPONENT_IMAGE_CANDIDATE',selector=SELECTOR,sid=6,actual_module='ot_s81sl_xg -> ot_s81sl_xs',capture_added_edges=0,source_revision=REV,source_contract=BASE+'retained_xs_program_model/contract.json',native_receipt=BASE+'retained_xs_result/result.json',existing_native_job=3731309,source_clock_ps=834,clock_note='Original native harness #417 halfperiod; no new833ps or physical-clock measurement',actual_frames=6,actual_phases=15,private_period_edges=600,family=0,parity=0,genuine_component_images=7,qualified_mission_images=0,upstream_current_native_xrt_qualified=False,mission_epoch_qualified=False,physical_sampling_qualified=False,full_token=False,default_or_cohort_changed=False,source_compatibility='b12d983ca native-gated legacy optional INSTANCE affects only simulation filenames, default source pipeline unchanged',images=[dict(source=p,file=n,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))for n,b,p in material])
 (a.out/'component_images.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
if __name__=='__main__':main()
