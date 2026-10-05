#!/usr/bin/env python3
"""All retained macro ports and native-grid parent-route reservation, no flows.
An explicit conservative candidate is priced; incomplete source providers deny build.
"""
import argparse,bisect,collections,gzip,hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/full_sm_actual_parent_route_20261002'
GEOM=ROOT/'results/uarch/dsrom_l20_hierarchical_reservation_20261002'
PINS={}
def git(path,rev):
 b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT);PINS[rev+':'+path]=hashlib.sha256(b).hexdigest();return b
def emit(name,x):
 p=OUT/name;b=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
 if p.exists():assert p.read_bytes()==b,'immutable evidence drift: '+name
 else:p.write_bytes(b)
def norm(s):return s.replace('\\','')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--geometry-dir',type=Path,required=True);a=ap.parse_args()
 parent=json.loads(git('results/uarch/hbm_tc_parent_capacity_20261002/model.json','d215c4bf4'))
 native=json.load((GEOM/'actual_grid_usable_capacity.json').open())
 units=json.loads(git('results/arch/arch_budget_v41.json','e72abea5ae169d3167dddc89543013f0e6bb3a7a'))['unit_areas_um2']
 repair=git('rtl/v41rom/ot_v41_bmul2_rne_prepare.sv','d8c2d19c2f9d732e8bf4985277abc4cdf13d7af0')
 helper=git('rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv','d8c2d19c2f9d732e8bf4985277abc4cdf13d7af0')
 gate=json.loads(git('results/rtl/parent_dsrom_bmul_rne_execution_20261002_r2/parent_review.json','00c2008c7'))
 models={}
 for label,key,top,params in [('DS','deepseek_v41','ot_gpu_sm_v',dict(SUB=4,LBS=2,LSB=16,NC=8,IL=8,RMAX=4096,LEV=4,XD=128,MAX_OUT=512)),('Qwen','qwen','ot_gpu_sm_q',dict(SUB=4,LS=32,NC=16,IL=8,RMAX=4096,LEV=5,NXM=16,MAX_OUT=512))]:
  source=git('rtl/gpu/'+top+'.sv','000ba0898f5120a66d5905ccff333ebbbe28394d').decode()
  for p in ['rtl/gpu/ot_gpu_tc_col.sv','rtl/gpu/ot_gpu_tree.sv','rtl/gpu/ot_gpu_stack.sv','rtl/gpu/ot_gpu_issue.sv','rtl/gpu/ot_gpu_bulk_copy.sv']:git(p,'000ba0898f5120a66d5905ccff333ebbbe28394d')
  path=a.geometry_dir/(label+'_geometry.json.gz');blob=path.read_bytes();g=json.loads(gzip.decompress(blob));v=native['models'][label];assert v['export_sha256']==hashlib.sha256(blob).hexdigest();dbu=g['dbu_per_um'];assert dbu==1000
  grid=json.load((GEOM/'grid_inputs'/(label+'_grid.json')).open());nets={};masters=collections.Counter();missing=[]
  bindings=json.load(gzip.open(OUT/('source_macro_pin_binding_'+label+'.json.gz'),'rt'))
  source_pins={(p['instance'],p['pin']):p for p in bindings}
  assert len(source_pins)==len(bindings)
  for m in g['macro_instances']:
   masters[m['master']]+=1
   for p in m['pins']:
    if p['sig']!='SIGNAL' or not p['net'] or norm(p['net']) in ['clk','rst_n']:continue
    xy=p['avg_access_xy']
    if xy is None:missing.append([m['name'],p['pin']]);continue
    binding=source_pins[(norm(m['name']),p['pin'])];assert binding['access_DBU']==xy
    net=binding['source_resolved_net'];row=nets.setdefault(net,[]);row.append({'instance':norm(m['name']),'master':m['master'],'pin':p['pin'],'direction':p['io'],'access_DBU':xy})
  assert not missing,'Connected macro signal pin without access location'
  # ALL SRAM pins are included, not merely the TC/BD partial manifest.
  endpoints=sum(map(len,nets.values()));single=sum(len(ps)==1 for ps in nets.values())
  W=g['die'][2]/dbu;H=g['die'][3]/dbu
  root=[g['die'][2]/2,g['die'][3]+4320]
  cuts={}
  for l in v['native_cut_capacity']:
   axis=0 if l['direction']=='HORIZONTAL' else 1
   lows=sorted(min(p['access_DBU'][axis] for p in ps) for ps in nets.values());highs=sorted(max(p['access_DBU'][axis] for p in ps) for ps in nets.values())
   rlows=sorted(min(root[axis],min(p['access_DBU'][axis] for p in ps)) for ps in nets.values());rhighs=sorted(max(root[axis],max(p['access_DBU'][axis] for p in ps)) for ps in nets.values())
   rr=[]
   for r in l['cut_records']:
    c=r['cut_DBU'];lower=bisect.bisect_left(lows,c)-bisect.bisect_right(highs,c);bound=bisect.bisect_left(rlows,c)-bisect.bisect_right(rhighs,c)
    rr.append(dict(cut_DBU=c,macro_to_macro_unique_net_lower_demand=lower,parent_band_root_unique_net_demand=bound,native_OBS_halo_PDN_via_free_tracks=r['free_tracks'],policy50pct_signal_tracks=r['policy50pct_signal_tracks'],parent_band_single_plane_screen=bound<=r['policy50pct_signal_tracks']))
   cuts[l['layer']]=rr
  # A constructive upper reservation: distinct signal-net horizontal trunks
  # plus distinct endpoint vertical escape tracks. Shared endpoints do not
  # acquire free ports; repeated source-net fanout remains in endpoint count.
  trunk_count=len(nets);branch_count=endpoints+len(nets)
  # Actual FF connectivity constrains a distributed parent plan. A single
  # FF's D/Q/reset interfaces are never split into independently free roots.
  ff_classes=collections.Counter();direct_nets=set();ff_groups={}
  for ff in g['FF_instances']:
   linked={norm(p['net']) for p in ff['pins'] if p.get('net') and norm(p['net']) in nets}
   direct_nets.update(linked)
   xyz=[p['access_DBU'] for n in linked for p in nets[n]]
   if xyz:
    # Median is a proposed source-connected cluster anchor, not a placed
    # cell or source route bound. It preserves one position per actual FF.
    xx=sorted(p[0] for p in xyz);yy=sorted(p[1] for p in xyz)
    anchor=[xx[len(xx)//2],yy[len(yy)//2]];group='direct_macro_connected'
   else:anchor=None;group='requires_parent_comb_cone_binding'
   ff_classes[group]+=1
   ff_groups[ff['name']]={'master':ff['master'],'actual_macro_interface_net_ids':sorted(linked),'proposed_cluster_anchor_DBU':anchor}
  ffb=(json.dumps(ff_groups,sort_keys=True,separators=(',',':'))+'\n').encode();ffp=OUT/('actual_FF_interface_bindings_'+label+'.json.gz');ffc=gzip.compress(ffb,mtime=0)
  if ffp.exists():assert ffp.read_bytes()==ffc
  else:ffp.write_bytes(ffc)

  # Use actual exported planes; TC OBS M1..M6 forbids across-body lower metal.
  # A fresh east corridor and north corridor are macro-free. Reserve half
  # their track positions for PG/clock/vias/control before signal allocation.
  h=math.ceil((2*trunk_count*80/1000+4.32)/2.16)*2.16
  w=math.ceil((2*branch_count/(1000/64+1000/80)+4.32)/2.16)*2.16
  nw=W+w;nh=H+h
  horizontal_capacity=math.floor((h-4.32)*1000/80/2)
  vertical_capacity=math.floor((w-4.32)*1000/64/2)+math.floor((w-4.32)*1000/80/2)
  assert horizontal_capacity>=trunk_count and vertical_capacity>=branch_count
  cap=parent['models'][key]['parent_capacity'];base=cap['mandatory_parent_cell_reservation_cap_um2']
  # Explicit source-model obligations. RF uses only an existing 1R1W SRAM:
  #16 banks x4 pages x2 replicated operand-read copies;128 lane32bit writes
  # broadcast to both copies. No four-port SRAM or perfect bank service.
  rf_n=16*4*2;rf_macro=[94.824,41.04];rf_area=rf_n*math.prod(rf_macro)/1e6
  scratch_n=2;scratch_macro=[174.744,70.47];scratch_area=scratch_n*math.prod(scratch_macro)/1e6
  rf_mux_bits=2*16*3*256;rf_mux_cell=rf_mux_bits*.2
  simd_cell=128*units['fp32_mac_um2']
  rf_control=16*4*2*32*5*.2
  nonmatrix=(simd_cell+rf_mux_cell+rf_control)/.5/1e6+rf_area+scratch_area
  # RF/scratch get their own rectangles, not old row credit. Source binding
  # must provide the exact read request/write visible ack/epoch interfaces.
  side_area=nonmatrix;side_w=math.ceil(side_area*1e6/H/2.16)*2.16
  nw+=side_w;candidate_area=nw*nh/1e6
  # Existing ROW area can hold retained parent controls, but current repaired
  # parent area/pins are not inferred from that historical mapping.
  fp=max(abs(root[0]-p['access_DBU'][0])+abs(root[1]-p['access_DBU'][1]) for ps in nets.values() for p in ps)/dbu
  model=dict(source_top=top,source_commit='000ba0898f5120a66d5905ccff333ebbbe28394d',actual_params=params,ODB_sha256=g['ODB_sha256'],export_sha256=hashlib.sha256(blob).hexdigest(),dbu_per_um=dbu,
   retained_macro_master_counts=dict(masters),all_connected_macro_signal_net_count=len(nets),all_connected_macro_signal_endpoint_count=endpoints,single_macro_endpoint_nets_still_charged_parent_route=single,connected_pin_access_missing=missing,
   source_pin_binding_sha256=hashlib.sha256((OUT/('source_macro_pin_binding_'+label+'.json.gz')).read_bytes()).hexdigest(),constant_policy='Mapped TIEHI/TIELO output nets remain charged with every physical endpoint; no free tie replication,ideal zero/one distribution or service inferred.',complete_macro_signal_net_ledger='macro_signals_'+label+'.json.gz',actual_FF_interface_classes=dict(ff_classes),actual_macro_interface_nets_connected_directly_to_FF=len(direct_nets),actual_FF_connectivity_ledger='actual_FF_interface_bindings_'+label+'.json.gz',native_parent_route_cut_screens=cuts,
   source_transport=dict(weight_payload_Bpc=128,weight_line_Bpc=136 if label=='DS' else 128,x_write_Bpc=256,result_payload_Bpc=params['NC']*4,MAX_OUT=512,ring_depth=1024,bulk_copy_tags=1024,guarantee='Response input has no ready; actual tag/credit acceptance and backend guarantees must be preserved. No unconstrained producer rate or infinite response seats.',tree='Original SUB and lane order,chunk8 accumulation,IL8/ALAT7 ring,stack LEV unchanged'),
   actual_parent_cell_reservation_um2=base,actual_parent_post_cut_cell_capacity_um2=v['parent50pct_cell_capacity_um2'],retained_parent_cell_screen=base<=v['parent50pct_cell_capacity_um2'],
   nonmatrix_reservation=dict(SIMD_FP32_lanes=128,SIMD_cell_proxy_um2=simd_cell,RF_logical_bytes=256*1024,RF_1R1W_shallow_macros=rf_n,RF_banks=16,RF_pages=4,RF_operand_read_replicas=2,RF_read_Bpc=2*128*4,RF_write_Bpc=128*4,RF_mux_cell_proxy_um2=rf_mux_cell,RF_physical_bytes=rf_n*128*256//8,scratch_bytes=64*1024,scratch_macros=scratch_n,placed_reservation_mm2=nonmatrix,macro_OBS='All M1-M4 of existing SRAM masters,translated into reserved side rectangle; no TC space borrowed',RF_service_contract='At most one128lane aligned register vector/read/cycle per copy; random lane addresses require bank arbitration and cannot claim2048Bpc. All writes mirrored,visible acknowledge after macro completion. Source provider absent, no performance guarantee asserted.'),
   candidate=dict(die_bbox_um=[nw,nh],gross_mm2=candidate_area,retained_macro_body_um=[0,0,W,H],fresh_horizontal_signal_trunk_band_um=[0,H+4.32,nw,nh],fresh_vertical_signal_escape_band_um=[W+4.32,0,W+w,nh],RF_SIMD_scratch_reserved_rectangle_um=[W+w,0,nw,H],required_trunk_tracks=trunk_count,required_distinct_endpoint_escape_tracks=branch_count,horizontal_M8_capacity=horizontal_capacity,vertical_M7_M9_capacity=vertical_capacity,TC_OBS_crossed_below_M7=False,PG_clock_via_track_reservation_fraction=.5,actual_new_PDN_shapes_bound=False,full_macro_parallelism_preserved=True,replicas=32,array_gross_mm2_32SM=32*candidate_area,allocation_verdict='REJECT_CENTRALIZED_PARENT_BINDING: explicit all-port reservation preservesparallelism but expands to an impractical32SMarray; require distributed actual parent-cell/FF ownership binding',allocation_scope='Constructive upper reservation for the declared centralizedroot binding,not a routed layout. It is preserved as FAIL ratherthanadopted or tuned. Fresh PDN grid and detailed macro pin-escape/parent placement remain prerequisites.'),
   latency=dict(actual_source_multiplier_cycles=5,actual_source_IL=8,source_tree_and_ports_changed=False,shared_repair_additional_cycles=0,source_parent_band_worst_L1_um=fp,wire_timing_qualification_transfer=False,diagnostic_504um_reach_stages=math.ceil(fp/504),diagnostic_scope='Historical504um is an unqualified reach screen,not a timing contract or certifiedminimum. No transport cuts inserted.',gate='Transport stages cannot be silently inserted: require aligned control/data/tag acceptance and finitecredits/skids. Samecycle unpipelined candidate requires SSFF full-parent result; no column closure transfer.'),
   hardening_ready=False,exact_remaining_bindings=['Source-matched full SM opt-in join to the one GRADUAL_RNE=1 shared multiplier implementation; no divergent arithmetic repair','RF/SIMD/scratch and HC/SU actual source instance/schema/port/provider binding,not only priced rectangles','Detailed M4 pin escape to M7/M9 and fresh PG/via exclusions;current export unknownvia layer reserved on all planes','Actual parent producer/consumer placement and finite aligned transport schedule before any extra cuts'])
  nb=(json.dumps(nets,sort_keys=True,separators=(',',':'))+'\n').encode();np=OUT/('macro_signals_'+label+'.json.gz');compressed=gzip.compress(nb,mtime=0)
  if np.exists():assert np.read_bytes()==compressed
  else:np.write_bytes(compressed)
  models[label]=model
  del g,nets,blob
 emit('model.json',dict(schema='opentallas.full-SM.actual-ODB-parent-route.v2',models=models,pins=PINS,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),shared_numerical_gate='00c2008c7',shared_numerical_gate_receipt=gate,shared_implementation_sha256=hashlib.sha256(repair).hexdigest(),shared_encoder_sha256=hashlib.sha256(helper).hexdigest(),original_failures_unchanged=True,full_SM_build_GO=False,new_OpenROAD_invocations=0))
 print(json.dumps({k:{'nets':v['all_connected_macro_signal_net_count'],'endpoints':v['all_connected_macro_signal_endpoint_count'],'candidate_um':v['candidate']['die_bbox_um'],'candidate_mm2':v['candidate']['gross_mm2'],'hardening_ready':False} for k,v in models.items()}))
if __name__=='__main__':main()
