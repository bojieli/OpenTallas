#!/usr/bin/env python3
"""One full protected K512 geometry reservation; source sites, not physical GO."""
import argparse,collections,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_MTP_full_scalar_home_20261003'
ASR='DFFASRHQNx1_ASAP7_75t_R';BUF='BUFx4_ASAP7_75t_R'
INV='INVx1_ASAP7_75t_R';NAND='NAND2x1_ASAP7_75t_R';TIE='TIEHIx1_ASAP7_75t_R'
def read(name):return json.loads((OUT/'inputs'/name).read_text())
def snap(v,grid):return math.ceil(v/grid)*grid
def tree(n,leaf):
 out=[math.ceil(n/leaf)]
 while out[-1]>1:out.append(math.ceil(out[-1]/8))
 return out
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def build():
 for row in read('origins.json'):
  if hashlib.sha256((OUT/'inputs'/row['copy']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('changed frozen input')
 s=read('scalar_model.json');f=read('cell_prices.json')['facts'];lefs=read('cell_LEF.json');rc=read('RC.json');p=read('field_parent.json');inventory=read('parent_inventory.json')
 bits=s['state']['protected_bits']
 if bits!=112608 or s['state']['width_delta_only']!=7690:raise ValueError('not full current scalar')
 sections={k:collections.Counter(v) for k,v in s['cost']['cell_counts_by_section'].items()}
 storage=sections['storage_QN_restore_hold_clock_reset_lower_bound']
 # Native storage/feedback clusters have positive localclock wire spans.
 # Pin-only fanout8CLK/7RESET minima do not establish those spans. Use one
 # fixed three-sink leaf for both networks; charged upperFO8 remains a floor.
 levels=tree(bits,3);old_clock=sum(s['cost']['clock_levels_minimum']);old_reset=sum(s['cost']['reset_levels_minimum'])
 delta=2*sum(levels)-old_clock-old_reset
 storage[BUF]+=delta;storage[TIE]=bits # each ASR SETN tie, no unproven shared tie
 totals=sum(sections.values(),collections.Counter())
 widths={m:round((.162 if m==TIE else f[m]['SS']['size_um'][0])*1000) for m in totals}
 if any(v%54 for v in widths.values()):raise ValueError('native site multiple')
 width=snap(1300000,54);halo=12960;pitch=540;cursor=0;layouts=[];placed=collections.Counter()
 for section,counts in sections.items():
  remaining=counts.copy();groups=[]
  if section=='storage_QN_restore_hold_clock_reset_lower_bound':
   template=[ASR,INV,INV,NAND,NAND,NAND,BUF,BUF,TIE]
   # Three independent SAMECELL hold/restore clusters, two local branchBUF.
   template=template*3+[BUF,BUF];members=[];x=0
   for master in template:members.append(dict(master=master,x_DBU=x,width_DBU=widths[master]));x+=widths[master]
   groups.append(('protected3FF_CLK_RESET_leaf',bits//3,x,members))
   for master,n in collections.Counter(template).items():remaining[master]-=n*(bits//3)
  for master,n in sorted(remaining.items()):
   if n<0:raise ValueError('unpriced cell cluster')
   if n:groups.append((master,n,widths[master],[dict(master=master,x_DBU=0,width_DBU=widths[master])]))
  runs=[];row=0
  for name,count,w,members in groups:
   perrow=width//w;rows=math.ceil(count/perrow)
   runs.append(dict(name=name,count=count,group_width_DBU=w,per_row=perrow,rows=rows,first_row_DBU=cursor+row*pitch,row_pitch_DBU=pitch,members=members))
   for master,n in collections.Counter(v['master'] for v in members).items():placed[master]+=n*count
   row+=rows
  layouts.append(dict(section=section,bbox_relative_DBU=[0,cursor,width,cursor+row*pitch],runs=runs));cursor+=row*pitch+4320
 if placed!=totals:raise ValueError('dropped or duplicated full provider cells')
 old_reader=p['new_home']['new_identical_home_per_shard_DBU'];x=snap(old_reader[2]+halo,54);top=old_reader[3]
 home=[x,top-(cursor+2*halo),x+width+2*halo,top]
 corridor=[old_reader[2],home[1],home[0],home[3]]
 boxes=inventory['boxes']+[dict(kind='reader',name='FIELD_PARENT_READER_FULL_SHARD_RESERVATION',bbox_DBU=old_reader)]
 conflicts=[v for v in boxes if overlap(home,v['bbox_DBU']) or overlap(corridor,v['bbox_DBU'])]
 if conflicts:raise ValueError('named scalar/corridor collides with retained inventory')
 if not 0<=home[0]<home[2]<=33000000 or not 0<=home[1]<home[3]<=26000000:raise ValueError('26x33 reticle')
 # Exact literal R0 M1rails on ALL occupied native masters. Highermetal
 #upfeed/contacts and macroOBS are separate constraints, never free tracks.
 rails={}
 for master in totals:
  rails[master]={}
  for supply,expected in [('VSS',[-9,9]),('VDD',[261,279])]:
   pin=re.search(r'PIN '+supply+r'\b(.*?)END '+supply,lefs[master],re.S);rect=re.search(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pin[1])
   y=[round(float(rect[k])*1000) for k in (2,4)]
   if y!=expected:raise ValueError('native PG rail phase')
   rails[master][supply]=y
 # Reserve separate sections of a native horizontal M4 cut. These are
 #actual track positions in a cell-free corridor, not PG/clock occupancy proof.
 txt=(OUT/'inputs/tracks.txt').read_text();g=re.search(r'make_tracks M4[^\n]*-y_offset ([\d.]+)[^\n]*-y_pitch ([\d.]+)',txt);offset,pitch_um=map(float,g.groups());y=home[1]+halo;cuts=[]
 names=[('score',66),('index',25),('original_lease',30),('fence',33),('VM_read_request',31),('VM_read_return',32),('VM_write',63),('XU_origin',52),('ME_origin',52)]
 for name,n in names:
  h=snap(2*n*round(pitch_um*1000),270);lo=y/1000;hi=(y+h)/1000
  first=math.ceil((lo-offset)/pitch_um);last=math.floor((hi-offset)/pitch_um);count=last-first+1
  if count//2<n:raise ValueError('source cut underreserved')
  cuts.append(dict(name=name,signals=n,bbox_DBU=[corridor[0],y,corridor[2],y+h],layer='M4',direction='HORIZONTAL',first_grid_track=first,last_grid_track=last,gross_grid_tracks=count,policy_half_reserved_tracks=count//2,actual_available_after_PG_via_clock=None));y+=h+4320
 if y>home[3]-halo:raise ValueError('cuts exceed corridor')
 body=sum(n*(.04374 if m==TIE else f[m]['SS']['area_um2']) for m,n in totals.items())
 # All3leaves reside in11.61um groups. Conservative15um nativepin-to-pin
 #wire envelope includes branch spine + short stubs; actual viaCap unknown.
 load={}
 for pin in ('CLK','RESETN'):
  pins=3*f[ASR]['FF']['pins'][pin]['cap_fF'];wire=15*rc['C_fF_per_um']
  load[pin]=dict(sinks=3,pins_fF=pins,positive_wire_length_envelope_um=15,wire_fF=wire,total_excluding_via_fF=pins+wire,remaining_to5p76_for_all_vias_fF=5.76-pins-wire,actual_pin_via_route_verified=False)
  if pins+wire>=5.76:raise ValueError('fixed positive local branch screen fails')
 return dict(schema='DS_MTP_FULL_K512_NAMED_HOME_R1',source='594fee25fd9b5ba5a29e99b2b14c381841dd44d8',candidate='DS4096-TP4-S58-PAR2-NP2048',
  instance=dict(name='DS_S58_S0_TP_R0_PAR2_SHARD0_NATIVE_CORE_K512_ORIGIN',namespace='die.u_tile.u_core.u_xu.u_sel + source XU/ME origins',stage=0,rank=0,physical_shard=0,allocated_instances_this_receipt=1,source_cores_per_wrapper=1,fleet_replica_count=None,other_shards_or_head_provider_not_instantiated_here=True,model_home_binding_only_not_new_topology_adoption=True,representative_parent_binding_not_proof_stage0_owns_native_MTP_program=True),
  named_home=dict(bbox_DBU=home,width_um=(home[2]-home[0])/1000,height_um=(home[3]-home[1])/1000,gross_mm2=(home[2]-home[0])*(home[3]-home[1])/1e12,halo_DBU=halo,row_pitch_DBU=540,site_DBU=54,orientation='R0',all_cell_runs=layouts,retained_rectangle_conflicts=conflicts,reader_reservation_kept=old_reader,all_compiled2048pairs_and14336cfg_macros_unchanged=True,source_geometry_reservation=True,placed_fit=False),
  cells=dict(source_full_counts=s['cost']['cell_counts_total'],selected_counts=dict(totals),exact_conserved=True,body_um2=body,gross50pct_mm2=body*2/1e6,original_full_gross50pct_mm2=s['cost']['gross50pct_mm2'],additional_CLK_RESET_BUF_vs_pin_minimum=delta,additional_per_ASR_SETN_TIE=bits,width7690_already_inside_full112608=True,width_only_0p03135116988_NOT_ADDED=True,old_scalar_removal_or_containment_credit=0,full112608_protected_bits=bits,leaf2016_and578buffer_cost_not_inside_this_provider=True),
  named_corridor=dict(bbox_DBU=corridor,area_mm2=(corridor[2]-corridor[0])*(corridor[3]-corridor[1])/1e12,cuts=cuts,total_interface_signals=384,ports_not_deduplicated_or_renamed=True,policy_half_is_reservation_not_actual_available_tracks=True,full_router_to_VM_HUB_or_leaf_accept_path_unbound=True),
  clock_reset=dict(domain_GHz=.9,SS_setup_ps=60,FF_hold_ps=25,local_matched3sink_levels_per_network=levels,total_BUF_floor_two_networks=2*sum(levels),local_branch_loads=load,native_CLK_RESET_ASR_polygons={pin:re.search(r'PIN '+pin+r'\b(.*?)END '+pin,lefs[ASR],re.S)[1] for pin in ('CLK','RESETN')},local_R0_PG_rails_DBU=rails,root_Clock_reset_native_contact_and_M8_upfeed=None,upper_FO8_spatial_relays_not_in_minimum_cell_counts=True,first_upper8_leaf_cluster_span_um=7*11.61,upper8_BUF_pin_load_fF=8*f[BUF]['FF']['pins']['A']['cap_fF'],upper8_branch_wire_length_ceiling_um=(5.76-8*f[BUF]['FF']['pins']['A']['cap_fF'])/rc['C_fF_per_um'],pin_minimum_tree_not_spatially_reachable_without_added_relays=True,full_K512_clock_baseline_not_removed=True,reset_assert_does_not_clear_accepted_holder_debt=True),
  latency=dict(source_logical_tick_II=1,loaded_codec_compare_encode_II_unqualified=True,source_after_last_edges=1026,source_129280score_segment_edges=130817,conditional_ns_at0p9GHz=130817/.9,VM_freeze_read_reservation2_retained=True,extra_pipeline_edges_selected=0,zero_extra_edge_measured=False,full_iteration_latency=None,allcopies_delivery_reverseCDC_stalls_not_zero=True),
  admission=dict(named_one_provider_cellsite_and_corridor_reservation_ready=True,physical_G0=False,RTL_GO=False,rate_or_tau=False,reason='All cells have a named disjoint source-row reservation; loaded codecs, upperclock relays, legal native contacts/vias, PGupfeed and source VM/provider fence still require construction. No wholeparent placedfit or actualfleet mapping transferred.',new_jobs=0,original_RTL_changed=False,global_solver_changed=False),
  owner_actions=dict(Russell='Use named one fullK512 origin home, full112608bit state and complete sourcecost; no extra7690width-only debit. Own actual defaultoff source control/native acceptance and loaded feedback cuts.',Arch='Place/capture complete feedback codec at0.9GHz within named runs and corridor; join native CLK/RESET/SETN contacts, upperrelays and actual M8/PGupfeed. Local3sink wire model leaves only explicit viaCap allowance, not proof.',Maxwell='Join constructed routes and loaded stage costs back into selected field-parent budget; no copy to allS58/PAR2 fleet until actual core namespaces enrolled.'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
 if a.verify:
  for f,h in json.loads((OUT/'pins.json').read_text()).items():
   if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise ValueError('changed source/artifact '+f)
  if json.dumps(build(),sort_keys=True,indent=2)+'\n'!=(OUT/'model.json').read_text():raise ValueError('nonidentical fullscalar home')
  print('PASS full source cell/site/port reservation; NO PHYSICAL OR RTL ADMISSION')
 else:
  if a.out is None:p.error('--out required')
  a.out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
