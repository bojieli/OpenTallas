#!/usr/bin/env python3
"""Bounded exclusive publication candidate; actual delayed-visible provider model, not RTL/P&R."""
import argparse,hashlib,json,math,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
BACKEND=('6e1158394262bc47773993e04efce0672ac4552e','tools/common_hbm_backend_provider_contract.py')
BASE='d2c28c279c4b8df731f9c4937e790831529a954b'
def get(p):return subprocess.check_output(['git','show',p[0]+':'+p[1]],cwd=ROOT)
def build():
 raw=get(BACKEND);env=dict(__name__='immutable_model_import',__file__=str(pathlib.Path(__file__).resolve()));exec(compile(raw,BACKEND[1],'exec'),env)
 model=env['BurstVisibilityModel'](capacity_sectors=1<<24);trace=[];complete=0;held_owner=True
 for sector in range(9):
  before=bytes([0]*32);data=bytes([sector+1]*32);model.preload(sector,before)
  tag=model.reserve(sector,sector,data);assert tag is not None
  column=model.now;model.WR_issue(tag,sector,column);model.take_scheduled(tag)
  assert model.read(sector,True)==before and model.peek_visible(tag) is None
  while model.now<column+7274:
   assert model.memory[sector]==before and model.peek_visible(tag) is None and held_owner
   model.tick()
  # Completion event held under consumer stall, no slot/owner credit freed by visibility alone.
  assert model.memory[sector]==data;event=model.peek_visible(tag);assert event['visible_ps']>=column+7274
  model.tick(3);assert tag in model.slots and held_owner
  model.take_visible(tag);complete+=1;trace.append(dict(sector=sector,column_ps=column,due_ps=column+7274,visible_ps=event['visible_ps'],completion_count=complete,row_publication=(complete==9)))
  assert (complete==9) or held_owner
 held_owner=False;assert complete==9 and not model.slots
 for sector in range(9):assert model.read(sector,not held_owner)==bytes([sector+1]*32)
 provider=env['compose']();write_terms=dict(REQ=10000,RAS=28125,RP=16250,RCDWR=9375,RFCPB=200000,CWL=6250,BURST=1024)
 envelope=sum(write_terms.values());assert envelope==271024
 cycles_per_write=math.ceil(envelope*3/2500);serialized=9*cycles_per_write+9+8+1
 return dict(schema='opentallas.w17.ckv-exclusive-publication-lease.v1',status='BOUNDED_MODEL_CANDIDATE_REQUIRES_JOINT_ADMISSION',source_pins=dict(backend=dict(commit=BACKEND[0],path=BACKEND[1],sha256=hashlib.sha256(raw).hexdigest()),legacy_idx=dict(commit=BASE,path='rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',sha256=hashlib.sha256(get((BASE,'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'))).hexdigest()),negative_mux='d4391b2e0',negative_early_visibility='a5839799b'),
 publication_lease=dict(stacks=4,exclusive_scope='all32PCs perstack: reject newW/C/P/indexB requests duringlease; includeprioracceptedB/Kwrites,queuebeats,andreadreturns inprelease drain',maximum_CKV_write_outstanding_per_stack=1,W_C_owner_token='pending+owner heldthroughactual WRvisible +consumeraccept; no newleaseowner untiloldtokenreleased',row_sector_count=9,sector_bits=256,row_bits=2304,prelease_required='actual backend queued-request-empty AND readreturn-empty AND no pendingB/Kwrite; scheduledboundedconsumer reserves and drainsallpriorreadreturns',duringlease='no competitorread/window/index/rope; soleCKVsector serialized tillactualvisible then next',publish_after='all9 actual backing updates and visibleeventaccepts; readfence and nexttoken producercredit helduntilpublication; downstreamconsumercredit independently helduntilfinaldone'),
 backend_correction=dict(clock='exact1.2GHz timestamp ceil(cycle*2500/3)ps, explicitforwarding instead oflegacy1000psdefault',capture_scheduled='retainactual h_tcol/sector/PC/data/strb beforequeuepop',backing_update='once at orafter actual h_tcol+CWL6250+BURST1024, nevercolumnissue',WR_visible='after backingupdate, hold stable untilaccepted; nohosttimer or guessedfutureack',read_fence='sameaddressread cannotissueuntilall9rowpublication; preservebackendWTR/RTW/RAS/WR constraints',finite_backend_slots=provider['geometry']['pending_backend_write_slots_per_controller'],provider_storage=provider['storage'],additional_backend_ports_and_area=provider['additional_port_cost']),
 ownership_exclusion=dict(actual_karb='k_ok disallowsKwrite whenbw_out!=0; b_ok disallowsBwrite whenkw_out!=0; incrementonacceptedwrite, decrementonrouted h_wr_done',required_stronger_event='replace legacyh_wr_done withactualvisiblecommit event in source-selectedbackend/karb closure; preserve exclusion whilepending untilactualvisible',done_OR='oneKpending/stack avoidlost simultaneousPC ORevents; W/C owner latch routes untagged Kdone'),
 numeric_pricing=dict(write_envelope_terms_ps=write_terms,perwrite_conservative_candidate_ps=envelope,perwrite_cycles_exact1p2GHz=cycles_per_write,ninewrite_group_cycles_with_sampling_turnover_publish=serialized,ninewrite_group_ns=serialized*5/6,one_time_row_CDC_and_consumer_publish_latency='Ram mustaddactualdomain crossing+publication/consumeracceptedcalendar; zeroCDC onlyifsource-proven sameclock',prelease_max_old_queue_beats_per_stack=64*32,prelease_max_return_beats_per_stack=32*32,prelease_total_landing_bound_beats=3072,prelease_landing_byte_demand_ifallbuffered=3072*32,prelease_cost='charge actual draineservice/consumerreservation separately; no overlapcredit',area_no_doublecount='backend additional.0443039744mm2 plusmandatoryW/C14FF+1152muxbits.0004689648mm2; excludes CDC/newproducerready/lease/drainobservability/readfence/consumer/control/routefit',conservative_envelope_scope='Ram-proposed analytical uppercandidate underexclusivelease+completedprelease drain; refresh recurrence and actualprovider replay mustvalidate beforefreeze orRTLadmission'),
 model_validation=dict(actual_supplied_column_events_delayed_commit_cases=9,early_read_data_stayed_old=True,visible_event_never_before_burst_end=True,stalled_visible_event_held=True,all9_data_rows_exact=True,consumer_stall_cycles3='test-only stall duration, notmodelservicebound',trace=trace),
 full_consumer_binding='acced7668 fourlanes16960bitbeat,17x256macros/lane,all1masks; no265groupport; finalaccepted/storedresultdone calendar separatelyrequired',scope='model-only sourcebinding+burst-provider deterministic test; noactualRTL/provider/persistence qualification',RTL_changed=False,hardware_jobs_launched=0,launch_allowed=False,adopt=False)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();r=build();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['numeric_pricing'],indent=2))
