import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;read=lambda p:json.loads(p.read_text())
base=(P/'base.log').read_text();assert 'PDSK_REPAIR_PASS checks20 errors0 clock833'in base
assert 'BASE_RC=0\nOLD_ACTUAL_RC=1\nWRONG_SELECTOR_RC=1\nWRONG_DATE_RC=1\nGATE_PASS'in(P/'status.txt').read_text()
for name,fault,count in [('old_actual','01','21/5'),('wrong_selector','01','6/5'),('wrong_date','10','5/6')]:
 text=(P/(name+'.log')).read_text()
 for sid in (0,5):assert f'COLLECTOR_FAULT sid{sid} fault{fault} count{count}'in text
candidate=read(P.parent/'producer/repair_candidate.json');control=read(P.parent/'norm_control.json');routes=read(P.parent/'leaf_routes.json')
ctl=read(P.parent/'control_routes.json');bookings=[]
for sid in (0,5):
 old=sorted((c for c in control['commands']if c['kind']=='NORMR'and c['sid']==sid),key=lambda c:c['leaf'])
 changed=sorted((c for c in candidate['commands']if c['sid']==sid),key=lambda c:c['leaf'])
 physical=sorted((r for r in routes['leaves']if r['sid']==sid),key=lambda r:r['leaf'])
 profile=next(p for p in candidate['selector_changes']if p['sid']==sid)
 total=[c['issue']+116+r['xr_command_to_leaf_boundary_edges']+r['vn_b_partial_to_xr_input_edges']+profile['candidate_depths'][k]for k,(c,r)in enumerate(zip(changed,physical))]
 assert len(set(total))==1
 normalization=20-min(c['issue']for c in old)
 actual=[normalization+c['issue']+116+r['xr_command_to_leaf_boundary_edges']+r['vn_b_partial_to_xr_input_edges']for c,r in zip(old,physical)]
 assert actual==([147,142,159,161,175]if sid==0 else[147,142,161,163,175])
 bookings.append(dict(sid=sid,current_issuer_dates=[c['issue']for c in old],current_common_CTL_transport_edges=next(r['calendar_command_to_XR_command_edges']for r in ctl['paths']if r['sid']==sid),
  negative_component_normalization='omit common SID CTL transport and shift first issuer to20; preserve every actual per-leaf difference',
  negative_normalized_current_input_dates=actual,
  reference_legal_XR_input_dates=[100-d for d in profile['old_depths']],
  candidate_legal_XR_input_dates=[100-d for d in profile['candidate_depths']],
  candidate_actual_issuer_dates=[c['issue']for c in changed],candidate_partial_alignment_before_common_CTL=total[0],
  compare='same genuine FP32 partials,leaf0..4 output order,valid andindex; matched semantic input-set event100,firstoutput104'))
result=dict(schema='opentallas.s81.pdsk_current_consumer_repair_proof.v1',status='PASS_UNADOPTED_PARAMETER_SCHEDULE_MITER',
 clock_ps=833,actual_source_sha256={'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv':'59a53960b2c66851b14fbfcc615e451d380774ac483f2987a5f806abeb0cffa9','rtl/lib/ot_rst_relay.sv':'0071a3d067e72da7a450dd265aa8390b968f0228491ed2245fe8947b499264c5'},
 bench_sha256=hashlib.sha256((P/'tb_pdsk_repair.sv').read_bytes()).hexdigest(),
 actual_partial_producer_source='producer/partial.memh from actual current VP/VN80partial PASS,not checkpoint operation answers',
 actual_partial_file_sha256=hashlib.sha256((P.parent/'producer/partial.memh').read_bytes()).hexdigest(),
 bookings=bookings,scalar_output_checks=20,reference_and_candidate_faults='00',
 old_actual_calendar_control='bothSIDs fault01;21referencepackets vs5candidate',
 wrong_selector_control='bothSIDs fault01;6referencepackets vs5candidate',
 wrong_date_control='bothSIDs fault10;5referencepackets vs6candidate',
 model=dict(changed_existing_PDSK_fields=2,data_FF_delta=-64,valid_FF_delta=-2,total_FF_delta=-66,
 local_max_partial_path_delta_cycles=0,local_partial_set_to_first_XR_x_sv_edges=4,XR_output_partial_beats=5,
 note='path includes116currentproducer; source-only component bookings,globalGO/XFIN/RSTD/physicalSTART andaffectedphysicaltiming stillheld'),
 production_RTL_changed=False,source_adopted=False,plan_adopted=False,forced_GO=False,global_exchange_qualified=False,
 physical_START_qualified=False,physical_timing_qualified=False,full_token=False)
(P/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],result['scalar_output_checks'],'checks,threecontrols,−66FF,0localmaxdelta')
