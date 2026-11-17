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
"""Whole-64-word-beat assembly relocation; analytical resource price only."""
import json
from pathlib import Path
from collections import Counter,defaultdict
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116')
d=json.loads((r/'final_ffn_calendar_model_2340/model.json').read_text())
old=json.loads((r/'final_ffn_calendar_model_2340/packets.json').read_text())
frags=json.loads((r/'final_ffn_mask_map_2320/fragments.json').read_text())
edge={}
for p in old:
 for z in p['legs']:
  if z['kind']!='wide':continue
  a,b=z['source'],z['destination'];step=1 if b>a else -1
  for i,c in enumerate(range(a//2,b//2,step)):
   key=(2*c+a%2,2*(c+step)+a%2);q=z['path'][4*i:4*i+4]
   assert key not in edge or edge[key]==q
   edge[key]=q
# When run after the existing selected-source prefix, collect the entire bound
# adjacency, including edges the previous canonical-owner route never used.
if 'die' in globals():
 names={v['sid']:k for k,v in die.slices().items()}
 for a in range(16):
  for b in (a-2,a+2):
   if not 0<=b<16:continue
   right=b>a
   q=[dict(link=k,age=v['age_edges']) for k,v in die.links.items() if (names[a],'ro_e' if right else 'ro_w') in v['src'] and (names[b],'ri_w' if right else 'ri_e') in v['dst']]
   if q:
    assert len(q)==4,(a,b,q)
    edge[a,b]=q
def horizontal(a,b):
 step=1 if b>a else -1
 return [x for c in range(a//2,b//2,step) for x in edge[2*c+a%2,2*(c+step)+a%2]]
bridges=d['actual_bridges']
def legs_for(rank,a,al,ar,b,bl,br,mask,phase,identity):
 out=[];current=a;lf=al;row=ar;partial=mask!=255
 def add(kind,dst,dl,dr,path):
  nonlocal current,lf,row
  out.append(dict(rank=rank,phase=phase,identity=identity,kind=kind,source=current,source_leaf=lf,source_row=row,destination=dst,leaf=dl,row=dr,pairs=1,path=path,mask=mask if kind=='local_masked_copy_candidate' else 255))
  current,lf,row=dst,dl,dr
 if a%2!=b%2:
  bridge=min((x for x in bridges if x['source']%2==a%2),key=lambda x:(abs(a//2-x['source']//2)+abs(b//2-x['destination']//2),x['source']))
  x,y=bridge['source'],bridge['destination']
  if a!=x:add('wide',x,bl,304,horizontal(a,x))
  add('V',y,bl,br if y==b and not partial else 304,[dict(link=bridge['link'],age=bridge['age'])])
  if y!=b:add('wide',b,bl,304 if partial else br,horizontal(y,b))
 elif a!=b:add('wide',b,bl,304 if partial else br,horizontal(a,b))
 else:add('local_masked_copy_candidate' if partial else 'local_copy',b,bl,br,[])
 if partial and a!=b:add('local_masked_copy_candidate',b,bl,br,[])
 return out
bybeat=defaultdict(list)
for f in frags:bybeat[f['rank'],f['global_pair_first']//64].append(f)
assign={};used=set();assignments=[]
for key,fs in sorted(bybeat.items()):
 rank,beat=key;counts=Counter();leaves=Counter()
 for f in fs:
  if f['expert']!=0:continue
  n=f['mask'].bit_count();counts[f['source_sid']]+=n;leaves[f['source_sid'],f['source_leaf']]+=n
 assert sum(counts.values())==64
 sid=min(counts,key=lambda s:(-counts[s],s))
 leaf=min((lf for lf in range(5) if (rank,sid,lf) not in used),key=lambda lf:(-leaves[sid,lf],lf))
 used.add((rank,sid,leaf));assign[key]=(sid,leaf)
 canonical_sid=beat//5;canonical_leaf=beat%5
 assignments.append(dict(rank=rank,global_beat=beat,assembly_sid=sid,assembly_leaf=leaf,canonical_sid=canonical_sid,canonical_leaf=canonical_leaf,source_word_counts=dict(counts),source_majority_words=counts[sid]))
assert len(assignments)==80 and len(used)==80
assembly=[];returns=[]
for i,f in enumerate(frags):
 rank=f['rank'];beat=f['global_pair_first']//64;sid,leaf=assign[rank,beat]
 row=320+16*f['expert']+2*((f['global_pair_first']%64)//8)
 assembly+=legs_for(rank,f['source_sid'],f['source_leaf'],f['source_row'],sid,leaf,row,f['mask'],'assembly',i)
for a in assignments:
 for pair in range(8):
  returns+=legs_for(a['rank'],a['assembly_sid'],a['assembly_leaf'],448+2*pair,a['canonical_sid'],a['canonical_leaf'],464+2*pair,255,'combined_return',[a['global_beat'],pair])
def price(legs):
 c=Counter();rd=Counter();wr=Counter();lane=Counter();kinds=Counter()
 for z in legs:
  rank=z['rank'];src=z['source'];dst=z['destination'];kinds[z['kind']]+=1
  c[rank,0 if src%2 else 1]+=2
  rd[rank,src,z['source_leaf']]+=1;wr[rank,dst,z['leaf']]+=1
  for x in z['path']:lane[rank,x['link']]+=1
 alias=Counter()
 for (rank,eng),n in c.items():alias[eng]+=n
 return dict(legs=len(legs),leg_counts=dict(kinds),controls=2*len(legs),per_rank_engine=[dict(rank=k[0],engine=k[1],slots=n) for k,n in sorted(c.items())],separate_rank_control_floor=max(c.values()),aliased_rank_control_floor=max(alias.values()),read_port_floor=max(rd.values()),write_port_floor=max(wr.values()),lane_floor=max(lane.values()))
pa,pr,pt=price(assembly),price(returns),price(assembly+returns)
result=dict(schema='opentallas.s81.ffn.whole64beat-relocation-model.v1',status='MODEL_ONLY_CALENDAR_BLOCKED',rom_ownership_changed=False,row_tags_changed=False,numeric_order_changed=False,actual_source_counts=[107,107,53,53,107,107,53,53,53,53,107,107,53,53,107,107],assignment_method='For each of20canonical64wordbeats/rank chooseSIDwithmostactualproducerwords; pick unusedleaf preferringproducerleaf. No global optimality claim.',assignments=assignments,assembly_price=pa,combined_return_price=pr,total_transport_price=pt,existing_original_price=dict(controls=d['controls'],separate_rank_control_floor=d['busiest_control_engine_slots']),saving=dict(transport_controls=d['controls']-pt['controls'],separate_rank_floor_cycles=d['busiest_control_engine_slots']-pt['separate_rank_control_floor']),existing_combine_budget=827,minimum_separate_rank_budget_deficit=max(0,pt['separate_rank_control_floor']-827),storage=dict(capture=[128,254],scratch=[304,306],assembled=[320,432],combined_source=[448,464],canonical_combined_receive=[464,480],assembly_leaf_slots=len(used),assembly_leaves_per_rank=20,assembly_rows_per_used_leaf=112,combined_source_rows_per_used_leaf=16,new_canonical_receive_rows_per_used_leaf=16,new_canonical_receive_bytes_per_leaf=256,new_canonical_receive_bytes_per_rank=5120,full_bulk_enabled=False),commands=dict(vs13='Existing OP_MOE n8,seven expert stride16 at assemblyleaf;80commands across4ranks',post='Existing VPPOST mechanism on canonicalleaf with mutablea1base464 instead448;80commands across4ranks',additional_vs13_and_post_control_words=160),blocked=['VPXcapture/scratch/assembly retirement and producerready/lastreader leases absent.','Rows464..480 fit static gap FFNC448..464 to HEADG480..496 but need new explicit dynamic lifetime.','Candidate local mask RTL/native selectedXRT timing not qualified.','Control issue/resource floors omit distribution/pipeline delay,VS13dependency,POSTduration,peerbroadcast and template reload.','No deterministic event calendar yet; no measured throughput or physical adoption.'],scope='Whole64beat assembly relocation plus single combined return preserves canonical POST/H ownership and unchanged ROM107/53 allocation. Pure model; lowerbounds are not full token prices.')
out=r/'final_ffn_relocation_model_0000';out.mkdir(exist_ok=True)
(out/'model.json').write_text(json.dumps(result,indent=1)+'\n')
(out/'legs.json').write_text(json.dumps(assembly+returns,indent=1)+'\n')
print(json.dumps({k:result[k] for k in ['assembly_price','combined_return_price','total_transport_price','saving','minimum_separate_rank_budget_deficit']}))
