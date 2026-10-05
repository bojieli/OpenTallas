#!/usr/bin/env python3
"""Partition/index/actual-return factorial in the retained token DAG.
Source-structural/nominal calendar diagnostic, no hardware service guarantee.
"""
import argparse,collections,copy,hashlib,json,math,re,resource,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_4096_comparable_capacity_20261002'
def main():
 resource.setrlimit(resource.RLIMIT_AS,(16*1024**3,16*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
 ap=argparse.ArgumentParser();ap.add_argument('--keys-per-site',type=int,required=True);args=ap.parse_args();assert args.keys_per_site==131072
 sys.path.insert(0,str(ROOT/'tools'));import uarch_model as u
 pins={}
 for p in ['tools/uarch_model.py','tools/decode_critical_path.py','rtl/v41rom/ot_v41_rom_array.sv','rtl/v41rom/ot_v41_ret.sv']:
  b=subprocess.check_output(['git','show','e72abea5ae169d3167dddc89543013f0e6bb3a7a:'+p],cwd=ROOT);assert (ROOT/p).read_bytes()==b;pins[p]=hashlib.sha256(b).hexdigest()
 options=json.load(open(OUT/'partition_token_options.json'));candidate=options['lowest_stages_passing_conservative_capacity'];owned=json.loads(subprocess.check_output(['git','show','4b6708348f3938e0830c3549fbbecadbce18e798:results/uarch/dsrom_l20_hierarchical_reservation_20261002/model.json'],cwd=ROOT));lat=owned['latency']
 batch=lat['batch_pipeline_empty_slot_conditional_cycles'];assert batch==392 and lat['batch_META_accepted_events']==64
 count=math.ceil(args.keys_per_site/64);calendar=count*batch;calendar_us=calendar/1.2e9*1e6
 original=u._cons_adjust;saved=copy.deepcopy(u.PRESETS['proposal']);rows=[]
 for S in [41,candidate]:
  opt=next(x for x in options['priced_options'] if x['capacity']['stages']==S);capacity=opt['capacity'];L=math.ceil(math.log2(2*capacity['pairs_per_die']))
  for index in [False,True]:
   for ret in [False,True]:
    capture=[]
    u.PRESETS['proposal']['bf16_stripe_macros']=2*capacity['BF16_pairs_per_die'];u.PRESETS['proposal']['vm_write_elems']=1 if ret else saved['vm_write_elems']
    def adjustment(g,P,*a,**kw):
     sites=[]
     for name,nd in g.nodes.items():
      if name.endswith('.idx.score'):
       desc=nd['desc'];match=re.search(r'index scores: (\d+) keys/die x (\d+) heads',desc);assert match,desc
       keys=int(match[1]);heads=int(match[2]);assert heads==32
       site_cycles=math.ceil(keys/64)*392
       sites.append(dict(name=name,source_description=desc,source_keys_per_die=keys,source_heads=heads,source_key_dim=128,retained_issue_us=nd['issue']*1e6,retained_depth_us=nd['depth']*1e6,nominal_calendar_us=site_cycles/1.2e9*P))
       if index:nd['issue']=max(nd['issue'],site_cycles/1.2e9*P)
     assert len(sites)==8
     value=original(g,P,*a,**kw);delta=[]
     if ret:
      # Retained array has binary nodes,5cycle decision pipeline and RST1;
      # one actual root result word percycle. Replace old assumed fanin8
      # tree + Ksplit-depth term with the fixed source array traversal screen.
      # WAIT/FIFO/late siblings/root additions remain unbounded, not perfect.
      for name,nd in g.nodes.items():
       v=nd.get('_uarch')
       if v:
        previous=v['tree']+v['adder_levels']*8;source=6*L+1;extra=max(0,source-previous)
        nd['depth']+=extra/1.2e9;delta.append(dict(node=name,old_return_and_Ksplit_cycles=previous,binary_return_min_forward_cycles=source,added_depth_cycles=extra,vm_return_rows_pc=1))
      finish=g.solve(True);value=finish[next(n for n in g.nodes if n.endswith('token.return'))]
     if P==1:capture.append(dict(index_sites=sites,actual_source_array_traversal_deltas=delta,graph_nodes=len(g.nodes),graph_kinds=dict(collections.Counter(n['kind'] for n in g.nodes.values()))))
     return value
    u._cons_adjust=adjustment
    try:
     p=u.cons_v41_rom(S,8,36,bf16='columns',clock_hz=u.PRODUCT_CLOCK_HZ,field_concurrency=u.FIELD_CONCURRENCY,added_latency=dict(u.SOFTPLUS_FIX,**u.W11_STREAM_SS,**u.PLUS_LAT),dyn_scale=u.PRODUCT_DYN_SCALE,slow_domain=(.9e9,'w18'),elem_stages=8,ss_wire=True,serial=u.PRODUCT_SERIAL,die=u.DIE_SHRUNK_INTERIM,vmh=u.VMC_FUSED,hub_block=u.PRODUCT_HUB)
    finally:u._cons_adjust=original;u.PRESETS['proposal'].clear();u.PRESETS['proposal'].update(saved)
    r=dict(stages=S,dies=4*S+44,pairs_per_die=capacity['pairs_per_die'],BF16_pairs_per_die=capacity['BF16_pairs_per_die'],finite_index_nominal_calendar_enabled=index,source_return_one_root_binary_screen_enabled=ret,conditional_analytical_whole_token_us=1e6/p['ar_tokens_s_b1'],pipeline_hops_us=p.get('pipeline_hops_us'),source_graph_calibration=capture,physical_or_service_qualified=False);rows.append(r)
    print(json.dumps({k:v for k,v in r.items() if k!='source_graph_calibration'}),flush=True)
 def at(S,i,r):return next(v['conditional_analytical_whole_token_us'] for v in rows if v['stages']==S and v['finite_index_nominal_calendar_enabled']==i and v['source_return_one_root_binary_screen_enabled']==r)
 delta=dict(partition_only_legacy_services_us=at(candidate,False,False)-at(41,False,False),partition_only_same_index_calendar_us=at(candidate,True,False)-at(41,True,False),partition_only_same_corrected_index_return_us=at(candidate,True,True)-at(41,True,True),index_correction_unchanged_partition_us=at(41,True,False)-at(41,False,False),return_correction_unchanged_partition_us=at(41,False,True)-at(41,False,False),index_return_interaction_at41_us=at(41,True,True)-at(41,True,False)-at(41,False,True)+at(41,False,False))
 x=dict(schema='opentallas.DSROM4096.partition-index-return-factorial.v1',pins=pins,rows=rows,deltas=delta,index=dict(keys_per_site=args.keys_per_site,keys_input_provenance='Explicit parent source-screen requirement; actual G/quarter/owner key-distribution join remains unqualified',sites=8,site_work_ownership_basis='Each retained source-generated idx.score description, not eight identical131072key jobs. L2/L8/L14=131072,L20=262144,L24/L28/L32/L36=4096; sourceG/owner and instruction binding still open.',actual_source_IH=32,actual_source_MD=128,batch_keys=64,batch_cycles=392,batches=count,cycles_per_site=calendar,no_stall_calendar_us_per_site=calendar_us,keys_per_second_nominal=args.keys_per_site/(calendar/1.2e9),payload_B_per_key=68,minimum_average_key_payload_Bps=args.keys_per_site*68/(calendar/1.2e9),actual_HBM_ports=128,WB=32,GA=24,finite_backend_max_stall_or_delivery_guarantee_bound=False,scan_upper_service_bound_us=None,source_schedule_scope=lat['batch_schedule_scope']),return_source=dict(binary=True,decision_pipeline_cycles=5,RST_cycles_screen=1,root_result_words_pc=1,source_input_has_no_backpressure=True,queue_depth_RD_driver_bound=False,source_root_QD=16,golden_sibling_order_preserved_as_required=True,actual_fixed_N_power_of_two_and_cfg_namespace_bound=False,return_roots_per_die_bound=False,one_root_screen_is_not_actual_product_return_bandwidth=True,retained_cfg_e_width_bits=8,required_pair_cluster_count_at_cfg_namespace_limit='ceil(NP/256); additional hierarchy/merger/source allocation required; no free parallel output ports inferred',WAIT_late_sibling_FIFO_overflow_contract_bound=False,source5cycle_add_SSFF_qualified=False,full138469120bit_store_not_shrunk=True),calendar_only_is_not_131072key_RTL_PASS=True,full_product_return_correction_row_qualified=False,reported_parent_r7=dict(before_correction_us=540.81,after_correction_us=4004.59,reference_us=358.84,source_file_intaken=False,explanation='Those exact totals are not reproduced here; retained LAT8 mixed-product factorial is source-pinned separately. No11xloss is attributed to partition alone.'),optimal_certified_per_user_latency_us=None,new_HDL_or_OpenROAD_invocations=0,new_pve2_pve3_tasks=0,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 p=OUT/'service_factorial.json';b=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
if __name__=='__main__':main()
