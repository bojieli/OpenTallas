#!/usr/bin/env python3
"""Source admission/alias-lease lower bounds; bank idle is never a read fence.
Model-only required opt-in guard, not native callback or trace qualification.
"""
import argparse,gzip,hashlib,json,math
from pathlib import Path
import dsrom_capture_home_r49 as H
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_consumer_admission_20261003'
def inputs():
 out={}
 for r in json.loads((BASE/'inputs/origins.json').read_text()):
  raw=(BASE/'inputs'/r['copy']).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=r['copy_sha256']:raise ValueError('Source input drift')
  out[r['copy']]=gzip.decompress(raw).decode()
 return out

def census(nodes):
 layer=sorted((n for n in nodes if n.get('scope')==0 and n.get('kind')=='instruction'),key=lambda n:n['instruction_index'])
 matrix=[n for n in layer if 66<=n['instruction_index']<=100 and n['instruction'].get('unit')==3]
 producers=[]
 for n in matrix:
  i=n['instruction'];pc=n['instruction_index'];labels=set(i['_writes']);first=next((c for c in layer if c['instruction_index']>pc and labels.intersection(c['instruction'].get('_reads',[]))),None)
  if first is None:raise ValueError('Missing first-use descriptor')
  count=i['qe_nout'];base=i['qe_obase']
  if base<0 or base+count>1<<19:raise ValueError('VM19 range')
  producers.append(dict(producer_pc=pc,label=i['_writes'][0],base=base,words=count,end_exclusive=base+count,first_consumer_pc=first['instruction_index'],consumer_unit=first['instruction']['unit'],wait=first['instruction'].get('wait',0),capture_W1_W3=count==576))
 live=[];peak=0;trace=[]
 # Optimistic release at FIRST consumer descriptor, before any real read/tag
 # tail: lower bound only. Real accepted order/stalls may require more slots.
 for n in layer:
  pc=n['instruction_index'];live=[p for p in live if p['first_consumer_pc']>pc]
  live.extend(p for p in producers if p['producer_pc']==pc)
  peak=max(peak,len(live));trace.append(dict(pc=pc,live_producer_pcs=[p['producer_pc'] for p in live],frames=len(live),capture_frames=sum(p['capture_W1_W3'] for p in live)))
 captured=[p for p in producers if p['capture_W1_W3']]
 if len(captured)!=12:raise ValueError('Expected twelve W1/W3 frames')
 for p in captured:
  c=next(n['instruction'] for n in layer if n['instruction_index']==p['first_consumer_pc'])
  if p['base'] not in (c.get('a_base'),c.get('c_base')) or c.get('su_nin')!=576:raise ValueError('A/C first-read range mismatch')
 return dict(producers=producers,optimistic_first_descriptor_release_trace=trace,all_matrix_frames_lower_bound=peak,capture_frames_lower_bound=max(t['capture_frames'] for t in trace),exact_peak_accepted_read_and_Rplus2_tail=None)

def consumer_guard(versions,requests,actual_identity_bound):
 # Required new predicate before accepted SUgo, using named full versions.
 # No bank idle, producer idle or guessed calendar edge is an input.
 if not actual_identity_bound:return False
 for request in requests:
  key=request['producer_pc'];v=versions.get(key)
  if v is None or not v['same_identity'] or not v['VMvisible'] or not v['VMversion_lease_live']:return False
  if request['src']!=0 or not 0<=request['address']<1<<19 or not v['base']<=request['address']<v['end_exclusive']:return False
 return bool(requests)

def guarded_native_accept_lower(native_lower,visibility_edges):
 # A visible NBA update cannot finance an admission at that same edge.
 # Core sees prior registered visibility then emits su_go NBA; unit accepts
 # next edge. +2 is an ordering lower bound, not qualified guard delay.
 if native_lower is None or not visibility_edges or any(v is None for v in visibility_edges):raise ValueError('No zero missing provider/origin')
 return max(native_lower,max(visibility_edges)+2)

