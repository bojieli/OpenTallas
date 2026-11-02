import sys,json,collections,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/autopilot'))
import geom_rules as G
D=G.Design('/srv/opentallas-scratch/claude/codex-kv-ctl-place-2330/collector/geom.tsv',[str(Path(__file__).parent/'memory_tt.lib')],True)
pairs=[];m=G.r2r_metrics(D,pairs)
O=Path(__file__).parent;(O/'far_capture_pairs.json').write_text(json.dumps(pairs,indent=1)+'\n')
key=lambda s:re.sub(r'\\?\[\d+\\?\]','[]',s)
launch=collections.Counter(key(p['launch']) for p in pairs);capture=collections.Counter(key(p['capture']) for p in pairs)
# All captures fit a405-Manhattan diamond around a possible common launch
# iff intersected u=x+y and v=x-y ranges are nonempty.
groups=collections.defaultdict(list)
for p in pairs:groups[p['launch']].append(p)
proposals=[]
for name,ps in sorted(groups.items(),key=lambda x:-len(x[1])):
 u0=max(sum(p['capture_xy'])-405 for p in ps);u1=min(sum(p['capture_xy'])+405 for p in ps)
 v0=max(p['capture_xy'][0]-p['capture_xy'][1]-405 for p in ps);v1=min(p['capture_xy'][0]-p['capture_xy'][1]+405 for p in ps)
 proposed=[185.76,185.76];mx=max(abs(p['capture_xy'][0]-proposed[0])+abs(p['capture_xy'][1]-proposed[1]) for p in ps)
 proposals.append(dict(launch=name,old_xy=ps[0]['launch_xy'],far_captures=len(ps),feasible_u=[u0,u1],feasible_v=[v0,v1],feasible=u0<=u1 and v0<=v1,central_target=proposed,central_max_to_far_captures=round(mx,3)))
report=dict(actual=m,launch_groups=launch.most_common(),capture_groups=capture.most_common(),launches=proposals)
(O/'reach_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print('launch_groups',launch.most_common(12));print('capture_groups',capture.most_common(10));print('launch_count',len(proposals),'central_impossible',sum(p['central_max_to_far_captures']>405 for p in proposals));print('top',proposals[:3])
