#!/usr/bin/env python3
"""One shared complete-frame reservation map and directed phase trace preparation."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/dsrom_noECC_complete_parent_map_20261002';I=BASE/'inputs'
def read(n):
 raw=(I/n).read_bytes();return json.loads(gzip.decompress(raw) if n.endswith('.gz') else raw)
def shifted(b,dy):return [b[0],b[1]+dy,b[2],b[3]+dy]
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def build():
 e=read('element.json.gz');p=read('local_physical.json');old=read('field.json.gz');macros=read('macros.json.gz');services=read('services.json');j=read('join.json.gz')
 if e['candidate']!=j['candidate'] or len(old)!=2048:raise ValueError('one shared compiled candidate')
 halo=4320;x=y=halo;rowh=0;fields=[];placed=[]
 for row in old:
  c=e['elements'][row['source_class']];w,h=c['outline_DBU'][2:]
  if x+w+halo>33000000:x=halo;y+=rowh+2*halo;rowh=0
  b=[x,y,x+w,y+h];local=row['local_pair'];fields.append(dict(local_pair=local,source_class=row['source_class'],bbox_DBU=b,source_root=local//32,full_hard_abstract=False))
  for m in c['macro_instances']:
   placed.append(dict(name=f'pair{local}.MB{m["MB"]}.PP{m["bank"]}',local_pair=local,MB=m['MB'],PP=m['bank'],bbox_DBU=[v+(x if k%2==0 else y) for k,v in enumerate(m['bbox_DBU'])],class_source=row['source_class'],template_record='inputs/element.json.gz',actual_mapped_cells_pending=True))
  x+=w+2*halo;rowh=max(rowh,h)
 end=max(r['bbox_DBU'][3] for r in fields);oldend=p['geometry']['field_end_DBU'];dy=end-oldend
 cfg=[dict(name=r['name'],bbox_DBU=shifted(r['bbox_DBU'],dy)) for r in macros if r['template']=='CFG']
 bands=[dict(r,bbox_DBU=shifted(r['bbox_DBU'],dy)) for r in p['geometry']['additional_named_reservations']]
 bf=sum(r['source_class']=='BF16_column_pair' for r in fields)
 if bf!=362 or len(placed)!=8192 or len(cfg)!=14336:raise ValueError('compiled inventory deleted')
 increment=sum(e['elements'][r['source_class']]['added_area_over_existing_PAR2_reservation_um2'] for r in fields)/1e6
 rowband=33*dy/1e6;extra_void=rowband-increment
 service_boxes=[dict(name=r['name'],bbox_DBU=[round(v*1000) for v in r['candidate_anchor_bbox_um']]) for r in services['rectangles']]
 # A single explicit conservative selector reservation, same logical provider.
 # Choose the first row-grid-aligned free strip after relocated cfg/return
 # reservations. No new class/partition sweep or reuse credit on old location.
 cursor=p['geometry']['last_field_cfg_return_repair_end_DBU']+dy
 selector=e['selector_replacement'];fullarea=selector['staged_unoptimized_core_proxy_mm2'];sw=2125440
 sy=math.ceil((cursor+2*halo)/2160)*2160;sh=math.ceil(fullarea*1e12/sw/2160)*2160
 select=[1000000,sy,1000000+sw,sy+sh]
 outside=[b for b in service_boxes if b['name']!='X_SEL_TOPK_STORE']
 if any(overlap(select,b['bbox_DBU']) for b in outside+bands+cfg+fields):raise ValueError('selector displaces preserved capacity')
 if select[3]>26000000 or end>26000000:raise ValueError('reticle violated')
 # Check frame placement without quadratic full pin-shape flattening.
 by_y={}
 for r in fields:by_y.setdefault(r['bbox_DBU'][1],[]).append(r)
 for rows in by_y.values():
  for a,b in zip(rows,rows[1:]):
   if overlap(a['bbox_DBU'],b['bbox_DBU']):raise ValueError('field frame collision')
 for a,b in zip(sorted(by_y),sorted(by_y)[1:]):
  if max(r['bbox_DBU'][3] for r in by_y[a])>b:raise ValueError('field rows overlap')
 # Known actual instance union is not established; retain repair bands as
 # explicit counterfactual headroom, not duplicate hardware instances.
 base=j['area']['prior_conservative_main_proxy_screen_mm2'];state=e['selector_replacement']['state_only_delta_mm2'];selector_extra=sw*sh/1e12-.3693656376
 cost=base+increment+max(0,extra_void)+selector_extra
 bench=(I/'LAT8_bench.sv').read_text()
 if '.r_v(128\'d0)' not in bench or '.w_we()' not in bench:raise ValueError('historical bench scope changed')
 trace=dict(case='L0.exp0.w1, stage0/rank0/shard1/phase10/key2149580800/runtimeEID0',
  source_reference='106fdd686 r3 + retained actual LAT8 adapter/spine/pair bench',
  hierarchy='Complete logical owner NP4096/NBF724/R128/PHW10/NB2/PP1, split inventory observed as two NP2048/R64 shards. Same LAT8/RNE/WAKE source; all padding retained, no constant root producers. One logical-owner trace does not qualify inter-die transport/CDC.',
  required_existing_bench_adaptation=['PHW6 singlepair historical diagnostic -> PHW10 full logical-owner selected product source pins, preserving R128 across two64root inventories','Replace one-pair-only connection with complete field/ordered forest/root provider','Connect actual spine w_we/w_addr/w_data to registered VM destination writes; observe postNBA visibility','Use exact phase10 cfg/stream/key/matrix address and native runtime EID path','Use committed directed macro images accepted by real source loader; record payload provenance, do not replace producer or inject golden results'],
  events=['Accepted q_go/runtime EID read with address/value/owner','accepted s_go under source ready/idle','actual cfg_go and each c_v/c_a/c_d delivery, final class/act visibility','VM x_re acceptance and registered x_q/quant/have visibility','s_ok/s_adv,xs/xb receipts and native mainCE/cap/lane events','tree/root r_v row/pos/value/fault receipt','w_we/address/data and postNBA VM visibility','source phase idle plus writer drain; coll_busy only if actual connected core/provider included'],
  checks=['Matching stage/rank/shard/phase/key/reset-era and runtime EID0 branch','No injected XFIFO push/root result, no made-up ACK, no global seat pool','All emitted paired reads across both shard inventories preserve address/order/captureN+2/consumerN+3; knownshard1 exp0w1 subset10240 is not fullowner count','Fullowner phase10 source nrow576 root/destination writes conserved; builder must pin both shard readcounts and rowtag coverage, no duplicate/lost writes','No arithmetic/XFIFO/tree/root/control faults','Do not replace firstCE7/last196/consume199 conditional indices with actual acceptance'],
  owner_split={'Nash':'phase10 exact native cfg/key/address/image and valid EID source binding','Epicurus':'reuse actual LAT8 bench/source; implement sole complete-phase observer/root/writer connection','Maxwell':'consume accepted trace and complete-phase/root/cfg/visibility costs','parent':'source/admission review and fleet lease; no duplicate active job'},
  launch_admitted=False,reason='Complete phase source/image/root-writer package and measured resources not yet supplied; historical bench lacks root/writer connections.',
  no_simulator_cycle_to_physical_clock_credit=True,no_RTL_engine_changes=True,no_ECC_requirements=True)
 model=dict(schema='opentallas.dsrom.noECC.complete-parent-map.v1',candidate=e['candidate'],origins=read('origins.json'),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  input_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(I.iterdir()) if f.is_file()},
  field={'all_compiled_pairs':2048,'q_pairs':2048-bf,'BF_pairs':bf,'macros':8192,'cfg_macros':14336,'root_regions':64,'field_end_DBU':end,'old_field_end_DBU':oldend,'cfg_return_band_y_translation_DBU':dy,'final_band_end_DBU':cursor,'placement_rows':len(by_y),'all_field_frames_disjoint':True,'full_macro_pin_OBS_PG_templates_from_complete4b15':True,'full_stdcell_placement_not_available':True},
  selector={'single_full_slot_bbox_DBU':select,'reserved_rectangle_mm2':sw*sh/1e12,'full_proxy_mm2':fullarea,'state_already_priced_mm2':.3693656376,'only_additional_full_proxy_charge_mm2':selector_extra,'old_store_location_not_reused_or_credited':True,'does_not_displace_preserved_controller_and_corridors':True,'new_location_transport_latency_unpriced':True,'balanced_filter_full_G0_not_closed':True,'proxy_not_variant_adoption':True},
  area={'prior_proposal_screen_mm2':base,'BF_complete_frame_growth_charged_once_mm2':increment,'additional_field_row_envelope_mm2':rowband,'extra_row_whitespace_noncontainment_policy_mm2':max(0,extra_void),'complete_selector_extra_charged_once_mm2':selector_extra,'combined_noncontainment_policy_screen_mm2':cost,'remaining_before_unpriced_interfaces_mm2':858-cost,'new_row_void_may_already_be_contained_in_inherited418_no_credit_until_disjoint_union':True,'RNE_WAKE_band_shadow_retained_as_policy_not_extra_instances':True,'actual_instantiated_area_credit_mm2':0,'fit_proven':False},
  clock={k:e['elements']['q_pair']['actual_WAKE1_clock_branch_topology'][k]['distinct_capture_plus4ROM_load_groups_lowerbound'] for k in ('ss','ff')},
  current_clock_basis='branch-aware15SS17FF before compute/control/wire; supersedes old12/14 aggregate reference',
  physical_GATE=e['physical_G0'],trace_plan=trace,
  single_user_objective={'headline':'strictly >3000 accepted tokens/s afterMTP','AR':'baseline reported separately',
    'assumed_tau':3.649,'assumed_iteration_budget_us':1216.3333333333333,
    'required_iteration':'actual sixposition verification + drafter + commit/rollback + exposed crossings/service stalls',
    'tau_is_assumption_not_measured':True,'phase_trace_not_MTP_rate':True,'historical_4500_rate_not_candidate_qualification':True,
    'changes_to_stages_dies_or_selector_location_require_entire_iteration_delta':True},all_ROM_ECC_mandatory=False,SRAM_HBM_link_semantic_checks_retained=True,new_jobs=0,physical_fit=False,fulltoken_rate=False)
 return model,fields,placed,cfg,bands,service_boxes
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output-dir',type=Path,required=True);x=a.parse_args()
 if x.output_dir.exists():raise ValueError('fresh record required')
 m,field,macro,cfg,bands,services=build();x.output_dir.mkdir(parents=True)
 for name,data in [('model.json',m),('trace_plan.json',m['trace_plan'])]:(x.output_dir/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
 for name,data in [('field.json.gz',field),('macros.json.gz',macro),('cfg.json.gz',cfg),('bands.json.gz',bands),('services.json.gz',services)]:
  (x.output_dir/name).write_bytes(gzip.compress((json.dumps(data,sort_keys=True)+'\n').encode(),mtime=0))
