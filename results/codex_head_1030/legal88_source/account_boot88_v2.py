#!/usr/bin/env python3
"""Conservative boot accounting; actual ready/fault/host events still control mission admission."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);raw=json.loads((p/'source_plan.json').read_text());s=json.loads((p/'source_sidecar.json').read_text());st=json.loads((p/'start_stages_src25q.json').read_text());rr=json.loads((p/'root88_report.json').read_text())
ca=s['count_aligned'];c=s['collector'];types=raw['partition_types'];root=next(x for x in st['stages'] if x['root']);base=root['reset_source']['raw_release']+root['settle']+1
# A falling-edge sampler is conservatively charged a complete cycle; no phase qualification inferred.
regdelay={};visiting=set()
def delay(n):
 if n in regdelay:return regdelay[n]
 assert n not in visiting;visiting.add(n);r=ca['regions'][n]
 v=0 if r['parent'] is None else delay(r['parent'])+3+int(r['pad'])+int(r['edge_fall'])
 regdelay[n]=v;visiting.remove(n);return v
for n in ca['regions']:delay(n)
start={pn:base+delay(v['region'])+int(v.get('stages',0)) for pn,v in ca['parts'].items()}
rw={};depths={};loc={};agg={}
for tn,t in types.items():
 ck=t.get('clock',{});z=lambda k:int(ck.get(k,{}).get('depth',0))
 rw[tn]=max(z('landing_reader_start'),z('landing_writer_start'))
 inf=c['types'].get(tn,{});sd=ck.get('landing_status_input_stages',{})
 extra=lambda target:max((len(v) for v in sd.get(target,{}).values()),default=0)
 ls=inf.get('local_status_depth',1);ls=max(ls.values(),default=1) if isinstance(ls,dict) else ls
 depths[tn]=dict(aggregate=int(inf.get('local_registered_depth',0))+extra('agg'),local=int(ls)+max([extra(k) for k in sd if k!='agg']or[0]))
# D8 strap TIMEOUT is171; charging it covers every legal static strap before eitherready or stickyfault.
train=171
localboot={pn:max(rr['all_part_raw_release_max'],start.get(pn,base))+rw[v['type']]+train for pn,v in c['parts'].items()}
for pn,v in c['parts'].items():loc[pn]=localboot[pn]+depths[v['type']]['local']
incoming={pn:[] for pn in c['parts']}
for e in c['edges']:incoming[e['dst']].append(e)
active=set()
def status(pn):
 if pn in agg:return agg[pn]
 assert pn not in active,pn;active.add(pn);t=c['parts'][pn]['type'];a=[localboot[pn]]
 for e in incoming[pn]:
  src=status(e['src']) if e['carries']=='aggregate' else loc[e['src']]
  # Legacy status seam3 is increased to full strap timeout; coversready transition through a CA seam.
  a.append(src+(train if e.get('seam') else int(e['boot_transport_extra_cycles'])))
 agg[pn]=max(a)+depths[t]['aggregate'];active.remove(pn);return agg[pn]
ready=status(c['observer']['part'])+1
report=dict(schema='HEAD_ROOT88_BOOT_ACCOUNT_1',root_settle_cycles=88,previous_settle_cycles=74,delta_boot_cycles=14,added_steady_cycles=0,root_raw_release_cycle=root['reset_source']['raw_release'],root_start_upper_cycle=base,raw_relative_span=rr['raw_relative_span'],raw_guard_cycles=4,all_part_raw_release_max_cycles=rr['all_part_raw_release_max'],start_transport_max_cycles=max(regdelay.values()),part_start_max_cycle=max(start.values()),local_reset_start_stage_max=max(rw.values()),strap_ready_or_fault_timeout_cycles=train,status_ready_or_fault_at_glue_upper_cycle=ready,observer_capture_cycles=1,per_type_start_stages=rw,per_type_status_depths=depths,mission_admission='actual registered root ready && !actual sticky fault && actual host boot_done; a numeric bound never asserts mission',cold_and_warm='same accounting after each asserted reset; all START/CA/statusstate must reset; 84-edge ROOT88 coupon coverscold1/warm3',physical_clock_phase_qualified=False,actual_external_host_event_cycle=None,actual_physical_full_array_boot_receipt=None,qualification='conditional generated START/CA/status-network bound only, assuming its declared continuously running clock contracts and proven CA windows/static straps; timeout establishes ready OR fault. Native PMA/PHY producer readiness, unqualified periods/phases, external host events and full-array mission readiness are excluded.')
c['start_contract']='START follows qualified primary raw-driver release span plus4guard; CA/status training follows START. Mission requires actual registered root ready && !stickyfault && actual native host boot_done; no numeric budget asserts mission.'
c['boot_budget']=dict(scope='generated START/CA/status network PREP only',root_settle_cycles=88,delta_boot_cycles=14,
 raw_reset_release_max_cycles=rr['all_part_raw_release_max'],root_start_upper_cycle=base,
 part_start_max_cycle=max(start.values()),ring_ready_or_fault_timeout_cycles=train,
 control_ready_or_fault_upper_cycle=ready,observer_input_capture_cycles=1,
 native_pma_phy_ready_cycle=None,actual_external_host_event_cycle=None,actual_mission_cycle=None,
 data_cycles_added=0,physical_clock_phase_qualified=False,
 contract=report['qualification'],mission_admission=report['mission_admission'])
(p/'source_sidecar.json').write_text(json.dumps(s,indent=1)+'\n')
(p/'boot88_account.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
