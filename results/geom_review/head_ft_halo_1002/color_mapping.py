import sys,json,collections
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-head-tree-0830/tools/die_plan')
import schema as S,die_clock_mesh as D
P=S.Plan(S.load('/srv/opentallas-scratch2/claude/wt/codex-head-tree-0830/physical/die_plan/s81_head/die_plan.json'));base=Path('/srv/opentallas-scratch2/claude/codex-head-ft-review-0958');d=json.load(open('/srv/opentallas-scratch2/claude/codex-head-tree-0830/physical_interval_my_8fcd/explicit_tree.json'))
groups=collections.defaultdict(list);edges=collections.defaultdict(list)
for n,c in d['cell_sites'].items():groups['g'+str(c['group'])].append((n,c))
for e in d['nets']:edges[e['drv']].append(e)
out=[]
for g,cs in groups.items():
 lay={e['layer'] for e in edges[g]} if edges[g] else {'M8'}
 if lay!={'M8'}:continue
 parts={c['part'] for n,c in cs};assert len(parts)==1
 pn=next(iter(parts));pt=P.parts[pn];tn=pt['type'];ori=P.orient(pn);ph=P.types[tn]['outline_um'][1];oy=pt['origin_um'][1]
 # Apply lower-gap reservation only to row carriers with this shared354.24 band.
 if tn not in ('hd_tile','hd_spn','hd_spn_end'):continue
 height=max(c['origin_um'][1]+.27 for n,c in cs)-min(c['origin_um'][1] for n,c in cs)
 L,U=330.32,352.78
 dlo,dhi=(oy+L,oy+U) if ori in ('R0','MY') else (oy+ph-U,oy+ph-L)
 current=(min(c['origin_um'][1] for n,c in cs)+max(c['origin_um'][1]+.27 for n,c in cs))/2
 type_center=P.to_type(pn,(pt["origin_um"][0],current))[1]
 if not 328.32 <= type_center <= 380.16:continue
 desired=(dlo+height/2,dhi-height/2)
 # Nearest legal body-centre target; caller must snap to actual PG-gap tracks.
 clamped=min(max(current,desired[0]),desired[1])
 out.append(dict(group=g,part=pn,type=tn,orient=ori,units=len(cs),bank_height_um=round(height,4),current_die_center_y=round(current,4),legal_die_corridor_y=[round(v,4) for v in desired],desired_type_body_y=[L,U],nearest_die_shift_um=round(clamped-current,4),note='Snap corridor to actual M8 PG gaps INSIDE this interval; interval-color overlaps, not one global shift.'))
(base/'lower_gap_group_mapping.json').write_text(json.dumps(dict(rule='type bank body330.32..352.78; transform whole bank and reserve height before PG snapping',groups=out),indent=1)+'\n')
print('groups',len(out),'orientations',dict(collections.Counter(v['orient'] for v in out)),'outside',sum(v['nearest_die_shift_um']!=0 for v in out));print([v for v in out if v['nearest_die_shift_um']!=0][:3])