def build():
 d=inputs();core=d['core.sv.gz'];adapter=d['adapter.sv.gz'];lane=d['lane.sv.gz']
 for text in ['wire [4:0] idles = {he_idle, xu_idle, qe_idle, su_idle, me_idle};','wire waited = ((d_wait & ~(idles & ~gos)) == 5\'d0);','S_GO: begin pc <= pc + 1\'b1; st <= S_FETCH; end']:
  if text not in core:raise ValueError('Source admission sequence changed')
 if 'assign ready = st == S_IDLE && s_ready;' not in adapter or 'S_WAIT: if (!s_go && s_idle) st <= S_IDLE;' not in adapter:raise ValueError('Native phase retirement changed')
 if 'm_v <= mr_v; x_v <= m_v;' not in lane:raise ValueError('Read tag sequence changed')
 c=census(json.loads(d['program.json.gz'])['nodes']);captured=[p for p in c['producers'] if p['capture_W1_W3']]
 fields={'producer_context':169,'VM_base':19,'VM_end_exclusive':20,'lease_valid':1};bits=sum(fields.values())
 hd,_=H.H.inputs();f=hd['capture.json']['source_cell_facts'];tie=hd['capture.json']['SETN_TIEHI_LEF_area_um2']/1483
 def floor(entries):
  n=bits*entries;tree=[];k=n
  while k>1:k=math.ceil(k/8);tree.append(k)
  counts={'DFFASRHQNx1_ASAP7_75t_R':n,'INVx1_ASAP7_75t_R':n,'NAND2x1_ASAP7_75t_R':3*n,'BUFx4_ASAP7_75t_R':2*n+2*sum(tree),'TIEHIx1_ASAP7_75t_R':n}
  body=sum(count*(tie if master.startswith('TIEHI') else f[master]['SS']['area_um2']) for master,count in counts.items())
  return dict(entries_lower_bound=entries,metadata_FF=n,counts=counts,metadata_body_um2=body,metadata_50pct_floor_mm2=body*2/1e6,comparator_guard_pending_tag_counter_and_routes_not_included=True,existing_context_containment_credit=0,full169_copies_are_priced_proposal_not_information_theoretic_requirement=True,physical_home_clone_count_not_bound=True)
 return dict(schema='DS_CAPTURE_VM_VERSION_CONSUMER_ADMISSION_1',candidate='DS4096-TP4-S58-PAR2-NP2048',source_census=c,source_wait_bits={'ME':1,'SU':2,'QE':4,'XU':8,'HE':16},first_W1_W3_consumers=[dict(producer_pc=p['producer_pc'],first_consumer_pc=p['first_consumer_pc'],wait=p['wait'],explicit_ME_wait=bool(p['wait']&1),explicit_QE_wait=bool(p['wait']&4)) for p in captured],
  source_core_pc66_to_pc70_native_accept_lower_bound_edges=24,lower_bound_not_deadline=True,actual_consumer_first_edge=None,actual_consumer_last_edge=None,current_PHW10_program_user_generation_origin=None,actual_callback_handle=None,
  required_defaultoff_guard='Before actual registered SUgo for dependent descriptor, require all exact operand-version extents sameidentity and VMvisible with live VMversion lease; annotate and verify each xs_rd_re+src0/address and aligned vx/cwx at read R+2. Existing unit_ready/waited are necessary but insufficient. No rom_idle or producerbanklease substitute.',
  named_hook='core S_ISSUE d_unit==2 admission conjunction before su_go NBA; NEW opt-in guard implementation/source equivalence and acceptance callback required',guard_implemented=False,
  bank_phase_release='source-idle + every formatted row VMvisible + packet debts + positive captured sourcecredit terminal; next edge rearm for I67, separately from retained VM version leases',
  VMversion_release='accepted consuming VM read(s), exact address/version and fullcontext association, all corresponding R+2 tags retired; no timed promise',
  suppress_native_ROM_slots=list(range(128)),native_scalar_publication_slot=0,competing_writer_families=['ww_h','rom','vw_me','vw_su','vw_rd','xs_vm','xs_res','vw_xe','ww_q','ww_x','xa','xb'],sameaddress_equaldata_veto=True,
  one_bank_generation_until_SUread_deadlocks_I66_I67_I70=True,bank_and_VMlease_distinct=True,no_new_payloadseat_or_VM512_lease_assumed=True,
  metadata_fields=fields,metadata_bits_per_VMversion=bits,capture_minimum_metadata=floor(c['capture_frames_lower_bound']),all_matrix_minimum_metadata=floor(c['all_matrix_frames_lower_bound']),two_metadata_scopes_alternatives_not_additive=True,selected_VMlease_capacity=None,
  source_native_singleclk=True,target_stream_GHz=1.2,target_SU_GHz=.9,CDC_provider_and_grant_latency=None,station_C=None,consumer_ordering_equation='native_SUaccept >= max(native_prerequisite_accept_lower, last_required_VMvisible + 2 native edges); only ordering lower bound, guard delay and physical CDC unknown',VMlease_release_after='all accepted required sourceVM reads + matched R+2 tag retirement, then positive captured lease feedback; never idle alone',composed_token_delta_cycles=None,contextual_PR_admitted=False,new_jobs=[])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
