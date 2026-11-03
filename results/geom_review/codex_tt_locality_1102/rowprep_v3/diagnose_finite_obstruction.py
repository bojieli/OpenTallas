"""Join the finite87 occupancy obstruction to actual fresh244/live12 phase, no solve."""
from pathlib import Path
import json,collections
P=Path(__file__).parent
prefix=(P/'rowprep_feasible.py').read_text()
# Do not execute guard/budget/solver. Reuse only exact shared graph construction.
common=(P/'rowprep_greedy.py').read_text().split('# Place the most constrained')[0]
common=common.replace("P/'final_composed_homes_DISABLED.json'","P/'rowprep_homes.json'");exec(compile(common,'finite_obstruction_common','exec'))
failed=json.loads((P/'rowprep_report.json').read_text())['failed'];seed={names[n] for n in failed};joint=set(seed)
for i in seed:joint.update(j for j in adj[i] if isinstance(j,int) and j in variables)
cutset=json.loads((P/'rowfeas_occupancy_cuts.json').read_text());fresh={r['name']:r for r in json.loads((P/'fresh_master_changes.json').read_text())}
fixed_ids=sorted({j for i,kind,j in cutset if kind=='F' and j>=0});source_ids=sorted({j for i,kind,j in cutset if kind=='F' and j<0});macro_ids=sorted({j for i,kind,j in cutset if kind=='M'})
edge_subset={(a,b) for a,b in edges if a in joint or b in joint};anchor_ids={n for edge in edge_subset for n in edge if isinstance(n,int) and n not in joint}
def record(i):
 c=d.cells[i];name=c[6];return dict(id=i,name=name,kind=c[0],master=c[1],box=list(c[2:6]),was_moved_guide=i in variables,fresh_change=fresh.get(name),clock_parent=assign.get(name),other_clock_root=next((r['logical_root'] for r in clock['retained_other_cohorts'] if r['name']==name),None))
blockers=[record(i) for i in fixed_ids];jointfresh=[record(i) for i in sorted(joint) if d.cells[i][6] in fresh];anchorfresh=[record(i) for i in sorted(anchor_ids) if d.cells[i][6] in fresh]
# Counter source-slot IDs use -k-1 over exactly source+raw frozen order.
source_blockers=[dict(fixed_index=i,slot=source[-i-1]) for i in source_ids]
macro_records=[record(i) for i in macro_ids]
result=dict(status='FINITE_OBSTRUCTION_CAUSE_JOIN_ONLY',variables=len(joint),typed_incident_edges=len(edge_subset),cut_count=len(cutset),cut_kind_counts=dict(collections.Counter(k for _,k,_ in cutset)),actual_fixed_ff_blockers=blockers,fresh_shrinking_variable_cells=jointfresh,fresh_shrinking_fixed_reach_anchors=anchorfresh,fresh_shrinking_fixed_obstacle_count=sum(r['fresh_change'] is not None for r in blockers),source_slot_obstacles=source_blockers,dead_PD3_obstacle_involved=any(r['slot']['stage']=='pd' and r['slot']['region']==3 for r in source_blockers),actual_fixed_macros=macro_records,all_joint_cells=[record(i) for i in sorted(joint)],actual_live_source_extra_ff=12,declared_source_extra_ff=13,geometry_global_infeasibility_claim=False,native_correspondence='HELD',physical_release=False)
expanded=joint|set(fixed_ids);expanded_edges=set(edge_subset)
for i in fixed_ids:
 for j in walk(i,False):expanded_edges.update(translate(j,i))
 for j in walk(i,True):expanded_edges.update(translate(i,j))
expanded_anchors={n for edge in expanded_edges for n in edge if isinstance(n,int) and n not in expanded}
result['targeted_expansion']=dict(variable_count=len(expanded),added_actual_ff=[record(i) for i in fixed_ids],typed_edges=len(expanded_edges),fresh_shrinking_variable_cells=[record(i) for i in sorted(expanded) if d.cells[i][6] in fresh],fresh_shrinking_fixed_reach_anchors=[record(i) for i in sorted(expanded_anchors) if d.cells[i][6] in fresh],new_TL_pin_bits=[364,368,369,384,392],all_added_ff_clock_roots=[assign.get(d.cells[i][6]) for i in fixed_ids],no_macro_or_tap_or_cycle_change=True,solver_run=False)
(P/'finite_obstruction_diagnosis.json').write_text(json.dumps(result,indent=1)+'\n')
print('FINITE_OBSTRUCTION',len(joint),'vars',len(fixed_ids),'fixedFF',len(macro_ids),'macro; fresh variables',len(jointfresh),'fresh fixedobstacles',result['fresh_shrinking_fixed_obstacle_count'],'fresh anchors',len(anchorfresh),'deadPD3',result['dead_PD3_obstacle_involved'],'expandedfreshanchors',len(result['targeted_expansion']['fresh_shrinking_fixed_reach_anchors']),flush=True)
