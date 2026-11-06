from pathlib import Path
from collections import Counter,defaultdict
import csv,json,re,math
p=Path(__file__).parent
rows=list(csv.DictReader((p/'vm_meta_pipe_complete.tsv').open(),delimiter='\t'));allrows=list(csv.DictReader((p/'clock_membership_native.tsv').open(),delimiter='\t'))
placed={r['name'].replace('\\',''):r for r in csv.DictReader((p.parent/'vA-cts/placed.csv').open())}
for r in rows:
 q=placed[r["instance"]];r["x"],r["y"]=q["x"],q["y"]
bybit=defaultdict(list)
for r in rows:
 st,bit=map(int,re.search(r'vm_meta_pipe\[(\d+)\]\[(\d+)\]',r['native_alias']).groups());r=dict(r,stage=st,bit=bit);bybit[bit].append(r)
for rs in bybit.values():rs.sort(key=lambda r:r['stage'])
base={r['instance']:r['leaf'] for r in rows};failure=list(csv.DictReader((p/'related_hold_native.tsv').open(),delimiter='\t'));origload=Counter(r['leaf'] for r in allrows if r['leaf']);cap=max(origload.values())+4;allcontrol={r['leaf'] for r in allrows if r['native_clock']=='clk_control' and r['leaf'] in placed}
anchors=set(json.loads((p/"vm_meta_external_clock_anchors.json").read_text()))
def model(radius,limit,global_candidates):
 load=origload.copy();assign=base.copy();groups=[];skips=Counter()
 def pick(group):
  if len(group)>limit:return None
  orig=Counter(assign[r['instance']] for r in group)
  cand=allcontrol if global_candidates else set(orig)
  good=[]
  for name in cand:
   if any(r["native_alias"] in anchors and name!=base[r["instance"]] for r in group):continue
   if name not in placed:continue
   d=placed[name];x,y=float(d['x']),float(d['y']);ds=[abs(float(r['x'])-x)+abs(float(r['y'])-y) for r in group]
   if max(ds)>radius:continue
   if load[name]+len(group)-orig[name]>cap:continue
   good.append((len(group)-orig[name],sum(ds),name,max(ds)))
  return min(good) if good else None
 def flush(group):
  if len(group)<2:return
  target=pick(group)
  if target is None:skips['no_legal_radius_or_capacity']+=1;return
  _,cost,name,maxdist=target;orig={assign[r['instance']] for r in group}
  if orig=={name}:return
  for r in group:
   old=assign[r['instance']];load[old]-=1;load[name]+=1;assign[r['instance']]=name
  groups.append({'bit':group[0]['bit'],'first_stage':group[0]['stage'],'last_stage':group[-1]['stage'],'n':len(group),'target_leaf':name,'max_radius_um':maxdist,'bbox':[min(float(r['x']) for r in group),min(float(r['y']) for r in group),max(float(r['x']) for r in group),max(float(r['y']) for r in group)],'instances':[r['instance'] for r in group]})
 priority={}
 for f in failure:
  m=re.search(r"vm_meta_pipe\[\d+\]\[(\d+)\]",f["native_end"])
  if m:priority[int(m[1])]=min(priority.get(int(m[1]),0),float(f["slack_ps"]))
 for bit,rs in sorted(bybit.items(),key=lambda x:(priority.get(x[0],0),x[0])):
  runs=[]
  for r in rs:
   if not runs or runs[-1][-1]['leaf']!=r['leaf']:runs.append([])
   runs[-1].append(r)
  seg=[]
  weights={}
  for f in failure:
   ma=re.search(r"vm_meta_pipe\[(\d+)\]\[(\d+)\]",f['native_start']);mb=re.search(r"vm_meta_pipe\[(\d+)\]\[(\d+)\]",f['native_end'])
   if ma and mb and int(ma[2])==bit and int(mb[2])==bit and int(mb[1])==int(ma[1])+1:weights[int(mb[1])]=abs(float(f['slack_ps']))
  for ri,run in enumerate(runs):
   if seg and ri+1<len(runs):
    nxt=runs[ri+1]
    if weights.get(nxt[0]['stage'],0)>weights.get(run[0]['stage'],0) and pick(seg+run+nxt) is None and pick(run+nxt) is not None:
     flush(seg);seg=[]
   if len(run)>limit:flush(seg);seg=[];skips['coherent_run_over_limit']+=1;continue
   trial=seg+run
   if seg and pick(trial) is None:flush(seg);seg=[]
   seg+=run
  flush(seg)
 edges=[(rs[i-1],rs[i]) for rs in bybit.values() for i in range(1,len(rs))]
 oldcross=sum(a['leaf']!=b['leaf'] for a,b in edges);newcross=sum(assign[a['instance']]!=assign[b['instance']] for a,b in edges);newedges=sum(a['leaf']==b['leaf'] and assign[a['instance']]!=assign[b['instance']] for a,b in edges);assert newedges==0
 improved=[]
 for f in failure:
  a=f['startpoint'].rsplit('/',1)[0];b=f['endpoint'].rsplit('/',1)[0]
  if a in assign and b in assign and f['launch_leaf']!=f['capture_leaf'] and assign[a]==assign[b]:improved.append(f)
 return {'radius_um':radius,'group_limit':limit,'leaf_sink_cap':cap,'candidate_scope':'all_existing_clk_control_leaves' if global_candidates else 'member_leaves_only','groups':groups,'skip_counts':dict(skips),'moved_members':sum(assign[k]!=v for k,v in base.items()),'new_leaf_load_max':max(load.values()),'chain_cross_leaf_before':oldcross,'chain_cross_leaf_after':newcross,'new_A_relative_chain_crossings':newedges,'negative_RR_pairs_coleaf_after':len(improved),'worst_original_pair_now_coleaf':any('_231143_[110]' in f['startpoint'] for f in improved),'source':'existingCTS geometry only; not STA or new placement; no new cells or data/clock/reset edits'}
results=[]
for global_candidates in [False]:
 for rad in [30,50]:
  r=model(rad,24,global_candidates);name='anchored_'+('all_control' if global_candidates else 'member')+'_'+str(rad);(p/('model_'+name+'.json')).write_text(json.dumps(r,indent=2));results.append({k:v for k,v in r.items() if k!='groups'}|{'group_count':len(r['groups']),'artifact':'model_'+name+'.json'})
(p/'models_anchored_summary.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
