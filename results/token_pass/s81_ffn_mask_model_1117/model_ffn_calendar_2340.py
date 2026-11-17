from pathlib import Path
import os,json,sys,re
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116');code=r/'code_bf_components_2240';source=r/'source_bf_components_2240';b=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1')
a=json.loads((source/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(source),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_FRAME_SOURCE_ROOT=str(source),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN='/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4tapfix1.json',OT_XS_ASB_SCHEDULE_DIR=str(r/'profiles'),OT_GUNIT_BF_DEFINES='OT_GUNIT_BF_M1REG,OT_GUNIT_BF_C1REG,OT_GUNIT_BF_SVREG,OT_GUNIT_BF_FWPIPE')
sys.path[:0]=[str(code/'tools/s81_dv/layer_prog'),str(code/'tools/s81_dv'),str(code/'tools')]
os.environ['OT_S81_SELECTED_CHILD_FILES']='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv'
import dv_layer_compile as C
from layer_prog import bound_data as BD,bound_ctl_lanes as BCL,lower_gu as GU,lower_vpx as VPX
B=BD.load_bind(b/'out',str(b/'asbuilt_run.json'),code)
die=C.Die(code,netlist=B['netlist_path'],netlist_sha=B['netlist_sha256'],bound_rtl=b/'out/rtl');BD.rebind_links(die,B)
from layer_prog import xs_place as XP,final_ffn as FF,xs_calendar as XC
fx=XP.Fix(r/'L0')
from collections import Counter
from dv_layer_compile import ctl_path
fragments=json.loads((r/'final_ffn_mask_map_2320/fragments.json').read_text())
sched=json.loads((r/'l0_current_model_lk_r4_bf_vctl_2255/schedule.json').read_text())
sid_to_inst={v['sid']:k for k,v in die.slices().items()}
links=die.links
def horizontal(a,b):
 assert a%2==b%2
 step=1 if b>a else -1
 out=[]
 for c in range(a//2,b//2,step):
  x,y=sid_to_inst[2*c+a%2],sid_to_inst[2*(c+step)+a%2]
  q=[(k,v) for k,v in links.items() if (x,'ro_e' if step==1 else 'ro_w') in v['src'] and (y,'ri_w' if step==1 else 'ri_e') in v['dst']]
  assert len(q)==4,(a,b,x,y,len(q))
  out.extend(dict(link=k,age=v['age_edges']) for k,v in q)
 return out
bridges={}
for a in range(16):
 for b in range(16):
  q=[(k,v) for k,v in links.items() if (sid_to_inst[a],'vo') in v['src'] and (sid_to_inst[b],'vi') in v['dst']]
  if q:assert len(q)==1;bridges[a,b]=q[0]
legs=[];packets=[]
for idx,f in enumerate(fragments):
 a,b=f['source_sid'],f['sid']; lf,df=f['source_leaf'],f['leaf']; rank=f['rank']; partial=f['mask']!=255
 current=a;row=f['source_row'];source_leaf=lf;ls=[]
 def add(kind,destination,dr,dleaf,path):
  global current,row,source_leaf
  z=dict(fragment=idx,rank=rank,kind=kind,source=current,destination=destination,source_leaf=source_leaf,leaf=dleaf,source_row=row,row=dr,path=path,pairs=1,mask=f['mask'] if kind=='local_masked_copy_candidate' else 255)
  ls.append(z);current,row,source_leaf=destination,dr,dleaf
 if a%2!=b%2:
  choices=[(abs(a//2-x//2)+abs(b//2-y//2),x,y,k,v) for (x,y),(k,v) in bridges.items() if x%2==a%2 and y%2==b%2]
  _,x,y,k,v=min(choices,key=lambda q:q[:3])
  if a!=x:add('wide',x,304,df,horizontal(a,x))
  # A partial remote arrival stays in scratch; full arrival is direct only at final SID.
  add('V',y,f['row'] if y==b and not partial else 304,df,[dict(link=k,age=v['age_edges'])])
  if y!=b:add('wide',b,304 if partial else f['row'],df,horizontal(y,b))
 elif a!=b:add('wide',b,304 if partial else f['row'],df,horizontal(a,b))
 else:
  add('local_masked_copy_candidate' if partial else 'local_copy',b,f['row'],df,[])
 if partial and a!=b:add('local_masked_copy_candidate',b,f['row'],df,[])
 legs.extend(ls);packets.append(dict(fragment=idx,legs=ls))
read=Counter();write=Counter();lane=Counter();controls=Counter();kinds=Counter();scratch=[]
for z in legs:
 rank=z['rank'];a=z['source'];b=z['destination']
 read[rank,a,z['source_leaf']]+=1;write[rank,b,z['leaf']]+=1;kinds[z['kind']]+=1
 # Both RDOUT and sendcfg are source-issued on its tier's single host engine.
 controls[rank,0 if sid_to_inst[a].endswith('N') else 1]+=2
 for p in z['path']:lane[rank,p['link']]+=1
 if z['row']==304:scratch.append(z)
floor=max(max(read.values()),max(write.values()),max(lane.values()),max(controls.values()))
def rows(c):return [dict(key=list(k) if isinstance(k,tuple) else k,count=v) for k,v in sorted(c.items())]
current_ops={o['op']:o for o in sched['ops']}
transport_budget=current_ops['ffn.combine_allreduce']['cycles']
result=dict(schema='opentallas.s81.ffn.actual-bound-path-finite-resource-model.v1',status='MODEL_ONLY_CALENDAR_BLOCKED',die_sha=die.die_sha,sid_to_inst=sid_to_inst,actual_bridges=[dict(source=a,destination=b,link=k,age=v['age_edges']) for (a,b),(k,v) in bridges.items()],fragments=len(fragments),one_pair_packet_policy=True,scratch_rows=[304,306],scratch_row_owner='VPX [0,448): requires explicit retirement/release before reuse',leg_counts=dict(kinds),leg_count=len(legs),controls=len(legs)*2,control_slots_by_rank_engine=rows(controls),read_pairs_by_port=rows(read),write_pairs_by_port=rows(write),lane_pair_slots=rows(lane),busiest_read_pairs=max(read.values()),busiest_write_pairs=max(write.values()),busiest_lane_slots=max(lane.values()),busiest_control_engine_slots=max(controls.values()),resource_only_local_transport_floor_cycles=floor,existing_entire_combine_budget_cycles=transport_budget,minimum_combine_budget_deficit_cycles=max(0,floor-transport_budget),scratch_writes=len(scratch),ctl_paths={str(s):ctl_path(die,i) for s,i in sid_to_inst.items()},blockers=['Current actual R4 calendar has no final FFN CAP ready/arrival/last-read row lease events: scratch304..306 is inside VPX0..448, so exclusivity cannot be claimed.','Actual source-bound XRT native runtime age qualification remains PENDING_SELECTED_XRT; candidate masked-local CI-to-SW latency has no measured contract.','Every source read+sendcfg consumes distinct host engine issue cycles. Resource floor excludes control distribution delays, path occupancy/return ages, combine75, POST63, offdie allgather, host reload and template inventory overhead.','Full-packet bulk4 needs8 scratchrows per intermediate stage; current2row proposal intentionally uses one pair per leg.','CAP padding changes write-port selection: producer arrival calendar must be decoded with padded descriptors to expose actual per-port conflicts.'],scope='Finite static resource lower bound from unchanged actual fragments and actual bound physical paths. No invented event ages or row lease; no complete schedule/RTL/physical/token qualification.')
out=r/'final_ffn_calendar_model_2340';out.mkdir(exist_ok=True)
(out/'model.json').write_text(json.dumps(result,indent=1)+'\n')
(out/'packets.json').write_text(json.dumps(packets,indent=1)+'\n')
print(json.dumps({k:result[k] for k in ['actual_bridges','leg_counts','controls','busiest_read_pairs','busiest_write_pairs','busiest_lane_slots','busiest_control_engine_slots','resource_only_local_transport_floor_cycles','existing_entire_combine_budget_cycles','minimum_combine_budget_deficit_cycles','scratch_writes','status']}))
